#!/usr/bin/env python3
"""
Test script to verify the AI Assistant adversarial handling implementation.
Run: uv run python test_ai_assistant.py
"""

import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_prompts():
    """Test that prompts are correctly defined."""
    print("=" * 60)
    print("Testing Prompts...")
    print("=" * 60)

    from apps.core.prompts import CROSS_EXAMINATION_PROMPT, SYNC_PROMPT_TEMPLATE, ADVERSARIAL_DISCLAIMER_TEMPLATES

    # Check CROSS_EXAMINATION_PROMPT has all required elements
    required_elements = [
        "skeptical legal assistant",
        "Prioritize Verified Sources",
        "Handle Adversarial Sources",
        "Clarify Disputes",
        "Citation Requirements",
        "Response Templates",
        "Examples",
    ]

    all_ok = True
    for element in required_elements:
        if element in CROSS_EXAMINATION_PROMPT:
            print(f"✓ Contains: {element}")
        else:
            print(f"✗ Missing: {element}")
            all_ok = False

    # Check adversarial disclaimer templates
    if 'OPPOSING' in ADVERSARIAL_DISCLAIMER_TEMPLATES:
        print(f"✓ ADVERSARIAL_DISCLAIMER_TEMPLATES has OPPOSING template")
    else:
        print(f"✗ ADVERSARIAL_DISCLAIMER_TEMPLATES missing OPPOSING template")
        all_ok = False

    return all_ok


def test_utils():
    """Test utility functions."""
    print("\n" + "=" * 60)
    print("Testing Utils...")
    print("=" * 60)

    from apps.core.utils import apply_adversarial_labeling, validate_adversarial_disclaimers

    # Test apply_adversarial_labeling
    test_cases = [
        ("The contract was signed", "OPPOSING", "The opposing party alleges: The contract was signed"),
        ("The document states facts", "CLIENT", "The document states facts"),
        ("Court order received", "NEUTRAL", "According to the document: Court order received"),
    ]

    all_ok = True
    for text, source_party, expected_start in test_cases:
        result = apply_adversarial_labeling(text, source_party)
        if result.startswith(expected_start):
            print(f"✓ apply_adversarial_labeling({source_party}): Correct")
        else:
            print(f"✗ apply_adversarial_labeling({source_party}): Got '{result}', expected start with '{expected_start}'")
            all_ok = False

    # Test validate_adversarial_disclaimers
    response_with_disclaimer = "The opposing party alleges that the contract was breached."
    response_without_disclaimer = "The contract was breached."

    if validate_adversarial_disclaimers(response_with_disclaimer, ["OPPOSING"]):
        print(f"✓ validate_adversarial_disclaimers: Correctly detected disclaimer")
    else:
        print(f"✗ validate_adversarial_disclaimers: Failed to detect disclaimer")
        all_ok = False

    if not validate_adversarial_disclaimers(response_without_disclaimer, ["OPPOSING"]):
        print(f"✓ validate_adversarial_disclaimers: Correctly flagged missing disclaimer")
    else:
        print(f"✗ validate_adversarial_disclaimers: Failed to flag missing disclaimer")
        all_ok = False

    return all_ok


def test_django_models():
    """Test that Django models have required fields."""
    print("\n" + "=" * 60)
    print("Testing Django Models...")
    print("=" * 60)

    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

    from apps.core.models import WikiPage, RawDocument

    # Check WikiPage has category field
    wiki_fields = [f.name for f in WikiPage._meta.fields]
    if 'category' in wiki_fields:
        print(f"✓ WikiPage has 'category' field")
    else:
        print(f"✗ WikiPage missing 'category' field")
        return False

    # Check RawDocument has source_party and reliability_note
    raw_doc_fields = [f.name for f in RawDocument._meta.fields]
    for field in ['source_party', 'reliability_note']:
        if field in raw_doc_fields:
            print(f"✓ RawDocument has '{field}' field")
        else:
            print(f"✗ RawDocument missing '{field}' field")
            return False

    return True


def test_ai_response_function():
    """Test the get_ai_response function structure."""
    print("\n" + "=" * 60)
    print("Testing AI Response Function...")
    print("=" * 60)

    # Check if the function exists in views.py
    import ast
    with open('apps/ai_assistant/views.py', 'r') as f:
        tree = ast.parse(f.read())

    function_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'get_ai_response':
            function_found = True
            print(f"✓ get_ai_response function found in views.py")
            break

    if not function_found:
        print(f"✗ get_ai_response function not found in views.py")
        return False

    return True


def main():
    print("\n" + "=" * 60)
    print("AI ASSISTANT ADVERSARIAL HANDLING TEST")
    print("=" * 60)

    results = []

    results.append(("Prompts", test_prompts()))
    results.append(("Utils", test_utils()))
    results.append(("Django Models", test_django_models()))
    results.append(("AI Response Function", test_ai_response_function()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    total_pass = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nTotal: {total_pass}/{total} tests passed")

    return 0 if total_pass == total else 1


if __name__ == "__main__":
    sys.exit(main())
