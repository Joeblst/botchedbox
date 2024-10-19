import ast
import multiprocessing
from concurrent.futures.thread import ThreadPoolExecutor

from benchmark.models import Testcase, Result
from service import testcase_service

executor = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())

def run_benchmark(benchmark_id: str):
    for testcase in Testcase.objects.all():
        for llm in ast.literal_eval(testcase.config)['llm'].keys():
            if llm == 'default':
                continue
            result = Result()
            result.benchmark_id = benchmark_id
            result.testcase_id = testcase.id
            result.model = llm
            result.state = 'PENDING'
            result.save()
        executor.submit(testcase_service.run_testcase, benchmark_id, testcase)
