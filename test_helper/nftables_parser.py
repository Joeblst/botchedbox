from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from ipaddress import ip_network
from enum import Enum


class NFTHook(Enum):
    PREROUTING = "prerouting"
    INPUT = "input"
    FORWARD = "forward"
    OUTPUT = "output"
    POSTROUTING = "postrouting"


@dataclass
class NFTRule:
    family: str  # ip, ip6, inet, arp, bridge, netdev
    table: str
    chain: str
    position: Optional[int] = None
    handle: Optional[int] = None

    # Rule matching criteria
    source: Optional[str] = None
    destination: Optional[str] = None
    protocol: Optional[str] = None
    source_port: Optional[str] = None
    dest_port: Optional[List[str]] = None
    in_interface: Optional[str] = None
    out_interface: Optional[str] = None

    # Action
    verdict: Optional[str] = None  # accept, drop, reject, queue, continue, return, jump, goto

    # Additional features
    ct_state: Optional[List[str]] = None
    counter: bool = False
    comment: Optional[str] = None
    extras: Dict[str, Any] = None

    def __post_init__(self):
        if self.extras is None:
            self.extras = {}


@dataclass
class NFTChain:
    family: str
    table: str
    name: str
    type: Optional[str] = None  # filter, route, nat
    hook: Optional[NFTHook] = None
    priority: Optional[int] = None
    policy: Optional[str] = None  # accept, drop


class NFTablesParser:
    def __init__(self):
        self.rules = []
        self.chains = []
        self.current_family = None
        self.current_table = None

    def _parse_address(self, addr_str: str) -> str:
        """Parse and validate IP address/network."""
        try:
            return str(ip_network(addr_str, strict=False))
        except ValueError:
            return addr_str

    def parse_chain_declaration(self, line: str) -> Optional[NFTChain]:
        """Parse a chain declaration line."""
        parts = line.strip().split()
        if not (parts and parts[0] == "chain"):
            return None

        # Example: chain input { type filter hook input priority 0; policy accept; }
        try:
            chain_name = parts[1]
            chain = NFTChain(
                family=self.current_family,
                table=self.current_table,
                name=chain_name
            )

            # Parse chain properties
            if "{" in line:
                props = line[line.index("{"):].strip("{}").strip()
                for prop in props.split(";"):
                    prop = prop.strip()
                    if not prop:
                        continue

                    prop_parts = prop.split()
                    if prop_parts[0] == "type":
                        chain.type = prop_parts[1]
                    elif prop_parts[0] == "hook":
                        chain.hook = NFTHook(prop_parts[1].lower())
                    elif prop_parts[0] == "priority":
                        chain.priority = int(prop_parts[1])
                    elif prop_parts[0] == "policy":
                        chain.policy = prop_parts[1]

            return chain
        except (IndexError, ValueError) as e:
            raise ValueError(f"Invalid chain declaration: {line}") from e

    def parse_rule(self, rule_str: str) -> Optional[NFTRule]:
        """Parse a single nftables rule string into an NFTRule object."""
        if rule_str.startswith('#') or not rule_str.strip():
            return None

        parts = rule_str.strip().split()

        # Handle add rule syntax
        if parts[0] != "add" or parts[1] != "rule":
            return None

        try:
            # Basic rule structure: add rule [family] [table] [chain] [matches...] [verdict]
            rule = NFTRule(
                family=parts[2] if not self.current_family else self.current_family,
                table=parts[3] if not self.current_table else self.current_table,
                chain=parts[4]
            )

            i = 5  # Skip to the rule contents
            while i < len(parts):
                if parts[i] == "ip":
                    if parts[i + 1] == "saddr":
                        rule.source = self._parse_address(parts[i + 2])
                        i += 3
                    elif parts[i + 1] == "daddr":
                        rule.destination = self._parse_address(parts[i + 2])
                        i += 3
                elif parts[i] == "tcp" or parts[i] == "udp":
                    rule.protocol = parts[i]
                    if i + 2 < len(parts):
                        if parts[i + 1] == "sport":
                            rule.source_port = parts[i + 2]
                            i += 3
                        elif parts[i + 1] == "dport":
                            rule.dest_port = [parts[i + 2]]
                            i += 3
                elif parts[i] == "iifname":
                    rule.in_interface = parts[i + 1]
                    i += 2
                elif parts[i] == "oifname":
                    rule.out_interface = parts[i + 1]
                    i += 2
                elif parts[i] == "ct":
                    if parts[i + 1] == "state":
                        rule.ct_state = parts[i + 2].split(",")
                        i += 3
                elif parts[i] == "counter":
                    rule.counter = True
                    i += 1
                elif parts[i] == "comment":
                    rule.comment = parts[i + 1].strip('"')
                    i += 2
                elif parts[i] in ["accept", "drop", "reject", "queue", "continue", "return", "jump", "goto"]:
                    rule.verdict = parts[i]
                    i += 1
                else:
                    i += 1

            return rule
        except IndexError as e:
            raise ValueError(f"Invalid nftables rule: {rule_str}") from e

    def parse_ruleset(self, ruleset_str: str) -> List[NFTRule]:
        """Parse a complete nftables ruleset."""
        rules = []
        chains = []

        for line in ruleset_str.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()

            # Handle table declarations
            if parts[0] == "table" and len(parts) >= 3:
                self.current_family = parts[1]
                self.current_table = parts[2]
                continue

            # Handle chain declarations
            if parts[0] == "chain":
                chain = self.parse_chain_declaration(line)
                if chain:
                    chains.append(chain)
                continue

            # Handle rules
            if parts[0] == "add" and parts[1] == "rule":
                rule = self.parse_rule(line)
                if rule:
                    rules.append(rule)

        self.rules = rules
        self.chains = chains
        return rules

    def analyze_ruleset(self) -> Dict:
        """Analyze the parsed rules and chains to extract useful information."""
        analysis = {
            'families': set(),
            'tables': set(),
            'chains': {},  # family -> table -> chain_names
            'protocols': set(),
            'ports': set(),
            'networks': {
                'source': set(),
                'destination': set()
            },
            'interfaces': {
                'in': set(),
                'out': set()
            },
            'verdicts': set()
        }

        # Analyze chains
        for chain in self.chains:
            if chain.family not in analysis['chains']:
                analysis['chains'][chain.family] = {}
            if chain.table not in analysis['chains'][chain.family]:
                analysis['chains'][chain.family][chain.table] = set()
            analysis['chains'][chain.family][chain.table].add(chain.name)
            analysis['families'].add(chain.family)
            analysis['tables'].add(chain.table)

        # Analyze rules
        for rule in self.rules:
            analysis['families'].add(rule.family)
            analysis['tables'].add(rule.table)

            if rule.protocol:
                analysis['protocols'].add(rule.protocol)

            if rule.dest_port:
                analysis['ports'].update(rule.dest_port)

            if rule.source:
                analysis['networks']['source'].add(rule.source)
            if rule.destination:
                analysis['networks']['destination'].add(rule.destination)

            if rule.in_interface:
                analysis['interfaces']['in'].add(rule.in_interface)
            if rule.out_interface:
                analysis['interfaces']['out'].add(rule.out_interface)

            if rule.verdict:
                analysis['verdicts'].add(rule.verdict)

        return analysis