import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Union

from pathlib import Path


@dataclass
class Directive:
    name: str
    arguments: List[str]
    children: List['Directive']
    parent: Optional['Directive'] = None


class ApacheConfigParser:
    def __init__(self):
        self.root = Directive("root", [], [])

    def parse_string(self, content: str) -> Directive:
        self.root = Directive("root", [], [])

        lines = [
            line.strip()
            for line in content.split('\n')
            if line.strip() and not line.strip().startswith('#')
        ]
        directive_stack = []
        for line in lines:
            if line.startswith('<') and not line.startswith('</'):
                section_match = re.match(r'<(\w+)\s*(.*)>', line)
                if section_match:
                    name = section_match.group(1)
                    args = section_match.group(2).split()
