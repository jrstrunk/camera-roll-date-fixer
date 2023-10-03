import re
from datetime import datetime
from configparser import ConfigParser
import exif
import random
import re
import string
from .preserve_wordlist import words_to_preserve, words_to_not_preserve
from . import fixer_util 

class ImgNameGen:
    def __init__(self):
        self.prev_filenames = []

    def gen_file_name(self, 
            file_name: str, 
            file_type: str,
            file_extension: str,
            file_date: datetime, 
            config: ConfigParser):
        date_str = self.get_date_str(file_date)
        file_name_no_ext = ".".join(file_name.split(".")[0:-1])

        if not config.getboolean("settings", "rename_files"):
            return file_name

        if config.getboolean("settings", "preserve_original_file_name"):
            return date_str + "_" + file_name

        postfix = self.get_postfix(file_name_no_ext)
        media_type_prefix = self.get_media_type_prefix(file_name, file_type)
        nonceless_name = date_str + media_type_prefix + postfix

        return date_str \
            + self.get_nonce(nonceless_name) \
            + media_type_prefix \
            + postfix \
            + "." + file_extension.lower()

    def get_date_str(self, img_date: datetime):
        return datetime.strftime(img_date, '%Y%m%d_%H%M%S')

    def get_nonce(self, img_filename: str):
        """This adds an random postfix value to the filename to reduce the 
            chance that files generated will collide with other external 
            files when merged into the same directory and assures that no 
            two filenames in the current process collide by keeping track 
            of all previously generated file names. If there could be a 
            collision, a number is incremented and put in the nonce so that 
            a collision in files names is not possible"""
        incr = len([d for d in self.prev_filenames if d == img_filename])

        self.prev_filenames.append(img_filename)

        consonants = ''.join(set(string.ascii_uppercase) - set('AEIOUYJXZ'))

        if incr == 0:
            return "_" + "".join(random.choices(consonants, k=2))
        if 0 < incr < 10:
            return f"_{incr}" + "".join(random.choices(consonants, k=1))
        return f"_{incr}"

    def get_media_type_prefix(self, file_name: str, file_type: str) -> str:
        img_prefix_regexs_from_file_name = {
            "^PXL_": "_PXL",
            "^WIN_": "_WIN",
            "^MVIMG": "_MVIMG",
            "^MVI_": "_MVI",
            ".MP$": "_MPVID",
            ".MP.JPG$": "_MPIMG",
            "SNAPCHAT.*JPG": "_SNAPP",
            "SNAPCHAT.*MP4": "_SNAPV",
            "SCREENSHOT": "_SSHOT",
            "PORTRAIT": "_PORTR",
        }

        file_ext = file_name.split(".")[-1].lower()

        for regex, prefix in img_prefix_regexs_from_file_name.items():
            if re.search(regex, file_name.upper()):
                return prefix

        if file_type == "image":
            return "_IMG"
        
        if file_type == "video":
            return "_VID"
        
        if file_type == "audio":
            return "_AUD"

        return "_UKN"

    def get_postfix(self, file_name_no_ext: str):
        # Do not waste time checking for words if it does not have more than 
        # two letters in the name, like when it is a numerical filename.
        # Filenames without their extension or path should be passed to this 
        # function.
        cleaned_file_name = file_name_no_ext\
            .replace("IMG_", "")\
            .replace("MVIMG", "")\
            .replace("VID_", "")\
            .replace("WIN_", "")\
            .replace("PXL_", "")
        if not bool(re.search("[a-zA-Z]{3,}", cleaned_file_name)):
            return ""

        any_valid_words = False

        # find all valid words in the filename and add them to the postfix words
        # list
        postfix_words = []
        mut_img_filename = cleaned_file_name.lower()

        for word in words_to_not_preserve:
            mut_img_filename = mut_img_filename.replace(word, "")

        for word in words_to_preserve:
            if word in mut_img_filename:
                mut_img_filename = mut_img_filename.replace(word, "")
                postfix_words.append(word)
                any_valid_words = True

        # create an postfix that consists of each word in the postfix word list
        # in its original order and in camel case
        word_indices = {word: cleaned_file_name.lower().find(word) for word in postfix_words}
        sorted_postfix_words = sorted(postfix_words, key=lambda x: word_indices[x])

        # if there is an alphanumerical designation at the end of the 
        # name, like "My Photo 41d.jpg", then try to preserve that
        desig = ""
        if any_valid_words:
            last_sect = mut_img_filename.split(" ")[-1]
            last_sect = re.sub(r"\([^()]*\)", "", last_sect) # remove potential (2) at the end
            if len(last_sect) < 5 and re.match("^([A-Za-z]|\d)+$", last_sect):
                desig = last_sect

        postfix = "".join([w.capitalize() for w in sorted_postfix_words])
        if len(postfix):
            return "_" + postfix + desig

        return ""
