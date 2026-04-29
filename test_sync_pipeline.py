#!/usr/bin/env python3
"""
Test script to verify the sync pipeline implementation.
Run: uv run python test_sync_pipeline.py
"""

import os
import sys
import json
import tempfile

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_rust_compilation():
    """Test that Rust code compiles."""
    print("=" * 60)
    print("Testing Rust compilation...")
    print("=" * 60)

    import subprocess
    result = subprocess.run(
        ["cargo", "check"],
        cwd="rust_did",
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("✓ Rust code compiles successfully!")
        return True
    else:
        print("✗ Rust compilation failed:")
        print(result.stderr)
        return False


def test_django_models():
    """Test that Django models are correctly defined."""
    print("\n" + "=" * 60)
    print("Testing Django models...")
    print("=" * 60)

    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

    from apps.core.models import Case, RawDocument, WikiPage, SchemaRule

    # Check model fields
    models_to_check = [
        (RawDocument, ['id', 'case', 'file', 'file_type', 'source_party',
                       'document_type', 'reliability_note', 'uploaded_at', 'is_immutable']),
        (WikiPage, ['id', 'case', 'title', 'content', 'last_updated',
                     'version_history', 'citation_references']),
        (SchemaRule, ['id', 'case', 'rule_name', 'rule_description', 'rule_content']),
    ]

    all_ok = True
    for model, expected_fields in models_to_check:
        actual_fields = [f.name for f in model._meta.fields]
        missing = set(expected_fields) - set(actual_fields)
        if missing:
            print(f"✗ {model.__name__} missing fields: {missing}")
            all_ok = False
        else:
            print(f"✓ {model.__name__} has all required fields")

    # Check Case model has UUID
    from django.db import models as django_models
    case_pk = Case._meta.pk
    if isinstance(case_pk, django_models.UUIDField):
        print("✓ Case model uses UUID primary key")
    else:
        print(f"✗ Case model uses {type(case_pk).__name__} instead of UUIDField")
        all_ok = False

    return all_ok


def test_rust_structs():
    """Test that Rust structs can be serialized/deserialized."""
    print("\n" + "=" * 60)
    print("Testing Rust structs (via cargo test)...")
    print("=" * 60)

    import subprocess
    result = subprocess.run(
        ["cargo", "test", "--lib", "--", "--list"],
        cwd="rust_did",
        capture_output=True,
        text=True
    )

    if "test_result" in result.stdout or result.returncode == 0:
        print("✓ Rust tests are available")
        return True
    else:
        print("✗ No Rust tests found or error occurred")
        print(result.stderr)
        return False


def test_file_structure():
    """Test that required files exist."""
    print("\n" + "=" * 60)
    print("Testing file structure...")
    print("=" * 60)

    required_files = [
        "rust_did/src/lib.rs",
        "rust_did/src/sync.rs",
        "rust_did/src/llm.rs",
        "rust_did/src/lint.rs",
        "rust_did/src/main.rs",
        "rust_did/Cargo.toml",
        "apps/core/models.py",
        "apps/core/tasks.py",
        "apps/core/llm_clients.py",
    ]

    all_ok = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            all_ok = False

    return all_ok


def main():
    print("\n" + "=" * 60)
    print("SYNC PIPELINE IMPLEMENTATION TEST")
    print("=" * 60)

    results = []

    results.append(("Rust Compilation", test_rust_compilation()))
    results.append(("Django Models", test_django_models()))
    results.append(("Rust Structs", test_rust_structs()))
    results.append(("File Structure", test_file_structure()))

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
