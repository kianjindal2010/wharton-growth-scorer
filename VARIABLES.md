# Complete Variable Dictionary

This document lists every input and calculated variable used by Growth Scorer v0.4.0. Not every variable applies to every company: the selected scorecard determines which factors receive weight. Missing scored variables receive a neutral factor score of 50 and reduce data confidence; weights are never redistributed.

## Run identification and classification

| Variable | Meaning |
|---|---|
| `ticker` | Exact Yahoo Finance symbol, including exchange suffix where required |
| `country` | Market code: `US`, `JP`, `GB`, `IN`, `TW`, or `KR` |
| `as_of` | Information cutoff date in `YYYY-MM-DD` format |
| `scorecard` | `auto` or a manually selected scorecard |
| `company_name` | Company name returned by Yahoo Finance |
| `sector` | Yahoo Finance sector used in automatic classification |
| `industry` | Yahoo Finance industry used in automatic classification |
| `currency` | Security's local trading/reporting currency |
| `retrieved_at` | Timestamp when the snapshot was downloaded |
| `last_price_date` | Latest eligible market-price date |
| `latest_financial_date` | Latest eligible statement period |

## Raw market variables

| Variable | Meaning |
|---|---|
| `open`, `high`, `low`, `close` | Daily local-market OHLC prices |
| `adj_close` | Split- and distribution-adjusted closing price |
| `volume` | Daily trading volume |
| `dividends` | Recorded cash distributions |
| `stock_splits` | Recorded split events |
| `benchmark_prices` | Adjusted prices for the local market index |
| `fx_rates` | Daily local-currency/US-dollar conversion series |

Benchmarks are S&P 500 (`^GSPC`), Nikkei 225 (`^N225`), FTSE 100 (`^FTSE`), Nifty 50 (`^NSEI`), Taiwan Weighted (`^TWII`), and KOSPI (`^KS11`).

## Market-risk and momentum variables

| Metric key | Meaning |
|---|---|
| `usd_volatility` | Annualized standard deviation of daily USD returns, using up to three years |
| `max_drawdown` | Worst peak-to-trough decline in the USD price series |
| `downside_beta` | Beta to the local benchmark on benchmark down-days |
| `relative_return_12m` | Twelve-month local stock return minus local benchmark return |
| `relative_return_6m` | Six-month local stock return minus local benchmark return |
| `relative_return_3m` | Three-month local stock return minus local benchmark return |
| `relative_momentum_12_1` | Stock return from month 12 to month 1 minus the equivalent benchmark return |

## Raw financial-statement variables

| Group | Variables |
|---|---|
| Income statement | Revenue, gross profit, cost of revenue, operating income, EBIT, EBITDA, net income, pretax income, tax provision, diluted/basic EPS, R&D, operating expense, interest expense, investment income, premium revenue |
| Balance sheet | Cash and short-term investments, total debt, shareholders' equity, total assets, current assets, current liabilities, inventory, shares outstanding, tangible book value |
| Cash flow | Operating cash flow, capital expenditure, reported/calculated free cash flow, dividends paid, share repurchases, share issuance |

Annual and quarterly statement tables are retained in the frozen snapshot and Excel Raw Data sheet.

## Calculated fundamental variables

| Metric key | Calculation or interpretation |
|---|---|
| `book_equity` | Latest shareholders' equity |
| `operating_income` | Latest operating income; also used to identify pre-profit biotechnology |
| `free_cash_flow` | Reported FCF or operating cash flow less capital expenditure |
| `roic` | Tax-adjusted EBIT divided by equity plus debt less cash |
| `roe` | Net income divided by equity |
| `roa` | Net income divided by total assets |
| `gross_margin` | Gross profit divided by revenue |
| `operating_margin` | Operating income divided by revenue |
| `fcf_margin` | Free cash flow divided by revenue |
| `cash_conversion` | Operating cash flow divided by positive net income |
| `operating_margin_stability` | Standard deviation of historical operating margins |
| `revenue_cagr_3y` | Approximately three-year revenue compound annual growth |
| `eps_cagr_3y` | Approximately three-year EPS compound annual growth |
| `fcf_cagr_3y` | Approximately three-year FCF compound annual growth |
| `latest_revenue_growth` | Latest annual revenue change |
| `revenue_acceleration` | Latest annual revenue-growth rate minus the preceding rate |
| `gross_margin_trend` | Latest gross margin minus prior-period gross margin |
| `inventory_days_change` | Latest inventory days minus prior-period inventory days |
| `asset_turnover` | Revenue divided by total assets |
| `inventory_turnover` | Cost of revenue divided by inventory |
| `capex_to_sales` | Absolute capital expenditure divided by revenue |
| `revenue_growth_to_capex` | Latest revenue growth divided by capex intensity |
| `incremental_roic` | Change in tax-adjusted EBIT divided by change in invested capital |
| `fcf_yield` | Free cash flow divided by market capitalization |
| `ebit_ev` | EBIT divided by enterprise value |
| `earnings_yield` | Net income divided by market capitalization |
| `shareholder_yield` | Dividends plus repurchases less issuance, divided by market capitalization |
| `price_to_sales` | Market capitalization divided by revenue |
| `price_to_book` | Market capitalization divided by book equity |
| `price_to_tangible_book` | Market capitalization divided by tangible book value |
| `dividend_yield` | Dividends divided by market capitalization |
| `net_debt_ebitda` | Debt less cash divided by EBITDA |
| `interest_coverage` | EBIT divided by absolute interest expense |
| `current_ratio` | Current assets divided by current liabilities |
| `cash_to_debt` | Cash divided by debt |
| `debt_to_equity` | Debt divided by equity |
| `inventory_to_current_assets` | Inventory divided by current assets |
| `tangible_book_cagr_3y` | Approximately three-year tangible-book growth |
| `book_value_cagr_3y` | Approximately three-year equity/book-value growth |
| `premium_growth` | Insurer premium growth |
| `investment_income_stability` | Variability of insurer investment income relative to its average magnitude |
| `rd_to_revenue` | R&D expense divided by revenue |
| `rd_to_opex` | R&D expense divided by operating expense |
| `rd_growth` | Latest annual R&D growth |
| `cash_runway_months` | Cash divided by annual FCF burn, converted to months |
| `share_count_cagr` | Compound annual growth in shares outstanding; measures dilution |
| `cash_burn_to_market_cap` | Annual cash burn divided by market capitalization |
| `debt_to_cash` | Debt divided by cash |
| `ev_to_rd` | Enterprise value divided by R&D expense |

