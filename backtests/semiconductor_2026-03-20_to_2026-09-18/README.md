# DRAM manufacturers and TSMC diagnostic

This folder contains the original long-term-semiconductor run, the enhanced cycle-aware run, and the frozen inputs for Micron, SK Hynix, Samsung Electronics, Nanya, Winbond, and TSMC.

The five memory manufacturers use `memory_semiconductor`; TSMC uses `semiconductor`. The dated DRAM pricing override is stored in `config/overrides/memory_cycle_2026-03-20.csv` and cites the TrendForce forecast published before the scoring date.

The DRAM ETF itself was not used because it did not exist at the scoring date and version 0.4.0 evaluates stocks only.

Reproduce from the repository root:

```powershell
wharton backtest --universe config/semiconductor_backtest_universe.csv --start 2026-03-20 --end 2026-09-18 --output-dir backtests/semiconductor_2026-03-20_to_2026-09-18 --reuse-snapshots
```

The cycle-aware redesign was informed by this outcome. It is an in-sample diagnostic and must be frozen before walk-forward validation.
