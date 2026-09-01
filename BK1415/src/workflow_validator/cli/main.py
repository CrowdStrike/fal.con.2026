"""Main CLI interface for workflow validator."""

import os
import sys
from pathlib import Path
from typing import List

from ..registry.rule_registry import ValidationRuleRegistry
from ..rules.required_fields import RequiredFieldsRule
from ..rules.action_structure import ActionStructureRule
from ..rules.field_placement import InvalidFieldPlacementRule
from ..rules.sendemail_rules import SendEmailValidationRule
from ..rules.inline_query_size import InlineQuerySizeRule
from ..rules.inline_query_pipes import InlineQueryPipesRule
from ..rules.csv_header_fields import CsvHeaderFieldsRule
from ..rules.output_schema import OutputSchemaRule
from ..rules.trigger_structure import TriggerStructureRule
from ..rules.duplicate_action_names import DuplicateActionNamesRule
from ..rules.mixed_print_formats import MixedPrintFormatsRule
from ..rules.orphaned_yaml_fragments import OrphanedYamlFragmentsRule
from ..rules.field_names import FieldNamesRule
from ..rules.createcase_field_limits import CreateCaseFieldLimitsRule
from ..rules.soar_payload_size import SoarPayloadSizeRule
from ..rules.invalid_variable_subscript import InvalidVariableSubscriptRule
from ..rules.loop_iteration_usage import LoopIterationUsageRule
from ..core.parallel_validator import ParallelValidator
from ..config import ConfigurationManager, ValidationConfig
from .rich_reporter import RichReporter


def setup_validation_registry(config: ValidationConfig) -> ValidationRuleRegistry:
    """Set up the validation registry with all available rules based on configuration."""
    registry = ValidationRuleRegistry()

    all_rules = [
        ("required_fields", RequiredFieldsRule()),
        ("action_structure", ActionStructureRule()),
        ("field_placement", InvalidFieldPlacementRule()),
        ("sendemail_validation", SendEmailValidationRule()),
        ("inline_query_size", InlineQuerySizeRule()),
        ("inline_query_pipes", InlineQueryPipesRule()),
        ("csv_header_fields", CsvHeaderFieldsRule()),
        ("output_schema", OutputSchemaRule()),
        ("trigger_structure", TriggerStructureRule()),
        ("duplicate_action_names", DuplicateActionNamesRule()),
        ("mixed_print_formats", MixedPrintFormatsRule()),
        ("orphaned_yaml_fragments", OrphanedYamlFragmentsRule()),
        ("field_names", FieldNamesRule()),
        ("createcase_field_limits", CreateCaseFieldLimitsRule()),
        ("soar_payload_size", SoarPayloadSizeRule()),
        ("invalid_variable_subscript", InvalidVariableSubscriptRule()),
        ("loop_iteration_usage", LoopIterationUsageRule()),
    ]

    for rule_name, rule_instance in all_rules:
        if config.is_rule_enabled(rule_name):
            registry.register(rule_instance)

    return registry


