import importlib.util
import re
from io import StringIO
from typing import Tuple

import pandas as pd

from benchmark.models import Testcase, Test, Response
from service.llm_service import LlmInstance, LlmService

def run_tests(benchmark_id: str, testcase: Testcase) -> None:
    """Executes all tests for the given testcase."""
    config = testcase.get_config().get('problem')
    llm_service = LlmService()
    for test in Test.objects.filter(benchmark_id=benchmark_id, testcase_id=testcase.id, state='PENDING'):
        llm_instance = llm_service.get_instance(test.model)
        if config.get('verify_method') == 'script':
            run_test_script(testcase, test, llm_instance)
        elif config.get('verify_method') == 'table':
            run_test_table(testcase, test, llm_instance)


def _prepare_test(testcase: Testcase, test: Test) -> Tuple[Response, str, str]:
    test.set_state("RUNNING")
    response = Response()
    response.test = test
    response.set_model(test.model)
    llm_prompt_config = testcase.get_config().get('llm')
    system = llm_prompt_config.get(test.model).get('system') if llm_prompt_config.get(test.model) else None
    prompt = llm_prompt_config.get(test.model).get('prompt') if llm_prompt_config.get(test.model) else None
    system = system if system and system.strip() else llm_prompt_config.get('default').get('system')
    prompt = prompt if prompt and prompt.strip() else llm_prompt_config.get('default').get('prompt')
    return response, prompt, system

def run_test_script(testcase: Testcase, test: Test, llm_instance: LlmInstance) -> None:
    """Executes the given test based on its configuration."""
    response, prompt, system = _prepare_test(testcase, test)
    file = testcase.get_file()
    response.content, response.duration = llm_instance.execute_timed_prompt(system=system, prompt=prompt, temperature=0, file=file)
    response.save()
    test.score = calculate_score_script(testcase, response)
    test.state.set_state('FINISHED')


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


def run_test_table(testcase: Testcase, test: Test, llm_instance: LlmInstance) -> None:
    response, prompt, system = _prepare_test(testcase, test)
    file = StringIO(testcase.get_file())
    df = pd.read_csv(file, sep=";", quotechar='"')
    score_weighting = 100 / len(df) if len(df) > 0 else 1
    line = 0
    for index, row in df.iterrows():
        try:
            line += 1
            content, duration = llm_instance.execute_timed_prompt(system=system, prompt=prompt, temperature=1, file=row[0])
            response.add_content(f'line + :{content}\n')
            response.duration += duration
            test.score += (1 * score_weighting) if row[-1] == _interpret_bool_string(content) else 0
        except Exception as e:
            continue
        finally:
            response.save()
    test.set_state('FINISHED')


def _interpret_bool_string(string: str) -> bool:
    true_strings = ['true', 'yes']
    false_strings = ['false', 'no']
    string = string.lower().strip()
    if string in true_strings:
        return True
    elif string in false_strings:
        return False
    else:
        raise ValueError(f"Cannot interpret '{string}' as a boolean string")