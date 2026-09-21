from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from .batch import BatchItem, run_batch
from .data import build_snapshot
from .engine import score_snapshot
from .reporting import write_json, write_workbook
from .storage import record_and_rank, update_paths
from .validation import (
    COUNTRY_CODES,
    infer_country_from_ticker,
    normalize_ticker_for_country,
    safe_name,
    validate_ticker_country,
)


APP_HOST = "127.0.0.1"
APP_PORT = 8765
USER_DATA_ROOT = Path(
    os.environ.get("WHARTON_DATA_DIR", Path.home() / "Documents" / "Wharton Growth Scorer")
)


def parse_as_of(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Use an as-of date in YYYY-MM-DD format") from exc
    if parsed > date.today():
        raise ValueError("The as-of date cannot be in the future")
    return parsed


def parse_batch_items(raw_items: Any) -> list[BatchItem]:
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("Add at least one company to the batch")
    if len(raw_items) > 100:
        raise ValueError("A batch can contain at most 100 companies")
    items: list[BatchItem] = []
    for number, raw in enumerate(raw_items, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Company {number} is invalid")
        ticker = str(raw.get("ticker", "")).strip().upper()
        country = str(raw.get("country", "")).strip().upper()
        if not ticker:
            raise ValueError(f"Company {number} needs a ticker")
        if country:
            ticker = normalize_ticker_for_country(ticker, country)
        else:
            country = infer_country_from_ticker(ticker)
        validate_ticker_country(ticker, country)
        items.append(BatchItem(ticker=ticker, country=country, scorecard="auto"))
    return items


def score_company(ticker: str, country: str, as_of: date) -> dict[str, Any]:
    ticker = normalize_ticker_for_country(ticker, country)
    country = country.strip().upper()
    validate_ticker_country(ticker, country)

    output_dir = USER_DATA_ROOT / "output" / "scores"
    data_dir = USER_DATA_ROOT / "data" / "snapshots"
    history_db = USER_DATA_ROOT / "data" / "score_history.sqlite3"

    snapshot = build_snapshot(ticker, country, as_of)
    ticker_name = safe_name(snapshot.ticker)
    frozen_path = data_dir / ticker_name / f"{as_of.isoformat()}.json"
    snapshot.save(frozen_path)
    result = score_snapshot(snapshot, "auto")
    result.snapshot_path = str(frozen_path.resolve())
    rank, count = record_and_rank(history_db, result)
    result.rank = rank
    result.comparable_count = count
    if count < 2:
        result.warnings.append(
            "Weekly rank is not meaningful until at least two companies use the same scorecard"
        )

    run_dir = output_dir / as_of.isoformat()
    base = f"{ticker_name}_{as_of.isoformat()}_{result.scorecard}"
    workbook_path = run_dir / f"{base}.xlsx"
    json_path = run_dir / f"{base}.json"
    result.workbook_path = str(workbook_path.resolve())
    result.json_path = str(json_path.resolve())
    write_workbook(workbook_path, result, snapshot)
    write_json(json_path, result)
    update_paths(history_db, result)

    return {
        "ticker": result.ticker,
        "company_name": result.company_name or result.ticker,
        "score": result.score,
        "verdict": result.verdict,
        "confidence": result.confidence,
        "scorecard": result.scorecard,
        "classification_reason": result.classification_reason,
        "rank": result.rank,
        "comparable_count": result.comparable_count,
        "warnings": result.warnings,
        "risk_gates": result.risk_gates,
        "workbook_path": str(workbook_path.resolve()),
        "output_directory": str(run_dir.resolve()),
    }


def score_batch(raw_items: Any, as_of: date) -> dict[str, Any]:
    items = parse_batch_items(raw_items)
    workbook_path, _, payload = run_batch(
        items,
        as_of,
        USER_DATA_ROOT / "output" / "batches",
        USER_DATA_ROOT / "data" / "snapshots",
        USER_DATA_ROOT / "data" / "score_history.sqlite3",
    )
    return {
        "successful": payload["successful"],
        "failed": payload["failed"],
        "verdict_counts": payload["verdict_counts"],
        "results": payload["results"],
        "failures": payload["failures"],
        "workbook_path": str(workbook_path.resolve()),
        "output_directory": str(workbook_path.parent.resolve()),
    }


def _open_path(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class AppServer(ThreadingHTTPServer):
    daemon_threads = True
    allowed_paths: set[Path]

    def __init__(self, address: tuple[str, int]):
        super().__init__(address, AppHandler)
        self.allowed_paths = set()

    def allow_artifacts(self, payload: dict[str, Any]) -> None:
        for key in ("workbook_path", "output_directory"):
            value = payload.get(key)
            if value:
                self.allowed_paths.add(Path(value).resolve())


class AppHandler(BaseHTTPRequestHandler):
    server: AppServer

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid request length") from exc
        if length <= 0 or length > 1_000_000:
            raise ValueError("Invalid request size")
        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid request data") from exc
        if not isinstance(payload, dict):
            raise ValueError("Invalid request data")
        return payload

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/api/health":
            self._json(200, {"status": "ok"})
            return
        if path not in {"/", "/index.html"}:
            self.send_error(404)
            return
        body = files("growth_scorer").joinpath("web/index.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
            if self.path == "/api/score":
                result = score_company(
                    str(payload.get("ticker", "")),
                    str(payload.get("country", "")),
                    parse_as_of(str(payload.get("as_of", ""))),
                )
                self.server.allow_artifacts(result)
                self._json(200, {"ok": True, "result": result})
                return
            if self.path == "/api/batch":
                result = score_batch(payload.get("items"), parse_as_of(str(payload.get("as_of", ""))))
                self.server.allow_artifacts(result)
                self._json(200, {"ok": True, "result": result})
                return
            if self.path == "/api/open":
                requested = Path(str(payload.get("path", ""))).resolve()
                if requested not in self.server.allowed_paths or not requested.exists():
                    raise ValueError("That output is not available from this session")
                _open_path(requested)
                self._json(200, {"ok": True})
                return
            if self.path == "/api/shutdown":
                self._json(200, {"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            self._json(404, {"ok": False, "error": "Unknown action"})
        except Exception as exc:
            self._json(400, {"ok": False, "error": str(exc)})


def _existing_app_is_running() -> bool:
    try:
        with urlopen(f"http://{APP_HOST}:{APP_PORT}/api/health", timeout=1) as response:
            return response.status == 200 and json.loads(response.read()).get("status") == "ok"
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return False


def main() -> int:
    url = f"http://{APP_HOST}:{APP_PORT}/"
    if _existing_app_is_running():
        webbrowser.open(url)
        return 0
    try:
        server = AppServer((APP_HOST, APP_PORT))
    except OSError:
        server = AppServer((APP_HOST, 0))
        url = f"http://{APP_HOST}:{server.server_port}/"
    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
