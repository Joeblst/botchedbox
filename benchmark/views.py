import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from service import testcase_service, benchmark_service
from .models import Test, Testcase, Benchmark, Response

executor = ThreadPoolExecutor()


def index(request):
    benchmarks = Benchmark.objects.all().order_by('-timestamp')
    finished_count = benchmarks.filter(state='FINISHED').count()
    test_count = Test.objects.count()
    latest_run = benchmarks.first().timestamp if benchmarks.exists() else None
    running_count = benchmarks.filter(state='RUNNING').count()

    context = {
        'benchmarks': benchmarks,
        'finished_count': finished_count,
        'test_count': test_count,
        'latest_run': latest_run,
        'running_count': running_count
    }
    return render(request, 'benchmark/default.html', context)


def get_benchmarks(request):
    benchmarks = Benchmark.objects.all().order_by('-timestamp')
    return render(request, 'benchmark/table.html', {'benchmarks': benchmarks})


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


def toggle_testcase(request, testcase_id):
    testcase = get_object_or_404(Testcase, id=testcase_id)
    testcase.disabled = not testcase.disabled
    testcase.save()
    return redirect(reverse('get_testcases'))


def start_benchmark(request):
    benchmark_id = uuid.uuid4().hex
    executor.submit(benchmark_service.run_benchmark, benchmark_id)
    return HttpResponse('Benchmark started')


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
    current_test = get_object_or_404(Test, pk=test_id)
    responses_list = Response.objects.filter(test=current_test).order_by('-timestamp')
    paginator = Paginator(responses_list, 1)
    page = request.GET.get('page')

    try:
        response = paginator.page(page)
    except PageNotAnInteger:
        response = paginator.page(1)
    except EmptyPage:
        response = paginator.page(paginator.num_pages)

    testcase = get_object_or_404(Testcase, id=current_test.testcase_id)
    is_manual = testcase.get_config().get('problem', {}).get('verify_method') == 'manual'

    current_checks = {}
    if response and response[0].check_result:
        try:
            current_checks = json.loads(response[0].check_result)
        except json.JSONDecodeError:
            current_checks = {}

    return render(
        request,
        'test/responses.html',
        {
            'benchmark_id': current_test.benchmark.benchmark_id,
            'testcase_id': current_test.testcase_id,
            'response': response[0] if response else None,
            'page_obj': response,
            'is_manual': is_manual,
            'current_checks': current_checks
        }
    )


def manual_validation(request, response_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    response = get_object_or_404(Response, id=response_id)
    testcase = get_object_or_404(Testcase, id=response.test.testcase_id)
    is_manual = testcase.get_config().get('problem', {}).get('verify_method') == 'manual'

    if is_manual:
        # Calculate base score for manual validation
        base_score = sum([
            request.POST.get('valid') == 'true',
            request.POST.get('executable') == 'true',
            request.POST.get('available_function') == 'true',
            request.POST.get('formatting') == 'true',
            request.POST.get('knowledge') == 'true',
        ]) * 20

        validation_data = {
            'valid': request.POST.get('valid') == 'true',
            'executable': request.POST.get('executable') == 'true',
            'available_function': request.POST.get('available_function') == 'true',
            'formatting': request.POST.get('formatting') == 'true',
            'knowledge': request.POST.get('knowledge') == 'true',
            'base_score': base_score,
        }
    else:
        # For automated validation, maintain existing validation data
        try:
            validation_data = json.loads(response.check_result) if response.check_result else {}
        except json.JSONDecodeError:
            validation_data = {}

    # Handle score override and comments for both manual and automated
    override_score = request.POST.get('score_override')
    validation_data.update({
        'override_score': override_score if override_score.strip() else None,
        'final_score': int(override_score) if override_score.strip() else validation_data.get('base_score', 0),
        'comment': request.POST.get('comment', '').strip(),
        'timestamp': datetime.now().isoformat()
    })

    response.check_result = json.dumps(validation_data)
    if is_manual:
        response.valid = validation_data['valid']

    response.test.score = validation_data['final_score']
    response.test.save()
    response.save()

    return JsonResponse({
        'status': 'success',
        'message': 'Validation saved successfully',
        'score': validation_data['final_score']
    })


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


def get_testcase_tests(request, testcase_id):
    testcase = get_object_or_404(Testcase, id=testcase_id)
    tests = Test.objects.filter(testcase_id=testcase_id).order_by('-timestamp')

    # Calculate statistics for the testcase
    total_tests = tests.count()
    validated_tests = tests.filter(responses__valid=True).distinct().count()
    pending_validation = tests.exclude(responses__valid=True).distinct().count()

    # Calculate average score for validated tests
    validated_tests_list = tests.filter(responses__valid=True, score__isnull=False)
    avg_score = sum([test.score for test in
                     validated_tests_list]) / validated_tests_list.count() if validated_tests_list.exists() else 0

    context = {
        'testcase': testcase,
        'tests': tests,
        'total_tests': total_tests,
        'validated_tests': validated_tests,
        'pending_validation': pending_validation,
        'avg_score': avg_score,
    }
    return render(request, 'testcase/tests.html', context)
