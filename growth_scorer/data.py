from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yfinance as yf

from .config import COUNTRIES
from .models import InputSnapshot, SourceRecord
from .news import fetch_news_metrics
from .transforms import safe_div, signed_cagr


ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": ("Total Revenue", "Operating Revenue"),
    "gross_profit": ("Gross Profit",),
    "cost_of_revenue": ("Cost Of Revenue", "Reconciled Cost Of Revenue"),
    "operating_income": ("Operating Income",),
    "ebit": ("EBIT", "Operating Income"),
    "ebitda": ("EBITDA", "Normalized EBITDA"),
    "net_income": ("Net Income", "Net Income Common Stockholders"),
    "pretax_income": ("Pretax Income",),
    "tax_provision": ("Tax Provision",),
    "diluted_eps": ("Diluted EPS", "Basic EPS"),
    "rd": ("Research And Development",),
    "operating_expense": ("Operating Expense", "Total Expenses"),
    "interest_expense": ("Interest Expense", "Interest Expense Non Operating"),
    "investment_income": ("Investment Income", "Net Investment Income"),
    "premium_revenue": ("Premiums Earned", "Net Premiums Written"),
    "cash": (
        "Cash Cash Equivalents And Short Term Investments",
        "Cash And Cash Equivalents",
        "Cash Financial",
    ),
    "debt": ("Total Debt", "Long Term Debt And Capital Lease Obligation"),
    "equity": ("Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"),
    "assets": ("Total Assets",),
    "current_assets": ("Current Assets", "Total Current Assets"),
    "current_liabilities": ("Current Liabilities", "Total Current Liabilities"),
    "inventory": ("Inventory",),
    "shares": ("Ordinary Shares Number", "Share Issued", "Diluted Average Shares"),
    "tangible_book": ("Tangible Book Value",),
    "ocf": ("Operating Cash Flow", "Total Cash From Operating Activities"),
    "capex": ("Capital Expenditure", "Capital Expenditures"),
    "free_cash_flow": ("Free Cash Flow",),
    "dividends": ("Cash Dividends Paid", "Common Stock Dividend Paid"),
    "repurchases": ("Repurchase Of Capital Stock", "Repurchase Of Stock"),
    "issuance": ("Issuance Of Capital Stock", "Issuance Of Stock"),
}


def _finite(value: Any) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


def _clean_frame(frame: pd.DataFrame | None, as_of: date) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    result = frame.copy()
    valid_columns = []
    for column in result.columns:
        parsed = pd.Timestamp(column)
        if parsed.date() <= as_of:
            valid_columns.append(column)
    result = result.loc[:, valid_columns]
    return result.sort_index(axis=1)


def _row(frame: pd.DataFrame, key: str) -> list[tuple[date, float]]:
    if frame.empty:
        return []
    for label in ALIASES[key]:
        if label in frame.index:
            values: list[tuple[date, float]] = []
            for column, value in frame.loc[label].items():
                numeric = _finite(value)
                if numeric is not None:
                    values.append((pd.Timestamp(column).date(), numeric))
            return sorted(values)
    return []


def _latest(frame: pd.DataFrame, key: str) -> float | None:
    values = _row(frame, key)
    return values[-1][1] if values else None


def _growth(values: list[tuple[date, float]], target_years: int = 3) -> float | None:
    if len(values) < 2:
        return None
    last_date, last = values[-1]
    candidates = [
        (d, v)
        for d, v in values[:-1]
        if (last_date - d).days / 365.25 >= max(0.75, target_years - 0.5)
    ]
    if not candidates:
        return None
    first_date, first = min(
        candidates,
        key=lambda item: abs((last_date - item[0]).days / 365.25 - target_years),
    )
    years = (last_date - first_date).days / 365.25
    return signed_cagr(first, last, years)


def _frame_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for column in frame.columns:
        record: dict[str, Any] = {"period": pd.Timestamp(column).date().isoformat()}
        for index, value in frame[column].items():
            numeric = _finite(value)
            record[str(index)] = numeric
        records.append(record)
    return records


