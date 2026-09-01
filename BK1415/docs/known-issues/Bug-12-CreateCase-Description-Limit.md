# Bug #12: CreateCase Description Field Exceeds 2000 Character Limit

**Date Discovered:** February 24, 2026
**Severity:** HIGH
**Status:** Documented, awaiting validator enhancement

## Summary

The Fusion Cases API enforces a 2000-character limit on the `Description` field when creating cases. The Mass Mailing Behavior (MMB) workflow's `CalculateRiskScore` action generates case descriptions that can exceed this limit, causing `CreateANewCase` to fail with:

```
The length of "Description" is 2103, which exceeds the maximum permitted of 2000.
```

## Failed Execution Details

**Execution ID:** Feb 24, 2026 20:56:11 [TEST]
**Workflow:** TEST-MMBv5.8.0-Mass-Mailing-Behavior
**User:** agnes.baudry@example.com
**Detection ID:** `1ee2492f98ef4f9fb5f23b5269a12d4d:thirdparty:1ee2492f98ef4f9fb5f23b5269a12d4d:44a801a913844e97bf6f4dc834e7bcdb`

**Action Sequence:**
1. All enrichment queries completed successfully
2. Risk score calculated: 47/116 (HIGH)
3. Companion detection closed successfully
4. `CreateANewCase` action failed with description length error

**Generated Description Length:** 2103 characters (103 over limit)

## Case Description Structure

The case description is built from these sections:

```
=== SUMMARY === (attack_story + XDR recipients + threshold summary)
=== EMAIL VOLUME (40/40) === (current vs baseline with deviation %)
=== EMAIL CONTENT (5/15) === (bulk subjects list, top 5 subjects)
=== AUTHENTICATION (0/26) === (sign-in summary)
=== CLIENT AGENT (0/5) === (client breakdown with full app lists)
=== IP ENRICHMENT (VirusTotal) === (IP, ASN, country, reputation)
=== MAILBOX RULES (0/15) === (rule changes)
=== OTHER SECURITY ALERTS & DETECTIONS (5/15) === (detection list)
=== MITIGATING FACTORS (-3) === (MFA, clean mailbox)
```

**High-Risk Sections (contributing most to length):**

1. **CLIENT AGENT section** — Full app name lists can be 200+ chars:
   ```
   Client breakdown (24h): Browser 96% (54, apps: NB Recognition, Yammer Web,
   Office365 Shell WCSS-Client, LinkedIn Learning, Mimecast SAML SSO, SharePoint
   Online Web Client Extensibility, Microsoft Docs, My Apps, Microsoft Account
   Controls V2, Workday) | Desktop/Mobile 4% (2, apps: Windows Sign In) | ...
   ```

2. **EMAIL CONTENT section** — Subject lines can be very long:
   ```
   Bulk Subjects (100+ recipients, 2h):
   Canceled: 2026 Data & Analytics Meetups (1332 rcpts)
   2026 Data & Analytics Meetups (393 rcpts)

   Top 5 Subjects (by recipient count, 2h):
   Re: [EXT] Kenny, discover trending activity in your organization (2 rcpts)
   Introduction and guidance (2 rcpts)
   ...
   ```

3. **OTHER SECURITY ALERTS section** — Detection lists can be verbose if multiple detection types exist

## Impact

- HIGH severity detections cannot have cases created
- Workflow appears to complete but silently fails at case creation
- No automatic retry or fallback mechanism
- Detection remains open with no case tracking

## Validator Gap

**Current validator does NOT check:**
- Character length limits for CreateCase action fields
- Property binding expressions that could exceed limits at runtime
- Dynamic content that varies by execution context

**Current validator DOES check:**
- Inline query size limits (26,000 chars)
- Pipe/subquery limits (100 pipes)
- Output schema completeness

## Proposed Validation Rule

### Rule Name: `CreateCaseFieldLimits`

### Rule Logic:
1. Identify all actions with `class: CreateCaseV1` or similar case creation classes
2. For each action, check property bindings for the `Description` field
3. If the binding uses a static string:
   - Measure length directly
   - ERROR if > 2000 chars
   - WARN if > 1800 chars (90% threshold)
4. If the binding uses a dynamic expression (`${data[...]}`):
   - WARN that runtime validation is not possible
   - Suggest adding truncation logic or defensive length checks
5. Provide fix suggestion: Use `format()` with max length or truncation

### Example Violations:

```yaml
# STATIC - can be validated
configuration:
  Description: "Very long static description that exceeds 2000 characters..."
# ERROR: Description field is 2103 characters, exceeds 2000 char limit

# DYNAMIC - runtime risk
configuration:
  Description: ${data['CalculateRiskScore.results'][0]['case_description']}
# WARN: Description uses dynamic binding - cannot validate length at workflow design time.
#       Consider adding truncation: ${data['...']['case_description'][:1900] + '...'}
```

### Implementation Notes:

- Create new rule file: `src/workflow_validator/rules/createcase_field_limits.py`
- Register in rule registry
- Add test fixtures in `tests/` with known-good and known-bad workflows
- Document in validator README

## Known API Field Limits (Fusion Cases)

| Field | Limit | Source |
|-------|-------|--------|
| `Description` | 2000 chars | Observed runtime error (Feb 24, 2026) |
| `Name` | Unknown | Not yet tested |
| `Tags` | Unknown (array) | Not yet tested |

## Workarounds (Temporary)

1. **Truncate in CEL expression:**
   ```yaml
   Description: ${data['CalculateRiskScore.results'][0]['case_description'][:1900] + '\n\n[TRUNCATED - see detection comments for full details]'}
   ```

2. **Abbreviate verbose sections:**
   - Limit app name lists to top 5 instead of full list
   - Show only top 3 subjects instead of top 5
   - Truncate subject lines to 60 chars max

3. **Move verbose details to detection comments:**
   - Keep case description minimal (summary only)
   - Add full details via `AddCommentToCase` action (comments have higher/no limits)

## Related Platform Rules

This issue relates to **Platform Rule #14**:
> Always validate LogScale query syntax via `ngsiem_query_runner.py` before deploying to workflows.

**Proposed Platform Rule #16:**
> Fusion Cases API has a 2000-character limit on the Description field. When generating case descriptions dynamically, ensure templates stay under 1800 chars (90% threshold) to account for variable content. Consider truncation logic or moving verbose details to case comments.

## Test Fixtures Needed

1. `tests/fixtures/createcase-description-over-limit.yaml` — Static description > 2000 chars (should ERROR)
2. `tests/fixtures/createcase-description-near-limit.yaml` — Static description 1850 chars (should WARN)
3. `tests/fixtures/createcase-description-dynamic.yaml` — Dynamic binding from CalculateRiskScore (should WARN about runtime risk)

## References

- Execution log: Feb 24, 2026 20:56:11 [TEST] - agnes.baudry@example.com
- Failed action: `CreateANewCase`
- Error message: `The length of "Description" is 2103, which exceeds the maximum permitted of 2000.`
- Workflow files: `workflows/MMB_v5.6.0.yaml`, `workflows/TEST-MMB_v5.6.0.yaml`
- CalculateRiskScore action generates the `case_description` field
