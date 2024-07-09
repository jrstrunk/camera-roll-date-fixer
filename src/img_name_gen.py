import re
from datetime import datetime
from configparser import ConfigParser
import random
import re
import string
from .preserve_wordlist import larger_words_to_preserve, words_to_not_preserve

class ImgNameGen:
    def __init__(self):
        self.prev_filenames = []

    def gen_file_name(self, 
            file_name: str, 
            file_type: str,
            file_extension: str,
            file_date: datetime, 
            config: ConfigParser):
        if not config.getboolean("output", "rename_files"):
            return file_name

        if config.getboolean("output", "expand_file_types_in_name"):
            file_name = self.expand_media_type(file_name)

        date_str = self.get_date_str(file_date)

        if config.getboolean("output", "preserve_original_file_name"):
            if date_str in file_name:
                # do not duplicate the date in the file name if the 
                # original already had it
                return file_name 
            return date_str + "_" + file_name

        file_name_no_ext = ".".join(file_name.split(".")[0:-1])

        media_type_prefix = self.get_media_type_prefix(file_name, file_type)
        postfix = self.get_postfix(file_name_no_ext)

        nonceless_name = date_str + media_type_prefix
        nonce = self.get_nonce(nonceless_name, postfix)

        return date_str \
            + media_type_prefix \
            + postfix \
            + nonce \
            + "." + file_extension.lower()

    def get_date_str(self, img_date: datetime):
        return datetime.strftime(img_date, '%Y%m%d_%H%M%S')

    def get_nonce(self, img_filename: str, postfix: str):
        """This adds an random value to the filename to reduce the 
            chance that files generated will collide with other external 
            files when merged into the same directory and assures that no 
            two filenames in the current process collide by keeping track 
            of all previously generated file names. If there could be a 
            collision, a number is incremented and put in the nonce so that 
            a collision in files names is not possible"""
        img_filename = img_filename + postfix
        incr = len([d for d in self.prev_filenames if d == img_filename])

        self.prev_filenames.append(img_filename)

        consonants = ''.join(set(string.ascii_uppercase) - set('AEIOUYJXZ'))

        # if there is a postfix, the nonce should just be the number of the
        # file name with no extra formatting
        if postfix:
            if incr == 0:
                return ""
            return f"_{incr}"

        if incr == 0:
            return "_" + "".join(random.choices(consonants, k=2))
        if 0 < incr < 10:
            return f"_{incr}" + "".join(random.choices(consonants, k=1))
        return f"_{incr}"

    def get_media_type_prefix(self, file_name: str, file_type: str) -> str:
        img_prefix_regexes_from_file_name = {
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

        for regex, prefix in img_prefix_regexes_from_file_name.items():
            if re.search(regex, file_name.upper()):
                return prefix

        if file_type == "image":
            return "_IMG"
        
        if file_type == "video":
            return "_VID"
        
        if file_type == "audio":
            return "_AUD"

        return "_UKN"

    def expand_media_type(self, file_name: str) -> str:
        img_media_types = {
            "WIN_": "_Windows",
            "SNAPP_": "_Snapchat",
            "SNAPV_": "_Snapchat",
            "SSHOT_": "_Screenshot",
            "PORTR_": "_Portrait",
        }

        file_ext = "." + file_name.split(".")[-1].lower()

        for short_type, full_type in img_media_types.items():
            if short_type in file_name.upper():
                file_name = file_name.replace(short_type, "")
                file_name = file_name.replace(file_ext, "")
                return file_name + full_type + file_ext
        
        return file_name

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
            .replace("WIN_", "")\
            .replace("PXL_", "")\
            .replace("Snapchat", "")\
            .replace("Screenshot", "")\
            .replace("PORTRAIT", "")\
            .replace("image", "")
        if not bool(re.search("[a-zA-Z]{3,}", cleaned_file_name)):
            return ""

        meaningful_words = self.__get_meaningful_words(cleaned_file_name)

        postfix = "".join([w.capitalize() for w in meaningful_words])
        if len(postfix):
            return "_" + postfix

        return ""
    
    def __get_meaningful_words(self, file_name):
        # first check if there are any valid words at all, excluding words to ignore
        valid_words = get_valid_words(file_name)
        
        if not len(valid_words) > 0:
            return []

        expanded_sorted_words, expanded_word_indices = get_entire_valid_words(valid_words, file_name)

        words = split_all_words_based_on_valid_words(expanded_sorted_words, expanded_word_indices, file_name)

        # remove words that are just digits & symbols and more than 4 chars
        words = remove_serials(words)

        # remove words that are delimiter characters "_", " "
        words = remove_delimiter_words(words)

        words = split_sub_delimited_words(words)

        words = remove_duplicate_file_ind(words)

        words = remove_brackets(words)

        return words

def split_camel_case(string):
    return re.findall(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))|[\W\da-z]+', string)

def split_letter_and_symbol_groupings(string):
    return re.findall(r'([a-zA-Z]+|[\W\d]+)', string)

def get_valid_words(string):
    postfix_words = []
    mut_img_filename = string.lower()

    for word in words_to_not_preserve:
        mut_img_filename = mut_img_filename.replace(word, "")

    for word in larger_words_to_preserve:
        if word in mut_img_filename:
            mut_img_filename = mut_img_filename.replace(word, "")
            postfix_words.append(word)
    
    return postfix_words

