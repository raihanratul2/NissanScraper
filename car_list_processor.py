"""
Car List Processor - Loads car list from JSON and processes each car
WITHOUT CLICKING ANY LINKS
"""

import json
import time
import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException


class CarListProcessor:
    def __init__(self, scraper_instance):
        self.scraper = scraper_instance
        self.driver = scraper_instance.driver
        self.wait = scraper_instance.wait
        self.all_trim_data = []
        self.processed_car_links = set()  # Track processed car links
    
    def load_car_list(self, filename="nissan_car_list.json"):
        """Load car list from JSON file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ File {filename} not found!")
            return []
    
    def process_car_links(self):
        """Process each car link WITHOUT clicking any trim links"""
        car_list = self.load_car_list()
        
        if not car_list:
            print("No car list found. Please run the main scraper first.")
            return
        
        print(f"\n{'='*60}")
        print(f"PROCESSING {len(car_list)} CARS (NO CLICK MODE)")
        print(f"{'='*60}\n")
        
        for idx, car in enumerate(car_list, 1):
            page_link = car.get('page_link')
            
            if not page_link or page_link == 'No link':
                print(f"{idx:3d}. Skipping: {car.get('name')} - No link")
                continue
            
            # Skip if already processed
            if page_link in self.processed_car_links:
                print(f"{idx:3d}. Skipping: {car.get('name')} - Already processed")
                continue
            
            print(f"{idx:3d}. Processing: {car.get('name')}")
            print(f"    Link: {page_link[:80]}...")
            
            # Process the car page WITHOUT clicking any links
            trim_data = self.scrape_car_details_without_clicks(page_link, car)
            
            if trim_data:
                print(f"    ✓ Found {len(trim_data)} trim(s) (no clicks made)")
                self.all_trim_data.extend(trim_data)
                self.processed_car_links.add(page_link)
            else:
                print(f"    ⚠ No trim data found")
            
            print()
        
        # Save all trim data
        if self.all_trim_data:
            self.save_trim_data()
    
    def scrape_car_details_without_clicks(self, page_link, base_car_info):
        """Scrape trim details from car page WITHOUT clicking any links"""
        try:
            # Navigate to car page
            self.driver.get(page_link)
            time.sleep(3)
            
            # Handle popups
            self.scraper._handle_cookies_popup()
            self.scraper._close_popups()
            
            # Scroll to load content (but don't click anything)
            self.scraper._scroll_page_gradually()
            
            # Find all trim cards WITHOUT clicking
            trim_cards = self.find_trim_cards_without_clicks()
            
            if not trim_cards:
                print("      ⚠ No trim cards found, trying alternative selectors...")
                trim_cards = self.find_trim_cards_alternative_without_clicks()
            
            trim_data = []
            
            for card_idx, card in enumerate(trim_cards, 1):
                try:
                    # Extract trim info WITHOUT clicking
                    trim_info = self.extract_trim_info_without_clicks(card, base_car_info, card_idx)
                    if trim_info and self.validate_trim_data(trim_info):
                        trim_data.append(trim_info)
                        print(f"      ✓ Trim {card_idx}: {trim_info.get('trim_name', 'Unknown')}")
                    else:
                        print(f"      ✗ Trim {card_idx}: Failed validation")
                        
                except Exception as e:
                    print(f"      ✗ Error with trim {card_idx}: {str(e)[:50]}")
                    continue
            
            return trim_data
            
        except Exception as e:
            print(f"    ✗ Error processing page: {str(e)[:50]}")
            return []
    
    def find_trim_cards_without_clicks(self):
        """Find trim cards WITHOUT clicking"""
        all_cards = []
        
        # Primary selector from requirements
        primary_selectors = [
            '.sc-hEJUTg.ceCyPE',
            '[class*="trim-card"]',
            '[class*="vehicle-card"]',
            '[data-testid*="trim"]',
            '.vehicle-trim'
        ]
        
        print("      Looking for trim cards (no click mode)...")
        
        for selector in primary_selectors:
            try:
                cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    print(f"      Found {len(cards)} cards with selector: {selector}")
                    
                    validated_cards = []
                    for idx, card in enumerate(cards):
                        if self.is_valid_trim_card_without_clicks(card):
                            validated_cards.append(card)
                            print(f"        Card {idx+1}: Valid")
                        else:
                            print(f"        Card {idx+1}: Invalid - skipping")
                    
                    if validated_cards:
                        print(f"      Valid cards: {len(validated_cards)}")
                        return validated_cards
                        
            except Exception as e:
                print(f"      ⚠ Error with selector {selector}: {e}")
                continue
        
        return []
    
    def find_trim_cards_alternative_without_clicks(self):
        """Find trim cards using alternative selectors WITHOUT clicking"""
        alternative_selectors = [
            '.model-card',
            '.car-card',
            '[class*="card"]',
            '.inventory-item',
            '.product-item',
            '.model-item',
            '.vehicle-item',
            '[class*="sc-hEJUTg"]',
            '[class*="ceCyPE"]'
        ]
        
        for selector in alternative_selectors:
            try:
                cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    print(f"      Found {len(cards)} cards with alternative selector: {selector}")
                    
                    validated_cards = []
                    for card in cards:
                        if self.is_valid_trim_card_without_clicks(card):
                            validated_cards.append(card)
                    
                    if validated_cards:
                        print(f"      Valid alternative cards: {len(validated_cards)}")
                        return validated_cards
                        
            except Exception as e:
                continue
        
        return []
    
    def is_valid_trim_card_without_clicks(self, card):
        """Validate trim card WITHOUT clicking"""
        try:
            # Basic visibility check
            if not card.is_displayed():
                return False
            
            # Get card text
            card_text = card.text.strip()
            if len(card_text) < 10:
                return False
            
            # Check for required elements WITHOUT clicking
            
            # 1. Name element (h3 with specific classes from requirements)
            name_selectors = [
                'h3.sc-gLaqbQ.eDBrkr.sc-eQwNpu.kogNIX.sc-Goufe.bwIAyQ',  # Your exact class
                'h3',  # Fallback
                '.vehicle-name',
                '.model-name',
                '[class*="title"]',
                '[class*="name"]'
            ]
            
            has_name = False
            for selector in name_selectors:
                try:
                    name_elem = card.find_element(By.CSS_SELECTOR, selector)
                    if name_elem.text.strip():
                        has_name = True
                        break
                except:
                    continue
            
            if not has_name:
                return False
            
            # 2. Link element (a tag with specific classes from requirements)
            link_selectors = [
                'a.sc-fhHczv.buKfDP.sc-kEjqvK.kDaJzo',  # Your exact class
                'a[href*="nissan"]',
                'a[href*="build"]',
                'a'
            ]
            
            has_link = False
            for selector in link_selectors:
                try:
                    link_elem = card.find_element(By.CSS_SELECTOR, selector)
                    href = link_elem.get_attribute('href')
                    if href and ('nissan' in href or 'http' in href):
                        has_link = True
                        break
                except:
                    continue
            
            if not has_link:
                return False
            
            # 3. Image element (optional but preferred)
            has_image = False
            try:
                img_elem = card.find_element(By.TAG_NAME, 'img')
                src = img_elem.get_attribute('src')
                if src:
                    has_image = True
            except:
                # Image not required but preferred
                pass
            
            # 4. Price element (optional)
            has_price = False
            price_selectors = [
                '[class*="price"]',
                '.price',
                '.msrp',
                '[class*="Price"]'
            ]
            
            for selector in price_selectors:
                try:
                    price_elem = card.find_element(By.CSS_SELECTOR, selector)
                    if price_elem.text.strip():
                        has_price = True
                        break
                except:
                    continue
            
            # Final validation: Must have name and link, prefer image and price
            return has_name and has_link
            
        except Exception as e:
            print(f"        ⚠ Card validation error: {e}")
            return False
    
    def extract_trim_info_without_clicks(self, card, base_car_info, card_idx):
        """Extract trim info WITHOUT clicking any links"""
        trim_info = base_car_info.copy()
        trim_info['card_index'] = card_idx
        
        try:
            # Generate unique ID for this card
            card_id = self.get_card_unique_id_without_clicks(card)
            trim_info['card_unique_id'] = card_id
            
            # 1. Extract CAR NAME from h3 tag
            name_selectors = [
                'h3.sc-gLaqbQ.eDBrkr.sc-eQwNpu.kogNIX.sc-Goufe.bwIAyQ',
                'h3',
                '.vehicle-name',
                '.model-name',
                '[class*="title"]',
                '[class*="name"]'
            ]
            
            car_name = ""
            model_name = ""
            trim_name = ""
            
            for selector in name_selectors:
                try:
                    name_element = card.find_element(By.CSS_SELECTOR, selector)
                    car_name = name_element.text.strip()
                    if car_name:
                        # Try to separate model and trim names
                        # Pattern: "2024 Nissan Altima S"
                        match = re.match(r'(\d{4})\s+(.+?)\s+(.+)', car_name)
                        if match:
                            trim_info['year'] = match.group(1)
                            model_name = match.group(2)
                            trim_name = match.group(3)
                        else:
                            # Try other patterns
                            parts = car_name.split()
                            if len(parts) >= 3:
                                if parts[0].isdigit() and len(parts[0]) == 4:
                                    trim_info['year'] = parts[0]
                                    model_name = ' '.join(parts[1:-1])
                                    trim_name = parts[-1]
                                else:
                                    model_name = ' '.join(parts[:-1])
                                    trim_name = parts[-1]
                            elif len(parts) == 2:
                                model_name = parts[0]
                                trim_name = parts[1]
                        
                        break
                except:
                    continue
            
            if not car_name:
                # Get any text from card
                car_name = card.text.split('\n')[0] if card.text else f"Car_{card_idx}"
            
            trim_info['car_name'] = car_name
            trim_info['model_name'] = model_name or base_car_info.get('name', '')
            trim_info['trim_name'] = trim_name or f"Trim_{card_idx}"
            
            # Extract year from name if available
            if 'year' not in trim_info:
                year_match = re.search(r'(20\d{2})', car_name)
                if year_match:
                    trim_info['year'] = year_match.group(1)
            
            # 2. Extract PAGE LINK (NO CLICKING)
            link_selectors = [
                'a.sc-fhHczv.buKfDP.sc-kEjqvK.kDaJzo',
                'a[class*="sc-fhHczv"]',
                'a[href*="nissan"]',
                'a[href]'
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
            
            trim_info['page_link'] = page_link
            
            # 3. Extract IMAGE URL (NO CLICKING)
            try:
                img_selectors = [
                    'img.sc-cdmAjP',  # Your exact class
                    'img',
                    '[class*="image"] img',
                    'picture img'
                ]
                
                for selector in img_selectors:
                    try:
                        img_element = card.find_element(By.CSS_SELECTOR, selector)
                        src = img_element.get_attribute('src')
                        srcset = img_element.get_attribute('srcset')
                        
                        if src:
                            trim_info['image_url'] = src
                            break
                        elif srcset:
                            # Take first image from srcset
                            first_img = srcset.split(',')[0].split(' ')[0]
                            trim_info['image_url'] = first_img
                            break
                    except:
                        continue
                
                if 'image_url' not in trim_info:
                    trim_info['image_url'] = ""
            except:
                trim_info['image_url'] = ""
            
            # 4. Extract PRICE (NO CLICKING)
            price_selectors = [
                '.sc-clirCP.HQxrh',  # Your exact price class
                '[class*="price"]',
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
                        # Clean price text
                        price_text = ' '.join(price_text.split())
                        break
                except:
                    continue
            
            trim_info['price'] = price_text
            
            # 5. Extract additional info if visible
            try:
                # Try to get drivetrain info if visible
                drivetrain_selectors = [
                    '[class*="drivetrain"]',
                    '[class*="engine"]',
                    '[class*="spec"]'
                ]
                
                for selector in drivetrain_selectors:
                    try:
                        spec_element = card.find_element(By.CSS_SELECTOR, selector)
                        spec_text = spec_element.text.strip()
                        if spec_text and len(spec_text) < 50:
                            trim_info['specs'] = spec_text
                            break
                    except:
                        continue
            except:
                pass
            
            return trim_info
            
        except Exception as e:
            print(f"      ✗ Error extracting trim info: {str(e)[:50]}")
            return None
    
    def get_card_unique_id_without_clicks(self, card):
        """Generate unique ID for card based on visible attributes (NO CLICKING)"""
        id_parts = []
        
        try:
            # 1. Try data-testid
            data_testid = card.get_attribute('data-testid')
            if data_testid:
                id_parts.append(f"testid:{data_testid}")
            
            # 2. Try id attribute
            elem_id = card.get_attribute('id')
            if elem_id:
                id_parts.append(f"id:{elem_id}")
            
            # 3. Try data-id
            data_id = card.get_attribute('data-id')
            if data_id:
                id_parts.append(f"data-id:{data_id}")
            
            # 4. Use visible text content (first 2 lines)
            card_text = card.text.strip()
            lines = [line.strip() for line in card_text.split('\n') if line.strip()]
            if lines:
                # Use first 2 meaningful lines, max 50 chars
                text_id = '_'.join(lines[:2])[:50]
                id_parts.append(f"text:{hash(text_id)}")
            
            # 5. Use classes
            classes = card.get_attribute('class') or ''
            if classes:
                # Filter out generic classes
                specific_classes = [cls for cls in classes.split() 
                                  if len(cls) > 3]
                if specific_classes:
                    id_parts.append(f"class:{hash('_'.join(specific_classes[:2]))}")
            
            # 6. Use position (as fallback)
            try:
                location = card.location
                id_parts.append(f"pos:{int(location['x'])}_{int(location['y'])}")
            except:
                pass
            
            return '|'.join(id_parts) if id_parts else f"card_{time.time()}"
            
        except:
            return f"card_{time.time()}"
    
    def validate_trim_data(self, trim_info):
        """Validate that trim data has required fields"""
        required_fields = ['car_name', 'page_link']
        
        for field in required_fields:
            if not trim_info.get(field):
                print(f"        ⚠ Missing required field: {field}")
                return False
        
        # Validate link format
        page_link = trim_info.get('page_link', '')
        if not page_link.startswith('http'):
            print(f"        ⚠ Invalid link format: {page_link}")
            return False
        
        # Validate name
        car_name = trim_info.get('car_name', '')
        if len(car_name) < 3:
            print(f"        ⚠ Car name too short: {car_name}")
            return False
        
        return True
    
    def save_trim_data(self):
        """Save all trim data to JSON file"""
        if not self.all_trim_data:
            print("No trim data to save!")
            return
        
        # Save detailed data
        self.scraper.save_to_json(self.all_trim_data, "nissan_trims_detailed.json")
        
        # Save simplified version with validation
        simplified_data = []
        
        for trim in self.all_trim_data:
            # Only include validated data
            if self.validate_trim_data(trim):
                simple_trim = {
                    'id': trim.get('id'),
                    'car_name': trim.get('car_name', ''),
                    'model_name': trim.get('model_name', ''),
                    'trim_name': trim.get('trim_name', ''),
                    'year': trim.get('year', ''),
                    'price': trim.get('price', ''),
                    'page_link': trim.get('page_link', ''),
                    'image_url': trim.get('image_url', ''),
                    'specs': trim.get('specs', ''),
                    'card_unique_id': trim.get('card_unique_id', '')
                }
                
                # Validate each field is not empty where required
                if simple_trim['car_name'] and simple_trim['page_link']:
                    simplified_data.append(simple_trim)
        
        self.scraper.save_to_json(simplified_data, "nissan_trims_simple.json")
        
        print(f"\n{'='*60}")
        print("TRIM PROCESSING COMPLETE (NO CLICK MODE)")
        print(f"{'='*60}")
        print(f"✓ Total cards processed: {len(self.all_trim_data)}")
        print(f"✓ Validated trims saved: {len(simplified_data)}")
        print(f"✓ Detailed data saved to: nissan_trims_detailed.json")
        print(f"✓ Simplified data saved to: nissan_trims_simple.json")
        print(f"✓ No links were clicked during processing")
        print(f"{'='*60}")
        
        # Print validation summary
        self.print_validation_summary()
        
        # Open build instructions file
        self.show_build_instructions()
    
    def print_validation_summary(self):
        """Print validation summary"""
        print("\n📊 VALIDATION SUMMARY:")
        print("-" * 40)
        
        total = len(self.all_trim_data)
        with_name = sum(1 for t in self.all_trim_data if t.get('car_name'))
        with_link = sum(1 for t in self.all_trim_data if t.get('page_link'))
        with_image = sum(1 for t in self.all_trim_data if t.get('image_url'))
        with_price = sum(1 for t in self.all_trim_data if t.get('price'))
        
        print(f"Total trims found: {total}")
        print(f"With valid name: {with_name} ({with_name/total*100:.1f}%)")
        print(f"With valid link: {with_link} ({with_link/total*100:.1f}%)")
        print(f"With image URL: {with_image} ({with_image/total*100:.1f}%)")
        print(f"With price info: {with_price} ({with_price/total*100:.1f}%)")
        print("-" * 40)
    
    def show_build_instructions(self):
        """Display build instructions"""
        print("\n📋 BUILD CONFIGURATION INSTRUCTIONS:")
        print("="*60)
        print("1. Open 'build_configurator.py' to continue with build process")
        print("2. The script will:")
        print("   - Load trim data from 'nissan_trims_simple.json'")
        print("   - Process each build configuration")
        print("   - Extract detailed options and packages")
        print("3. Run: python build_configurator.py")
        print("="*60)