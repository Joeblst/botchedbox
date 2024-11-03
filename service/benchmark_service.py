from benchmark.models import Testcase, Benchmark
from service import testcase_service, test_service


def run_benchmark(benchmark_id: str):
    benchmark = Benchmark()
    benchmark.set_benchmark_id(benchmark_id)
    benchmark.set_state('RUNNING')
    for testcase in Testcase.objects.all():
        testcase_service.run_testcase(benchmark, testcase)
        test_service.run_tests(benchmark, testcase)
    benchmark.set_state('FINISHED')
