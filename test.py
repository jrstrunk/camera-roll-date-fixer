import json
import src.determine_date as determine_date
from configparser import ConfigParser

def test_filename_date_parser():
    config = ConfigParser()
    config.read('config.ini')

    # Open the JSON file
    with open('resources/photonames.json') as f:
        data = json.load(f)

    # Iterate over each top-level key
    for filename in data:
        date = determine_date.from_file_name(filename, config) or ""

        if not type(date) == str:
            date = date.strftime("%Y/%m/%d %H:%M:%S")

        # the millisecond of the date will not be output in any way to the
        # final file so we do not parse it
        expected_date = data[filename]["date"].split(".")[0]

        if not date == expected_date:
            print(
                "Failed match on ", 
                filename,
                " - Expected: \"",
                expected_date,
                "\" got \"",
                date,
                "\"", 
                sep="",
            )

test_filename_date_parser()
