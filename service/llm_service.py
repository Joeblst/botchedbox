import os.path
import time
import yaml

from anthropic import Anthropic
from openai import OpenAI


class LlmInstance:

    def __init__(self, model: str, client: OpenAI | Anthropic):
        self.client = client
        self.model = model

    def get_model(self):
        return self.model

    def execute_timed_prompt(self, system: str, prompt: str, temperature: float = 0, file: str = None):
        if file is not None and len(file) > 0:
            file_string = f'@@@START_FILE@@@\n{file}\n@@@END_FILE@@@'
            prompt = '\n\n'.join([prompt, file_string])

        start = time.time()
        if type(self.client) is Anthropic:
            response = self._get_anthropic_message(system, prompt, temperature)
        else:
            response = self._get_openai_message(system, prompt, temperature)
        end = time.time()
        return response, end - start

    def _get_openai_message(self, system: str, prompt: str, temperature: float = 0) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )
        return response.choices[0].message.content

    def _get_anthropic_message(self, system: str, prompt: str, temperature: float = 0) -> str:
        response = self.client.messages.create(
            model=self.model,
            system=system,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens = 4096
        )
        return response.content[0].text


class LlmService:

    def __init__(self):
        with open(os.path.join("config", "llm.yaml"), "r") as file:
            self.config = yaml.load(file, Loader=yaml.FullLoader)
        self.instances = self._register_instances()

    def _register_instances(self):
        instances = {}
        for key, value in self.config.get('credentials', {}).items():
            if value.get('api', 'openai') == 'anthropic':
                instance = LlmInstance(
                    key,
                    Anthropic(
                        base_url=value.get('base_url'),
                        api_key=value.get('api_key'),
                    )
                )
            else:
                instance = LlmInstance(
                    key,
                    OpenAI(
                        base_url=value.get('base_url'),
                        api_key=value.get('api_key'),
                    )
                )
            instances[key] = instance
        return instances

    def get_instance(self, model: str) -> LlmInstance:
        return self.instances.get(model)
