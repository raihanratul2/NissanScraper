"""
Nissan USA Scraper Base Class
Contains common utilities and base functionality
"""

import time
import random
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    StaleElementReferenceException,
    ElementClickInterceptedException
)


class NissanScraperBase:
    """Base class with common scraping utilities"""
    
    def __init__(self, headless=False, delay_range=(2, 4)):
        self.delay_range = delay_range
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, 15)
        
    def _setup_driver(self, headless=False):
        """Configure Chrome WebDriver with anti-detection measures"""
        options = webdriver.ChromeOptions()
        
        # Basic options
        options.add_argument('--start-maximized')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        
        # Anti-detection
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # User agent
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        if headless:
            options.add_argument('--headless=new')
        
        driver = webdriver.Chrome(options=options)
        
        # Additional anti-detection
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def _random_delay(self):
        """Add random delay between actions"""
        delay = random.uniform(self.delay_range[0], self.delay_range[1])
        time.sleep(delay)
    
    def _scroll_to_element(self, element):
        """Scroll element into view"""
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                element
            )
            self._random_delay()
        except:
            pass
    
    def _safe_click(self, element):
        """Safely click on element with JavaScript fallback"""
        try:
            self._scroll_to_element(element)
            element.click()
            return True
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except:
                return False
    
    def _handle_cookies_popup(self):
        """Handle cookie consent popup"""
        cookie_selectors = [
            'button#accept-cookies',
            'button#cookie-accept',
            'button[class*="cookie"]',
            'button[class*="accept"]',
            '#onetrust-accept-btn-handler',
            '.cookie-accept',
            '.accept-cookies'
        ]
        
        for selector in cookie_selectors:
            try:
                cookie_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                if cookie_btn.is_displayed():
                    self._safe_click(cookie_btn)
                    print("✓ Cookie consent handled")
                    self._random_delay()
                    break
            except:
                continue
    
    def _close_popups(self):
        """Close any popup modals"""
        popup_selectors = [
            'button.close',
            'button[class*="close"]',
            'button[aria-label="Close"]',
            '.modal-close',
            '[class*="popup"] button'
        ]
        
        for selector in popup_selectors:
            try:
                close_btns = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in close_btns:
                    if btn.is_displayed():
                        self._safe_click(btn)
                        print(f"✓ Closed popup")
                        break
            except:
                continue
    
    def _scroll_page_gradually(self):
        """Scroll page gradually to load content"""
        print("Scrolling page to load content...")
        
        scroll_height = self.driver.execute_script("return document.body.scrollHeight")
        current_position = 0
        scroll_step = 500
        
        while current_position < scroll_height:
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")
            current_position += scroll_step
            time.sleep(0.5)
        
        # Scroll back to top
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
    
    def save_to_json(self, data, filename):
        """Save data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✓ Data saved to {filename}")
    
    def print_car_list(self, car_data):
        """Print car list to terminal"""
        print("\n" + "="*60)
        print("CAR LIST FOUND:")
        print("="*60)
        
        for idx, car in enumerate(car_data, 1):
            name = car.get('name', 'Unknown')
            year = car.get('year', '')
            if year:
                print(f"{idx:3d}. {name} ({year})")
            else:
                print(f"{idx:3d}. {name}")
        
        print(f"\nTotal cars found: {len(car_data)}")
        print("="*60)
    
    def close(self):
        """Close the browser"""
        try:
            self.driver.quit()
            print("Browser closed")
        except:
            pass