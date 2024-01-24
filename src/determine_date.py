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
import src.fixer_util as fixer_util
from dateutil import parser
from .ffprobe import FFProbe

def determine_date(file_name: str, config: ConfigParser):
    use_sys_date = config.getboolean("settings", "get_date_from_sys_file_times")
    use_json_date = config.getboolean("settings", "get_date_from_json_file")
    use_metadata_date = config.getboolean("settings", "get_date_from_file_metadata")
    use_gphotos_json_date = config.getboolean("settings", "get_date_from_gphotos_json_file")
    use_file_name_date = config.getboolean("settings", "get_date_from_file_name")

    got_date_from_metadata = False

    file_date = from_user_override(config)

    if not file_date and use_json_date:
        file_date, original_file_date = from_json(file_name, config)

    if not file_date and use_metadata_date:
        file_date, got_date_from_metadata = from_metadata(file_name, config)

    if not file_date and use_gphotos_json_date:
        file_date = from_gphotos_json(file_name, config)

    if not file_date and use_file_name_date:
        file_date = from_file_name(file_name, config)

    if not file_date and use_sys_date:
        file_date = from_sys_file_times(file_name, config)
    
    local_timezone = pytz.timezone(config.get("settings", "local_timezone"))

    # if we got a naive date time from the file, assume it is local 
    # time, otherwise change it to local time
    if file_date:
        if not file_date.tzinfo:
            file_date = file_date.replace(tzinfo=local_timezone)
        else:
            file_date = file_date.astimezone(local_timezone)

    if original_file_date:
        if not original_file_date.tzinfo:
            original_file_date = original_file_date.replace(tz_info=local_timezone)
        else:
            original_file_date = original_file_date.astimezone(local_timezone)

    return file_date, original_file_date, not got_date_from_metadata

def from_metadata(file_name: str, config: ConfigParser):
    file_date, got_date = from_photo_metadata(file_name)
    if not got_date:
        file_date, got_date = from_video_metadata(file_name)

    if fixer_util.is_within_years(file_date, config):
        return file_date, got_date

    return None, False

def from_photo_metadata(file_name: str):
    """Photo metadata often stores the time in Local Time"""
    # jpg file handling
    try:
        with open(file_name, 'rb') as fi:
            img = exif.Image(fi)

        try:
            if img.datetime_original:
                img_date = datetime.strptime(img.datetime_original, "%Y:%m:%d %H:%M:%S")

                try:
                    if img.offset_time_original:
                        offset_minutes = int(img.offset_time_original[:3]) \
                            * 60 + int(img.offset_time_original[4:])
                        offset_tz = pytz.FixedOffset(offset_minutes)
                        img_date = img_date.replace(tzinfo=offset_tz)
                except:
                    pass
                    
                return img_date, True
        except:
            pass

        try:
            if img.datetime:
                img_date = datetime.strptime(img.datetime, "%Y:%m:%d %H:%M:%S"), True

                try:
                    if img.offset_time:
                        offset_minutes = int(img.offset_time[:3]) \
                            * 60 + int(img.offset_time[4:])
                        offset_tz = pytz.FixedOffset(offset_minutes)
                        img_date = img_date.replace(tzinfo=offset_tz)
                except:
                    pass

                return img_date, True
        except:
            pass

        try:
            if img.datetime_digitized:
                img_date = datetime.strptime(img.datetime_digitized, "%Y:%m:%d %H:%M:%S"), True

                try:
                    if img.offset_time_digitized:
                        offset_minutes = int(img.offset_time_digitized[:3]) \
                            * 60 + int(img.offset_time_digitized[4:])
                        offset_tz = pytz.FixedOffset(offset_minutes)
                        img_date = img_date.replace(tzinfo=offset_tz)
                except:
                    pass

                return img_date, True
        except:
            pass
    except:
        pass

    # png file handling
    try:
        for datetimeTag in ["Creation Time", "CreationTime", "DateTime", "DateTimeOriginal", "DateTimeDigitized"]:
            img = PIL.Image.open(file_name)
            if img.info.get(datetimeTag):
                img_date = datetime.strptime(img.info["Creation Time"], "%Y:%m:%d %H:%M:%S")

                try:
                    for offsetTag in ["Offset Time", "OffsetTime", "OffsetTimeOriginal", "OffsetTimeDigitized"]:
                        if img.info.get(effsetTag):
                            offset_minutes = int(img.info["Offset Time"][:3]) \
                                * 60 + int(img.info["Offset Time"][4:])
                            offset_tz = pytz.FixedOffset(offset_minutes)
                            img_date = img_date.replace(tzinfo=offset_tz)
                            break
                except:
                    pass

                return img_date, True
    except:
        pass

    return None, False

def from_video_metadata(file_name: str):
    """Video metadata often stores the time in UTC"""
    metadata = {}
    try:
        # Use FFprobe to get metadata from the video file
        probe = FFProbe(file_name)

        # Extract the metadata
        if probe.metadata.get("creation_time"):
            utc_time = datetime.strptime(probe.metadata["creation_time"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC)
            return utc_time, True

        for stream in probe.streams:
            creation_time = stream.__dict__.get("TAG:creation_time")
            if creation_time:
                utc_time = datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC)
                return utc_time, True

    except Exception as e:
        print("Error getting video metadata: ", e)
        pass

    return None, False

