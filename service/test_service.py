import importlib.util
import re

from benchmark.models import Testcase, Test, Response
from service.llm_service import LlmInstance, LlmService

file_output_pattern = r"@@@START_FILE@@@(.*?)@@@END_FILE@@@"

def run_tests(benchmark_id: str, testcase: Testcase) -> None:
    """Executes all tests for the given testcase."""
    llm_service = LlmService()
    for test in Test.objects.filter(benchmark_id=benchmark_id, testcase_id=testcase.id, state='PENDING'):
        llm_instance = llm_service.get_instance(test.model)
        run_test(testcase, test, llm_instance)


def run_test(testcase: Testcase, test: Test, llm_instance: LlmInstance) -> None:
    """Executes the given test based on its configuration."""
    response = Response()
    response.test = test
    response.model = test.model
    files = testcase.get_files()
    llm_prompt_config = testcase.get_config().get('llm')
    system = llm_prompt_config.get(test.model).get('system') if llm_prompt_config.get(test.model) else None
    prompt = llm_prompt_config.get(test.model).get('prompt') if llm_prompt_config.get(test.model) else None
    system = system if system and system.strip() else llm_prompt_config.get('default').get('system')
    prompt = prompt if prompt and prompt.strip() else llm_prompt_config.get('default').get('prompt')
    response.content, response.duration = llm_instance.execute_timed_prompt(system=system, prompt=prompt, temperature=0, files=files)
    response.save()
    test.score = calculate_score_script(testcase, response.content)
    test.state = 'FINISHED'
    test.save()


def calculate_score_script(testcase: Testcase, llm_output: str) -> int:
    verify_script_path = testcase.get_verify_script_path()
    spec = importlib.util.spec_from_file_location("verify_module", verify_script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    verify_function = getattr(module, 'verify')
    file_matches = re.findall(file_output_pattern, llm_output, re.DOTALL)

    if file_matches:
        for i, match in enumerate(file_matches, 1):
            # TODO: Multiple files
            return verify_function(testcase, match)
    else:
        print("No valid content found between the tokens.")
        return 0