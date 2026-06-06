import psycopg2
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from Task41 import latest_nobitex

NOBITEX_CODES = {
    "usdtirt": "USDTIRT",
    "btcirt": "BTCIRT",
}

def check_big_changes(data):
    """Log price changes > 2% to file, also compare with nobitex latest price"""
    logged = set() 

    for currency, values in data.items():
        prices = values["price"]

        for i in range(1, len(prices)):
            change = ((float(prices[i]) - float(prices[i-1])) / float(prices[i-1])) * 100
            if abs(change) > 2:
                entry = f"{currency}: {float(prices[i-1]):,.2f} -> {float(prices[i]):,.2f} ({change:+.2f}%)"
                if entry not in logged:
                    logged.add(entry)
                    with open("price_changes.log", "a") as f:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"[{timestamp}] {entry}\n")                  
        # compare db latest price vs nobitex latest price 
        code = NOBITEX_CODES.get(currency.lower())
        if code:
            try:
                nobitex_price = float(latest_nobitex(code))
                db_last_price = float(prices[-1])
                change = ((nobitex_price - db_last_price) / db_last_price) * 100
                if abs(change) > 2:
                    with open("price_changes.log", "a") as f:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"[{timestamp}] {currency} [DB vs Nobitex]: {db_last_price:,.2f} -> {nobitex_price:,.2f} ({change:+.2f}%)\n")
            except Exception as e:
                print(f"Nobitex fetch failed for {currency}: {e}")

def fetch_data(db_config):          
    try:
        with psycopg2.connect(**db_config) as con, con.cursor() as cursor:
            cursor.execute("""
                SELECT currency, price, created_at
                FROM prices
                ORDER BY currency, created_at
            """)
# ORDER BY currency — groups all rows of the same currency together
# ORDER BY created_at — within each currency, rows are sorted oldest to newest, which is essential so the price line plots left-to-right in correct time order

            columns = [desc[0] for desc in cursor.description[1:]]
            rows = cursor.fetchall()

        data = {}

        for row in rows:
            currency = row[0]
            values   = row[1:]

            if currency not in data:
                data[currency] = {col: [] for col in columns}

            for col, val in zip(columns, values):
                data[currency][col].append(val)
        
        print(data)
        check_big_changes(data)  # Log changes > 2%
        return data

    except (psycopg2.Error, ValueError) as e:
        print(f"Database error: {e}")
        return {}


def plot_data(data):
    if not data:
        print("No data to plot.")
        return

    n = len(data)
    fig, axes = plt.subplots(n, 1, figsize=(14, 5 * n))
    fig.suptitle("Currency Price Analysis", fontsize=16, fontweight="bold", y=1.01)

    if n == 1:
        axes = [axes]

    date_fmt = mdates.DateFormatter("%m-%d")

    for ax, (currency, values) in zip(axes, data.items()):
        times  = values["created_at"]
        prices = np.array(values["price"], dtype=float)

        naive_times = [t.replace(tzinfo=None) for t in times]

        ax.plot(naive_times, prices, linewidth=1.5, color="steelblue")

        idx_max, idx_min = prices.argmax(), prices.argmin()
        ax.annotate(f"Max\n{prices[idx_max]:,.2f}",
                    xy=(naive_times[idx_max], prices[idx_max]),
                    xytext=(10, 10), textcoords="offset points",
                    arrowprops=dict(arrowstyle="->"), fontsize=8, color="green")
        ax.annotate(f"Min\n{prices[idx_min]:,.2f}",
                    xy=(naive_times[idx_min], prices[idx_min]),
                    xytext=(10, -20), textcoords="offset points",
                    arrowprops=dict(arrowstyle="->"), fontsize=8, color="red")

        ax.set_title(f"{currency} — Price", fontweight="bold")
        ax.set_ylabel("Price")
        ax.grid(True, alpha=0.4)
        ax.xaxis.set_major_formatter(date_fmt)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")

    plt.tight_layout()
    plt.show()


db_config = {
    'host':     'localhost',
    'database': 'Task3',
    'user':     'postgres',
    'password': '@442sorena',
}

data = fetch_data(db_config)
plot_data(data)

