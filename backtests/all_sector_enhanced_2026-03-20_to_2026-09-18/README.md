# All-sector enhanced backtest

This folder freezes the 20 March 2026 inputs and six-month outcomes used for the sector-aware comparison in the report.

- Universe: 18 companies across the six team mandates and five markets.
- Scorecards: technology, healthcare, bank, insurer, industrial, consumer, energy/materials, and semiconductor.
- News: no eligible March 2026 Yahoo Finance articles were available when the retrospective test ran. News factors were therefore neutral and reduced confidence by five percentage points; current headlines were not substituted.
- Result: score/return Spearman correlation 0.566; benchmark-relative correlation 0.440; directional hit rate 88.9%.

Reproduce from the repository root:

```powershell
wharton backtest --universe config/enhanced_backtest_universe.csv --start 2026-03-20 --end 2026-09-18 --output-dir backtests/all_sector_enhanced_2026-03-20_to_2026-09-18 --reuse-snapshots
```

Frozen snapshots are the audit record because Yahoo Finance may later revise historical data.
