import sqlite3
from playwright.sync_api import sync_playwright
from datetime import datetime
import os

# Database setup
def init_db(check_same_thread=True):
    db_path = "funding_rates.db"
    conn = sqlite3.connect(db_path, check_same_thread=check_same_thread)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funding_rates (
            timestamp TEXT,
            symbol TEXT,
            exchange TEXT,
            interval TEXT,
            funding_rate TEXT,
            PRIMARY KEY (timestamp, symbol, exchange)
        )
    ''')
    conn.commit()
    return conn

def scrape_funding_rates():
    data = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.coinglass.com/FundingRate", wait_until="networkidle")
            page.wait_for_timeout(5000)
            try:
                page.wait_for_selector('tr', timeout=10000)
            except Exception as e:
                print("Timeout waiting for table rows:", e, flush=True)
            rows = page.locator('tr').all()
            print("Number of rows found:", len(rows), flush=True)
            for row in rows:
                cells = row.locator("td").all()
                if len(cells) > 4:
                    symbol = cells[0].inner_text().strip()
                    for i in range(1, len(cells), 2):
                        try:
                            exchange = cells[i].inner_text()
                            rate = cells[i+1].inner_text()
                            data.append((symbol, exchange, rate))
                        except Exception as e:
                            print("Error parsing row:", e, flush=True)
                            continue
            browser.close()
    except Exception as e:
        print("Exception in scrape_funding_rates:", e, flush=True)
    return data

def save_to_db(conn, funding_data):
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    for symbol, exchange, rate in funding_data:
        try:
            cursor.execute('''
                INSERT INTO funding_rates (timestamp, symbol, exchange, interval, funding_rate)
                VALUES (?, ?, ?, ?, ?)
            ''', (now, symbol, exchange, '8h', rate))
        except sqlite3.IntegrityError:
            continue
    conn.commit()

def get_latest_funding_rates(conn, limit=100):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp, symbol, exchange, funding_rate
        FROM funding_rates
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    return cursor.fetchall()

def get_historical_funding_rates(conn, symbol, exchange, days=7):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp, funding_rate
        FROM funding_rates
        WHERE symbol = ? AND exchange = ?
        AND timestamp >= datetime('now', ?)
        ORDER BY timestamp ASC
    ''', (symbol, exchange, f'-{days} days'))
    return cursor.fetchall() 