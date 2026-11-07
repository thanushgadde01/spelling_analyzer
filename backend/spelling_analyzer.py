"""
spelling_analyzer.py - Compatibility wrapper

This thin module restores the original module name expected by older
parts of the project. It re-exports the functions implemented in
`spell.py` so `from spelling_analyzer import ...` works unchanged.
"""

from spell import (
    load_dictionary,
    correct_text,
    analyze_spelling,
    determine_level_and_feedback,
    append_entry_to_master,
)

__all__ = [
    "load_dictionary",
    "correct_text",
    "analyze_spelling",
    "determine_level_and_feedback",
    "append_entry_to_master",
]
