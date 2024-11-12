import ipaddress
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class Action(Enum):
    ACCEPT = "accept"
    DROP = "drop"
    REJECT = "reject"


class Chain(Enum):
    INPUT = "input"
    OUTPUT = "output"
    FORWARD = "forward"


class State(Enum):
    NEW = "new"
    ESTABLISHED = "established"
    RELATED = "related"
    INVALID = "invalid"
    UNTRACKED = "untracked"
    DST = "dst"


class Protocol(Enum):
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"


@dataclass
class Package:
    interface: str
    source: str
    destination: str
    protocol: Protocol
    port: int
    state: State
    expected: Action

    def __str__(self) -> str:
        return (f"Package({self.interface}, {self.source} -> {self.destination}, "
                f"{self.protocol}:{self.port}, state={self.state}, expected={self.expected})")


@dataclass
class Policy:
    chain: Chain
    action: Action


@dataclass
class Rule:
    chain: Chain
    action: Action
    protocol: Optional[Protocol]
    source: Optional[List[str]]
    destination: Optional[List[str]]
    source_ports: Optional[List[int]]
    destination_ports: Optional[List[int]]
    in_interface: Optional[str]
    out_interface: Optional[str]
    states: Optional[List[State]]


def check_ip_match(rule_ips: Optional[List[str]], package_ip: str) -> bool:
    if not rule_ips:
        return True


    for rule_ip in rule_ips:
        negated = rule_ip.startswith('!')
        ip_str = rule_ip.lstrip('!')

        try:
            if '/' in ip_str:
                network = ipaddress.ip_network(ip_str)
                package_addr = ipaddress.ip_address(package_ip)
                match = package_addr in network
            else:
                rule_addr = ipaddress.ip_address(ip_str)
                package_addr = ipaddress.ip_address(package_ip)
                match = rule_addr == package_addr

            if negated:
                match = not match

            if match:
                return True
        except ValueError:
            continue
    return False