import random
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor

from fastapi import FastAPI, Query, requests
import requests
from seleniumbase import Driver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from starlette.responses import JSONResponse
from selenium import webdriver


app = FastAPI()


CHROMEDRIVER_PATH = 'chromedriver.exe'

# def create_driver():
#     remote_url = "https://standalone-chrome-production-2d05.up.railway.app/wd/hub"  # Your Selenium Grid / remote Chrome URL
#
#     # 1) Create ChromeOptions
#     options = Options()
#     # Add your preferred arguments if needed:
#     options.add_argument("--headless")
#     options.add_argument("--disable-gpu")
#     options.add_argument("--no-sandbox")
#
#     # 2) Pass those options to Remote
#     driver = webdriver.Remote(
#         command_executor=remote_url,
#         options=options
#     )
#     return driver


def create_driver():
    driver = Driver(uc=True, headless=True)
    return driver


# def scrape_website_1(from_address: str, to_address: str, quantity: str):
#     # Call the first scraping function and return its result
#     return search_second(from_address, to_address, quantity)
#
#
# def scrape_website_2(from_address: str, to_address: str, quantity: str):
#     # Call the second scraping function and return its result
#     return search_first(from_address, to_address, quantity)



@app.get("/scrape")
async def scrape_both(
    from_address: str = Query(..., description="The origin address (hardcoded for cargoboard API)"),
    to_address: str = Query(..., description="The destination address"),
    quantity: str = Query(..., description="The quantity of items to scrape"),
):
    results = {}
    all_prices = []  # To store all prices from both APIs

    try:
        cargoboard_response = call_cargoboard_api(from_address, to_address, quantity)
        cargoboard_price = cargoboard_response.get("price")
        results["website_1"] = cargoboard_response

        # Append cargoboard price if available
        if cargoboard_price is not None:
            all_prices.append(cargoboard_price)
    except Exception as e:
        cargoboard_price = None
        results["website_1"] = {"error": str(e)}

    driver = create_driver()
    try:
        search_first_response = search_first(from_address, to_address, quantity, driver)

        results["website_2"] = search_first_response

        if isinstance(search_first_response, list):
            all_prices.extend(search_first_response)
    except Exception as e:
        results["website_2"] = {"error": str(e)}
    finally:
        driver.quit()

    # Determine the lowest price
    overall_lowest_price = min(all_prices) if all_prices else None

    # Include all prices and the lowest price in the final response
    results["all_prices"] = all_prices
    results["lowest_price"] = overall_lowest_price

    return JSONResponse(content=results)



