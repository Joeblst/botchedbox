import ast
import csv
import importlib.util
import os
import logging

import yaml
from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform
from lxml import etree

from benchmark.models import Testcase, Result
from service.openvas_service import OpenvasService
from service.test_env_service import TestEnvService

cwd = os.getcwd()
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_testcases() -> None:
    """Loads test cases from the '../testcases' directory and saves them to the database."""
    testcases_path = os.path.join('..', 'testcases')
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
            path=os.path.join('testcases', testcase_dir),
            config=config
        )
        testcase.save()


def run_testcase(benchmark_id: str, testcase: Testcase) -> None:
    """Executes the given testcase based on its configuration."""
    testcase_config = ast.literal_eval(testcase.config)
    for llm in testcase_config['llm']:
        result = Result.objects.get(benchmark_id=benchmark_id, testcase_id=testcase.id, model=llm)
        result.set_state("RUNNING")

        problem = testcase_config.get('problem')
        result.set_problem_type(problem.get('type'))
        if problem:
            check_method = problem.get('check_method')
            if check_method == 'script':
                run_testing_script(testcase, result)
            elif check_method == 'openvas':
                run_openvas_testcase(testcase, result)
            else:
                logger.error("Error: No known check_method was provided")
                result.set_state("ERROR")
        else:
            logger.error("Error: 'problem' key is missing in the testcase configuration.")
            result.set_state("ERROR")


def run_openvas_testcase(testcase: Testcase, result: Result) -> None:
    """Runs a CVE-based test case using OpenVAS."""
    test_env_service = TestEnvService(testcase)
    containers = test_env_service.start_testenv()
    ips = [container.attrs['NetworkSettings']['Networks']['vulnerable-network']['IPAddress'] for container in containers]

    connection = UnixSocketConnection(path='/run/gvmd/gvmd.sock')
    try:
        with Gmp(connection, transform=EtreeTransform()) as gmp:
            scanner = OpenvasService(gmp=gmp, target_name=testcase.id, target_ips=ips)
            task_id = scanner.create_task()
            scanner.start_scan(task_id)
            report_id = scanner.retrieve_latest_report_id(task_id)
            report = scanner.retrieve_report(report_id)
            ref = report.xpath(f'//ref[@id="{testcase.id}"]')[0]
            result_data = ref.xpath('ancestor::result')[0]
            logger.info(etree.tostring(result_data))
            # TODO: Handle LLM fix logic here
    except Exception as e:
        logger.error(f"Error during CVE testing: {e}")
    finally:
        test_env_service.stop_testenv()


def run_phishing_testcase(testcase: Testcase, result: Result) -> None:
    """Runs a phishing test case based on the configuration."""
    test_config = ast.literal_eval(testcase.config)
    table_path = test_config['phishing'].get('table')
    if table_path:
        try:
            csv_file_path = os.path.join('/app/', testcase.path, table_path)
            with open(csv_file_path, newline='', encoding='utf-8') as file:
                reader = csv.DictReader(
                    file,
                    delimiter=';',
                    quotechar='"',
                    lineterminator='\n'
                )

                for row in reader:
                    if 'phishing' in row:
                        row['phishing'] = row['phishing'].strip().lower() == 'true'
                    logger.info(row)
                    #TODO: LLM detection

        except Exception as e:
            logger.error(f"Error reading phishing table {table_path}: {e}")


def run_testing_script(testcase: Testcase, result: Result) -> None:
    """Runs a custom testing script from the testcase."""
    script_path = os.path.join('/app/', testcase.path, 'testing_script.py')
    try:
        spec = importlib.util.spec_from_file_location("config_checker_module", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # TODO: Integrate LLM output here
        llm_output = 'Test'
        func = getattr(module, 'test_config')
        result.score = func(llm_output)
        result.state = 'FINISHED'
        result.save()
    except Exception as e:
        logger.error(f"Error executing testing script {script_path}: {e}")

