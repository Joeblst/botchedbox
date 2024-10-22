import os
import tempfile

import ansible_runner

from benchmark.models import Result


def run_ansible_playbook(result: Result, ips: list):
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.yml') as playbook:
        playbook.write(result.response)
        playbook.close()

        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.ini') as inventory:
            inventory.write('\n'.join(
                ['[all]'] + [f'{ip} ansible_user=root ansible_password=root' for ip in ips]
            ))
            inventory.close()

            env_vars = {
                'ANSIBLE_HOST_KEY_CHECKING': 'false',
                'ANSIBLE_REMOTE_USER': 'root',
                'ANSIBLE_PASSWORD': 'root',
                'ANSIBLE_SSH_EXTRA_ARGS': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null',
            }
            r = ansible_runner.run(playbook=playbook.name, inventory=inventory.name, envvars=env_vars)
        return r.rc