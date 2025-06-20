"""
Financial Tools for LangChain Agent

Professional financial analysis tools with structured outputs using Pydantic models.
All tools follow LangChain best practices for reliable agent integration.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Optional
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from pydantic import BaseModel, Field
import config

# Pydantic models for structured outputs
class StockPriceData(BaseModel):
    """Stock price and key metrics."""
    symbol: str = Field(description="Stock ticker symbol")
    current_price: Optional[float] = Field(description="Current stock price")
    market_cap: Optional[int] = Field(description="Market capitalization")
    pe_ratio: Optional[float] = Field(description="Price-to-earnings ratio")
    week_52_high: Optional[float] = Field(description="52-week high price")
    week_52_low: Optional[float] = Field(description="52-week low price")
    formatted_summary: str = Field(description="Human-readable summary")
    error: Optional[str] = None

class CompanyInfo(BaseModel):
    """Company information and fundamentals."""
    symbol: str = Field(description="Stock ticker symbol")
    name: Optional[str] = Field(description="Company name")
    sector: Optional[str] = Field(description="Business sector")
    industry: Optional[str] = Field(description="Industry classification")
    country: Optional[str] = Field(description="Country of incorporation")
    employees: Optional[int] = Field(description="Number of employees")
    business_summary: Optional[str] = Field(description="Business description")
    error: Optional[str] = None

class FinancialHistoryResult(BaseModel):
    """Historical performance analysis."""
    symbol: str
    period: str
    start_price: Optional[float] = None
    end_price: Optional[float] = None
    total_return_percent: Optional[float] = None
    cagr_percent: Optional[float] = None
    volatility_percent: Optional[float] = None
    max_drawdown_percent: Optional[float] = None
    trading_days: Optional[int] = None
    formatted_summary: Optional[str] = None
    error: Optional[str] = None

class CompoundGrowthResult(BaseModel):
    """Compound growth calculation results."""
    principal: float
    annual_rate: float
    years: float
    future_value: float
    total_growth: float
    total_return_percent: float
    formatted_summary: str
    error: Optional[str] = None

class FinancialRatioResult(BaseModel):
    """Financial ratio calculation and interpretation."""
    numerator: float
    denominator: float
    ratio_type: str
    ratio_value: Optional[float] = None
    description: Optional[str] = None
    interpretation: Optional[str] = None
    context: Optional[str] = None
    formatted_summary: Optional[str] = None
    error: Optional[str] = None

@tool
def get_stock_price(symbol: str) -> StockPriceData:
    """
    Get current stock price and key metrics.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA', 'NVDA')

    Returns:
        Structured stock price data with current price, market cap, and ratios
    """
    try:
        symbol = symbol.upper().strip()
        ticker = yf.Ticker(symbol)
        info = ticker.info

        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        market_cap = info.get('marketCap')
        pe_ratio = info.get('trailingPE') or info.get('forwardPE')
        week_52_high = info.get('fiftyTwoWeekHigh')
        week_52_low = info.get('fiftyTwoWeekLow')

        if market_cap:
            market_cap = int(market_cap)

        # Create summary
        summary_parts = [f"Stock: {symbol}"]
        if current_price:
            summary_parts.append(f"Price: ${current_price:.2f}")
        if market_cap:
            summary_parts.append(f"Market Cap: ${market_cap:,}")
        if pe_ratio:
            summary_parts.append(f"P/E: {pe_ratio:.2f}")
        if week_52_high and week_52_low:
            summary_parts.append(f"52W Range: ${week_52_low:.2f} - ${week_52_high:.2f}")

        return StockPriceData(
            symbol=symbol,
            current_price=current_price,
            market_cap=market_cap,
            pe_ratio=pe_ratio,
            week_52_high=week_52_high,
            week_52_low=week_52_low,
            formatted_summary=" | ".join(summary_parts)
        )

    except Exception as e:
        return StockPriceData(
            symbol=symbol,
            current_price=None,
            market_cap=None,
            pe_ratio=None,
            week_52_high=None,
            week_52_low=None,
            formatted_summary=f"Error retrieving stock data for {symbol}: {str(e)}",
            error=str(e)
        )

@tool
def get_company_info(symbol: str) -> CompanyInfo:
    """
    Get detailed company information.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT')

    Returns:
        Structured company information including sector, industry, and business details
    """
    try:
        symbol = symbol.upper().strip()
        ticker = yf.Ticker(symbol)
        info = ticker.info

        return CompanyInfo(
            symbol=symbol,
            name=info.get('longName') or info.get('shortName'),
            sector=info.get('sector'),
            industry=info.get('industry'),
            country=info.get('country'),
            employees=info.get('fullTimeEmployees'),
            business_summary=info.get('longBusinessSummary', 'No business summary available')
        )

    except Exception as e:
        return CompanyInfo(
            symbol=symbol,
            name=None,
            sector=None,
            industry=None,
            country=None,
            employees=None,
            business_summary=f"Error retrieving company info for {symbol}: {str(e)}",
            error=str(e)
        )

@tool
def get_financial_history(query: str) -> FinancialHistoryResult:
    """
    Get historical performance and calculate key metrics.

    Args:
        query: Format "SYMBOL PERIOD" (e.g., "AAPL 5y", "TSLA 2y")

    Returns:
        Historical performance analysis with returns, CAGR, volatility, and drawdown
    """
    try:
        # Parse query
        parts = query.strip().split()
        symbol = parts[0].upper() if parts else query.upper()
        period = parts[1].lower() if len(parts) > 1 else "1y"

        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            return FinancialHistoryResult(
                symbol=symbol,
                period=period,
                formatted_summary=f"No historical data available for {symbol}",
                error="No data available"
            )

        # Calculate metrics
        start_price = hist['Close'].iloc[0]
        end_price = hist['Close'].iloc[-1]
        total_return = ((end_price - start_price) / start_price) * 100

        # CAGR calculation
        years = len(hist) / 252  # Trading days per year
        cagr = ((end_price / start_price) ** (1/years) - 1) * 100 if years > 0 else 0

        # Volatility (annualized)
        daily_returns = hist['Close'].pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(252) * 100

        # Max drawdown
        rolling_max = hist['Close'].expanding().max()
        drawdown = (hist['Close'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100

        formatted_summary = f"{symbol} Performance ({period}): Total Return: {total_return:.2f}%, CAGR: {cagr:.2f}%, Volatility: {volatility:.2f}%, Max Drawdown: {max_drawdown:.2f}%"

        return FinancialHistoryResult(
            symbol=symbol,
            period=period,
            start_price=round(start_price, 2),
            end_price=round(end_price, 2),
            total_return_percent=round(total_return, 2),
            cagr_percent=round(cagr, 2),
            volatility_percent=round(volatility, 2),
            max_drawdown_percent=round(max_drawdown, 2),
            trading_days=len(hist),
            formatted_summary=formatted_summary
        )

    except Exception as e:
        return FinancialHistoryResult(
            symbol=symbol if 'symbol' in locals() else 'UNKNOWN',
            period=period if 'period' in locals() else 'UNKNOWN',
            formatted_summary=f"Error retrieving financial history: {str(e)}",
            error=str(e)
        )

@tool
def calculate_compound_growth(query: str) -> CompoundGrowthResult:
    """
    Calculate compound growth and future value.

    Args:
        query: Format "PRINCIPAL RATE YEARS" (e.g., "10000 0.07 10")

    Returns:
        Future value, growth, and return calculations
    """
    try:
        parts = query.strip().split()
        if len(parts) < 3:
            raise ValueError("Query must contain principal, annual_rate, and years")

        principal = float(parts[0])
        annual_rate = float(parts[1])
        years = float(parts[2])

        if years <= 0 or principal <= 0:
            raise ValueError("Principal and years must be positive")

        future_value = principal * (1 + annual_rate) ** years
        total_growth = future_value - principal
        total_return_pct = (future_value / principal - 1) * 100

        formatted_summary = f"Investment: ${principal:,.2f} at {annual_rate*100:.2f}% for {years} years → Future Value: ${future_value:,.2f} (Total Return: {total_return_pct:.2f}%)"

        return CompoundGrowthResult(
            principal=principal,
            annual_rate=annual_rate,
            years=years,
            future_value=round(future_value, 2),
            total_growth=round(total_growth, 2),
            total_return_percent=round(total_return_pct, 2),
            formatted_summary=formatted_summary
        )

    except Exception as e:
        return CompoundGrowthResult(
            principal=0.0,
            annual_rate=0.0,
            years=0.0,
            future_value=0.0,
            total_growth=0.0,
            total_return_percent=0.0,
            formatted_summary="",
            error=f"Calculation error: {str(e)}"
        )

@tool
def calculate_financial_ratio(query: str) -> FinancialRatioResult:
    """
    Calculate and interpret financial ratios.

    Args:
        query: Format "NUMERATOR DENOMINATOR TYPE" (e.g., "82.50 5.50 pe")

    Returns:
        Ratio value, interpretation, and context
    """
    try:
        parts = query.strip().split()
        if len(parts) < 2:
            raise ValueError("Query must contain at least numerator and denominator")

        numerator = float(parts[0])
        denominator = float(parts[1])
        ratio_type = parts[2].lower() if len(parts) > 2 else "generic"

        if denominator == 0:
            raise ValueError("Denominator cannot be zero")

        ratio_value = numerator / denominator

        # Ratio interpretations
        ratio_info = {
            'pe': ("Price-to-Earnings Ratio", "High" if ratio_value > 25 else "Moderate" if ratio_value > 15 else "Low"),
            'debt_to_equity': ("Debt-to-Equity Ratio", "High leverage" if ratio_value > 1 else "Conservative"),
            'current': ("Current Ratio", "Good liquidity" if ratio_value > 1.5 else "Potential concern"),
            'roe': ("Return on Equity", "Strong" if ratio_value > 0.15 else "Average" if ratio_value > 0.10 else "Weak"),
            'generic': ("Financial Ratio", "Custom calculation")
        }

        description, context = ratio_info.get(ratio_type, ratio_info['generic'])
        interpretation = f"{description}: {ratio_value:.2f}"
        formatted_summary = f"{description}: {ratio_value:.2f} - {context}"

        return FinancialRatioResult(
            numerator=numerator,
            denominator=denominator,
            ratio_type=ratio_type,
            ratio_value=round(ratio_value, 4),
            description=description,
            interpretation=interpretation,
            context=context,
            formatted_summary=formatted_summary
        )

    except Exception as e:
        return FinancialRatioResult(
            numerator=0.0,
            denominator=0.0,
            ratio_type="error",
            error=f"Calculation error: {str(e)}"
        )

# Initialize Tavily search tool
try:
    tavily_search = TavilySearch(
        api_key=config.TAVILY_API_KEY,
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=False,
        include_images=False
    )
    FINANCIAL_TOOLS = [
        get_stock_price,
        get_company_info,
        get_financial_history,
        calculate_compound_growth,
        calculate_financial_ratio,
        tavily_search
    ]
except Exception as e:
    print(f"Warning: Tavily search not available: {e}")
    FINANCIAL_TOOLS = [
        get_stock_price,
        get_company_info,
        get_financial_history,
        calculate_compound_growth,
        calculate_financial_ratio
    ]

print(f"Loaded {len(FINANCIAL_TOOLS)} financial tools")