"""Pin compatibility and control identities for the Phase 4 treatment.

``GOVERNED_APP_VERSION`` identifies the HTTP treatment, while
``WORKFLOW_SCHEMA_VERSION`` gates durable state compatibility.
``BASELINE_CONTROL_SHA256`` is the reviewed aggregate digest of Phase 3 baseline v5;
experiment startup verifies it instead of silently accepting control drift.
"""

GOVERNED_APP_VERSION = "0.6.2"
WORKFLOW_SCHEMA_VERSION = 1
BASELINE_CONTROL_SHA256 = "199ed67020eac95de5a67b53e84b2dd4423beedd4c20ecf8e61b136071f14552"
