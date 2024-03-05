import os
from datetime import datetime, timedelta
from configparser import ConfigParser
from .ffprobe import FFProbe
from .log import Logger
import hashlib
import shutil
import ffmpeg
import exif
import piexif
import pytz
import PIL
import magic
import tempfile
import json

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
    "ogv",
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
    "weba",
    "oga",
]

mime_types = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/heic": "heic",
    "image/tiff": "tiff",
    "image/x-panasonic-raw": "raw",
    "video/x-msvideo": "avi",
    "video/mp4": "mp4",
    "video/mpeg": "mpeg",
    "video/ogg": "ogv",
    "video/webm": "webm",
    "video/x-matroska": "mkv",
    "video/quicktime": "mov",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/webm": "weba",
    "audio/ogg": "oga",
}

def is_within_years(dt: datetime, config: ConfigParser):
    if not dt: 
        return False

    earliest_year = config.get("parsing", "earliest_year")
    latest_year = config.get("parsing", "latest_year")

    try:
        earliest_year = int(earliest_year)
    except:
        earliest_year = 1826

    try:
        latest_year = int(latest_year)
    except:
        # get the year of tomorrow+1 in case the photo was taken in a later tz
        latest_year = (datetime.now() + timedelta(days=2)).year

    if (earliest_year and dt.year < earliest_year):
        return False

    if (latest_year and dt.year > latest_year):
        return False

    return True

def create_directories(file_path: str):
    dir_path = os.path.dirname(file_path)
    
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def get_file_type(file_path: str, logger: Logger) -> str:
    file_type = "unknown"
    file_extension = ""

    try:
        mime = magic.from_file(file_path, mime=True)
        file_type = mime.split("/")[0]
        file_extension = mime_types.get(mime, "")
    except:
        logger.log("! Unknown MIME type -> ", end="")

    try:
        if not file_extension:
            file_extension = file_name.split(".")[-1]

        if file_type == "unknown":
            if file_extension in image_extensions:
                file_type = "image"
            elif file_extension in video_extensions:
                file_type = "video"
            elif file_extension in audio_extensions:
                file_type = "audio"
    except:
        logger.log("! Unable to get extension type -> ", end="")

    return file_type, file_extension

def get_utc_offset(localized_datetime: datetime) -> str:
    return localized_datetime.isoformat()[-6:]

def write_jpg_with_exif(
        input_file_name: str, 
        output_file_name: str, 
        img_datetime: datetime, 
        logger: Logger,
        img_original_datetime: datetime = None,
) -> bool:
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
        logger.log(f"! Error writing jpg metadata: {e} -> ", end="")
        return False
    return True

def write_png_with_metadata(
    input_file_name: str,
    output_file_name: str,
    img_datetime: datetime,
    logger: Logger,
) -> bool:
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
        metadata.add_text("DateTime", img_datetime_str)
        metadata.add_text("OffsetTime", img_offset_str)
        
        image.save(output_file_name, "PNG", pnginfo=metadata)
        image.close()
    except Exception as e:
        logger.log(f"! Error writing png metadata: {e} -> ", end="")
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
        logger: Logger,
        config: ConfigParser,
) -> bool:
    try:
        video_datetime_utc = video_date.astimezone(pytz.UTC)

        creation_time = video_datetime_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        comment = get_video_comment(input_file_name) + \
            "creation_time_iso " + video_date.isoformat()

        with tempfile.TemporaryDirectory(dir=".") as tmpd:
            # create a tmp file that has the proper creation time metadata
            input_stream = ffmpeg.input(input_file_name)

            tmp_output_file_name = tmpd.replace("./", "") + "/" + output_file_name.split("/")[-1]

            tmp_output_stream = ffmpeg.output(
                input_stream,
                tmp_output_file_name,
                c="copy",
                map_metadata="0",
                metadata=f'creation_time={creation_time}',
            )

            ffmpeg.run(tmp_output_stream, overwrite_output=True, quiet=True)

            # copy the tmp file but add a comment with the offset time
            input_stream = ffmpeg.input(tmp_output_file_name)

            output_stream = ffmpeg.output(
                input_stream,
                output_file_name,
                c="copy",
                map_metadata="0",
                metadata=f'comment={comment}',
            )

            ffmpeg.run(output_stream, overwrite_output=True, quiet=True)
    except Exception as e:
        logger.log(f"! Error writing video metadata: {e} -> ", end="")
        return False
    return True

def write_sidecar(output_file_name: str, file_date: datetime):
    """Use the XMP file format and the photoshop DateCreated tag because
        it supports offset time and PhotoPrism is known to parse it on import"""
    img_datetime_str = file_date.strftime('%Y-%m-%dT%H:%M:%S')
    img_offset_str = get_utc_offset(file_date)

    file_name_no_ext, _ = os.path.splitext(output_file_name)
    output_file_name = file_name_no_ext + ".xmp"

    with open(output_file_name, "w") as f:
        print(
            '<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 6.0.0">',
            '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">',
            '    <rdf:Description rdf:about=""',
            '            xmlns:exif="http://ns.adobe.com/exif/1.0/"',
            '            xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">',
            f"        <photoshop:DateCreated>{img_datetime_str}{img_offset_str}</photoshop:DateCreated>",
            '    </rdf:Description>',
            "</rdf:RDF>",
            "</x:xmpmeta>",
            sep="\n",
            file=f,
        )

def guess_media_type(file_name: str):
    file_ext = file_name.split(".")[-1].lower()

    if file_ext in image_extensions:
        return "image"
    if file_ext in video_extensions:
        return "video"
    if file_ext in audio_extensions:
        return "audio"
    return "unknown"
