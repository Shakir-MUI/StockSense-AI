# StockSense AI

StockSense AI is a Flask application that analyses Indian NSE daily stock data and estimates the next available trading session's direction.

## Features

- User registration, sign in and sign out
- Secure password hashing using Werkzeug
- Remember-me login sessions
- User-specific prediction history
- Search an NSE ticker (for example `RELIANCE` or `TCS`)
- Download daily historical OHLCV data using `yfinance`
- Calculate RSI, SMA and EMA
- Train a Random Forest classifier for next-session UP/DOWN direction
- Display BUY, SELL or HOLD using conservative example rules
- Interactive closing-price chart using Plotly
- Responsive dark fintech interface

## Requirements

- Python 3.10 or later
- Internet connection for `yfinance` data and Bootstrap, Plotly and Google Fonts CDN assets

## Windows setup

Open Command Prompt or PowerShell in this folder.

```powershell
py -m venv venv
venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in your browser. Create an account from the registration page.

## Example symbols

- `RELIANCE`
- `TCS`
- `INFY`
- `HDFCBANK`
- `ICICIBANK`

The application automatically adds `.NS`.

## Authentication and database

- User passwords are stored as password hashes; plaintext passwords are never saved.
- Each new prediction is linked to the signed-in user's account.
- The prediction history page only displays records belonging to the current account.
- The application automatically adds a nullable `user_id` column to an existing `prediction_history` table when it starts.
- Existing predictions from before account support are retained in the database but are not assigned to any new user. New predictions are stored against the signed-in account.
- The default SQLite database is stored in Flask's `instance` folder.

For deployment, set a long, random `SECRET_KEY` environment variable. Do not use the development fallback key in a public deployment. Use HTTPS and a production WSGI server; do not run Flask's debug server publicly.

## How the prediction works

The target for each historical row is whether the next available trading session's close is higher than the current row's close. The first 80% of labelled observations are used for training and the later 20% are used as a chronological holdout. The model is then refitted on all labelled observations before estimating the next session.

The BUY/SELL/HOLD logic is a simple project rule, not a validated trading strategy:

- BUY when the model's UP probability is at least 58%, latest close is above the 20-day SMA, and RSI is below 70.
- SELL when the model's DOWN probability is at least 58% and latest close is below the 20-day SMA.
- HOLD otherwise.

The probability is a classifier score and should not be interpreted as a calibrated real-world chance unless calibration is separately tested. Historical accuracy is not a promise of future performance.

## Important notes

- `yfinance` is an unofficial data interface and availability can change.
- This is an educational software project, not a registered investment advisory service.
- Market data may be delayed, incomplete or unavailable.
- Never use model output alone to make an investment decision.
