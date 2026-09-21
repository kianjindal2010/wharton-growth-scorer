# Team Guide for the Wharton Growth Scorer

## Standard weekly workflow

1. Confirm that the security is eligible and tradable in WInS.
2. Verify the exact Yahoo Finance ticker and country code.
3. Review the latest filing as a human research check; the scoring program itself remains fully automated.
4. Open the **Wharton Growth Scorer** shortcut and use Single company or Batch comparison. The CLI remains available for advanced use.
5. Review the verdict, confidence, risk gates, warnings, and Factor Breakdown sheet.
6. Compare the company only with names scored in the same weekly cycle and scorecard.
7. Save the workbook and source filing in the team's shared research folder.

## Interactive example

The recommended workflow requires no terminal: open the installed application, enter the ticker, country, and date, then select **Run analysis**. Open the Excel report directly from the result screen.

For advanced command-line use, activate the installed environment once after opening PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then run:

```text
wharton predict
Yahoo Finance ticker (example 2330.TW): 2330.TW
Country code [US, JP, GB, IN, TW, KR]: TW
As-of date YYYY-MM-DD [today]:
Scorecard [press Enter for fully automatic detailed selection]:
```

## Automated example

```powershell
wharton predict --ticker 2330.TW --country TW --as-of 2026-09-20 --scorecard auto
```

## Batch workflow

Use one shared as-of date for all companies in a weekly comparison. For a guided run:

```powershell
wharton batch
```

Keep adding tickers when prompted, then press Enter at the next blank ticker prompt. The model processes every company, creates the same detailed five-sheet workbook for each one, and adds a consolidated `Batch_Summary.xlsx` workbook.

For a prepared team list, use a CSV with this format:

```csv
ticker,country,scorecard
MSFT,US,auto
2330.TW,TW,auto
7203.T,JP,auto
```

Then run:

```powershell
wharton batch --input .\examples\batch_input.csv --as-of 2026-09-21
```

The `scorecard` field may be blank. The batch continues when one company fails and records the reason on the Failures sheet. Review ranks only within the same resolved scorecard; cross-scorecard ranks are not valid.

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

The automatic detector uses Yahoo's detailed industry key and company description. It selects `semiconductor` for foundries, chip designers, equipment suppliers, and diversified semiconductor firms. It selects `memory_semiconductor` for DRAM, HBM, NAND, flash, or memory-chip operations. The memory model is fully automated and measures reported cycle inflection, inventory, margins, cash flow, valuation, R&D, risk, and momentum.

## Sector-aware scorecards

| Team mandate | Typical automatic scorecard | Extra emphasis |
|---|---|---|
| Technology, communications and digital infrastructure | Software/cloud, hardware/telecom, semiconductor, memory semiconductor | Scalable margins, R&D, cash flow, chip cycle and valuation |
| Healthcare and life sciences | Pharmaceuticals, medical devices, healthcare, pre-profit biotech | Innovation, margins, cash runway, growth and resilience |
| Financial services | Bank, insurer, payments/fintech, asset management | Automated profitability, growth, valuation and balance-sheet resilience |
| Industrials, infrastructure and mobility | Aerospace/defense, transportation/logistics, automotive, capital goods | Capital efficiency, turnover, capex, leverage and inventory cycle |
| Consumer, media and education | Staples, retail/discretionary, media/education | Margin durability, inventory productivity, growth and cash conversion |
| Energy, utilities, materials and climate transition | Oil/gas, utilities/renewables, materials/mining | Cash returns, leverage, capital intensity and cycle discipline |

Use `auto` unless an analyst has documented why a manual scorecard is more appropriate. Review the classification reason in the Summary sheet.

## News sentiment

The news pillar is 5% of every final score. The model analyzes eligible Yahoo Finance headlines and summaries, removes duplicates, excludes future-dated items, rejects articles that do not mention the company or ticker, and weights the rest for relevance, source quality, and recency. Review the stored news records in the Raw Data sheet; sentiment is supporting evidence, not a substitute for reading the underlying articles.

For a historical run, an empty news set is expected when Yahoo Finance no longer exposes that period. The model applies neutral scores and lowers confidence by five percentage points.

## Fully automated data policy

The command accepts no manual metric replacement files. Bank and insurer models use automatically calculated ROE, ROA, net margin, book-value growth, asset growth, earnings yield, price-to-book measures, dividend yield, equity/assets, leverage, market risk and momentum. The memory model uses reported revenue, margin, inventory, cash-flow and price-cycle evidence. Missing values remain neutral and reduce data confidence; weights are never silently redistributed.

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
