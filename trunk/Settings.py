import json


class Settings:
    def __init__(self):
        self.settingsFileName = "settings.json"
        self.settingsData = None

    def get_media_path(self):
        try:
            with open(self.settingsFileName) as json_file:
                self.settingsData = json.load(json_file)
            return self.settingsData["mediaPath"]
        except FileNotFoundError:
            return None

    def write_settings(self):
        try:
            with open(self.settingsFileName, 'w') as outfile:
                json.dump(self.settingsData, outfile, indent=4)
        except FileNotFoundError:
            print("Error saving Settings file")

    def create_settings(self):
        self.settingsData = {
            "mediaPath": "-",
            "downloadFolder": "-"
        }

    def ask_settings(self):
        self.create_settings()
        print("SETTINGS:")
        self.settingsData["mediaPath"] = input(" * What's the media path location: ")
        self.settingsData["downloadFolder"] = input(" * What's the download folder path: ")

    def check_settings(self):
        try:
            with open(self.settingsFileName) as json_file:
                self.settingsData = json.load(json_file)
        except FileNotFoundError:
            pass
        if not self.settingsData:
            self.ask_settings()
            self.write_settings()
