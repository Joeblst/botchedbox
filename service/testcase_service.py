import ast
import importlib.util
import os
import subprocess

import docker
import yaml
from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform
from lxml import etree

from benchmark.models import Testcase, Result
from service.openvas_service import OpenvasService


def load_testcases():
    for testcase_dir in os.listdir(os.path.join('..', 'testcases')):
        try:
            config = yaml.safe_load(open(os.path.join('..', 'testcases', testcase_dir, 'benchmark.yaml'), 'r'))
        except:
            continue
        testcase = Testcase()
        testcase.id = config['problem']['id']
        testcase.path = os.path.join('testcases', testcase_dir)
        testcase.config = config
        testcase.save()


def run_testcase(benchmark_id: str, testcase: Testcase):
    testcase_config = ast.literal_eval(testcase.config)
    for llm in testcase_config['llm'].keys():
        result = Result.objects.get(benchmark_id=benchmark_id, testcase_id=testcase.id, model=llm)
        result.state = 'RUNNING'
        result.save()
        if testcase_config['problem']['check_method'] == 'script':
            run_testing_script(testcase, result)
        elif testcase_config['problem']['type'] == 'cve':
            run_cve_testcase(testcase, result)
        elif testcase_config['problem']['type'] == 'phishing':
            run_phishing_testcase(testcase, result)
        elif testcase_config['problem']['type'] == 'config':
            run_config_testcase(testcase, result)
        elif testcase_config['problem']['type'] == 'firewall':
            run_firewall_testcase(testcase, result)


def run_cve_testcase(testcase: Testcase, result: Result):
    containers = _start_testenv(testcase)
    ips = []
    for container in containers:
        ips.append(container.attrs['NetworkSettings']['Networks']['vulnerable-network']['IPAddress'])
    connection = UnixSocketConnection(path='/run/gvmd/gvmd.sock')
    with Gmp(connection, transform=EtreeTransform()) as gmp:
        scanner = OpenvasService(gmp=gmp, target_name=testcase.id, target_ips=ips)
        task_id = scanner.create_task()
        scanner.start_scan(task_id)
        report_id = scanner.retrieve_latest_report_id(task_id)
        report = scanner.retrieve_report(report_id)
        ref = report.xpath(f'//ref[@id="{testcase.id}"]')[0]
        result = ref.xpath('ancestor::result')[0]
        print(etree.tostring(result))
        #TODO: LLM fix
    _stop_testenv(testcase)

def run_firewall_testcase(testcase: Testcase, result: Result):
    pass

def run_phishing_testcase(testcase: Testcase, result: Result):
    pass

def run_config_testcase(testcase: Testcase, result: Result):
    pass

def run_testing_script(testcase: Testcase, result: Result):
    spec = importlib.util.spec_from_file_location("config_checker_module", '/app/' + testcase.path + '/testing_script.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # TODO LLM
    llm_output = 'Test'
    func = getattr(module, 'test_config')
    return func(llm_output)

def _start_testenv(testcase: Testcase):
    compose_path = "/app/" + testcase.path + '/docker-compose.yml'
    try:
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_path,
                "up",
                "-d",
                "--build",
                "--remove-orphans",
                "--force-recreate",
                "-V"
            ],
            check=True
        )
        print("Docker Compose started successfully.")
        client = docker.from_env()
        containers_list = client.containers.list()
        containers = []
        for container in containers_list:
            if testcase.id.lower() in container.name:
                containers.append(container)
        return containers
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running Docker Compose: {e}")

def _stop_testenv(testcase: Testcase):
    compose_path = "/app/" + testcase.path + '/docker-compose.yml'
    try:
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_path,
                "down",
                "-v"
            ],
            check=True
        )
        print("Docker Compose stopped successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running Docker Compose: {e}")