def _load_dotenv_if_available():
    """Best-effort .env load so --server-validate picks up FALCON_* vars."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    start = Path.cwd().resolve()
    for d in [start, *start.parents]:
        env = d / ".env"
        if env.is_file():
            load_dotenv(env)
            return


def run_server_validate(file_paths: List[Path]) -> int:
    """Call the Fusion validate_only=true endpoint for each file.

    Returns exit code: 0 if all pass, 1 if any errors, 2 on auth/network failure.
    """
    _load_dotenv_if_available()
    try:
        from ..server_validate import server_validate_only
    except Exception as e:
        print(f"❌ Server-validate module unavailable: {e}", file=sys.stderr)
        return 2

    total_errors = 0
    files_with_errors = 0
    any_infra_error = False

    for path in file_paths:
        print(f"\n🔎 Server-validate: {path}")
        try:
            yaml_text = path.read_text()
        except Exception as e:
            print(f"   ❌ Could not read file: {e}")
            total_errors += 1
            files_with_errors += 1
            continue

        try:
            ok, errors, summary = server_validate_only(yaml_text)
        except RuntimeError as e:
            # Auth/env errors — treat as infrastructure failure, not validation.
            print(f"   ❌ {e}")
            any_infra_error = True
            continue
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            any_infra_error = True
            continue

        if ok:
            print(f"   ✅ PASS ({summary})")
        else:
            files_with_errors += 1
            total_errors += len(errors) or 1
            print(f"   ❌ FAIL ({summary}) — {len(errors)} server error(s):")
            for err in errors:
                code = err.get('code', 'N/A')
                msg = err.get('message', 'N/A')
                where = err.get('id') or err.get('node_id') or ''
                suffix = f" (node: {where})" if where else ""
                print(f"      [{code}] {msg}{suffix}")

    print()
    # Infra/auth errors dominate the exit code: a partial run where some files
    # couldn't be reached is "could not validate" (2), not "validation failed"
    # (1) — even if the files that DID run reported validation errors. Treating
    # an incomplete run as a clean 1 would let CI conclude "only N errors" when
    # the true count is unknown.
    if any_infra_error:
        if total_errors > 0:
            print(f"⚠️  Server-validate incomplete: {files_with_errors} file(s) with "
                  f"{total_errors} error(s), plus auth/network failures on other file(s).")
        else:
            print("⚠️  Server-validate could not be completed (auth/network).")
        return 2
    if total_errors > 0:
        print(f"❌ Server-validate: {files_with_errors} file(s) with {total_errors} error(s).")
        return 1
    print(f"✅ Server-validate: {len(file_paths)} file(s) passed.")
    return 0


def validate_files(file_paths: List[Path], config_path: Path = None,
                   server_validate: bool = False) -> int:
    """Validate workflow files and return exit code.

    Returns:
        Exit code (0 = success, 1 = validation errors, 2 = script/auth error)
    """
    if not file_paths:
        print("No files provided for validation", file=sys.stderr)
        return 2

    config_manager = ConfigurationManager()
    config = config_manager.load_config(config_path)

    registry = setup_validation_registry(config)
    validator = ParallelValidator(registry, max_workers=config.parallel.get("max_workers"))
    reporter = RichReporter(use_colors=config.output.get("colors", True))

    results = list(validator.validate_batch(file_paths))

    total_errors = 0
    files_with_errors = 0

    for result in results:
        blocker_count = sum(1 for e in result.errors if e.is_blocker())
        if blocker_count > 0:
            files_with_errors += 1
            total_errors += blocker_count

        reporter.report_file_summary(str(result.file_path), result.errors)
        for error in result.errors:
            reporter.report_error(error)

    reporter.report_batch_summary(
        total_files=len(results),
        total_errors=total_errors,
        files_with_errors=files_with_errors,
    )

    local_exit = 1 if total_errors > 0 else 0

    if not server_validate:
        return local_exit

    # Server-side gate runs regardless of local result (may surface additional errors).
    print("\n" + "=" * 50)
    print("Server-side validation (validate_only=true)")
    print("=" * 50)
    server_exit = run_server_validate(file_paths)

    # Aggregate: worst wins. 2 (infra) > 1 (validation) > 0.
    if local_exit == 2 or server_exit == 2:
        return 2
    return 1 if (local_exit == 1 or server_exit == 1) else 0


def main():
    """Main CLI entry point."""
    argv = sys.argv[1:]
    if not argv:
        print("Usage: python -m workflow_validator <workflow_file> [<workflow_file> ...]")
        print("       python -m workflow_validator workflows/*.yaml")
        print("       python -m workflow_validator --config config.yaml workflows/*.yaml")
        print("       python -m workflow_validator --server-validate workflow.yaml")
        return 2

    config_path = None
    server_validate = False
    file_args = []

    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--config" and i + 1 < len(argv):
            config_path = Path(argv[i + 1])
            i += 2
        elif tok in ("--server-validate", "-s"):
            server_validate = True
            i += 1
        elif tok in ("-h", "--help"):
            print("Usage: workflow_validator.py <file...> [--config FILE] [--server-validate|-s]")
            print()
            print("  --server-validate, -s   Call Fusion validate_only=true as a second gate.")
            print("                          Requires FALCON_CLIENT_ID/SECRET/BASE_URL in env.")
            return 0
        else:
            file_args.append(tok)
            i += 1

    file_paths = []
    for arg in file_args:
        path = Path(arg)
        if path.exists():
            file_paths.append(path)
        else:
            print(f"Warning: File not found: {arg}", file=sys.stderr)

    return validate_files(file_paths, config_path, server_validate=server_validate)


if __name__ == "__main__":
    sys.exit(main())
