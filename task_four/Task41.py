import psycopg2
import requests
import time

# we want to update our database every 15 minutes from nobitex


def latest_nobitex(code):
    """Get the latest price from Nobitex"""
    try:
        url = f"https://apiv2.nobitex.ir/v3/orderbook/{code}"
        res = requests.get(url)
        return res.json()['lastTradePrice']
    except Exception as e:
        raise e


def save_to_database(data, db_config):
    """Insert new price rows into the database"""
    con = psycopg2.connect(
        host=db_config['host'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )
    cursor = con.cursor()

    for cur_info in data:
        cur = cur_info['code']
        price = cur_info['price']
        cursor.execute(
    '''
    INSERT INTO prices (currency, price, created_at)
    VALUES (%s, %s, NOW())
    ''',
    (cur, price)
)
    con.commit()
    cursor.close()
    con.close()
