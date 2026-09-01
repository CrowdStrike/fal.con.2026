---
title: "Fusion SOAR Workflow Validator"
confluence_space: "Nathan Church - Personal Space"
confluence_space_key: "NCHURCH"
confluence_page_id: 827644892
confluence_url: "https://wiki.cs.sys/spaces/NCHURCH/pages/827644892/Fusion+SOAR+Workflow+Validator"
confluence_version: 5
last_modified: "2026-01-31T02:59:23.000Z"
last_modified_by: "Nathan Church"
pulled_at: "2026-02-13T20:22:29.000Z"
---

# Fusion SOAR Workflow Validator

Fusion SOAR Workflow Validator
==============================

**Tool:** workflow\_validator.py  
**Purpose:** Validates CrowdStrike Fusion SOAR workflow YAML files before import  
**Download:**

Overview
--------

The Fusion SOAR Workflow Validator is a Python tool that validates SOAR workflow YAML files against schema requirements before importing them into the Fusion platform. It identifies common configuration issues that cause import failures or runtime problems.

### Key Features

* Validates workflow schema compliance
* Detects common configuration errors
* Provides specific fix recommendations
* Supports batch processing of multiple workflows
* Integrates with CI/CD pipelines

Installation
------------

Download the script from the attachment above. Requires Python 3.7+ and the PyYAML library:

bash
pip install pyyaml

Usage
-----

### Basic Validation

bash
# Validate a single workflow
python3 workflow\_validator.py my-workflow.yaml
# Validate with verbose output
python3 workflow\_validator.py my-workflow.yaml --verbose

### Batch Processing

bash
# Validate multiple workflows with summary output
python3 workflow\_validator.py workflows/\*.yaml --summary
# Generate detailed reports plus JSON output for automation
python3 workflow\_validator.py workflows/\*.yaml --json

### Command Line Options

| Option | Description |
| --- | --- |
| `--verbose, -v` | Show detailed validation information including INFO messages |
| `--summary, -s` | Summary mode for multiple files (shows pass/fail status only) |
| `--json` | Show full validation reports plus JSON output for automation |
| `--help` | Show help and usage information |

Validation Checks
-----------------

The validator performs the following checks:

### Required Structure

* Top-level required fields (name, trigger, actions)
* Action structure and required properties
* Proper field placement (properties vs action level)

### Common Issues

* **Field Placement:** Properties incorrectly placed at action level instead of within properties block
* **SendEmail Configuration:** Empty recipient lists in email actions
* **Output Schema:** Missing or incomplete schema definitions for UI integration
* **CSV Header Fields:** Missing workflow\_csv\_header\_fields for inline query actions

Understanding Output
--------------------

### Error Levels

* **ERROR:** Critical issues that will prevent workflow import
* **WARNING:** Issues that may cause problems or reduced functionality
* **INFO:** Recommendations for best practices (shown with --verbose)

### Exit Codes

* **0:** Validation passed (no critical errors)
* **1:** Validation failed (critical errors found)
* **2:** Script error or invalid usage

Common Fixes
------------

### Property Placement Issues

Move properties from action level to properties block:

yamlIncorrect
MyAction:
id: action-uuid
workflow\_csv\_header\_fields: [] # Wrong location
properties:
alertId: ${data['Detection.ID']}
yamlCorrect
MyAction:
id: action-uuid
properties:
alertId: ${data['Detection.ID']}
workflow\_csv\_header\_fields: [] # Correct location

### SendEmail Recipients

Ensure email actions have configured recipients:

yamlIncorrect
SendAlert:
properties:
to: [] # Empty recipients
subject: "Alert"
yamlCorrect
SendAlert:
properties:
to:
- team@company.com
- alerts@company.com
subject: "Alert"

CI/CD Integration
-----------------

Integrate validation into your deployment pipeline:

bashPre-deployment validation script
#!/bin/bash
echo "Validating workflows..."
python3 workflow\_validator.py workflows/\*.yaml --summary
if [ $? -eq 0 ]; then
echo "Validation passed"
exit 0
else
echo "Validation failed"
exit 1
fi

Configuration
-------------

The validator can be customized by modifying the validation rules in the source code. Key areas for customization:

* **Required Schema Fields:** Update the `required_schema_fields` list in `_check_inline_query_output_schema()`
* **SendEmail Detection:** Modify the `known_sendemail_id_prefix` in `_check_sendemail_recipients()`
* **Allowed Action Fields:** Update `allowed_action_fields` in `_check_invalid_action_level_fields()`

Troubleshooting
---------------

### Common Error Messages

| Error | Cause | Solution |
| --- | --- | --- |
| "Invalid YAML syntax" | Malformed YAML file | Check YAML syntax and indentation |
| "pyyaml not installed" | Missing dependency | Run `pip install pyyaml` |
| "No workflow files found" | Incorrect file path | Verify file paths and glob patterns |

### Getting Help

bash
# Show help information
python3 workflow\_validator.py --help

Technical Details
-----------------

### Architecture

* **ValidationError class:** Represents validation issues with severity and fix suggestions
* **WorkflowValidator class:** Main validation engine with modular check methods
* **Modular validation:** Each check is implemented as a separate method for maintainability

### Performance

* Typical validation time: < 2 seconds per workflow
* Memory usage: < 50MB for batch processing
* Scales linearly with number of workflows

### Security

* Uses `yaml.safe_load()` to prevent code injection
* No external network connections
* Read-only operation on workflow files

Version Control
---------------

This tool will be migrated to GitLab in the future, enabling version control, issue tracking, and collaborative development. Once hosted in GitLab, teams will be able to clone the repository, submit pull requests for enhancements, and track issues centrally.



---

*Last updated: January 30, 2026  
Tool version: Compatible with CrowdStrike Fusion SOAR platform*