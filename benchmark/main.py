from openvas import OpenVasScanner
from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform
from openai import OpenAI
from lxml import etree

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
            client = OpenAI()
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You only return a Ansible Playbook YAML-File nothing else which fixes the specified CVE"},
                    {
                        "role": "user",
                        "content": scanner.get_cve_description("CVE-2020-1938"),
                    }
                ]
            )
            print(completion.choices[0].message)
