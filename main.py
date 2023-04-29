import exif
from datetime import datetime
import os
import time
from os import listdir
from os.path import isfile, join
import shutil
import ffmpeg
import src.determine_date as determine_date
import src.fixer_util as fixer_util
from src.img_name_gen import ImgNameGen

# PROGRAM CONSTANTS
earliest_year = "2000"
lastest_year = "2023"
input_path = "input"
output_path = "fixed"
error_path = "error"
duplicate_path = "duplicates"
preferred_keyword_in_dups = "" # can be a dir name in the path or file extension
unpreferred_keyword_in_dups = "" 
get_date_from_sys_file_times = False # be careful!
output_fixed_files_in_month_subdirs = True
report_duplicated_files = True
move_reported_duplicate_files = True
local_timezone = "America/New_York"

img_name_gen = ImgNameGen()

files = [f for f in listdir(input_path) if isfile(join(input_path, f))]

fixer_util.create_directories(output_path + "/o")
fixer_util.create_directories(error_path + "/e")

print(datetime.now(), f"Attemping to fix file times for all files in {input_path} ...")

for i, file_name in enumerate(files):
    input_file_name = f'{input_path}/{file_name}'
    error_file_name = f'{error_path}/{file_name}'
    
    print(i, file_name, "->", end=" ")
    got_date_from_metadata = False

    file_date, original_file_date = determine_date.from_json(input_file_name)

    if not file_date:
        file_date, got_date_from_metadata = \
            determine_date.from_video_metadata(input_file_name)

    if not file_date:
        file_date, got_date_from_metadata = \
            determine_date.from_exif(input_file_name)

    if not file_date:
        file_date = \
            determine_date.from_gphotos_json(input_file_name, local_timezone)

    if not file_date:
        file_date = determine_date.from_file_name(input_file_name)

    if not file_date and get_date_from_sys_file_times:
        file_date = determine_date.from_sys_file_times(input_file_name)

    # if the parsed date is not valid, write the file to the error path and
    # continue to the next
    if not fixer_util.is_within_years(file_date, earliest_year, lastest_year):
        shutil.copy2(input_file_name, error_file_name)
        print("Error!")
        continue

    new_file_name = img_name_gen.gen_image_name(file_name, file_date)
    if output_fixed_files_in_month_subdirs:
        output_file_name = f"{output_path}/" \
            + f"{file_date.strftime('%Y')}/{file_date.strftime('%m')}/" \
            + f"{new_file_name}"
        fixer_util.create_directories(output_file_name)
    else:
        output_file_name = f"{output_path}/{new_file_name}"

    # write the date to the exif data if it is a jpg file and the date did not
    # originally come from the exif data
    successful_metadata_write = False
    if not got_date_from_metadata and (".jpg" in input_file_name.lower()
            or ".jpeg" in input_file_name.lower()):
        try:
            fixer_util.write_jpg_with_exif(
                input_file_name, 
                output_file_name, 
                file_date, 
                original_file_date
            )

            successful_metadata_write = True

        except:
            pass

    elif not got_date_from_metadata and (".mp4" in input_file_name.lower() \
            or ".mkv" in input_file_name.lower() \
            or ".webm" in input_file_name.lower() \
            or ".m4a" in input_file_name.lower() \
            or ".mov" in input_file_name.lower()):
        try:
            fixer_util.write_video_with_metadata(
                input_file_name, 
                output_file_name, 
                file_date,
            )

            successful_metadata_write = True

        except:
            pass

    # copy the file to the output file if a new file was not 
    # written with metadata 
    if not successful_metadata_write:
        shutil.copy2(input_file_name, output_file_name)

    # create a time object that can be set as the file's modification date
    modTime = time.mktime(file_date.timetuple())

    # write that the file was modified when it was taken
    os.utime(output_file_name, (modTime, modTime))
    print(new_file_name)

    time.sleep(0.01)

print(datetime.now(), "Done fixing file times!")

if report_duplicated_files:
    dups = fixer_util.generate_duplicate_report(output_path)

    if move_reported_duplicate_files and dups:
        fixer_util.create_directories(duplicate_path + "/d")
        fixer_util.move_older_duplicates(
            dups, 
            duplicate_path, 
            preferred_keyword_in_dups, 
            unpreferred_keyword_in_dups
        )
