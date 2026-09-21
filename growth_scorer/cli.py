from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from .data import build_snapshot
from .backtest import run_backtest
from .batch import BatchItem, read_batch_csv, run_batch
from .engine import classify, score_snapshot
from .models import InputSnapshot
from .overrides import apply_overrides, discover_override, read_overrides
from .reporting import write_json, write_workbook
from .storage import record_and_rank, update_paths
from .validation import COUNTRY_CODES, SCORECARDS, safe_name, validate_ticker_country


USER_DATA_ROOT = Path(os.environ.get("WHARTON_DATA_DIR", Path.home() / "Documents" / "Wharton Growth Scorer"))
_safe_name = safe_name
_validate_ticker_country = validate_ticker_country


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="growth_scorer", description="Deterministic growth-sleeve stock scorer")
    subparsers = parser.add_subparsers(dest="command", required=True)
    score = subparsers.add_parser("score", aliases=["predict"], help="score one analyst-vetted stock")
    score.add_argument("--ticker", help="exact Yahoo Finance ticker")
    score.add_argument("--country", choices=["US", "JP", "GB", "IN", "TW", "KR"])
    score.add_argument("--as-of", type=_date)
    score.add_argument("--scorecard", default="auto", choices=["auto", "general", "technology", "healthcare", "financial_platform", "industrial", "consumer", "energy_materials", "bank", "insurer", "biotech", "semiconductor", "memory_semiconductor"])
    score.add_argument("--overrides", type=Path)
    score.add_argument("--overrides-dir", type=Path, default=USER_DATA_ROOT / "overrides", help="folder searched for ticker-specific verified overrides")
    score.add_argument("--snapshot", type=Path, help="replay an existing frozen snapshot instead of downloading")
    score.add_argument("--output-dir", type=Path, default=USER_DATA_ROOT / "output" / "scores")
    score.add_argument("--data-dir", type=Path, default=USER_DATA_ROOT / "data" / "snapshots")
    score.add_argument("--history-db", type=Path, default=USER_DATA_ROOT / "data" / "score_history.sqlite3")
    batch = subparsers.add_parser("batch", help="score multiple stocks in one run and create a comparison workbook")
    batch.add_argument("--input", type=Path, help="CSV with ticker, country, optional scorecard and overrides columns")
    batch.add_argument("--as-of", type=_date)
    batch.add_argument("--output-dir", type=Path, default=USER_DATA_ROOT / "output" / "batches")
    batch.add_argument("--data-dir", type=Path, default=USER_DATA_ROOT / "data" / "snapshots")
    batch.add_argument("--history-db", type=Path, default=USER_DATA_ROOT / "data" / "score_history.sqlite3")
    batch.add_argument("--overrides-dir", type=Path, default=USER_DATA_ROOT / "overrides", help="folder searched for ticker-specific verified overrides")
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
        raw_override = input("Verified override workbook [Enter to auto-search the overrides folder]: ").strip().strip('"')
        if raw_override:
            args.overrides = Path(raw_override)
    return args


def _interactive_batch_args(args: argparse.Namespace) -> tuple[argparse.Namespace, list[BatchItem] | None]:
    if not args.as_of:
        raw = input(f"One as-of date for the whole batch YYYY-MM-DD [{date.today().isoformat()}]: ").strip()
        args.as_of = date.today() if not raw else _date(raw)
    if args.input:
        return args, None

    print("\nAdd companies one at a time. Press Enter on a blank ticker when finished.")
    items: list[BatchItem] = []
    while True:
        ticker = input(f"Company {len(items) + 1} ticker [blank to run batch]: ").strip().upper()
        if not ticker:
            if items:
                break
            print("Please add at least one company.")
            continue
        while True:
            country = input("Country code [US / JP / GB / IN / TW / KR]: ").strip().upper()
            if country in COUNTRY_CODES:
                break
            print("Please enter US, JP, GB, IN, TW, or KR.")
        scorecard = input("Scorecard [press Enter for automatic selection]: ").strip().lower() or "auto"
        if scorecard not in SCORECARDS:
            raise ValueError(f"Invalid scorecard: {scorecard}")
        override = input("Verified override workbook [Enter to auto-search the overrides folder]: ").strip().strip('"')
        items.append(BatchItem(ticker, country, scorecard, Path(override) if override else None))
        print(f"Added {ticker}. Total companies: {len(items)}\n")
    return args, items


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

    detected_scorecard = classify(snapshot, args.scorecard)
    override_path = args.overrides or discover_override(args.overrides_dir, snapshot.ticker, detected_scorecard)
    if override_path:
        records, warnings = read_overrides(override_path, args.as_of)
        apply_overrides(snapshot, records, warnings)
        if args.overrides is None:
            snapshot.warnings.append(f"Automatically applied ticker-specific verified overrides: {override_path}")

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
        if args.command == "batch":
            args, interactive_items = _interactive_batch_args(args)
            items = interactive_items if interactive_items is not None else read_batch_csv(args.input)
            workbook_path, json_path, payload = run_batch(
                items, args.as_of, args.output_dir, args.data_dir, args.history_db, args.overrides_dir,
            )
            print(f"\nBatch complete: {payload['successful']} scored, {payload['failed']} failed")
            print(f"Batch Excel summary: {workbook_path.resolve()}")
            print(f"Batch JSON summary: {json_path.resolve()}")
            print(f"Individual reports: {(workbook_path.parent / 'companies').resolve()}")
            return 0 if payload["successful"] else 1
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
