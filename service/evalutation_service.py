import numpy as np


def calculate_box_stats(queryset):
    """Calculate statistics needed for a boxplot"""
    if not queryset.exists():
        return {
            'min': 0,
            'q1': 0,
            'median': 0,
            'q3': 0,
            'max': 0,
            'mean': 0
        }

    scores = list(queryset.values_list('score', flat=True))
    scores = [float(score) for score in scores if score is not None]

    if not scores:
        return {
            'min': 0,
            'q1': 0,
            'median': 0,
            'q3': 0,
            'max': 0,
            'mean': 0
        }

    return {
        'min': float(np.min(scores)),
        'q1': float(np.percentile(scores, 25)),
        'median': float(np.percentile(scores, 50)),
        'q3': float(np.percentile(scores, 75)),
        'max': float(np.max(scores)),
        'mean': float(np.mean(scores))
    }