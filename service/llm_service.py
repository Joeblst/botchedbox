import os.path
import yaml

from openai import OpenAI

class LlmService:

    def __init__(self):
        with open(os.path.join("config", "llm.yaml"), "r") as file:
            self.config = yaml.load(file, Loader=yaml.FullLoader)
        self.instances = self._register_instances()

    def _register_instances(self):
        instances = {}
        for key, value in self.config["credentials"].items():
            client = OpenAI(
                base_url=value["base_url"],
                api_key=value["api_key"],
            )
            instances[key] = client
        return instances

    def get_instances(self) -> dict[str, OpenAI]:
        return self.instances