import os
from datetime import datetime
from configparser import ConfigParser
import hashlib
import shutil
import ffmpeg
import exif
import pytz

def is_within_years(dt: datetime, config: ConfigParser):
    if not dt: 
        return False

    year1 = config.getint("settings", "earliest_year")
    year2 = config.getint("settings", "latest_year")
    
    if year1 > year2:
        tmp = year1
        year1 = year2
        year2 = tmp
    
    return year1 <= dt.year <= year2

def create_directories(file_path: str):
    dir_path = os.path.dirname(file_path)
    
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def __generate_file_hash(file_path):
    BUF_SIZE = 65536
    hasher = hashlib.sha256()
    
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            hasher.update(data)
            
    return hasher.hexdigest()

def __find_duplicate_files(*paths):
    file_hashes = {}
    
    for path in paths:
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                
                try:
                    file_hash = __generate_file_hash(file_path)
                except OSError as e:
                    continue
                
                if file_hash in file_hashes:
                    file_hashes[file_hash].append(file_path)
                else:
                    file_hashes[file_hash] = [file_path]
                    
    duplicates = [tuple(files) for files in file_hashes.values() if len(files) > 1]
    return duplicates

def generate_duplicate_report(start_path):
    print(datetime.now(), "Generating duplicate file report ... ")
    dups = __find_duplicate_files(start_path)
    with open("duplicates.txt", "w") as fi:
        for dup in dups:
            print('"', '","'.join(dup), '"', file=fi, sep="")
    print(datetime.now(), "Done!")
    return dups

def move_older_duplicates(duplicate_tuples: list, config: ConfigParser):
    print(datetime.now(), "Moving duplicate files ... ")
    dest_dir = config.get("settings", "duplicate_path")
    preferred_keyword = config.get("settings", "preferred_keyword_in_dups")
    unpreferred_keyword = config.get("settings", "unpreferred_keyword_in_dups")

    create_directories(dest_dir + "/d")
    moved_files = []

    for duplicate_files in duplicate_tuples:
        if not duplicate_files:
            continue

        # Find the file with the newest system modification date. If the files 
        # have the same date, prefer the file with the smallest file name to get
        # rid of common "(1)" or "- Copy" postfixes in file names. If the files
        # have the same modificatin date and same filename length, then prefer 
        # files that have the passed preferred keywords in them, then prefer 
        # files that don't have the unpreferred keyword in them. If all of those 
        # conditions are the same, then prefer the file with the least amount of 
        # digits at the end of the file. This will move files that an increment 
        # added to their nonce in the output of this program.
        def file_criteria(file_name: str):
            mtime = os.path.getmtime(file_name)
            name = os.path.basename(file_name)
            last_7_chars_digit_count = sum(c.isdigit() for c in name[-7:])
            return (
                mtime, 
                -len(name), 
                preferred_keyword in file_name, 
                not unpreferred_keyword in file_name, 
                -last_7_chars_digit_count
            )

        preferred_file = max(duplicate_files, key=file_criteria)

        # Move the other files to the destination directory
        for file in duplicate_files:
            if file != preferred_file:
                try:
                    dest_file_path = os.path.join(dest_dir, os.path.basename(file))
                    shutil.move(file, dest_file_path)
                    moved_files.append((file, dest_file_path))
                except (OSError, shutil.Error) as e:
                    pass

    print(datetime.now(), "Done!")
    return moved_files

def write_jpg_with_exif(
        input_file_name: str, 
        output_file_name: str, 
        img_datetime: datetime, 
        img_original_datetime: datetime = None):
    img_datetime_str = img_datetime.strftime('%Y:%m:%d %H:%M:%S')
    
    with open(input_file_name, 'rb') as fi:
        img = exif.Image(fi)

    img.datetime = img_datetime_str

    if img_original_datetime:
        img.datetime_original = \
            original_file_date.strftime('%Y:%m:%d %H:%M:%S')
    else:
        img.datetime_original = img_datetime_str

    img.datetime_digitized = img_datetime_str

    with open(output_file_name, 'wb') as fi:
        fi.write(img.get_file())

def write_video_with_metadata(
        input_file_name: str, 
        output_file_name: str, 
        video_date: datetime,
        config: ConfigParser):
    local_timezone = pytz.timezone(config.get("settings", "local_timezone"))
    video_datetime_localized = local_timezone.localize(video_date)
    video_datetime_utc = video_datetime_localized.astimezone(pytz.UTC)

    # Parse the video_datetime_utc into a formatted string
    creation_time = video_datetime_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    
    # Create a FFmpeg input stream
    input_stream = ffmpeg.input(input_file_name)

    # Create an FFmpeg output stream with the updated creation_date metadata
    output_stream = ffmpeg.output(
        input_stream,
        output_file_name,
        **{
            "metadata": f"creation_time={creation_time}",
            "c": "copy",
        }
    )

    # Run the FFmpeg command
    ffmpeg.run(output_stream, quiet=True)

if __name__ == "__main__":
    dups = generate_duplicate_report('/home/john/Pictures/AddToJessicaNC')
    move_older_duplicates(dups, "duplicates")