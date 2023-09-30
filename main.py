from datetime import datetime
import os
import time
from os import listdir
from os.path import isfile, join
import shutil
import ffmpeg
from configparser import ConfigParser
import src.determine_date as determine_date
import src.fixer_util as fixer_util
from src.img_name_gen import ImgNameGen
import src.duplicates as duplicates

config = ConfigParser()
config.read('config.ini')

input_path = config.get("settings", "input_path")
output_path = config.get("settings", "output_path")
error_path = config.get("settings", "error_path")
duplicate_path = config.get("settings", "duplicate_path")
use_sys_date = config.getboolean("settings", "get_date_from_sys_file_times")
use_month_subdirs = config.getboolean("settings", "output_in_month_subdirs")
report_dups = config.getboolean("settings", "report_duplicated_files")
move_dups = config.getboolean("settings", "move_reported_duplicate_files")
only_dedup = config.getboolean("settings", "only_dedup")

img_name_gen = ImgNameGen()

files = [
    f for f in listdir(input_path) 
        if isfile(join(input_path, f)) and not ".json" in f
] if not only_dedup else []

fixer_util.create_directories(output_path + "/o")
fixer_util.create_directories(error_path + "/e")

print(datetime.now(), f"Attemping to fix file times for all files in {input_path} ...")

for i, file_name in enumerate(files):
    input_file_name = f'{input_path}/{file_name}'
    error_file_name = f'{error_path}/{file_name}'
    
    print(i, file_name, "->", end=" ")
    got_date_from_metadata = False

    file_date = determine_date.from_user_override(config)

    if not file_date:
        file_date, original_file_date = \
            determine_date.from_json(input_file_name)

    if not file_date:
        file_date, got_date_from_metadata = \
            determine_date.from_metadata(input_file_name, config)

    if not file_date:
        file_date = \
            determine_date.from_gphotos_json(input_file_name, config)

    if not file_date:
        file_date = determine_date.from_file_name(input_file_name)

    if not file_date and use_sys_date:
        file_date = determine_date.from_sys_file_times(input_file_name)

    # if the parsed date is not valid, write the file to the error path and
    # continue to the next
    if not fixer_util.is_within_years(file_date, config):
        shutil.copy2(input_file_name, error_file_name)
        print("Error!")
        continue

    new_file_name = img_name_gen.gen_image_name(file_name, file_date, config)

    if use_month_subdirs:
        output_file_name = f"{output_path}/" \
            + f"{file_date.strftime('%Y')}/{file_date.strftime('%m')}/" \
            + f"{new_file_name}"
        fixer_util.create_directories(output_file_name)
    else:
        output_file_name = f"{output_path}/{new_file_name}"

    # write the date to the exif data if it is a jpg file and the date did not
    # originally come from the exif data
    successful_metadata_write = False
    if not got_date_from_metadata:
        if ".jpg" in input_file_name.lower() \
                or ".jpeg" in input_file_name.lower():
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

        elif ".png" in input_file_name.lower():
            try:
                fixer_util.write_png_with_metadata(
                    input_file_name, 
                    output_file_name, 
                    file_date, 
                )

                successful_metadata_write = True

            except Exception as e:
                print(e)
                pass

        elif ".mp4" in input_file_name.lower() \
                or ".mkv" in input_file_name.lower() \
                or ".webm" in input_file_name.lower() \
                or ".m4a" in input_file_name.lower() \
                or ".mov" in input_file_name.lower():
            try:
                fixer_util.write_video_with_metadata(
                    input_file_name, 
                    output_file_name, 
                    file_date,
                    config,
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

if report_dups:
    dups = duplicates.generate_report(output_path, config)

    if dups and move_dups:
        duplicates.move_older(dups, config)
