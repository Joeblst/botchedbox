import uuid
from concurrent.futures import ThreadPoolExecutor

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from service import testcase_service, benchmark_service
from .models import Test, Testcase, Benchmark, Response

executor = ThreadPoolExecutor()


def index(request):
    return render(request, 'benchmark/default.html')


def load_testcases(request):
    testcase_service.load_testcases()
    context = {'testcase_infos': testcase_service.get_testcase_infos()}
    return render(request, 'testcase/table.html', context)


def testcases(request):
    context = {'testcase_infos': testcase_service.get_testcase_infos()}
    return render(request, 'testcase/default.html', context)


def delete_testcase(request, testcase_id):
    testcase = get_object_or_404(Testcase, id=testcase_id)
    testcase.delete()
    return redirect(reverse('get_testcases'))


def start_benchmark(request):
    benchmark_id = uuid.uuid4().hex
    executor.submit(benchmark_service.run_benchmark, benchmark_id)
    return HttpResponse('Benchmark started')


def get_benchmarks(request):
    benchmarks = Benchmark.objects.all()
    context = {'benchmarks': benchmarks}
    return render(request, 'benchmark/table.html', context)


def get_benchmark(request, benchmark_id):
    current_benchmark = Benchmark.objects.get(pk=benchmark_id)
    tests = Test.objects.filter(benchmark=current_benchmark)

    return render(
        request,
        'test/default.html',
        {
            'benchmark_id': benchmark_id,
            'tests': tests
        }
    )


def delete_benchmark(request, benchmark_id):
    benchmark = get_object_or_404(Benchmark, benchmark_id=benchmark_id)
    benchmark.delete()
    return redirect(reverse('index'))


def get_tests(request, benchmark_id):
    current_benchmark = Benchmark.objects.get(pk=benchmark_id)
    tests = Test.objects.filter(benchmark=current_benchmark)
    context = {
        'tests': tests
    }
    return render(request, 'test/table.html', context)


def get_test(request, test_id):
    current_test = Test.objects.get(pk=test_id)
    responses = Response.objects.filter(test=current_test).all()

    return render(
        request,
        'test/responses.html',
        {
            'benchmark_id': current_test.benchmark.benchmark_id,
            'testcase_id': current_test.testcase_id,
            'test_responses': responses
        }
    )


def recalculate_score(request, test_id: int):
    current_test = Test.objects.get(pk=test_id)
    try:
        testcase_service.recalculate_score(current_test)
        return JsonResponse({
            'status': 'success',
            'message': f'Scores recalculated for Test {current_test}'
        })

    except ObjectDoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f'Test {current_test} not found'
        }, status=404)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
