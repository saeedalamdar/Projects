from fastapi import FastAPI, Depends
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import psycopg2

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# Database connection settings
DB_HOST = "localhost"
DB_NAME = "Task3"
DB_USER = "postgres"
DB_PASSWORD = "@442sorena"

def get_db():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()
        conn.close()

@app.get("/dashboard")
def dashboard(request: Request, currency: str = "btcirt", cursor=Depends(get_db)):
    latest = get_latest_prices(cursor)
    history = get_price_history(currency, cursor)
    return templates.TemplateResponse("prices_dashboard.html", {
        "request": request,
        "latest_prices": latest,
        "history_data": history,
    })

# Endpoint 1: Get latest price of each currency
@app.get("/api/prices/latest")
def get_latest_prices(cursor=Depends(get_db)):
    """Returns the latest price for each currency"""
    try:
        # SQL query: get the latest price for each currency
        cursor.execute("""
            SELECT DISTINCT ON (currency) currency, price, created_at
            FROM prices
            ORDER BY currency, created_at DESC
        """)
        
        rows = cursor.fetchall()
        
        # Convert to list of dictionaries
        result = []
        for row in rows:
            result.append({
                "currency": row[0],
                "price": row[1],
                "created_at": str(row[2])
            })

        return result
    
    except Exception as e:
        return {"error": str(e)}


# Endpoint 2: Get price history for a specific currency
@app.get("/api/prices/history/{currency}")
def get_price_history(currency: str, cursor=Depends(get_db)):
    """Returns all historical prices for a specific currency"""
    try:
        
        # SQL query: get all prices for the given currency, ordered by time
        cursor.execute("""
            SELECT currency, price, created_at
            FROM prices
            WHERE LOWER(currency) = LOWER(%s)
            ORDER BY created_at
        """, (currency,))
        
        rows = cursor.fetchall()
        if not rows:
            return {"error": f"No data found for currency: {currency}"}
        
        # Convert to list of dictionaries
        prices = []
        for row in rows:
            prices.append({
                "currency": row[0],
                "price": row[1],
                "created_at": str(row[2])
            })
        
        return  {
        "currency": rows[0][0],
        "total_records": len(prices),
        "prices": prices
    }
    
   
    except Exception as e:
        return {"error": str(e)}


# Test endpoint
@app.get("/")
def test():
    """Just for testing - shows the API is running"""
    return {"message": "API is running! Visit /prices/latest or /prices/history/btcirt"}



# http://localhost:8000/api/prices/history/usdtirt
# http://localhost:8000/api/prices/latest
# http://localhost:8000/
# http://localhost:8000/docs
# http://localhost:8000/dashboard?currency=btcirt
