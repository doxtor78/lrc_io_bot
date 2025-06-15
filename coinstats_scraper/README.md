# Coinstats Portfolio Scraper

This script allows you to scrape your portfolio data from Coinstats.app using Selenium WebDriver.

## Setup

1. Create a virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project directory with your Coinstats credentials:
```
COINSTATS_EMAIL=your_email@example.com
COINSTATS_PASSWORD=your_password
```

## Usage

1. Make sure you have Chrome browser installed on your system.

2. Run the script:
```bash
python coinstats_scraper.py
```

The script will:
- Open Chrome browser
- Log in to your Coinstats account
- Navigate to your portfolio page
- Scrape the portfolio data
- Save the data to a CSV file named `portfolio_data.csv`

## Notes

- The script currently has a placeholder for the portfolio data extraction. You'll need to inspect the Coinstats portfolio page and update the selectors in the `get_portfolio_data()` method to match the actual page structure.
- The script includes a 5-second wait after login and page navigation to ensure the content is loaded. You might need to adjust these timings based on your internet speed.
- For security, never commit your `.env` file to version control.

## Troubleshooting

If you encounter any issues:
1. Make sure Chrome is installed and up to date
2. Check that your credentials in the `.env` file are correct
3. Ensure you have a stable internet connection
4. If the page structure has changed, you may need to update the selectors in the code 