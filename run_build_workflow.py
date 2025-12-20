"""
Build Workflow Manager - Complete build configuration workflow
"""

import time
import sys
from build_configurator import BuildConfigurator


def run_build_workflow():
    """Run complete build configuration workflow"""
    print("="*70)
    print("NISSAN BUILD CONFIGURATION WORKFLOW")
    print("="*70)
    
    print("\n📋 This workflow will:")
    print("1. Load trim data from nissan_trims_simple.json")
    print("2. Process each build configuration")
    print("3. Handle multiple drivetrain options")
    print("4. Track button clicks and changes")
    print("5. Generate detailed reports")
    print("="*70)
    
    # Check if trim data exists
    import os
    if not os.path.exists("nissan_trims_simple.json"):
        print("\n❌ Error: nissan_trims_simple.json not found!")
        print("\nPlease run car_list_processor.py first to generate trim data.")
        print("Or run run_full_process.py for complete workflow.")
        return
    
    # Configuration options
    print("\n⚙️  Configuration Options:")
    print("1. Process all trims")
    print("2. Process specific number of trims")
    print("3. Test mode (process first trim only)")
    
    try:
        choice = input("\nSelect option (1-3): ").strip()
        
        configurator = BuildConfigurator(headless=False)
        
        if choice == "1":
            print("\nProcessing ALL trims...")
            configurator.process_build_configurations()
            
        elif choice == "2":
            try:
                count = int(input("How many trims to process? "))
                print(f"\nProcessing first {count} trims...")
                # We'll modify the configurator to process limited trims
                configurator.process_limited_configurations(count)
            except ValueError:
                print("Invalid number. Processing all trims.")
                configurator.process_build_configurations()
                
        elif choice == "3":
            print("\nRunning in TEST mode (first trim only)...")
            # Test with first trim only
            import json
            with open("nissan_trims_simple.json", 'r') as f:
                trim_data = json.load(f)
            
            if trim_data:
                test_trim = trim_data[0]
                print(f"Testing with: {test_trim.get('full_name', 'Unknown')}")
                
                # Process single trim
                config_data = configurator.scrape_build_page_with_drivetrains(
                    test_trim.get('build_link', ''),
                    test_trim
                )
                
                if config_data:
                    configurator.configurations = [config_data]
                    configurator.save_configurations()
                    print("\n✅ Test completed successfully!")
                else:
                    print("\n❌ Test failed!")
            else:
                print("No trim data available for testing.")
        
        else:
            print("Invalid choice. Processing all trims.")
            configurator.process_build_configurations()
            
    except KeyboardInterrupt:
        print("\n\n⚠ Workflow interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'configurator' in locals():
            configurator.close()
        
        print("\n" + "="*70)
        print("WORKFLOW COMPLETED")
        print("="*70)
        print("\nGenerated files:")
        print("• nissan_build_configurations_detailed.json")
        print("• nissan_build_configurations_simple.json")
        print("• build_configuration_detailed_report.txt")
        print("\nYou can view the detailed report for button click statistics.")
        print("="*70)


if __name__ == "__main__":
    run_build_workflow()