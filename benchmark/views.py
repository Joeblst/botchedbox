import ast

from django.http import HttpResponse
from django.template import loader

from benchmark.models import Benchmark
from service import testcase_service

# Create your views here.
def index(request):
    view = loader.get_template('index.html')
    return HttpResponse(view.render({}, request))

def load_testcases(request):
    view = loader.get_template('testcases/table.html')
    testcase_service.load_testcases()
    testcase_objs = Benchmark.objects.all()
    testcase_infos = []
    for testcases_obj in testcase_objs:
        config = ast.literal_eval(testcases_obj.config)
        testcase_infos.append({
            'id': testcases_obj.id,
            'type': config['problem']['type'],
            'openvas': config['problem']['openvas_required'],
            'description': config['problem']['description'],
        })
    context = {'testcase_infos': testcase_infos}
    return HttpResponse(view.render(context, request))

def testcases(request):
    view = loader.get_template('testcases/default.html')
    testcase_objs = Benchmark.objects.all()
    testcase_infos = []
    for testcases_obj in testcase_objs:
        config = ast.literal_eval(testcases_obj.config)
        testcase_infos.append({
            'id': testcases_obj.id,
            'type': config['problem']['type'],
            'openvas': config['problem']['openvas_required'],
            'description': config['problem']['description'],
        })
    context = {'testcase_infos': testcase_infos}
    return HttpResponse(view.render(context, request))
