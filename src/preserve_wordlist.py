__custom_words_to_preserve = [
    "screenshot",
    "snapchat",
    "strunk",
    "websize",
    "edited",
    "signal",
    "scan",
    "rehearsal",
    "rendered",
    "rpreplay",
    "vlcsnap",
]

words_to_not_preserve = [
    "from",
]

with open('resources/words.txt') as word_file:
    valid_words = set(word_file.read().split())

words_to_preserve = [
    *__custom_words_to_preserve, 
    *sorted(
        [w for w in valid_words if len(w) > 2 and not w in words_to_not_preserve], 
        key=lambda x: len(x),
        reverse=True
    )
]
