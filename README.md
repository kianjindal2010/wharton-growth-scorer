# Growth Sleeve Scoring Model

A deterministic, auditable stock-scoring engine for the 50% equity growth sleeve. It scores one analyst-vetted Yahoo Finance ticker at a time and deliberately does **not** determine WInS eligibility, asset allocation, or defensive-sleeve investments.

## Quick start

### One-line PowerShell installation

Paste this entire line into PowerShell. No GitHub account or Git installation is required:

```powershell
irm https://raw.githubusercontent.com/kianjindal2010/wharton-growth-scorer/main/bootstrap.ps1 | iex
```

Then run from any folder:

```powershell
wharton predict
```

To score several companies together and receive one comparison workbook, run:

```powershell
wharton batch
```

Excel reports are stored permanently under `Documents\Wharton Growth Scorer\output\scores\YYYY-MM-DD\`.
The same installer command can be used later to download updates and reinstall the model.

### Manual developer installation

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
wharton predict
```

### One-line macOS installation

Paste this into Terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/kianjindal2010/wharton-growth-scorer/main/bootstrap.sh | bash && export PATH="$HOME/.local/bin:$PATH"
```

Then run `wharton predict`. Detailed macOS instructions are in [INSTALL_MAC.md](INSTALL_MAC.md).

The interactive command asks for the ticker, country, as-of date, and scorecard. `auto` examines Yahoo's sector, sector key, industry, industry key, company description, and financial condition. It selects one of 28 broad or detailed models. The Excel Summary sheet records the classification confidence and exact matching reason. Experienced users can supply everything in one command:

```powershell
wharton predict --ticker 2330.TW --country TW --as-of 2026-09-20 --scorecard auto
```

Add `--snapshot path.json` to reproduce a frozen run without downloading new data. The model is fully automated and accepts no manual metric replacement files.

Each run writes a five-sheet Excel workbook, a JSON result, a frozen input snapshot, and a row in `data/score_history.sqlite3`. Default output is under `output/scores/<as-of>/`.

Every scorecard includes a 5% Yahoo Finance news overlay: 30-day finance-aware headline sentiment (3%), change versus 90-day sentiment (1%), and quality-adjusted coverage (1%). Articles are deduplicated, must mention the company or ticker, and are weighted for relevance, source quality, and recency. Items published after the selected as-of date are excluded. When Yahoo Finance has no eligible historical news, the three metrics remain neutral and the workbook records a warning.

Team installation and operating instructions are in [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) and [TEAM_GUIDE.md](TEAM_GUIDE.md).
The exhaustive input and metric reference is in [VARIABLES.md](VARIABLES.md).

## Exact interactive input format

Run `wharton predict`, then enter:

```text
Yahoo Finance ticker (example 2330.TW): MSFT
Country code [US, JP, GB, IN, TW, KR]: US
As-of date YYYY-MM-DD [today]: 2026-09-20
Scorecard [auto/...]: auto
```

Ticker examples: `MSFT` (US), `7203.T` (Japan), `AZN.L` (UK), `TCS.NS` (India), `2330.TW` (Taiwan), and `000660.KS` (South Korea). Use ISO dates only. For normal companies choose `auto`; manually choose a specialist scorecard only when the analyst can justify it.

The generated Excel file is saved under `Documents/Wharton Growth Scorer/output/scores/YYYY-MM-DD/` and contains Summary, Factor Breakdown, Raw Data, Source Log, and Warnings sheets.

## Batch scoring

Run the guided batch interface from PowerShell, Command Prompt, or macOS Terminal:

```text
wharton batch
One as-of date for the whole batch YYYY-MM-DD [today]: 2026-09-21
Company 1 ticker [blank to run batch]: MSFT
Country code [US / JP / GB / IN / TW / KR]: US
Scorecard [press Enter for automatic selection]:
Company 2 ticker [blank to run batch]: 2330.TW
Country code [US / JP / GB / IN / TW / KR]: TW
Scorecard [press Enter for automatic selection]:
Company 3 ticker [blank to run batch]:
```

For a larger list, copy [examples/batch_input.csv](examples/batch_input.csv), add one company per row, and run:

```powershell
wharton batch --input .\examples\batch_input.csv --as-of 2026-09-21
```

The CSV requires `ticker` and `country`. The `scorecard` column is optional; use `auto` or leave it blank.

Each batch creates:

- `Batch_Summary.xlsx`, containing the consolidated results, within-scorecard ranks, warnings, failures, and clickable links to each detailed report.
- `Batch_Summary.json`, containing the same machine-readable results.
- A `companies` folder containing the normal five-sheet Excel workbook and JSON result for every successfully scored company.
- Frozen snapshots and score-history entries, exactly as with individual runs.

Batch ranks compare only companies that resolved to the same scorecard. A rank is intentionally marked “Not meaningful” when fewer than two companies share that scorecard. One failed ticker does not stop the rest of the batch. Default batch output is stored under `Documents\Wharton Growth Scorer\output\batches\YYYY-MM-DD\batch_TIMESTAMP\`.

## Detailed automatic models

The detailed models are `software_cloud`, `hardware_telecom`, `pharmaceuticals`, `medical_devices`, `payments_fintech`, `asset_management`, `aerospace_defense`, `transportation_logistics`, `automotive`, `capital_goods`, `consumer_staples`, `retail_discretionary`, `media_education`, `oil_gas`, `utilities_renewables`, and `materials_mining`. Banks, insurers, pre-profit biotechnology, general semiconductors, and memory semiconductors retain dedicated specialist models. Broad technology, healthcare, financial-platform, industrial, consumer, energy/materials, and general models remain as fallbacks.

Each detailed model uses its own normalized metric weights. Examples: software emphasizes scalable margins, growth and R&D; logistics emphasizes asset turnover and capex; retail emphasizes inventory efficiency; utilities emphasize debt coverage and capital intensity; mining emphasizes cycle acceleration and incremental returns. All inputs are calculated automatically from Yahoo prices, company profiles, statements, benchmarks, exchange rates, and news.

Run the included multi-market historical comparison with:

```powershell
wharton backtest --start 2026-03-20 --end 2026-09-18
```

Run the all-sector enhanced comparison with:

```powershell
wharton backtest --universe config/enhanced_backtest_universe.csv --start 2026-03-20 --end 2026-09-18
```

The repository includes the [six-month backtest report](reports/Growth_Sleeve_Six_Month_Backtest_Report.docx), [company-level results](backtests/2026-03-20_to_2026-09-18/backtest_results.csv), and frozen scoring snapshots used in that test. Those results describe the earlier broad sector-aware model; version 0.7.0's 28-model architecture requires a fresh out-of-sample evaluation.

Run the dedicated DRAM-manufacturer and TSMC diagnostic with:

```powershell
wharton backtest --universe config/semiconductor_backtest_universe.csv --start 2026-03-20 --end 2026-09-18
```

Memory manufacturers are automatically identified from DRAM, HBM, NAND, flash, and memory-chip language. Their model measures revenue acceleration, gross-margin inflection, inventory normalization, cash generation, valuation, financial strength, R&D, risk, and momentum. TSMC and other foundries use the broader `semiconductor` model.

## Important limitations

- Yahoo Finance is a convenience data source, not a regulatory filing system. The fully automated bank and insurer models use statement-based balance-sheet resilience rather than unavailable regulatory ratios.
- Yahoo Finance normally exposes a recent news window, not a complete historical archive. Historical scores must never substitute present-day headlines for missing point-in-time news.
- The model is a research consistency tool, not a prediction of returns or a substitute for investment judgment.
- The memory scorecard is a tactical six-to-twelve-month cyclical screen. Its first reported improvement is in-sample and requires walk-forward validation before portfolio use.
- Version one contains no machine learning, LLM sentiment, Monte Carlo funding model, eligibility screening, or automated position sizing.