def _price_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if frame.empty:
        return records
    for index, row in frame.iterrows():
        record: dict[str, Any] = {"date": pd.Timestamp(index).date().isoformat()}
        for column, value in row.items():
            if isinstance(column, tuple):
                column = column[0]
            record[str(column)] = _finite(value)
        records.append(record)
    return records


def _download(symbol: str, start: date, end: date, actions: bool = False) -> pd.DataFrame:
    frame = yf.download(
        symbol,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        auto_adjust=False,
        actions=actions,
        progress=False,
        threads=False,
    )
    if isinstance(frame.columns, pd.MultiIndex):
        if symbol in frame.columns.get_level_values(-1):
            frame = frame.xs(symbol, axis=1, level=-1)
        else:
            frame.columns = frame.columns.get_level_values(0)
    frame.index = pd.to_datetime(frame.index).tz_localize(None)
    return frame.loc[frame.index.date <= end]


def _adjusted_close(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=float)
    column = "Adj Close" if "Adj Close" in frame.columns else "Close"
    return pd.to_numeric(frame[column], errors="coerce").dropna().sort_index()


def _fx_aligned(index: pd.Index, fx: pd.Series, mode: str) -> pd.Series:
    if mode == "none":
        return pd.Series(1.0, index=index)
    aligned = fx.reindex(index).ffill().bfill()
    if aligned.isna().all():
        return aligned
    return aligned


def _to_usd(local: pd.Series, fx: pd.Series, mode: str) -> pd.Series:
    rates = _fx_aligned(local.index, fx, mode)
    if mode == "divide":
        return local / rates
    if mode == "multiply":
        return local * rates
    return local


def _period_return(series: pd.Series, days: int) -> float | None:
    if len(series) < 2:
        return None
    cutoff = series.index[-1] - pd.Timedelta(days=days)
    earlier = series.loc[series.index <= cutoff]
    if earlier.empty or earlier.iloc[-1] == 0:
        return None
    return float(series.iloc[-1] / earlier.iloc[-1] - 1)


def _return_between(series: pd.Series, start_days: int, end_days: int) -> float | None:
    if len(series) < 2 or start_days <= end_days:
        return None
    last_date = series.index[-1]
    start_values = series.loc[series.index <= last_date - pd.Timedelta(days=start_days)]
    end_values = series.loc[series.index <= last_date - pd.Timedelta(days=end_days)]
    if start_values.empty or end_values.empty or start_values.iloc[-1] == 0:
        return None
    return float(end_values.iloc[-1] / start_values.iloc[-1] - 1)


def _market_metrics(
    prices: pd.DataFrame,
    benchmark: pd.DataFrame,
    fx_frame: pd.DataFrame,
    fx_mode: str,
) -> dict[str, float | None]:
    local = _adjusted_close(prices)
    local_benchmark = _adjusted_close(benchmark)
    fx = _adjusted_close(fx_frame) if not fx_frame.empty else pd.Series(1.0, index=local.index)
    usd = _to_usd(local, fx, fx_mode).dropna()
    usd_benchmark = _to_usd(local_benchmark, fx, fx_mode).dropna()

    risk_window = usd.tail(756)
    daily = risk_window.pct_change().dropna()
    volatility = float(daily.std(ddof=1) * np.sqrt(252)) if len(daily) >= 60 else None
    drawdown = None
    if len(risk_window) >= 60:
        drawdown = float((risk_window / risk_window.cummax() - 1).min())

    joined = pd.concat([usd.pct_change().rename("stock"), usd_benchmark.pct_change().rename("market")], axis=1).dropna()
    joined = joined.tail(756)
    downside = joined.loc[joined["market"] < 0]
    downside_beta = None
    if len(downside) >= 20 and downside["market"].var() > 0:
        downside_beta = float(downside.cov().loc["stock", "market"] / downside["market"].var())

    stock_12m = _period_return(local, 365)
    market_12m = _period_return(local_benchmark, 365)
    stock_6m = _period_return(local, 183)
    market_6m = _period_return(local_benchmark, 183)
    stock_3m = _period_return(local, 92)
    market_3m = _period_return(local_benchmark, 92)
    stock_12_1 = _return_between(local, 365, 30)
    market_12_1 = _return_between(local_benchmark, 365, 30)
    return {
        "usd_volatility": volatility,
        "max_drawdown": drawdown,
        "downside_beta": downside_beta,
        "relative_return_12m": None if stock_12m is None or market_12m is None else stock_12m - market_12m,
        "relative_return_6m": None if stock_6m is None or market_6m is None else stock_6m - market_6m,
        "relative_return_3m": None if stock_3m is None or market_3m is None else stock_3m - market_3m,
        "relative_momentum_12_1": None
        if stock_12_1 is None or market_12_1 is None
        else stock_12_1 - market_12_1,
    }


