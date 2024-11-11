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


@dataclass
class Package:
    interface: str
    source: str
    destination: str
    protocol: str
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
    protocol: Optional[str]
    source: Optional[str]
    destination: Optional[str]
    source_ports: Optional[List[int]]
    destination_ports: Optional[List[int]]
    in_interface: Optional[str]
    out_interface: Optional[str]
    states: Optional[List[State]]