## Verified specialist variables

These are normally entered through a dated analyst override file because Yahoo Finance does not provide them consistently.

| Scorecard | Metric keys |
|---|---|
| Bank | `efficiency_ratio`, `cet1_buffer`, `npl_ratio`, `loan_loss_coverage`, `loan_to_deposit` |
| Insurer | `combined_ratio`, `solvency_buffer`, `reserve_coverage` |
| Pre-profit biotechnology | Cash runway, share dilution, R&D commitment, debt/cash and EV/R&D variables above |
| Memory semiconductor | `memory_contract_price_growth`—a verified, dated DRAM pricing-cycle input |

The override record also stores `unit`, `reporting_period`, `publication_date`, `source_url`, and `verified_by`. Future-dated and unverified rows are rejected.

## Industry-detection variables

Automatic scorecard selection now evaluates all available Yahoo profile fields below before using a broad sector fallback:

| Variable | Use |
|---|---|
| `sector` | Human-readable broad sector |
| `sector_key` | Normalized Yahoo sector identifier |
| `industry` | Human-readable detailed industry |
| `industry_key` | Normalized Yahoo industry identifier |
| `business_summary` | Company-description evidence used when the detailed industry is ambiguous |
| `quote_type` | Security-type audit field |
| `exchange` | Listing-venue audit field |

The result records `classification_confidence` and `classification_reason`. Exact industry matches take precedence over company-description matches, which take precedence over broad sector fallbacks.

## News variables

| Metric key | Meaning |
|---|---|
| `news_sentiment_30d` | Weighted sentiment of eligible articles published during the last 30 days, from -1 to +1 |
| `news_sentiment_trend` | Thirty-day sentiment minus weighted 90-day sentiment |
| `news_quality_coverage` | Quality/relevance/recency-adjusted article coverage, capped at 1 |
| `news_count_30d` | Number of eligible unique articles in 30 days |
| `news_count_90d` | Number of eligible unique articles in 90 days |

Each stored article includes title, summary, publication timestamp, provider, URL, article sentiment, company relevance, source quality, recency weight, and combined weight. Articles must mention the company or ticker. Future items and duplicates are excluded. The news pillar is 5% of every score: 30-day sentiment 3%, sentiment trend 1%, and quality coverage 1%.

## Scorecards and their major emphases

| Scorecard | Principal variables |
|---|---|
| `general` | Quality, growth, valuation, financial strength, market risk, momentum |
| `technology` | Gross margin, scalable FCF, R&D intensity, growth, valuation |
| `healthcare` | Product economics, innovation spending, profitable growth, resilience |
| `financial_platform` | ROE/ROA, cash economics, growth, valuation, balance sheet |
| `industrial` | ROIC, cash conversion, asset turnover, capex and inventory cycle |
| `consumer` | Brand economics, margins, inventory turnover, cash conversion |
| `energy_materials` | Cash returns, leverage, capital discipline and cyclicality |
| `bank` | Profitability, growth, valuation, capital and asset quality |
| `insurer` | Profitability, growth, valuation, solvency and reserve coverage |
| `biotech` | Cash runway, dilution, R&D commitment, funding and valuation |
| `semiconductor` | Quality, cycle, valuation, balance sheet, innovation and momentum |
| `memory_semiconductor` | Earnings inflection, DRAM pricing cycle, inventory, margins and momentum |

Every core scorecard contributes 95% of the final score; the common news layer contributes the remaining 5%.

## Freshness, confidence and risk-gate variables

| Check | Rule |
|---|---|
| Data confidence | Sum of weights for observed metrics; below 70% produces `Insufficient Data` |
| Price freshness | More than five trading days stale produces `Insufficient Data` |
| Statement freshness | Statements older than 21 months produce `Insufficient Data` |
| Operating-company gate | Negative book equity, or net debt/EBITDA above 6x with interest coverage below 1x, produces `Reject` |
| Bank gate | Regulatory capital below the applicable minimum produces `Reject` |
| Insurer gate | Solvency below the applicable minimum produces `Reject` |
| Biotechnology gate | Cash runway below 12 months produces `Reject` |

## Output variables

The final result records overall score, verdict, confidence, scorecard, comparable-company rank, risk gates, warnings, pillar scores, every raw metric, transformed 0–100 factor score, factor weight, contribution, source, and bad/neutral/excellent anchors.
