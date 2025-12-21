"""
Build Configurator - Processes ONLY main section of build pages
Uses ESC key for popup closing, skips prohibited buttons
Now extracts ALL specified items from requirements
"""

import json
import time
import re
from typing import Dict, List, Optional, Set
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from base import NissanScraperBase


class BuildConfigurator(NissanScraperBase):
    def __init__(self, headless: bool = False):
        super().__init__(headless)
        self.configurations: List[Dict] = []
        self.processed_button_ids: Set[str] = set()
        
        # Prohibited content - buttons containing these texts will NOT be clicked
        self.prohibited_contents = [
            "change trim", "compare", "share", "save", "print", "email",
            "dealer", "inventory", "contact", "chat", "help", "support",
            "faq", "legal", "privacy", "terms", "cookie", "feedback"
        ]
    
    def load_trim_data(self, filename: str = "nissan_trims_simple.json") -> List[Dict]:
        """Load trim data from JSON file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ File {filename} not found!")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            return []
    
    def process_build_configurations(self) -> None:
        """Process ONLY main section of build configurations"""
        trim_data = self.load_trim_data()
        
        if not trim_data:
            print("No trim data found. Please run car_list_processor.py first.")
            return
        
        self.print_banner()
        
        successful = 0
        failed = 0
        
        for idx, trim in enumerate(trim_data, 1):
            build_link = trim.get('page_link')
            
            if not build_link:
                print(f"{idx:3d}. Skipping: {trim.get('car_name', 'Unknown')} - No build link")
                failed += 1
                continue
            
            self.print_processing_info(idx, trim, build_link)
            
            # Reset for each trim
            self.processed_button_ids.clear()
            
            # Process ONLY main section
            config_data = self.scrape_main_section_only(build_link, trim)
            
            if config_data:
                self.configurations.append(config_data)
                successful += 1
                print(f"    ✓ All specified items extracted")
            else:
                failed += 1
                print(f"    ⚠ Failed to extract main section")
            
            print()
        
        # Save configurations
        if self.configurations:
            self.save_configurations()
        
        self.print_summary(successful, failed)
    
    def print_banner(self) -> None:
        """Print program banner"""
        separator = "=" * 60
        print(f"\n{separator}")
        print("MAIN SECTION BUILD CONFIGURATOR - COMPLETE")
        print(separator)
        print("Now extracts ALL specified items:")
        print("1. Main Vehicle Display Section")
        print("2. Navigation Tabs (disabled)")
        print("3. 360° Car Rotator")
        print(separator)
        print("Rules:")
        print("• Processes ONLY main section (no navigation)")
        print("• Uses ESC key for popup closing")
        print("• Skips prohibited buttons")
        print("• No section navigation")
        print(separator)
        print()
    
    def print_processing_info(self, idx: int, trim: Dict, build_link: str) -> None:
        """Print processing information"""
        car_name = trim.get('car_name', 'Unknown')
        truncated_link = build_link[:80] + "..." if len(build_link) > 80 else build_link
        print(f"{idx:3d}. Processing: {car_name}")
        print(f"    Link: {truncated_link}")
    
    def print_summary(self, successful: int, failed: int) -> None:
        """Print processing summary"""
        separator = "=" * 60
        print(f"\n{separator}")
        print("PROCESSING SUMMARY")
        print(separator)
        print(f"✓ Successful: {successful}")
        print(f"✗ Failed: {failed}")
        print(f"Total: {successful + failed}")
        print(separator)

    def find_accessories_containers_alternative(self) -> List[WebElement]:
        """Alternative method to find accessories containers"""
        containers = []
        
        try:
            # Method 1: Look for containers with specific data attributes
            data_containers = self.driver.find_elements(
                By.CSS_SELECTOR, '[data-testid*="accessor"], [data-testid*="option"]'
            )
            containers.extend(data_containers)
            
            # Method 2: Look for containers with specific text patterns
            all_divs = self.driver.find_elements(By.CSS_SELECTOR, 'div')
            for div in all_divs:
                try:
                    if div.is_displayed():
                        div_text = div.text.strip().lower()
                        div_class = div.get_attribute('class') or ''
                        
                        # Check for accessories keywords in text or class
                        accessories_keywords = ['accessor', 'option', 'add-on', 'extra', 'feature']
                        
                        if any(keyword in div_text or keyword in div_class 
                               for keyword in accessories_keywords):
                            # Check if it has buttons inside
                            buttons_inside = div.find_elements(By.CSS_SELECTOR, 'button')
                            if buttons_inside:
                                containers.append(div)
                except:
                    continue
            
            # Remove duplicates
            unique_containers = self._remove_duplicate_elements(containers)
            return unique_containers
            
        except Exception as e:
            print(f"          ⚠ Alternative container search error: {e}")
            return []

    def _remove_duplicate_elements(self, elements: List[WebElement]) -> List[WebElement]:
        """Remove duplicate web elements based on location"""
        unique_elements = []
        seen = set()
        
        for element in elements:
            try:
                container_id = f"{element.location['x']}_{element.location['y']}"
                if container_id not in seen:
                    seen.add(container_id)
                    unique_elements.append(element)
            except:
                unique_elements.append(element)
        
        return unique_elements

    def click_accessories_section_buttons(self) -> Dict:
        """Click all buttons in accessories section containers"""
        accessories_results = {
            'total_containers_found': 0,
            'buttons_clicked': 0,
            'buttons_failed': 0,
            'containers_processed': 0,
            'details': []
        }
        
        try:
            print("        Looking for accessories containers...")
            
            # Find containers using multiple selectors
            all_containers = self._find_containers_with_selectors([
                'div.sc-CezhS.kLWQDy',
                'div[class*="sc-CezhS"]',
                'div[class*="accessor"]',
                '.accessories-container',
                '.options-container'
            ])
            
            # Also try alternative method
            if not all_containers:
                print(f"        No containers found with primary selectors, trying alternatives...")
                all_containers = self.find_accessories_containers_alternative()
            
            # Remove duplicates
            unique_containers = self._remove_duplicate_elements(all_containers)
            accessories_results['total_containers_found'] = len(unique_containers)
            print(f"        Total unique containers found: {len(unique_containers)}")
            
            # Process each container
            for idx, container in enumerate(unique_containers, 1):
                if not container.is_displayed():
                    continue
                
                container_info = self._process_single_container(idx, container, accessories_results)
                accessories_results['details'].append(container_info)
            
            self._print_accessories_results(accessories_results)
            
        except Exception as e:
            print(f"        ⚠ Error in accessories clicking: {e}")
            accessories_results['error'] = str(e)
        
        return accessories_results
    
    def _find_containers_with_selectors(self, selectors: List[str]) -> List[WebElement]:
        """Find containers using multiple CSS selectors"""
        all_containers = []
        
        for selector in selectors:
            try:
                containers = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if containers:
                    all_containers.extend(containers)
                    print(f"        Found {len(containers)} containers with selector: {selector}")
            except:
                continue
        
        return all_containers
    
    def _process_single_container(self, idx: int, container: WebElement, 
                                 accessories_results: Dict) -> Dict:
        """Process a single container"""
        container_info = {
            'container_index': idx,
            'location': container.location,
            'size': container.size,
            'class': container.get_attribute('class') or '',
            'buttons_found': 0,
            'buttons_clicked': 0
        }
        
        print(f"        Processing container {idx}...")
        
        try:
            # Find buttons in container
            buttons = self._find_buttons_in_container(container)
            container_info['buttons_found'] = len(buttons)
            
            # Click first button
            if buttons:
                first_button = buttons[0]
                self._click_first_button(first_button, container_info, accessories_results)
            else:
                print(f"          No buttons found in container")
                
        except Exception as e:
            print(f"          ⚠ Error processing container: {e}")
            container_info['error'] = str(e)
        
        return container_info
    
    def _find_buttons_in_container(self, container: WebElement) -> List[WebElement]:
        """Find buttons within a container"""
        buttons = container.find_elements(By.CSS_SELECTOR, 'button')
        
        if not buttons:
            # Try alternative button selectors
            button_selectors = [
                '[role="button"]',
                '.btn',
                '.button',
                'a[href="#"]',
                'div[onclick]'
            ]
            
            for btn_selector in button_selectors:
                try:
                    buttons = container.find_elements(By.CSS_SELECTOR, btn_selector)
                    if buttons:
                        break
                except:
                    continue
        
        return buttons
    
    def _click_first_button(self, button: WebElement, container_info: Dict, 
                           accessories_results: Dict) -> None:
        """Click the first button in a container"""
        if not button.is_displayed() or not button.is_enabled():
            print(f"          ⚠ First button not clickable")
            return
        
        button_text = button.text.strip()[:30] or "No text"
        print(f"          Clicking first button: '{button_text}'")
        
        # Scroll to button
        self._scroll_to_element(button)
        time.sleep(0.5)
        
        # Try to click
        clicked = self._safe_click_element(button)
        
        if clicked:
            container_info['buttons_clicked'] += 1
            accessories_results['buttons_clicked'] += 1
            accessories_results['containers_processed'] += 1
            
            # Wait for popup/modal to appear
            time.sleep(1)
            
            # Try to close any popup with ESC
            self.close_popup_with_esc()
            
            # Wait before next click
            time.sleep(0.5)
        else:
            accessories_results['buttons_failed'] += 1
            print(f"          ⚠ Failed to click button")
    
    def _safe_click_element(self, element: WebElement) -> bool:
        """Safely click an element"""
        try:
            element.click()
            return True
        except:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except:
                return False
    
    def _print_accessories_results(self, accessories_results: Dict) -> None:
        """Print accessories clicking results"""
        print(f"        Accessories clicking complete: "
              f"{accessories_results['buttons_clicked']} clicked, "
              f"{accessories_results['buttons_failed']} failed")
    
    def scrape_main_section_only(self, build_link: str, trim_info: Dict) -> Optional[Dict]:
        """Scrape ONLY the main section without navigation"""
        config_data = trim_info.copy()
        
        try:
            # Navigate to build page
            print("      Navigating to build page...")
            self.driver.get(build_link)
            time.sleep(4)
            
            # Handle initial popups with ESC key
            self.handle_initial_popups()
            
            # Wait for main content
            self.wait_for_main_content()
            
            # Get viewport dimensions
            viewport_height = self.driver.execute_script("return window.innerHeight")
            main_section_height = int(viewport_height * 0.8)
            
            print(f"      Viewport: {viewport_height}px, Main section: {main_section_height}px")
            
            # Process accessories section first
            print("      Processing accessories section first...")
            accessories_results = self.click_accessories_section_buttons()
            config_data['accessories_clicking'] = accessories_results
            
            # Wait for page to stabilize
            time.sleep(2)
            
            # Extract ALL specified items from main section
            main_section_data = self.extract_complete_main_section()
            config_data.update(main_section_data)
            
            # Find and click other buttons in main section ONLY
            click_results = self.click_main_section_buttons(main_section_height)
            
            # Extract data after clicking
            time.sleep(2)
            updated_data = self.extract_complete_main_section()
            config_data['after_clicking'] = updated_data
            
            # Add click statistics
            config_data['click_statistics'] = click_results
            
            # Take screenshot of main section
            screenshot_name = self._take_screenshot(trim_info)
            config_data['screenshot'] = screenshot_name
            
            print(f"      ✓ Main section processing complete")
            return config_data
            
        except Exception as e:
            print(f"    ✗ Error processing main section: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
            return None
    
    def _take_screenshot(self, trim_info: Dict) -> str:
        """Take screenshot of main section"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_name = f"main_section_{trim_info.get('id', '0')}_{timestamp}.png"
        self.driver.save_screenshot(screenshot_name)
        return screenshot_name
    
    def handle_initial_popups(self) -> None:
        """Handle initial popups with ESC key"""
        try:
            # Try ESC key first
            print("      Pressing ESC to close any popups...")
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ESCAPE)
            time.sleep(1)
            
            # Also try common close buttons
            self._try_close_buttons([
                'button.close',
                '.close-button',
                '[aria-label="Close"]',
                '[class*="close"]'
            ])
                    
        except Exception as e:
            print(f"      ⚠ Error handling popups: {e}")
    
    def _try_close_buttons(self, selectors: List[str]) -> None:
        """Try to click close buttons with given selectors"""
        for selector in selectors:
            try:
                if "contains" in selector:
                    text = selector.split('contains("')[1].split('")')[0]
                    buttons = self.driver.find_elements(
                        By.XPATH, f'//button[contains(text(), "{text}")]'
                    )
                else:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for button in buttons:
                    if button.is_displayed():
                        self._safe_click(button)
                        print(f"      Closed popup with: {selector}")
                        time.sleep(1)
                        break
            except:
                continue

    def wait_for_main_content(self) -> None:
        """Wait for main content to load"""
        try:
            # Wait for main content indicators
            main_content_selectors = [
                'main',
                '#main',
                '.main-content',
                '[role="main"]',
                'p[data-testid="NGST_QA_mainstage_vehicle"]',
                '.build-configurator'
            ]
            
            for selector in main_content_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"      ✓ Main content loaded: {selector}")
                    return
                except:
                    continue
            
            # If no specific selector found, wait for body
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            print(f"      ✓ Page loaded")
            
        except Exception as e:
            print(f"      ⚠ Error waiting for main content: {e}")

    def extract_detailed_feature_data(self) -> Dict:
        """Extract detailed data after clicking on a feature section"""
        detailed_data = {
            'expanded_content': [],
            'options_list': [],
            'prices': [],
            'images': [],
            'specifications': []
        }
        
        # Look for expanded content/panels
        detailed_data['expanded_content'] = self._extract_expanded_content()
        
        # Look for options list
        detailed_data['options_list'] = self._extract_options_list()
        
        # Look for prices
        detailed_data['prices'] = self._extract_prices()
        
        # Look for images
        detailed_data['images'] = self._extract_images()
        
        # Look for specifications
        detailed_data['specifications'] = self._extract_specifications()
        
        print(f"          Found: {len(detailed_data['expanded_content'])} expanded items, "
              f"{len(detailed_data['options_list'])} options")
        
        return detailed_data
    
    def _extract_expanded_content(self) -> List[str]:
        """Extract expanded content/panels"""
        expanded_content = []
        expanded_selectors = [
            '.expanded-content',
            '.details-panel',
            '.modal-content',
            '.popup-content',
            '[role="dialog"]',
            '.sc-bdVaJa.cfGLTe'  # Specific class for expanded content
        ]
        
        for selector in expanded_selectors:
            try:
                expanded_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in expanded_elements:
                    if element.is_displayed():
                        text = element.text.strip()
                        if text:
                            expanded_content.append(text)
            except:
                continue
        
        return expanded_content
    
    def _extract_options_list(self) -> List[str]:
        """Extract options list"""
        options = []
        try:
            list_items = self.driver.find_elements(
                By.CSS_SELECTOR, 'li, .option-item, .choice-item'
            )
            for item in list_items:
                if item.is_displayed():
                    item_text = item.text.strip()
                    if item_text:
                        options.append(item_text)
        except:
            pass
        
        return options
    
    def _extract_prices(self) -> List[str]:
        """Extract price information"""
        prices = []
        try:
            price_elements = self.driver.find_elements(
                By.CSS_SELECTOR, '[class*="price"], [class*="Price"], .sc-gLaqbQ'
            )
            for element in price_elements:
                if element.is_displayed():
                    price_text = element.text.strip()
                    if any(currency in price_text for currency in ['$', '€', '£']):
                        prices.append(price_text)
        except:
            pass
        
        return prices
    
    def _extract_images(self) -> List[Dict]:
        """Extract image information"""
        images = []
        try:
            img_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 'img[src*="color"], img[alt*="color"], img[alt*="interior"]'
            )
            for img in img_elements:
                if img.is_displayed():
                    img_info = {
                        'src': img.get_attribute('src') or '',
                        'alt': img.get_attribute('alt') or ''
                    }
                    if img_info['src']:
                        images.append(img_info)
        except:
            pass
        
        return images
    
    def _extract_specifications(self) -> List[str]:
        """Extract specification information"""
        specifications = []
        try:
            spec_rows = self.driver.find_elements(
                By.CSS_SELECTOR, 'tr, .spec-row, .detail-row'
            )
            for row in spec_rows:
                if row.is_displayed():
                    row_text = row.text.strip()
                    if row_text and len(row_text.split('\n')) >= 2:
                        specifications.append(row_text)
        except:
            pass
        
        return specifications
    
    def click_and_extract_feature_section(self, title_element: WebElement) -> Dict:
        """Click on a feature section and extract detailed data"""
        detailed_data = {}
        
        try:
            # Scroll to the section
            self._scroll_to_element(title_element)
            time.sleep(0.5)
            
            # Find clickable elements in this section
            clicked_successfully = self._click_feature_element(title_element)
            
            # If clicked successfully, extract the detailed data
            if clicked_successfully:
                detailed_data = self.extract_detailed_feature_data()
            
        except Exception as e:
            print(f"          ⚠ Error clicking feature section: {e}")
        
        return detailed_data
    
    def _click_feature_element(self, title_element: WebElement) -> bool:
        """Try to click on feature elements"""
        clickable_selectors = [
            'div[data-testid="NGST_QA_rail_section"]',
            '.feature-item',
            '.spec-item',
            'div.sc-12670f55-3',  # Specific class for feature items
            'div[class*="feature"]',
            'div[class*="spec"]'
        ]
        
        for selector in clickable_selectors:
            try:
                parent = title_element.find_element(By.XPATH, '..')
                clickable_elements = parent.find_elements(By.CSS_SELECTOR, selector)
                
                for element in clickable_elements:
                    if element.is_displayed() and element.is_enabled():
                        print(f"          Clicking on element...")
                        
                        # Try to click
                        try:
                            element.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", element)
                        
                        time.sleep(2)  # Wait for data to load
                        return True
                        
            except:
                continue
        
        # Try clicking the title itself
        try:
            title_element.click()
            time.sleep(2)
            return True
        except:
            return False

    def extract_features_with_clicking(self) -> List[Dict]:
        """Extract features by clicking on each section"""
        features_data = []
        
        try:
            section_titles = self.driver.find_elements(
                By.CSS_SELECTOR, 'h2.sc-12670f55-5.iPnYKV'
            )
            
            print(f"        Found {len(section_titles)} feature sections")
            
            for idx, title in enumerate(section_titles, 1):
                if not title.is_displayed():
                    continue
                    
                section_name = title.text.strip()
                print(f"        [{idx}] Processing section: {section_name}")
                
                section_info = self._process_feature_section(idx, title, section_name)
                features_data.append(section_info)
                
                # Close popup if exists
                self.close_popup_with_esc()
                time.sleep(1)
        
        except Exception as e:
            print(f"      ⚠ Error extracting features: {e}")
        
        return features_data
    
    def _process_feature_section(self, idx: int, title: WebElement, 
                                section_name: str) -> Dict:
        """Process a single feature section"""
        section_info = {
            'section': section_name,
            'basic_info': '',
            'clicked_data': {}
        }
        
        # Get basic info before clicking
        section_info['basic_info'] = self._get_basic_feature_info(title)
        
        # Click on section and get detailed data
        clicked_data = self.click_and_extract_feature_section(title)
        if clicked_data:
            section_info['clicked_data'] = clicked_data
        
        return section_info
    
    def _get_basic_feature_info(self, title: WebElement) -> str:
        """Get basic feature information before clicking"""
        try:
            parent = title.find_element(By.XPATH, '..')
            feature_items = parent.find_elements(
                By.CSS_SELECTOR, 'div[data-testid="NGST_QA_rail_section"] > *'
            )
            
            basic_texts = []
            for item in feature_items:
                if item.is_displayed():
                    item_text = item.text.strip()
                    if item_text:
                        basic_texts.append(item_text)
            
            return '\n'.join(basic_texts)
                        
        except Exception as e:
            print(f"          ⚠ Error getting basic info: {e}")
            return ""
    
    def extract_complete_main_section(self) -> Dict:
        """Extract ALL specified items from main section"""
        main_data = {
            'vehicle_display': {},
            'car_rotator': {},
            'vehicle_info': {},
            'current_selections': [],
            'available_options': [],
            'pricing': {},
            'features': []
        }
        
        try:
            print("      Extracting vehicle display section...")
            main_data['vehicle_display'] = self.extract_vehicle_display()
            
            print("      Extracting car rotator...")
            main_data['car_rotator'] = self.extract_car_rotator()
            
            main_data['vehicle_info'] = self._extract_vehicle_info()
            
            print("      Extracting features (with clicking)...")
            main_data['features'] = self.extract_features_with_clicking()
            
            main_data['available_options'] = self._extract_available_options()
            
            main_data['pricing'] = self._extract_pricing_info()
            
            main_data['current_selections'] = self._extract_current_selections()
            
            self._print_extraction_summary(main_data)
            
        except Exception as e:
            print(f"      ⚠ Error extracting main section: {e}")
        
        return main_data
    
    def _extract_vehicle_info(self) -> Dict:
        """Extract vehicle information"""
        vehicle_info = {}
        
        # Vehicle Model Name
        try:
            vehicle_model = self.driver.find_element(
                By.CSS_SELECTOR, 'p[data-testid="NGST_QA_mainstage_vehicle"]'
            )
            vehicle_info['model'] = vehicle_model.text.strip()
        except:
            vehicle_info['model'] = "Not found"
        
        # Current Trim Name
        try:
            trim_name = self.driver.find_element(
                By.CSS_SELECTOR, 'p.sc-eQwNpu.kLGtky.sc-d4bdcb3-1.hplpik'
            )
            vehicle_info['trim'] = trim_name.text.strip()
        except:
            try:
                trim_name = self.driver.find_element(
                    By.CSS_SELECTOR, 'p.sc-d4bdcb3-1.hplpik'
                )
                vehicle_info['trim'] = trim_name.text.strip()
            except:
                vehicle_info['trim'] = "Not found"
        
        return vehicle_info
    
    def _extract_available_options(self) -> List[Dict]:
        """Extract available options"""
        options = []
        
        try:
            categories = self.driver.find_elements(
                By.CSS_SELECTOR, 'span.sc-a64f1049-14.gyxydV'
            )
            
            for category in categories:
                if category.is_displayed():
                    category_name = category.text.strip()
                    
                    parent = category.find_element(By.XPATH, '../..')
                    option_titles = parent.find_elements(
                        By.CSS_SELECTOR, 'p.sc-a64f1049-0.eVBtpM'
                    )
                    
                    for title in option_titles:
                        if title.is_displayed():
                            option_name = title.text.strip()
                            option_price = self.find_option_price_near_element(title)
                            
                            options.append({
                                'category': category_name,
                                'name': option_name,
                                'price': option_price
                            })
        except:
            pass
        
        return options
    
    def _extract_pricing_info(self) -> Dict:
        """Extract pricing information"""
        pricing = {}
        
        try:
            label_elem = self.driver.find_element(
                By.CSS_SELECTOR, 'p.sc-ad50de1b-5.gLhmbt'
            )
            pricing['label'] = label_elem.text.strip()
        except:
            pricing['label'] = "MSRP"
        
        try:
            amount_elem = self.driver.find_element(
                By.CSS_SELECTOR, 'p.sc-ad50de1b-6.fFhJKT'
            )
            pricing['amount'] = amount_elem.text.strip()
        except:
            pricing['amount'] = "Not found"
        
        return pricing
    
    def _extract_current_selections(self) -> List[str]:
        """Extract current selections"""
        selections = []
        
        try:
            selected_elements = self.driver.find_elements(
                By.CSS_SELECTOR, '.selected, [aria-selected="true"], [data-selected="true"]'
            )
            
            for element in selected_elements:
                if element.is_displayed():
                    text = element.text.strip()
                    if text:
                        selections.append(text)
        except:
            pass
        
        return selections
    
    def _print_extraction_summary(self, main_data: Dict) -> None:
        """Print extraction summary"""
        print(f"      Summary: {len(main_data['vehicle_display'])} display items, "
              f"{len(main_data['features'])} features, "
              f"{len(main_data['available_options'])} options")
    
    def extract_vehicle_display(self) -> Dict:
        """Extract Main Vehicle Display Section"""
        vehicle_display = {
            'model_name': '',
            'trim_level': '',
            'change_trim_button': {},
            'elements_found': 0
        }
        
        # 1. Vehicle Model/Trim
        vehicle_display['model_name'] = self._extract_model_name()
        if vehicle_display['model_name'] != "Not found":
            vehicle_display['elements_found'] += 1
        
        # 2. Trim Level
        vehicle_display['trim_level'] = self._extract_trim_level()
        if vehicle_display['trim_level'] != "Not found":
            vehicle_display['elements_found'] += 1
        
        # 3. Change Trim Button
        vehicle_display['change_trim_button'] = self._extract_change_trim_button()
        if vehicle_display['change_trim_button'].get('exists', True):
            vehicle_display['elements_found'] += 1
        
        return vehicle_display
    
    def _extract_model_name(self) -> str:
        """Extract vehicle model name"""
        try:
            model_element = self.driver.find_element(
                By.CSS_SELECTOR, 'p[data-testid="NGST_QA_mainstage_vehicle"]'
            )
            return model_element.text.strip()
        except:
            return "Not found"
    
    def _extract_trim_level(self) -> str:
        """Extract trim level"""
        try:
            trim_element = self.driver.find_element(
                By.CSS_SELECTOR, 'p.sc-eQwNpu.kLGtky.sc-d4bdcb3-1.hplpik'
            )
            return trim_element.text.strip()
        except:
            try:
                trim_element = self.driver.find_element(
                    By.CSS_SELECTOR, 'p.sc-d4bdcb3-1.hplpik'
                )
                return trim_element.text.strip()
            except:
                return "Not found"
    
    def _extract_change_trim_button(self) -> Dict:
        """Extract change trim button information"""
        try:
            change_trim_button = self.driver.find_element(
                By.CSS_SELECTOR, 'button[data-testid="NGST_QA_change_trim_button"]'
            )
            
            return {
                'text': change_trim_button.text.strip(),
                'is_displayed': change_trim_button.is_displayed(),
                'is_enabled': change_trim_button.is_enabled(),
                'location': change_trim_button.location,
                'size': change_trim_button.size
            }
        except:
            return {
                'exists': False,
                'message': "Change trim button not found"
            }
    
    def extract_car_rotator(self) -> Dict:
        """Extract 360° Car Rotator"""
        rotator_data = {
            'exists': False,
            'car_images': [],
            'current_image': {},
            'total_images': 0,
            'car_rotate_container': {}
        }
        
        # 1. Car Images Container
        rotator_data['car_rotate_container'] = self._extract_car_rotate_container()
        if rotator_data['car_rotate_container']['exists']:
            rotator_data['exists'] = True
        
        # 2. Individual Car Angles
        self._extract_car_angles(rotator_data)
        
        return rotator_data
    
    def _extract_car_rotate_container(self) -> Dict:
        """Extract car rotate container"""
        try:
            car_rotate_container = self.driver.find_element(
                By.CSS_SELECTOR, 'div.car_rotate'
            )
            
            return {
                'exists': True,
                'is_displayed': car_rotate_container.is_displayed(),
                'location': car_rotate_container.location,
                'size': car_rotate_container.size,
                'class': car_rotate_container.get_attribute('class') or ''
            }
        except:
            return {
                'exists': False,
                'message': "Car rotate container not found"
            }
    
    def _extract_car_angles(self, rotator_data: Dict) -> None:
        """Extract car angle images"""
        try:
            car_angles = self.driver.find_elements(
                By.CSS_SELECTOR, 'div.sc-bruwDQ.eZQFEO, div.sc-bruwDQ.eZQFEP'
            )
            
            # If not found, try general selectors
            if not car_angles:
                car_angles = self.driver.find_elements(
                    By.CSS_SELECTOR, '.car-image, .rotator-image, .car-angle'
                )
            
            if car_angles:
                rotator_data['total_images'] = len(car_angles)
                
                for idx, angle in enumerate(car_angles, 1):
                    if angle.is_displayed():
                        angle_info = self._extract_angle_info(idx, angle)
                        rotator_data['car_images'].append(angle_info)
                        
                        # Store first image separately
                        if idx == 1:
                            rotator_data['current_image'] = angle_info.copy()
                            rotator_data['current_image']['description'] = "First/default car angle"
                
                print(f"        Found {len(rotator_data['car_images'])} car angles")
                
                # Log first image info
                if rotator_data['current_image']:
                    print(f"        First image: Class={rotator_data['current_image'].get('class', 'N/A')}")
            else:
                print(f"        No car angles found")
                
        except Exception as e:
            print(f"        ⚠ Error extracting car angles: {e}")
    
    def _extract_angle_info(self, idx: int, angle: WebElement) -> Dict:
        """Extract information about a car angle"""
        angle_info = {
            'index': idx,
            'class': angle.get_attribute('class') or '',
            'is_displayed': angle.is_displayed(),
            'location': angle.location,
            'size': angle.size
        }
        
        # Try to get image source
        try:
            img_element = angle.find_element(By.TAG_NAME, 'img')
            angle_info['img_src'] = img_element.get_attribute('src') or ''
            angle_info['img_alt'] = img_element.get_attribute('alt') or ''
            angle_info['img_size'] = img_element.size
        except:
            angle_info['img_info'] = "No img tag found"
        
        return angle_info
    
    def find_option_price_near_element(self, element: WebElement) -> str:
        """Find price near an option element"""
        try:
            parent = element.find_element(By.XPATH, '..')
            
            # Try exact price class
            try:
                price_elem = parent.find_element(By.CSS_SELECTOR, 'p.sc-gLaqbQ.hGVaco')
                return price_elem.text.strip()
            except:
                pass
            
            # Try general price patterns
            price_pattern = r'[\$\£\€]\s*[\d,]+(?:\.\d{2})?'
            
            # Check parent text
            parent_text = parent.text.strip()
            price_match = re.search(price_pattern, parent_text)
            if price_match:
                return price_match.group()
            
            # Check element's own text
            element_text = element.text.strip()
            price_match = re.search(price_pattern, element_text)
            if price_match:
                return price_match.group()
            
            return "Price not found"
            
        except:
            return "Price not found"
        
    def is_feature_section_button(self, button: WebElement) -> bool:
        """Check if button is part of a feature section"""
        try:
            button_text = button.text.strip().lower()
            
            feature_keywords = [
                'details', 'view', 'more', 'info', 'spec',
                'color', 'drivetrain', 'exterior', 'interior',
                'accessories', 'powertrain', 'engine', 'wheel'
            ]
            
            # If button text contains feature keywords
            if any(keyword in button_text for keyword in feature_keywords):
                return True
            
            # Check parent elements for feature section classes
            parent = button.find_element(By.XPATH, '..')
            parent_class = parent.get_attribute('class') or ''
            
            feature_classes = ['sc-12670f55', 'feature', 'spec', 'rail_section']
            return any(f_class in parent_class for f_class in feature_classes)
            
        except:
            return False
   
    def is_accessories_container_button(self, button: WebElement) -> bool:
        """Check if button is inside an accessories container"""
        try:
            parent = button.find_element(By.XPATH, './ancestor::div[contains(@class, "sc-CezhS")]')
            
            if parent:
                parent_class = parent.get_attribute('class') or ''
                return 'sc-CezhS' in parent_class and 'kLWQDy' in parent_class
            
            return False
            
        except:
            return False
    
    def click_main_section_buttons(self, main_section_height: int) -> Dict:
        """Click buttons in main section ONLY"""
        click_results = {
            'total_found': 0,
            'clicked': 0,
            'skipped_prohibited': 0,
            'skipped_feature_sections': 0,
            'skipped_accessories': 0,
            'skipped_already_processed': 0,
            'failed': 0
        }
        
        try:
            # Find all buttons in viewport
            all_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button, [role="button"]')
            main_section_buttons = self._filter_main_section_buttons(all_buttons, main_section_height)
            
            click_results['total_found'] = len(main_section_buttons)
            print(f"      Found {len(main_section_buttons)} buttons in main section")
            
            # Click each button
            for idx, button in enumerate(main_section_buttons, 1):
                self._process_single_button(idx, button, click_results)
            
            self._print_click_results(click_results)
            
        except Exception as e:
            print(f"      ⚠ Error clicking buttons: {e}")
        
        return click_results
    
    def _filter_main_section_buttons(self, buttons: List[WebElement], 
                                    main_section_height: int) -> List[WebElement]:
        """Filter buttons to only those in main section"""
        main_section_buttons = []
        
        for button in buttons:
            try:
                if button.is_displayed() and button.is_enabled():
                    location = button.location
                    if location['y'] < main_section_height:
                        main_section_buttons.append(button)
            except:
                continue
        
        return main_section_buttons
    
    def _process_single_button(self, idx: int, button: WebElement, 
                              click_results: Dict) -> None:
        """Process a single button"""
        button_id = self.generate_button_id(button)
        
        # Skip if already processed
        if button_id in self.processed_button_ids:
            click_results['skipped_already_processed'] += 1
            return
        
        button_text = button.text.strip().lower()
        
        # Check for prohibited content
        if self.is_prohibited_button(button_text):
            click_results['skipped_prohibited'] += 1
            print(f"        [{idx}] Skipped (prohibited): {button_text[:30]}")
            return
        
        # Skip feature section buttons
        if self.is_feature_section_button(button):
            click_results['skipped_feature_sections'] += 1
            print(f"        [{idx}] Skipped (feature section): {button_text[:30]}")
            return
        
        # Skip accessories container buttons
        if self.is_accessories_container_button(button):
            click_results['skipped_accessories'] += 1
            print(f"        [{idx}] Skipped (accessories): {button_text[:30]}")
            return
        
        print(f"        [{idx}] Clicking: {button_text[:30]}")
        
        # Try to click
        if self.safe_click_with_esc(button):
            click_results['clicked'] += 1
            self.processed_button_ids.add(button_id)
        else:
            click_results['failed'] += 1
        
        # Small delay
        time.sleep(0.5)
    
    def _print_click_results(self, click_results: Dict) -> None:
        """Print click results"""
        print(f"      Results: {click_results['clicked']} clicked, "
              f"{click_results['skipped_prohibited']} skipped (prohibited), "
              f"{click_results['skipped_feature_sections']} skipped (feature sections), "
              f"{click_results['skipped_accessories']} skipped (accessories), "
              f"{click_results['skipped_already_processed']} skipped (processed)")
    
    def is_prohibited_button(self, button_text: str) -> bool:
        """Check if button contains prohibited content"""
        if not button_text:
            return False
        
        return any(prohibited in button_text for prohibited in self.prohibited_contents)
    
    def generate_button_id(self, button: WebElement) -> str:
        """Generate unique ID for button"""
        id_parts = []
        
        try:
            # Use data attributes
            for attr in ['data-testid', 'id', 'data-id']:
                value = button.get_attribute(attr)
                if value:
                    id_parts.append(f"{attr}:{value}")
            
            # Use text hash
            text = button.text.strip()[:20]
            if text:
                id_parts.append(f"text:{hash(text)}")
            
            # Use classes
            classes = button.get_attribute('class') or ''
            if classes:
                # Take specific classes
                specific_classes = [c for c in classes.split() if 'sc-' in c]
                if specific_classes:
                    class_hash = hash('_'.join(specific_classes[:2]))
                    id_parts.append(f"class:{class_hash}")
            
            return '|'.join(id_parts) if id_parts else f"btn_{time.time()}"
            
        except:
            return f"btn_{time.time()}"
    
    def safe_click_with_esc(self, button: WebElement) -> bool:
        """Safely click button with ESC fallback for popups"""
        try:
            # Scroll to button
            self._scroll_to_element(button)
            
            # Check if still clickable
            if not button.is_displayed() or not button.is_enabled():
                return False
            
            # Click the button
            try:
                button.click()
            except:
                self.driver.execute_script("arguments[0].click();", button)
            
            # Wait and check for popup
            time.sleep(1)
            
            # Try to close any popup with ESC
            self.close_popup_with_esc()
            
            return True
            
        except Exception as e:
            print(f"          ⚠ Click error: {e}")
            return False
    
    def close_popup_with_esc(self) -> None:
        """Close popup using ESC key"""
        try:
            # First try ESC key
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            
            # Check if popup still exists
            if self.is_popup_visible():
                time.sleep(1)
                body.send_keys(Keys.ESCAPE)
                time.sleep(0.5)
                
                # If still exists, try specific close button
                if self.is_popup_visible():
                    self.try_specific_close_button()
            
        except Exception as e:
            print(f"          ⚠ ESC handling error: {e}")
    
    def is_popup_visible(self) -> bool:
        """Check if any popup is visible"""
        popup_selectors = [
            '.modal',
            '.popup',
            '[role="dialog"]',
            '.overlay:not([style*="none"])'
        ]
        
        for selector in popup_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        return True
            except:
                continue
        
        return False
    
    def try_specific_close_button(self) -> bool:
        """Try specific close buttons"""
        close_selectors = [
            '.sc-fhHczv.froHwv.sc-ca049354-5.gPlqdH',  # Your specific class
            'button.close',
            '.close-button',
            '[aria-label="Close"]'
        ]
        
        for selector in close_selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        self._safe_click(button)
                        print(f"          Closed popup with: {selector}")
                        return True
            except:
                continue
        
        return False
    
    def save_configurations(self) -> None:
        """Save all configuration data"""
        if not self.configurations:
            print("No configuration data to save!")
            return
        
        # Clean data
        cleaned_configs = [self.clean_config_data(config) for config in self.configurations]
        cleaned_configs = [config for config in cleaned_configs if config]
        
        # Save detailed configurations
        with open('nissan_main_section_complete.json', 'w', encoding='utf-8') as f:
            json.dump(cleaned_configs, f, indent=2, ensure_ascii=False)
        
        # Create summary
        summary = self._create_summary(cleaned_configs)
        
        with open('nissan_main_section_complete_summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Generate report
        self.generate_complete_report(cleaned_configs)
        
        self._print_save_confirmation(len(cleaned_configs))
    
    def _create_summary(self, cleaned_configs: List[Dict]) -> List[Dict]:
        """Create summary of configurations"""
        summary = []
        
        for config in cleaned_configs:
            summary_config = {
                'car_name': config.get('car_name', ''),
                'vehicle_display': {
                    'model': config.get('vehicle_display', {}).get('model_name', ''),
                    'trim': config.get('vehicle_display', {}).get('trim_level', ''),
                    'elements_found': config.get('vehicle_display', {}).get('elements_found', 0)
                },
                'car_rotator': {
                    'exists': config.get('car_rotator', {}).get('exists', False),
                    'total_images': config.get('car_rotator', {}).get('total_images', 0),
                    'has_first_image': 'current_image' in config.get('car_rotator', {})
                },
                'total_msrp': config.get('pricing', {}).get('amount', 'N/A'),
                'features_count': len(config.get('features', [])),
                'options_count': len(config.get('available_options', [])),
                'buttons_clicked': config.get('click_statistics', {}).get('clicked', 0),
                'buttons_skipped': config.get('click_statistics', {}).get('skipped_prohibited', 0)
            }
            summary.append(summary_config)
        
        return summary
    
    def _print_save_confirmation(self, num_configs: int) -> None:
        """Print save confirmation"""
        separator = "=" * 60
        print(f"\n{separator}")
        print("COMPLETE MAIN SECTION PROCESSING COMPLETE")
        print(separator)
        print(f"✓ Configurations processed: {num_configs}")
        print(f"✓ Complete data: nissan_main_section_complete.json")
        print(f"✓ Summary data: nissan_main_section_complete_summary.json")
        print(f"✓ Report: main_section_complete_report.txt")
        print(separator)
    
    def clean_config_data(self, config: Dict) -> Optional[Dict]:
        """Clean configuration data"""
        if not config:
            return None
        
        cleaned = {}
        for key, value in config.items():
            if value is None or value == '':
                continue
            
            if isinstance(value, dict):
                cleaned_value = self._clean_dict(value)
                if cleaned_value:
                    cleaned[key] = cleaned_value
            elif isinstance(value, list):
                cleaned_value = self._clean_list(value)
                if cleaned_value:
                    cleaned[key] = cleaned_value
            else:
                cleaned[key] = value
        
        return cleaned
    
    def _clean_dict(self, value: Dict) -> Dict:
        """Clean dictionary values"""
        return {k: v for k, v in value.items() 
                if v is not None and v != ''}
    
    def _clean_list(self, value: List) -> List:
        """Clean list values"""
        return [v for v in value if v is not None and v != '']
    
    def generate_complete_report(self, configurations: List[Dict]) -> None:
        """Generate detailed report"""
        report_lines = self._create_report_header(configurations)
        
        # Add accessories statistics
        self._add_accessories_statistics(configurations, report_lines)
        
        # Add vehicle details
        for config_idx, config in enumerate(configurations, 1):
            self._add_vehicle_details(config_idx, config, report_lines)
        
        # Add summary
        self._add_report_summary(configurations, report_lines)
        
        # Save report
        with open('main_section_complete_report.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
    
    def _create_report_header(self, configurations: List[Dict]) -> List[str]:
        """Create report header"""
        return [
            "=" * 80,
            "COMPLETE MAIN SECTION BUILD CONFIGURATION REPORT",
            "=" * 80,
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Vehicles Processed: {len(configurations)}",
            f"Items Extracted:",
            f"  1. Main Vehicle Display Section",
            f"  2. Navigation Tabs (disabled)",
            f"  3. 360° Car Rotator",
            f"  4. Vehicle Info, Features, Options, Pricing",
            f"Prohibited Contents: {', '.join(self.prohibited_contents)}",
            ""
        ]
    
    def _add_accessories_statistics(self, configurations: List[Dict], report_lines: List[str]) -> None:
        """Add accessories statistics to report"""
        total_accessories_clicked = sum(
            config.get('accessories_clicking', {}).get('buttons_clicked', 0)
            for config in configurations
        )
        
        total_accessories_containers = sum(
            config.get('accessories_clicking', {}).get('total_containers_found', 0)
            for config in configurations
        )
        
        if configurations:
            report_lines.append(f"\nACCESSORIES PROCESSING STATISTICS:")
            report_lines.append(f"  Total containers found: {total_accessories_containers}")
            report_lines.append(f"  Total buttons clicked: {total_accessories_clicked}")
            
            if total_accessories_containers > 0:
                success_rate = (total_accessories_clicked / total_accessories_containers) * 100
                report_lines.append(f"  Click success rate: {success_rate:.1f}%")
    
    def _add_vehicle_details(self, config_idx: int, config: Dict, report_lines: List[str]) -> None:
        """Add vehicle details to report"""
        separator = "=" * 60
        report_lines.append(f"{separator}")
        report_lines.append(f"VEHICLE {config_idx}: {config.get('car_name', 'Unknown')}")
        report_lines.append(f"{separator}")
        
        # Vehicle Display Section
        vehicle_display = config.get('vehicle_display', {})
        report_lines.append(f"\n1. MAIN VEHICLE DISPLAY:")
        report_lines.append(f"   Model Name: {vehicle_display.get('model_name', 'N/A')}")
        report_lines.append(f"   Trim Level: {vehicle_display.get('trim_level', 'N/A')}")
        
        change_trim = vehicle_display.get('change_trim_button', {})
        if change_trim.get('exists', True):
            report_lines.append(f"   Change Trim Button: {change_trim.get('text', 'Found')}")
            report_lines.append(f"     Displayed: {change_trim.get('is_displayed', False)}")
            report_lines.append(f"     Enabled: {change_trim.get('is_enabled', False)}")
        else:
            report_lines.append(f"   Change Trim Button: Not found")
        
        report_lines.append(f"   Elements found: {vehicle_display.get('elements_found', 0)}/3")
        
        # Car Rotator
        rotator = config.get('car_rotator', {})
        report_lines.append(f"\n3. 360° CAR ROTATOR:")
        report_lines.append(f"   Exists: {rotator.get('exists', False)}")
        report_lines.append(f"   Total images: {rotator.get('total_images', 0)}")
        
        # Pricing
        pricing = config.get('pricing', {})
        report_lines.append(f"\n4. PRICING:")
        report_lines.append(f"   {pricing.get('label', 'MSRP')}: {pricing.get('amount', 'N/A')}")
        
        # Click statistics
        click_stats = config.get('click_statistics', {})
        report_lines.append(f"\n5. BUTTON CLICKS:")
        report_lines.append(f"   Clicked: {click_stats.get('clicked', 0)}")
        report_lines.append(f"   Skipped (prohibited): {click_stats.get('skipped_prohibited', 0)}")
        
        # Other data
        report_lines.append(f"\n6. OTHER DATA:")
        report_lines.append(f"   Features: {len(config.get('features', []))}")
        report_lines.append(f"   Available Options: {len(config.get('available_options', []))}")
        report_lines.append(f"   Current Selections: {len(config.get('current_selections', []))}")
        
        report_lines.append("")
    
    def _add_report_summary(self, configurations: List[Dict], report_lines: List[str]) -> None:
        """Add summary to report"""
        # Calculate totals
        total_clicks = sum(
            config.get('click_statistics', {}).get('clicked', 0)
            for config in configurations
        )
        
        total_skipped = sum(
            config.get('click_statistics', {}).get('skipped_prohibited', 0)
            for config in configurations
        )
        
        display_elements_total = sum(
            config.get('vehicle_display', {}).get('elements_found', 0)
            for config in configurations
        )
        
        rotator_exists_count = sum(
            1 for config in configurations
            if config.get('car_rotator', {}).get('exists', False)
        )
        
        total_car_images = sum(
            config.get('car_rotator', {}).get('total_images', 0)
            for config in configurations
        )
        
        report_lines.append(f"\n{'='*80}")
        report_lines.append("OVERALL SUMMARY")
        report_lines.append(f"{'='*80}")
        report_lines.append(f"Total vehicles: {len(configurations)}")
        report_lines.append(f"Total buttons clicked: {total_clicks}")
        report_lines.append(f"Total buttons skipped (prohibited): {total_skipped}")
        
        if configurations:
            avg_clicks = total_clicks / len(configurations)
            avg_skipped = total_skipped / len(configurations)
            report_lines.append(f"Average clicks per vehicle: {avg_clicks:.1f}")
            report_lines.append(f"Average skipped per vehicle: {avg_skipped:.1f}")
        
        # Vehicle Display Statistics
        if configurations:
            avg_display_elements = display_elements_total / len(configurations)
            report_lines.append(f"\nVEHICLE DISPLAY STATISTICS:")
            report_lines.append(f"  Total elements found: {display_elements_total}")
            report_lines.append(f"  Average per vehicle: {avg_display_elements:.1f}/3")
        
        # Car Rotator Statistics
        if configurations:
            report_lines.append(f"\nCAR ROTATOR STATISTICS:")
            report_lines.append(f"  Vehicles with rotator: {rotator_exists_count}/{len(configurations)}")
            report_lines.append(f"  Total car images: {total_car_images}")
            if rotator_exists_count > 0:
                report_lines.append(f"  Average images per rotator: {total_car_images/rotator_exists_count:.1f}")
        
        report_lines.append(f"\nProcessing Rules:")
        report_lines.append(f"• Only main section processed (no navigation)")
        report_lines.append(f"• ESC key used for popup closing")
        report_lines.append(f"• Prohibited buttons skipped")
        report_lines.append(f"{'='*80}")


def main():
    """Main function to run main section configurator"""
    banner = "=" * 70
    print(banner)
    print("COMPLETE MAIN SECTION BUILD CONFIGURATOR")
    print(banner)
    print("\nThis configurator will extract ALL specified items:")
    print("\n1. MAIN VEHICLE DISPLAY SECTION:")
    print("   • Vehicle Model/Trim: p[data-testid='NGST_QA_mainstage_vehicle']")
    print("   • Trim Level: p.sc-eQwNpu.kLGtky.sc-d4bdcb3-1.hplpik")
    print("   • Change Trim Button: button[data-testid='NGST_QA_change_trim_button']")
    
    print("\n3. 360° CAR ROTATOR:")
    print("   • Car Images Container: div.car_rotate")
    print("   • Individual Car Angles: div.sc-bruwDQ.eZQFEO (first), eZQFEP (others)")
    print("   • Only first image will be extracted")
    
    print(f"\n{banner}")
    print("Prohibited button contents: change trim, compare, share, etc.")
    print(banner)
    
    confirm = input("\nContinue? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("Operation cancelled.")
        return
    
    # Run configurator
    configurator = BuildConfigurator(headless=False)
    
    try:
        configurator.process_build_configurations()
    except KeyboardInterrupt:
        print("\n\n⚠ Process interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        configurator.close()


if __name__ == "__main__":
    main()