import re

from typing import List, Dict
from dataclasses import dataclass

@dataclass
class SambaShare:
    name: str
    options: Dict[str, str]


@dataclass
class SambaConfig:
    global_options: Dict[str, str]
    shares: List[SambaShare]

    def get_option_value(self, option: str, share: SambaShare, default: str = '') -> str:
        """Get option value, checking share options first then global options."""
        return share.options.get(option, self.global_options.get(option, default)).lower()


class SambaConfigParser:
    def parse_string(self, config_text: str) -> SambaConfig:
        lines = config_text.split('\n')
        current_section = None
        global_options = {}
        shares = []
        current_options = {}

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            section_match = re.match(r'\[(.*?)\]', line)
            if section_match:
                if current_section and current_section != 'global':
                    shares.append(SambaShare(current_section, current_options))
                elif current_section == 'global':
                    global_options = current_options
                current_section = section_match.group(1)
                current_options = {}
            else:
                if '=' in line:
                    key, value = [x.strip() for x in line.split('=', 1)]
                    current_options[key.lower()] = value.lower()

        if current_section and current_section != 'global':
            shares.append(SambaShare(current_section, current_options))

        return SambaConfig(global_options, shares)