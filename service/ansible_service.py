import ansible_runner
import tempfile

from benchmark.models import Result


def run_ansible_playbook(result: Result):
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.yml') as temp_playbook:
        temp_playbook.write(result.response)
        temp_playbook.close()

        r = ansible_runner.run(playbook=temp_playbook.name)
        return r.rc