import json
import sys

"""
Self-explanatory, a place to stick utilities
"""


def print_stderr(*args, **kwargs):
    print(file=sys.stderr, *args, **kwargs)


def pretty_print_stderr(obj):
    print(json.dumps(obj, indent=2, sort_keys=True), file=sys.stderr)
