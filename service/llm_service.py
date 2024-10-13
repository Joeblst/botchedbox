import os.path

import yaml


class LlmService:

    def __init__(self):
        with open(os.path.join("config", "llm.yml"), "r") as file:
            self.config = yaml.load(file, Loader=yaml.FullLoader)
            self.llms = self.config["llms"]
