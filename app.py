from datetime import datetime
import os
import re

from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, current_user, login_user,
    logout_user, login_required
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import inspect, text

from stock_data import get_stock_data, get_supported_symbol
from indicators import add_indicators
from prediction import make_prediction


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-before-deployment")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///stocksense.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please sign in to access your dashboard."
login_manager.login_message_category = "info"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    predictions = db.relationship("PredictionHistory", backref="user", lazy=True)


class PredictionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    symbol = db.Column(db.String(30), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    signal = db.Column(db.String(10), nullable=False)
    predicted_direction = db.Column(db.String(10), nullable=False)
    up_probability = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    rsi = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def initialize_database():
    """Create new tables and safely add user ownership to an existing database."""
    db.create_all()

    inspector = inspect(db.engine)
    columns = [column["name"] for column in inspector.get_columns("prediction_history")]

    # Existing installations predate accounts. Keep their old records intact;
    # new predictions are linked to the currently signed-in user.
    if "user_id" not in columns:
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE prediction_history "
                    "ADD COLUMN user_id INTEGER REFERENCES users(id)"
                )
            )


with app.app_context():
    initialize_database()



@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(full_name) < 2:
            flash("Please enter your full name.", "warning")

        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Enter a valid email address.", "warning")

        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "warning")

        elif password != confirm_password:
            flash("The passwords do not match.", "warning")

        elif User.query.filter_by(email=email).first():
            flash(
                "An account with this email already exists. Please sign in.",
                "warning"
            )

        else:
            user = User(
                full_name=full_name,
                email=email,
                password_hash=generate_password_hash(password),
            )

            db.session.add(user)
            db.session.commit()

            login_user(user)

            flash("Your StockSense AI account has been created.", "success")

            return redirect(url_for("dashboard"))

    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=bool(request.form.get("remember")))
            flash("Welcome back to StockSense AI.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email address or password.", "danger")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
@login_required
def dashboard():
    result = None
    chart_labels = []
    chart_prices = []

    if request.method == "POST":
        entered_symbol = request.form.get("symbol", "").strip().upper()
        period = request.form.get("period", "2y")

        if not entered_symbol:
            flash("Enter an NSE stock symbol first.", "warning")
            return redirect(url_for("dashboard"))

        if period not in {"1y", "2y", "5y"}:
            period = "2y"

        symbol = get_supported_symbol(entered_symbol)

        try:
            data = get_stock_data(symbol, period)
            data = add_indicators(data)
            result = make_prediction(data)

            row = data.iloc[-1]
            result["symbol"] = symbol
            result["company_name"] = symbol.replace(".NS", "")
            result["current_price"] = round(float(row["Close"]), 2)
            result["rsi"] = round(float(row["RSI"]), 2)
            result["sma_20"] = round(float(row["SMA_20"]), 2)
            result["ema_20"] = round(float(row["EMA_20"]), 2)
            result["last_date"] = data.index[-1].strftime("%d %b %Y")
            result["period"] = period

            recent = data.tail(90)
            chart_labels = [day.strftime("%d %b") for day in recent.index]
            chart_prices = [round(float(value), 2) for value in recent["Close"]]

            history = PredictionHistory(
                user_id=current_user.id,
                symbol=symbol,
                company_name=result["company_name"],
                signal=result["signal"],
                predicted_direction=result["direction"],
                up_probability=result["up_probability"],
                current_price=result["current_price"],
                rsi=result["rsi"],
            )
            db.session.add(history)
            db.session.commit()

        except Exception as error:
            db.session.rollback()
            flash(str(error), "danger")

    return render_template(
        "dashboard.html",
        result=result,
        chart_labels=chart_labels,
        chart_prices=chart_prices,
    )


@app.route("/history")
@login_required
def history():
    records = (
        PredictionHistory.query
        .filter_by(user_id=current_user.id)
        .order_by(PredictionHistory.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template("history.html", records=records)


@app.route("/about")
def about():
    return render_template("about.html")


if __name__ == "__main__":
    app.run(debug=True)
