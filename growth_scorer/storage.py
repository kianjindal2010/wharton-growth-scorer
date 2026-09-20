from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

from .models import ScoreResult


SCHEMA = """
CREATE TABLE IF NOT EXISTS score_history (
    ticker TEXT NOT NULL,
    country TEXT NOT NULL,
    as_of TEXT NOT NULL,
    week_start TEXT NOT NULL,
    scorecard TEXT NOT NULL,
    score REAL NOT NULL,
    verdict TEXT NOT NULL,
    confidence REAL NOT NULL,
    snapshot_path TEXT,
    workbook_path TEXT,
    json_path TEXT,
    PRIMARY KEY (ticker, as_of, scorecard)
)
"""


def _week_start(result: ScoreResult) -> str:
    return (result.as_of - timedelta(days=result.as_of.weekday())).isoformat()


def record_and_rank(path: Path, result: ScoreResult) -> tuple[int | None, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(SCHEMA)
        connection.execute(
            """
            INSERT INTO score_history (
                ticker, country, as_of, week_start, scorecard, score, verdict,
                confidence, snapshot_path, workbook_path, json_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, as_of, scorecard) DO UPDATE SET
                country=excluded.country,
                week_start=excluded.week_start,
                score=excluded.score,
                verdict=excluded.verdict,
                confidence=excluded.confidence,
                snapshot_path=excluded.snapshot_path,
                workbook_path=excluded.workbook_path,
                json_path=excluded.json_path
            """,
            (
                result.ticker,
                result.country,
                result.as_of.isoformat(),
                _week_start(result),
                result.scorecard,
                result.score,
                result.verdict,
                result.confidence,
                result.snapshot_path,
                result.workbook_path,
                result.json_path,
            ),
        )
        rows = connection.execute(
            """
            SELECT ticker, MAX(score) AS score
            FROM score_history
            WHERE week_start = ? AND scorecard = ?
            GROUP BY ticker
            ORDER BY score DESC, ticker ASC
            """,
            (_week_start(result), result.scorecard),
        ).fetchall()
        connection.commit()
    if len(rows) < 2:
        return None, len(rows)
    rank = next(index for index, row in enumerate(rows, start=1) if row[0] == result.ticker)
    return rank, len(rows)


def update_paths(path: Path, result: ScoreResult) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            UPDATE score_history SET snapshot_path=?, workbook_path=?, json_path=?
            WHERE ticker=? AND as_of=? AND scorecard=?
            """,
            (
                result.snapshot_path,
                result.workbook_path,
                result.json_path,
                result.ticker,
                result.as_of.isoformat(),
                result.scorecard,
            ),
        )
        connection.commit()

