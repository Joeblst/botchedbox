import os.path
import time

import yaml
from openai import OpenAI


class LlmInstance:

    def __init__(self, model: str, client: OpenAI):
        self.client = client
        self.model = model

    def get_model(self):
        return self.model

    def execute_timed_prompt(self, system: str, prompt: str, temperature: float = 0, files: list = None):
        if files is not None and len(files) > 0:
            file_strings = []
            for file in files:
                file_strings.append(f'@@@START_BOTCHED@@@\n{file}\n@@@END_BOTCHED@@@')
            prompt_appendix = '\n'.join(file_strings)
            prompt = '\n\n'.join([prompt, prompt_appendix])

        start = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )
        end = time.time()
        return response.choices[0].message.content, end - start


class LlmService:

    def __init__(self):
        with open(os.path.join("config", "llm.yaml"), "r") as file:
            self.config = yaml.load(file, Loader=yaml.FullLoader)
        self.instances = self._register_instances()

    def _register_instances(self):
        instances = {}
        for key, value in self.config["credentials"].items():
            question = LlmInstance(
                key,
                OpenAI(
                    base_url=value["base_url"],
                    api_key=value["api_key"],
                )
            )
            instances[key] = question
        return instances

    def get_instance(self, model: str) -> LlmInstance:
        return self.instances.get(model)



