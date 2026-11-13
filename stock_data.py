import yfinance as yf
import pandas as pd


def get_supported_symbol(value):
    """Accept either RELIANCE or RELIANCE.NS for NSE stocks."""
    symbol = value.strip().upper()
    if not symbol:
        raise ValueError("Please enter a stock symbol.")

    if not symbol.endswith(".NS"):
        symbol += ".NS"

    return symbol


def get_stock_data(symbol, period="2y"):
    """Download daily NSE data and return a clean OHLCV DataFrame."""
    try:
        data = yf.download(
            symbol,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception as error:
        raise ValueError(
            "Could not download stock data. Check your internet connection "
            "or try again later."
        ) from error

    if data is None or data.empty:
        raise ValueError(
            f"No market data was returned for {symbol}. "
            "Check the symbol or try another NSE-listed stock."
        )

    # Recent yfinance versions can return MultiIndex columns even for one ticker.
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError("The downloaded data is missing: " + ", ".join(missing))

    data = data[required].copy()
    data = data.dropna(subset=["Open", "High", "Low", "Close"])
    data = data[~data.index.duplicated(keep="last")]
    data = data.sort_index()

    if len(data) < 100:
        raise ValueError(
            "Not enough historical data to train a useful model. "
            "Try a larger listed company or a longer period."
        )

    return data
