BTC Funding Rates Collector - Setup Instructions (for Germany)
============================================================

Hi! Here's how to set up and run the BTC funding rates collector on your computer.

**1. Unpack the files**
- Place all provided files (including `funding_rates.py`, `requirements.txt`, and any folders like `templates/`) into a new folder, e.g. `btc_funding_collector`.

**2. Install Python 3 (if not already installed)**
- On Mac: `brew install python3`
- On Ubuntu/Debian: `sudo apt-get install python3 python3-venv`

**3. Open a terminal and navigate to the project folder**
```
cd /path/to/btc_funding_collector
```

**4. Create and activate a virtual environment**
```
python3 -m venv venv
source venv/bin/activate
```

**5. Install dependencies**
```
pip install -r requirements.txt
```

**6. Run the funding rates collector**
```
python funding_rates.py
```
- This will fetch the latest funding rates and save them to `funding_rates.db` in the same folder.

**7. (Optional) Automate with cron**
- To fetch data every 8 hours, add this line to your crontab (`crontab -e`):
```
0 */8 * * * cd /path/to/btc_funding_collector && source venv/bin/activate && python funding_rates.py
```

**8. (Optional) Export data to CSV**
- To export the database to CSV, run:
```
sqlite3 funding_rates.db -header -csv "SELECT * FROM funding_rates ORDER BY timestamp DESC;" > funding_rates_export.csv
```

**If you have any questions, just ask!** 