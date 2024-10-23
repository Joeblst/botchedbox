import ast
import multiprocessing
from concurrent.futures.thread import ThreadPoolExecutor

from benchmark.models import Testcase, Test
from service import testcase_service

executor = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())

def run_benchmark(benchmark_id: str):
    for testcase in Testcase.objects.all():
        testcase_service.run_testcase(benchmark_id, testcase)
