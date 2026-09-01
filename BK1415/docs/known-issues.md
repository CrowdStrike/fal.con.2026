# Known Issues / False Positives

## `default_name` flagged as INVALID_FIELD_PLACEMENT

**Status:** Suspected false positive  
**Rule:** `INVALID_FIELD_PLACEMENT`  
**Reported:** 2026-04-24 (AmberHead engagement)

### Description

The validator flags `default_name` at the action level as an unknown field with a CRITICAL severity. However, this field appears in Fusion workflow exports and is accepted by the Falcon UI without errors.

**Evidence:** The `non-pam-act-devices-v2.yml` workflow (Falcon ID `c6cf602206594729821a0b52f1e71394`) contains `default_name` on multiple actions and passes Falcon's own validator cleanly. The same field on structurally similar workflows is flagged by our validator as CRITICAL.

### Likely Cause

`default_name` is written by Fusion on export to record the action type's display name, and is accepted (or silently ignored) by Fusion on import. The validator's schema check doesn't account for it.

### Recommended Fix

Add `default_name` to the list of known/allowed action-level fields so it doesn't trigger `INVALID_FIELD_PLACEMENT`. Alternatively, downgrade to INFO if it can't be confirmed safe to suppress entirely.
