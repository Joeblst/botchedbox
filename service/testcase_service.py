import ast
import csv
import importlib.util
import os
import subprocess
import logging

import docker
import yaml
from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform
from lxml import etree

from benchmark.models import Testcase, Result
from service.openvas_service import OpenvasService

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
        result.state = 'RUNNING'
        result.save()

        problem = testcase_config.get('problem')
        if problem:
            check_method = problem.get('check_method')
            if check_method == 'script':
                run_testing_script(testcase, result)
            else:
                problem_type = problem.get('type')
                run_problem_type_testcase(problem_type, testcase, result)
        else:
            logger.error("Error: 'problem' key is missing in the testcase configuration.")


def run_problem_type_testcase(problem_type: str, testcase: Testcase, result: Result) -> None:
    """Routes the testcase execution based on the problem type."""
    if problem_type == 'cve':
        run_cve_testcase(testcase, result)
    elif problem_type == 'phishing':
        run_phishing_testcase(testcase, result)
    elif problem_type == 'config':
        run_config_testcase(testcase, result)
    elif problem_type == 'firewall':
        run_firewall_testcase(testcase, result)
    else:
        logger.error(f"Unknown problem type: {problem_type}")


def run_cve_testcase(testcase: Testcase, result: Result) -> None:
    """Runs a CVE-based test case using OpenVAS."""
    containers = _start_testenv(testcase)
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
        _stop_testenv(testcase)


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


def run_config_testcase(testcase: Testcase, result: Result) -> None:
    """Runs a configuration-based test case."""
    # Placeholder for configuration test case logic
    pass


def run_firewall_testcase(testcase: Testcase, result: Result) -> None:
    """Runs a firewall-based test case."""
    # Placeholder for firewall test case logic
    pass


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


def _start_testenv(testcase: Testcase) -> list:
    """Starts the Docker environment for the test case."""
    compose_path = os.path.join("/app/", testcase.path, 'docker-compose.yml')
    try:
        subprocess.run(
            [
                "docker-compose",
                "-f", compose_path,
                "up", "-d",
                "--build",
                "--remove-orphans",
                "--force-recreate",
                "-V"
            ],
            check=True
        )
        logger.info("Docker Compose started successfully.")

        client = docker.from_env()
        containers = [container for container in client.containers.list() if testcase.id.lower() in container.name]
        return containers
    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred while running Docker Compose: {e}")
        return []


def _stop_testenv(testcase: Testcase) -> None:
    """Stops the Docker environment for the test case."""
    compose_path = os.path.join("/app/", testcase.path, 'docker-compose.yml')
    try:
        subprocess.run(
            ["docker-compose", "-f", compose_path, "down", "-v"],
            check=True
        )
        logger.info("Docker Compose stopped successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred while stopping Docker Compose: {e}")

