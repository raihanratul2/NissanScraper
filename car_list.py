"""
Nissan USA Car List Scraper - Working File
This script scrapes car list from a provided car build link
"""

import time
import re
from base import NissanScraperBase
from selenium.webdriver.common.by import By


class NissanCarListScraper(NissanScraperBase):
    """Scraper specifically for Nissan car list from build page"""
    
    def __init__(self, headless=False, delay_range=(2, 4)):
        super().__init__(headless, delay_range)
        self.car_data = []
    
    def scrape_car_list_from_link(self, build_link):
        """
        Scrape car list from provided build link
        
        Steps:
        1. Go to provided build link
        2. Find all car product cards
        3. Extract car names (from h3 tag)
        4. Extract page links
        5. Print list in terminal
        6. Save to JSON file
        """
        print(f"\nScraping from link: {build_link}")
        
        try:
            # Step 1: Navigate to build link
            print("\n1. Navigating to build link...")
            self.driver.get(build_link)
            time.sleep(3)  # Initial load
            
            # Handle popups
            self._handle_cookies_popup()
            self._close_popups()
            
            # Step 2: Scroll to load all content
            print("2. Loading page content...")
            self._scroll_page_gradually()
            
            # Step 3: Find all product cards
            print("3. Looking for product cards...")
            
            # Using the exact class you provided
            product_card_selector = '.sc-dyuvay.dHgRuz'
            
            # Wait for cards to load
            time.sleep(2)
            
            # Find all product cards
            product_cards = self.driver.find_elements(By.CSS_SELECTOR, product_card_selector)
            
            if not product_cards:
                print("⚠ No cards found with exact selector, trying alternatives...")
                # Try alternative selectors
                alternative_selectors = [
                    '[class*="product-card"]',
                    '[class*="vehicle-card"]',
                    '.vehicle-item',
                    '.model-card'
                ]
                
                for alt_selector in alternative_selectors:
                    product_cards = self.driver.find_elements(By.CSS_SELECTOR, alt_selector)
                    if product_cards:
                        print(f"✓ Found {len(product_cards)} cards with selector: {alt_selector}")
                        break
            
            print(f"✓ Found {len(product_cards)} product cards")
            
            # Step 4: Extract data from each card
            print("4. Extracting car details...")
            
            self.car_data = []
            
            # Step 4: Extract data from each card
            print("4. Extracting car details...")

            self.car_data = []

            for idx, card in enumerate(product_cards, 1):
                try:
                    car_info = {}
                    car_info['id'] = idx
                    
                    # Scroll to card
                    self._scroll_to_element(card)
                    
                    # A. Extract CAR NAME from h3 tag
                    name_selectors = [
                        'h3.sc-gLaqbQ.eDBrkr.sc-eQwNpu.kogNIX.sc-Goufe.bwIAyQ',  # Your exact class
                        'h3',  # Fallback to any h3
                        '.vehicle-name',
                        '.model-name',
                        '[class*="title"]',
                        '[class*="name"]'
                    ]
                    
                    car_name = ""
                    for selector in name_selectors:
                        try:
                            name_element = card.find_element(By.CSS_SELECTOR, selector)
                            car_name = name_element.text.strip()
                            if car_name:
                                break
                        except:
                            continue
                    
                    if not car_name:
                        car_name = card.text.split('\n')[0] if card.text else f"Car_{idx}"
                    
                    car_info['name'] = car_name
                    
                    # B. Extract YEAR from name if available
                    year_match = re.search(r'(20\d{2})', car_name)
                    if year_match:
                        car_info['year'] = year_match.group(1)
                    else:
                        car_info['year'] = ""
                    
                    # C. Extract PRICE with exact class "sc-clirCP HQxrh"
                    price_selectors = [
                        '.sc-clirCP.HQxrh',  # Your exact price class
                        'span.sc-clirCP.HQxrh',  # As span tag
                        'div.sc-clirCP.HQxrh',  # As div tag
                        '[class*="sc-clirCP"]',  # Partial match
                        '[class*="price"]',  # Fallback
                        '.price',
                        '.msrp',
                        '[data-testid*="price"]'
                    ]
                    
                    price_text = ""
                    for selector in price_selectors:
                        try:
                            price_element = card.find_element(By.CSS_SELECTOR, selector)
                            price_text = price_element.text.strip()
                            if price_text:
                                # Clean price text (remove extra spaces, newlines)
                                price_text = ' '.join(price_text.split())
                                break
                        except:
                            continue
                    
                    car_info['price'] = price_text
                    
                    # D. Extract PAGE LINK
                    link_selectors = [
                        'a.sc-fhHczv.buKfDP.sc-kEjqvK.kDaJzo',  # Your exact class
                        'a[class*="sc-fhHczv"]',  # Partial match
                        'a',  # Fallback to any link
                        '[class*="link"]',
                        '[href*="nissan"]'
                    ]
                    
                    page_link = ""
                    for selector in link_selectors:
                        try:
                            link_element = card.find_element(By.CSS_SELECTOR, selector)
                            href = link_element.get_attribute('href')
                            if href and ('nissan' in href or 'http' in href):
                                page_link = href
                                break
                        except:
                            continue
                    
                    car_info['page_link'] = page_link
                    
                    # E. Extract additional info if available
                    try:
                        # Try to get trim/model info
                        trim_selectors = ['[class*="trim"]', '[class*="model"]', '[class*="variant"]']
                        for selector in trim_selectors:
                            try:
                                trim_element = card.find_element(By.CSS_SELECTOR, selector)
                                trim_text = trim_element.text.strip()
                                if trim_text and len(trim_text) < 50:  # Avoid large texts
                                    car_info['trim'] = trim_text
                                    break
                            except:
                                continue
                    except:
                        pass
                    
                    # Add to list
                    self.car_data.append(car_info)
                    
                    # Print progress with price
                    price_display = f" - {price_text}" if price_text else ""
                    print(f"  ✓ {idx:3d}. {car_name}{price_display}")
                    
                except Exception as e:
                    print(f"  ✗ Error with card {idx}: {str(e)[:50]}")
                    continue
            
            # Step 5: Print list in terminal
            print("\n" + "="*60)
            print("EXTRACTED CAR LIST WITH PRICES:")
            print("="*60)

            for car in self.car_data:
                name = car.get('name', 'Unknown')
                year = car.get('year', '')
                price = car.get('price', 'Price not available')
                link = car.get('page_link', 'No link')
                
                if year and price:
                    print(f"• {name} ({year}) - {price}")
                elif year:
                    print(f"• {name} ({year})")
                elif price and price != 'Price not available':
                    print(f"• {name} - {price}")
                else:
                    print(f"• {name}")
                
                if link and link != 'No link':
                    print(f"  🔗 {link[:80]}...")
                print()
            
            print(f"Total cars extracted: {len(self.car_data)}")
            print("="*60)
            
            # Step 6: Save to JSON
            if self.car_data:
                self.save_to_json(self.car_data, "nissan_car_list.json")
                
                # Also save a simplified version
                # Also save a simplified version
                simplified_data = []
                for car in self.car_data:
                    simplified = {
                        'id': car.get('id'),
                        'name': car.get('name'),
                        'year': car.get('year', ''),
                        'price': car.get('price', ''),
                        'page_link': car.get('page_link', '')
                    }
                    simplified_data.append(simplified)
                
                self.save_to_json(simplified_data, "nissan_cars_simple.json")
                
                # Print summary
                print("\n✓ Scraping completed successfully!")
                print(f"✓ Total cars found: {len(self.car_data)}")
                print("✓ Data saved to: nissan_car_list.json")
                print("✓ Simplified data saved to: nissan_cars_simple.json")
            
            else:
                print("\n⚠ No car data was extracted!")
                
        except Exception as e:
            print(f"\n✗ Error during scraping: {str(e)}")
            
            # Try to save partial data
            if self.car_data:
                print("Saving partial data...")
                self.save_to_json(self.car_data, "nissan_car_list_partial.json")


def main():
    """Main function to run the scraper"""
    print("="*60)
    print("NISSAN USA CAR LIST SCRAPER")
    print("="*60)
    
    # Get build link from user
    print("\nPlease enter the Nissan car build link:")
    print("Example: https://www.nissanusa.com/vehicles/build-price.html")
    print("Or: https://www.nissanusa.com/shopping-tools/build-price.html")
    
    build_link = input("\nEnter link: ").strip()
    
    if not build_link:
        # Default link if none provided
        build_link = "https://www.nissanusa.com/vehicles/build-price.html"
        print(f"\nUsing default link: {build_link}")
    
    # Configuration
    HEADLESS = False  # Set to True to run without browser window
    DELAY_RANGE = (2, 4)  # Delay between actions
    
    # Create scraper instance
    scraper = NissanCarListScraper(headless=HEADLESS, delay_range=DELAY_RANGE)
    
    try:
        # Start scraping
        scraper.scrape_car_list_from_link(build_link)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Scraping interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
    finally:
        # Always close the browser
        scraper.close()
        print("\n" + "="*60)
        print("PROGRAM COMPLETED")
        print("="*60)


if __name__ == "__main__":
    main()