"""Pin compatibility and control identities for the Phase 4 treatment.

``GOVERNED_APP_VERSION`` identifies the HTTP treatment, while
``WORKFLOW_SCHEMA_VERSION`` gates durable state compatibility.
``BASELINE_CONTROL_SHA256`` is the reviewed aggregate digest of Phase 3 baseline v2;
experiment startup verifies it instead of silently accepting control drift.
"""

GOVERNED_APP_VERSION = "0.6.0"
WORKFLOW_SCHEMA_VERSION = 1
BASELINE_CONTROL_SHA256 = "02cc38a83da90d2ac2a5b835ac657183f2b085d30d56e6c5ec59603a7c131ac2"
