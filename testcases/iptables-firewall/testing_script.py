import logging

from benchmark.models import Testcase, Response
from test_helper.iptables_helper import IPTablesParser

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
test_counts = 0

def verify(testcase: Testcase, response: Response) -> int:
    """Run all verification checks and return a score."""
    global test_counts
    score = 0

    parser = IPTablesParser()
    config = parser.parse_config(response.response_file)
    config = parser.analyze_config(config)
    return 0