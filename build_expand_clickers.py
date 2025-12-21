"""
Smart Card Button Clicker - Clicks specific card buttons with icon and state checking
Only clicks buttons with PLUS icon (not minus/minus icon)
Also clicks Show More buttons
"""

import json
import time
from typing import List, Dict, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from base import NissanScraperBase


class SmartCardButtonClicker(NissanScraperBase):
    def __init__(self, headless: bool = False):
        super().__init__(headless)
        self.clicked_sections = []
        self.click_results = {}
        
        # Static classes to target (from analysis)
        self.CARD_BUTTON_CLASSES = [
            'sc-OkURm hDaMYr',  # Primary card button
            'sc-12670f55-2 kxoBpd'  # Inner container
        ]
        
        # Show More button classes (static)
        self.SHOW_MORE_BUTTON_CLASSES = [
            'sc-fhHczv cCMIhZ sc-51c52cc8-2 ixgEOY'
        ]
        
        # PLUS icon SVG path (to click)
        self.PLUS_ICON_PATH = "M17 11h-6v6H9v-6H3V9h6V3h2v6h6z"
        
        # MINUS icon SVG path (to skip)
        self.MINUS_ICON_PATH = "M17.3 11H2.7V9h14.6z"
        
        # Static classes to avoid clicking when expanded
        self.EXPANDED_CLASS_INDICATORS = [
            'sc-OkURm hDaMYr sc-12670f55-2 kxoBpd'  # When expanded
        ]

    def process_all_trims(self) -> None:
        """Process all trims from the JSON file"""
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
            
            # Process the build page
            result = self.process_single_page(build_link, trim)
            
            if result:
                successful += 1
                print(f"    ✓ Smart button clicking complete")
            else:
                failed += 1
                print(f"    ⚠ Failed to process page")
            
            print()
        
        # Save results
        self.save_click_results()
        
        self.print_summary(successful, failed)
    
    def print_banner(self):
        """Print program banner"""
        separator = "="*70
        print(f"\n{separator}")
        print("SMART CARD BUTTON CLICKER")
        print(separator)
        print("Rules:")
        print("• Only clicks buttons with PLUS (+) icon")
        print("• Skips buttons with MINUS (-) icon")
        print("• Clicks 'Show More' buttons")
        print("• Uses only STATIC classes, no dynamic selectors")
        print(separator + "\n")
    
    def print_processing_info(self, idx: int, trim: Dict, build_link: str):
        """Print processing information"""
        car_name = trim.get('car_name', 'Unknown')
        truncated_link = build_link[:80] + "..." if len(build_link) > 80 else build_link
        print(f"{idx:3d}. Processing: {car_name}")
        print(f"    Link: {truncated_link}")
    
    def print_summary(self, successful: int, failed: int):
        """Print processing summary"""
        separator = "="*70
        print(f"\n{separator}")
        print("PROCESSING COMPLETE")
        print(separator)
        print(f"✓ Successful: {successful}")
        print(f"✗ Failed: {failed}")
        print(f"Total: {successful + failed}")
        print(separator)
    
    def process_single_page(self, url: str, trim_info: Dict) -> bool:
        """Process a single build page with smart clicking"""
        try:
            # Navigate to page
            print("      Navigating to build page...")
            self.driver.get(url)
            time.sleep(4)
            
            # Handle any initial popups
            self.handle_initial_popups()
            
            # Wait for page to load
            self.wait_for_page_load()
            
            # Take before screenshot
            before_screenshot = f"before_click_{trim_info.get('id', '0')}_{int(time.time())}.png"
            self.driver.save_screenshot(before_screenshot)
            
            # Click all card section buttons (with icon checking)
            card_results = self.click_card_buttons_with_icon_check()
            
            # Click Show More buttons
            show_more_results = self.click_show_more_buttons()
            
            # Take after screenshot
            time.sleep(2)
            after_screenshot = f"after_click_{trim_info.get('id', '0')}_{int(time.time())}.png"
            self.driver.save_screenshot(after_screenshot)
            
            # Store combined results
            self.click_results[trim_info.get('car_name', 'Unknown')] = {
                'url': url,
                'trim_info': trim_info,
                'card_button_results': card_results,
                'show_more_results': show_more_results,
                'screenshots': {
                    'before': before_screenshot,
                    'after': after_screenshot
                }
            }
            
            return True
            
        except Exception as e:
            print(f"    ✗ Error processing page: {str(e)[:100]}")
            return False
    
    def handle_initial_popups(self):
        """Handle initial popups with ESC key"""
        try:
            # Try ESC key
            print("      Pressing ESC to close any popups...")
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ESCAPE)
            time.sleep(1)
            
            # Try common close buttons
            close_selectors = [
                'button.close',
                '.close-button',
                '[aria-label="Close"]',
                '[class*="close"]'
            ]
            
            for selector in close_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed():
                            self._safe_click(button)
                            time.sleep(1)
                            break
                except:
                    continue
                    
        except Exception as e:
            print(f"      ⚠ Error handling popups: {e}")
    
    def wait_for_page_load(self):
        """Wait for page to load"""
        try:
            # Wait for main content
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            
            # Wait for specific static Nissan elements
            static_selectors = [
                '.sc-OkURm.hDaMYr',
                '.sc-12670f55-2.kxoBpd',
                '[data-testid*="NGST_QA"]'
            ]
            
            for selector in static_selectors:
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"      ✓ Found static elements with: {selector}")
                    break
                except:
                    continue
            
            print(f"      ✓ Page loaded successfully")
            
        except Exception as e:
            print(f"      ⚠ Error waiting for page load: {e}")
    
    def click_card_buttons_with_icon_check(self) -> Dict:
        """Click card buttons only if they have PLUS icon"""
        results = {
            'total_buttons_found': 0,
            'buttons_with_plus_icon': 0,
            'buttons_with_minus_icon': 0,
            'buttons_clicked': 0,
            'buttons_skipped': 0,
            'buttons_failed': 0,
            'sections_clicked': [],
            'sections_skipped': []
        }
        
        try:
            print("      Looking for card buttons with icon checking...")
            
            # Find all potential card buttons
            all_buttons = self.find_all_card_buttons()
            results['total_buttons_found'] = len(all_buttons)
            
            print(f"      Found {len(all_buttons)} potential card buttons")
            
            # Process each button
            for idx, button in enumerate(all_buttons, 1):
                self.process_single_card_button(idx, button, results)
            
            # Print summary
            self.print_card_button_summary(results)
            
        except Exception as e:
            print(f"      ⚠ Error in card button clicking: {e}")
            results['error'] = str(e)
        
        return results
    
    def find_all_card_buttons(self) -> List[WebElement]:
        """Find all card buttons using STATIC class selectors only"""
        all_buttons = []
        
        # Strategy 1: Primary card button selector
        try:
            buttons1 = self.driver.find_elements(
                By.CSS_SELECTOR, 'div.sc-OkURm.hDaMYr[role="button"]'
            )
            if buttons1:
                all_buttons.extend(buttons1)
                print(f"        Found {len(buttons1)} buttons with primary selector")
        except:
            pass
        
        # Strategy 2: Inner container with specific class
        try:
            containers = self.driver.find_elements(
                By.CSS_SELECTOR, 'div.sc-12670f55-2.kxoBpd'
            )
            for container in containers:
                try:
                    # Find button inside
                    button = container.find_element(
                        By.XPATH, './parent::div[contains(@class, "sc-OkURm")]'
                    )
                    if button not in all_buttons:
                        all_buttons.append(button)
                except:
                    continue
        except:
            pass
        
        # Remove duplicates
        return self.remove_duplicate_elements(all_buttons)
    
    def process_single_card_button(self, idx: int, button: WebElement, results: Dict):
        """Process a single card button with icon checking"""
        section_name = self.get_section_name(button)
        
        print(f"        [{idx}] Checking: {section_name}")
        
        try:
            # Check the icon
            icon_type = self.get_button_icon_type(button)
            
            if icon_type == "PLUS":
                results['buttons_with_plus_icon'] += 1
                print(f"          Found PLUS icon - will click")
                
                # Click the button
                if self.click_button_safely(button, section_name):
                    results['buttons_clicked'] += 1
                    results['sections_clicked'].append(section_name)
                else:
                    results['buttons_failed'] += 1
                    
            elif icon_type == "MINUS":
                results['buttons_with_minus_icon'] += 1
                print(f"          Found MINUS icon - skipping")
                results['buttons_skipped'] += 1
                results['sections_skipped'].append(section_name)
                
            else:
                print(f"          Unknown icon type - skipping")
                results['buttons_skipped'] += 1
                
        except Exception as e:
            print(f"          ⚠ Error processing button: {e}")
            results['buttons_failed'] += 1
    
    def get_button_icon_type(self, button: WebElement) -> str:
        """Determine if button has PLUS or MINUS icon"""
        try:
            # Find SVG element inside button
            svg_element = button.find_element(By.CSS_SELECTOR, 'svg')
            
            # Get the SVG inner HTML
            svg_html = svg_element.get_attribute('innerHTML')
            
            if self.PLUS_ICON_PATH in svg_html:
                return "PLUS"
            elif self.MINUS_ICON_PATH in svg_html:
                return "MINUS"
            else:
                return "UNKNOWN"
                
        except Exception as e:
            # If no SVG found, try to check aria-expanded
            try:
                aria_expanded = button.get_attribute('aria-expanded')
                if aria_expanded == 'true':
                    return "MINUS"  # Probably expanded
                elif aria_expanded == 'false':
                    return "PLUS"   # Probably collapsed
            except:
                pass
            
            return "UNKNOWN"
    
    def click_button_safely(self, button: WebElement, section_name: str) -> bool:
        """Safely click a button"""
        try:
            # Scroll to button
            self._scroll_to_element(button)
            time.sleep(0.3)
            
            # Check if button is clickable
            if not button.is_displayed() or not button.is_enabled():
                print(f"          ⚠ Button not clickable")
                return False
            
            # Get state before click
            state_before = button.get_attribute('aria-expanded')
            print(f"          State before: aria-expanded='{state_before}'")
            
            # Click the button
            try:
                button.click()
                print(f"          Clicked successfully")
            except:
                # Try JavaScript click
                self.driver.execute_script("arguments[0].click();", button)
                print(f"          Clicked via JavaScript")
            
            # Wait for animation
            time.sleep(1.5)
            
            # Get state after click
            state_after = button.get_attribute('aria-expanded')
            print(f"          State after: aria-expanded='{state_after}'")
            
            # Take screenshot of this specific section
            try:
                timestamp = int(time.time())
                self.driver.save_screenshot(f"section_{section_name.replace(' ', '_')}_{timestamp}.png")
            except:
                pass
            
            return True
            
        except Exception as e:
            print(f"          ⚠ Failed to click: {e}")
            return False
    
    def print_card_button_summary(self, results: Dict):
        """Print card button click summary"""
        print(f"      Card Button Summary:")
        print(f"        Total found: {results['total_buttons_found']}")
        print(f"        With PLUS icon: {results['buttons_with_plus_icon']}")
        print(f"        With MINUS icon: {results['buttons_with_minus_icon']}")
        print(f"        Clicked: {results['buttons_clicked']}")
        print(f"        Skipped: {results['buttons_skipped']}")
        print(f"        Failed: {results['buttons_failed']}")
        
        if results['sections_clicked']:
            print(f"        Sections clicked: {', '.join(results['sections_clicked'])}")
        
        if results['sections_skipped']:
            print(f"        Sections skipped: {', '.join(results['sections_skipped'])}")
    
    def click_show_more_buttons(self) -> Dict:
        """Click all Show More buttons (with static class checking)"""
        results = {
            'total_found': 0,
            'clicked': 0,
            'failed': 0,
            'buttons_found': []
        }
        
        try:
            print("      Looking for Show More buttons...")
            
            # Find Show More buttons with static class
            show_more_buttons = self.driver.find_elements(
                By.CSS_SELECTOR, 'button.sc-fhHczv.cCMIhZ.sc-51c52cc8-2.ixgEOY'
            )
            
            results['total_found'] = len(show_more_buttons)
            
            if show_more_buttons:
                print(f"        Found {len(show_more_buttons)} Show More buttons")
                
                for idx, button in enumerate(show_more_buttons, 1):
                    button_text = button.text.strip() or "Show More"
                    print(f"        [{idx}] Clicking: {button_text}")
                    
                    # Check if button is clickable
                    if button.is_displayed() and button.is_enabled():
                        try:
                            # Scroll to button
                            self._scroll_to_element(button)
                            time.sleep(0.3)
                            
                            # Click the button
                            try:
                                button.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", button)
                            
                            results['clicked'] += 1
                            results['buttons_found'].append(button_text)
                            print(f"          ✓ Clicked successfully")
                            
                            # Wait a bit
                            time.sleep(1)
                            
                        except Exception as e:
                            results['failed'] += 1
                            print(f"          ⚠ Failed to click: {e}")
                    else:
                        results['failed'] += 1
                        print(f"          ⚠ Button not clickable")
            else:
                print(f"        No Show More buttons found")
                
        except Exception as e:
            print(f"      ⚠ Error finding Show More buttons: {e}")
            results['error'] = str(e)
        
        return results
    
    def get_section_name(self, button: WebElement) -> str:
        """Extract section name from button"""
        try:
            # Look for h3 with data-testid
            h3_element = button.find_element(By.CSS_SELECTOR, 'h3[data-testid]')
            data_testid = h3_element.get_attribute('data-testid')
            
            if data_testid and 'NGST_QA_' in data_testid:
                # Extract section name from data-testid
                # Format: NGST_QA_Drivetrain_label -> Drivetrain
                section = data_testid.replace('NGST_QA_', '').replace('_label', '')
                return section
            
            # Fallback to text
            return h3_element.text.strip() or "Unknown Section"
            
        except:
            try:
                # Try any h3
                h3_element = button.find_element(By.CSS_SELECTOR, 'h3')
                return h3_element.text.strip() or "Unknown Section"
            except:
                return "Unknown Section"
    
    def remove_duplicate_elements(self, elements: List[WebElement]) -> List[WebElement]:
        """Remove duplicate web elements"""
        unique_elements = []
        seen = set()
        
        for element in elements:
            try:
                # Create a unique identifier
                try:
                    element_id = element.id if element.id else ""
                except:
                    element_id = ""
                
                location = element.location
                location_key = f"{location['x']}_{location['y']}"
                
                unique_key = f"{element_id}_{location_key}"
                
                if unique_key not in seen:
                    seen.add(unique_key)
                    unique_elements.append(element)
            except:
                unique_elements.append(element)
        
        return unique_elements
    
    def save_click_results(self):
        """Save click results to JSON file"""
        if not self.click_results:
            print("No click results to save!")
            return
        
        # Save detailed results
        with open('smart_card_clicks.json', 'w', encoding='utf-8') as f:
            json.dump(self.click_results, f, indent=2, ensure_ascii=False)
        
        # Create summary
        summary = self.create_summary()
        
        with open('smart_card_clicks_summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*70)
        print("RESULTS SAVED")
        print("="*70)
        print(f"✓ Detailed results: smart_card_clicks.json")
        print(f"✓ Summary: smart_card_clicks_summary.json")
        print("="*70)
    
    def create_summary(self) -> List[Dict]:
        """Create summary of click results"""
        summary = []
        
        for car_name, data in self.click_results.items():
            card_results = data.get('card_button_results', {})
            show_more_results = data.get('show_more_results', {})
            
            summary_entry = {
                'car_name': car_name,
                'url': data.get('url', ''),
                'card_buttons': {
                    'total_found': card_results.get('total_buttons_found', 0),
                    'with_plus_icon': card_results.get('buttons_with_plus_icon', 0),
                    'with_minus_icon': card_results.get('buttons_with_minus_icon', 0),
                    'clicked': card_results.get('buttons_clicked', 0),
                    'sections_clicked': card_results.get('sections_clicked', [])
                },
                'show_more_buttons': {
                    'total_found': show_more_results.get('total_found', 0),
                    'clicked': show_more_results.get('clicked', 0),
                    'buttons_found': show_more_results.get('buttons_found', [])
                },
                'screenshots': data.get('screenshots', {})
            }
            
            summary.append(summary_entry)
        
        return summary


# Function to integrate into your existing BuildConfigurator
def integrate_with_build_configurator():
    """Example of how to integrate with your existing BuildConfigurator"""
    
    # Add this method to your BuildConfigurator class:
    """
    def smart_click_card_buttons(self):
        ""
        Smart clicking of card buttons (only PLUS icons) and Show More buttons
        ""
        # Create smart clicker instance
        smart_clicker = SmartCardButtonClicker(headless=self.headless)
        smart_clicker.driver = self.driver  # Use existing driver
        
        # Click card buttons with icon checking
        card_results = smart_clicker.click_card_buttons_with_icon_check()
        
        # Click Show More buttons
        show_more_results = smart_clicker.click_show_more_buttons()
        
        return {
            'card_button_results': card_results,
            'show_more_results': show_more_results
        }
    """
    
    # Then in your scrape_main_section_only method, call it:
    """
    def scrape_main_section_only(self, build_link, trim_info):
        config_data = trim_info.copy()
        
        try:
            # ... existing navigation code ...
            
            # ✅ NEW: Smart card button clicking
            print("      Smart clicking card buttons...")
            smart_click_results = self.smart_click_card_buttons()
            config_data['smart_card_clicks'] = smart_click_results
            
            # ... rest of your code ...
    """


def main():
    """Main function"""
    print("="*70)
    print("SMART CARD BUTTON CLICKER")
    print("="*70)
    print("\nRules:")
    print("1. Only clicks buttons with PLUS (+) icon")
    print("2. Skips buttons with MINUS (-) icon")  
    print("3. Clicks 'Show More' buttons")
    print("4. Uses only STATIC classes")
    print("\n" + "="*70)
    
    confirm = input("\nContinue? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("Operation cancelled.")
        return
    
    # Create and run clicker
    clicker = SmartCardButtonClicker(headless=False)
    
    try:
        clicker.process_all_trims()
    except KeyboardInterrupt:
        print("\n\n⚠ Process interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        clicker.close()


def test_specific_page():
    """Test on a specific page"""
    print("="*70)
    print("TEST SPECIFIC PAGE")
    print("="*70)
    
    url = input("\nEnter URL to test: ").strip()
    
    if not url:
        print("No URL provided.")
        return
    
    clicker = SmartCardButtonClicker(headless=False)
    
    try:
        # Navigate to page
        print(f"\nTesting URL: {url}")
        clicker.driver.get(url)
        time.sleep(4)
        
        # Test icon detection
        print("\n" + "="*70)
        print("TESTING ICON DETECTION")
        print("="*70)
        
        # Find all card buttons
        all_buttons = clicker.find_all_card_buttons()
        print(f"\nFound {len(all_buttons)} card buttons:")
        
        for idx, button in enumerate(all_buttons, 1):
            section_name = clicker.get_section_name(button)
            icon_type = clicker.get_button_icon_type(button)
            print(f"{idx}. {section_name} - Icon: {icon_type}")
            
            # Show SVG path if available
            try:
                svg = button.find_element(By.CSS_SELECTOR, 'svg')
                svg_html = svg.get_attribute('innerHTML')
                if clicker.PLUS_ICON_PATH in svg_html:
                    print(f"   Contains PLUS path: ✓")
                elif clicker.MINUS_ICON_PATH in svg_html:
                    print(f"   Contains MINUS path: ✓")
            except:
                pass
        
        # Click buttons
        print("\n" + "="*70)
        print("CLICKING BUTTONS")
        print("="*70)
        
        card_results = clicker.click_card_buttons_with_icon_check()
        show_more_results = clicker.click_show_more_buttons()
        
        print("\n" + "="*70)
        print("TEST COMPLETE")
        print("="*70)
        
        input("\nPress Enter to close...")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        clicker.close()


if __name__ == "__main__":
    print("Choose option:")
    print("1. Process all trims from JSON file")
    print("2. Test specific URL")
    print("3. Integrate with existing BuildConfigurator")
    
    choice = input("\nEnter choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        main()
    elif choice == "2":
        test_specific_page()
    elif choice == "3":
        integrate_with_build_configurator()
        print("\nIntegration code has been displayed above.")
        print("Copy the methods into your BuildConfigurator class.")
    else:
        print("Invalid choice.")