#!/usr/bin/env python3
"""
Test script to verify the AI Assistant adversarial handling implementation.
Run: uv run python test_ai_assitant.py
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

    return all_ok


def main():
    print("\n" + "=" * 60)
    print("AI ASSISTANT ADVERSARIAL HANDLING TEST")
    print("=" * 60)

    results = []

    results.append(("Prompts", test_prompts()))
    results.append(("Utils", test_utils()))

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
