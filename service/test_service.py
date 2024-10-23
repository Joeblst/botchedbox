from benchmark.models import Testcase, Test
from service.llm_service import LlmInstance


def run_test(testcase: Testcase, test: Test, llm_instance: LlmInstance) -> None:
    """Executes the given test based on its configuration."""
    test.set_state('RUNNING')
    response = llm_instance.run_test(testcase.get_config())
    test.set_score(response['score'])
    test.set_state('COMPLETE')
    response = test.responses.create(model=llm_instance.model)
    response.set_content(response['content'])
    response.set_duration(response['duration'])