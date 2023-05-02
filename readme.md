# Camera Roll Date Fixer

Helps you to fix incorrect file and metadata dates for your photos and videos. It can determine the correct date for your media files, rename them based on the determined date, organize them into appropriate folders, and remove duplicate files.

## Process Overview
1. Determines the date of the photo or video by reading from 4 potential sources in this order:
    - A user-provided JSON file
    - File metadata
    - File name
    - System timestamps (optional, off by default)

2. If a date was determined for the file, it is written in three places to assure that you do not lose track of its date again:
    - The file's metadata
    - The file's name
    - The file's system mod timestamp

3. The new file with updated dates is then written to the specified output directory, leaving the original intact

4 All output files are searched for duplicates, a duplicate file report is generated, and the duplicate files are moved to the duplicates directory

## How to Use

1. Clone this repository to your local machine.

2. Install the required Python packages by running `pip install -r requirements.txt`.

3. Configure the `config.ini` file with your desired settings. The available settings are as follows:

    - `input_path`: The directory containing the input files (photos and videos).
    - `output_path`: The directory where the fixed files will be saved.
    - `error_path`: The directory where files with undetermined dates will be saved.
    - `duplicate_path`: The directory where duplicate files will be moved.
    - `preferred_keyword_in_dups`: Keyword to prioritize when handling duplicates (can be a directory name or file extension).
    - `unpreferred_keyword_in_dups`: Keyword to deprioritize when handling duplicates (can be a directory name or file extension).
    - `get_date_from_sys_file_times`: Whether to use system file times as a fallback method to determine dates (less reliable).
    - `output_in_month_subdirs`: Whether to organize output files into month-based subdirectories, eg. fixed/2023/05/photo.jpg
    - `report_duplicated_files`: Whether to check for duplicate files.
    - `move_reported_duplicate_files`: Whether to move the found duplicate files.
    - `heavy_duplicate_file_checking`: Whether to use pixel comparison for duplicate checking (increased accuracy but longer processing time).
    - `only_dedup`: Whether to run only the de-duplication logic and skip date fixing.
    - `rename_files`: Whether to rename files based on their determined dates.
    - `preserve_original_file_name`: Whether to append the original file name to the newly generated file name.
    - `earliest_year` and `latest_year`: The range of years to consider as valid dates.
    - `local_timezone`: The local timezone to use when parsing dates.

4. Run the script with `python main.py`.
