from datetime import datetime

from django.db import models


# Create your models here.
class Result(models.Model):
    benchmark_id = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    response = models.TextField(blank=True)
    score = models.IntegerField(default=0)
    state = models.CharField(max_length=100)
    duration = models.IntegerField(default=0)
    timestamp = models.DateTimeField(default=datetime.now)

class Benchmark(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    path = models.CharField(max_length=255)
    config = models.TextField(blank=True)
