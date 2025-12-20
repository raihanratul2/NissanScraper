"""
Build Configurator - Processes ONLY main section of build pages
Uses ESC key for popup closing, skips prohibited buttons
"""

import json
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from base import NissanScraperBase


class BuildConfigurator(NissanScraperBase):
    def __init__(self, headless=False):
        super().__init__(headless)
        self.configurations = []
        self.processed_button_ids = set()
        
        # Prohibited content - buttons containing these texts will NOT be clicked
        self.prohibited_contents = [
            "change trim",
            "compare",
            "share",
            "save",
            "print",
            "email",
            "dealer",
            "inventory",
            "contact",
            "chat",
            "help",
            "support",
            "faq",
            "legal",
            "privacy",
            "terms",
            "cookie",
            "feedback"
        ]
    
    def load_trim_data(self, filename="nissan_trims_simple.json"):
        """Load trim data from JSON file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ File {filename} not found!")
            return []
    
    def process_build_configurations(self):
        """Process ONLY main section of build configurations"""
        trim_data = self.load_trim_data()
        
        if not trim_data:
            print("No trim data found. Please run car_list_processor.py first.")
            return
        
        print(f"\n{'='*60}")
        print(f"MAIN SECTION BUILD CONFIGURATOR")
        print(f"{'='*60}")
        print("Rules:")
        print("• Processes ONLY main section (no navigation)")
        print("• Uses ESC key for popup closing")
        print("• Skips prohibited buttons")
        print("• No section navigation")
        print(f"{'='*60}\n")
        
        successful = 0
        failed = 0
        
        for idx, trim in enumerate(trim_data, 1):
            build_link = trim.get('page_link')
            
            if not build_link:
                print(f"{idx:3d}. Skipping: {trim.get('car_name')} - No build link")
                failed += 1
                continue
            
            print(f"{idx:3d}. Processing: {trim.get('car_name')}")
            print(f"    Link: {build_link[:80]}...")
            
            # Reset for each trim
            self.processed_button_ids.clear()
            
            # Process ONLY main section
            config_data = self.scrape_main_section_only(build_link, trim)
            
            if config_data:
                self.configurations.append(config_data)
                successful += 1
                print(f"    ✓ Main section extracted")
            else:
                failed += 1
                print(f"    ⚠ Failed to extract main section")
            
            print()
        
        # Save configurations
        if self.configurations:
            self.save_configurations()
        
        print(f"\n{'='*60}")
        print("PROCESSING SUMMARY")
        print(f"{'='*60}")
        print(f"✓ Successful: {successful}")
        print(f"✗ Failed: {failed}")
        print(f"Total: {successful + failed}")
        print(f"{'='*60}")
    
    def scrape_main_section_only(self, build_link, trim_info):
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
            
            # Define main section area (top 80% of viewport)
            main_section_height = int(viewport_height * 0.8)
            
            print(f"      Viewport: {viewport_height}px, Main section: {main_section_height}px")
            
            # Extract main section content
            main_section_data = self.extract_main_section_content()
            config_data.update(main_section_data)
            
            # Find and click buttons in main section ONLY
            click_results = self.click_main_section_buttons(main_section_height)
            
            # Extract data after clicking
            time.sleep(2)
            updated_data = self.extract_main_section_content()
            config_data['after_clicking'] = updated_data
            
            # Add click statistics
            config_data['click_statistics'] = click_results
            
            # Take screenshot of main section
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            screenshot_name = f"main_section_{trim_info.get('id', '0')}_{timestamp}.png"
            self.driver.save_screenshot(screenshot_name)
            config_data['screenshot'] = screenshot_name
            
            print(f"      ✓ Main section processing complete")
            return config_data
            
        except Exception as e:
            print(f"    ✗ Error processing main section: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
            return None
    
    def handle_initial_popups(self):
        """Handle initial popups with ESC key"""
        try:
            # Try ESC key first
            print("      Pressing ESC to close any popups...")
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ESCAPE)
            time.sleep(1)
            
            # Also try common close buttons
            close_selectors = [
                'button.close',
                '.close-button',
                '[aria-label="Close"]',
                '[class*="close"]',
                'button:contains("Close")',
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
                            self._safe_click(button)
                            print(f"      Closed popup with: {selector}")
                            time.sleep(1)
                            break
                except:
                    continue
                    
        except Exception as e:
            print(f"      ⚠ Error handling popups: {e}")
    
    def wait_for_main_content(self):
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
    
    def extract_main_section_content(self):
        """Extract content from main section ONLY"""
        main_data = {
            'vehicle_info': {},
            'current_selections': [],
            'available_options': [],
            'pricing': {},
            'features': []
        }
        
        try:
            # 1. Vehicle Model Name
            try:
                vehicle_model = self.driver.find_element(
                    By.CSS_SELECTOR, 'p[data-testid="NGST_QA_mainstage_vehicle"]'
                )
                main_data['vehicle_info']['model'] = vehicle_model.text.strip()
            except:
                main_data['vehicle_info']['model'] = "Not found"
            
            # 2. Current Trim Name
            try:
                trim_name = self.driver.find_element(
                    By.CSS_SELECTOR, 'p.sc-d4bdcb3-1.hplpik'
                )
                main_data['vehicle_info']['trim'] = trim_name.text.strip()
            except:
                main_data['vehicle_info']['trim'] = "Not found"
            
            # 3. Features & Specs Section
            try:
                # Section Title
                section_titles = self.driver.find_elements(
                    By.CSS_SELECTOR, 'h2.sc-12670f55-5.iPnYKV'
                )
                for title in section_titles:
                    if title.is_displayed():
                        section_name = title.text.strip()
                        
                        # Get parent section
                        parent = title.find_element(By.XPATH, '..')
                        
                        # Feature Items
                        feature_items = parent.find_elements(
                            By.CSS_SELECTOR, 'div[data-testid="NGST_QA_rail_section"] > *'
                        )
                        
                        for item in feature_items:
                            if item.is_displayed():
                                item_text = item.text.strip()
                                if item_text:
                                    main_data['features'].append({
                                        'section': section_name,
                                        'feature': item_text
                                    })
                        
                        # Tooltips
                        tooltips = parent.find_elements(
                            By.CSS_SELECTOR, 'span.sc-dFVmKS.dziboY'
                        )
                        for tooltip in tooltips:
                            if tooltip.is_displayed():
                                tooltip_text = tooltip.text.strip()
                                if tooltip_text:
                                    main_data['features'].append({
                                        'section': section_name,
                                        'tooltip': tooltip_text
                                    })
            except:
                pass
            
            # 4. Accessory & Options
            try:
                # Category Name
                categories = self.driver.find_elements(
                    By.CSS_SELECTOR, 'span.sc-a64f1049-14.gyxydV'
                )
                
                for category in categories:
                    if category.is_displayed():
                        category_name = category.text.strip()
                        
                        # Find nearby options
                        parent = category.find_element(By.XPATH, '../..')
                        
                        # Option Titles
                        option_titles = parent.find_elements(
                            By.CSS_SELECTOR, 'p.sc-a64f1049-0.eVBtpM'
                        )
                        
                        for title in option_titles:
                            if title.is_displayed():
                                option_name = title.text.strip()
                                
                                # Find price
                                option_price = self.find_option_price_near_element(title)
                                
                                main_data['available_options'].append({
                                    'category': category_name,
                                    'name': option_name,
                                    'price': option_price
                                })
            except:
                pass
            
            # 5. Total MSRP
            try:
                # MSRP Label
                label_elem = self.driver.find_element(
                    By.CSS_SELECTOR, 'p.sc-ad50de1b-5.gLhmbt'
                )
                main_data['pricing']['label'] = label_elem.text.strip()
            except:
                main_data['pricing']['label'] = "MSRP"
            
            try:
                # Final Amount
                amount_elem = self.driver.find_element(
                    By.CSS_SELECTOR, 'p.sc-ad50de1b-6.fFhJKT'
                )
                main_data['pricing']['amount'] = amount_elem.text.strip()
            except:
                main_data['pricing']['amount'] = "Not found"
            
            # 6. Current Selections (selected options)
            try:
                selected_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, '.selected, [aria-selected="true"], [data-selected="true"]'
                )
                
                for element in selected_elements:
                    if element.is_displayed():
                        text = element.text.strip()
                        if text:
                            main_data['current_selections'].append(text)
            except:
                pass
            
            print(f"      Extracted: {len(main_data['features'])} features, "
                  f"{len(main_data['available_options'])} options")
            
        except Exception as e:
            print(f"      ⚠ Error extracting main section: {e}")
        
        return main_data
    
    def find_option_price_near_element(self, element):
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
    
    def click_main_section_buttons(self, main_section_height):
        """Click buttons in main section ONLY, skipping prohibited ones"""
        click_results = {
            'total_found': 0,
            'clicked': 0,
            'skipped_prohibited': 0,
            'skipped_already_processed': 0,
            'failed': 0
        }
        
        try:
            # Find all buttons in viewport
            all_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button, [role="button"]')
            
            main_section_buttons = []
            
            for button in all_buttons:
                try:
                    if button.is_displayed() and button.is_enabled():
                        # Check if button is in main section (top 80% of viewport)
                        location = button.location
                        if location['y'] < main_section_height:
                            main_section_buttons.append(button)
                except:
                    continue
            
            click_results['total_found'] = len(main_section_buttons)
            print(f"      Found {len(main_section_buttons)} buttons in main section")
            
            # Click each button
            for idx, button in enumerate(main_section_buttons, 1):
                button_id = self.generate_button_id(button)
                
                # Skip if already processed
                if button_id in self.processed_button_ids:
                    click_results['skipped_already_processed'] += 1
                    continue
                
                # Check for prohibited content
                button_text = button.text.strip().lower()
                if self.is_prohibited_button(button_text):
                    click_results['skipped_prohibited'] += 1
                    print(f"        [{idx}] Skipped (prohibited): {button_text[:30]}")
                    continue
                
                print(f"        [{idx}] Clicking: {button_text[:30]}")
                
                # Try to click
                if self.safe_click_with_esc(button):
                    click_results['clicked'] += 1
                    self.processed_button_ids.add(button_id)
                else:
                    click_results['failed'] += 1
                
                # Small delay
                time.sleep(0.5)
            
            print(f"      Results: {click_results['clicked']} clicked, "
                  f"{click_results['skipped_prohibited']} skipped (prohibited), "
                  f"{click_results['skipped_already_processed']} skipped (processed)")
            
        except Exception as e:
            print(f"      ⚠ Error clicking buttons: {e}")
        
        return click_results
    
    def is_prohibited_button(self, button_text):
        """Check if button contains prohibited content"""
        if not button_text:
            return False
        
        for prohibited in self.prohibited_contents:
            if prohibited in button_text:
                return True
        
        return False
    
    def generate_button_id(self, button):
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
                    id_parts.append(f"class:{hash('_'.join(specific_classes[:2]))}")
            
            return '|'.join(id_parts) if id_parts else f"btn_{time.time()}"
            
        except:
            return f"btn_{time.time()}"
    
    def safe_click_with_esc(self, button):
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
    
    def close_popup_with_esc(self):
        """Close popup using ESC key"""
        try:
            # First try ESC key
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            
            # Check if popup still exists
            popup_selectors = [
                '.modal',
                '.popup',
                '[role="dialog"]',
                '.overlay'
            ]
            
            popup_still_exists = False
            for selector in popup_selectors:
                try:
                    popup = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if popup.is_displayed():
                        popup_still_exists = True
                        break
                except:
                    continue
            
            # If popup still exists, try again with longer wait
            if popup_still_exists:
                time.sleep(1)
                body.send_keys(Keys.ESCAPE)
                time.sleep(0.5)
                
                # If still exists, try specific close button
                if self.is_popup_visible():
                    self.try_specific_close_button()
            
        except Exception as e:
            print(f"          ⚠ ESC handling error: {e}")
    
    def is_popup_visible(self):
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
    
    def try_specific_close_button(self):
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
    
    def save_configurations(self):
        """Save all configuration data"""
        if not self.configurations:
            print("No configuration data to save!")
            return
        
        # Clean data
        cleaned_configs = []
        for config in self.configurations:
            cleaned = self.clean_config_data(config)
            if cleaned:
                cleaned_configs.append(cleaned)
        
        # Save detailed configurations
        with open('nissan_main_section_configurations.json', 'w', encoding='utf-8') as f:
            json.dump(cleaned_configs, f, indent=2, ensure_ascii=False)
        
        # Create summary
        summary = []
        for config in cleaned_configs:
            summary_config = {
                'car_name': config.get('car_name', ''),
                'model': config.get('vehicle_info', {}).get('model', ''),
                'trim': config.get('vehicle_info', {}).get('trim', ''),
                'total_msrp': config.get('pricing', {}).get('amount', 'N/A'),
                'features_count': len(config.get('features', [])),
                'options_count': len(config.get('available_options', [])),
                'buttons_clicked': config.get('click_statistics', {}).get('clicked', 0),
                'buttons_skipped': config.get('click_statistics', {}).get('skipped_prohibited', 0)
            }
            summary.append(summary_config)
        
        with open('nissan_main_section_summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Generate report
        self.generate_report(cleaned_configs)
        
        print(f"\n{'='*60}")
        print("MAIN SECTION PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Configurations processed: {len(cleaned_configs)}")
        print(f"✓ Detailed data: nissan_main_section_configurations.json")
        print(f"✓ Summary data: nissan_main_section_summary.json")
        print(f"✓ Report: main_section_report.txt")
        print(f"{'='*60}")
    
    def clean_config_data(self, config):
        """Clean configuration data"""
        if not config:
            return None
        
        # Remove None and empty values
        cleaned = {}
        for key, value in config.items():
            if value is not None:
                if isinstance(value, (dict, list)):
                    # Clean nested structures
                    if isinstance(value, dict):
                        cleaned_value = {k: v for k, v in value.items() 
                                       if v is not None and v != ''}
                    else:  # list
                        cleaned_value = [v for v in value 
                                       if v is not None and v != '']
                    
                    if cleaned_value:
                        cleaned[key] = cleaned_value
                elif value != '':
                    cleaned[key] = value
        
        return cleaned
    
    def generate_report(self, configurations):
        """Generate detailed report"""
        report_lines = [
            "="*70,
            "MAIN SECTION BUILD CONFIGURATION REPORT",
            "="*70,
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Vehicles Processed: {len(configurations)}",
            f"Prohibited Contents: {', '.join(self.prohibited_contents)}",
            ""
        ]
        
        total_clicks = 0
        total_skipped = 0
        
        for config_idx, config in enumerate(configurations, 1):
            report_lines.append(f"{'='*50}")
            report_lines.append(f"VEHICLE {config_idx}: {config.get('car_name', 'Unknown')}")
            report_lines.append(f"{'='*50}")
            
            # Vehicle info
            vehicle_info = config.get('vehicle_info', {})
            report_lines.append(f"Model: {vehicle_info.get('model', 'N/A')}")
            report_lines.append(f"Trim: {vehicle_info.get('trim', 'N/A')}")
            
            # Pricing
            pricing = config.get('pricing', {})
            report_lines.append(f"MSRP: {pricing.get('amount', 'N/A')}")
            
            # Click statistics
            click_stats = config.get('click_statistics', {})
            clicks = click_stats.get('clicked', 0)
            skipped = click_stats.get('skipped_prohibited', 0)
            total_clicks += clicks
            total_skipped += skipped
            
            report_lines.append(f"\nButton Clicks:")
            report_lines.append(f"  Clicked: {clicks}")
            report_lines.append(f"  Skipped (prohibited): {skipped}")
            report_lines.append(f"  Total found: {click_stats.get('total_found', 0)}")
            
            # Features summary
            features = config.get('features', [])
            report_lines.append(f"\nFeatures: {len(features)}")
            
            # Options summary
            options = config.get('available_options', [])
            report_lines.append(f"Available Options: {len(options)}")
            
            report_lines.append("")
        
        # Summary
        report_lines.append(f"\n{'='*70}")
        report_lines.append("OVERALL SUMMARY")
        report_lines.append(f"{'='*70}")
        report_lines.append(f"Total vehicles: {len(configurations)}")
        report_lines.append(f"Total buttons clicked: {total_clicks}")
        report_lines.append(f"Total buttons skipped (prohibited): {total_skipped}")
        
        if configurations:
            avg_clicks = total_clicks / len(configurations)
            avg_skipped = total_skipped / len(configurations)
            report_lines.append(f"Average clicks per vehicle: {avg_clicks:.1f}")
            report_lines.append(f"Average skipped per vehicle: {avg_skipped:.1f}")
        
        report_lines.append(f"\nProcessing Rules:")
        report_lines.append(f"• Only main section processed (no navigation)")
        report_lines.append(f"• ESC key used for popup closing")
        report_lines.append(f"• Prohibited buttons skipped")
        report_lines.append(f"{'='*70}")
        
        # Save report
        with open('main_section_report.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))


def main():
    """Main function to run main section configurator"""
    print("="*60)
    print("MAIN SECTION BUILD CONFIGURATOR")
    print("="*60)
    print("\nThis configurator will:")
    print("• Process ONLY main section (no navigation)")
    print("• Use ESC key for popup closing")
    print("• Skip prohibited buttons")
    print(f"\nProhibited button contents: change trim, compare, share, etc.")
    print(f"{'='*60}")
    
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