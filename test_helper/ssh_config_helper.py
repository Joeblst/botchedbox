from dataclasses import dataclass, field
from typing import List


@dataclass
class SSHOption:
    name: str
    value: str


@dataclass
class MatchBlock:
    criteria: str
    criteria_value: str
    options: List[SSHOption] = None

    def __post_init__(self):
        if self.options is None:
            self.options = []


@dataclass
class SSHConfig:
    global_options: List[SSHOption] = field(default_factory=list)
    match_blocks: List[MatchBlock] = field(default_factory=list)


class SSHConfigParser:
    def __init__(self):
        self.config = SSHConfig()

    def parse_string(self, config_string: str) -> SSHConfig:
        lines = [
            line
            for line in config_string.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

        current_match_block = None
        for line in lines:
            stripped_line = line.strip()
            current_indentation = len(line) - len(stripped_line)

            if stripped_line.startswith("Match"):
                match_parts = stripped_line.split(maxsplit=2)
                if len(match_parts) >= 3:
                    current_match_block = MatchBlock(
                        criteria=match_parts[1],
                        criteria_value=match_parts[2]
                    )
                    self.config.match_blocks.append(current_match_block)
            else:
                option_parts = stripped_line.split(maxsplit=1)
                if len(option_parts) >= 2:
                    option = SSHOption(option_parts[0], option_parts[1])
                    if current_indentation > 0 and current_match_block:
                        current_match_block.options.append(option)
                    elif current_indentation == 0:
                        current_match_block = None
                        self.config.global_options.append(option)

        return self.config
