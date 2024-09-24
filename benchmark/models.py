from datetime import datetime

from django.db import models


class Result(models.Model):
    benchmark_id = models.CharField(max_length=100)
    testcase_id = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    response = models.TextField(blank=True, null=True)
    score = models.IntegerField(default=0, blank=True, null=True)
    state = models.CharField(max_length=100)
    duration = models.IntegerField(default=0, blank=True, null=True)
    timestamp = models.DateTimeField(default=datetime.now)
    class Meta:
        unique_together = ['benchmark_id', 'testcase_id', 'model']


class Testcase(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    path = models.CharField(max_length=255)
    config = models.TextField(blank=True)
