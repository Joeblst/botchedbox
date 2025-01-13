import ipaddress
import logging
from typing import Optional, List
from .firewall_helper import Chain, Policy, Package, Action, State, Rule, Protocol, check_ip_match

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


class IPTablesSimulator:
    def __init__(self):
        self.policies = {
            Chain.INPUT.value: Policy(chain=Chain.INPUT, action=Action.ACCEPT),
            Chain.OUTPUT.value: Policy(chain=Chain.OUTPUT, action=Action.ACCEPT),
            Chain.FORWARD.value: Policy(chain=Chain.FORWARD, action=Action.ACCEPT),
        }
        self.rules = []

    def parse_rules(self, content: str) -> List[Rule]:
        """ To simulate the firewall we need to parse the rules in a filter """
        saved_format = False
        if len(self.rules) > 0:
            self.rules = []
        for line in content.split('\n'):
            try:
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
                source = _find_ips(line, ['-s', '--source'])
                destination = _find_ips(line, ['-d', '--destination'])
                source_ports = _find_value(parts, ['--source-port', '--sport', '--source-ports', '--sports'])
                destination_ports = _find_value(parts,
                                                ['--destination-port', '--dport', '--destination-ports', '--dports'])
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

                if protocol and protocol != 'all':
                    protocol = getattr(Protocol, protocol.upper())

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
            except Exception as e:
                logging.warning(str(e))
        return self.rules

    def evaluate_package(self, package: Package) -> Action:
        """ Run package through the firewall """
        if package.in_if.startswith("lo"):
            chain = Chain.INPUT
        elif package.in_if.startswith("eth") or package.in_if.startswith("wan0"):
            chain = Chain.FORWARD
        else:
            chain = Chain.OUTPUT

        action = self.policies[chain.value].action
        for rule in self.rules:
            if rule.chain != chain:
                continue

            if rule.in_interface and package.in_if != rule.in_interface:
                continue

            if rule.out_interface and package.out_if != rule.out_interface:
                continue

            if not check_ip_match(rule.source, package.source):
                continue

            if not check_ip_match(rule.destination, package.destination):
                continue

            if rule.protocol and package.protocol != rule.protocol:
                continue

            if rule.destination_ports and package.port not in rule.destination_ports:
                continue

            if rule.states and package.state not in rule.states:
                continue

            action = rule.action
            break
        return action


def _find_value(haystack: List[str], needles: List[str]) -> str | None:
    try:
        for needle in needles:
            if needle in haystack:
                index = haystack.index(needle)
                return haystack[index + 1]
    except ValueError:
        return None


def _find_ips(line: str, options: List[str]) -> Optional[List[str]]:
    """Find a value in parts list after any of the keywords."""
    if not any(opt in line for opt in options):
        return None

    parts = [part.strip() for part in line.split()]
    ips = []

    for index, part in enumerate(parts):
        negated = index > 0 and parts[index - 1] == '!'

        for opt in options:
            if opt == part:
                if index + 1 < len(parts):
                    ip = parts[index + 1]
                    ips.append('!' + ip if negated else ip)

    return ips if ips else None


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