def _statement_metrics(
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cashflow: pd.DataFrame,
    last_price_local: float | None,
    metadata_currency: str | None,
) -> dict[str, float | None]:
    revenue = _latest(income, "revenue")
    gross_profit = _latest(income, "gross_profit")
    cost_of_revenue = _latest(income, "cost_of_revenue")
    operating_income = _latest(income, "operating_income")
    ebit = _latest(income, "ebit")
    ebitda = _latest(income, "ebitda")
    net_income = _latest(income, "net_income")
    pretax = _latest(income, "pretax_income")
    tax = _latest(income, "tax_provision")
    cash = _latest(balance, "cash")
    debt = _latest(balance, "debt") or 0.0
    equity = _latest(balance, "equity")
    assets = _latest(balance, "assets")
    current_assets = _latest(balance, "current_assets")
    current_liabilities = _latest(balance, "current_liabilities")
    inventory = _latest(balance, "inventory")
    shares = _latest(balance, "shares")
    ocf = _latest(cashflow, "ocf")
    capex = _latest(cashflow, "capex")
    reported_fcf = _latest(cashflow, "free_cash_flow")
    if reported_fcf is not None:
        fcf = reported_fcf
    elif ocf is not None and capex is not None:
        fcf = ocf + capex if capex < 0 else ocf - capex
    else:
        fcf = None

    price = last_price_local
    if price is not None and metadata_currency and metadata_currency.upper() in {"GBX", "GBPENCE", "GBP"}:
        # Yahoo's .L prices are commonly in pence while statements are in pounds.
        if metadata_currency.upper() in {"GBX", "GBPENCE"}:
            price /= 100.0
    market_cap = price * shares if price is not None and shares is not None else None
    enterprise_value = None if market_cap is None or cash is None else market_cap + debt - cash
    tax_rate = safe_div(tax, pretax)
    if tax_rate is not None:
        tax_rate = min(max(tax_rate, 0.0), 0.35)
    nopat = None if ebit is None else ebit * (1 - (tax_rate if tax_rate is not None else 0.21))
    invested_capital = None if equity is None or cash is None else equity + debt - cash

    operating_margins = []
    op_by_date = dict(_row(income, "operating_income"))
    for period, rev in _row(income, "revenue"):
        if rev != 0 and period in op_by_date:
            operating_margins.append(op_by_date[period] / rev)
    margin_stability = float(np.std(operating_margins, ddof=0)) if len(operating_margins) >= 3 else None

    gross_margin_values: list[tuple[date, float]] = []
    gross_by_date = dict(_row(income, "gross_profit"))
    revenue_by_date = dict(_row(income, "revenue"))
    for period in sorted(set(gross_by_date) & set(revenue_by_date)):
        if revenue_by_date[period] != 0:
            gross_margin_values.append((period, gross_by_date[period] / revenue_by_date[period]))
    gross_margin = gross_margin_values[-1][1] if gross_margin_values else safe_div(gross_profit, revenue)
    gross_margin_trend = (
        gross_margin_values[-1][1] - gross_margin_values[-2][1]
        if len(gross_margin_values) >= 2
        else None
    )

    revenue_values = _row(income, "revenue")
    annual_revenue_growth: list[float] = []
    for (_, prior), (_, latest) in zip(revenue_values, revenue_values[1:]):
        if prior != 0:
            annual_revenue_growth.append(latest / prior - 1)
    revenue_acceleration = (
        annual_revenue_growth[-1] - annual_revenue_growth[-2]
        if len(annual_revenue_growth) >= 2
        else None
    )

    inventory_by_date = dict(_row(balance, "inventory"))
    cost_by_date = dict(_row(income, "cost_of_revenue"))
    inventory_days_values: list[tuple[date, float]] = []
    for period in sorted(set(inventory_by_date) & set(cost_by_date)):
        if cost_by_date[period] != 0:
            inventory_days_values.append((period, inventory_by_date[period] / abs(cost_by_date[period]) * 365))
    inventory_days_change = (
        inventory_days_values[-1][1] - inventory_days_values[-2][1]
        if len(inventory_days_values) >= 2
        else None
    )

    dividends = _latest(cashflow, "dividends")
    repurchases = _latest(cashflow, "repurchases")
    issuance = _latest(cashflow, "issuance")
    distributions = abs(dividends or 0.0) + abs(repurchases or 0.0) - abs(issuance or 0.0)
    rd = _latest(income, "rd")
    opex = _latest(income, "operating_expense")
    interest = _latest(income, "interest_expense")
    burn = max(-(fcf or 0.0), 0.0) if fcf is not None else None
    capex_intensity = safe_div(abs(capex), revenue) if capex is not None else None

    tangible_values = _row(balance, "tangible_book")
    if not tangible_values and equity is not None:
        tangible_values = _row(balance, "equity")

    metrics: dict[str, float | None] = {
        "operating_income": operating_income,
        "free_cash_flow": fcf,
        "book_equity": equity,
        "roic": safe_div(nopat, invested_capital),
        "gross_margin": gross_margin,
        "operating_margin": safe_div(operating_income, revenue),
        "fcf_margin": safe_div(fcf, revenue),
        "cash_conversion": safe_div(ocf, net_income) if net_income is not None and net_income > 0 else None,
        "operating_margin_stability": margin_stability,
        "revenue_cagr_3y": _growth(_row(income, "revenue")),
        "eps_cagr_3y": _growth(_row(income, "diluted_eps")),
        "fcf_cagr_3y": _growth(_row(cashflow, "free_cash_flow")),
        "latest_revenue_growth": None,
        "revenue_acceleration": revenue_acceleration,
        "gross_margin_trend": gross_margin_trend,
        "inventory_days_change": inventory_days_change,
        "fcf_yield": safe_div(fcf, market_cap),
        "ebit_ev": safe_div(ebit, enterprise_value),
        "earnings_yield": safe_div(net_income, market_cap),
        "shareholder_yield": safe_div(distributions, market_cap),
        "price_to_sales": safe_div(market_cap, revenue),
        "net_debt_ebitda": safe_div(debt - (cash or 0.0), ebitda),
        "interest_coverage": safe_div(ebit, abs(interest)) if interest not in (None, 0) else None,
        "current_ratio": safe_div(current_assets, current_liabilities),
        "cash_to_debt": safe_div(cash, debt) if debt != 0 else (10.0 if cash is not None and cash > 0 else None),
        "inventory_to_current_assets": safe_div(inventory, current_assets),
        "asset_turnover": safe_div(revenue, assets),
        "inventory_turnover": safe_div(abs(cost_of_revenue), inventory) if cost_of_revenue is not None else None,
        "capex_to_sales": capex_intensity,
        "roe": safe_div(net_income, equity),
        "roa": safe_div(net_income, assets),
        "tangible_book_cagr_3y": _growth(tangible_values),
        "book_value_cagr_3y": _growth(_row(balance, "equity")),
        "price_to_tangible_book": safe_div(market_cap, tangible_values[-1][1]) if tangible_values else None,
        "price_to_book": safe_div(market_cap, equity),
        "dividend_yield": safe_div(abs(dividends), market_cap) if dividends is not None else None,
        "debt_to_equity": safe_div(debt, equity),
        "premium_growth": _growth(_row(income, "premium_revenue"), 1),
        "investment_income_stability": None,
        "cash_runway_months": (safe_div(cash, burn) * 12) if burn not in (None, 0) else (120.0 if cash is not None else None),
        "share_count_cagr": _growth(_row(balance, "shares")),
        "cash_burn_to_market_cap": safe_div(burn, market_cap),
        "rd_to_opex": safe_div(rd, abs(opex)) if opex is not None else None,
        "rd_to_revenue": safe_div(rd, revenue),
        "revenue_growth_to_capex": None,
        "incremental_roic": None,
        "rd_growth": _growth(_row(income, "rd"), 1),
        "debt_to_cash": safe_div(debt, cash),
        "ev_to_rd": safe_div(enterprise_value, rd),
    }
    revenues = _row(income, "revenue")
    if len(revenues) >= 2 and revenues[-2][1] != 0:
        metrics["latest_revenue_growth"] = revenues[-1][1] / revenues[-2][1] - 1
        if capex_intensity not in (None, 0):
            metrics["revenue_growth_to_capex"] = metrics["latest_revenue_growth"] / capex_intensity

    equity_by_date = dict(_row(balance, "equity"))
    debt_by_date = dict(_row(balance, "debt"))
    cash_by_date = dict(_row(balance, "cash"))
    ebit_by_date = dict(_row(income, "ebit"))
    capital_returns: list[tuple[date, float, float]] = []
    for period in sorted(set(equity_by_date) & set(ebit_by_date)):
        capital = equity_by_date[period] + debt_by_date.get(period, 0.0) - cash_by_date.get(period, 0.0)
        if capital != 0:
            capital_returns.append((period, ebit_by_date[period] * (1 - (tax_rate or 0.21)), capital))
    if len(capital_returns) >= 2:
        _, prior_nopat, prior_capital = capital_returns[-2]
        _, latest_nopat, latest_capital = capital_returns[-1]
        metrics["incremental_roic"] = safe_div(latest_nopat - prior_nopat, latest_capital - prior_capital)

    investment_values = [v for _, v in _row(income, "investment_income")]
    if len(investment_values) >= 3 and np.mean(np.abs(investment_values)) > 0:
        metrics["investment_income_stability"] = float(
            np.std(investment_values, ddof=0) / np.mean(np.abs(investment_values))
        )
    return metrics


