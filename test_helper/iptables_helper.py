from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class Action(Enum):
    ACCEPT = "ACCEPT"
    DROP = "DROP"
    REJECT = "REJECT"


class Chain(Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    FORWARD = "FORWARD"


class State(Enum):
    NEW = "NEW"
    ESTABLISHED = "ESTABLISHED"
    RELATED = "RELATED"
    INVALID = "INVALID"
    UNTRACKED = "UNTRACKED"


class Expected(Enum):
    DROP = "DROP"
    ACCEPT = "ACCEPT"


@dataclass
class Packet:
    interface: str
    source: str
    destination: str
    protocol: str
    port: int
    state: State
    expected: Expected


@dataclass
class Policy:
    chain: Chain
    action: Action


@dataclass
class Rule:
    chain: Chain
    action: Action
    protocol: Optional[str]
    source: Optional[str]
    destination: Optional[str]
    port: Optional[List[int]]
    in_interface: Optional[str]
    out_interface: Optional[str]
    state: Optional[List[State]]


class IPTablesSimulator:
    def __init__(self):
        self.policies = {
            Chain.INPUT: Policy(chain=Chain.INPUT, action=Action.ACCEPT),
            Chain.OUTPUT: Policy(chain=Chain.OUTPUT, action=Action.ACCEPT),
            Chain.FORWARD: Policy(chain=Chain.FORWARD, action=Action.ACCEPT),
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
                chain = getattr(Chain, parts[0])
                action = getattr(Action, parts[1])
                self.policies[Chain.INPUT] = Policy(chain=chain, action=action)
                continue

            chain = _find_value(parts, ['-A', '--append'])
            action = _find_value(parts, ['-j', '--jump'])
            protocol = _find_value(parts, ['-p', '--protocol'])
            source = _find_value(parts, ['-s', '--source'])
            destination = _find_value(parts, ['-d', '--destination'])
            ports = _find_value(parts, ['-p', '--port'])
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
                chain = getattr(Chain, chain)

            if action:
                action = getattr(Action, action)

            if ports:
                ports = ports.split(',')

            if states:
                states = states.split(',')
                states = [getattr(State, state) for state in states]

            rule = Rule(
                chain=chain,
                action=action,
                protocol=protocol,
                source=source,
                destination=destination,
                port=ports,
                in_interface=in_interface,
                out_interface=out_interface,
                state=states,
            )
            self.rules.append(rule)
        return self.rules







def _find_value(haystack: List[str], needles: List[str]) -> str | None:
    try:
        for needle in needles:
            if needle in haystack:
                index = haystack.index(needle)
                return haystack[index + 1]
    except ValueError:
        return None