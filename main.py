import os
import sys
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
from src.log import Logger

def main(config_path: str):
    config = ConfigParser()
    config.read(config_path)

    input_path = config.get("structure", "input_path")
    output_path = config.get("structure", "output_path")
    error_path = config.get("structure", "error_path")
    use_month_subdirs = config.getboolean("structure", "output_in_month_subdirs")
    report_dups = config.getboolean("deduplication", "search_for_duplicate_files")
    move_dups = config.getboolean("deduplication", "move_duplicate_files")
    only_dedup = config.getboolean("deduplication", "only_dedup")

    img_name_gen = ImgNameGen()
    logger = Logger(config)

    fixer_util.create_directories(output_path + "/o")
    fixer_util.create_directories(error_path + "/e")

    input_files = []
    if not only_dedup:
        for root, dirs, files in os.walk(input_path):
            for f in [f for f in files if not ".json" in f]:
                input_files.append(os.path.join(root, f))

    logger.log_timestamped(
        f"Attemping to fix file times for all files in {input_path} ...",
    )

    if config.getboolean("output", "rename_files"):
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

            if config.getboolean("structure", "preserve_directory_structure"):
                rel_file_path = "/" + split_name[0]

        error_file_name = f"{error_path + rel_file_path}/{file_name}"
        
        logger.log(f"{i} {file_name} -> ", end="")

        file_date, original_file_date, write_metadata = determine_date(
            input_file_name, config)

        # if the parsed date is not valid, write the file to the error path and
        # continue to the next
        if not file_date:
            fixer_util.create_directories(error_file_name)
            shutil.copy2(input_file_name, error_file_name)
            logger.log("! Date out of bounds, putting in error dir")
            continue

        file_type, file_extension = fixer_util.get_file_type(
            input_file_name,
            logger,
        )

        new_file_name = img_name_gen.gen_file_name(
            file_name, 
            file_type, 
            file_extension, 
            file_date, 
            config,
        )

        preserve_dirs = config.getboolean("structure", "preserve_directory_structure")
        if use_month_subdirs and (not preserve_dirs or not rel_file_path):
            output_file_name = f"{output_path}/" \
                + f"{file_date.strftime('%Y')}/{file_date.strftime('%m')}/" \
                + f"{new_file_name}"
        else:
            output_file_name = f"{output_path}{rel_file_path}/{new_file_name}"

        fixer_util.create_directories(output_file_name)

        write_sidecar = False

        # write the date to the exif data if it is a jpg file and the date did not
        # originally come from the exif data
        if config.getboolean("output", "override_png_metadata") \
                and file_extension == "png" :
            write_metadata = True

        successful_metadata_write = False
        if write_metadata:
            if file_extension == "jpg":
                successful_metadata_write = fixer_util.write_jpg_with_exif(
                    input_file_name, 
                    output_file_name, 
                    file_date, 
                    logger,
                    original_file_date
                )

            elif file_extension == "png":
                successful_metadata_write = fixer_util.write_png_with_metadata(
                    input_file_name,
                    output_file_name,
                    file_date,
                    logger,
                )

            elif file_type == "video":
                # Write to a sidecar for video files since most video file 
                # containers do not support time offset
                write_sidecar = True
                successful_metadata_write = fixer_util.write_video_with_metadata(
                    input_file_name, 
                    output_file_name, 
                    file_date,
                    logger,
                    config,
                )

            if not successful_metadata_write:
                write_sidecar = True

        if config.getboolean("output", "write_sidecar_for_unsupported_types") \
                    and write_sidecar:
                fixer_util.write_sidecar(output_file_name, file_date)

        # copy the file to the output file if a new file was not 
        # written with metadata 
        if not successful_metadata_write:
            shutil.copy2(input_file_name, output_file_name)

        # create a time object that can be set as the file's modification date
        modTime = time.mktime(file_date.timetuple())

        # write that the file was modified when it was taken
        os.utime(output_file_name, (modTime, modTime))

        logger.log(
            new_file_name if config.getboolean("output", "rename_files") \
                else file_date.strftime('%Y-%m-%d %H:%M:%S'),
        )

        time.sleep(0.01)

    logger.log_timestamped("Done fixing file times!")

    if report_dups:
        logger.log_timestamped("Generating duplicate file report ... ")
        dups = duplicates.generate_report(output_path, config)

        if dups and move_dups:
            logger.log_timestamped("Moving duplicate files ... ")
            duplicates.move_older(dups, config)

        logger.log_timestamped("Done!")

    logger.log("", end="\n")

if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) == 2 else "config.ini"
    main(config_path)