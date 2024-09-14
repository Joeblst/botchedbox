import sys
import time
from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform
from lxml import etree

def create_task_and_scan(hosts):
    # Connect to the OpenVAS Unix socket (modify to fit your connection setup)
    connection = UnixSocketConnection(path='/run/gvmd/gvmd.sock')

    # Open GVM connection
    with Gmp(connection, transform=EtreeTransform()) as gmp:
        # Authenticate
        gmp.authenticate(username='admin', password='admin')

        # Check if SSH credentials already exist
        print("Checking for existing SSH credentials...")
        existing_credentials = gmp.get_credentials(filter_string="name='Root SSH Credential'")
        if len(existing_credentials.xpath("//credential")) > 0:
            ssh_credential_id = existing_credentials.xpath("//credential/@id")[0]
            print(f"Found existing SSH credentials with ID: {ssh_credential_id}")
        else:
            # Create SSH credentials with root:root
            print("Creating SSH credentials...")
            ssh_response = gmp.create_credential(
                name="Root SSH Credential",
                login="root",
                password="root",
                credential_type="USERNAME_PASSWORD",
                comment="SSH credentials for root access"
            )
            ssh_credential_id = ssh_response.xpath('//@id')[0]
            print(f"SSH credentials created with ID: {ssh_credential_id}")

        # Get the ID of the "All IANA assigned TCP and UDP" port list
        port_lists = gmp.get_port_lists()
        port_list_id = port_lists.xpath("//port_list[name='All IANA assigned TCP']/@id")[0]

        # Check if target already exists
        target_name = f'Target for {",".join(hosts)}'
        print(f"Checking for existing target with name: {target_name}")
        existing_targets = gmp.get_targets(filter_string=f"name='{target_name}'")
        if len(existing_targets.xpath("//target")) > 0:
            target_id = existing_targets.xpath("//target/@id")[0]
            print(f"Found existing target with ID: {target_id}")
        else:
            # Create a target with the given range and SSH credentials
            print(f"Creating target for range {','.join(hosts)}...")
            target_response = gmp.create_target(
                name=target_name,
                hosts=hosts,
                port_list_id=port_list_id,
                ssh_credential_id=ssh_credential_id
            )
            target_id = target_response.xpath('//@id')[0]
            print(f"Target created with ID: {target_id}")

        # Get scan config ID (Full and fast, or custom configuration if needed)
        scan_configs = gmp.get_scan_configs()
        scan_config_id = scan_configs.xpath("//config[name='Full and fast']/@id")[0]

        print("Retrieving Scanner ID for 'CVE' scanner...")
        scanners = gmp.get_scanners(filter_string=f"name=OpenVAS Default")
        scanner_id = None
        for scanner in scanners.xpath("//scanner"):
            scanner_name = scanner.xpath("name/text()")[0]
            if scanner_name == "OpenVAS Default":
                scanner_id = scanner.xpath("@id")[0]
                break

        if scanner_id:
            print(f"Scanner 'CVE' found with ID: {scanner_id}")
        else:
            print("Scanner 'CVE' not found. Exiting.")
            return

        # Check if task already exists
        task_name = f'Vulnerability Scan Task for {",".join(hosts)}'
        print(f"Checking for existing task with name: {task_name}")
        existing_tasks = gmp.get_tasks(filter_string=f"name='{task_name}'")
        if len(existing_tasks.xpath("//task")) > 0:
            task_id = existing_tasks.xpath("//task/@id")[0]
            print(f"Found existing task with ID: {task_id}")
        else:
            # Create a task for the scan
            print(f"Creating scan task for {','.join(hosts)}...")
            task_response = gmp.create_task(
                name=task_name,
                config_id=scan_config_id,
                target_id=target_id,
                scanner_id=scanner_id  # Use the retrieved CVE scanner ID
            )
            task_id = task_response.xpath('//@id')[0]
            print(f"Task created with ID: {task_id}")

        # Start the scan
        print(f"Starting scan for task ID: {task_id}")
        gmp.start_task(task_id)

        # Monitor the status of the scan until it finishes
        print("Scan started. Waiting for completion...")
        status = "Running"
        while status != "Done":
            time.sleep(30)  # Wait for 30 seconds between checks
            status_response = gmp.get_task(task_id=task_id)
            status = status_response.xpath('//task/status/text()')[0]
            print(f"Current scan status: {status}")

        # Retrieve the scan results
        print("Scan finished. Retrieving results...")
        report_id = status_response.xpath('//last_report/report/@id')[0]
        report_response = gmp.get_report(report_id=report_id,
                                         report_format_id='a994b278-1f62-11e1-96ac-406186ea4fc5')  # Default report format
        report = etree.tostring(report_response, pretty_print=True).decode()

        # Print the report
        print("Scan Report:")
        print(report)

if __name__ == "__main__":
    # Define the IP range for the target (default: 172.20.0.0/16)
    host_list = ['172.20.0.2']

    # Call the function to set up OpenVAS, scan, and retrieve the results
    create_task_and_scan(host_list)
