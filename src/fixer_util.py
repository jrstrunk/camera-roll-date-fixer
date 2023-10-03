import os
from datetime import datetime
from configparser import ConfigParser
from .ffprobe import FFProbe
import hashlib
import shutil
import ffmpeg
import exif
import piexif
import pytz
import PIL

video_extensions = [
    "mp4", 
    "avi", 
    "mkv", 
    "mov", 
    "webm", 
    "m4v", 
    "3gp", 
    "mpeg",
    "mp",
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

def get_utc_offset(localized_datetime: datetime) -> str:
    return localized_datetime.isoformat()[-6:]

def write_jpg_with_exif(
        input_file_name: str, 
        output_file_name: str, 
        img_datetime: datetime, 
        img_original_datetime: datetime = None) -> bool:
    try:
        img_datetime_str = img_datetime.strftime('%Y:%m:%d %H:%M:%S')
        offset_str = get_utc_offset(img_datetime)

        image = PIL.Image.open(input_file_name)
        if image.info.get("exif"):
            exif_dict = piexif.load(image.info['exif'])
        else:
            exif_dict = {"Exif":{}}
        
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = img_datetime_str.encode()
        exif_dict['Exif'][piexif.ExifIFD.OffsetTimeOriginal] = offset_str.encode()

        exif_bytes = piexif.dump(exif_dict)
        image.save(output_file_name, exif=exif_bytes)

    except Exception as e:
        with open("report.txt", "a") as f:
            print("! Error writing jpg metadata:", e, "->", end=" ", file=f)
        print("! Error writing jpg metadata:", e, "->", end=" ")
        return False
    return True

def write_png_with_metadata(
    input_file_name: str,
    output_file_name: str,
    img_datetime: datetime) -> bool:
    try:
        image = PIL.Image.open(input_file_name)

        # Create a PngInfo object to store metadata
        metadata = PIL.PngImagePlugin.PngInfo()

        for key in image.info:
            if type(image.info[key]) is int or type(image.info[key]) is float:
                val = str(image.info[key])
            elif type(image.info[key]) is tuple or type(image.info[key]) is list:
                val = ", ".join(map(str,image.info[key]))
            elif type(image.info[key]) is dict:
                val = ', '.join(f'{key}: {value}' for key, value in image.info[key].items())
            else:
                val = image.info[key]
            metadata.add_text(key, val)
        
        img_datetime_str = img_datetime.strftime('%Y:%m:%d %H:%M:%S')
        img_offset_str = get_utc_offset(img_datetime)
        metadata.add_text("Creation Time", img_datetime_str)
        metadata.add_text("Offset Time", img_offset_str)
        
        image.save(output_file_name, "PNG", pnginfo=metadata)
        image.close()
    except Exception as e:
        with open("report.txt", "a") as f:
            print("! Error writing png metadata:", e, "->", end=" ", file=f)
        print("! Error writing png metadata:", e, "->", end=" ")
        return False
    return True

def get_video_comment(file_name: str):
    try:
        # Use FFprobe to get metadata from the video file
        probe = FFProbe(file_name)

        # Extract the metadata
        if probe.metadata.get("comment"):
            return probe.metadata.get("comment") + ", "

    except Exception as e:
        print("Error getting video comment metdata: ", e)
        pass

    return ""

def write_video_with_metadata(
        input_file_name: str, 
        output_file_name: str, 
        video_date: datetime,
        config: ConfigParser) -> bool:
    try:
        video_datetime_utc = video_date.astimezone(pytz.UTC)

        creation_time = video_datetime_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        comment = get_video_comment(input_file_name) + \
            "creation_time_iso " + video_date.isoformat()

        # create a tmp file that has the proper creation time metadata
        input_stream = ffmpeg.input(input_file_name)

        tmp_output_file_name = "tmp/" + output_file_name.split("/")[-1]

        tmp_output_stream = ffmpeg.output(
            input_stream,
            tmp_output_file_name,
            c="copy",
            map_metadata="0",
            metadata=f'creation_time={creation_time}',
        )

        ffmpeg.run(tmp_output_stream, quiet=True)

        # copy the tmp file but add a comment with the offset time
        input_stream = ffmpeg.input(tmp_output_file_name)

        output_stream = ffmpeg.output(
            input_stream,
            output_file_name,
            c="copy",
            map_metadata="0",
            metadata=f'comment={comment}',
        )

        ffmpeg.run(output_stream, quiet=True)

        os.remove(tmp_output_file_name)
    except Exception as e:
        with open("report.txt", "a") as f:
            print("! Error writing video metadata:", e, "->", end=" ", file=f)
        print("! Error writing video metadata:", e, "->", end=" ")
        return False
    return True

def guess_media_type(file_name: str):
    file_ext = file_name.split(".")[-1].lower()

    if file_ext in image_extensions:
        return "image"
    if file_ext in video_extensions:
        return "video"
    if file_ext in audio_extensions:
        return "audio"
    return "unknown"
