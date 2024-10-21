import csv
import importlib.util
import os
import logging
from curses.ascii import isspace

import yaml
from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform
from lxml import etree

from benchmark.models import Testcase, Result
from service.ansible_service import run_ansible_playbook
from service.llm_service import LlmService, LlmInstance
from service.openvas_service import OpenvasService
from service.test_env_service import TestEnvService

cwd = os.getcwd()
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
llm_service = LlmService()

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
        llm_instance = llm_service.get_instance(llm)
        result = Result.objects.get(benchmark_id=benchmark_id, testcase_id=testcase.id, model=llm)
        result.set_state("RUNNING")

        problem = testcase_config.get('problem')
        result.set_problem_type(problem.get('type'))
        if problem:
            check_method = problem.get('check_method')
            if check_method == 'script':
                run_testing_script(testcase, result, llm_instance)
            elif check_method == 'openvas':
                run_openvas_testcase(testcase, result, llm_instance)
            else:
                logger.error("Error: No known check_method was provided")
                result.set_state("ERROR")
        else:
            logger.error("Error: 'problem' key is missing in the testcase configuration.")
            result.set_state("ERROR")


def run_openvas_testcase(testcase: Testcase, result: Result, llm_instance) -> None:
    """Runs a CVE-based test case using OpenVAS."""
    test_env_service = TestEnvService(testcase)
    containers = test_env_service.start_testenv()
    ips = [
        container.attrs['NetworkSettings']['Networks']['vulnerable-network']['IPAddress'] for container in containers
    ]
    connection = UnixSocketConnection(path='/run/gvmd/gvmd.sock')
    try:
        with Gmp(connection, transform=EtreeTransform()) as gmp:
            scanner = OpenvasService(gmp=gmp, target_name=testcase.id, target_ips=ips)
            result_data = _run_openvas_scan(testcase, scanner)
            tags_info = "Information about the Problem: " + result_data.xpath('//tags/text()')[0] if result_data.xpath('//tags/text()') else None
            solution_info = "Information about the Solution: " + result_data.xpath('//solution/text()')[0] if result_data.xpath('//tags/text()') else None
            host_info = "The hosts are: " + ", ".join(ips)
            prompt_appendix = "\n\n".join([host_info, tags_info, solution_info])
            run_llm_prompt(testcase, result, llm_instance, prompt_appendix)
            run_ansible_playbook(result)
            result_data = _run_openvas_scan(testcase, scanner)
            result.state = 'FINISHED'
            result.save()
    except Exception as e:
        logger.error(f"Error during CVE testing: {e}")
    finally:
        test_env_service.stop_testenv()

def _run_openvas_scan(testcase: Testcase, scanner: OpenvasService):
    task_id = scanner.create_task()
    scanner.start_scan(task_id)
    report_id = scanner.retrieve_latest_report_id(task_id)
    report = scanner.retrieve_report(report_id)
    ref = report.xpath(f'//ref[@id="{testcase.id}"]')[0]
    return ref.xpath('ancestor::result')[0]


def run_phishing_testcase(testcase: Testcase, result: Result, llm_instance) -> None:
    """Runs a phishing test case based on the configuration."""
    test_config = testcase.get_config()
    table_path = test_config['phishing'].get('table')
    if table_path:
        try:
            csv_file_path = os.path.join(testcase.path, table_path)
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


def run_testing_script(testcase: Testcase, result: Result, llm_instance: LlmInstance) -> None:
    """Runs a custom testing script from the testcase."""
    test_config = testcase.get_config()
    script_path = os.path.join(testcase.path, test_config.get('problem').get('check_script'))
    try:
        spec = importlib.util.spec_from_file_location("checker_module", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        func = getattr(module, 'do_test')
        run_llm_prompt(testcase, func, llm_instance)
        result.score = func(result.response)
        result.state = 'FINISHED'
        result.save()
    except Exception as e:
        logger.error(f"Error executing testing script {script_path}: {e}")

def run_llm_prompt(testcase: Testcase, result: Result, llm_instance: LlmInstance, prompt_appendix: str = None):
    llm_prompt_config = testcase.get_config().get('llm')
    model = llm_instance.get_model()
    files = testcase.get_files()
    system = llm_prompt_config.get(model).get('system') if llm_prompt_config.get(model) else None
    prompt = llm_prompt_config.get(model).get('prompt') if llm_prompt_config.get(model) else None
    system = system if system and system.strip() else llm_prompt_config.get('default').get('system')
    prompt = prompt if prompt and prompt.strip() else llm_prompt_config.get('default').get('prompt')
    prompt = "\n\n".join([prompt, prompt_appendix])
    result.response, result.duration = llm_instance.execute_timed_prompt(system, prompt, files)
    result.save()