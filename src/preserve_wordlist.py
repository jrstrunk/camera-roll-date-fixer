import os, sys
import re
__custom_words_to_preserve = [
    "strunk",
    "websize",
    "edited",
    "signal",
    "scan",
    "rehearsal",
    "rendered",
    "rpreplay",
    "vlcsnap",
    "my",
    "by",
    "we",
    "nani!",
    "youtube",
    "google",
    "nike",
    "addidas",
    "reddit",
    "instagram",
]

# many of these are already accounted for in some way and to not
# need to be preserved at the end of the file name
words_to_not_preserve = [
    "from",
    "image",
]

words_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) \
    + '/resources/words.txt'

with open(words_path, "r") as word_file:
    valid_words = set(word_file.read().split())

words_to_preserve = [
    *__custom_words_to_preserve, 
    *sorted(
        [w for w in valid_words if len(w) > 2 and not w in words_to_not_preserve], 
        key=lambda x: len(x),
        reverse=True
    )
]

larger_words_to_preserve = [
    *__custom_words_to_preserve, 
    *sorted(
        [w for w in valid_words if len(w) > 3 and not w in words_to_not_preserve], 
        key=lambda x: len(x),
        reverse=True
    )
]