def _get_info(ticker: yf.Ticker) -> dict[str, Any]:
    try:
        return ticker.get_info() or {}
    except Exception:
        return {}


def build_snapshot(ticker_symbol: str, country: str, as_of: date) -> InputSnapshot:
    country = country.upper()
    if country not in COUNTRIES:
        raise ValueError(f"Unsupported country {country}; choose from {', '.join(COUNTRIES)}")
    config = COUNTRIES[country]
    start = as_of - timedelta(days=365 * 6 + 10)
    retrieved = datetime.now().astimezone()
    ticker = yf.Ticker(ticker_symbol)
    info = _get_info(ticker)

    prices = _download(ticker_symbol, start, as_of, actions=True)
    benchmark = _download(str(config["benchmark"]), start, as_of)
    fx_symbol = config["fx"]
    fx_frame = _download(str(fx_symbol), start, as_of) if fx_symbol else pd.DataFrame()
    if prices.empty:
        raise RuntimeError(f"No Yahoo Finance prices returned for {ticker_symbol} through {as_of}")

    try:
        income = _clean_frame(ticker.financials, as_of)
        balance = _clean_frame(ticker.balance_sheet, as_of)
        cashflow = _clean_frame(ticker.cashflow, as_of)
        quarterly_income = _clean_frame(ticker.quarterly_financials, as_of)
        quarterly_balance = _clean_frame(ticker.quarterly_balance_sheet, as_of)
        quarterly_cashflow = _clean_frame(ticker.quarterly_cashflow, as_of)
    except Exception as exc:
        income = balance = cashflow = pd.DataFrame()
        quarterly_income = quarterly_balance = quarterly_cashflow = pd.DataFrame()
        statement_warning = f"Yahoo statement retrieval failed: {exc}"
    else:
        statement_warning = None

    local_close = _adjusted_close(prices)
    last_price = float(local_close.iloc[-1]) if not local_close.empty else None
    metrics = _statement_metrics(income, balance, cashflow, last_price, info.get("currency"))
    metrics.update(_market_metrics(prices, benchmark, fx_frame, str(config["fx_mode"])))
    news_metrics, news_items, news_warnings = fetch_news_metrics(
        ticker, as_of, ticker_symbol, info.get("longName") or info.get("shortName")
    )
    metrics.update(news_metrics)

    statement_dates: list[date] = []
    for frame in (income, balance, cashflow, quarterly_income, quarterly_balance, quarterly_cashflow):
        statement_dates.extend(pd.Timestamp(column).date() for column in frame.columns)
    latest_financial_date = max(statement_dates) if statement_dates else None
    warnings = [
        "Yahoo statement periods are filtered by period end; filing publication dates are unavailable and should be verified for historical backtests."
    ]
    if statement_warning:
        warnings.append(statement_warning)
    if benchmark.empty:
        warnings.append(f"No benchmark prices returned for {config['benchmark']}")
    if fx_symbol and fx_frame.empty:
        warnings.append(f"No FX prices returned for {fx_symbol}; USD risk metrics may be missing")
    warnings.extend(news_warnings)

    statements = {
        "annual_income": _frame_records(income),
        "annual_balance": _frame_records(balance),
        "annual_cashflow": _frame_records(cashflow),
        "quarterly_income": _frame_records(quarterly_income),
        "quarterly_balance": _frame_records(quarterly_balance),
        "quarterly_cashflow": _frame_records(quarterly_cashflow),
    }
    source_url = f"https://finance.yahoo.com/quote/{ticker_symbol}"
    source_log = [
        SourceRecord(source="Yahoo Finance prices and corporate actions", retrieval_time=retrieved, reporting_period=f"through {as_of}", url=source_url),
        SourceRecord(source="Yahoo Finance financial statements", retrieval_time=retrieved, reporting_period=str(latest_financial_date) if latest_financial_date else None, url=source_url),
        SourceRecord(source=f"Yahoo Finance benchmark {config['benchmark']}", retrieval_time=retrieved, reporting_period=f"through {as_of}"),
    ]
    if fx_symbol:
        source_log.append(SourceRecord(source=f"Yahoo Finance FX {fx_symbol}", retrieval_time=retrieved, reporting_period=f"through {as_of}"))
    source_log.append(SourceRecord(source="Yahoo Finance news", retrieval_time=retrieved, reporting_period=f"90 days through {as_of}", url=source_url))

    observed_sources = {name: "calculated from Yahoo Finance" for name, value in metrics.items() if value is not None}
    return InputSnapshot(
        ticker=ticker_symbol.upper(),
        country=country,
        as_of=as_of,
        retrieved_at=retrieved,
        company_name=info.get("longName") or info.get("shortName"),
        sector=info.get("sector") or info.get("sectorDisp"),
        industry=info.get("industry") or info.get("industryDisp"),
        currency=info.get("currency") or config["currency"],
        prices=_price_records(prices),
        benchmark_prices=_price_records(benchmark),
        fx_rates=_price_records(fx_frame),
        news=news_items,
        statements=statements,
        metrics=metrics,
        metric_sources=observed_sources,
        last_price_date=pd.Timestamp(local_close.index[-1]).date() if not local_close.empty else None,
        latest_financial_date=latest_financial_date,
        source_log=source_log,
        warnings=warnings,
    )
