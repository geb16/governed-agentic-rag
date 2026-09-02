"""Pin compatibility and control identities for the Phase 4 treatment.

``GOVERNED_APP_VERSION`` identifies the HTTP treatment, while
``WORKFLOW_SCHEMA_VERSION`` gates durable state compatibility.
``BASELINE_CONTROL_SHA256`` is the reviewed aggregate digest of Phase 3 baseline v2;
experiment startup verifies it instead of silently accepting control drift.
"""

GOVERNED_APP_VERSION = "0.5.1"
WORKFLOW_SCHEMA_VERSION = 1
BASELINE_CONTROL_SHA256 = "e3d16bb50cf815fda5939a53223356ce96c6dbafec1c4e00e01cf9e6d51fb12e"
