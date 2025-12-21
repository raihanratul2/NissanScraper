"""
Nissan Build Configurator - Dynamic Configuration Scraper
Based on JSON configuration with element/content dependency
"""

import json
import time
import re
import traceback
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from base import NissanScraperBase


class DynamicBuildConfigurator(NissanScraperBase):
    def __init__(self, headless=False, config_file=None):
        super().__init__(headless)
        self.config = self.load_configuration(config_file)
        self.current_data = {}
        self.interaction_log = []
        
        # Prohibited content
        self.prohibited_contents = [
            "change trim", "compare", "share", "save", "print", "email",
            "dealer", "inventory", "contact", "chat", "help", "support"
        ]
    
    def load_configuration(self, config_file=None):
        """Load scraping configuration from JSON file or use default"""
        if config_file:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠ Error loading config file: {e}")
        
        # Use the provided JSON as default configuration
        default_config = {
            "scraping_configuration": {
                "vehicle_info": {
                    "year": "2025",
                    "model": "Kicks Play",
                    "trim": "S",
                    "base_msrp": "$21,520"
                },
                # ... (same as your provided JSON)
            }
        }
        
        # Merge your complete JSON here (too long to include fully)
        return default_config
    
    def process_vehicle_configurations(self, build_links):
        """Process multiple build configurations"""
        print("=" * 80)
        print("DYNAMIC BUILD CONFIGURATOR")
        print("=" * 80)
        print(f"Configuration loaded: {self.config['scraping_configuration']['vehicle_info']['model']}")
        print(f"Section types: {len(self.config['scraping_configuration']['section_types'])}")
        print("=" * 80)
        
        all_results = []
        
        for idx, build_link in enumerate(build_links, 1):
            print(f"\n[{idx}/{len(build_links)}] Processing: {build_link[:80]}...")
            
            try:
                result = self.scrape_single_configuration(build_link)
                if result:
                    all_results.append(result)
                    print(f"✓ Successfully scraped configuration")
                else:
                    print(f"✗ Failed to scrape configuration")
            except Exception as e:
                print(f"✗ Error: {str(e)[:100]}")
                self.log_interaction("error", f"Processing failed: {str(e)}")
            
            # Small delay between vehicles
            time.sleep(2)
        
        # Save results
        if all_results:
            self.save_results(all_results)
        
        return all_results
    
    def scrape_single_configuration(self, build_url):
        """Scrape a single vehicle configuration"""
        self.current_data = {
            "url": build_url,
            "scraped_at": datetime.now().isoformat(),
            "vehicle_info": {},
            "sections": [],
            "interaction_log": []
        }
        
        try:
            # 1. Navigate to build page
            print("  Navigating to build page...")
            self.driver.get(build_url)
            time.sleep(3)
            
            # 2. Handle initial popups
            self.handle_initial_popups()
            
            # 3. Wait for main content
            self.wait_for_main_container()
            
            # 4. Extract vehicle info
            print("  Extracting vehicle information...")
            self.extract_vehicle_info()
            
            # 5. Discover and process sections
            print("  Discovering sections...")
            sections = self.discover_sections()
            
            for section_idx, section_info in enumerate(sections, 1):
                print(f"  Processing section {section_idx}/{len(sections)}: {section_info.get('section_name', 'Unknown')}")
                
                section_data = self.process_section(section_info)
                if section_data:
                    self.current_data["sections"].append(section_data)
            
            # 6. Calculate total MSRP
            self.calculate_total_msrp()
            
            # 7. Take screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_name = f"config_{self.current_data['vehicle_info'].get('model', 'unknown')}_{timestamp}.png"
            self.driver.save_screenshot(screenshot_name)
            self.current_data["screenshot"] = screenshot_name
            
            print(f"✓ Configuration scraped successfully")
            return self.current_data
            
        except Exception as e:
            print(f"✗ Error scraping configuration: {str(e)[:100]}")
            self.log_interaction("error", f"Scraping failed: {traceback.format_exc()}")
            return None
    
    def wait_for_main_container(self):
        """Wait for main container to load"""
        config = self.config['scraping_configuration']
        selectors = config['navigation']['main_container']
        
        # Try multiple selectors
        all_selectors = [
            selectors['selector'],
            selectors['data_testid'],
            "#mainstage-rail",
            "[data-testid='NGST_QA_rail_section']",
            ".build-configurator",
            "main"
        ]
        
        for selector in all_selectors:
            try:
                # Clean selector
                if selector.startswith("[") and "=" in selector:
                    # Handle data-testid selector
                    attr_name = selector.split("'")[1] if "'" in selector else selector.split('"')[1]
                    attr_value = selector.split("'")[3] if "'" in selector else selector.split('"')[3]
                    xpath = f"//*[@{attr_name}='{attr_value}']"
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                else:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                
                if element.is_displayed():
                    print(f"  ✓ Main container found: {selector[:50]}")
                    self.log_interaction("info", f"Main container found: {selector}")
                    return element
            except:
                continue
        
        raise Exception("Main container not found")
    
    def extract_vehicle_info(self):
        """Extract vehicle information"""
        try:
            # Get from configuration
            vehicle_config = self.config['scraping_configuration']['vehicle_info']
            
            # Try to extract dynamically from page
            try:
                # Vehicle model/trim
                model_element = self.driver.find_element(
                    By.CSS_SELECTOR, "p[data-testid='NGST_QA_mainstage_vehicle']"
                )
                vehicle_config['model'] = model_element.text.strip()
            except:
                pass
            
            # Store in current data
            self.current_data["vehicle_info"] = vehicle_config
            
            # Also try to get current MSRP
            try:
                msrp_element = self.driver.find_element(
                    By.CSS_SELECTOR, "p.sc-ad50de1b-6.fFhJKT"
                )
                self.current_data["vehicle_info"]["current_msrp"] = msrp_element.text.strip()
            except:
                pass
            
            self.log_interaction("info", f"Vehicle info extracted: {vehicle_config}")
            
        except Exception as e:
            print(f"  ⚠ Error extracting vehicle info: {e}")
            self.log_interaction("warning", f"Vehicle info extraction failed: {e}")
    
    def discover_sections(self):
        """Discover all sections in the configurator"""
        sections = []
        config = self.config['scraping_configuration']
        
        try:
            # Find section containers
            section_selector = config['navigation']['sections']['container']
            section_elements = self.driver.find_elements(
                By.CSS_SELECTOR, section_selector
            )
            
            print(f"  Found {len(section_elements)} section containers")
            
            for element in section_elements:
                if not element.is_displayed():
                    continue
                
                section_info = {
                    "element": element,
                    "location": element.location
                }
                
                # Extract section ID
                try:
                    section_id = element.get_attribute(
                        config['navigation']['sections']['section_id_attribute']
                    )
                    section_info["section_id"] = section_id
                except:
                    pass
                
                # Extract section title
                try:
                    title_element = element.find_element(
                        By.CSS_SELECTOR, config['navigation']['sections']['title']
                    )
                    section_info["section_name"] = title_element.text.strip()
                except:
                    pass
                
                # Determine section type based on ID
                section_type = self.determine_section_type(section_info.get("section_id", ""))
                section_info["section_type"] = section_type
                
                sections.append(section_info)
            
            self.log_interaction("info", f"Discovered {len(sections)} sections")
            
        except Exception as e:
            print(f"  ⚠ Error discovering sections: {e}")
            self.log_interaction("error", f"Section discovery failed: {e}")
        
        return sections
    
    def determine_section_type(self, section_id):
        """Determine the type of section based on ID"""
        config = self.config['scraping_configuration']['section_types']
        
        # Check color selection
        if section_id == config['color_selection']['section_id']:
            return "color_selection"
        
        # Check single option sections
        for section_id_pattern in config['single_option']['section_ids']:
            if section_id_pattern in section_id:
                return "single_option"
        
        # Check accessory grid sections
        for section_id_pattern in config['accessory_grid']['section_ids']:
            if section_id_pattern in section_id:
                return "accessory_grid"
        
        # Default
        return "unknown"
    
    def process_section(self, section_info):
        """Process a single section based on its type"""
        section_data = {
            "section_id": section_info.get("section_id", ""),
            "section_name": section_info.get("section_name", "Unknown"),
            "section_type": section_info.get("section_type", "unknown"),
            "processed_at": datetime.now().isoformat()
        }
        
        try:
            section_type = section_info.get("section_type", "unknown")
            
            if section_type == "color_selection":
                section_data["data"] = self.process_color_section(section_info)
            elif section_type == "single_option":
                section_data["data"] = self.process_single_option_section(section_info)
            elif section_type == "accessory_grid":
                section_data["data"] = self.process_accessory_grid_section(section_info)
            else:
                section_data["data"] = self.process_unknown_section(section_info)
            
            self.log_interaction("info", f"Section processed: {section_data['section_name']}")
            
        except Exception as e:
            print(f"    ⚠ Error processing section: {e}")
            section_data["error"] = str(e)
            self.log_interaction("error", f"Section processing failed: {e}")
        
        return section_data
    
    def process_color_section(self, section_info):
        """Process color selection section"""
        config = self.config['scraping_configuration']
        section_config = config['section_types']['color_selection']
        data_selectors = config['data_selectors']['color_section']
        
        color_data = {
            "available_colors": [],
            "selected_color": None,
            "car_images": []
        }
        
        try:
            # Find all color buttons
            color_buttons = section_info['element'].find_elements(
                By.CSS_SELECTOR, section_config['item_class']
            )
            
            print(f"    Found {len(color_buttons)} color options")
            
            # Process each color button
            for idx, button in enumerate(color_buttons[:5]):  # Limit to first 5
                if not button.is_displayed():
                    continue
                
                color_info = self.extract_color_info(button, data_selectors)
                color_data["available_colors"].append(color_info)
                
                # Check if this color is selected
                try:
                    selected_indicator = button.find_element(
                        By.CSS_SELECTOR, data_selectors['selected_indicator']
                    )
                    if selected_indicator.is_displayed():
                        color_data["selected_color"] = color_info
                        
                        # Extract car images for selected color
                        car_images = self.extract_car_images(data_selectors['car_images'])
                        color_data["car_images"] = car_images
                except:
                    pass
            
            self.log_interaction("info", f"Color section processed: {len(color_data['available_colors'])} colors")
            
        except Exception as e:
            print(f"      ⚠ Error processing color section: {e}")
            color_data["error"] = str(e)
        
        return color_data
    
    def extract_color_info(self, button_element, data_selectors):
        """Extract color information from button"""
        color_info = {
            "is_selected": False,
            "is_standard": False
        }
        
        try:
            # Color name
            try:
                name_element = button_element.find_element(
                    By.CSS_SELECTOR, data_selectors['color_name']
                )
                color_info["color_name"] = name_element.text.strip()
            except:
                pass
            
            # Color swatch image
            try:
                swatch_element = button_element.find_element(
                    By.CSS_SELECTOR, data_selectors['color_swatch']
                )
                color_info["swatch_url"] = swatch_element.get_attribute("src") or ""
                color_info["swatch_alt"] = swatch_element.get_attribute("alt") or ""
            except:
                pass
            
            # Check if selected
            try:
                selected_element = button_element.find_element(
                    By.CSS_SELECTOR, data_selectors['selected_indicator']
                )
                color_info["is_selected"] = selected_element.is_displayed()
            except:
                pass
            
            # Check if standard
            try:
                # Look for standard indicator near the button
                parent = button_element.find_element(By.XPATH, "..")
                standard_elements = parent.find_elements(
                    By.CSS_SELECTOR, data_selectors['standard_indicator']
                )
                color_info["is_standard"] = len(standard_elements) > 0
            except:
                pass
            
        except Exception as e:
            print(f"        ⚠ Error extracting color info: {e}")
        
        return color_info
    
    def extract_car_images(self, car_images_config):
        """Extract car images from rotator"""
        car_images = []
        
        try:
            # First try active images
            active_selector = car_images_config.get('active', '')
            if active_selector:
                active_images = self.driver.find_elements(
                    By.CSS_SELECTOR, active_selector
                )
                
                for img in active_images[:3]:  # Limit to 3 images
                    if img.is_displayed():
                        img_info = {
                            "image_url": img.get_attribute("src") or "",
                            "alt": img.get_attribute("alt") or "",
                            "srcset": img.get_attribute("srcset") or "",
                            "is_active": True
                        }
                        car_images.append(img_info)
            
            # Then try hidden images
            hidden_selector = car_images_config.get('hidden', '')
            if hidden_selector:
                hidden_images = self.driver.find_elements(
                    By.CSS_SELECTOR, hidden_selector
                )
                
                for img in hidden_images[:2]:  # Limit to 2 hidden images
                    if not img.is_displayed():
                        img_info = {
                            "image_url": img.get_attribute("src") or "",
                            "alt": img.get_attribute("alt") or "",
                            "srcset": img.get_attribute("srcset") or "",
                            "is_active": False
                        }
                        car_images.append(img_info)
            
        except Exception as e:
            print(f"        ⚠ Error extracting car images: {e}")
        
        return car_images
    
    def process_single_option_section(self, section_info):
        """Process single option section (like drivetrain)"""
        config = self.config['scraping_configuration']
        section_config = config['section_types']['single_option']
        
        options_data = {
            "available_options": [],
            "selected_option": None
        }
        
        try:
            # Find all option items
            option_items = section_info['element'].find_elements(
                By.CSS_SELECTOR, section_config['item_class']
            )
            
            print(f"    Found {len(option_items)} options")
            
            # Process each option
            for item in option_items:
                if not item.is_displayed():
                    continue
                
                option_info = self.extract_option_info(item, config['data_selectors']['common'])
                options_data["available_options"].append(option_info)
                
                # Check if selected (look for selected classes)
                item_classes = item.get_attribute("class") or ""
                if "selected" in item_classes.lower():
                    options_data["selected_option"] = option_info
            
            self.log_interaction("info", f"Single option section processed: {len(options_data['available_options'])} options")
            
        except Exception as e:
            print(f"      ⚠ Error processing single option section: {e}")
            options_data["error"] = str(e)
        
        return options_data
    
    def process_accessory_grid_section(self, section_info):
        """Process accessory grid section"""
        config = self.config['scraping_configuration']
        section_config = config['section_types']['accessory_grid']
        
        accessories_data = {
            "items": [],
            "categories": [],
            "total_items": 0
        }
        
        try:
            # Find all accessory items
            accessory_items = section_info['element'].find_elements(
                By.CSS_SELECTOR, section_config['item_class']
            )
            
            print(f"    Found {len(accessory_items)} accessories")
            accessories_data["total_items"] = len(accessory_items)
            
            # Process each accessory (limit to first 10 for performance)
            for idx, item in enumerate(accessory_items[:10]):
                if not item.is_displayed():
                    continue
                
                accessory_info = self.extract_accessory_info(item, config)
                accessories_data["items"].append(accessory_info)
                
                # Extract category
                try:
                    category_element = item.find_element(
                        By.CSS_SELECTOR, config['data_selectors']['accessory_sections']['category']
                    )
                    category = category_element.text.strip()
                    if category and category not in accessories_data["categories"]:
                        accessories_data["categories"].append(category)
                except:
                    pass
            
            self.log_interaction("info", f"Accessory grid processed: {len(accessories_data['items'])} items")
            
        except Exception as e:
            print(f"      ⚠ Error processing accessory grid: {e}")
            accessories_data["error"] = str(e)
        
        return accessories_data
    
    def extract_accessory_info(self, item_element, config):
        """Extract accessory information"""
        accessory_info = {
            "has_conflict": False,
            "details_available": False
        }
        
        try:
            # Extract basic info
            common_selectors = config['data_selectors']['common']
            accessory_selectors = config['data_selectors']['accessory_sections']
            
            # Accessory name
            try:
                name_element = item_element.find_element(
                    By.CSS_SELECTOR, common_selectors['item_name']
                )
                accessory_info["name"] = name_element.text.strip()
            except:
                pass
            
            # Price
            try:
                price_element = item_element.find_element(
                    By.CSS_SELECTOR, accessory_selectors['price']
                )
                accessory_info["price"] = price_element.text.strip()
            except:
                pass
            
            # Thumbnail image
            try:
                thumbnail_element = item_element.find_element(
                    By.CSS_SELECTOR, common_selectors['thumbnail_image']
                )
                accessory_info["thumbnail_url"] = thumbnail_element.get_attribute("src") or ""
            except:
                pass
            
            # Check for conflict
            conflict_config = config['section_types']['accessory_grid']
            if 'conflict_class' in conflict_config:
                try:
                    conflict_elements = item_element.find_elements(
                        By.CSS_SELECTOR, conflict_config['conflict_class']
                    )
                    accessory_info["has_conflict"] = len(conflict_elements) > 0
                except:
                    pass
            
            # Check for details button
            try:
                details_button = item_element.find_element(
                    By.CSS_SELECTOR, common_selectors['details_button']
                )
                accessory_info["details_available"] = details_button.is_displayed()
                
                # Optionally click and extract details
                if accessory_info["details_available"]:
                    details_data = self.extract_accessory_details(details_button, config)
                    accessory_info["details"] = details_data
            except:
                pass
            
        except Exception as e:
            print(f"        ⚠ Error extracting accessory info: {e}")
        
        return accessory_info
    
    def extract_accessory_details(self, details_button, config):
        """Extract details from accessory modal"""
        details_data = {}
        
        try:
            # Click details button
            details_button.click()
            time.sleep(1.5)
            
            # Wait for modal
            modal_config = config['data_selectors']['details_modal']
            try:
                modal = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, modal_config['container']))
                )
                
                # Extract modal data
                if modal.is_displayed():
                    # Large image
                    try:
                        large_img = modal.find_element(
                            By.CSS_SELECTOR, modal_config['large_image']
                        )
                        details_data["large_image_url"] = large_img.get_attribute("src") or ""
                    except:
                        pass
                    
                    # Product name
                    try:
                        product_name = modal.find_element(
                            By.CSS_SELECTOR, modal_config['product_name']
                        )
                        details_data["product_name"] = product_name.text.strip()
                    except:
                        pass
                    
                    # MSRP
                    try:
                        msrp = modal.find_element(
                            By.CSS_SELECTOR, modal_config['msrp']
                        )
                        details_data["msrp"] = msrp.text.strip()
                    except:
                        pass
                    
                    # Description
                    try:
                        desc_container = modal.find_element(
                            By.CSS_SELECTOR, modal_config['description_container']
                        )
                        desc_points = desc_container.find_elements(
                            By.CSS_SELECTOR, modal_config['description_points']
                        )
                        details_data["description_points"] = [p.text.strip() for p in desc_points if p.text.strip()]
                    except:
                        pass
                
                # Close modal
                self.close_modal(config['interaction_handlers']['close_details_modal'])
                
            except TimeoutException:
                print("        Modal didn't appear within timeout")
            
        except Exception as e:
            print(f"        ⚠ Error extracting accessory details: {e}")
        
        return details_data
    
    def close_modal(self, close_config):
        """Close modal using multiple methods"""
        methods = close_config.get('methods', [])
        
        for method in sorted(methods, key=lambda x: x.get('priority', 999)):
            try:
                if method.get('action') == 'press_escape':
                    body = self.driver.find_element(By.TAG_NAME, 'body')
                    body.send_keys(Keys.ESCAPE)
                    time.sleep(0.5)
                    return True
                
                elif 'selector' in method:
                    close_buttons = self.driver.find_elements(
                        By.CSS_SELECTOR, method['selector']
                    )
                    for button in close_buttons:
                        if button.is_displayed() and button.is_enabled():
                            button.click()
                            time.sleep(0.5)
                            return True
                            
            except:
                continue
        
        return False
    
    def process_unknown_section(self, section_info):
        """Process unknown section type"""
        return {
            "message": "Unknown section type",
            "raw_html_sample": section_info['element'].text[:200] if section_info.get('element') else ""
        }
    
    def calculate_total_msrp(self):
        """Calculate total MSRP from all sections"""
        try:
            base_msrp = self.current_data["vehicle_info"].get("base_msrp", "$0")
            
            # Parse base MSRP
            base_value = 0
            match = re.search(r'[\$\£\€]?\s*([\d,]+)', base_msrp)
            if match:
                base_value = float(match.group(1).replace(',', ''))
            
            # Add accessory prices
            accessory_total = 0
            for section in self.current_data.get("sections", []):
                if section.get("section_type") == "accessory_grid":
                    for item in section.get("data", {}).get("items", []):
                        price = item.get("price", "$0")
                        match = re.search(r'[\$\£\€]?\s*([\d,]+)', price)
                        if match:
                            accessory_total += float(match.group(1).replace(',', ''))
            
            total_value = base_value + accessory_total
            
            self.current_data["pricing_summary"] = {
                "base_msrp": base_msrp,
                "accessories_total": f"${accessory_total:,.2f}",
                "total_msrp": f"${total_value:,.2f}",
                "calculated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"  ⚠ Error calculating MSRP: {e}")
    
    def log_interaction(self, level, message):
        """Log interaction for debugging"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message[:500]  # Limit message length
        }
        self.interaction_log.append(log_entry)
        self.current_data.setdefault("interaction_log", []).append(log_entry)
    
    def handle_initial_popups(self):
        """Handle initial popups"""
        try:
            # Press ESC
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ESCAPE)
            time.sleep(1)
            
            # Try close buttons
            close_selectors = [
                'button[aria-label="Close"]',
                '.close-button',
                '[class*="close"]',
                'button:contains("No Thanks")'
            ]
            
            for selector in close_selectors:
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
                            button.click()
                            time.sleep(0.5)
                            break
                except:
                    continue
                    
        except Exception as e:
            print(f"  ⚠ Error handling popups: {e}")
    
    def save_results(self, all_results):
        """Save all results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results
        detailed_file = f"nissan_configurations_{timestamp}.json"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        # Save summary
        summary = []
        for result in all_results:
            summary_entry = {
                "model": result.get("vehicle_info", {}).get("model", "Unknown"),
                "trim": result.get("vehicle_info", {}).get("trim", "Unknown"),
                "total_msrp": result.get("pricing_summary", {}).get("total_msrp", "N/A"),
                "sections_count": len(result.get("sections", [])),
                "url": result.get("url", "")
            }
            summary.append(summary_entry)
        
        summary_file = f"nissan_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Save interaction log
        all_logs = []
        for result in all_results:
            all_logs.extend(result.get("interaction_log", []))
        
        if all_logs:
            log_file = f"nissan_interactions_{timestamp}.json"
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(all_logs, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*80}")
        print("RESULTS SAVED")
        print(f"{'='*80}")
        print(f"✓ Detailed data: {detailed_file}")
        print(f"✓ Summary: {summary_file}")
        if all_logs:
            print(f"✓ Interaction logs: {log_file}")
        print(f"✓ Total configurations: {len(all_results)}")
        print(f"{'='*80}")


def main():
    """Main function"""
    print("=" * 80)
    print("DYNAMIC NISSAN BUILD CONFIGURATOR")
    print("=" * 80)
    print("Based on JSON configuration with element/content dependency")
    print("This script will dynamically adapt to website content changes")
    print("=" * 80)
    
    # Load build links from file or use sample
    build_links = []
    try:
        with open('nissan_trims_simple.json', 'r', encoding='utf-8') as f:
            trim_data = json.load(f)
            build_links = [trim.get('page_link') for trim in trim_data if trim.get('page_link')]
    except:
        print("⚠ Could not load trim data file")
        # Use sample links for testing
        build_links = [
            "https://www.nissanusa.com/vehicles/cars/altima/build.html",
            "https://www.nissanusa.com/vehicles/cars/sentra/build.html"
        ]
    
    if not build_links:
        print("❌ No build links found!")
        return
    
    print(f"\nFound {len(build_links)} build links to process")
    print(f"Sample: {build_links[0][:80]}...")
    
    confirm = input("\nContinue? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("Operation cancelled.")
        return
    
    # Initialize and run configurator
    configurator = DynamicBuildConfigurator(headless=False, config_file='nissan_config.json')
    
    try:
        results = configurator.process_vehicle_configurations(build_links)
        print(f"\n✓ Processing complete: {len(results)} configurations scraped")
    except KeyboardInterrupt:
        print("\n⚠ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
    finally:
        configurator.close()


if __name__ == "__main__":
    main()