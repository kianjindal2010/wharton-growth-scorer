# Team Guide for the Wharton Growth Scorer

## Standard weekly workflow

1. Confirm that the security is eligible and tradable in WInS.
2. Verify the exact Yahoo Finance ticker and country code.
3. Review the latest filing and prepare verified overrides when specialist data is absent.
4. Run `wharton predict` or `run_wharton.bat`.
5. Review the verdict, confidence, risk gates, warnings, and Factor Breakdown sheet.
6. Compare the company only with names scored in the same weekly cycle and scorecard.
7. Save the workbook and source filing in the team's shared research folder.

## Interactive example

Activate the installed environment once after opening PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then run:

```text
wharton predict
Yahoo Finance ticker (example 2330.TW): 2330.TW
Country code [US, JP, GB, IN, TW, KR]: TW
As-of date YYYY-MM-DD [today]:
Scorecard [auto/general/technology/healthcare/financial_platform/industrial/consumer/energy_materials/bank/insurer/biotech/semiconductor/memory_semiconductor] [auto]:
Verified override workbook path [press Enter to skip]:
```

## Automated example

```powershell
wharton predict --ticker 2330.TW --country TW --as-of 2026-09-20 --scorecard auto
```

## Supported country codes

| Code | Market | Local benchmark |
|---|---|---|
| US | United States | S&P 500 |
| JP | Japan | Nikkei 225 |
| GB | United Kingdom | FTSE 100 |
| IN | India | Nifty 50 |
| TW | Taiwan | Taiwan Weighted Index |
| KR | South Korea | KOSPI |

## Semiconductor scorecards

Use `semiconductor` for long-term analysis of foundries, chip designers, equipment suppliers, and diversified semiconductor firms. Use `memory_semiconductor` only for DRAM, HBM, and memory manufacturers when a dated, verified memory-pricing override is available. The memory scorecard emphasizes earnings-cycle inflection and is intended for a six-to-twelve-month tactical research horizon.

The included 20 March 2026 memory override is a historical backtest input. Do not reuse it for a current score. For each new scoring date, verify and document the latest industry forecast that was public by that date.

## Sector-aware scorecards

| Team mandate | Typical automatic scorecard | Extra emphasis |
|---|---|---|
| Technology, communications and digital infrastructure | Technology or semiconductor | Gross margin, R&D intensity, scalable cash flow, growth-adjusted valuation |
| Healthcare and life sciences | Healthcare or pre-profit biotech | Innovation spending, cash runway where relevant, margins and balance-sheet resilience |
| Financial services | Bank, insurer, or financial platform | Regulatory strength for banks/insurers; ROE, cash economics and valuation for platforms |
| Industrials, infrastructure and mobility | Industrial | Capital efficiency, asset turnover, capex intensity and inventory-cycle control |
| Consumer, media and education | Consumer | Brand economics, gross margin, inventory turnover, cash conversion and valuation |
| Energy, utilities, materials and climate transition | Energy/materials | Cash returns, leverage, capital discipline, cyclicality and shareholder yield |

Use `auto` unless an analyst has documented why a manual override is more appropriate.

## News sentiment

The news pillar is 5% of every final score. The model analyzes eligible Yahoo Finance headlines and summaries, removes duplicates, excludes future-dated items, rejects articles that do not mention the company or ticker, and weights the rest for relevance, source quality, and recency. Review the stored news records in the Raw Data sheet; sentiment is supporting evidence, not a substitute for reading the underlying articles.

For a historical run, an empty news set is expected when Yahoo Finance no longer exposes that period. The model applies neutral scores and lowers confidence by five percentage points. Never paste current sentiment into a historical override.

## Override workbook rules

Use the columns below exactly. Rows without a verifier or with a publication date after the scoring date are ignored.

| Column | Purpose |
|---|---|
| Metric name | Canonical metric key from `scorecards.yaml` |
| Value | Numeric value expressed as a decimal where appropriate |
| Unit | Percent, ratio, months, or currency |
| Reporting period | Filing period covered by the value |
| Publication date | Date the information became public |
| Source URL | Direct regulatory or company filing link |
| Verified by | Team member who checked the value |

Bank CET1, insurer solvency and reserves, and biotechnology-specific measures normally require overrides. Missing values receive a neutral metric score but reduce confidence; weights are never redistributed.

## Reading the verdict

- **Buy Candidate:** score of 75 or more, sufficient data, and no rejecting risk gate.
- **Watch:** score from 60 to 74.99, sufficient data, and no rejecting risk gate.
- **Reject:** score below 60 or a rejecting risk gate.
- **Insufficient Data:** confidence below 70%, stale prices, or financial statements older than 21 months.

The verdict is a research-screening result, not a forecast of a specific return and not an instruction to trade.

## Reproducing the included backtest

```powershell
wharton backtest --start 2026-03-20 --end 2026-09-18
```

Add `--reuse-snapshots` when the matching frozen snapshots already exist in the selected output folder.
