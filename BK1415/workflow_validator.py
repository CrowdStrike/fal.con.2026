#!/usr/bin/env python3
"""
Fusion SOAR Workflow Validator (v2 shim)

Thin wrapper that delegates to the v2 plugin-based validator in
src/workflow_validator/. This file is symlinked into project folders
(MDDA, MMB) as tools/workflow_validator.py, so it must remain
directly runnable as a standalone script.

Usage:
    python3 tools/workflow_validator.py workflows/my-workflow.yaml
    python3 tools/workflow_validator.py workflows/*.yaml
    python3 tools/workflow_validator.py workflows/*.yaml --config config.yaml

Exit Codes:
    0 - No errors found
    1 - Validation errors found
    2 - Script error or invalid usage
"""

import sys
from pathlib import Path

# Add src/ to the FRONT of sys.path so the workflow_validator *package*
# is found before this file (which shares the same base name).
# We must also remove CWD / '' to prevent this script from shadowing
# the package during recursive imports.
_src_dir = str(Path(__file__).resolve().parent / "src")
_cwd = str(Path(__file__).resolve().parent)

# Prepend src/ and suppress CWD shadowing
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
# Remove entries that would resolve this script instead of the package
for _shadow in ('', '.', _cwd):
    while _shadow in sys.path:
        sys.path.remove(_shadow)

from workflow_validator.cli.main import main  # noqa: E402

# Restore CWD to sys.path after import (for any downstream code that needs it)
if '' not in sys.path:
    sys.path.append('')

if __name__ == '__main__':
    sys.exit(main())
