from configparser import ConfigParser
from datetime import datetime

class logger:
    filename = "report.txt"

    def __init__(self, config: ConfigParser):
        report_path = config.get("structure", "report_path")
        if report_path:
            self.filename = report_path + "/" + self.filename

        if not config.getboolean("structure", "continuous_reporting"):
            self.wipe_log()

    def wipe_log(self):
        with open(self.filename, "w") as f:
            print("", end="", file=f)

    def log_timestamped(self, text: str, end="\n"):
        with open(self.filename, "a") as f:
            print(datetime.now(), text, end=end, file=f)
        print(datetime.now(), text, end=end)

    def log(self, text: str, end="\n"):
        with open(self.filename, "a") as f:
            print(text, end=end, file=f)
        print(text, end=end)