def search_second(from_address: str, to_address: str, quantityAmount: str, driver):

    unitLength = "100"
    unitWidth = "120"
    unitHeight = "200"
    unitWeight = "999"


    url = "https://my.cargoboard.com/"

    try:
        # Step 1: Open the website
        driver.get(url)

        # Step 2: Accept cookies
        try:
            print("About to accept cookies")
            accept_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[@id='CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll']"))
            )
            accept_button.click()
        except Exception as e:
            print("Cookie acceptance button not found or already accepted:", e)

        # Step 3: Enter the pickup address
        pickup_address = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//input[@data-cy='input-pickUpLocation']")))
        pickup_address.click()
        pickup_address.send_keys(from_address)

        # Wait for the list to become visible
        autocomplete_list = WebDriverWait(driver, 3).until(
            EC.visibility_of_element_located((By.ID, "autocomplete-result-list-1"))
        )

        # Locate the first option in the list
        first_option = autocomplete_list.find_element(By.CSS_SELECTOR, "li:first-child")

        # Click the first option
        first_option.click()

        # Step 4: Enter the delivery address
        delivery_address = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//input[@data-cy='input-deliveryLocation']")))

        delivery_address.click()
        delivery_address.send_keys(to_address)

        # Wait for the list to become visible
        autocomplete_list = WebDriverWait(driver, 3).until(
            EC.visibility_of_element_located((By.ID, "autocomplete-result-list-2"))
        )

        # Locate the first option in the list
        first_option = autocomplete_list.find_element(By.CSS_SELECTOR, "li:first-child")

        # Click the first option
        first_option.click()


        package_type_dropdown = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "package-type"))
        )
        select = Select(package_type_dropdown)
        select.select_by_visible_text("One-way pallet")

        length = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.XPATH, "//input[@data-cy='input-package-unit-length']"))
        )
        length.clear()
        length.send_keys(unitLength)

        width = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.XPATH, "//input[@data-cy='input-package-unit-width']"))
        )
        width.clear()
        width.send_keys(unitWidth)

        height = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.XPATH, "//input[@data-cy='input-package-unit-height']"))
        )
        height.clear()
        height.send_keys(unitHeight)

        weight = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.XPATH, "//input[@data-cy='input-packageWeight']"))
        )
        weight.clear()
        weight.send_keys(unitWeight)

        quantity = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.XPATH, "//input[@data-cy='input-package-quantity']"))
        )

        quantity.clear()

        quantity.send_keys(quantityAmount)
        quantity.submit()


        # calculate_button = WebDriverWait(driver, 5).until(
        #     EC.element_to_be_clickable((By.XPATH, "//input[@data-cy='button-']"))
        # )
        # calculate_button.click()

        print("about to parse prices")

        # Step 5: Parse prices
        price_elements = WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//span[contains(@class, 'fs-20 fs-md-23 fw-extra-bold font-secondary')]"))
        )
        print(f"Number of price elements found: {len(price_elements)}")
        for element in price_elements:
            print(f"Visible: {element.is_displayed()}, Text: {element.text}")

        # Extract prices and convert to float
        prices = []
        for element in price_elements:
            price_text = element.text.strip().replace("€", "").replace(",", ".")
            prices.append(float(price_text))

        # Find the lowest price
        lowest_price = min(prices)

        return {"prices": prices, "lowest_price": lowest_price}
    except Exception as e:
        return {"error": str(e)}



def search_first(from_address: str, to_address: str, quantityAmount: str, driver):
    url = "https://www.pamyra.de/"

    unitLength = "100"
    unitWidth = "120"
    unitHeight = "200"
    unitWeight = "999"

    try:
        # Step 1: Open the website
        driver.get(url)

        # Step 2: Accept cookies
        try:
            print("About to accept cookies")
            accept_button = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'GEHT KLAR') or contains(text(), 'accept')]"))
            )
            accept_button.click()
        except Exception as e:
            print("Cookie acceptance button not found or already accepted:", e)


        # Step 3: Input the "From" address
        from_field = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//input[@data-cy='origin']"))
        )
        from_field.clear()
        from_field.send_keys(from_address)

        # Step 4: Wait for the dropdown to appear and select the first option
        first_option = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, "//mat-option[@role='option']"))
        )
        first_option.click()

        to_field = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//input[@data-cy='destination']"))
        )

        to_field.clear()
        to_field.send_keys(to_address)

        # Wait for the dropdown to appear and select the first option
        to_first_option = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, "//mat-option[@role='option']"))
        )
        to_first_option.click()

        dropdown = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, "//mat-select[@data-cy='customer-type']"))
        )
        dropdown.click()

        element = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.ID, "mat-option-0"))
        )

        # Click the element
        element.click()

        button = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.ID, "elem-0"))  # Locate by ID
        )

        # Click the button
        button.click()

        time.sleep(3)

        length = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//input[@data-cy='length']"))
        )
        length.clear()
        length.send_keys(unitLength)

        width = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//input[@data-cy='width']"))
        )

        width.clear()
        width.send_keys(unitWidth)

        height = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//input[@data-cy='height']"))
        )

        height.clear()
        height.send_keys(unitHeight)

        weight = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//input[@data-cy='weight']"))
        )

        weight.clear()
        weight.send_keys(unitWeight)

        quantity = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//input[@data-cy='quantity']"))
        )

        quantity.clear()
        quantity.send_keys(quantityAmount)

        palletType = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, "//mat-select[@data-cy='type']")))
        palletType.click()

        type = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, "//mat-option[span[text()='Einweg-Palette ']]"))
        )
        type.click()

        button = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, "//button[span[text()=' Zeig mir Preise ']]"))
        )

        button.click()

        search_results = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "app-search-result-list-item"))
        )

        # # Step 9: Open the details of the record
        # details_button = WebDriverWait(driver, 10).until(
        #     EC.element_to_be_clickable((By.XPATH, "//button[contains(@data-cy, 'offer-detail-and-booking-id')]"))
        # )
        # details_button.click()

        # Extract prices from the search results
        prices = []
        for result in search_results:
            try:
                # Locate the price element
                price_element = result.find_element(By.CSS_SELECTOR, ".trip-price")
                price_text = price_element.text.replace("€", "").strip()

                # Remove thousands separator and convert to float
                price_text = price_text.replace(".", "").replace(",", ".")
                price_value = float(price_text)

                prices.append(price_value)
            except Exception as e:
                print(f"Error extracting price: {e}")
        # Sort the prices and find the first 3 cheapest
        prices.sort()
        cheapest_three = prices[:3]

        print("Cheapest 3 prices:", cheapest_three)

        return cheapest_three
    except Exception as e:
        return {"error": str(e)}



