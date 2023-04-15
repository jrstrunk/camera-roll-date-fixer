import exif
from pprint import pprint
from datetime import datetime
import os
import time
from os import listdir
from os.path import isfile, join
import json
import re
import itertools
from .ffprobe import FFProbe

def from_exif(file_name: str):
    if not ".jpg" in file_name.lower() \
            and not ".jpeg" in file_name.lower():
        return None, False

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

    return None, False

def from_video_metadata(file_name: str):
    metadata = {}
    try:
        # Use FFprobe to get metadata from the video file
        probe = FFProbe(file_name)

        # Extract the metadata
        if probe.metadata.get("creation_time"):
            return datetime.strptime(probe.metadata["creation_time"], "%Y-%m-%dT%H:%M:%S.%fZ"), True

        for stream in probe.streams:
            creation_time = stream.__dict__.get("TAG:creation_time")
            if creation_time:
                return datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%S.%fZ"), True

    except Exception as e:
        print(e)
        pass

    return None, False

def from_file_name(filename: str):
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
        match = re.search(date_format["regex"], filename)
        if match:
            try:
                return datetime.strptime(match.group(0), date_format["format"])
            # if this throws an error, then the "date" being parsed was not 
            # a valid date, so continue in the loop
            except:
                pass

    return None

def from_json(filename: str):
    return None, None

def from_sys_file_times(file_name: str):
    """This is dangerous!"""
    # get the file modified date
    mod_time = os.path.getmtime(file_name)
    return datetime.fromtimestamp(mod_time)
