import ipaddress
from typing import Optional, List, Dict
from firewall_helper import Chain, Policy, Package, Action, State, Rule


class NFTablesSimulator:
    def __init__(self):
        self.policies: Dict[str, Policy] = {
            Chain.INPUT.value: Policy(chain=Chain.INPUT, action=Action.ACCEPT),
            Chain.OUTPUT.value: Policy(chain=Chain.OUTPUT, action=Action.ACCEPT),
            Chain.FORWARD.value: Policy(chain=Chain.FORWARD, action=Action.ACCEPT),
        }
        self.rules: List[Rule] = []

    def parse_rules(self, content: str) -> List[Rule]:
        if len(self.rules) > 0:
            self.rules = []

        current_chain = None
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = [part.strip() for part in line.split()]

            # Handle table and chain declaration
            if line.startswith('table'):
                if 'filter' not in line:
                    continue
            elif line.startswith('chain'):
                chain_name = parts[1].upper()
                if chain_name in Chain.__members__:
                    current_chain = getattr(Chain, chain_name)
                    # Check for policy in chain declaration
                    if 'policy' in line:
                        policy_index = parts.index('policy')
                        action = getattr(Action, parts[policy_index + 1].upper())
                        self.policies[current_chain.value] = Policy(chain=current_chain, action=action)
                continue

            if not any(keyword in line for keyword in ['accept', 'drop', 'reject']):
                continue

            # Parse rule components
            protocol = _find_value(parts, ['meta l4proto'])
            source = _find_value(parts, ['ip saddr'])
            destination = _find_value(parts, ['ip daddr'])
            in_interface = _find_value(parts, ['iifname'])
            out_interface = _find_value(parts, ['oifname'])

            # Parse ports
            source_ports = _find_ports(line, 'sport')
            destination_ports = _find_ports(line, 'dport')

            # Parse states
            states = _find_states(line)

            # Determine action
            action = None
            for act in Action:
                if act.value in line:
                    action = act
                    break

            if current_chain and action:
                rule = Rule(
                    chain=current_chain,
                    action=action,
                    protocol=protocol,
                    source=source,
                    destination=destination,
                    source_ports=source_ports,
                    destination_ports=destination_ports,
                    in_interface=in_interface,
                    out_interface=out_interface,
                    states=states
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

def _find_value(parts: List[str], keywords: List[str]) -> Optional[str]:
    """Find a value in parts list after any of the keywords."""
    for i, part in enumerate(parts):
        if part in keywords and i + 1 < len(parts):
            return parts[i + 1]
    return None

def _find_ports(line: str, port_type: str) -> Optional[List[int]]:
    """Parse ports from a rule line."""
    if port_type not in line:
        return None

    parts = line.split()
    for i, part in enumerate(parts):
        if port_type in part and i + 1 < len(parts):
            ports_str = parts[i + 1]
            if '{' in ports_str:  # Handle port ranges/sets
                ports_str = ports_str.strip('{}')
                return [int(p) for p in ports_str.split(',')]
            return [int(ports_str)]
    return None

def _find_states(line: str) -> Optional[List[State]]:
    if 'ct state' not in line:
        return None

    parts = line.split()
    state_idx = parts.index('state')
    if state_idx + 1 < len(parts):
        states_str = parts[state_idx + 1].strip('{}')
        return [getattr(State, state.upper()) for state in states_str.split(',')]
    return None

def _check_ip_match(rule_ip: Optional[str], package_ip: str) -> bool:
    if not rule_ip:
        return True

    negated = rule_ip.startswith('!')
    ip_str = rule_ip.lstrip('!')

    try:
        if '/' in ip_str:  # Network
            network = ipaddress.ip_network(ip_str)
            package_addr = ipaddress.ip_address(package_ip)
            match = package_addr in network
        else:  # Single IP
            rule_addr = ipaddress.ip_address(ip_str)
            package_addr = ipaddress.ip_address(package_ip)
            match = rule_addr == package_addr

        return not match if negated else match
    except ValueError:
        return False