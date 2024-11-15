import logging
from typing import List

import math

from benchmark.models import Testcase, Response
from test_helper.nftables_helper import NFTablesSimulator
from test_helper.firewall_helper import Package, State, Action, Protocol


def verify(testcase: Testcase, response: Response) -> int:
    """Run all verification checks and return a score."""
    issues = []
    simulator = NFTablesSimulator()
    simulator.parse_rules(response.response_file)
    packages = create_packages()
    score = 0
    for package in packages:
        try:
            if simulator.evaluate_package(package):
                score += 1
            else:
                issues.append("- " + package.__str__() + f" expected {package.expected.value}")
        except Exception as e:
            issues.append("- " + str(e))
    if issues:
        response.check_result = "### Firewall Issues Found\n\n" + "\n".join(issues)
    response.set_valid(True)
    score = (score / len(packages)) * 100
    return math.floor(score)


def create_packages() -> List[Package]:
    return [
        # Default Deny Check
        Package(
            interface='wan0',
            source='8.8.8.8',
            destination='10.0.0.2',
            protocol=Protocol.TCP,
            port=443,
            state=State.NEW,
            expected=Action.DROP,
        ),
        # Internal to DMZ check
        Package(
            interface='eth1',
            source='10.0.0.2',
            destination='172.16.20.20',
            protocol=Protocol.TCP,
            port=25,
            state=State.NEW,
            expected=Action.ACCEPT,
        ),
        Package(
            interface='eth1',
            source='10.0.0.2',
            destination='172.16.20.30',
            protocol=Protocol.UDP,
            port=53,
            state=State.NEW,
            expected=Action.ACCEPT,
        ),
        Package(
            interface='eth0',
            source='172.16.20.20',
            destination='10.0.0.2',
            protocol=Protocol.TCP,
            port=12345,
            state=State.NEW,
            expected=Action.DROP,
        ),
        Package(
            interface='eth0',
            source='172.16.20.20',
            destination='10.0.0.2',
            protocol=Protocol.TCP,
            port=12345,
            state=State.ESTABLISHED,
            expected=Action.ACCEPT,
        ),
        # Management check
        Package(
            interface='eth1',
            source='10.0.0.2',
            destination='172.16.20.30',
            protocol=Protocol.TCP,
            port=22,
            state=State.NEW,
            expected=Action.DROP,
        ),
        Package(
            interface='eth1',
            source='10.1.0.80',
            destination='172.16.20.30',
            protocol=Protocol.TCP,
            port=22,
            state=State.NEW,
            expected=Action.ACCEPT,
        ),
        Package(
            interface='wan0',
            source='8.8.8.8',
            destination='172.16.20.30',
            protocol=Protocol.TCP,
            port=22,
            state=State.NEW,
            expected=Action.DROP,
        ),
        # Application Proxy check
        Package(
            interface='eth1',
            source='10.0.0.2',
            destination='8.8.8.8',
            protocol=Protocol.TCP,
            port=443,
            state=State.NEW,
            expected=Action.DROP,
        ),
        Package(
            interface='eth0',
            source='172.16.20.50',
            destination='8.8.8.8',
            protocol=Protocol.TCP,
            port=443,
            state=State.NEW,
            expected=Action.ACCEPT,
        ),
        Package(
            interface='eth1',
            source='10.0.0.2',
            destination='172.16.20.50',
            protocol=Protocol.TCP,
            port=443,
            state=State.NEW,
            expected=Action.ACCEPT,
        ),
        Package(
            interface='eth1',
            source='10.0.0.2',
            destination='172.16.20.50',
            protocol=Protocol.TCP,
            port=443,
            state=State.ESTABLISHED,
            expected=Action.ACCEPT,
        ),
        Package(
            interface='eth0',
            source='172.16.20.50',
            destination='10.0.0.2',
            protocol=Protocol.TCP,
            port=12345,
            state=State.NEW,
            expected=Action.DROP,
        ),
        # DMZ check
        Package(
            interface='eth0',
            source='172.16.20.10',
            destination='8.8.8.8',
            protocol=Protocol.TCP,
            port=443,
            state=State.NEW,
            expected=Action.ACCEPT,
        ),
        Package(
            interface='eth0',
            source='172.16.20.11',
            destination='8.8.8.8',
            protocol=Protocol.TCP,
            port=443,
            state=State.NEW,
            expected=Action.ACCEPT,
        ),
        Package(
            interface='eth0',
            source='172.16.20.20',
            destination='8.8.8.8',
            protocol=Protocol.TCP,
            port=25,
            state=State.NEW,
            expected=Action.ACCEPT,
        ),
        Package(
            interface='wan0',
            source='8.8.8.8',
            destination='172.16.20.20',
            protocol=Protocol.TCP,
            port=25,
            state=State.NEW,
            expected=Action.ACCEPT,
        ),
        Package(
            interface='wan0',
            source='8.8.8.8',
            destination='172.16.20.20',
            protocol=Protocol.TCP,
            port=443,
            state=State.NEW,
            expected=Action.DROP,
        ),
        Package(
            interface='wan0',
            source='8.8.8.8',
            destination='172.16.20.30',
            protocol=Protocol.TCP,
            port=53,
            state=State.NEW,
            expected=Action.ACCEPT,
        ),
        Package(
            interface='wan0',
            source='8.8.8.8',
            destination='172.16.20.30',
            protocol=Protocol.TCP,
            port=443,
            state=State.NEW,
            expected=Action.DROP,
        ),
        Package(
            interface='eth0',
            source='172.16.20.30',
            destination='8.8.8.8',
            protocol=Protocol.UDP,
            port=53,
            state=State.NEW,
            expected=Action.ACCEPT,
        ),
        # Webserver Check
        Package(
            interface='eth0',
            source='172.16.20.100',
            destination='172.16.20.10',
            protocol=Protocol.TCP,
            port=443,
            state=State.NEW,
            expected=Action.ACCEPT,
        ),
        Package(
            interface='eth0',
            source='172.16.20.100',
            destination='172.16.20.11',
            protocol=Protocol.TCP,
            port=8080,
            state=State.NEW,
            expected=Action.DROP,
        ),
        Package(
            interface='wan0',
            source='8.8.8.8',
            destination='172.16.20.11',
            protocol=Protocol.TCP,
            port=80,
            state=State.NEW,
            expected=Action.DROP,
        ),
        Package(
            interface='wan0',
            source='8.8.8.8',
            destination='172.16.20.100',
            protocol=Protocol.TCP,
            port=80,
            state=State.NEW,
            expected=Action.ACCEPT,
        ),
    ]
