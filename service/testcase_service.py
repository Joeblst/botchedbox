import os
import yaml

from benchmark.models import Benchmark


def load_testcases():
    for testcase_dir in os.listdir(os.path.join('..', 'testcases')):
        try:
            config = yaml.safe_load(open(os.path.join('..', 'testcases', testcase_dir, 'benchmark.yaml'), 'r'))
        except:
            continue
        testcase = Benchmark()
        testcase.id = config['problem']['id']
        testcase.name = config['problem']['id']
        testcase.path = os.path.join('testcases', testcase_dir)
        testcase.config = config
        testcase.save()



class TestcaseService:

    def __init__(self):
        pass

