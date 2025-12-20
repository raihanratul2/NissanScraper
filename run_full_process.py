"""
Complete Workflow Runner - Runs the entire scraping process
"""

import time
from car_list import NissanCarListScraper
from car_list_processor import CarListProcessor


def run_full_process():
    """Run the complete scraping process"""
    print("="*60)
    print("NISSAN USA COMPLETE SCRAPING WORKFLOW")
    print("="*60)
    
    print("\n📋 WORKFLOW STEPS:")
    print("1. Get car list from build link")
    print("2. Save car list to JSON")
    print("3. Process each car for trim details")
    print("4. Process build configurations")
    print("="*60)
    
    # Get build link from user
    print("\nEnter Nissan build link (or press Enter for default):")
    build_link = input("Link: ").strip()
    
    if not build_link:
        build_link = "https://www.nissanusa.com/vehicles/build-price.html"
        print(f"Using default: {build_link}")
    
    # STEP 1: Get car list
    print(f"\n{'='*60}")
    print("STEP 1: GETTING CAR LIST")
    print(f"{'='*60}")
    
    scraper = NissanCarListScraper(headless=False)
    
    try:
        scraper.scrape_car_list_from_link(build_link)
    except Exception as e:
        print(f"Error in step 1: {e}")
        scraper.close()
        return
    
    # Wait a bit before next step
    time.sleep(2)
    
    # STEP 2: Process car list for trims
    print(f"\n{'='*60}")
    print("STEP 2: PROCESSING TRIM DETAILS")
    print(f"{'='*60}")
    
    processor = CarListProcessor(scraper)
    processor.process_car_links()
    
    # Close scraper
    scraper.close()
    
    # STEP 3: Instructions for build configurator
    print(f"\n{'='*60}")
    print("NEXT STEP INSTRUCTIONS")
    print(f"{'='*60}")
    print("\nTo process build configurations:")
    print("1. Open a new terminal/command prompt")
    print("2. Run: python build_configurator.py")
    print("\nThe build configurator will:")
    print("• Load trim data from nissan_trims_simple.json")
    print("• Process each build link")
    print("• Extract detailed configuration options")
    print("• Generate summary report")
    print(f"{'='*60}")
    
    # Optional: Ask if user wants to run build configurator now
    print("\nDo you want to run the build configurator now?")
    run_now = input("Run build configurator? (yes/no): ").strip().lower()
    
    if run_now in ['yes', 'y']:
        print("\nStarting build configurator...")
        print("="*60)
        
        # Import and run build configurator
        from build_configurator import BuildConfigurator, main as run_build_config
        
        run_build_config()
    else:
        print("\nYou can run the build configurator later with:")
        print("> python build_configurator.py")


if __name__ == "__main__":
    run_full_process()