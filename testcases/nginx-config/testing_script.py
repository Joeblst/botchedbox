import logging
import tempfile

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

    return 0