from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

from .data import build_snapshot
from .backtest import run_backtest
from .engine import score_snapshot
from .models import InputSnapshot
from .overrides import apply_overrides, read_overrides
from .reporting import write_json, write_workbook
from .storage import record_and_rank, update_paths


USER_DATA_ROOT = Path(os.environ.get("WHARTON_DATA_DIR", Path.home() / "Documents" / "Wharton Growth Scorer"))
COUNTRY_CODES = {"US", "JP", "GB", "IN", "TW", "KR"}
SCORECARDS = {
    "auto", "general", "technology", "healthcare", "financial_platform", "industrial",
    "consumer", "energy_materials", "bank", "insurer", "biotech", "semiconductor",
    "memory_semiconductor",
}


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD") from exc


def _safe_name(ticker: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", ticker)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="growth_scorer", description="Deterministic growth-sleeve stock scorer")
    subparsers = parser.add_subparsers(dest="command", required=True)
    score = subparsers.add_parser("score", aliases=["predict"], help="score one analyst-vetted stock")
    score.add_argument("--ticker", help="exact Yahoo Finance ticker")
    score.add_argument("--country", choices=["US", "JP", "GB", "IN", "TW", "KR"])
    score.add_argument("--as-of", type=_date)
    score.add_argument("--scorecard", default="auto", choices=["auto", "general", "technology", "healthcare", "financial_platform", "industrial", "consumer", "energy_materials", "bank", "insurer", "biotech", "semiconductor", "memory_semiconductor"])
    score.add_argument("--overrides", type=Path)
    score.add_argument("--snapshot", type=Path, help="replay an existing frozen snapshot instead of downloading")
    score.add_argument("--output-dir", type=Path, default=USER_DATA_ROOT / "output" / "scores")
    score.add_argument("--data-dir", type=Path, default=USER_DATA_ROOT / "data" / "snapshots")
    score.add_argument("--history-db", type=Path, default=USER_DATA_ROOT / "data" / "score_history.sqlite3")
    backtest = subparsers.add_parser("backtest", help="run a historical multi-company scoring comparison")
    backtest.add_argument("--universe", type=Path, default=Path("config/backtest_universe.csv"))
    backtest.add_argument("--start", required=True, type=_date)
    backtest.add_argument("--end", required=True, type=_date)
    backtest.add_argument("--output-dir", type=Path, default=Path("output/backtest"))
    backtest.add_argument("--reuse-snapshots", action="store_true", help="reuse previously frozen scoring inputs")
    return parser


def _interactive_score_args(args: argparse.Namespace) -> argparse.Namespace:
    interactive = not (args.ticker and args.country and args.as_of)
    if not interactive:
        return args
    if not args.ticker:
        print("Wharton Growth Scorer")
        print("Enter one stock already checked by your team for WInS eligibility.\n")
        args.ticker = input(
            "Stock ticker in Yahoo Finance format "
            "(MSFT / 7203.T / AZN.L / TCS.NS / 2330.TW / 000660.KS): "
        ).strip().upper()
    if not args.country:
        while True:
            value = input("Matching country code [US / JP / GB / IN / TW / KR]: ").strip().upper()
            if value in COUNTRY_CODES:
                args.country = value
                break
            print("Please enter US, JP, GB, IN, TW, or KR.")
    if not args.as_of:
        raw = input(f"As-of date YYYY-MM-DD [{date.today().isoformat()}]: ").strip()
        args.as_of = date.today() if not raw else _date(raw)
    if args.scorecard == "auto":
        raw_scorecard = input("Scorecard [press Enter for automatic sector selection]: ").strip().lower()
        if raw_scorecard:
            if raw_scorecard not in SCORECARDS:
                raise ValueError("Invalid scorecard. Use auto, general, technology, healthcare, financial_platform, industrial, consumer, energy_materials, bank, insurer, biotech, semiconductor, or memory_semiconductor.")
            args.scorecard = raw_scorecard
    if args.overrides is None:
        raw_override = input("Verified override workbook path [press Enter to skip]: ").strip().strip('"')
        if raw_override:
            args.overrides = Path(raw_override)
    return args


def _validate_ticker_country(ticker: str, country: str) -> None:
    ticker = ticker.upper()
    valid = {
        "US": lambda value: not value.endswith((".T", ".L", ".NS", ".BO", ".TW", ".TWO", ".KS", ".KQ")),
        "JP": lambda value: value.endswith(".T"),
        "GB": lambda value: value.endswith(".L"),
        "IN": lambda value: value.endswith((".NS", ".BO")),
        "TW": lambda value: value.endswith((".TW", ".TWO")),
        "KR": lambda value: value.endswith((".KS", ".KQ")),
    }
    examples = {"US": "MSFT", "JP": "7203.T", "GB": "AZN.L", "IN": "TCS.NS", "TW": "2330.TW", "KR": "000660.KS"}
    if country not in valid or not valid[country](ticker):
        raise ValueError(f"Ticker {ticker} does not match country {country}. Example: {examples.get(country, 'MSFT')}")


def run_score(args: argparse.Namespace) -> int:
    args = _interactive_score_args(args)
    args.ticker = args.ticker.strip().upper()
    _validate_ticker_country(args.ticker, args.country)
    print("\nDownloading prices, statements, exchange rates, benchmarks, and eligible news...")
    if args.snapshot:
        snapshot = InputSnapshot.load(args.snapshot)
        if snapshot.ticker.upper() != args.ticker.upper() or snapshot.country != args.country or snapshot.as_of != args.as_of:
            raise ValueError("Snapshot ticker, country, and as-of date must match the command")
    else:
        snapshot = build_snapshot(args.ticker, args.country, args.as_of)

    if args.overrides:
        records, warnings = read_overrides(args.overrides, args.as_of)
        apply_overrides(snapshot, records, warnings)

    ticker_name = _safe_name(snapshot.ticker)
    frozen_path = args.data_dir / ticker_name / f"{args.as_of.isoformat()}.json"
    snapshot.save(frozen_path)
    result = score_snapshot(snapshot, args.scorecard)
    result.snapshot_path = str(frozen_path.resolve())
    rank, count = record_and_rank(args.history_db, result)
    result.rank = rank
    result.comparable_count = count
    if count < 2:
        result.warnings.append("Weekly rank is not meaningful until at least two companies use the same scorecard")

    run_dir = args.output_dir / args.as_of.isoformat()
    base = f"{ticker_name}_{args.as_of.isoformat()}_{result.scorecard}"
    workbook_path = run_dir / f"{base}.xlsx"
    json_path = run_dir / f"{base}.json"
    result.workbook_path = str(workbook_path.resolve())
    result.json_path = str(json_path.resolve())
    write_workbook(workbook_path, result, snapshot)
    write_json(json_path, result)
    update_paths(args.history_db, result)

    rank_text = "not meaningful (fewer than two comparables)" if rank is None else f"{rank} of {count}"
    print(f"{result.ticker}: {result.score:.2f}/100 - {result.verdict}")
    print(f"Scorecard: {result.scorecard}; confidence: {result.confidence:.1f}%; weekly rank: {rank_text}")
    print(f"Excel report created: {workbook_path.resolve()}")
    print(f"JSON: {json_path.resolve()}")
    print(f"Snapshot: {frozen_path.resolve()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] in {"-predict", "--predict"}:
        argv[0] = "predict"
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command in {"score", "predict"}:
            return run_score(args)
        if args.command == "backtest":
            csv_path, json_path, payload = run_backtest(
                args.universe,
                args.start,
                args.end,
                args.output_dir,
                reuse_snapshots=args.reuse_snapshots,
            )
            print(f"Completed {payload['summary']['companies']} companies")
            print(f"CSV: {csv_path.resolve()}")
            print(f"JSON: {json_path.resolve()}")
            return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 1
