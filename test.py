import time
import random
import functools
import pytest
import requests
import os
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common import NoSuchElementException, ElementNotInteractableException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(filename='debugtest.log', level=logging.INFO)
logging.info('Debugging started.')

# Configure Chrome to run in headless mode
chrome_options = Options()
#chrome_options.add_argument("--headless=new") # Run browser in headless mode
chrome_options.add_argument("--disable-gpu") # Disable GPU usage
chrome_options.add_argument("--no-sandbox") # Bypass OS security model (Linux-specific)
chrome_options.add_argument("--window-size=1920,1080") # Set window size
chrome_options.add_argument("--disable-dev-shm-usage") # Overcome resource limitations
chrome_options.add_argument("--disable-features=NetworkService,NetworkServiceInProcess")  # Disable certain features
chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Mask automation

# Initialize WebDriver

try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(60)  # Set page load timeout to 60 seconds
    logging.info("WebDriver initialized successfully.")
except Exception as e:
    service = Service(executable_path="./chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=chrome_options)

soup = BeautifulSoup(driver.page_source, features='lxml')
#soup2 = BeautifulSoup(html, 'html.parser')

# Global constants
BASE_URL = "https://sirocco-pos.orange.tn"
LOGIN_URL = f"{BASE_URL}/"
PURCHASE_OPTIONS_URL = f"{BASE_URL}/data-options/purchase-options"
# Default credentials (from environment variables or hardcoded fallback)
DEFAULT_USERNAME  = os.getenv("CRM_USERNAME", "default_username")
DEFAULT_PASSWORD = os.getenv("CRM_PASSWORD", "default_password")
PURCHASE_NUMS = [55665805, 29630432]
offres = ["100 Mo", "200 Mo", "2,2 Go", "10 Go", "25 Go", "30 Go", "55 Go", "75 Go", "100 Go"]

# Utility functions

# Retry logic: Retries a task indefinitely until it succeeds.
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

def random_purshase_num(start=None, end=None, numbers_list=None):
    """
    Picks a random number from a given range or list.
    
    Parameters:
        start (int): Start of the range (inclusive).
        end (int): End of the range (inclusive).
        numbers_list (list): A list of numbers to choose from.
    
    Returns:
        int: A randomly chosen number.
    """
    if numbers_list:
        return random.choice(numbers_list)
    elif start is not None and end is not None:
        return random.randint(start, end)
    else:
        raise ValueError("Provide either a list of numbers or a valid range (start and end).")

def wait_for_page_load(driver, timeout=20):
    """Waits for the page to fully load."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        return True
    except TimeoutException:
        logging.error("Page did not load completely.")
        return False

def wait_for_element(locator, timeout=20, condition=EC.presence_of_element_located):
    """Wait for an element with a specific condition."""
    try:
        return WebDriverWait(driver, timeout).until(condition(locator))
    except TimeoutException:
        logging.error(f"Timeout while waiting for element: {locator}")
        return None

def login(username=None, password=None):
    """Logs into the CRM system."""
    logging.info("Logging in task in progress...")
    user, pwd = get_credentials(username, password)
    driver.get(LOGIN_URL)
    if not wait_for_page_load(driver):
        logging.error("Login page failed to load.")
        return False

    try:
        username_field = wait_for_element((By.XPATH, "/html/body/div/div/div/div[2]/form/div[1]/input[@id='identifier']"), condition=EC.visibility_of_element_located)
        password_field = wait_for_element((By.XPATH, "/html/body/div/div/div/div[2]/form/div[2]/input[@id='password']"), condition=EC.visibility_of_element_located)
        login_button = wait_for_element((By.XPATH, "/html/body/div/div/div/div[2]/form/div[3]/button[@type='submit']"), condition=EC.element_to_be_clickable)

        if username_field and password_field and login_button:
            username_field.send_keys(user)
            password_field.send_keys(pwd)
            login_button.click()
            logging.info("Login successful.")
            return True
        else:
            logging.error("One or more login elements were not interactable.")
            return False
    except Exception as e:
        logging.error(f"Error during login: {e}")
        return False

def verify_dashboard_loaded():
    logging.info("Dashboard loading task in progress...")
    """Verifies if the dashboard is loaded."""
    try:
        dashboard_element = wait_for_element((By.XPATH, "/html/body/main/div/div/div[1]/div[1]/div/h2[text()='Mon tableau de bord']"), condition=EC.visibility_of_element_located)
        infos_flash_element = wait_for_element((By.XPATH, "/html/body/main/div/div/div[4]/div[1]/div/h2[text()='Infos Flash']"), condition=EC.visibility_of_element_located)

        if dashboard_element and infos_flash_element:
            logging.info("Dashboard loaded successfully.")
            return True
        else:
            logging.error("Dashboard elements are missing.")
            return False
    except Exception as e:
        logging.error(f"Error verifying dashboard: {e}")
        return False

def navigate_to_purchase_options():
    logging.info("Navigating to purshase options task in progress...")
    """Navigates to the purchase options page."""
    driver.get(PURCHASE_OPTIONS_URL)
    if not wait_for_page_load(driver):
        logging.error("Purchase options page failed to load.")
        return False

    try:
        form = wait_for_element((By.ID, "buyOptionsForm"), condition=EC.visibility_of_element_located)
        input_field = wait_for_element((By.XPATH, "//input[@inputmode='numeric']"), condition=EC.visibility_of_element_located)
        submit_button = wait_for_element((By.XPATH, "//button[@type='submit']"), condition=EC.element_to_be_clickable)

        if form and input_field and submit_button:
            random_phone_number = random.choice(PURCHASE_NUMS)
            input_field.send_keys(random_phone_number)
            submit_button.click()
            logging.info("Navigated to purchase options page and submitted MSISDN.")
            return True
        else:
            logging.error("Purchase options form elements are missing or not interactable.")
            return False
    except Exception as e:
        logging.error(f"Error navigating to purchase options: {e}")
        return False

def submit_purchase_request():
    logging.info("Submitting purshase request task in progress...")
    """Submits a purchase request."""
    try:
        internet_options = wait_for_element((By.XPATH, "//*[text()='Options internet Mobile']"), condition=EC.visibility_of_element_located)
        option_element = wait_for_element((By.XPATH, "//*[text()='Navigui 100 Mo (1j)']"), condition=EC.visibility_of_element_located)

        if internet_options and option_element:
            option_element.click()
            logging.info("Purchase request submitted successfully.")
            return True
        else:
            logging.error("Internet options are missing or not interactable.")
            return False
        
        # Use XPath to select an offer
        offer = driver.find_element(By.XPATH, f"//*[contains(text(), 'Navigui {offres[0]}')]")

        # Find the parent of the element (using XPath to navigate to the parent)
        offer_parent = offer.find_element(By.XPATH, "..")  # ".." refers to the parent element

        # Find the next sibling of the parent element (using XPath)
        next_sibling = offer_parent.find_element(By.XPATH, "following-sibling::*")

        off_submit_button = next_sibling.find_element(By.TAG_NAME, "button")
        if off_submit_button:
            off_submit_button.click()
            logging.info("your offer is submitted.")
            time.sleep(20)
            confirmation_form = wait_for_element((By.XPATH, "//*[@role='dialog']"), condition=EC.visibility_of_element_located)
            confirmation_button = confirmation_form.find_element(By.XPATH, ".//button[text()='Confirmer']")
            confirmation_button.click()
            time.sleep(20)
            logging.info("your offer is confirmed.")
            return True
        else:
            logging.error("an error occured during offer request or form elements are not interactable.")
            return False

    except Exception as e:
        logging.error(f"Error submitting purchase request: {e}")
        return False

# Main execution
# Integrate retry for critical tasks
if __name__ == "__main__":
    try:
        retry_forever(login)  # Retry login until it succeeds
        retry_forever(verify_dashboard_loaded)  # Retry dashboard verification
        retry_forever(navigate_to_purchase_options)  # Retry navigation
        retry_forever(submit_purchase_request)  # Retry purchase request submission
    except Exception as e:
        logging.error(f"Critical error in execution: {e}")
    finally:
        driver.quit()