def from_file_name(file_name: str, config: ConfigParser):
    possible_date_formats = []

    delimiters = ["", " ", "-", "_", ".", " AT ", " at "]
    sub_delimiters = ["", "-", "_", ".", " "]
    # the empty period must be last or else it will match dates with a period
    # before the appropiate period has had a chance to
    periods = [" AM", " PM", " am", " pm", "AM", "PM", "am", "pm", ""]

    # generate regex and datetime format str for each possible date format that
    # has the same sub delimiter for each block, eg. "2024-01-21 09.36.10"
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

        # account for all digit date
        possible_date_formats.append({
            "regex": f"\\d\\d\\d\\d{sub_delim1}\\d\\d{sub_delim1}\\d\\d{delim}\\d\\d{sub_delim2}\\d\\d{sub_delim2}\\d\\d{period}".replace(".", "\\."),
            "format": f"%Y{sub_delim1}%m{sub_delim1}%d{delim}{hour_code}{sub_delim2}%M{sub_delim2}%S{period_code}",
        })
        # account for date with short month name
        possible_date_formats.append({
            "regex": f"\\d\\d\\d\\d{sub_delim1}[A-Za-z][A-Za-z][A-Za-z]{sub_delim1}\\d\\d{delim}\\d\\d{sub_delim2}\\d\\d{sub_delim2}\\d\\d{period}".replace(".", "\\."),
            "format": f"%Y{sub_delim1}%b{sub_delim1}%d{delim}{hour_code}{sub_delim2}%M{sub_delim2}%S{period_code}",
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

        # account for all digit date
        possible_date_formats.append({
            "regex": f"\\d\\d\\d\\d{sub_delim1}\\d\\d{sub_delim1}\\d\\d{delim}\\d\\dh\\d\\dm\\d\\ds{period}".replace(".", "\\."),
            "format": f"%Y{sub_delim1}%m{sub_delim1}%d{delim}{hour_code}h%Mm%Ss{period_code}",
        })
        # account for date with short month name
        possible_date_formats.append({
            "regex": f"\\d\\d\\d\\d{sub_delim1}[A-Za-z][A-Za-z][A-Za-z]{sub_delim1}\\d\\d{delim}\\d\\dh\\d\\dm\\d\\ds{period}".replace(".", "\\."),
            "format": f"%Y{sub_delim1}%d{sub_delim1}%d{delim}{hour_code}h%Mm%Ss{period_code}",
        })

    # generate regex and datetime format str for each possible date format that
    # only has the date, eg. "2011.08.24"
    date_format_singles = sub_delimiters

    for sub_delim1 in date_format_singles:
        # account for all digit date
        possible_date_formats.append({
            "regex": f"\\d\\d\\d\\d{sub_delim1}\\d\\d{sub_delim1}\\d\\d".replace(".", "\\."),
            "format": f"%Y{sub_delim1}%m{sub_delim1}%d",
        })
        # account for date with short month name
        possible_date_formats.append({
            "regex": f"\\d\\d\\d\\d{sub_delim1}[A-Za-z][A-Za-z][A-Za-z]{sub_delim1}\\d\\d".replace(".", "\\."),
            "format": f"%Y{sub_delim1}%b{sub_delim1}%d",
        })

    for date_format in possible_date_formats:
        matches = re.findall(f"(?=({date_format['regex']}))", file_name)
        for match in matches:
            try:
                file_date = datetime.strptime(match, date_format["format"])
                if fixer_util.is_within_years(file_date, config):
                    return file_date

            # if this throws an error, then the "date" being parsed was not 
            # a valid date, so continue in the loop
            except:
                pass

    return None

def from_json(file_name: str, config: ConfigParser):
    return None, None

def from_gphotos_json(file_name: str, config: ConfigParser):
    data = None

    def get_json_data(file_name):
        try:
            file_path_split = file_name.split("/")
            file_path_split[-1] = file_path_split[-1][0:46]
            short_file_name = "/".join(file_path_split)

            # check for a straight conversion from the file name to 
            # the json file
            if os.path.isfile(f"{short_file_name}.json"):
                with open(f"{short_file_name}.json") as f:
                    return json.load(f)

            # translating a file with a filename duplicate number at the 
            # end is not straigtforward, "hi(2).jpg" -> "hi.jpg(2).json
            for num in range(5):
                minus_num_file_name = \
                    short_file_name.replace(f"({num})", "") + f"({num}).json"

                if f"({num})" in file_name and os.path.isfile(minus_num_file_name):
                    with open(minus_num_file_name) as f:
                        return json.load(f)

            # google photos names the json files a little differently than the 
            # actual file when there was an edit
            minus_edited_file_name = file_name.replace('-edited', '') + ".json"
            if "-edited" in file_name and os.path.isfile(minus_edited_file_name):
                with open(minus_edited_file_name) as f:
                    return json.load(f)

            # in some cases the file extension is just left out of the json 
            # file name, like "de.jpg_large.jpg" -> "de.jpg_large.json"
            minus_ext_file_name = ".".join(file_name.split(".")[0:-1]) + ".json"
            if os.path.isfile(minus_ext_file_name):
                with open(minus_ext_file_name) as f:
                    return json.load(f)

        except:
            pass

    data = get_json_data(file_name)

    if data:
        file_date = parser.parse(data["photoTakenTime"]["formatted"])
        if fixer_util.is_within_years(file_date, config):
            return file_date

    return None

def from_user_override(config: ConfigParser):
    user_override = config.get("settings", "manual_file_date_override")
    if not user_override:
        return
    return parser.isoparse(user_override)

def from_sys_file_times(file_name: str, config: ConfigParser):
    """This is dangerous!"""
    # get the file modified date
    mod_time = os.path.getmtime(file_name)
    return datetime.fromtimestamp(mod_time)
