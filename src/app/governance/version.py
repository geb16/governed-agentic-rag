"""Pin compatibility and control identities for the Phase 4 treatment.

``GOVERNED_APP_VERSION`` identifies the HTTP treatment, while
``WORKFLOW_SCHEMA_VERSION`` gates durable state compatibility.
``BASELINE_CONTROL_SHA256`` is the reviewed aggregate digest of Phase 3 baseline v2;
experiment startup verifies it instead of silently accepting control drift.
"""

GOVERNED_APP_VERSION = "0.6.0"
WORKFLOW_SCHEMA_VERSION = 1
BASELINE_CONTROL_SHA256 = "1e4b31364496f692880aeb82e983133d10be5f66cc6125bf5c11454ca18012e3"
