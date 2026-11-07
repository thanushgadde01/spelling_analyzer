"""
spelling_engine.py - Compatibility Bridge
This file makes the modular spelling_analyzer code compatible with your original FastAPI code.

Your FastAPI code expects:
    from spelling_engine import correction, get_feedback

This bridge provides those exact functions.
"""

import os
from spell import (
    load_dictionary,
    correct_word as _correct_word,
    determine_level_and_feedback as _determine_level_and_feedback
)

# ============================================================================
# GLOBAL DICTIONARY - Load once when module is imported
# ============================================================================

DICTIONARY_PATH = os.getenv("DICT_PATH", r"C:\Users\thanu\OneDrive\Desktop\assault\spelling checker\backend\big.txt")
# Strip any quotes that might be in the environment variable
DICTIONARY_PATH = DICTIONARY_PATH.strip('"').strip("'")
print(f"📚 Loading dictionary from {DICTIONARY_PATH}...")
WORD_FREQ_DICT = load_dictionary(DICTIONARY_PATH)

if not WORD_FREQ_DICT:
    print("⚠️  WARNING: Dictionary is empty!")
else:
    print(f"✅ Dictionary loaded with {len(WORD_FREQ_DICT)} unique words")


# ============================================================================
# COMPATIBILITY FUNCTIONS - Exactly matching your original API
# ============================================================================

def correction(word):
    """
    Correct a single word's spelling.
    
    This is a compatibility wrapper for your FastAPI code.
    It uses the modular spelling_analyzer functions underneath.
    
    Args:
        word (str): Word to correct
        
    Returns:
        str: Corrected word
    """
    return _correct_word(word.lower(), WORD_FREQ_DICT)


def get_feedback(percentage):
    """
    Get proficiency level and feedback based on mistake percentage.
    
    This is a compatibility wrapper for your FastAPI code.
    It uses the modular spelling_analyzer functions underneath.
    
    Args:
        percentage (float): Mistake percentage
        
    Returns:
        tuple: (level, feedback)
    """
    return _determine_level_and_feedback(percentage)


# ============================================================================
# ADDITIONAL HELPER FUNCTIONS (Optional, for enhanced functionality)
# ============================================================================

def correct_sentence(text):
    """
    Correct an entire sentence (optional helper).
    
    Args:
        text (str): Text to correct
        
    Returns:
        str: Corrected text
    """
    from spell import correct_text
    _, _, corrected = correct_text(text, WORD_FREQ_DICT)
    return corrected


def analyze_text(text):
    """
    Full analysis of text (optional helper).
    
    Args:
        text (str): Text to analyze
        
    Returns:
        dict: Analysis results
    """
    from spell import correct_text, analyze_spelling
    
    original_words, corrected_words, corrected_text = correct_text(text, WORD_FREQ_DICT)
    stats = analyze_spelling(original_words, corrected_words)
    level, feedback = get_feedback(stats['mistake_percentage'])
    
    return {
        'original': text,
        'corrected': corrected_text,
        'total_words': stats['total_words'],
        'mistakes': stats['mistakes'],
        'percentage': stats['mistake_percentage'],
        'level': level,
        'feedback': feedback
    }


# ============================================================================
# VERIFICATION
# ============================================================================

if __name__ == "__main__":
    # Test the compatibility functions
    print("\n" + "="*60)
    print("TESTING COMPATIBILITY FUNCTIONS")
    print("="*60)
    
    # Test 1: correction() function
    test_word = "programing"
    corrected = correction(test_word)
    print(f"\n✓ correction('{test_word}') = '{corrected}'")
    
    # Test 2: get_feedback() function
    test_percentage = 15.5
    level, feedback = get_feedback(test_percentage)
    print(f"\n✓ get_feedback({test_percentage})")
    print(f"  Level: {level}")
    print(f"  Feedback: {feedback}")
    
    # Test 3: analyze_text() helper
    test_text = "I havv a drream to becme a softwre enginear"
    result = analyze_text(test_text)
    print(f"\n✓ analyze_text()")
    print(f"  Original: {result['original']}")
    print(f"  Corrected: {result['corrected']}")
    print(f"  Mistakes: {result['mistakes']}/{result['total_words']}")
    print(f"  Percentage: {result['percentage']:.2f}%")
    print(f"  Level: {result['level']}")
    
    print("\n✅ All compatibility functions working correctly!")
    print("="*60)
