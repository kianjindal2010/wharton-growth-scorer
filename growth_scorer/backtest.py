from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import __version__
from .config import COUNTRIES
from .data import _adjusted_close, _download, _to_usd, build_snapshot
from .engine import score_snapshot


def _return(series: pd.Series) -> float | None:
    clean = series.dropna()
    if len(clean) < 2 or clean.iloc[0] == 0:
        return None
    return float(clean.iloc[-1] / clean.iloc[0] - 1)


def _forward_returns(ticker: str, country: str, start: date, end: date) -> dict[str, Any]:
    config = COUNTRIES[country]
    prices = _download(ticker, start, end, actions=True)
    benchmark = _download(str(config["benchmark"]), start, end)
    fx_symbol = config["fx"]
    fx = _download(str(fx_symbol), start, end) if fx_symbol else pd.DataFrame()
    local = _adjusted_close(prices)
    local_benchmark = _adjusted_close(benchmark)
    fx_close = _adjusted_close(fx) if not fx.empty else pd.Series(1.0, index=local.index)
    usd = _to_usd(local, fx_close, str(config["fx_mode"]))
    usd_benchmark = _to_usd(local_benchmark, fx_close, str(config["fx_mode"]))
    local_return = _return(local)
    benchmark_local_return = _return(local_benchmark)
    usd_return = _return(usd)
    benchmark_usd_return = _return(usd_benchmark)
    return {
        "performance_start": local.index[0].date().isoformat() if not local.empty else None,
        "performance_end": local.index[-1].date().isoformat() if not local.empty else None,
        "local_return": local_return,
        "usd_return": usd_return,
        "benchmark_local_return": benchmark_local_return,
        "benchmark_usd_return": benchmark_usd_return,
        "local_excess_return": None
        if local_return is None or benchmark_local_return is None
        else local_return - benchmark_local_return,
        "usd_excess_return": None
        if usd_return is None or benchmark_usd_return is None
        else usd_return - benchmark_usd_return,
        "benchmark": config["benchmark"],
    }


def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    frame = pd.DataFrame(records)
    actionable = frame.loc[frame["verdict"] != "Insufficient Data"].dropna(subset=["score", "usd_return", "usd_excess_return"])
    buy = actionable.loc[actionable["verdict"] == "Buy Candidate"]
    watch = actionable.loc[actionable["verdict"] == "Watch"]
    reject = actionable.loc[actionable["verdict"] == "Reject"]
    score_corr = actionable["score"].rank().corr(actionable["usd_return"].rank()) if len(actionable) >= 3 else np.nan
    excess_corr = actionable["score"].rank().corr(actionable["usd_excess_return"].rank()) if len(actionable) >= 3 else np.nan
    ordered = actionable.sort_values("score", ascending=False)
    quartile_size = max(1, len(ordered) // 4) if len(ordered) else 0
    top_return = ordered.head(quartile_size)["usd_return"].mean() if quartile_size else np.nan
    bottom_return = ordered.tail(quartile_size)["usd_return"].mean() if quartile_size else np.nan
    directional = pd.concat([
        buy.assign(hit=buy["usd_excess_return"] > 0),
        reject.assign(hit=reject["usd_excess_return"] < 0),
    ])

    def number(value: Any) -> float | None:
        return None if pd.isna(value) else float(value)

    return {
        "companies": int(len(frame)),
        "actionable_companies": int(len(actionable)),
        "insufficient_data_companies": int((frame["verdict"] == "Insufficient Data").sum()),
        "buy_candidates": int(len(buy)),
        "watch_companies": int(len(watch)),
        "reject_companies": int(len(reject)),
        "spearman_score_vs_usd_return": number(score_corr),
        "spearman_score_vs_usd_excess_return": number(excess_corr),
        "top_quartile_mean_usd_return": number(top_return),
        "bottom_quartile_mean_usd_return": number(bottom_return),
        "top_minus_bottom_spread": number(top_return - bottom_return) if quartile_size else None,
        "buy_mean_usd_return": number(buy["usd_return"].mean()),
        "buy_mean_usd_excess_return": number(buy["usd_excess_return"].mean()),
        "watch_mean_usd_return": number(watch["usd_return"].mean()),
        "reject_mean_usd_return": number(reject["usd_return"].mean()),
        "directional_hit_rate": number(directional["hit"].mean()) if len(directional) else None,
    }


def run_backtest(
    universe_path: Path,
    start: date,
    end: date,
    output_dir: Path,
    reuse_snapshots: bool = False,
) -> tuple[Path, Path, dict[str, Any]]:
    if end <= start:
        raise ValueError("Backtest end date must be after start date")
    universe = pd.read_csv(universe_path)
    required = {"ticker", "country", "company", "mandate"}
    if not required.issubset({str(column).lower() for column in universe.columns}):
        raise ValueError(f"Universe CSV requires columns: {', '.join(sorted(required))}")

    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir = output_dir / "snapshots"
    records: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for row in universe.to_dict("records"):
        ticker = str(row["ticker"]).strip()
        country = str(row["country"]).strip().upper()
        try:
            snapshot_path = snapshot_dir / f"{ticker.replace('^', '_')}_{start.isoformat()}.json"
            if reuse_snapshots and snapshot_path.exists():
                from .models import InputSnapshot

                snapshot = InputSnapshot.load(snapshot_path)
            else:
                snapshot = build_snapshot(ticker, country, start)
                snapshot.save(snapshot_path)
                snapshot.save(snapshot_path)
            requested_scorecard = str(row.get("scorecard", "auto") or "auto").strip().lower()
            result = score_snapshot(snapshot, requested_scorecard)
            performance = _forward_returns(ticker, country, start, end)
            records.append({
                "ticker": ticker,
                "company": row["company"],
                "country": country,
                "mandate": row["mandate"],
                "scorecard": result.scorecard,
                "score": result.score,
                "verdict": result.verdict,
                "confidence": result.confidence,
                "risk_gates": "; ".join(result.risk_gates),
                "warnings_count": len(result.warnings),
                **performance,
                "snapshot_path": str(Path("snapshots") / snapshot_path.name),
            })
            print(f"[{len(records) + len(failures)}/{len(universe)}] {ticker}: {result.score:.2f} {result.verdict}", flush=True)
        except Exception as exc:
            failures.append({"ticker": ticker, "country": country, "error": str(exc)})
            print(f"[{len(records) + len(failures)}/{len(universe)}] {ticker}: FAILED {exc}", flush=True)

    if not records:
        raise RuntimeError("No company completed the backtest")
    summary = _summary(records)
    payload = {
        "method": {
            "model_version": __version__,
            "scoring_date": start.isoformat(),
            "performance_end_date": end.isoformat(),
            "created_at": datetime.now().astimezone().isoformat(),
            "return_basis": "Adjusted-close total return; USD return and local-benchmark-relative return",
            "point_in_time_warning": (
                "Yahoo Finance statement periods were filtered to dates on or before the scoring date, "
                "but historical filing publication timestamps and restatement vintages were unavailable. "
                "This is a retrospective screening test, not a fully point-in-time institutional backtest."
            ),
        },
        "summary": summary,
        "scorecard_summaries": {
            scorecard: _summary([record for record in records if record["scorecard"] == scorecard])
            for scorecard in sorted({record["scorecard"] for record in records})
        },
        "records": records,
        "failures": failures,
    }
    csv_path = output_dir / "backtest_results.csv"
    json_path = output_dir / "backtest_results.json"
    pd.DataFrame(records).to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    return csv_path, json_path, payload
