import os
import time
import platform
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from dotenv import load_dotenv
import pandas as pd

class CoinstatsScraper:
    def __init__(self):
        print("Initializing scraper...")
        load_dotenv()
        print("Environment variables loaded.")
        self.setup_driver()
        
    def setup_driver(self):
        """Set up the Chrome WebDriver with appropriate options."""
        print("Setting up Chrome WebDriver...")
        chrome_options = Options()
        # Uncomment the line below if you want to run in headless mode
        # chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        chromedriver_path = os.getenv('CHROMEDRIVER_PATH')
        print(f"CHROMEDRIVER_PATH from .env: {chromedriver_path}")
        if chromedriver_path and os.path.exists(chromedriver_path):
            print(f"Using manually specified ChromeDriver at {chromedriver_path}")
            service = Service(chromedriver_path)
        else:
            # Check if running on Mac with Apple Silicon
            if platform.system() == 'Darwin' and platform.machine() == 'arm64':
                print("Detected Mac with Apple Silicon, using webdriver-manager with Chromium type...")
                service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
            else:
                service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Chrome WebDriver setup complete.")
        
    def login(self):
        """Login to Coinstats."""
        print("Navigating to Coinstats...")
        self.driver.get('https://coinstats.app/')
        
        print("Looking for login button...")
        # Wait for login button and click it
        login_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login')]"))
        )
        print("Login button found, clicking...")
        login_button.click()
        
        print("Waiting for email input...")
        # Wait for email input and enter credentials
        email_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        print("Entering email...")
        email_input.send_keys(os.getenv('COINSTATS_EMAIL'))
        
        print("Entering password...")
        password_input = self.driver.find_element(By.NAME, "password")
        password_input.send_keys(os.getenv('COINSTATS_PASSWORD'))
        
        print("Clicking submit button...")
        # Click the submit button
        submit_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()
        
        print("Waiting for login to complete...")
        # Wait for login to complete
        time.sleep(5)
        print("Login process completed.")
        
    def get_portfolio_data(self):
        """Scrape portfolio data from the dashboard."""
        # Navigate to portfolio page
        self.driver.get('https://coinstats.app/portfolio')
        
        # Wait for portfolio data to load
        time.sleep(5)
        
        # TODO: Implement specific data extraction based on the actual page structure
        # This will need to be updated after inspecting the actual page elements
        
        portfolio_data = []
        # Example structure (to be updated):
        # portfolio_elements = self.driver.find_elements(By.CLASS_NAME, 'portfolio-item')
        # for element in portfolio_elements:
        #     coin_name = element.find_element(By.CLASS_NAME, 'coin-name').text
        #     amount = element.find_element(By.CLASS_NAME, 'amount').text
        #     value = element.find_element(By.CLASS_NAME, 'value').text
        #     portfolio_data.append({
        #         'coin': coin_name,
        #         'amount': amount,
        #         'value': value
        #     })
        
        return portfolio_data
    
    def save_to_csv(self, data, filename='portfolio_data.csv'):
        """Save the scraped data to a CSV file."""
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
    
    def close(self):
        """Close the browser."""
        print("Closing browser...")
        self.driver.quit()
        print("Browser closed.")

def main():
    scraper = CoinstatsScraper()
    try:
        print("\nStarting login process...")
        scraper.login()
        print("\nLogin successful! Testing complete.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main() 