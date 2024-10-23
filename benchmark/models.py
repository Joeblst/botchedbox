import ast
import os.path
from datetime import datetime

from django.db import models


class Test(models.Model):
    benchmark_id = models.CharField(max_length=100)
    testcase_id = models.CharField(max_length=100)
    problem_type = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    score = models.IntegerField(default=0, blank=True, null=True)
    state = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ['benchmark_id', 'testcase_id', 'model']

    def set_problem_type(self, problem_type):
        self.problem_type = problem_type
        self.save()

    def set_model(self, model):
        self.model = model
        self.save()

    def set_score(self, score):
        self.score = score
        self.save()

    def set_state(self, state):
        self.state = state
        self.save()

    def __str__(self):
        return f"Result for {self.benchmark_id}-{self.testcase_id} with {self.model}"

class Response(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='responses')
    model = models.CharField(max_length=100)
    content = models.TextField(blank=True, null=True)
    duration = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def set_model(self, model):
        self.model = model
        self.save()

    def set_content(self, content):
        self.content = content
        self.save()

    def set_duration(self, duration):
        self.duration = duration
        self.save()

    def __str__(self):
        return f"Response for {self.test.benchmark_id}-{self.test.testcase_id} with {self.test.model}"


class Testcase(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    path = models.CharField(max_length=255)
    config = models.TextField(blank=True)

    def set_path(self, path):
        self.path = path
        self.save()

    def set_config(self, config):
        self.config = config
        self.save()

    def get_config(self):
        return ast.literal_eval(self.config)

    def get_file_paths(self):
        config = self.get_config()
        file_names = config.get('problem').get('files')
        file_paths = []
        if file_names:
            for file_name in file_names:
                file_paths.append(os.path.join(self.path, file_name))
        return file_paths

    def get_files(self):
        file_paths = self.get_file_paths()
        files = []
        if file_paths:
            for file_path in file_paths:
                with open(file_path, 'r') as f:
                    files.append(f.read())
            return files
        return files

    def __str__(self):
        return f"Testcase {self.id}"