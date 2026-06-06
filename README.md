These are some series of tasks in my learning journey.
# Crypto Price Tracker

A FastAPI application that tracks cryptocurrency prices from the **Nobitex** exchange, stores them in PostgreSQL, and serves a live dashboard with embedded charts.

---

## Project Structure

```
Task42/
├── app.py                        ← FastAPI app (main entry point)
├── requirements.txt
├── templates/
│   └── prices_dashboard.html     ← Jinja2 dashboard template
├── task_four/
│   ├── __init__.py
│   ├── Task41.py                 ← Nobitex API + DB write
│   └── Task4.py                  ← Fetch, analyse, plot functions
└── price_changes.log             ← Auto-created; logs >2% swings
```

---

## Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Make sure PostgreSQL is running and the DB/table exist
#    (table: prices with columns: currency TEXT, price NUMERIC, created_at TIMESTAMPTZ)
```

---

## Running

```bash
# From the Task42/ directory:
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

---

## Endpoints

| URL | Description |
|-----|-------------|
| `GET /` | API info JSON |
| `GET /docs` | Swagger UI |
| `GET /dashboard?currency=btcirt` | HTML dashboard |
| `GET /api/prices/latest` | Latest price per currency (JSON) |
| `GET /api/prices/history/{currency}` | Full price history (JSON) |
| `GET /api/prices/plot/{currency}` | PNG chart image |

---

## Background Scheduler

On startup the app:
1. **Immediately** fetches prices from Nobitex and writes to PostgreSQL.
2. **Every 15 minutes** repeats the fetch/store cycle automatically.

This replaces the old `time.sleep` loop — no separate process needed.

---

## Price Change Alerts

`price_changes.log` is written whenever:
- Consecutive DB prices differ by **> 2%**
- The latest DB price differs from the current Nobitex live price by **> 2%**

http://localhost:8000/dashboard?currency=usdtirt
http://localhost:8000/api/prices/latest
http://localhost:8000/api/prices/plot/usdtirt