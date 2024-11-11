import ipaddress
from typing import Optional, List
from .firewall_helper import Chain, Policy, Package, Action, State, Rule


class IPTablesSimulator:
    def __init__(self):
        self.policies = {
            Chain.INPUT.value: Policy(chain=Chain.INPUT, action=Action.ACCEPT),
            Chain.OUTPUT.value: Policy(chain=Chain.OUTPUT, action=Action.ACCEPT),
            Chain.FORWARD.value: Policy(chain=Chain.FORWARD, action=Action.ACCEPT),
        }
        self.rules = []

    def parse_rules(self, content: str) -> List[Rule]:
        saved_format = False
        if len(self.rules) > 0:
            self.rules = []
        for line in content.split('\n'):
            line = line.strip()
            parts = [part.strip() for part in line.split()]
            if not line or line.startswith('#'):
                continue

            if line.startswith('*filter'):
                saved_format = True
                continue

            if not saved_format:
                parts = parts[1:]

            if line.startswith(':'):
                chain = getattr(Chain, parts[0].strip(':').upper())
                action = getattr(Action, parts[1].strip(':').upper())
                self.policies[chain.value] = Policy(chain=chain, action=action)
                continue
            chain_policy = _find_value(parts, ['-P', '--policy'])
            if chain_policy:
                chain = getattr(Chain, chain_policy.upper())
                action = getattr(Action, parts[2].upper())
                self.policies[chain.value] = Policy(chain=chain, action=action)
                continue

            chain = _find_value(parts, ['-A', '--append'])
            action = _find_value(parts, ['-j', '--jump'])
            protocol = _find_value(parts, ['-p', '--protocol'])
            source = _find_value(parts, ['-s', '--source'])
            destination = _find_value(parts, ['-d', '--destination'])
            source_ports = _find_value(parts, ['--source-port', '--sport', '--source-ports', '--sports'])
            destination_ports = _find_value(parts, ['--destination-port', '--dport', '--destination-ports', '--dports'])
            in_interface = _find_value(parts, ['-i', '--interface'])
            out_interface = _find_value(parts, ['-o', '--interface'])
            states = _find_value(parts, ['--ctstate', '--state'])

            if '!' in parts:
                negate_i = parts.index('!')
                if ['-d', '--destination'] in parts[negate_i + 1:]:
                    destination = f"!{parts[negate_i + 2]}"
                elif ['-s', '--source'] in parts[negate_i + 1:]:
                    source = f"!{parts[negate_i + 2]}"

            if chain:
                chain = getattr(Chain, chain.upper())

            if action:
                action = getattr(Action, action.upper())

            if source_ports:
                source_ports = [int(source_port) for source_port in source_ports.split(',')]
            if destination_ports:
                destination_ports = [int(destination_port) for destination_port in destination_ports.split(',')]

            if states:
                states = states.split(',')
                states = [getattr(State, state.upper()) for state in states]

            rule = Rule(
                chain=chain,
                action=action,
                protocol=protocol,
                source=source if source != '0.0.0.0/0' else None,
                destination=destination if destination != '0.0.0.0/0' else None,
                source_ports=source_ports,
                destination_ports=destination_ports,
                in_interface=in_interface,
                out_interface=out_interface,
                states=states,
            )
            self.rules.append(rule)
        return self.rules


    def evaluate_package(self, package: Package) -> bool:
        if package.interface.startswith("lo"):
            chain = Chain.INPUT
        elif package.interface.startswith("eth") or package.interface.startswith("wan0"):
            chain = Chain.FORWARD
        else:
            chain = Chain.OUTPUT

        action = self.policies[chain.value].action
        for rule in self.rules:
            if rule.chain != chain:
                continue

            if rule.in_interface and package.interface != rule.in_interface:
                continue

            if not _check_ip_match(rule.source, package.source):
                continue

            if not _check_ip_match(rule.destination, package.destination):
                continue

            if rule.protocol and package.protocol != rule.protocol:
                continue

            if rule.destination_ports and package.port not in rule.destination_ports:
                continue

            if rule.states and package.state not in rule.states:
                continue

            action = rule.action
            break
        return package.expected == action



def _find_value(haystack: List[str], needles: List[str]) -> str | None:
    try:
        for needle in needles:
            if needle in haystack:
                index = haystack.index(needle)
                return haystack[index + 1]
    except ValueError:
        return None


def _is_valid_ip(ip_str: str) -> bool:
    try:
        ipaddress.ip_address(ip_str.lstrip('!'))
        return True
    except ValueError:
        return False


def _is_valid_network(network_str: str) -> bool:
    try:
        ipaddress.ip_network(network_str.lstrip('!'))
        return True
    except ValueError:
        return False


def _check_ip_match(rule_ip: str, package_ip: str) -> bool:
    if rule_ip and rule_ip.startswith('!'):
        if _is_valid_ip(rule_ip):
            if ipaddress.ip_address(package_ip) == ipaddress.ip_address(rule_ip):
                return False
        elif _is_valid_network(rule_ip):
            if ipaddress.ip_address(package_ip) in ipaddress.ip_network(rule_ip):
                return False
    elif rule_ip:
        if _is_valid_ip(rule_ip):
            if ipaddress.ip_address(package_ip) != ipaddress.ip_address(rule_ip):
                return False
        elif _is_valid_network(rule_ip):
            if ipaddress.ip_address(package_ip) not in ipaddress.ip_network(rule_ip):
                return False
    return True