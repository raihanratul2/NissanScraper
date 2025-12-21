# NissanScraper

## Project Overview
NissanScraper is a web scraping project designed to extract and process data related to Nissan vehicles. The project includes various scripts and configurations to handle different aspects of the scraping workflow, such as extracting car lists, processing main sections, and generating reports.

## Folder Structure

### Root Directory
- **base.py**: Contains base classes or utility functions used across the project.
- **build_configurator.py**: Main script for building and configuring data extraction workflows.
- **build_configurator2.py**: An alternative or extended version of the build configurator.
- **build_expand_clickers.py**: Handles the expansion of clickable elements during scraping.
- **car_list_processor.py**: Processes car lists extracted from the website.
- **car_list.py**: Script for extracting car lists.
- **commad.txt**: Contains miscellaneous commands or notes.
- **main_section_complete_report.txt**: Detailed report of the main section extraction.
- **main_section_report.txt**: Summary report of the main section extraction.
- **nissan_all_builds_20251222_043836.json**: JSON file containing all builds data.
- **nissan_build_data_20251222_043755.json**: JSON file containing specific build data.
- **nissan_car_list.json**: JSON file containing a list of Nissan cars.
- **nissan_cars_simple.json**: Simplified JSON file of Nissan cars.
- **nissan_trims_detailed.json**: Detailed JSON file of Nissan trims.
- **nissan_trims_simple.json**: Simplified JSON file of Nissan trims.
- **requirements.txt**: Lists the Python dependencies required for the project.
- **run_build_workflow.py**: Script to execute the build workflow.
- **run_full_process.py**: Script to execute the full scraping process.

### Subdirectories

#### __pycache__/
- Contains Python cache files.

#### env/
- **pyvenv.cfg**: Configuration file for the virtual environment.
- **Include/**: Includes header files for the virtual environment.
- **Lib/**: Contains site-packages and other libraries.
  - **site-packages/**: Installed Python packages, such as `selenium`, `numpy`, `pandas`, etc.
- **Scripts/**: Scripts to activate or deactivate the virtual environment.

#### screenshots/
- Directory to store screenshots captured during the scraping process.

## How to Use
1. Set up the virtual environment:
   ```bash
   .\env\Scripts\activate
   pip install -r requirements.txt
   ```
2. Run the desired script, for example:
   ```bash
   python build_configurator.py
   ```

## Dependencies
- Python packages listed in `requirements.txt`, including:
  - `selenium`
  - `numpy`
  - `pandas`
  - `requests`

## Notes
- Ensure the virtual environment is activated before running any scripts.
- Reports and JSON files are generated in the root directory.
- Modify the scripts as needed to customize the scraping workflow.
