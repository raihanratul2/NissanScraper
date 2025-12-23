"""
Nissan Build Page Scraper
NissanScraperBase থেকে inherit করা হয়েছে
নির্দিষ্ট data-testid সিলেক্টর ব্যবহার করে
"""

import json
import time
import re
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from base import NissanScraperBase
from build_expand_clickers import SmartCardButtonClicker, main as clicker


class NissanBuildPageScraper(NissanScraperBase):
    def __init__(self, headless=False):
        super().__init__(headless)
        # self.headless = headless
        self.current_data = {}
        self.scraping_log = []
        
        # Section configuration based on your structure
        self.section_config = {
            "powertrain": {
                "id": "powertrain",
                "subsections": {
                    "drivetrain": {
                        "label": '[data-testid="NGST_QA_Drivetrain_label"]',
                        "cards": {
                            "list": '[data-testid="NGST_QA_option_list"]',
                            "item": "li"
                        }
                    }
                }
            },
            "exterior": {
                "id": "exterior",
                "color_section": {
                    "id": "exterior.colour",
                    "standard": {
                        "anchors": {
                        "primary_xpath": "//h4[normalize-space()='Standard']/parent::div",
                        "fallback_xpath": "//div[h4 and .//img[contains(@alt,'Exterior Color')]]"
                        },
                        "colors": {
                        "color_button": {
                            "css": "button",
                            "fallback_xpath": ".//button[.//img]"
                        },
                        "name": {
                            "css": "p",
                            "fallback_xpath": ".//p[normalize-space()]"
                        },
                        "image": {
                            "css": "img",
                            "fallback_xpath": ".//img[contains(@alt,'Exterior')]"
                        }
                        }
                    },

                    "premium": {
                        "anchors": {
                        "primary_xpath": "//h4[normalize-space()='Premium Colors']/parent::div",
                        "fallback_xpath": "//div[h4 and .//p[contains(text(),'$')]]"
                        },
                        "colors": {
                        "color_button": {
                            "css": "button",
                            "fallback_xpath": ".//button[.//p[contains(text(),'$')]]"
                        },
                        "name": {
                            "css": "div > p",
                            "fallback_xpath": ".//p[not(contains(text(),'$'))]"
                        },
                        "price": {
                            "css": "div > p:first-child",
                            "fallback_xpath": ".//p[contains(text(),'$')]"
                        },
                        "image": {
                            "css": "img",
                            "fallback_xpath": ".//img[contains(@alt,'Exterior')]"
                        }
                        }
                    }
                },
                "wheels": {
                    "id": "wheels",
                    "anchors": {
                    "primary_xpath": "//h3[normalize-space()='Wheels']/ancestor::div[@id='wheels']",
                    "fallback_xpath": "//div[@data-testid='NGST_QA_rail_section' and .//h3]"
                    },
                    "options": {
                        "container": {
                            "primary_xpath": ".//ul[@data-testid='NGST_QA_option_list']",
                            "fallback_xpath": ".//ul[.//li]"
                        },
                        "item": {
                            "css": "li",
                            "fallback_xpath": ".//li[.//img]"
                        },
                        "name": {
                            "css": "p[id$='_title']",
                            "fallback_xpath": ".//p[normalize-space() and not(contains(text(),'$'))]"
                        },
                        "price": {
                            "css": "p:has(span)",
                            "fallback_xpath": ".//p[contains(text(),'$')]"
                        },
                        "image": {
                            "css": "img",
                            "fallback_xpath": ".//img[contains(@alt,'Wheels')]"
                        },
                        "details_button": {
                            "css": "button[data-testid='NGST_QA_details_button']",
                            "fallback_xpath": ".//button[normalize-space()='Details']"
                        },
                        "add_button": {
                            "css": "button:last-child",
                            "fallback_xpath": ".//button[normalize-space()='Add']"
                        }
                    }
                }
            },
            "interior": {
                "id": "interior",
                "main_label": '[data-testid="interior"]',
                "fabric_color": {
                    "label": '[data-testid="NGST_QA_Color and Fabrics_label"]',
                    "cards": {
                        "list": '[data-testid="NGST_QA_option_list"]',
                        "item": "li"
                    }
                }
            },
            "packages": {
                "main_label": '[data-testid="packages"]',
                "sub_packages": {
                    "label": '[data-testid="NGST_QA_Packages_label"]',
                    "cards": {
                        "list": '[data-testid="NGST_QA_option_list"]',
                        "item": "li"
                    }
                }
            },
            "accessories": {
                "id": "accessories",
                "section_id": '[data-section-id="accessories"]',
                "sections": {
                    "container": '[data-testid="NGST_QA_rail_section"]'
                }
            }
        }
        
        # Common selectors
        self.COMMON_SELECTORS = {
            "section": {
                "container": '[data-testid="NGST_QA_rail_section"]',
                "title": 'h3[data-testid]',
                "cards_list": '[data-testid="NGST_QA_option_list"]',
                "card_item": 'li[data-testid]'
            },
            "card": {
                # radio wrapper (selection state)
                "radio_button": 'div[role="radio"]',

                # image (alt is stable)
                "image": 'div[role="radio"] img',

                # name → id always ends with _title
                "name": 'p[id$="_title"]',

                # price → only if exists (wheels / accessories)
                "price": 'p:has(span)',

                # details button (data-testid is solid)
                "details_button": '[data-testid="NGST_QA_details_button"]',

                # selected state (checked radio)
                "is_selected": 'div[role="radio"][aria-checked="true"]'
            },
            "details_modal": {
                "container": '[data-testid="NGST_QA_option_detail"]',
                "image": 'img',
                "name": 'h2',
                "subname": 'h3',
                "price": './/p[contains(text(),"$")]',
                "specification": './/div[.//ul]',
                "description": './/p'
            },

            # absolute xpath avoid করলে ভালো, তাও রাখলাম
            "main_image": "//main//img[contains(@alt,'Exterior') or contains(@alt,'Interior')]"
        }
    
    def smart_click_card_buttons(self):
        """
        Smart clicking of card buttons (only PLUS icons) and Show More buttons
        """
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
    
    def log_scraping(self, level, message):
        """Log scraping activities"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message[:500]
        }
        self.scraping_log.append(log_entry)
        self.current_data.setdefault("scraping_log", []).append(log_entry)
    
    def extract_main_image(self):
        """Extract main car image"""
        try:
            main_img_element = self.driver.find_element(
                By.XPATH, self.COMMON_SELECTORS["main_image"]
            )
            main_image_url = main_img_element.get_attribute("src")
            self.current_data["main_image"] = main_image_url
            self.log_scraping("info", f"Main image extracted: {main_image_url[:50]}...")
            return main_image_url
        except Exception as e:
            self.log_scraping("error", f"Main image extraction failed: {str(e)}")
            return None
    def run_smart_click_before_scraping(driver, headless=False):
        """
        Run SmartCardButtonClicker logic on the CURRENTLY LOADED build page
        without reloading or navigating away.
        Call this right after page load, before scraping starts.
        """
        try:
            print("      ▶ Running smart card button clicker (pre-scrape)...")

            smart_clicker = SmartCardButtonClicker(headless=headless)

            # 🔑 CRITICAL: reuse same driver & same page
            smart_clicker.driver = driver

            # Safety wait (React hydration complete)
            time.sleep(2)

            # Handle popups if any
            smart_clicker.handle_initial_popups()

            # Click PLUS-icon card buttons
            card_results = smart_clicker.click_card_buttons_with_icon_check()

            # Click Show More buttons
            show_more_results = smart_clicker.click_show_more_buttons()

            print("      ✓ Smart clicking finished, scraping can start now")

            return {
                "card_button_results": card_results,
                "show_more_results": show_more_results
            }

        except Exception as e:
            print(f"      ⚠ Smart clicker failed: {e}")
            return {
                "error": str(e)
            }

    def initialize_scraping(self, build_url):
        """Initialize scraping process for a build URL"""
        self.current_data = {
            "url": build_url,
            "scraped_at": datetime.now().isoformat(),
            "vehicle_info": {},
            "main_image": "",
            "sections": {},
            "scraping_log": []
        }
        
        try:
            print(f"\n{'='*60}")
            print(f"Processing: {build_url}")
            print(f"{'='*60}")
            
            # Navigate to URL
            print("1. Navigating to build page...")
            self.driver.get(build_url)
            time.sleep(3)
            
            
            # Wait for page to load
            print("3. Waiting for page to load...")
            self._wait_for_page_load()
            
            # Scroll to load all content
            print("4. Scrolling page...")
            self._scroll_page_gradually()
            
            # Handle initial popups using base class methods
            print("2. Handling popups and cookies...")
            self._handle_cookies_popup()
            self._close_popups()
            print("clicking card expand buttons...")
            
            self.run_smart_click_before_scraping(self.driver)
            time.sleep(1)

            # Extract main image
            print("5. Extracting main image...")
            self.extract_main_image()
            
            # Reload to ensure fresh state (as per your workflow)
            print("6. Reloading page for fresh state...")
            self.driver.refresh()
            time.sleep(2)
            self._scroll_page_gradually()
            
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {str(e)}")
            self.log_scraping("error", f"Initialization failed: {str(e)}")
            return False
    
    def _wait_for_page_load(self, timeout=10):
        """Wait for page to fully load"""
        try:
            # Wait for main container
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.COMMON_SELECTORS["section"]["container"]))
            )
            self.log_scraping("info", "Page loaded successfully")
            return True
        except TimeoutException:
            self.log_scraping("warning", "Page load timeout")
            return False
    
    def process_all_sections(self):
        """Process all sections on the build page"""
        print("\n7. Processing all sections...")
        
        # Get all section containers
        try:
            section_containers = self.driver.find_elements(
                By.CSS_SELECTOR, self.COMMON_SELECTORS["section"]["container"]
            )
            print(f"Found {len(section_containers)} section containers")
            
        except Exception as e:
            print(f"❌ Error finding sections: {e}")
            self.log_scraping("error", f"Section finding failed: {str(e)}")
            return
        
        # Process each section
        for idx, container in enumerate(section_containers):
            try:
                # Get section title
                title_element = container.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["section"]["title"]
                )
                section_title = title_element.text.strip()
                
                print(f"\n  Section {idx+1}: {section_title}")
                
                # Scroll to section
                self._scroll_to_element(container)
                time.sleep(0.5)
                
                # Process based on section type
                section_data = self._process_section_by_type(container, section_title)
                
                if section_data:
                    self.current_data["sections"][section_title] = section_data
                    
            except Exception as e:
                print(f"  ⚠ Error processing section: {e}")
                self.log_scraping("warning", f"Section processing error: {str(e)}")
                continue
    
    def _process_section_by_type(self, container, section_title):
        """Process section based on its type"""
        section_data = {
            "type": "generic",
            "cards": [],
            "processed_at": datetime.now().isoformat()
        }
        
        # Check for specific section types
        section_lower = section_title.lower()
        
        if "powertrain" in section_lower or "drivetrain" in section_lower:
            return self.scrape_powertrain(container)
        elif "exterior" in section_lower:
            return self.scrape_exterior(container)
        elif "interior" in section_lower:
            return self.scrape_interior(container)
        elif "package" in section_lower:
            return self.scrape_packages(container)
        elif "accessor" in section_lower:
            return self.scrape_accessories(container)
        else:
            # Generic section processing
            return self._process_generic_section(container)
    
    def _process_generic_section(self, container):
        """Process generic section with cards"""
        section_data = {
            "type": "generic",
            "cards": []
        }
        
        try:
            # Get all cards
            cards_list = container.find_element(
                By.CSS_SELECTOR, self.COMMON_SELECTORS["section"]["cards_list"]
            )
            cards = cards_list.find_elements(
                By.TAG_NAME, self.COMMON_SELECTORS["section"]["card_item"]
            )
            
            print(f"    Found {len(cards)} cards")
            
            # Process each card
            for card_idx, card in enumerate(cards[:5]):  # Limit to first 5 for testing
                try:
                    card_data = self._process_card(card, f"card_{card_idx}")
                    if card_data:
                        section_data["cards"].append(card_data)
                except Exception as e:
                    print(f"      ⚠ Card {card_idx} error: {e}")
                    continue
                    
        except Exception as e:
            print(f"    ⚠ Generic section error: {e}")
            section_data["error"] = str(e)
        
        return section_data
    
    def _process_card(self, card_element, card_id="unknown"):
        """Process individual card"""
        card_data = {
            "id": card_id,
            "basic_info": {},
            "detailed_info": {}
        }
        
        try:
            # Extract basic info from card
            basic_info = self._extract_card_basic_info(card_element)
            card_data["basic_info"] = basic_info
            
            # Check for details button and extract detailed info
            try:
                details_button = card_element.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["card"]["details_button"]
                )
                
                if details_button.is_displayed() and details_button.is_enabled():
                    detailed_info = self._extract_card_details(details_button)
                    card_data["detailed_info"] = detailed_info
                    
            except NoSuchElementException:
                pass  # No details button
            
        except Exception as e:
            print(f"        ⚠ Card processing error: {e}")
            card_data["error"] = str(e)
        
        return card_data
    
    def _extract_card_basic_info(self, card_element):
        """Extract basic information from card"""
        basic_info = {}
        
        try:
            # Image
            try:
                img_element = card_element.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["card"]["image"]
                )
                basic_info["image"] = img_element.get_attribute("src")
                basic_info["image_alt"] = img_element.get_attribute("alt") or ""
            except:
                basic_info["image"] = ""
            
            # Name
            try:
                name_element = card_element.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["card"]["name"]
                )
                basic_info["name"] = name_element.text.strip()
            except:
                basic_info["name"] = ""
            
            # Price
            try:
                price_element = card_element.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["card"]["price"]
                )
                basic_info["price"] = price_element.text.strip()
            except:
                basic_info["price"] = ""
            
            # Category
            try:
                category_element = card_element.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["card"]["category"]
                )
                basic_info["category"] = category_element.text.strip()
            except:
                basic_info["category"] = ""
            
            # Check if selected (radio button)
            try:
                radio_button = card_element.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["card"]["radio_button"]
                )
                aria_checked = radio_button.get_attribute("aria-checked")
                basic_info["selected"] = aria_checked == "true"
            except:
                basic_info["selected"] = False
            
        except Exception as e:
            print(f"          ⚠ Basic info extraction error: {e}")
        
        return basic_info
    
    def _extract_card_details(self, details_button):
        """Extract detailed information by clicking details button"""
        detailed_info = {}
        
        try:
            # Click details button
            self._scroll_to_element(details_button)
            self._safe_click(details_button)
            time.sleep(1.5)  # Wait for modal to open
            
            # Extract modal information
            try:
                modal = self.driver.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["details_modal"]["container"]
                )
                
                if modal.is_displayed():
                    # Extract all details
                    detailed_info = self._extract_modal_details(modal)
                    
            except NoSuchElementException:
                print("          Modal not found after clicking details")
            
            # Close modal
            self._close_modal()
            
        except Exception as e:
            print(f"          ⚠ Details extraction error: {e}")
        
        return detailed_info
    
    def _extract_modal_details(self, modal):
        """Extract details from modal"""
        details = {}
        
        try:
            # Image
            try:
                img_element = modal.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["details_modal"]["image"]
                )
                details["detailed_image"] = img_element.get_attribute("src")
                details["detailed_image_alt"] = img_element.get_attribute("alt") or ""
            except:
                pass
            
            # Name
            try:
                name_element = modal.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["details_modal"]["name"]
                )
                details["detailed_name"] = name_element.text.strip()
            except:
                pass
            
            # Subname
            try:
                subname_element = modal.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["details_modal"]["subname"]
                )
                details["subname"] = subname_element.text.strip()
            except:
                pass
            
            # Price
            try:
                price_element = modal.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["details_modal"]["price"]
                )
                details["detailed_price"] = price_element.text.strip()
            except:
                pass
            
            # Specification
            try:
                spec_element = modal.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["details_modal"]["specification"]
                )
                details["specifications"] = spec_element.text.strip()
            except:
                pass
            
            # Description
            try:
                desc_element = modal.find_element(
                    By.CSS_SELECTOR, self.COMMON_SELECTORS["details_modal"]["description"]
                )
                details["description"] = desc_element.text.strip()
            except:
                pass
            
            # Get all text content as fallback
            try:
                details["full_text"] = modal.text[:1000]  # Limit to 1000 chars
            except:
                pass
                
        except Exception as e:
            print(f"            ⚠ Modal details error: {e}")
        
        return details
    
    def _close_modal(self):
        """Close modal using various methods"""
        try:
            # Try pressing Escape
            from selenium.webdriver.common.keys import Keys
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            
            # Try clicking close buttons
            close_selectors = [
                'button[aria-label*="Close"]',
                '.close-button',
                '[class*="close"]',
                'svg[class*="close"]'
            ]
            
            for selector in close_selectors:
                try:
                    close_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in close_buttons:
                        if button.is_displayed():
                            button.click()
                            time.sleep(0.5)
                            break
                except:
                    continue
                    
        except Exception as e:
            print(f"            ⚠ Modal close error: {e}")
    
    def scrape_powertrain(self, container):
        """Scrape powertrain section"""
        print("    Processing Powertrain section...")
        
        powertrain_data = {
            "type": "powertrain",
            "drivetrain": {
                "options": []
            }
        }
        
        try:
            # Find drivetrain label
            drivetrain_label = container.find_element(
                By.CSS_SELECTOR, self.section_config["powertrain"]["subsections"]["drivetrain"]["label"]
            )
            powertrain_data["drivetrain"]["label"] = drivetrain_label.text.strip()
            
            # Find drivetrain cards
            cards_list = container.find_element(
                By.CSS_SELECTOR, self.section_config["powertrain"]["subsections"]["drivetrain"]["cards"]["list"]
            )
            cards = cards_list.find_elements(
                By.TAG_NAME, self.section_config["powertrain"]["subsections"]["drivetrain"]["cards"]["item"]
            )
            
            print(f"      Found {len(cards)} drivetrain options")
            
            # Process each drivetrain option
            for idx, card in enumerate(cards[:3]):  # Limit to 3
                try:
                    option_data = self._process_card(card, f"drivetrain_{idx}")
                    powertrain_data["drivetrain"]["options"].append(option_data)
                except Exception as e:
                    print(f"        ⚠ Drivetrain option {idx} error: {e}")
                    continue
                    
        except Exception as e:
            print(f"    ⚠ Powertrain scraping error: {e}")
            powertrain_data["error"] = str(e)
        
        return powertrain_data
    
    def scrape_exterior(self, container):
        """Scrape exterior section with colors, cards, and wheels"""
        print("    Processing Exterior section...")
        
        exterior_data = {
            "type": "exterior",
            "colors": {"standard": [], "premium": []},
            "cards": [],
            "wheels": []
        }

        def safe_find_element(parent, by, value, fallback_by=None, fallback_value=None):
            try:
                return parent.find_element(by, value)
            except:
                if fallback_by and fallback_value:
                    try:
                        return parent.find_element(fallback_by, fallback_value)
                    except:
                        return None
                return None

        def safe_find_elements(parent, by, value, fallback_by=None, fallback_value=None):
            try:
                return parent.find_elements(by, value)
            except:
                if fallback_by and fallback_value:
                    try:
                        return parent.find_elements(fallback_by, fallback_value)
                    except:
                        return []
                return []

        # 1️⃣ Find color section
        color_section = safe_find_element(self.driver, By.ID, "exterior.colour")
        if color_section:
            for color_type in ["standard", "premium"]:
                cfg = self.section_config["exterior"]["color_section"][color_type]
                container = safe_find_element(
                    color_section,
                    By.CSS_SELECTOR, cfg.get("colors", {}).get("container", ""),
                    By.XPATH, cfg.get("anchors", {}).get("fallback_xpath")
                )
                if not container:
                    continue

                buttons = safe_find_elements(
                    container,
                    By.CSS_SELECTOR, cfg["colors"]["color_button"].get("css"),
                    By.XPATH, cfg["colors"]["color_button"].get("fallback_xpath")
                )
                for idx, btn in enumerate(buttons[:5]):  # limit 5
                    try:
                        color_info = self._extract_color_info(btn, color_type)
                        exterior_data["colors"][color_type].append(color_info)
                    except Exception as e:
                        print(f"        ⚠ {color_type.capitalize()} color {idx} error: {e}")
                        continue

        # 2️⃣ Exterior cards
        cards_list = safe_find_element(container, By.CSS_SELECTOR, self.COMMON_SELECTORS["section"]["cards_list"])
        if cards_list:
            cards = safe_find_elements(cards_list, By.TAG_NAME, self.COMMON_SELECTORS["section"]["card_item"])
            for idx, card in enumerate(cards[:3]):
                try:
                    card_data = self._process_card(card, f"exterior_card_{idx}")
                    exterior_data["cards"].append(card_data)
                except:
                    continue

        # 3️⃣ Wheels section
        wheels_section = safe_find_element(self.driver, By.ID, "wheels")
        if wheels_section:
            wheels_cfg = self.section_config["exterior"]["wheels"]["options"]
            wheels_container = safe_find_element(
                wheels_section,
                By.XPATH, wheels_cfg["container"].get("primary_xpath"),
                By.XPATH, wheels_cfg["container"].get("fallback_xpath")
            )
            if wheels_container:
                wheel_items = safe_find_elements(
                    wheels_container,
                    By.CSS_SELECTOR, wheels_cfg["item"].get("css"),
                    By.XPATH, wheels_cfg["item"].get("fallback_xpath")
                )
                for idx, item in enumerate(wheel_items[:5]):
                    try:
                        wheel_data = self._process_card(item, f"wheel_{idx}")
                        exterior_data["wheels"].append(wheel_data)
                    except:
                        continue

        return exterior_data


    def _extract_color_info(self, color_button, color_type):
        """Extract color info from a color button (dynamic class safe)"""
        color_info = {"type": color_type, "selected": False, "name": "", "image": "", "image_alt": ""}
        
        try:
            cfg = self.section_config["exterior"]["color_section"][color_type]["colors"]

            # name
            try:
                name_el = color_button.find_element(By.CSS_SELECTOR, cfg["name"])
                color_info["name"] = name_el.text.strip()
            except:
                pass

            # image
            try:
                img_el = color_button.find_element(By.CSS_SELECTOR, cfg["image"])
                color_info["image"] = img_el.get_attribute("src")
                color_info["image_alt"] = img_el.get_attribute("alt") or ""
            except:
                pass

            # selected
            try:
                aria_pressed = color_button.get_attribute("aria-pressed")
                color_info["selected"] = aria_pressed == "true"
            except:
                try:
                    classes = color_button.get_attribute("class")
                    color_info["selected"] = "selected" in classes.lower()
                except:
                    pass

        except Exception as e:
            print(f"          ⚠ Color extraction error: {e}")

        return color_info

    
    def scrape_interior(self, container):
        """Scrape interior section"""
        print("    Processing Interior section...")
        
        interior_data = {
            "type": "interior",
            "fabric_colors": {
                "options": []
            }
        }
        
        try:
            # Find fabric color section
            try:
                fabric_label = container.find_element(
                    By.CSS_SELECTOR, self.section_config["interior"]["fabric_color"]["label"]
                )
                interior_data["fabric_colors"]["label"] = fabric_label.text.strip()
            except:
                interior_data["fabric_colors"]["label"] = "Color and Fabrics"
            
            # Find fabric color cards
            try:
                cards_list = container.find_element(
                    By.CSS_SELECTOR, self.section_config["interior"]["fabric_color"]["cards"]["list"]
                )
                cards = cards_list.find_elements(
                    By.TAG_NAME, self.section_config["interior"]["fabric_color"]["cards"]["item"]
                )
                
                print(f"      Found {len(cards)} fabric color options")
                
                for idx, card in enumerate(cards[:3]):  # Limit to 3
                    try:
                        color_data = self._process_card(card, f"fabric_color_{idx}")
                        interior_data["fabric_colors"]["options"].append(color_data)
                    except Exception as e:
                        print(f"        ⚠ Fabric color {idx} error: {e}")
                        continue
                        
            except Exception as e:
                print(f"      ⚠ Fabric colors error: {e}")
                interior_data["fabric_colors"]["error"] = str(e)
            
        except Exception as e:
            print(f"    ⚠ Interior scraping error: {e}")
            interior_data["error"] = str(e)
        
        return interior_data
    
    def scrape_packages(self, container):
        """Scrape packages section"""
        print("    Processing Packages section...")
        
        packages_data = {
            "type": "packages",
            "sub_packages": []
        }
        
        try:
            # Find all sub-packages
            try:
                sub_package_labels = container.find_elements(
                    By.CSS_SELECTOR, self.section_config["packages"]["sub_packages"]["label"]
                )
                
                for idx, label in enumerate(sub_package_labels[:3]):  # Limit to 3
                    try:
                        sub_package_data = {
                            "name": label.text.strip(),
                            "options": []
                        }
                        
                        # Find parent container
                        parent_section = label.find_element(By.XPATH, "..").find_element(By.XPATH, "..")
                        
                        # Find cards in this sub-package
                        try:
                            cards_list = parent_section.find_element(
                                By.CSS_SELECTOR, self.section_config["packages"]["sub_packages"]["cards"]["list"]
                            )
                            cards = cards_list.find_elements(
                                By.TAG_NAME, self.section_config["packages"]["sub_packages"]["cards"]["item"]
                            )
                            
                            for card_idx, card in enumerate(cards[:2]):  # Limit to 2 per sub-package
                                try:
                                    card_data = self._process_card(card, f"package_{idx}_{card_idx}")
                                    sub_package_data["options"].append(card_data)
                                except:
                                    continue
                                    
                        except:
                            pass  # No cards found
                        
                        packages_data["sub_packages"].append(sub_package_data)
                        
                    except Exception as e:
                        print(f"        ⚠ Sub-package {idx} error: {e}")
                        continue
                        
            except Exception as e:
                print(f"      ⚠ Sub-packages error: {e}")
                packages_data["error"] = str(e)
            
        except Exception as e:
            print(f"    ⚠ Packages scraping error: {e}")
            packages_data["error"] = str(e)
        
        return packages_data
    
    def scrape_accessories(self, container):
        """Scrape accessories section"""
        print("    Processing Accessories section...")
        
        accessories_data = {
            "type": "accessories",
            "categories": []
        }
        
        try:
            # Find all accessory sections
            accessory_sections = self.driver.find_elements(
                By.CSS_SELECTOR, self.section_config["accessories"]["sections"]["container"]
            )
            
            for section_idx, section in enumerate(accessory_sections[:3]):  # Limit to 3 sections
                try:
                    # Get section title
                    try:
                        title_element = section.find_element(
                            By.CSS_SELECTOR, self.COMMON_SELECTORS["section"]["title"]
                        )
                        category_name = title_element.text.strip()
                    except:
                        category_name = f"Accessory_Section_{section_idx}"
                    
                    category_data = {
                        "name": category_name,
                        "items": []
                    }
                    
                    # Find cards in this section
                    try:
                        cards_list = section.find_element(
                            By.CSS_SELECTOR, self.COMMON_SELECTORS["section"]["cards_list"]
                        )
                        cards = cards_list.find_elements(
                            By.TAG_NAME, self.COMMON_SELECTORS["section"]["card_item"]
                        )
                        
                        for card_idx, card in enumerate(cards[:5]):  # Limit to 5 per category
                            try:
                                card_data = self._process_card(card, f"accessory_{section_idx}_{card_idx}")
                                category_data["items"].append(card_data)
                            except Exception as e:
                                print(f"          ⚠ Accessory card error: {e}")
                                continue
                                
                    except Exception as e:
                        print(f"        ⚠ Cards error in {category_name}: {e}")
                        category_data["error"] = str(e)
                    
                    accessories_data["categories"].append(category_data)
                    
                except Exception as e:
                    print(f"      ⚠ Accessory section {section_idx} error: {e}")
                    continue
                    
        except Exception as e:
            print(f"    ⚠ Accessories scraping error: {e}")
            accessories_data["error"] = str(e)
        
        return accessories_data
    
    def save_results(self, filename=None):
        """Save scraping results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nissan_build_data_{timestamp}.json"
        
        try:
            # Add summary statistics
            self.current_data["summary"] = {
                "sections_count": len(self.current_data.get("sections", {})),
                "total_cards": sum(
                    len(section.get("cards", [])) if isinstance(section.get("cards"), list) else 0
                    for section in self.current_data.get("sections", {}).values()
                ),
                "scraping_duration": datetime.now().isoformat(),
                "status": "completed" if self.current_data.get("sections") else "partial"
            }
            
            # Save to file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.current_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n{'='*60}")
            print(f"RESULTS SAVED TO: {filename}")
            print(f"{'='*60}")
            print(f"✓ Main image: {'Extracted' if self.current_data.get('main_image') else 'Not found'}")
            print(f"✓ Sections scraped: {self.current_data['summary']['sections_count']}")
            print(f"✓ Total cards: {self.current_data['summary']['total_cards']}")
            print(f"{'='*60}")
            
            return filename
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            self.log_scraping("error", f"Save results failed: {str(e)}")
            return None
    
    def scrape_single_build(self, build_url):
        """Complete scraping process for a single build URL"""
        print(f"\n🚗 Starting Nissan Build Page Scraper")
        print(f"📄 URL: {build_url}")
        
        # Initialize scraping
        if not self.initialize_scraping(build_url):
            return None
        
        # Process all sections
        self.process_all_sections()
        
        # Save results
        result_file = self.save_results()
        
        print(f"\n✅ Scraping completed!")
        
        return self.current_data
    
    def scrape_multiple_builds(self, build_links, delay_between=3):
        """Scrape multiple build pages"""
        all_results = []
        
        print("=" * 60)
        print("NISSAN BUILD PAGE BATCH SCRAPER")
        print("=" * 60)
        print(f"Total URLs to process: {len(build_links)}")
        print("=" * 60)
        
        for idx, build_url in enumerate(build_links, 1):
            print(f"\n[{idx}/{len(build_links)}] Processing build page")
            
            try:
                # Setup new driver for each URL
                self._setup_driver()
                
                # Scrape this build
                result = self.scrape_single_build(build_url)
                
                if result:
                    all_results.append(result)
                    print(f"✓ Successfully scraped")
                else:
                    print(f"✗ Failed to scrape")
                
                # Close driver
                self.close()
                
                # Delay between scrapes (except last one)
                if idx < len(build_links):
                    print(f"⏳ Waiting {delay_between} seconds before next...")
                    time.sleep(delay_between)
                    
            except Exception as e:
                print(f"❌ Error processing {build_url}: {str(e)[:100]}")
                try:
                    self.close()
                except:
                    pass
                continue
        
        # Save all results
        if all_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            all_results_file = f"nissan_all_builds_{timestamp}.json"
            
            with open(all_results_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            
            print(f"\n{'='*60}")
            print("BATCH PROCESSING COMPLETE")
            print(f"{'='*60}")
            print(f"✓ Total processed: {len(build_links)}")
            print(f"✓ Successfully scraped: {len(all_results)}")
            print(f"✓ Failed: {len(build_links) - len(all_results)}")
            print(f"✓ Combined results: {all_results_file}")
            print(f"{'='*60}")
        
        return all_results


def main():
    """Main function to run the scraper"""
    # Load build links from your file
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
    
    print(f"Found {len(build_links)} build links to process")
    
    # Initialize scraper
    scraper = NissanBuildPageScraper()  # Set to True for production
    
    # Scrape single URL for testing
    # result = scraper.scrape_single_build(build_links[0])
    
    # Or scrape all URLs
    results = scraper.scrape_multiple_builds(build_links[:2])  # Limit to 2 for testing
    
    print("\n🎉 Nissan Build Page Scraping Complete!")


if __name__ == "__main__":
    main()