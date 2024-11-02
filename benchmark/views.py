import json

import yaml
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.urls import reverse

from .models import Test, Testcase
from service import testcase_service, benchmark_service
import ast
import uuid
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()

def index(request):
    return render(request, 'benchmark/default.html')


def get_testcase_infos():
    """Helper function to get formatted testcase information."""
    testcase_objs = Testcase.objects.all()
    testcase_infos = []

    for testcase in testcase_objs:
        try:
            config = ast.literal_eval(testcase.config)
            testcase_infos.append({
                'id': testcase.id,
                'type': config.get('problem', {}).get('type', 'Unknown'),
                'description': config.get('problem', {}).get('description', 'No description available'),
            })
        except (ValueError, SyntaxError) as e:
            print(f"Error parsing config for Testcase {testcase.id}: {e}")
            continue

    return testcase_infos


def load_testcases(request):
    testcase_service.load_testcases()
    context = {'testcase_infos': get_testcase_infos()}
    return render(request, 'testcase/table.html', context)


def testcases(request):
    context = {'testcase_infos': get_testcase_infos()}
    return render(request, 'testcase/default.html', context)


def start_benchmark(request):
    benchmark_id = uuid.uuid4().hex
    executor.submit(benchmark_service.run_benchmark, benchmark_id)
    return HttpResponse('Benchmark started')


def get_benchmarks(request):
    tests = Test.objects.all()
    context = {'tests': tests}
    return render(request, 'benchmark/table.html', context)


def benchmark(request, benchmark_id):
    tests = Test.objects.filter(benchmark_id=benchmark_id)
    test_responses = {}

    for test in tests:
        responses = test.responses.all()
        if test.model in test_responses:
            test_responses[test.model].extend(responses)
        else:
            test_responses[test.model] = list(responses)

    return render(
        request,
        'benchmark/responses.html',
        {
            'benchmark_id': benchmark_id,
            'test_responses': test_responses
        }
    )


def recalculate_benchmark_scores(request, benchmark_id):
    try:
        testcase_service.recalculate_scores(benchmark_id)
        return JsonResponse({
            'status': 'success',
            'message': f'Scores recalculated for benchmark {benchmark_id}'
        })

    except ObjectDoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f'Benchmark {benchmark_id} not found'
        }, status=404)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


def delete_testcase(request, testcase_id):
    testcase = get_object_or_404(Testcase, id=testcase_id)
    testcase.delete()
    return redirect(reverse('testcases'))
