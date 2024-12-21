import time
import random
import logging
import os
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, 
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(filename='debugtest.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("debug started...")

# Configure Chrome options
chrome_options = Options()
#chrome_options.add_argument("--headless=new") # Run browser in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-features=NetworkService,NetworkServiceInProcess")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")


# Global Constants
BASE_URL = "https://sirocco-pos.orange.tn"
LOGIN_URL = f"{BASE_URL}/"
PURCHASE_OPTIONS_URL = f"{BASE_URL}/data-options/purchase-options"
DEFAULT_USERNAME  = os.getenv("CRM_USERNAME", "default_username")
DEFAULT_PASSWORD = os.getenv("CRM_PASSWORD", "default_password")
PURCHASE_NUMS = [55665805, 29630432]
OFFERS = ["100 Mo", "200 Mo", "2,2 Go", "10 Go", "25 Go", "30 Go", "55 Go", "75 Go", "100 Go"]

# Initialize WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
driver.set_page_load_timeout(60)

# Helper Functions
def retry_forever(task, *args, **kwargs):
    while True:
        try:
            logging.info(f"Attempting task: {task.__name__}")
            result = task(*args, **kwargs)
            if result:  # Assuming the task returns a truthy value on success
                logging.info(f"Task {task.__name__} completed successfully.")
                return result
        except Exception as e:
            logging.error(f"Error in task {task.__name__}: {e}")
        logging.info(f"Retrying task: {task.__name__}")
        time.sleep(2)  # Optional delay between retries

def get_credentials(username=None, password=None):
    """
    Returns the username and password to use, prioritizing provided credentials.
    Falls back to environment variables or default values.
    
    Args:
        username (str): User-supplied username.
        password (str): User-supplied password.
    
    Returns:
        tuple: A tuple containing (username, password).
    """
    return username or DEFAULT_USERNAME, password or DEFAULT_PASSWORD

def wait_for_page_load(driver: webdriver.Chrome, timeout: int = 20) -> bool:
    try:
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")
        return True
    except TimeoutException:
        logging.error("Page did not load completely.")
        return False

def wait_for_element(driver: webdriver.Chrome, locator: tuple, condition=EC.presence_of_element_located, timeout: int = 20):
    try:
        return WebDriverWait(driver, timeout).until(condition(locator))
    except TimeoutException:
        logging.error(f"Timeout while waiting for element: {locator}")
        return None

def login(username=None, password=None):
    logging.info("Starting login process.")
    user, pwd = get_credentials(username, password)

    driver.get(LOGIN_URL)
    if not wait_for_page_load(driver):
        logging.error("Login page failed to load.")
        return False
    try:
        username_field = wait_for_element(driver, (By.ID, "identifier"), condition=EC.visibility_of_element_located)
        password_field = wait_for_element(driver, (By.ID, "password"), condition=EC.visibility_of_element_located)
        login_button = wait_for_element(driver, (By.XPATH, "//button[@type='submit']"), condition=EC.element_to_be_clickable)

        if username_field and password_field and login_button:
            username_field.send_keys(user)
            password_field.send_keys(pwd)
            login_button.click()
            logging.info("Login successful.")
            return True
        else:
            logging.error("Login elements are not interactable.")
            return False
    except Exception as e:
        logging.error(f"Error during login: {e}")
        return False

def verify_dashboard_loaded():
    logging.info("Verifying dashboard loaded.")
    try:
        dashboard_loaded = wait_for_element(driver, (By.XPATH, "//h2[text()='Mon tableau de bord']"), EC.visibility_of_element_located)
        flash_loaded = wait_for_element(driver, (By.XPATH, "//h2[text()='Infos Flash']"), EC.visibility_of_element_located)
        if dashboard_loaded and flash_loaded:
            logging.info("Dashboard verified successfully.")
            return True
        else:
            logging.error("Dashboard verification failed.")
            return False
    except Exception as e:
        logging.error(f"Error verifying dashboard: {e}")
        return False

def navigate_to_purchase_options():
    logging.info("Navigating to purchase options.")
    driver.get(PURCHASE_OPTIONS_URL)
    if not wait_for_page_load(driver):
        logging.error("Purchase options page failed to load.")
        return False
    try:
        input_field = wait_for_element(driver, (By.XPATH, "//input[@inputmode='numeric']"), EC.visibility_of_element_located)
        submit_button = wait_for_element(driver, (By.XPATH, "//button[@type='submit']"), EC.element_to_be_clickable)
        if input_field and submit_button:
            input_field.send_keys(random.choice(PURCHASE_NUMS))
            submit_button.click()
            logging.info("Purchase options submitted.")
            return True
        else:
            logging.error("Form elements not interactable.")
            return False
    except Exception as e:
        logging.error(f"Error navigating to purchase options: {e}")
        return False

def submit_purchase_request():
    logging.info("Submitting purchase request.")
    try:
        offer_element = wait_for_element(driver, (By.XPATH, f"//*[text()='Navigui {OFFERS[0]}']"), EC.visibility_of_element_located)
        if offer_element:
            offer_element.click()
            logging.info("Offer selected successfully.")
            return True
        else:
            logging.error("Offer not interactable.")
            return False
    except Exception as e:
        logging.error(f"Error submitting purchase request: {e}")
        return False

# Main Execution
if __name__ == "__main__":
    # Optionally provide custom credentials
    username_override = "my_custom_username"
    password_override = "my_custom_password"

    # Pass them into the login function
    login(username=username_override, password=password_override)
    try:
        if login():
            if verify_dashboard_loaded():
                if navigate_to_purchase_options():
                    submit_purchase_request()
    except Exception as e:
        logging.error(f"Critical error in execution: {e}")
finally:
    driver.quit()
    logging.info("Driver closed.")
