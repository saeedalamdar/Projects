import psycopg2
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend (safe for FastAPI)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import io
from datetime import datetime
from task_four.Task41 import latest_nobitex

NOBITEX_CODES = {
    "usdtirt": "USDTIRT",
    "btcirt":  "BTCIRT",
}


def check_big_changes(data):
    """Log price changes > 2% to file; also compare with Nobitex latest price."""
    logged = set()

    for currency, values in data.items():
        prices = values["price"]

        for i in range(1, len(prices)):
            change = ((float(prices[i]) - float(prices[i - 1])) / float(prices[i - 1])) * 100
            if abs(change) > 2:
                entry = (
                    f"{currency}: {float(prices[i-1]):,.2f} -> "
                    f"{float(prices[i]):,.2f} ({change:+.2f}%)"
                )
                if entry not in logged:
                    logged.add(entry)
                    with open("price_changes.log", "a") as f:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"[{timestamp}] {entry}\n")

        # Compare DB latest price vs Nobitex latest price
        code = NOBITEX_CODES.get(currency.lower())
        if code:
            try:
                nobitex_price = float(latest_nobitex(code))
                db_last_price = float(prices[-1])
                change = ((nobitex_price - db_last_price) / db_last_price) * 100
                if abs(change) > 2:
                    with open("price_changes.log", "a") as f:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.write(
                            f"[{timestamp}] {currency} [DB vs Nobitex]: "
                            f"{db_last_price:,.2f} -> {nobitex_price:,.2f} ({change:+.2f}%)\n"
                        )
            except Exception as e:
                print(f"Nobitex fetch failed for {currency}: {e}")


def fetch_data(db_config):
    """Fetch all price rows from the DB and check for big changes."""
    try:
        with psycopg2.connect(**db_config) as con, con.cursor() as cursor:
            cursor.execute("""
                SELECT currency, price, created_at
                FROM prices
                ORDER BY currency, created_at
            """)
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

        check_big_changes(data)
        return data

    except (psycopg2.Error, ValueError) as e:
        print(f"Database error: {e}")
        return {}


def plot_currency_to_bytes(currency: str, data: dict) -> bytes:
    """
    Render a price chart for a single currency and return PNG bytes.
    Used by the FastAPI /api/prices/plot/{currency} endpoint.
    """
    values = data.get(currency.lower()) or data.get(currency.upper()) or data.get(currency)
    if not values:
        # Try case-insensitive match
        for k, v in data.items():
            if k.lower() == currency.lower():
                values = v
                break

    if not values:
        return b""

    times  = values["created_at"]
    prices = np.array(values["price"], dtype=float)
    naive_times = [t.replace(tzinfo=None) for t in times]

    fig, ax = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    ax.plot(naive_times, prices, linewidth=2, color="#58a6ff")
    ax.fill_between(naive_times, prices, prices.min(), alpha=0.15, color="#58a6ff")

    idx_max, idx_min = prices.argmax(), prices.argmin()
    ax.annotate(
        f"Max\n{prices[idx_max]:,.0f}",
        xy=(naive_times[idx_max], prices[idx_max]),
        xytext=(10, 10), textcoords="offset points",
        arrowprops=dict(arrowstyle="->", color="#3fb950"),
        fontsize=8, color="#3fb950",
    )
    ax.annotate(
        f"Min\n{prices[idx_min]:,.0f}",
        xy=(naive_times[idx_min], prices[idx_min]),
        xytext=(10, -20), textcoords="offset points",
        arrowprops=dict(arrowstyle="->", color="#f85149"),
        fontsize=8, color="#f85149",
    )

    ax.set_title(f"{currency.upper()} — Price History", color="#e6edf3", fontsize=13, pad=10)
    ax.set_ylabel("Price (IRT)", color="#8b949e")
    ax.tick_params(colors="#8b949e")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", color="#8b949e")
    for spine in ax.spines.values():
        spine.set_edgecolor("#30363d")
    ax.grid(True, alpha=0.2, color="#30363d")

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def plot_data(data):
    """Interactive matplotlib window — used when running Task4.py directly."""
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
        ax.annotate(
            f"Max\n{prices[idx_max]:,.2f}",
            xy=(naive_times[idx_max], prices[idx_max]),
            xytext=(10, 10), textcoords="offset points",
            arrowprops=dict(arrowstyle="->"), fontsize=8, color="green",
        )
        ax.annotate(
            f"Min\n{prices[idx_min]:,.2f}",
            xy=(naive_times[idx_min], prices[idx_min]),
            xytext=(10, -20), textcoords="offset points",
            arrowprops=dict(arrowstyle="->"), fontsize=8, color="red",
        )

        ax.set_title(f"{currency} — Price", fontweight="bold")
        ax.set_ylabel("Price")
        ax.grid(True, alpha=0.4)
        ax.xaxis.set_major_formatter(date_fmt)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")

    plt.tight_layout()
    plt.show()