def get_entire_valid_words(words: list, file_name: str):
    # if there are valid words in the file name, check to make sure we 
    # picked up on whole words
    word_indices = {word: file_name.lower().find(word) for word in words}
    sorted_postfix_words = sorted(words, key=lambda x: word_indices[x])

    expanded_sorted_words = []
    expanded_word_indices = {}
    total_index = -1
    for word in sorted_postfix_words:
        index = word_indices[word]
        expanded_word = word
        expanded_word_index = index

        if index <= total_index:
            continue

        advanced_chars_count = 0

        # find letters afterhand that belong to the word we found
        for c in range(index+len(word), len(file_name)):
            if (re.match("[a-z]", file_name[c]) \
                    and re.match("[a-z]", file_name[c-1])) \
                    or (re.match("[A-Z]", file_name[c]) \
                    and re.match("[A-Z]", file_name[c-1])):
                expanded_word += file_name[c]
                advanced_chars_count += 1
            else:
                break
        
        # find letters beforehad that belong to the word we found
        if index > 0:
            for c in range(index-1, total_index, -1):
                if (re.match("[a-z]", file_name[c]) \
                        and re.match("[a-z]", file_name[c+1])) \
                        or (re.match("[A-Z]", file_name[c]) \
                        and re.match("[a-z]", file_name[c+1])) \
                        or (re.match("[A-Z]", file_name[c]) \
                        and re.match("[A-Z]", file_name[c+1]) \
                        and (not re.match("[a-z]", file_name[c+2]) \
                            if len(file_name) > c+2 else False)):
                    expanded_word = file_name[c] + expanded_word
                    expanded_word_index -= 1
                else:
                    break

        total_index = index + len(word) -1 + advanced_chars_count

        expanded_sorted_words.append(expanded_word)
        expanded_word_indices[expanded_word] = expanded_word_index
    return expanded_sorted_words, expanded_word_indices

def split_all_words_based_on_valid_words(valid_words: list, valid_word_indices: dict, file_name: str):
    # find the word delimiter
    delimiter_counts = {}
    for word, index in valid_word_indices.items():
        if index == 0 and len(file_name) > index + len(word):
            following_char = file_name[index + len(word)]

            if re.match("[A-Z]", following_char):
                following_char = "CAMEL_CASE"

            if not delimiter_counts.get(following_char):
                delimiter_counts[following_char] = 1
            else:
                delimiter_counts[following_char] += 1
        elif not index == 0 and index + len(word) == len(file_name):
            preceeding_char = file_name[index - 1]

            if re.match("[A-Z]", file_name[index]) \
                    and re.match("[a-z]", preceeding_char):
                preceeding_char = "CAMEL_CASE"

            if not delimiter_counts.get(preceeding_char):
                delimiter_counts[preceeding_char] = 1
            else:
                delimiter_counts[preceeding_char] += 1
        elif not index == 0 and index + len(word) < len(file_name):
            preceeding_char = file_name[index - 1]
            following_char = file_name[index + len(word)]

            if re.match("[A-Z]", following_char):
                following_char = "CAMEL_CASE"

            if re.match("[A-Z]", file_name[index]) \
                    and re.match("[a-z]", preceeding_char):
                preceeding_char = "CAMEL_CASE"

            if not delimiter_counts.get(preceeding_char):
                delimiter_counts[preceeding_char] = 1
            else:
                delimiter_counts[preceeding_char] += 1

            if not delimiter_counts.get(following_char):
                delimiter_counts[following_char] = 1
            else:
                delimiter_counts[following_char] += 1

    real_delimiter_counts = {}
    for delim in delimiter_counts:
        if delim in [" ", "_", "-", "."]:
            real_delimiter_counts[delim] = delimiter_counts[delim]
        elif delim == "CAMEL_CASE" and delimiter_counts[delim] > 1:
            real_delimiter_counts[delim] = delimiter_counts[delim]

    if real_delimiter_counts:
        delimiter = max(real_delimiter_counts, key=delimiter_counts.get)
        
        if delimiter == "CAMEL_CASE":
            return split_camel_case(file_name)

        return file_name.split(delimiter)

    # there is no delimiter
    return valid_words

def remove_serials(words: list):
    words_no_serials = []
    for word in words:
        if not re.match("^[\d_\-]{5,}$", word):
            words_no_serials.append(word)
    return words_no_serials

def remove_delimiter_words(words: list):
    words_no_delimiters = []
    for word in words:
        if not word == " " and not word == "-" and not word == "_" and not word == "":
            words_no_delimiters.append(word)
    return words_no_delimiters

def split_sub_delimited_words(words: list):
    words_separated = []
    for word in words:
        word_mut = word.lower()
        mutated = False
        # only do this if the word has both numbers and letters, and is not
        # a part (pt4) or page (pg6), and is not short
        if not re.match("pt[\.\-\d_]{1,4}|pg[\.\-\d_]{1,4}", word) \
                and len(word) > 4 \
                and re.match("^(?=.*[0-9])(?=.*[a-zA-Z]).*$", word):
            for pres_word in larger_words_to_preserve:
                mutated = True
                if pres_word in word_mut:
                    words_separated.append(pres_word)
                    word_mut = word_mut.replace(pres_word, "")
            
        if not mutated:
            words_separated.append(word)
    
    return words_separated

def remove_duplicate_file_ind(words: list):
    if not words:
        return words
    last_word = words[-1]
    del words[-1]
    words.append(re.sub("\(\d+\)$", "", last_word))
    return words

def remove_brackets(words: list):
    clean_words = []
    for word in words:
        clean_word = word.replace("(", "")
        clean_word = clean_word.replace(")", "")
        clean_word = clean_word.replace("[", "")
        clean_word = clean_word.replace("]", "")
        clean_words.append(clean_word)
    return clean_words
