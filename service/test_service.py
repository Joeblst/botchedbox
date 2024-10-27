import importlib.util
import re

from benchmark.models import Testcase, Test, Response
from service.llm_service import LlmInstance, LlmService

def run_tests(benchmark_id: str, testcase: Testcase) -> None:
    """Executes all tests for the given testcase."""
    llm_service = LlmService()
    for test in Test.objects.filter(benchmark_id=benchmark_id, testcase_id=testcase.id, state='PENDING'):
        llm_instance = llm_service.get_instance(test.model)
        run_test(testcase, test, llm_instance)


def run_test(testcase: Testcase, test: Test, llm_instance: LlmInstance) -> None:
    """Executes the given test based on its configuration."""
    test.state = "RUNNING"
    test.save()
    response = Response()
    response.test = test
    response.model = test.model
    file = testcase.get_file()
    llm_prompt_config = testcase.get_config().get('llm')
    system = llm_prompt_config.get(test.model).get('system') if llm_prompt_config.get(test.model) else None
    prompt = llm_prompt_config.get(test.model).get('prompt') if llm_prompt_config.get(test.model) else None
    system = system if system and system.strip() else llm_prompt_config.get('default').get('system')
    prompt = prompt if prompt and prompt.strip() else llm_prompt_config.get('default').get('prompt')
    response.content, response.duration = llm_instance.execute_timed_prompt(system=system, prompt=prompt, temperature=1, file=file)
    response.save()
    test.score = calculate_score_script(testcase, response)
    test.state = 'FINISHED'
    test.save()


def calculate_score_script(testcase: Testcase, response: Response) -> int:
    verify_script_path = testcase.get_verify_script_path()
    spec = importlib.util.spec_from_file_location("verify_module", verify_script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    verify_function = getattr(module, 'verify')
    file_match = re.search(r"@@@START_FILE@@@(.*?)@@@END_FILE@@@", response.content, re.DOTALL)

    if file_match:
        response.response_file = file_match.group(1)
        score = verify_function(testcase, response)
        response.save()
        return score
    else:
        print("No valid content found between the tokens.")
        return 0