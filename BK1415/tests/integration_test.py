"""Integration test for the complete validation pipeline.

Tests the full workflow: File loading → Rule execution → Error detection → CLI output
Validates that all components work together correctly.
"""

from pathlib import Path
from io import StringIO
import tempfile

# Import all the components we need to test
from workflow_validator.registry.rule_registry import ValidationRuleRegistry
from workflow_validator.rules.field_placement import InvalidFieldPlacementRule
from workflow_validator.rules.sendemail_rules import SendEmailValidationRule
from workflow_validator.rules.action_structure import ActionStructureRule
from workflow_validator.rules.required_fields import RequiredFieldsRule
from workflow_validator.core.parallel_validator import ParallelValidator
from workflow_validator.cli.rich_reporter import RichReporter
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity
import yaml


def test_full_validation_pipeline():
    """Test complete pipeline from file input to formatted output."""
    print("🧪 Testing Full Validation Pipeline...")

    # Create test workflow with multiple issues
    problematic_workflow = """name: Integration Test Workflow
trigger:
  type: "Manual"
actions:
  BadSendEmail:
    id: "test-id-1"
    class: "SendEmail"
    _fields: []  # WRONG LOCATION - should be inside properties
    properties:
      to: []  # EMPTY RECIPIENTS
      subject: "Test"
      # Missing 'msg' field

  GoodAction:
    id: "test-id-2"
    class: "Custom.Action"
    properties:
      _fields: []  # CORRECT LOCATION
      some_prop: "value"
"""

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(problematic_workflow)
        test_file = Path(f.name)

    try:
        # Step 1: Set up validation registry with all Priority 1 rules
        registry = ValidationRuleRegistry()
        registry.register(InvalidFieldPlacementRule())
        registry.register(SendEmailValidationRule())
        registry.register(ActionStructureRule())
        registry.register(RequiredFieldsRule())

        print(f"✅ Registry setup: {len(registry.get_enabled_rules())} rules registered")

        # Step 2: Load and parse the workflow
        with open(test_file, 'r') as f:
            workflow_content = f.read()
            workflow = yaml.safe_load(workflow_content)

        context = ValidationContext(
            file_path=str(test_file),
            raw_content=workflow_content
        )

        print("✅ Workflow loaded and parsed")

        # Step 3: Run all validation rules
        all_errors = []
        for rule in registry.get_enabled_rules():
            rule_errors = rule.validate(workflow, context)
            all_errors.extend(rule_errors)
            print(f"   {rule.name}: {len(rule_errors)} errors")

        print(f"✅ Validation complete: {len(all_errors)} total errors found")

        # Step 4: Test error detection - should find multiple issues
        expected_error_codes = {
            "INVALID_FIELD_PLACEMENT",   # _fields at wrong location
            "EMPTY_EMAIL_RECIPIENTS",    # Empty 'to' array
            "MISSING_SENDEMAIL_FIELD"    # Missing 'msg' field (INFO)
        }

        found_error_codes = {error.code for error in all_errors}

        print(f"   Expected errors: {expected_error_codes}")
        print(f"   Found errors: {found_error_codes}")

        # Verify we caught the expected issues
        missing_errors = expected_error_codes - found_error_codes
        if missing_errors:
            print(f"❌ Missing expected errors: {missing_errors}")
            return False

        print("✅ All expected validation errors detected")

        # Step 5: Test CLI output formatting
        output = StringIO()
        reporter = RichReporter(output)

        # Report each error
        for error in all_errors:
            reporter.report_error(error)

        # Report summary
        errors_by_severity = {
            'critical': [e for e in all_errors if e.severity == ErrorSeverity.CRITICAL],
            'error': [e for e in all_errors if e.severity == ErrorSeverity.ERROR],
            'warning': [e for e in all_errors if e.severity == ErrorSeverity.WARNING]
        }

        reporter.report_summary(
            errors_by_severity['critical'] + errors_by_severity['error'],
            errors_by_severity['warning'],
            []
        )

        # Verify output formatting
        output_text = output.getvalue()

        required_in_output = [
            "CRITICAL",  # Should have critical errors
            "SendEmail", # Should mention the problematic action
            "Fix:",      # Should include fix suggestions
            "Summary:"   # Should include summary
        ]

        for requirement in required_in_output:
            if requirement not in output_text:
                print(f"❌ Missing required output: {requirement}")
                return False

        print("✅ CLI output formatting validated")
        print("\n📋 Sample Output:")
        print("=" * 50)
        print(output_text[:500] + "..." if len(output_text) > 500 else output_text)
        print("=" * 50)

        return True

    finally:
        # Clean up
        test_file.unlink()


def test_parallel_processing_integration():
    """Test that parallel processing works with real validation rules."""
    print("\n🧪 Testing Parallel Processing Integration...")

    # Create multiple test files
    test_files = []
    workflows = [
        """name: Test 1\ntrigger: {}\nactions:\n  Action1:\n    id: "1"\n    class: "Test"\n    properties: {}""",
        """name: Test 2\ntrigger: {}\nactions:\n  Action2:\n    id: "2"\n    _fields: []\n    properties: {}""",  # Field placement error
        """name: Test 3\ntrigger: {}\nactions: {}"""  # Valid minimal workflow
    ]

    for i, workflow in enumerate(workflows):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(workflow)
            test_files.append(Path(f.name))

    try:
        # Test parallel validation
        registry = ValidationRuleRegistry()
        registry.register(RequiredFieldsRule())
        registry.register(InvalidFieldPlacementRule())
        validator = ParallelValidator(registry, max_workers=2)
        results = list(validator.validate_batch(test_files))

        print(f"✅ Parallel processing: {len(results)} files processed")

        # Verify all files were processed
        if len(results) != len(test_files):
            print(f"❌ File count mismatch: expected {len(test_files)}, got {len(results)}")
            return False

        # Verify results structure
        for result in results:
            if not hasattr(result, 'file_path') or not hasattr(result, 'success'):
                print(f"❌ Invalid result structure")
                return False

        print("✅ Parallel processing integration validated")
        return True

    finally:
        # Clean up
        for test_file in test_files:
            test_file.unlink()


def run_integration_tests():
    """Run all integration tests."""
    print("🚀 Starting Integration Testing Suite\n")

    tests = [
        ("Full Validation Pipeline", test_full_validation_pipeline),
        ("Parallel Processing Integration", test_parallel_processing_integration)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name} PASSED\n")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED\n")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}\n")
            failed += 1

    print(f"🏁 Integration Test Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)