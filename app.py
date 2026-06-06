"""
Crypto Price Tracker — FastAPI Application
==========================================
Endpoints:
  GET /                          → API info
  GET /dashboard                 → HTML dashboard (Jinja2)
  GET /api/prices/latest         → latest price per currency
  GET /api/prices/history/{cur}  → full price history
  GET /api/prices/plot/{cur}     → PNG chart (embedded in dashboard)

Background job (APScheduler):
  Fetches prices from Nobitex every 15 minutes and inserts into DB.
"""

import logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import psycopg2

from task_four.Task41 import latest_nobitex, save_to_database
from task_four.Task4 import fetch_data, plot_currency_to_bytes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host":     "localhost",
    "database": "Task3",
    "user":     "postgres",
    "password": "@442sorena",
}

PRICE_CODES = ["USDTIRT", "BTCIRT"]
FETCH_INTERVAL_MINUTES = 5

# ---------------------------------------------------------------------------
# Background scheduler
# ---------------------------------------------------------------------------
scheduler = BackgroundScheduler()


def fetch_and_store():
    """Fetch latest prices from Nobitex and persist them to PostgreSQL."""
    results = []
    for code in PRICE_CODES:
        try:
            price = latest_nobitex(code)
            results.append({"code": code, "price": price})
            logger.info(f"Fetched {code}: {price}")
        except Exception as e:
            logger.error(f"Failed to fetch {code}: {e}")

    if results:
        try:
            save_to_database(results, DB_CONFIG)
            logger.info("Database updated successfully.")
        except Exception as e:
            logger.error(f"DB write failed: {e}")


# ---------------------------------------------------------------------------
# App lifespan  (replaces deprecated on_event)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    fetch_and_store()                          # run once immediately at boot
    scheduler.add_job(
        fetch_and_store,
        trigger="interval",
        minutes=FETCH_INTERVAL_MINUTES,
        id="price_fetcher",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — updating every {FETCH_INTERVAL_MINUTES} min.")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Crypto Price Tracker",
    description="Real-time Nobitex price dashboard backed by PostgreSQL.",
    version="1.0.0",
    lifespan=lifespan,
)

# templates = Jinja2Templates(directory="templates")
from pathlib import Path
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# ---------------------------------------------------------------------------
# DB dependency
# ---------------------------------------------------------------------------
def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", tags=["Info"])
def root():
    return {
        "message": "Crypto Price Tracker is running.",
        "endpoints": {
            "dashboard":     "/dashboard",
            "latest prices": "/api/prices/latest",
            "history":       "/api/prices/history/{currency}",
            "plot":          "/api/prices/plot/{currency}",
            "docs":          "/docs",
        },
    }


@app.get("/dashboard", tags=["Dashboard"])
def dashboard(request: Request, currency: str = "btcirt", cursor=Depends(get_db)):
    """Renders the HTML price dashboard."""
    latest  = _latest_prices(cursor)
    history = _price_history(currency, cursor)
    return templates.TemplateResponse(
    request=request,
    name="prices_dashboard.html",
    context={
        "latest_prices": latest,
        "history_data":  history,
        "currency":      currency.upper(),
        "all_currencies": PRICE_CODES,
    }
)


@app.get("/api/prices/latest", tags=["Prices"])
def get_latest_prices(cursor=Depends(get_db)):
    """Returns the most recent price for each tracked currency."""
    return _latest_prices(cursor)


@app.get("/api/prices/history/{currency}", tags=["Prices"])
def get_price_history(currency: str, cursor=Depends(get_db)):
    """Returns the full price history for a specific currency."""
    return _price_history(currency, cursor)


@app.get("/api/prices/plot/{currency}", tags=["Prices"], response_class=Response)
def get_price_plot(currency: str):
    """Returns a PNG chart of price history for the given currency."""
    data = fetch_data(DB_CONFIG)
    png  = plot_currency_to_bytes(currency, data)
    if not png:
        raise HTTPException(status_code=404, detail=f"No data for currency: {currency}")
    return Response(content=png, media_type="image/png")


# ---------------------------------------------------------------------------
# Private helpers (reused by both HTML dashboard and JSON endpoints)
# ---------------------------------------------------------------------------
def _latest_prices(cursor):
    try:
        cursor.execute("""
            SELECT DISTINCT ON (currency) currency, price, created_at
            FROM prices
            ORDER BY currency, created_at DESC
        """)
        rows = cursor.fetchall()
        return [
            {"currency": r[0], "price": float(r[1]), "created_at": str(r[2])}
            for r in rows
        ]
    except Exception as e:
        return {"error": str(e)}


def _price_history(currency: str, cursor):
    try:
        cursor.execute("""
            SELECT currency, price, created_at
            FROM prices
            WHERE LOWER(currency) = LOWER(%s)
            ORDER BY created_at
        """, (currency,))
        rows = cursor.fetchall()
        if not rows:
            return {"error": f"No data found for currency: {currency}"}
        prices = [
            {"currency": r[0], "price": float(r[1]), "created_at": str(r[2])}
            for r in rows
        ]
        return {
            "currency":      rows[0][0],
            "total_records": len(prices),
            "prices":        prices,
        }
    except Exception as e:
        return {"error": str(e)}
