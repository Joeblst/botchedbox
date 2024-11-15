# templatetags/test_filters.py
from django import template

register = template.Library()


@register.filter
def filter_validated(tests):
    """Filter tests that have valid responses"""
    return [test for test in tests if test.responses.last() and test.responses.last().valid]


@register.filter
def filter_pending_validation(tests):
    """Filter tests that are waiting for validation"""
    return [test for test in tests if test.state == 'WAITING FOR VALIDATION']


@register.filter
def filter_running(tests):
    """Filter tests that are currently running"""
    return [test for test in tests if test.state == 'RUNNING']


@register.filter
def avg_score(tests):
    """Calculate average score of tests"""
    valid_scores = [test.score for test in tests if test.score is not None]
    if not valid_scores:
        return 0
    return sum(valid_scores) / len(valid_scores)
