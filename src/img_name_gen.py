import re
from datetime import datetime
from configparser import ConfigParser
import exif
import random
import string
from .preserve_wordlist import words_to_preserve, words_to_not_preserve
from . import fixer_util 

class ImgNameGen:
    def __init__(self):
        self.prev_filenames = []

    def gen_image_name(self, 
            file_name: str, 
            img_date: datetime, 
            config: ConfigParser):
        file_ext = "." + file_name.split(".")[-1]
        date_str = self.get_date_str(img_date)
        date_prefix_name = date_str + self.get_prefix(file_name)

        if not config.getboolean("settings", "rename_files"):
            return file_name

        if config.getboolean("settings", "preserve_original_file_name"):
            return date_str + "_" + file_name

        return date_prefix_name \
            + self.get_nonce(date_prefix_name) \
            + self.get_postfix(file_name.replace(file_ext, "")) \
            + file_ext.lower()

    def get_date_str(self, img_date: datetime):
        return datetime.strftime(img_date, '%Y%m%d_%H%M%S')

    def get_nonce(self, img_filename: str):
        """This assures that no two filenames collide by keeping track of all 
            previous file names. If there could be a collision from two files 
            having the same date, a number is incremented and put in the random 
            postfix so that a collision in files names is not possible"""
        incr = len([d for d in self.prev_filenames if d == img_filename])

        self.prev_filenames.append(img_filename)

        consonants = ''.join(set(string.ascii_uppercase) - set('AEIOU'))

        if incr == 0:
            return "_" + "".join(random.choices(consonants, k=2))
        if 0 < incr < 10:
            return f"_{incr}" + "".join(random.choices(consonants, k=1))
        return f"_{incr}"

    def get_prefix(self, file_name: str):
        img_prefixes_from_file_name = {
            "PXL_": "_PXL",
            "WIN_": "_WIN",
            "MVIMG": "_MVIMG",
            "MVI_": "_MVI",
            ".MP": "_MPVID",
            ".MP.JPG": "_MPIMG",
        }

        file_ext = file_name.split(".")[-1].lower()

        for val, prefix in img_prefixes_from_file_name.items():
            if val in file_name.upper():
                return prefix

        if file_ext in fixer_util.image_extensions:
            return "_IMG"
        
        if file_ext in fixer_util.video_extensions:
            return "_VID"
        
        if file_ext in fixer_util.audio_extensions:
            return "_AUD"

        return "_UKN"

    def get_postfix(self, img_filename: str):
        # Do not waste time checking for words if it does not have more than 
        # two letters in the name, like when it is a numerical filename.
        # Filenames without their extension or path should be passed to this 
        # function.
        cleaned_file_name = img_filename\
            .replace("IMG_", "")\
            .replace("MVIMG", "")\
            .replace("VID_", "")\
            .replace("WIN_", "")\
            .replace("PXL_", "")
        if not bool(re.search("[a-zA-Z]{3,}", cleaned_file_name)):
            return ""

        # find all valid words in the filename and add them to the infix words
        # list
        postfix_words = []
        mut_img_filename = cleaned_file_name.lower()

        for word in words_to_not_preserve:
            mut_img_filename = mut_img_filename.replace(word, "")

        for word in words_to_preserve:
            if word in mut_img_filename:
                mut_img_filename = mut_img_filename.replace(word, "")
                postfix_words.append(word)

        # create an infix that consists of each word in the infix word list
        # in its original order and in camel case
        word_indices = {word: cleaned_file_name.lower().find(word) for word in postfix_words}
        sorted_infix_words = sorted(postfix_words, key=lambda x: word_indices[x])

        postfix = "".join([w.capitalize() for w in sorted_infix_words])
        if len(postfix):
            return "_" + postfix

        return ""
