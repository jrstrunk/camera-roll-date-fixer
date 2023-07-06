import exif
import PIL
from datetime import datetime, timedelta
from configparser import ConfigParser
import os
import time
from os import listdir
from os.path import isfile, join
import json
import re
import itertools
import json
import pytz
from dateutil import parser
from .ffprobe import FFProbe

def from_photo_metadata(file_name: str):
    if ".jpg" in file_name.lower() \
            or ".jpeg" in file_name.lower():
        try:
            with open(file_name, 'rb') as fi:
                img = exif.Image(fi)

            try:
                if img.datetime_original:
                    return datetime.strptime(img.datetime_original, "%Y:%m:%d %H:%M:%S"), True
            except:
                pass

            try:
                if img.datetime:
                    return datetime.strptime(img.datetime, "%Y:%m:%d %H:%M:%S"), True
            except:
                pass

            try:
                if img.datetime_digitized:
                    return datetime.strptime(img.datetime_digitized, "%Y:%m:%d %H:%M:%S"), True
            except:
                pass
        except:
            pass

    elif ".png" in file_name.lower():
        try:
            img = PIL.Image.open(file_name)
            return datetime.strptime(img.info["Creation Time"], "%Y:%m:%d %H:%M:%S"), True
        except:
            pass

    return None, False

def from_video_metadata(file_name: str, config: ConfigParser):
    local_timezone = pytz.timezone(config.get("settings", "local_timezone"))
    metadata = {}
    try:
        # Use FFprobe to get metadata from the video file
        probe = FFProbe(file_name)

        # Extract the metadata
        if probe.metadata.get("creation_time"):
            utc_time = datetime.strptime(probe.metadata["creation_time"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC)
            return utc_time.astimezone(local_timezone), True

        for stream in probe.streams:
            creation_time = stream.__dict__.get("TAG:creation_time")
            if creation_time:
                utc_time = datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC)
                return utc_time.astimezone(local_timezone), True

    except Exception as e:
        print(e)
        pass

    return None, False

def from_file_name(file_name: str):
    possible_date_formats = []

    delimiters = ["", " ", "-", "_", ".", " AT ", " at "]
    sub_delimiters = ["", "-", "_", "."]
    # the empty period must be last or else it will match dates with a period
    # before the appropiate period has had a chance to
    periods = [" AM", " PM", " am", " pm", "AM", "PM", "am", "pm", ""]

    # generate regex and datetime format str for each possible date format that
    # has the same sub delimiter for each block
    date_format_quadruple_tuples = \
        itertools.product(sub_delimiters, delimiters, sub_delimiters, periods)

    for sub_delim1, delim, sub_delim2, period in date_format_quadruple_tuples:
        if not period:
            hour_code = "%H"
            period_code = ""
        elif " " in period:
            hour_code = "%I"
            period_code = " %p"
        else:
            hour_code = "%I"
            period_code = "%p"

        possible_date_formats.append({
            "regex": f"\\d\\d\\d\\d{sub_delim1}\\d\\d{sub_delim1}\\d\\d{delim}\\d\\d{sub_delim2}\\d\\d{sub_delim2}\\d\\d{period}",
            "format": f"%Y{sub_delim1}%m{sub_delim1}%d{delim}{hour_code}{sub_delim2}%M{sub_delim2}%S{period_code}",
        })
    
    # generate regex and datetime format str for each possible date format that
    # has the h,m,s delimiters for the time block
    date_format_triple_tuples = \
        itertools.product(sub_delimiters, delimiters, periods)

    for sub_delim1, delim, period in date_format_triple_tuples:
        if not period:
            hour_code = "%H"
            period_code = ""
        elif " " in period:
            hour_code = "%I"
            period_code = " %p"
        else:
            hour_code = "%I"
            period_code = "%p"

        possible_date_formats.append({
            "regex": f"\\d\\d\\d\\d{sub_delim1}\\d\\d{sub_delim1}\\d\\d{delim}\\d\\dh\\d\\dm\\d\\ds{period}",
            "format": f"%Y{sub_delim1}%m{sub_delim1}%d{delim}{hour_code}h%Mm%Ss{period_code}",
        })

    for date_format in possible_date_formats:
        match = re.search(date_format["regex"], file_name)
        if match:
            try:
                return datetime.strptime(match.group(0), date_format["format"])
            # if this throws an error, then the "date" being parsed was not 
            # a valid date, so continue in the loop
            except:
                pass

    return None

def from_json(file_name: str):
    return None, None

def from_gphotos_json(file_name: str, config: ConfigParser):
    data = None

    def get_json_data(file_name):
        try:
            file_path_split = file_name.split("/")
            file_path_split[-1] = file_path_split[-1][0:46]
            short_file_name = "/".join(file_path_split)

            if os.path.isfile(f"{short_file_name}.json"):
                with open(f"{short_file_name}.json") as fi:
                    return json.load(fi)

            for num in range(5):
                minus_num_file_name = \
                    short_file_name.replace(f"({num})", "") + f"({num}).json"

                if f"({num})" in file_name and os.path.isfile(minus_num_file_name):
                    with open(minus_num_file_name) as fi:
                        return json.load(fi)

            # google photos names the json files a little differently than the 
            # actual file in these circumstances
            minus_edited_file_name = file_name.replace('-edited', '') + ".json"
            if "-edited" in file_name and os.path.isfile(minus_edited_file_name):
                with open(minus_edited_file_name) as fi:
                    return json.load(fi)
        except:
            pass

    data = get_json_data(file_name)

    if data:
        date_obj = parser.parse(data["photoTakenTime"]["formatted"])
        local_timezone = pytz.timezone(config.get("settings", "local_timezone"))
        return date_obj.astimezone(local_timezone)

    return None

def from_user_override(config: ConfigParser):
    user_override = config.get("settings", "manual_file_date_override")
    if not user_override:
        return
    date_obj = parser.isoparse(user_override)
    local_timezone = pytz.timezone(config.get("settings", "local_timezone"))
    return date_obj.astimezone(local_timezone)

def from_sys_file_times(file_name: str):
    """This is dangerous!"""
    # get the file modified date
    mod_time = os.path.getmtime(file_name)
    return datetime.fromtimestamp(mod_time)
