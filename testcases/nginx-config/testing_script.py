import logging
import tempfile
from typing import List, Dict, Optional, Any

import crossplane

from io import StringIO
from benchmark.models import Testcase, Response
from test_helper.ssh_config_helper import SSHConfigParser, MatchBlock

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
test_count = 0


def verify(testcase: Testcase, response: Response) -> int:
    global test_count
    score = 0
    issues = []

    with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp_file:
        temp_file.write(response.response_file)
        temp_file_path = temp_file.name

    config = crossplane.parse(temp_file_path)
    errors = config.errors
    config = config.get('config', [])[0].get('parsed', [])

    return 0


def traverse_config(config: List[Dict[Any, Any]], parent_context: Optional[Dict] = None) -> Dict[str, Any]:
    if parent_context is None:
        parent_context = {}

    current_context = parent_context.copy()

    for directive in config:
        directive_name = directive['directive']
        args = directive.get('args', [])

        # Handle special inheritance cases
        if directive_name in ['location', 'server']:
            # Create new context for these blocks with inherited values
            block_context = current_context.copy()

            if 'block' in directive:
                # Recursively process the block with the current context
                block_result = traverse_config(directive['block'], block_context)

                # Store block result in current context
                current_context[f"{directive_name}_{directive.get('line', '')}"] = {
                    'type': directive_name,
                    'args': args,
                    'directives': block_result,
                    'line': directive.get('line', '')
                }
        else:
            # Handle normal directives
            if directive_name in ['root', 'access_log', 'error_log']:
                # These directives are inherited by child blocks
                current_context[directive_name] = {
                    'value': args,
                    'line': directive.get('line', ''),
                    'inherited': True
                }
            else:
                # Non-inheritable directives
                current_context[directive_name] = {
                    'value': args,
                    'line': directive.get('line', ''),
                    'inherited': False
                }

            # Handle includes
            if directive_name == 'include' and 'includes' in directive:
                includes_result = traverse_config(directive['includes'], current_context)
                current_context['includes'] = includes_result

    return current_context
