"""Pin compatibility and control identities for the Phase 4 treatment.

``GOVERNED_APP_VERSION`` identifies the HTTP treatment, while
``WORKFLOW_SCHEMA_VERSION`` gates durable state compatibility.
``BASELINE_CONTROL_SHA256`` is the reviewed aggregate digest of Phase 3 baseline v4;
experiment startup verifies it instead of silently accepting control drift.
"""

GOVERNED_APP_VERSION = "0.6.0"
WORKFLOW_SCHEMA_VERSION = 1
BASELINE_CONTROL_SHA256 = "eaa5c1e7db587618d0ab5d9b22a4e32042942b2b97d1aeced88d3c8d457ff288"
