from datetime import datetime
import os
import time
from os import listdir
from os.path import isfile, join
import shutil
import ffmpeg
from configparser import ConfigParser
from src.determine_date import determine_date
import src.fixer_util as fixer_util
from src.img_name_gen import ImgNameGen
import src.duplicates as duplicates

config = ConfigParser()
config.read('config.ini')

input_path = config.get("settings", "input_path")
output_path = config.get("settings", "output_path")
error_path = config.get("settings", "error_path")
duplicate_path = config.get("settings", "duplicate_path")
use_month_subdirs = config.getboolean("settings", "output_in_month_subdirs")
report_dups = config.getboolean("settings", "report_duplicated_files")
move_dups = config.getboolean("settings", "move_reported_duplicate_files")
only_dedup = config.getboolean("settings", "only_dedup")

img_name_gen = ImgNameGen()

input_files = []
if not only_dedup:
    for root, dirs, files in os.walk(input_path):
        for f in [f for f in files if not ".json" in f]:
            input_files.append(os.path.join(root, f))

fixer_util.create_directories(output_path + "/o")
fixer_util.create_directories(error_path + "/e")

if config.getboolean("settings", "continuous_reporting"):
    open_type = "a"
else:
    open_type = "w"

with open("report.txt", open_type) as f:
    print(
        datetime.now(), 
        f"Attemping to fix file times for all files in {input_path} ...", 
        file=f,
    )
print(
    datetime.now(), 
    f"Attemping to fix file times for all files in {input_path} ..."
)

if config.getboolean("settings", "rename_files"):
    print("!!!! Warning !!!!")
    print('For some reason "OffsetFix_20190208_015413_VID_CB.mov" ' + \
        'gets renamed to "20190207_205413_VID_Offset.mp4", missing the "Fix".')
    print("Either disable file renaming or accept this issue.", end="\n\n")

for i, input_file_name in enumerate(input_files):
    file_name = input_file_name.replace(input_path + "/", "")
    rel_file_path = ""

    split_name = file_name.rsplit("/", 1)
    if len(split_name) == 2:
        file_name = split_name[1]

        if config.getboolean("settings", "preserve_directory_structure"):
            rel_file_path = "/" + split_name[0]

    error_file_name = f"{error_path + rel_file_path}/{file_name}"
    
    with open("report.txt", "a") as f:
        print(i, file_name, "->", end=" ", file=f)
    print(i, file_name, "->", end=" ")

    file_date, original_file_date, write_metadata = determine_date(
        input_file_name, config)

    # if the parsed date is not valid, write the file to the error path and
    # continue to the next
    if not file_date:
        fixer_util.create_directories(error_file_name)
        shutil.copy2(input_file_name, error_file_name)
        with open("report.txt", "a") as f:
            print("! Date out of bounds, putting in error dir", file=f)
        print("! Date out of bounds, putting in error dir")
        continue

    file_type, file_extension = fixer_util.get_file_type(input_file_name)

    new_file_name = img_name_gen.gen_file_name(
        file_name, 
        file_type, 
        file_extension, 
        file_date, 
        config,
    )

    preserve_dirs = config.getboolean("settings", "preserve_directory_structure")
    if use_month_subdirs and (not preserve_dirs or not rel_file_path):
        output_file_name = f"{output_path}/" \
            + f"{file_date.strftime('%Y')}/{file_date.strftime('%m')}/" \
            + f"{new_file_name}"
    else:
        output_file_name = f"{output_path}{rel_file_path}/{new_file_name}"

    fixer_util.create_directories(output_file_name)

    # write the date to the exif data if it is a jpg file and the date did not
    # originally come from the exif data
    if config.getboolean("settings", "override_png_metadata") \
            and file_extension == "png" :
        write_metadata = True

    successful_metadata_write = False
    if write_metadata:
        if file_extension == "jpg":
            successful_metadata_write = fixer_util.write_jpg_with_exif(
                input_file_name, 
                output_file_name, 
                file_date, 
                original_file_date
            )

        elif file_extension == "png":
            successful_metadata_write = fixer_util.write_png_with_metadata(
                input_file_name, 
                output_file_name, 
                file_date, 
            )

        elif file_type == "video":
            successful_metadata_write = fixer_util.write_video_with_metadata(
                input_file_name, 
                output_file_name, 
                file_date,
                config,
            )

        elif config.getboolean("settings", "write_json_for_unsupported_types"):
            fixer_util.write_json_sidecar(output_file_name, file_date)

    # copy the file to the output file if a new file was not 
    # written with metadata 
    if not successful_metadata_write:
        shutil.copy2(input_file_name, output_file_name)

    # create a time object that can be set as the file's modification date
    modTime = time.mktime(file_date.timetuple())

    # write that the file was modified when it was taken
    os.utime(output_file_name, (modTime, modTime))

    log_stmt = new_file_name if config.getboolean("settings", "rename_files") \
        else file_date.strftime('%Y-%m-%d %H:%M:%S')
    with open("report.txt", "a") as f:
        print(log_stmt, file=f)
    print(log_stmt)

    time.sleep(0.01)

with open("report.txt", "a") as f:
    print(datetime.now(), "Done fixing file times!", file=f)
print(datetime.now(), "Done fixing file times!")

if report_dups:
    dups = duplicates.generate_report(output_path, config)

    if dups and move_dups:
        duplicates.move_older(dups, config)

with open("report.txt", "a") as f:
    print(datetime.now(), "Done!", end="\n\n", file=f)
print(datetime.now(), "Done!")