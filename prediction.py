import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


FEATURES = [
    "Daily_Return",
    "Volume_Change",
    "RSI",
    "SMA_20",
    "SMA_50",
    "EMA_20",
]


def make_prediction(data):
    """
    Train on historical rows and predict the next trading day's direction.

    The final row is not given a target label. It is used only for the
    next-session prediction. A chronological holdout is used for the
    displayed historical accuracy.
    """
    frame = data.copy()

    # Target for row t: whether the next available session's close is higher.
    frame["Target"] = (frame["Close"].shift(-1) > frame["Close"]).astype(int)
    labelled = frame.iloc[:-1].copy()
    labelled = labelled.dropna(subset=FEATURES + ["Target"])

    if len(labelled) < 80:
        raise ValueError("There is not enough clean data to train the model.")

    split_at = int(len(labelled) * 0.8)
    train = labelled.iloc[:split_at]
    test = labelled.iloc[split_at:]

    if train["Target"].nunique() < 2 or test.empty:
        raise ValueError("The historical data does not contain enough examples.")

    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=250,
                    max_depth=6,
                    min_samples_leaf=4,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )

    model.fit(train[FEATURES], train["Target"])
    test_predictions = model.predict(test[FEATURES])
    historical_accuracy = accuracy_score(test["Target"], test_predictions)

    # Retrain on all labelled history before predicting the latest row.
    model.fit(labelled[FEATURES], labelled["Target"])

    latest_features = frame.iloc[[-1]][FEATURES]
    probabilities = model.predict_proba(latest_features)[0]
    classes = list(model.named_steps["classifier"].classes_)
    probability_by_class = dict(zip(classes, probabilities))

    up_probability = float(probability_by_class.get(1, 0.0))
    down_probability = float(probability_by_class.get(0, 0.0))
    direction = "UP" if up_probability >= down_probability else "DOWN"

    latest = frame.iloc[-1]
    rsi = float(latest["RSI"])
    close = float(latest["Close"])
    sma20 = float(latest["SMA_20"])

    # Signals are intentionally conservative. The model's direction alone
    # is not treated as a trading instruction.
    if (
        up_probability >= 0.58
        and close > sma20
        and rsi < 70
    ):
        signal = "BUY"
        explanation = (
            "The model favours an upward move, the closing price is above "
            "its 20-day average, and RSI is below the overbought threshold."
        )
    elif (
        down_probability >= 0.58
        and close < sma20
    ):
        signal = "SELL"
        explanation = (
            "The model favours a downward move and the closing price is "
            "below its 20-day average. For an existing holding, review your "
            "own exit plan before acting."
        )
    else:
        signal = "HOLD"
        explanation = (
            "The model and indicator conditions do not provide a sufficiently "
            "clear signal. Waiting may be more appropriate than forcing a trade."
        )

    return {
        "direction": direction,
        "signal": signal,
        "up_probability": round(up_probability * 100, 1),
        "down_probability": round(down_probability * 100, 1),
        "historical_accuracy": round(historical_accuracy * 100, 1),
        "explanation": explanation,
    }





