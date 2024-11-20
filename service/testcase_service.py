import ast
import logging
import os

import yaml

from benchmark.models import Testcase, Test, Response, Benchmark
from service.test_service import calculate_score_script

cwd = os.getcwd()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
                'disabled': testcase.disabled,
            })
        except (ValueError, SyntaxError) as e:
            print(f"Error parsing config for Testcase {testcase.id}: {e}")
            continue

    return testcase_infos


def load_testcases() -> None:
    """Loads test cases from the '../testcases' directory and saves them to the database."""
    testcases_path = os.path.join(cwd, 'testcases')
    for testcase_dir in os.listdir(testcases_path):
        config_path = os.path.join(testcases_path, testcase_dir, 'benchmark.yaml')
        if not os.path.isfile(config_path):
            continue
        try:
            with open(config_path, 'r') as config_file:
                config = yaml.safe_load(config_file)
        except yaml.YAMLError as e:
            logger.error(f"Error loading YAML file {config_path}: {e}")
            continue

        testcase = Testcase(
            id=config.get('problem', {}).get('id', 'Unknown'),
            path=os.path.join(testcases_path, testcase_dir),
            config=config,
            disabled=config.get('problem', False).get('disabled', False),
        )
        testcase.save()


def run_testcase(benchmark: Benchmark, testcase: Testcase, temperature: int) -> None:
    with open(os.path.join("config", "llm.yaml"), "r") as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
        for llm in config.get('credentials'):
            if llm == 'default':
                continue
            test = Test(
                benchmark=benchmark,
                testcase_id=testcase.id,
                problem_type=testcase.get_problem_type(),
                model=llm,
                state='PENDING',
                temperature=temperature
            )
            test.save()


def recalculate_score(test: Test) -> None:
    try:
        response = Response.objects.get(test=test)
        testcase = Testcase.objects.get(id=test.testcase_id)

        # Recalculate and update score
        test.score = calculate_score_script(testcase, response)
        test.save()

    except (Response.DoesNotExist, Testcase.DoesNotExist) as e:
        print(f"Error processing test {test.id}: {str(e)}")
