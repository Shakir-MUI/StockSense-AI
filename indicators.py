import pandas as pd


def add_indicators(data):
    """Add a small set of indicators using only current and past prices."""
    frame = data.copy()

    frame["SMA_20"] = frame["Close"].rolling(window=20).mean()
    frame["SMA_50"] = frame["Close"].rolling(window=50).mean()
    frame["EMA_20"] = frame["Close"].ewm(
        span=20, adjust=False
    ).mean()

    change = frame["Close"].diff()
    gains = change.clip(lower=0)
    losses = -change.clip(upper=0)

    average_gain = gains.ewm(
        alpha=1 / 14, min_periods=14, adjust=False
    ).mean()
    average_loss = losses.ewm(
        alpha=1 / 14, min_periods=14, adjust=False
    ).mean()

    relative_strength = average_gain / average_loss.replace(0, 1e-10)
    frame["RSI"] = 100 - (100 / (1 + relative_strength))

    frame["Daily_Return"] = frame["Close"].pct_change()
    frame["Volume_Change"] = frame["Volume"].pct_change()

    return frame.replace([float("inf"), float("-inf")], pd.NA)
