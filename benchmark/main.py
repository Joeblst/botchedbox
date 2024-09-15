from openvas import OpenVasScanner
from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform
from openai import OpenAI
from lxml import etree
import ansible_runner
import tempfile
import os
import nmap

if __name__ == "__main__":
        connection = UnixSocketConnection(path='/run/gvmd/gvmd.sock')
        with Gmp(connection, transform=EtreeTransform()) as gmp:
            scanner = OpenVasScanner(gmp=gmp, target_ip="172.20.0.2")
            task_id = scanner.create_task()
            #scanner.start_scan(scan_id)
            report_id = scanner.retrieve_latest_report_id(task_id)
            report = scanner.retrieve_report(report_id)
            ref = report.xpath('//ref[@id="CVE-2020-1938"]')[0]
            result = ref.xpath('ancestor::result')[0]
            print(etree.tostring(result))
            print(scanner.get_cve_description("CVE-2020-1938"))
            #client = OpenAI()
            #completion = client.chat.completions.create(
            #    model="gpt-4o-mini",
            #    messages=[
            #        {"role": "system", "content": "You only return a Ansible Playbook YAML-File nothing else which fixes the specified CVE"},
            #        {
            #            "role": "user",
            #            "content": scanner.get_cve_description("CVE-2020-1938"),
            #        }
            #    ]
            #)
            #print(completion.choices[0].message)

            #nm = nmap.PortScanner()
            #results = nm.scan('firewall', '1-65535')
            #print(results)

            playbook_string = """
---
- name: Retrieve UFW rules
  hosts: all
  become: yes
  tasks:
    - name: Get UFW status and rules
      command: ufw status verbose
      register: ufw_rules

    - name: Display UFW rules
      debug:
        var: ufw_rules.stdout
                """
            inventory_string = """
[all]
firewall
"""

            with tempfile.TemporaryDirectory() as temp_dir:
                playbook_path = os.path.join(temp_dir, 'playbook.yml')
                inventory_path = os.path.join(temp_dir, 'inventory')

                with open(playbook_path, 'w') as playbook_file:
                    playbook_file.write(playbook_string)
                with open(inventory_path, 'w') as inventory_file:
                    inventory_file.write(inventory_string)

                runner = ansible_runner.run(
                    playbook=playbook_path,
                    inventory=inventory_path,
                    extravars={
                        'ansible_user': 'root',
                        'ansible_password': 'root',
                        'ansible_become': True,
                        'ansible_become_method': 'sudo'
                    }
                )

                print(runner.status, runner.rc, runner.stdout.read(), runner.stderr.read())
