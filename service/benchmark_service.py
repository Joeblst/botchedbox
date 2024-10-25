import ast
import multiprocessing
from concurrent.futures.thread import ThreadPoolExecutor

from benchmark.models import Testcase, Test
from service import testcase_service, test_service

def run_benchmark(benchmark_id: str):
    for testcase in Testcase.objects.all():
        testcase_service.run_testcase(benchmark_id, testcase)
        test_service.run_tests(benchmark_id, testcase)