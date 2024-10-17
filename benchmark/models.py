import ast
import os.path
from datetime import datetime

from django.db import models


class Result(models.Model):
    benchmark_id = models.CharField(max_length=100)
    testcase_id = models.CharField(max_length=100)
    problem_type = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    response = models.TextField(blank=True, null=True)
    score = models.IntegerField(default=0, blank=True, null=True)
    state = models.CharField(max_length=100)
    duration = models.IntegerField(default=0, blank=True, null=True)
    timestamp = models.DateTimeField(default=datetime.now)
    class Meta:
        unique_together = ['benchmark_id', 'testcase_id', 'model']

    def set_state(self, state):
        self.state = state
        self.save()

    def set_problem_type(self, problem_type):
        self.problem_type = problem_type
        self.save()


class Testcase(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    path = models.CharField(max_length=255)
    config = models.TextField(blank=True)

    def get_config(self):
        return ast.literal_eval(self.config)

    def get_files(self):
        config = self.get_config()
        file_paths = config.get('problem').get('files')
        files = []
        if file_paths:
            for file_path in file_paths:
                file_path = os.path.join(self.path, file_path)
                with open(file_path, 'r') as f:
                    files.append(f.read())
            return files
        return None