def call_cargoboard_api(from_address: str, to_address: str, quantity: str):
    from_postcode, from_city = from_address.split(", ")
    to_postcode, to_city = to_address.split(", ")

    payload = {
        "shipper": {
            "address": {
                "street": "35305 Grünberg, Laubacher Weg 18",
                "countryCode": "DE",
                "postCode": from_postcode,
                "city": from_city,
            }
        },
        "consignee": {
            "address": {
                "street": to_city,
                "countryCode": "DE",
                "postCode": to_postcode,
                "city": to_city,
            }
        },
        "product": "STANDARD",
        "wantsClimateNeutralShipment": False,
        "lines": [
            {
                "unitQuantity": int(quantity),
                "unitLength": 120,
                "unitWidth": 100,
                "unitHeight": 200,
                "unitWeight": 950,
                "content": "Paddockplatten",
                "unitPackageType": "EP",
            }
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJodHRwczovL2NhcmdvYm9hcmQuY29tIiwiYXVkIjoiQ2FyZ29ib2FyZCBDdXN0b21lcnMiLCJqdGkiOiJlODcyYWIyMy1mZmViLTQyYTUtOWQxMC1hNTY0MmZkZWNlZjYiLCJpYXQiOjE2NTg5NDQyOTAuOTUwOTI5LCJjdXN0b21lcl9pZCI6ImU4NzJhYjIzLWZmZWItNDJhNS05ZDEwLWE1NjQyZmRlY2VmNiJ9.9d-d0v9uBwD9lAOm47nzHieR1nIbAf-MI00YRIBLiuROwiUSTJ2Lh_FsXgVkjbVvTsm9bSY2O-dWcwPQI9zVMg"
    }

    api_url = "https://api-sandbox.cargoboard.com/v1/quotations"
    response = requests.post(api_url, json=payload, headers=headers, timeout=45)
    response.raise_for_status()  # Raise error for HTTP issues
    response_data = response.json()

    price = response_data.get("data", {}).get("price", {}).get("grossAmount")
    return {"price": price}



def human_like_typing(element, text, base_delay=0.2, typing_variation=0.1, pause_probability=0.2):
    """
    Type text into an element, simulating human keystrokes with random delays.

    :param element: The WebElement to type into.
    :param text: The string to type.
    :param base_delay: Average delay (seconds) between keystrokes.
    :param typing_variation: Max random variation added/subtracted from base_delay.
    :param pause_probability: Probability of an occasional "longer pause" or short break.
    """
    for char in text:
        element.send_keys(char)

        # Random short delay around the base_delay
        random_delay = base_delay + random.uniform(-typing_variation, typing_variation)
        random_delay = max(0.05, random_delay)  # ensure we don't go below 50ms

        time.sleep(random_delay)

        # Occasionally simulate a slightly longer pause
        if random.random() < pause_probability:
            # e.g. a random extra delay between 0.5s and 1.5s
            time.sleep(random.uniform(0.5, 1.5))
