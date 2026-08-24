"""Pin compatibility and control identities for the Phase 4 treatment.

``GOVERNED_APP_VERSION`` identifies the HTTP treatment, while
``WORKFLOW_SCHEMA_VERSION`` gates durable state compatibility.
``BASELINE_CONTROL_SHA256`` is the reviewed aggregate digest of Phase 3 baseline v2;
experiment startup verifies it instead of silently accepting control drift.
"""

GOVERNED_APP_VERSION = "0.5.0"
WORKFLOW_SCHEMA_VERSION = 1
BASELINE_CONTROL_SHA256 = "cd8c823a477419f7010c6d5beae1069baa154496e79fe52ed7fcaefcfe05f4b0"
