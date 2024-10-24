import logging
import os
import yaml

from benchmark.models import Testcase, Test

cwd = os.getcwd()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            id=config['problem']['id'],
            path=os.path.join(testcases_path, testcase_dir),
            config=config
        )
        testcase.save()


def run_testcase(benchmark_id: str, testcase: Testcase) -> None:
    """Executes the given testcase based on its configuration."""
    testcase_config = testcase.get_config()
    for llm in testcase_config.get('llm'):
        if llm == 'default':
            continue
        test = Test(
            benchmark_id=benchmark_id,
            testcase_id=testcase.id,
            model=llm,
            state='PENDING'
        )
        test.save()


