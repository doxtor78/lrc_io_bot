from playwright.sync_api import sync_playwright
from datetime import datetime
import sqlite3

def scrape_funding_rates():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.coinglass.com/FundingRate", wait_until="networkidle")
        page.wait_for_timeout(5000)
        page.wait_for_selector('tr', timeout=10000)

        funding_data = []

        # Find all table sections (Token-margined and USDT-margined)
        tables = page.locator('table').all()
        for table in tables:
            # Get the margin type from a nearby label or heading
            margin_type = "Unknown"
            # Try to find a label above the table
            parent = table.locator('xpath=..')
            label = parent.locator('div,span,h2,h3').first
            if label.count() > 0:
                margin_type = label.inner_text().strip()
            # Get exchange names from the table header
            header_row = table.locator('thead tr').first
            header_cells = header_row.locator('th').all()
            exchange_names = []
            for cell in header_cells[2:]:
                title = cell.get_attribute('title')
                if not title:
                    child = cell.locator('[title]')
                    if child.count() > 0:
                        title = child.first.get_attribute('title')
                if not title:
                    title = cell.inner_text().strip()
                exchange_names.append(title)
            # Get all BTC rows in this table
            rows = table.locator('tbody tr').all()
            for i, row in enumerate(rows):
                try:
                    tds = row.locator("td").all()
                    if len(tds) < 2:
                        continue
                    symbol_div = tds[1].locator('.symbol-name')
                    symbol = symbol_div.inner_text().strip().upper()
                    if symbol in ("BTC", "XBT"):
                        for j, exchange in enumerate(exchange_names):
                            if j + 2 >= len(tds):
                                continue
                            rate_td = tds[j + 2]
                            rate_text = rate_td.inner_text().strip().split('\n')[0]
                            rate_text = ''.join(c for c in rate_text if c.isdigit() or c in '.-')
                            if rate_text == '' or not exchange:
                                continue
                            rate = float(rate_text)
                            funding_data.append((datetime.now().isoformat(), symbol, exchange, margin_type, str(rate)))
                except Exception as e:
                    print(f"Row {i}: Error processing row: {e}", flush=True)
                    continue
        browser.close()
        print(f"Final funding_data: {funding_data}", flush=True)
        return funding_data

if __name__ == "__main__":
    scrape_funding_rates()

conn = sqlite3.connect("funding_rates.db")
cur = conn.cursor()
cur.execute("SELECT * FROM funding_rates LIMIT 5")
print(cur.fetchall())
conn.close() 