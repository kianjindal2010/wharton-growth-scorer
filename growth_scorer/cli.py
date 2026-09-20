from __future__ import annotations

import argparse
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
    score.add_argument("--output-dir", type=Path, default=Path("output/scores"))
    score.add_argument("--data-dir", type=Path, default=Path("data/snapshots"))
    score.add_argument("--history-db", type=Path, default=Path("data/score_history.sqlite3"))
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
        args.ticker = input("Yahoo Finance ticker (example 2330.TW): ").strip()
    if not args.country:
        while True:
            value = input("Country code [US, JP, GB, IN, TW, KR]: ").strip().upper()
            if value in {"US", "JP", "GB", "IN", "TW", "KR"}:
                args.country = value
                break
            print("Please enter US, JP, GB, IN, TW, or KR.")
    if not args.as_of:
        raw = input(f"As-of date YYYY-MM-DD [{date.today().isoformat()}]: ").strip()
        args.as_of = date.today() if not raw else _date(raw)
    if args.scorecard == "auto":
        raw_scorecard = input("Scorecard [auto/general/technology/healthcare/financial_platform/industrial/consumer/energy_materials/bank/insurer/biotech/semiconductor/memory_semiconductor] [auto]: ").strip().lower()
        if raw_scorecard:
            if raw_scorecard not in {"auto", "general", "technology", "healthcare", "financial_platform", "industrial", "consumer", "energy_materials", "bank", "insurer", "biotech", "semiconductor", "memory_semiconductor"}:
                raise ValueError("Invalid scorecard")
            args.scorecard = raw_scorecard
    if args.overrides is None:
        raw_override = input("Verified override workbook path [press Enter to skip]: ").strip().strip('"')
        if raw_override:
            args.overrides = Path(raw_override)
    return args


def run_score(args: argparse.Namespace) -> int:
    args = _interactive_score_args(args)
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
    print(f"{result.ticker}: {result.score:.2f}/100 — {result.verdict}")
    print(f"Scorecard: {result.scorecard}; confidence: {result.confidence:.1f}%; weekly rank: {rank_text}")
    print(f"Workbook: {workbook_path.resolve()}")
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
