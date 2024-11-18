from benchmark.models import Testcase, Benchmark
from service import testcase_service, test_service


def run_benchmark(benchmark_id: str, temperature: int):
    benchmark = Benchmark()
    benchmark.set_benchmark_id(benchmark_id)
    benchmark.set_state('RUNNING')
    for testcase in Testcase.objects.all():
        if testcase.disabled:
            continue
        testcase_service.run_testcase(benchmark, testcase, temperature)
        test_service.run_tests(benchmark, testcase)
    benchmark.set_state('FINISHED')
