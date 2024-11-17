import ast
import os.path
from typing import Dict, LiteralString

from django.db import models


class Benchmark(models.Model):
    benchmark_id = models.CharField(max_length=100, primary_key=True)
    state = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

    def set_benchmark_id(self, benchmark_id):
        self.benchmark_id = benchmark_id
        self.save()

    def set_state(self, state):
        self.state = state
        self.save()


class Test(models.Model):
    benchmark = models.ForeignKey(Benchmark, on_delete=models.CASCADE, related_name='responses')
    testcase_id = models.CharField(max_length=100)
    problem_type = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    score = models.IntegerField(default=0, blank=True, null=True)
    state = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['benchmark', 'testcase_id', 'model']

    def set_testcase_id(self, testcase_id):
        self.testcase_id = testcase_id
        self.save()

    def set_problem_type(self, problem_type):
        self.problem_type = problem_type
        self.save()

    def set_model(self, model):
        self.model = model
        self.save()

    def set_score(self, score):
        self.score += score
        self.save()

    def add_score(self, score):
        self.score = score
        self.save()

    def set_state(self, state):
        self.state = state
        self.save()

    def set_timestamp(self, timestamp):
        self.timestamp = timestamp
        self.save()

    def __str__(self):
        return f"Result for {self.benchmark_id}-{self.testcase_id} with {self.model}"


class Response(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='responses')
    model = models.CharField(max_length=100)
    content = models.TextField(blank=True, null=True)
    response_file = models.TextField(blank=True, null=True)
    check_result = models.TextField(blank=True, null=True)
    valid = models.BooleanField(default=False)
    duration = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def set_test(self, test):
        self.test = test
        self.save()

    def set_model(self, model):
        self.model = model
        self.save()

    def set_content(self, content):
        self.content = content
        self.save()

    def get_markdown_content(self):
        if self.content is None:
            return ""
        return "```\n" + self.content + "\n```"

    def get_markdown_response_file(self):
        if self.response_file is None:
            return ""
        return "```\n" + self.response_file + "\n```"

    def add_content(self, content):
        if self.content is None:
            self.content = content
        else:
            self.content += content
        self.save()

    def set_response_file(self, response_file):
        self.response_file = response_file
        self.save()

    def set_check_result(self, check_result):
        self.check_result = check_result
        self.save()

    def add_check_result(self, check_result):
        if self.check_result is None:
            self.check_result = ''
        self.check_result += check_result
        self.save()

    def set_valid(self, valid):
        self.valid = valid
        self.save()

    def set_duration(self, duration):
        self.duration = duration
        self.save()

    def set_timestamp(self, timestamp):
        self.timestamp = timestamp
        self.save()

    def __str__(self):
        return f"Response for {self.test.benchmark_id}-{self.test.testcase_id} with {self.test.model}"


class Testcase(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    path = models.CharField(max_length=255)
    config = models.TextField(blank=True)
    disabled = models.BooleanField(default=False)

    def set_path(self, path):
        self.path = path
        self.save()

    def set_config(self, config):
        self.config = config
        self.save()

    def get_config(self) -> Dict:
        return ast.literal_eval(self.config)

    def get_problem_type(self) -> LiteralString | str | bytes:
        config = self.get_config()
        return config.get('problem').get('type')

    def get_verify_script_path(self) -> LiteralString | str | bytes:
        config = self.get_config()
        return os.path.join(self.path, config.get('problem').get('verify_script'))

    def get_file_path(self) -> LiteralString | str | bytes | None:
        config = self.get_config()
        file_name = config.get('problem').get('file')
        if file_name:
            return os.path.join(self.path, file_name)
        return None

    def get_file(self) -> LiteralString | str | bytes | None:
        file_path = self.get_file_path()
        if file_path:
            with open(file_path, 'r') as f:
                return f.read()
        return None

    def __str__(self):
        return f"Testcase {self.id}"
