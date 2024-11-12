import re
from typing import Optional, List, Dict
from .firewall_helper import Chain, Policy, Package, Action, State, Rule, Protocol, check_ip_match


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

            if line.startswith('table'):
                if 'filter' not in line:
                    continue
            elif line.startswith('chain'):
                chain_name = parts[1].upper()
                if chain_name in Chain.__members__:
                    current_chain = getattr(Chain, chain_name)
                continue

            if 'policy' in line:
                policy_index = parts.index('policy')
                action = getattr(Action, parts[policy_index + 1].upper().rstrip(';'))
                self.policies[current_chain.value] = Policy(chain=current_chain, action=action)
                continue

            if not any(keyword in line for keyword in ['accept', 'drop', 'reject']):
                continue
            source = _find_ips(line, 'saddr')
            destination = _find_ips(line, 'daddr')
            in_interface = _find_value(parts, ['iifname', 'iif'])
            out_interface = _find_value(parts, ['oifname', 'oif'])

            source_ports = _find_ports(line, 'sport')
            destination_ports = _find_ports(line, 'dport')

            states = _find_states(line)

            action = None
            for act in Action:
                if act.value in line:
                    action = act
                    break

            protocol = None
            for proto in Protocol:
                if proto.value in line:
                    protocol = proto

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

        return package.expected == action

def _find_value(parts: List[str], keywords: List[str]) -> Optional[str]:
    """Find a value in parts list after any of the keywords."""
    for index, part in enumerate(parts):
        if part in keywords and index + 1 < len(parts):
            return parts[index + 1].strip('"')
    return None


def _find_ips(line: str, option: str) -> Optional[List[str]]:
    if not option in line:
        return None

    parts = [part.strip() for part in line.split()]
    ips = []

    for index, part in enumerate(parts):
        negate = False
        if option not in part:
            continue
        current_part = None
        i = index + 1
        if i < len(parts):
            current_part = parts[i]
        if current_part and current_part == '!=':
            negate = True
            current_part = parts[i := i + 1]
        if current_part and not current_part.startswith('{'):
            ips.append("!" + current_part if negate else current_part)
            continue
        if current_part and current_part.startswith('{'):
            if len(current_part) == 1:
                current_part = parts[i := i + 1]
                while not current_part.endswith('}'):
                    if current_part.endswith(','):
                        ips.append(current_part.rstrip(','))
                    else:
                        ip_list = current_part.split(',')
                        for ip in ip_list:
                            ips.append(ip)
                    current_part = parts[i := i + 1]
            else:
                ip_list = current_part.strip('{}').split(',')
                ips.extend([ip.strip() for ip in ip_list if ip])
    return ips if ips else None



def _find_ports(line: str, port_type: str) -> Optional[List[int]]:
    """Parse ports from a rule line."""
    if port_type not in line:
        return None

    pattern = fr'{port_type}\s*({{\s*[\d\s,\-]+\s*}}|\d+)'
    match = re.search(pattern, line)

    if not match:
        return None

    port_str = match.group(1)

    if '{' in port_str:
        port_str = port_str.strip('{}')
        port_parts = [p.strip() for p in port_str.split(',')]

        ports = []
        for part in port_parts:
            if '-' in part:
                start, end = map(int, part.split('-'))
                ports.extend(range(start, end + 1))
            else:
                ports.append(int(part))
        return sorted(ports)

    return [int(port_str)]


def _find_states(line: str) -> Optional[List[State]]:
    """Parse connection states from a rule line."""
    if 'ct state' not in line:
        return None

    pattern = r'state\s*({[\w\s,\-]+}|\w+)'
    match = re.search(pattern, line)

    if not match:
        return None

    state_str = match.group(1)

    if '{' in state_str:
        state_str = state_str.strip('{}')
        state_parts = [s.strip() for s in state_str.split(',')]
        return [getattr(State, state.upper()) for state in state_parts]

    return [getattr(State, state_str.upper())]
