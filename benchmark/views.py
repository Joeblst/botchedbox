import ast
import multiprocessing
import uuid
from concurrent.futures.process import ProcessPoolExecutor

from django.http import HttpResponse
from django.template import loader

from benchmark.models import Testcase, Test
from service import testcase_service, benchmark_service

executor = ProcessPoolExecutor(max_workers=multiprocessing.cpu_count())

def index(request):
    view = loader.get_template('benchmark/default.html')
    return HttpResponse(view.render({}, request))

def load_testcases(request):
    view = loader.get_template('testcase/table.html')
    testcase_service.load_testcases()
    testcase_objs = Testcase.objects.all()
    testcase_infos = []
    for testcases_obj in testcase_objs:
        config = ast.literal_eval(testcases_obj.config)
        testcase_infos.append({
            'id': testcases_obj.id,
            'type': config['problem']['type'],
            'description': config['problem']['description'],
        })
    context = {'testcase_infos': testcase_infos}
    return HttpResponse(view.render(context, request))

def testcases(request):
    view = loader.get_template('testcase/default.html')
    testcase_objs = Testcase.objects.all()
    testcase_infos = []
    for testcases_obj in testcase_objs:
        config = ast.literal_eval(testcases_obj.config)
        testcase_infos.append({
            'id': testcases_obj.id,
            'type': config['problem']['type'],
            'description': config['problem']['description'],
        })
    context = {'testcase_infos': testcase_infos}
    return HttpResponse(view.render(context, request))

def start_benchmark(request):
    benchmark_id = str(uuid.uuid4())
    executor.submit(benchmark_service.run_benchmark, benchmark_id)
    return HttpResponse('Benchmark started')

def get_benchmarks(request):
    view = loader.get_template('benchmark/table.html')
    tests = Test.objects.all()
    context = {'tests': tests}
    return HttpResponse(view.render(context, request))
