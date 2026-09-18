"""Pin compatibility and control identities for the Phase 4 treatment.

``GOVERNED_APP_VERSION`` identifies the HTTP treatment, while
``WORKFLOW_SCHEMA_VERSION`` gates durable state compatibility.
``BASELINE_CONTROL_SHA256`` is the reviewed aggregate digest of Phase 3 baseline v5;
experiment startup verifies it instead of silently accepting control drift.
"""

GOVERNED_APP_VERSION = "0.6.1"
WORKFLOW_SCHEMA_VERSION = 1
BASELINE_CONTROL_SHA256 = "06eb0c9086b43f5581805c946b727ee5503abe6a3a293fabeed4dca0edad03dc"
