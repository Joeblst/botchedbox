import time

from gvm.protocols.gmp import GMPv224, GMPv225


class OpenvasService:
    def __init__(
            self,
            gmp: GMPv224 | GMPv225,
            target_name: str,
            target_ips: [],
            username: str = "admin",
            password: str = "admin",
            ssh_username: str = "root",
            ssh_password: str = "root",
            port_list_name: str = "All IANA assigned TCP",
            scanner_name: str = "OpenVAS Default",
            scan_config_name: str = "Full and fast"
    ):
        self._gmp = gmp
        self._username = username
        self._password = password
        self._ssh_credentials_id = None
        self._port_list_id = None
        self._target_id = None
        self._scan_config_id = None
        self._scanner_id = None
        self.target_name = target_name

        self._connect()
        self._ssh_credentials_id = self._get_or_create_ssh_credentials(
            name=ssh_username,
            username=ssh_username,
            password=ssh_password
        )
        self._port_list_id = self._get_port_list_id(port_list_name)
        self._target_id = self._get_or_create_target(target_ips)
        self._scan_config_id = self._get_scan_config(scan_config_name)
        self._scanner_id = self._get_scanner(scanner_name)

    def _connect(self):
        """Establish connection to the OpenVAS server."""
        self._gmp.authenticate(username=self._username, password=self._password)

    def _get_ssh_credentials_id(self, name: str):
        """Check or create SSH credentials."""
        existing_credentials = self._gmp.get_credentials(filter_string=f"name={name}")
        credentials = existing_credentials.xpath("//credential")
        if credentials:
            return credentials[0].get("id")
        return None

    def _get_or_create_ssh_credentials(self, name: str, username: str, password: str):
        """Retrieve or create SSH credentials."""
        credentials_id = self._get_ssh_credentials_id(name)
        if credentials_id:
            return credentials_id
        print(f"Creating SSH credentials for {name}...")
        ssh_response = self._gmp.create_credential(
            name=name,
            login=username,
            password=password,
            credential_type="USERNAME_PASSWORD",
            comment=f"SSH credentials for {username} access"
        )
        return ssh_response.xpath('//@id')[0]

    def _get_port_list_id(self, name: str):
        """Retrieve the port list ID by name."""
        port_lists = self._gmp.get_port_lists(filter_string=f"name={name}")
        return port_lists.xpath(f"//port_list[name='{name}']/@id")[0]

    def _get_target(self, hosts: []):
        """Get existing target by host."""
        target_name = f'Target_{"_".join(hosts)}'
        targets = self._gmp.get_targets(filter_string=f"name={target_name}")
        return targets.xpath("//target/@id")[0] if targets.xpath("//target") else None

    def _get_or_create_target(self, hosts: []):
        """Retrieve or create a target for the host."""
        target_id = self._get_target(hosts)
        if target_id:
            return target_id
        print(f"Creating target for {hosts}...")
        target_name = f'Target_{"_".join(hosts)}'
        target_response = self._gmp.create_target(
            name=target_name,
            hosts=hosts,
            port_list_id=self._port_list_id,
            ssh_credential_id=self._ssh_credentials_id
        )
        return target_response.xpath('//@id')[0]

    def _get_scan_config(self, name: str):
        """Retrieve scan configuration by name."""
        scan_configs = self._gmp.get_scan_configs()
        return scan_configs.xpath(f"//config[name='{name}']/@id")[0]

    def _get_scanner(self, name: str):
        """Retrieve scanner by name."""
        scanners = self._gmp.get_scanners(filter_string=f"name={name}")
        for scanner in scanners.xpath("//scanner"):
            if scanner.xpath("name/text()")[0] == name:
                return scanner.get("id")
        raise ValueError(f"Scanner with name {name} not found.")

    def create_task(self):
        """Get or create a scan task."""
        task_name = f'Scan_{self.target_name}'
        tasks = self._gmp.get_tasks(filter_string=f"name={task_name}")
        if tasks.xpath("//task"):
            return tasks.xpath("//task/@id")[0]
        print(f"Creating scan task for {self.target_name}...")
        task_response = self._gmp.create_task(
            name=task_name,
            config_id=self._scan_config_id,
            target_id=self._target_id,
            scanner_id=self._scanner_id,
        )
        return task_response.xpath('//@id')[0]

    def start_scan(self, task_id: str):
        """Start the scan and monitor its status."""
        print(f"Starting scan for task ID: {task_id}")
        self._gmp.start_task(task_id)

    def retrieve_latest_report_id(self, task_id: str):
        status = "Running"
        status_response = None
        while status != "Done":
            status_response = self._gmp.get_task(task_id=task_id)
            status = status_response.xpath('//task/status/text()')[0]
            print(f"Scan status: {status}")
            if status != "Done":
                time.sleep(30)

        report_id = status_response.xpath('//last_report/report/@id')[0]
        return report_id


    def retrieve_report(self, report_id: str):
        """Retrieve and return the scan report."""
        report_response = self._gmp.get_report(
            report_id=report_id,
            report_format_id='a994b278-1f62-11e1-96ac-406186ea4fc5'
        )
        return report_response

    def get_cve_description(self, cve_id: str):
        cve_description = self._gmp.get_cve(cve_id=cve_id)
        return cve_description.xpath("//description//text()")[0]
