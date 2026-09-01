# Bug Test Fixture: CreateCase Description Over 2000 Character Limit

This fixture contains the TEST-MMB_v5.6.0.yaml workflow from February 24, 2026, which demonstrates Bug #12.

## Issue
The CalculateRiskScore action generates a `case_description` that can exceed Fusion's 2000-character limit for the CreateCase Description field.

## Test Execution That Failed
- **Date:** Feb 24, 2026 20:56:11
- **User:** agnes.baudry@example.com
- **Description Length:** 2103 characters (103 over limit)
- **Error:** `The length of "Description" is 2103, which exceeds the maximum permitted of 2000.`

## Expected Validator Behavior
The validator should detect this potential runtime issue and:
1. WARN that the `case_description` binding uses dynamic content (cannot validate exact length at design time)
2. Suggest adding truncation logic or defensive length checks
3. Recommend abbreviating verbose template sections

## Related Documentation
See `docs/known-issues/Bug-12-CreateCase-Description-Limit.md` for full details.

## Workflow Location
- Original: `Mass Mailing Behavior/workflows/TEST-MMB_v5.6.0.yaml`
- Copied: 2026-02-24 (before Bug #12 fix)
