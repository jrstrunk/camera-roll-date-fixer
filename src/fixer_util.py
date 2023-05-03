import os
from datetime import datetime
from configparser import ConfigParser
import hashlib
import shutil
import ffmpeg
import exif
import pytz

video_extensions = [
    "mp4", 
    "avi", 
    "mkv", 
    "mov", 
    "webm", 
    "m4v", 
    "3gp", 
    "mpeg",
]

image_extensions = [
    "jpg", 
    "jpeg", 
    "jpe",
    "jif",
    "jfif",
    "jfi",
    "jp2",
    "j2k",
    "jpf",
    "jpx",
    "jpm",
    "mj2",
    "png", 
    "webp", 
    "gif", 
    "tiff", 
    "tif", 
    "psd", 
    "raw", 
    "arw", 
    "cr2", 
    "nrw", 
    "k25", 
    "bmp", 
    "dib", 
    "heif", 
    "heic", 
    "ind",
    "indd",
    "indt",
]

audio_extensions = [
    "mp3",
    "wav",
    "m4a",
]

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
