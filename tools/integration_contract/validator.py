"""Structural and reference validation for Integration Contract V1."""
from __future__ import annotations

import math
import re
from typing import Any

API_VERSION = "constellation.integration/v1"
ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")


class ContractValidationError(ValueError):
    def __init__(self, code: str, field: str, message: str):
        super().__init__(message)
        self.code, self.field = code, field

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "field": self.field, "message": str(self)}


TOP_FIELDS = {
    "apiVersion", "integration", "sources", "owners", "authorities", "operations",
    "gates", "credentials", "receipts", "resourceRules", "repairAuthority", "outcomes",
    "reconciliation", "rawEvidence", "cleanupRules", "rollback", "privacyEgress",
    "ownerDecisions", "autonomousRepairs", "imports", "assessment",
}
INTERFACE_CLOSURE_FIELDS = {
    "basisSourceRefs", "ownerRefs", "authorityRefs", "operationRefs", "gateRefs",
    "credentialRefs", "receiptRefs", "resourceRuleRefs", "privacyRuleRefs",
    "cleanupRuleRefs",
}
OP_KINDS = {"local-preparation", "local-effect", "external-effect", "production-effect", "read-only-reconciliation", "cleanup"}
AUTHORITY_KINDS = {"local-work", "storage", "compute", "effect", "external-effect", "production-effect", "privacy", "acceptance", "cleanup"}
PROTECTED_BOUNDARIES = {"semantics", "authority", "privacy", "production-state", "acceptance-criteria"}
GATE_KINDS = {"owner", "prerequisite-source", "required-evidence", "time-boundary"}
AUTONOMOUS_REPAIR_CATEGORIES = {"composition", "implementation", "test", "documentation"}
EFFECT_AUTHORITY_KINDS = {
    "local-effect": "effect",
    "external-effect": "external-effect",
    "production-effect": "production-effect",
}
RECEIPT_FACT_STATES = {"recorded", "missing", "template", "unverified"}
EXECUTION_CLASSES = {"source-only", "runtime"}
UNPRIVILEGED_EQUIVALENCE = {"exact", "delegated-primitive", "none"}
PRIMITIVE_IDENTITY_KINDS = {"digest", "package-artifact", "service-endpoint"}
OBSERVATION_COVERAGE_KINDS = {
    "all-owner-uid-processes", "invoking-owner-processes", "declared-inputs", "endpoint-response",
}
OBSERVATION_COVERAGE_PROFILES = {
    "all-owner-uid-processes": {
        "population": "all-owner-uids",
        "pidNamespace": "bound-host-pid-namespace",
        "userNamespace": "bound-initial-user-namespace",
        "procfsVisibility": "all-pids-hidepid-zero-or-refuse",
        "requiresBinding": True,
    },
    "invoking-owner-processes": {
        "population": "invoking-owner-uid",
        "pidNamespace": "operation-pid-namespace",
        "userNamespace": "operation-user-namespace",
        "procfsVisibility": "invoking-owner-pids-or-refuse",
        "requiresBinding": False,
    },
    "declared-inputs": {
        "population": "declared-input-set",
        "pidNamespace": "operation-pid-namespace",
        "userNamespace": "operation-user-namespace",
        "procfsVisibility": "not-applicable",
        "requiresBinding": False,
    },
    "endpoint-response": {
        "population": "declared-endpoint",
        "pidNamespace": "not-applicable",
        "userNamespace": "not-applicable",
        "procfsVisibility": "not-applicable",
        "requiresBinding": False,
    },
}
OBSERVATION_CLAIM_KINDS = {"producer-absence", "input-state", "endpoint-state"}
SHARED_EXCLUSION_KINDS = {"filesystem-lock", "lease-record", "scheduler-slot"}
EXCLUSION_RECEIPT_ROLES = {
    "acquisition": "shared-exclusion-acquire",
    "hold": "shared-exclusion-hold",
    "handoff": "shared-exclusion-handoff",
    "release": "shared-exclusion-release",
}
EXCLUSION_PHASE_PREDICATES = {
    "before-observation", "before-dispatch", "through-dispatch-handoff",
    "through-attempt-terminal", "to-declared-operation",
    "after-dispatch-handoff", "after-attempt-terminal",
    "on-refusal-before-dispatch",
}
INVOCATION_AUTHORITY_KINDS = {
    "local-preparation": {"local-work", "compute"},
    "local-effect": {"effect"},
    "external-effect": {"external-effect"},
    "production-effect": {"production-effect"},
    "read-only-reconciliation": {"local-work"},
    "cleanup": {"cleanup"},
}


def fail(code: str, field: str, message: str) -> None:
    raise ContractValidationError(code, field, message)


def obj(value: Any, field: str, required: set[str], optional: set[str] = frozenset()) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail("TYPE_OBJECT", field, "must be an object")
    missing, extra = required - set(value), set(value) - required - optional
    if missing:
        fail("FIELD_MISSING", field, f"missing fields: {', '.join(sorted(missing))}")
    if extra:
        fail("FIELD_UNKNOWN", field, f"unknown fields: {', '.join(sorted(extra))}")
    return value


def string(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not value:
        fail("TYPE_STRING", field, "must be a non-empty string")
    return value


def identifier(value: Any, field: str) -> str:
    result = string(value, field)
    assert result is not None
    if not ID.fullmatch(result):
        fail("FORMAT_ID", field, "must be a simple identifier")
    return result


def boolean(value: Any, field: str) -> bool:
    if type(value) is not bool:
        fail("TYPE_BOOLEAN", field, "must be a boolean")
    return value


def number(value: Any, field: str) -> int | float:
    if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)) or value < 0:
        fail("TYPE_NUMBER", field, "must be a finite non-negative number (boolean is not a number)")
    return value


def strings(value: Any, field: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        fail("TYPE_STRING_LIST", field, "must be a string list" + (" with at least one item" if nonempty else ""))
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(string(item, f"{field}[{index}]") or "")
    if len(set(result)) != len(result):
        fail("DUPLICATE_LIST_ITEM", field, "must not contain duplicates")
    return result


def enum(value: Any, field: str, allowed: set[str]) -> str:
    result = string(value, field)
    assert result is not None
    if result not in allowed:
        fail("VALUE_ENUM", field, f"must be one of: {', '.join(sorted(allowed))}")
    return result


def collection(
    document: dict[str, Any],
    name: str,
    required: set[str],
    optional: set[str] = frozenset(),
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    value = document[name]
    if not isinstance(value, list):
        fail("TYPE_ARRAY", name, "must be an array")
    result, indexed = [], {}
    for index, item in enumerate(value):
        path = f"{name}[{index}]"
        parsed = obj(item, path, required, optional)
        item_id = identifier(parsed["id"], f"{path}.id")
        if item_id in indexed:
            fail("DUPLICATE_ID", f"{path}.id", f"duplicate {name} id: {item_id}")
        indexed[item_id] = parsed
        result.append(parsed)
    return result, indexed


def refs(values: list[str], allowed: set[str], field: str) -> None:
    missing = set(values) - allowed
    if missing:
        fail("REFERENCE_DANGLING", field, f"unknown references: {', '.join(sorted(missing))}")


def validate_namespace(value: Any, field: str) -> dict[str, Any]:
    namespace = obj(value, field, {"pidNamespace", "userNamespace", "procfsVisibility"})
    enum(namespace["pidNamespace"], f"{field}.pidNamespace", {"bound-host-pid-namespace", "operation-pid-namespace", "not-applicable"})
    enum(namespace["userNamespace"], f"{field}.userNamespace", {"bound-initial-user-namespace", "operation-user-namespace", "not-applicable"})
    enum(namespace["procfsVisibility"], f"{field}.procfsVisibility", {"all-pids-hidepid-zero-or-refuse", "invoking-owner-pids-or-refuse", "not-applicable"})
    return namespace


def validate_observation_coverage(value: Any, field: str) -> dict[str, Any]:
    coverage = obj(value, field, {"kind", "population", "completeness", "namespaceScope", "bindingReceiptRefs"})
    kind = enum(coverage["kind"], f"{field}.kind", OBSERVATION_COVERAGE_KINDS)
    enum(coverage["population"], f"{field}.population", {item["population"] for item in OBSERVATION_COVERAGE_PROFILES.values()})
    enum(coverage["completeness"], f"{field}.completeness", {"complete-or-refuse"})
    namespace = validate_namespace(coverage["namespaceScope"], f"{field}.namespaceScope")
    bindings = strings(coverage["bindingReceiptRefs"], f"{field}.bindingReceiptRefs")
    profile = OBSERVATION_COVERAGE_PROFILES[kind]
    for key in ("population", "pidNamespace", "userNamespace", "procfsVisibility"):
        actual = coverage["population"] if key == "population" else namespace[key]
        if actual != profile[key]:
            fail("EXECUTION_BOUNDARY_COVERAGE_PROFILE", f"{field}.{key if key == 'population' else 'namespaceScope.' + key}", f"{kind} requires {profile[key]}")
    if profile["requiresBinding"] != bool(bindings):
        fail("EXECUTION_BOUNDARY_COVERAGE_BINDING", f"{field}.bindingReceiptRefs", f"{kind} requires exact runtime-domain binding receipts" if profile["requiresBinding"] else f"{kind} does not accept process-domain binding receipts")
    return coverage


def validate_mechanism_identity(value: Any, field: str, kinds: set[str]) -> dict[str, Any]:
    identity = obj(value, field, {"kind", "reference", "identityPin", "sourceRef"})
    kind = enum(identity["kind"], f"{field}.kind", kinds)
    string(identity["reference"], f"{field}.reference")
    pin = string(identity["identityPin"], f"{field}.identityPin") or ""
    identifier(identity["sourceRef"], f"{field}.sourceRef")
    if kind != "service-endpoint" and not re.fullmatch(r"sha256:[0-9a-f]{64}", pin):
        fail("EXECUTION_BOUNDARY_PRIMITIVE_IDENTITY", f"{field}.identityPin", "local mechanism identity requires an exact lowercase sha256 pin")
    if kind == "service-endpoint" and not re.fullmatch(r"(?:spki-sha256:[0-9a-f]{64}|service-id:[a-zA-Z0-9][a-zA-Z0-9._:/@+-]*)", pin):
        fail("EXECUTION_BOUNDARY_PRIMITIVE_IDENTITY", f"{field}.identityPin", "service endpoint identity requires an exact SPKI digest or stable service-id pin")
    return identity


def validate_contract(document: Any) -> dict[str, Any]:
    # Pre-closure documents remain parseable as incomplete drafts. A declared
    # interfaceClosure is checked below after every referenced collection is
    # available; preflight makes its absence an integration blocker.
    doc = obj(document, "$", TOP_FIELDS, {"interfaceClosure"})
    if doc["apiVersion"] != API_VERSION:
        fail("VERSION_UNKNOWN", "apiVersion", f"must equal {API_VERSION}")
    integration = obj(doc["integration"], "integration", {"id", "description", "intendedConsumers"})
    identifier(integration["id"], "integration.id")
    string(integration["description"], "integration.description")
    consumers = set(strings(integration["intendedConsumers"], "integration.intendedConsumers", nonempty=True))

    sources, source_by = collection(doc, "sources", {"id", "kind", "ref", "pin", "status", "unresolvedReason"})
    for index, source in enumerate(sources):
        path = f"sources[{index}]"
        string(source["kind"], f"{path}.kind"); string(source["ref"], f"{path}.ref")
        state = enum(source["status"], f"{path}.status", {"pinned", "unverified"})
        pin = string(source["pin"], f"{path}.pin", nullable=True)
        reason = string(source["unresolvedReason"], f"{path}.unresolvedReason", nullable=True)
        if state == "pinned" and pin is None:
            fail("SOURCE_PIN_REQUIRED", f"{path}.pin", "pinned source requires a pin")
        if state == "unverified" and reason is None:
            fail("SOURCE_REASON_REQUIRED", f"{path}.unresolvedReason", "unverified source requires a reason")

    owners, owner_by = collection(doc, "owners", {"id", "name", "status", "boundary", "evidenceRefs"})
    for index, owner in enumerate(owners):
        path = f"owners[{index}]"; string(owner["name"], f"{path}.name")
        enum(owner["status"], f"{path}.status", {"resolved", "unresolved"}); string(owner["boundary"], f"{path}.boundary")
        strings(owner["evidenceRefs"], f"{path}.evidenceRefs")

    authorities, authority_by = collection(doc, "authorities", {"id", "ownerRef", "kind", "boundary", "status", "authorizedPrincipalRefs", "evidenceRefs"})
    for index, authority in enumerate(authorities):
        path = f"authorities[{index}]"; identifier(authority["ownerRef"], f"{path}.ownerRef")
        enum(authority["kind"], f"{path}.kind", AUTHORITY_KINDS); string(authority["boundary"], f"{path}.boundary")
        enum(authority["status"], f"{path}.status", {"established", "unresolved"}); strings(authority["evidenceRefs"], f"{path}.evidenceRefs")
        authorized_principals = strings(authority["authorizedPrincipalRefs"], f"{path}.authorizedPrincipalRefs")
        refs([authority["ownerRef"]], set(owner_by), f"{path}.ownerRef")
        refs(authorized_principals, set(owner_by), f"{path}.authorizedPrincipalRefs")

    operations, operation_by = collection(doc, "operations", {"id", "kind", "executionClass", "invocationBinding", "purpose", "consumer", "credentialRequirements", "requiredReceiptRefs", "producedReceiptRefs", "requiredAuthorityRefs", "requiredResourceRuleRefs", "requiredPrivacyRuleRefs"}, {"executionBoundary"})
    deferred_boundary_receipt_refs: list[tuple[list[str], str]] = []
    deferred_coverage_roles: list[dict[str, Any]] = []
    deferred_attempt_bindings: list[dict[str, Any]] = []
    deferred_exclusion_roles: list[dict[str, Any]] = []
    deferred_evidence_authority_anchors: list[dict[str, Any]] = []
    declared_shared_exclusions: dict[str, dict[str, dict[str, Any]]] = {}
    for index, operation in enumerate(operations):
        path = f"operations[{index}]"; enum(operation["kind"], f"{path}.kind", OP_KINDS)
        execution_class = enum(operation["executionClass"], f"{path}.executionClass", EXECUTION_CLASSES)
        binding = operation["invocationBinding"]
        if binding is not None:
            binding = obj(binding, f"{path}.invocationBinding", {"principalRef", "authorityRef"})
            identifier(binding["principalRef"], f"{path}.invocationBinding.principalRef")
            identifier(binding["authorityRef"], f"{path}.invocationBinding.authorityRef")
        if execution_class == "source-only" and operation["kind"] != "local-preparation":
            fail("EXECUTION_CLASS_KIND_MISMATCH", f"{path}.executionClass", "source-only is valid only for local-preparation")
        if execution_class == "source-only" and binding is not None:
            fail("SOURCE_ONLY_INVOCATION_BINDING", f"{path}.invocationBinding", "source-only operation must not declare a runtime invocation binding")
        boundary = operation.get("executionBoundary")
        if boundary is not None:
            boundary = obj(boundary, f"{path}.executionBoundary", {
                "status", "unresolvedReason",
                "baselinePlatformIdentity", "baselineCapabilities", "operationPlatformIdentity", "operationCapabilities",
                "platformMediation", "technicalVisibilityFacts", "authoritySemantics", "outputCustody",
                "campaignConvention", "leastPrivilegeAlternative", "delegatedPrimitives", "delegatedExecutors", "sharedExclusions",
            })
            boundary_status = enum(boundary["status"], f"{path}.executionBoundary.status", {"established", "unresolved"})
            unresolved_reason = string(boundary["unresolvedReason"], f"{path}.executionBoundary.unresolvedReason", nullable=True)
            if boundary_status == "unresolved" and unresolved_reason is None:
                fail("EXECUTION_BOUNDARY_REASON_REQUIRED", f"{path}.executionBoundary.unresolvedReason", "unresolved execution boundary requires a reason")
            if boundary_status == "established" and unresolved_reason is not None:
                fail("EXECUTION_BOUNDARY_REASON_UNEXPECTED", f"{path}.executionBoundary.unresolvedReason", "established execution boundary must not retain an unresolved reason")
            baseline_identity = string(boundary["baselinePlatformIdentity"], f"{path}.executionBoundary.baselinePlatformIdentity")
            baseline_capabilities = strings(boundary["baselineCapabilities"], f"{path}.executionBoundary.baselineCapabilities")
            operation_identity = string(boundary["operationPlatformIdentity"], f"{path}.executionBoundary.operationPlatformIdentity")
            operation_capabilities = strings(boundary["operationCapabilities"], f"{path}.executionBoundary.operationCapabilities")
            string(boundary["platformMediation"], f"{path}.executionBoundary.platformMediation")

            primitives: dict[str, dict[str, Any]] = {}
            if not isinstance(boundary["delegatedPrimitives"], list):
                fail("TYPE_ARRAY", f"{path}.executionBoundary.delegatedPrimitives", "must be an array")
            for primitive_index, primitive_value in enumerate(boundary["delegatedPrimitives"]):
                primitive_path = f"{path}.executionBoundary.delegatedPrimitives[{primitive_index}]"
                primitive = obj(primitive_value, primitive_path, {
                    "id", "identity", "command", "invokingPlatformPrincipal",
                    "executionPlatformIdentity", "requiredCapabilities", "interfaces",
                    "coverage", "onIncomplete", "receiptRefs",
                })
                primitive_id = identifier(primitive["id"], f"{primitive_path}.id")
                if primitive_id in primitives:
                    fail("DUPLICATE_ID", f"{primitive_path}.id", f"duplicate delegated primitive id: {primitive_id}")
                primitives[primitive_id] = primitive
                identity = validate_mechanism_identity(primitive["identity"], f"{primitive_path}.identity", PRIMITIVE_IDENTITY_KINDS)
                refs([identity["sourceRef"]], set(source_by), f"{primitive_path}.identity.sourceRef")
                if source_by[identity["sourceRef"]]["status"] != "pinned":
                    fail("EXECUTION_BOUNDARY_PRIMITIVE_SOURCE_UNPINNED", f"{primitive_path}.identity.sourceRef", "primitive identity source must be pinned")
                command = primitive["command"]
                if command is not None:
                    strings(command, f"{primitive_path}.command", nonempty=True)
                if identity["kind"] != "service-endpoint" and command is None:
                    fail("EXECUTION_BOUNDARY_PRIMITIVE_COMMAND", f"{primitive_path}.command", "local delegated primitive requires an exact argv command")
                if identity["kind"] == "digest" and command is not None and command[0] != identity["reference"]:
                    fail("EXECUTION_BOUNDARY_PRIMITIVE_IDENTITY", f"{primitive_path}.command", "digest-bound command must execute the exact identity reference")
                invoking_principal = string(primitive["invokingPlatformPrincipal"], f"{primitive_path}.invokingPlatformPrincipal")
                if invoking_principal != baseline_identity:
                    fail("EXECUTION_BOUNDARY_PRIMITIVE_PRINCIPAL_MISMATCH", f"{primitive_path}.invokingPlatformPrincipal", "delegated primitive must be invoked by the operation baseline platform principal")
                string(primitive["executionPlatformIdentity"], f"{primitive_path}.executionPlatformIdentity")
                strings(primitive["requiredCapabilities"], f"{primitive_path}.requiredCapabilities")
                strings(primitive["interfaces"], f"{primitive_path}.interfaces", nonempty=True)
                primitive_coverage = validate_observation_coverage(primitive["coverage"], f"{primitive_path}.coverage")
                deferred_boundary_receipt_refs.append((primitive_coverage["bindingReceiptRefs"], f"{primitive_path}.coverage.bindingReceiptRefs"))
                enum(primitive["onIncomplete"], f"{primitive_path}.onIncomplete", {"refuse"})
                primitive_receipts = strings(primitive["receiptRefs"], f"{primitive_path}.receiptRefs", nonempty=True)
                deferred_boundary_receipt_refs.append((primitive_receipts, f"{primitive_path}.receiptRefs"))

            executors: dict[str, dict[str, Any]] = {}
            if not isinstance(boundary["delegatedExecutors"], list):
                fail("TYPE_ARRAY", f"{path}.executionBoundary.delegatedExecutors", "must be an array")
            for executor_index, executor_value in enumerate(boundary["delegatedExecutors"]):
                executor_path = f"{path}.executionBoundary.delegatedExecutors[{executor_index}]"
                executor = obj(executor_value, executor_path, {
                    "id", "identity", "command", "invokingPlatformPrincipal", "executionPlatformIdentity",
                    "requiredCapabilities", "authorityRef", "operationRef", "onFailure", "receiptRefs",
                })
                executor_id = identifier(executor["id"], f"{executor_path}.id")
                if executor_id in executors:
                    fail("DUPLICATE_ID", f"{executor_path}.id", f"duplicate delegated executor id: {executor_id}")
                executors[executor_id] = executor
                identity = validate_mechanism_identity(executor["identity"], f"{executor_path}.identity", PRIMITIVE_IDENTITY_KINDS)
                refs([identity["sourceRef"]], set(source_by), f"{executor_path}.identity.sourceRef")
                if source_by[identity["sourceRef"]]["status"] != "pinned":
                    fail("EXECUTION_BOUNDARY_EXECUTOR_SOURCE_UNPINNED", f"{executor_path}.identity.sourceRef", "executor identity source must be pinned")
                command = executor["command"]
                if command is not None:
                    strings(command, f"{executor_path}.command", nonempty=True)
                if identity["kind"] != "service-endpoint" and command is None:
                    fail("EXECUTION_BOUNDARY_EXECUTOR_COMMAND", f"{executor_path}.command", "local delegated executor requires exact argv")
                if identity["kind"] == "digest" and command is not None and command[0] != identity["reference"]:
                    fail("EXECUTION_BOUNDARY_EXECUTOR_IDENTITY", f"{executor_path}.command", "digest-bound executor must execute the exact identity reference")
                if string(executor["invokingPlatformPrincipal"], f"{executor_path}.invokingPlatformPrincipal") != baseline_identity:
                    fail("EXECUTION_BOUNDARY_EXECUTOR_PRINCIPAL_MISMATCH", f"{executor_path}.invokingPlatformPrincipal", "delegated executor must be invoked by the operation baseline principal")
                string(executor["executionPlatformIdentity"], f"{executor_path}.executionPlatformIdentity")
                strings(executor["requiredCapabilities"], f"{executor_path}.requiredCapabilities")
                authority_ref = identifier(executor["authorityRef"], f"{executor_path}.authorityRef")
                refs([authority_ref], set(authority_by), f"{executor_path}.authorityRef")
                if authority_ref not in operation["requiredAuthorityRefs"]:
                    fail("EXECUTION_BOUNDARY_EXECUTOR_AUTHORITY", f"{executor_path}.authorityRef", "delegated executor authority must be required by the operation")
                if authority_by[authority_ref]["kind"] != EFFECT_AUTHORITY_KINDS.get(operation["kind"]):
                    fail("EXECUTION_BOUNDARY_EXECUTOR_AUTHORITY", f"{executor_path}.authorityRef", "delegated executor requires the operation's exact effect-authority kind")
                if identifier(executor["operationRef"], f"{executor_path}.operationRef") != operation["id"]:
                    fail("EXECUTION_BOUNDARY_EXECUTOR_OPERATION", f"{executor_path}.operationRef", "delegated executor must bind the current operation")
                enum(executor["onFailure"], f"{executor_path}.onFailure", {"refuse", "indeterminate"})
                executor_receipts = strings(executor["receiptRefs"], f"{executor_path}.receiptRefs", nonempty=True)
                deferred_boundary_receipt_refs.append((executor_receipts, f"{executor_path}.receiptRefs"))
                if not set(executor_receipts) <= set(operation["producedReceiptRefs"]):
                    fail("EXECUTION_BOUNDARY_EXECUTOR_RECEIPT_MISMATCH", f"{executor_path}.receiptRefs", "delegated executor receipts must be outputs of the bound operation")
                if operation["kind"] not in EFFECT_AUTHORITY_KINDS:
                    fail("EXECUTION_BOUNDARY_EXECUTOR_UNEXPECTED", executor_path, "delegated executors are valid only for effect operations")

            exclusions: dict[str, dict[str, Any]] = {}
            if not isinstance(boundary["sharedExclusions"], list):
                fail("TYPE_ARRAY", f"{path}.executionBoundary.sharedExclusions", "must be an array")
            for exclusion_index, exclusion_value in enumerate(boundary["sharedExclusions"]):
                exclusion_path = f"{path}.executionBoundary.sharedExclusions[{exclusion_index}]"
                exclusion = obj(exclusion_value, exclusion_path, {
                    "id", "mechanismIdentity", "attemptBinding", "ownerRef", "relevantOperationRefs",
                    "honoringOperationRefs", "acquisition", "hold", "handoff", "release",
                })
                exclusion_id = identifier(exclusion["id"], f"{exclusion_path}.id")
                if exclusion_id in exclusions:
                    fail("DUPLICATE_ID", f"{exclusion_path}.id", f"duplicate shared exclusion id: {exclusion_id}")
                exclusions[exclusion_id] = exclusion
                mechanism_identity = validate_mechanism_identity(exclusion["mechanismIdentity"], f"{exclusion_path}.mechanismIdentity", SHARED_EXCLUSION_KINDS)
                refs([mechanism_identity["sourceRef"]], set(source_by), f"{exclusion_path}.mechanismIdentity.sourceRef")
                if source_by[mechanism_identity["sourceRef"]]["status"] != "pinned":
                    fail("EXECUTION_BOUNDARY_EXCLUSION_SOURCE_UNPINNED", f"{exclusion_path}.mechanismIdentity.sourceRef", "shared exclusion identity source must be pinned")
                exclusion_owner = identifier(exclusion["ownerRef"], f"{exclusion_path}.ownerRef")
                refs([exclusion_owner], set(owner_by), f"{exclusion_path}.ownerRef")
                relevant = strings(exclusion["relevantOperationRefs"], f"{exclusion_path}.relevantOperationRefs", nonempty=True)
                honoring = strings(exclusion["honoringOperationRefs"], f"{exclusion_path}.honoringOperationRefs", nonempty=True)
                refs(relevant + honoring, set(operation_by), exclusion_path)
                if set(relevant) != set(honoring):
                    fail("EXECUTION_BOUNDARY_EXCLUSION_PARTICIPATION", f"{exclusion_path}.honoringOperationRefs", "every relevant producer operation must honor the same exclusion")
                attempt = obj(exclusion["attemptBinding"], f"{exclusion_path}.attemptBinding", {
                    "id", "operationRef", "supervisorOwnerRef", "identitySourceRef", "identityPin", "receiptRef",
                    "issuerOwnerRef", "issuerAuthorityRef", "authorityEvidenceReceiptRef",
                })
                attempt_id = identifier(attempt["id"], f"{exclusion_path}.attemptBinding.id")
                attempt_operation = identifier(attempt["operationRef"], f"{exclusion_path}.attemptBinding.operationRef")
                refs([attempt_operation], set(operation_by), f"{exclusion_path}.attemptBinding.operationRef")
                if attempt_operation not in relevant or operation_by[attempt_operation]["executionClass"] != "runtime" or operation_by[attempt_operation]["kind"] not in EFFECT_AUTHORITY_KINDS:
                    fail("EXECUTION_BOUNDARY_ATTEMPT_OPERATION", f"{exclusion_path}.attemptBinding.operationRef", "attempt must bind one relevant runtime effect operation")
                supervisor_owner = identifier(attempt["supervisorOwnerRef"], f"{exclusion_path}.attemptBinding.supervisorOwnerRef")
                refs([supervisor_owner], set(owner_by), f"{exclusion_path}.attemptBinding.supervisorOwnerRef")
                attempt_source = identifier(attempt["identitySourceRef"], f"{exclusion_path}.attemptBinding.identitySourceRef")
                refs([attempt_source], set(source_by), f"{exclusion_path}.attemptBinding.identitySourceRef")
                if source_by[attempt_source]["status"] != "pinned":
                    fail("EXECUTION_BOUNDARY_ATTEMPT_SOURCE_UNPINNED", f"{exclusion_path}.attemptBinding.identitySourceRef", "attempt identity source must be pinned")
                attempt_pin = string(attempt["identityPin"], f"{exclusion_path}.attemptBinding.identityPin")
                if not re.fullmatch(r"sha256:[0-9a-f]{64}", attempt_pin):
                    fail("EXECUTION_BOUNDARY_ATTEMPT_IDENTITY", f"{exclusion_path}.attemptBinding.identityPin", "attempt identity requires an exact lowercase sha256 pin")
                attempt_receipt = identifier(attempt["receiptRef"], f"{exclusion_path}.attemptBinding.receiptRef")
                deferred_boundary_receipt_refs.append(([attempt_receipt], f"{exclusion_path}.attemptBinding.receiptRef"))
                attempt_issuer_owner = identifier(attempt["issuerOwnerRef"], f"{exclusion_path}.attemptBinding.issuerOwnerRef")
                attempt_issuer_authority = identifier(attempt["issuerAuthorityRef"], f"{exclusion_path}.attemptBinding.issuerAuthorityRef")
                attempt_authority_evidence = identifier(attempt["authorityEvidenceReceiptRef"], f"{exclusion_path}.attemptBinding.authorityEvidenceReceiptRef")
                refs([attempt_issuer_owner], set(owner_by), f"{exclusion_path}.attemptBinding.issuerOwnerRef")
                refs([attempt_issuer_authority], set(authority_by), f"{exclusion_path}.attemptBinding.issuerAuthorityRef")
                if authority_by[attempt_issuer_authority]["kind"] != "acceptance" or authority_by[attempt_issuer_authority]["status"] != "established" or authority_by[attempt_issuer_authority]["ownerRef"] != attempt_issuer_owner:
                    fail("EXECUTION_BOUNDARY_EVIDENCE_AUTHORITY_MISMATCH", f"{exclusion_path}.attemptBinding.issuerAuthorityRef", "attempt evidence requires the exact established acceptance authority owned by its expected issuer")
                if attempt_authority_evidence not in authority_by[attempt_issuer_authority]["evidenceRefs"]:
                    fail("EXECUTION_BOUNDARY_EVIDENCE_AUTHORITY_UNANCHORED", f"{exclusion_path}.attemptBinding.authorityEvidenceReceiptRef", "expected attempt authority must reference the exact external authority evidence receipt")
                deferred_boundary_receipt_refs.append(([attempt_authority_evidence], f"{exclusion_path}.attemptBinding.authorityEvidenceReceiptRef"))
                deferred_evidence_authority_anchors.append({
                    "receiptRef": attempt_receipt, "issuerOwnerRef": attempt_issuer_owner,
                    "issuerAuthorityRef": attempt_issuer_authority,
                    "authorityEvidenceReceiptRef": attempt_authority_evidence, "phase": "attempt",
                })
                deferred_attempt_bindings.append({
                    "receiptRef": attempt_receipt, "bindingRef": attempt_id, "operationRef": attempt_operation,
                    "supervisorOwnerRef": supervisor_owner, "identitySourceRef": attempt_source,
                    "identityPin": attempt_pin, "producerOperationRefs": relevant,
                })
                phase_receipt_by_name: dict[str, str] = {}
                phase_specs = (
                    ("acquisition", {"before-observation", "before-dispatch"}, "current-input", "current-accepted"),
                    ("hold", {"through-dispatch-handoff", "through-attempt-terminal"}, "current-input", "current-accepted"),
                    ("handoff", {"to-declared-operation"}, "future-output", "owed"),
                    ("release", {"after-dispatch-handoff", "after-attempt-terminal", "on-refusal-before-dispatch"}, "future-output", "owed"),
                )
                for ordinal, (phase, allowed, required_direction, required_availability) in enumerate(phase_specs):
                    required_fields = {"predicate", "receiptRef", "direction", "availability", "predecessorReceiptRef"}
                    if required_direction == "current-input":
                        required_fields.update({"issuerOwnerRef", "issuerAuthorityRef", "authorityEvidenceReceiptRef"})
                    if phase == "handoff":
                        required_fields.add("targetOperationRef")
                    phase_value = obj(exclusion[phase], f"{exclusion_path}.{phase}", required_fields)
                    enum(phase_value["predicate"], f"{exclusion_path}.{phase}.predicate", allowed)
                    enum(phase_value["direction"], f"{exclusion_path}.{phase}.direction", {required_direction})
                    enum(phase_value["availability"], f"{exclusion_path}.{phase}.availability", {required_availability})
                    if phase == "handoff":
                        target = identifier(phase_value["targetOperationRef"], f"{exclusion_path}.handoff.targetOperationRef")
                        refs([target], set(operation_by), f"{exclusion_path}.handoff.targetOperationRef")
                        if target != attempt_operation:
                            fail("EXECUTION_BOUNDARY_EXCLUSION_HANDOFF_TARGET", f"{exclusion_path}.handoff.targetOperationRef", "handoff must target the exact relevant runtime effect operation bound to the attempt")
                    phase_receipt = identifier(phase_value["receiptRef"], f"{exclusion_path}.{phase}.receiptRef")
                    expected_predecessor = None if phase == "acquisition" else phase_receipt_by_name[phase_specs[ordinal - 1][0]]
                    predecessor = string(phase_value["predecessorReceiptRef"], f"{exclusion_path}.{phase}.predecessorReceiptRef", nullable=True)
                    if predecessor != expected_predecessor:
                        fail("EXECUTION_BOUNDARY_EXCLUSION_ORDER", f"{exclusion_path}.{phase}.predecessorReceiptRef", "phase must reference the exact immediately preceding phase receipt")
                    phase_receipt_by_name[phase] = phase_receipt
                    deferred_boundary_receipt_refs.append(([phase_receipt], f"{exclusion_path}.{phase}.receiptRef"))
                    if required_direction == "current-input":
                        expected_issuer_owner = identifier(phase_value["issuerOwnerRef"], f"{exclusion_path}.{phase}.issuerOwnerRef")
                        expected_issuer_authority = identifier(phase_value["issuerAuthorityRef"], f"{exclusion_path}.{phase}.issuerAuthorityRef")
                        authority_evidence = identifier(phase_value["authorityEvidenceReceiptRef"], f"{exclusion_path}.{phase}.authorityEvidenceReceiptRef")
                        refs([expected_issuer_owner], set(owner_by), f"{exclusion_path}.{phase}.issuerOwnerRef")
                        refs([expected_issuer_authority], set(authority_by), f"{exclusion_path}.{phase}.issuerAuthorityRef")
                        if authority_by[expected_issuer_authority]["kind"] != "acceptance" or authority_by[expected_issuer_authority]["status"] != "established" or authority_by[expected_issuer_authority]["ownerRef"] != expected_issuer_owner:
                            fail("EXECUTION_BOUNDARY_EVIDENCE_AUTHORITY_MISMATCH", f"{exclusion_path}.{phase}.issuerAuthorityRef", f"{phase} evidence requires the exact established acceptance authority owned by its expected issuer")
                        if authority_evidence not in authority_by[expected_issuer_authority]["evidenceRefs"]:
                            fail("EXECUTION_BOUNDARY_EVIDENCE_AUTHORITY_UNANCHORED", f"{exclusion_path}.{phase}.authorityEvidenceReceiptRef", f"expected {phase} authority must reference the exact external authority evidence receipt")
                        deferred_boundary_receipt_refs.append(([authority_evidence], f"{exclusion_path}.{phase}.authorityEvidenceReceiptRef"))
                        deferred_evidence_authority_anchors.append({
                            "receiptRef": phase_receipt, "issuerOwnerRef": expected_issuer_owner,
                            "issuerAuthorityRef": expected_issuer_authority,
                            "authorityEvidenceReceiptRef": authority_evidence, "phase": phase,
                        })
                    producer_kind = "owner" if required_direction == "current-input" else "operation"
                    producer_ref = supervisor_owner if producer_kind == "owner" else attempt_operation
                    deferred_exclusion_roles.append({
                        "receiptRef": phase_receipt, "phase": phase, "mechanismRef": exclusion_id,
                        "mechanismIdentityPin": mechanism_identity["identityPin"],
                        "attemptBindingRef": attempt_id, "attemptIdentityPin": attempt_pin, "ownerRef": exclusion_owner,
                        "producerOperationRefs": relevant, "phaseOrdinal": ordinal,
                        "predecessorReceiptRef": predecessor, "direction": required_direction,
                        "availability": required_availability, "producerKind": producer_kind,
                        "producerRef": producer_ref, "attemptOperationRef": attempt_operation,
                        "predicate": phase_value["predicate"],
                    })
                all_lifecycle_receipts = [attempt_receipt, *phase_receipt_by_name.values()]
                if len(set(all_lifecycle_receipts)) != len(all_lifecycle_receipts):
                    fail("EXECUTION_BOUNDARY_EXCLUSION_RECEIPT_REUSE", exclusion_path, "attempt and lifecycle phases require distinct receipt identities")

            if not isinstance(boundary["technicalVisibilityFacts"], list) or not boundary["technicalVisibilityFacts"]:
                fail("TYPE_ARRAY", f"{path}.executionBoundary.technicalVisibilityFacts", "must be an array with at least one load-bearing fact")
            fact_ids: set[str] = set()
            requires_delegation = False
            used_primitives: set[str] = set()
            used_exclusions: set[str] = set()
            for fact_index, value in enumerate(boundary["technicalVisibilityFacts"]):
                fact_path = f"{path}.executionBoundary.technicalVisibilityFacts[{fact_index}]"
                fact = obj(value, fact_path, {
                    "id", "fact", "interfaces", "requiredPlatformIdentity", "requiredCapabilities",
                    "visibilityPurpose", "claimKind", "coverage",
                    "delegatedPrimitiveRef", "temporalScope", "sharedExclusionRef",
                    "establishesExclusion", "onIncomplete",
                    "downstreamReceiptRefs", "downstreamClaim",
                })
                fact_id = identifier(fact["id"], f"{fact_path}.id")
                if fact_id in fact_ids:
                    fail("DUPLICATE_ID", f"{fact_path}.id", f"duplicate technical visibility fact id: {fact_id}")
                fact_ids.add(fact_id)
                string(fact["fact"], f"{fact_path}.fact")
                fact_interfaces = strings(fact["interfaces"], f"{fact_path}.interfaces", nonempty=True)
                enum(fact["visibilityPurpose"], f"{fact_path}.visibilityPurpose", {"observation-input"})
                claim_kind = enum(fact["claimKind"], f"{fact_path}.claimKind", OBSERVATION_CLAIM_KINDS)
                fact_identity = string(fact["requiredPlatformIdentity"], f"{fact_path}.requiredPlatformIdentity")
                fact_capabilities = strings(fact["requiredCapabilities"], f"{fact_path}.requiredCapabilities")
                fact_coverage = validate_observation_coverage(fact["coverage"], f"{fact_path}.coverage")
                deferred_boundary_receipt_refs.append((fact_coverage["bindingReceiptRefs"], f"{fact_path}.coverage.bindingReceiptRefs"))
                if claim_kind == "producer-absence" and fact_coverage["kind"] != "all-owner-uid-processes":
                    fail("EXECUTION_BOUNDARY_COVERAGE_MISMATCH", f"{fact_path}.coverage.kind", "producer-absence requires complete all-owner-UID process coverage")
                primitive_ref = string(fact["delegatedPrimitiveRef"], f"{fact_path}.delegatedPrimitiveRef", nullable=True)
                fact_needs_delegate = fact_identity != operation_identity or not set(fact_capabilities) <= set(operation_capabilities)
                requires_delegation = requires_delegation or fact_needs_delegate
                if primitive_ref is None and fact_needs_delegate:
                    fail("EXECUTION_BOUNDARY_PRIMITIVE_MISSING", f"{fact_path}.delegatedPrimitiveRef", "fact outside the main operation boundary requires a structured delegated primitive")
                if primitive_ref is not None:
                    if primitive_ref not in primitives:
                        fail("REFERENCE_DANGLING", f"{fact_path}.delegatedPrimitiveRef", f"unknown delegated primitive: {primitive_ref}")
                    used_primitives.add(primitive_ref)
                    primitive = primitives[primitive_ref]
                    if primitive["executionPlatformIdentity"] != fact_identity:
                        fail("EXECUTION_BOUNDARY_PRIMITIVE_IDENTITY_MISMATCH", f"{fact_path}.requiredPlatformIdentity", "fact and delegated primitive platform identities differ")
                    if set(fact_capabilities) != set(primitive["requiredCapabilities"]):
                        fail("EXECUTION_BOUNDARY_PRIMITIVE_CAPABILITY_MISMATCH", f"{fact_path}.requiredCapabilities", "fact and delegated primitive capabilities differ")
                    if not set(fact_interfaces) <= set(primitive["interfaces"]):
                        fail("EXECUTION_BOUNDARY_PRIMITIVE_INTERFACE_MISMATCH", f"{fact_path}.interfaces", "fact interfaces are not covered by the delegated primitive")
                    if fact_coverage != primitive["coverage"]:
                        fail("EXECUTION_BOUNDARY_PRIMITIVE_COVERAGE_MISMATCH", f"{fact_path}.coverage", "fact and delegated primitive coverage differ")
                    if not set(fact_coverage["bindingReceiptRefs"]) <= set(primitive["receiptRefs"]):
                        fail("EXECUTION_BOUNDARY_COVERAGE_BINDING", f"{fact_path}.coverage.bindingReceiptRefs", "coverage domain bindings must be emitted by the delegated primitive")
                if fact_coverage["kind"] == "all-owner-uid-processes":
                    if primitive_ref is None:
                        fail("EXECUTION_BOUNDARY_COVERAGE_PRIMITIVE", f"{fact_path}.delegatedPrimitiveRef", "all-owner-UID coverage requires an exact delegated census primitive")
                    primitive = primitives[primitive_ref]
                    for receipt_ref in fact_coverage["bindingReceiptRefs"]:
                        deferred_coverage_roles.append({
                            "receiptRef": receipt_ref, "operationRef": operation["id"],
                            "factRef": fact_id, "primitiveRef": primitive_ref,
                            "primitiveIdentityPin": primitive["identity"]["identityPin"],
                            "coverageKind": fact_coverage["kind"],
                            "population": fact_coverage["population"],
                            "completeness": fact_coverage["completeness"],
                            "namespaceScope": fact_coverage["namespaceScope"],
                        })
                temporal_scope = enum(fact["temporalScope"], f"{fact_path}.temporalScope", {"point-in-time", "continuous-observation", "reserved-through-dispatch"})
                exclusion_ref = string(fact["sharedExclusionRef"], f"{fact_path}.sharedExclusionRef", nullable=True)
                establishes_exclusion = boolean(fact["establishesExclusion"], f"{fact_path}.establishesExclusion")
                if temporal_scope == "reserved-through-dispatch" and exclusion_ref is None:
                    fail("EXECUTION_BOUNDARY_EXCLUSION_MISSING", f"{fact_path}.sharedExclusionRef", "a reservation claim requires a structured shared exclusion")
                if temporal_scope != "reserved-through-dispatch" and exclusion_ref is not None:
                    fail("EXECUTION_BOUNDARY_EXCLUSION_UNEXPECTED", f"{fact_path}.sharedExclusionRef", "point-in-time or continuous observation must not imply producer-slot reservation")
                if establishes_exclusion != (temporal_scope == "reserved-through-dispatch"):
                    fail("EXECUTION_BOUNDARY_TEMPORAL_OVERCLAIM", f"{fact_path}.establishesExclusion", "only a reserved-through-dispatch fact with a structured shared exclusion can establish exclusion")
                if exclusion_ref is not None:
                    if exclusion_ref not in exclusions:
                        fail("REFERENCE_DANGLING", f"{fact_path}.sharedExclusionRef", f"unknown shared exclusion: {exclusion_ref}")
                    used_exclusions.add(exclusion_ref)
                    if operation["id"] not in exclusions[exclusion_ref]["relevantOperationRefs"]:
                        fail("EXECUTION_BOUNDARY_EXCLUSION_SCOPE", f"{fact_path}.sharedExclusionRef", "current operation is outside the shared exclusion producer scope")
                    if temporal_scope == "reserved-through-dispatch" and exclusions[exclusion_ref]["acquisition"]["predicate"] != "before-observation":
                        fail("EXECUTION_BOUNDARY_EXCLUSION_OBSERVATION_ORDER", f"{fact_path}.sharedExclusionRef", "reserved-through-dispatch requires acquisition before the load-bearing observation")
                enum(fact["onIncomplete"], f"{fact_path}.onIncomplete", {"refuse"})
                fact_receipts = strings(fact["downstreamReceiptRefs"], f"{fact_path}.downstreamReceiptRefs", nonempty=True)
                deferred_boundary_receipt_refs.append((fact_receipts, f"{fact_path}.downstreamReceiptRefs"))
                if not set(fact_coverage["bindingReceiptRefs"]) <= set(fact_receipts):
                    fail("EXECUTION_BOUNDARY_COVERAGE_BINDING", f"{fact_path}.coverage.bindingReceiptRefs", "coverage domain bindings must be included in the fact's downstream receipts")
                if primitive_ref is not None and not set(fact_receipts) <= set(primitives[primitive_ref]["receiptRefs"]):
                    fail("EXECUTION_BOUNDARY_PRIMITIVE_RECEIPT_MISMATCH", f"{fact_path}.downstreamReceiptRefs", "fact receipts are not bound by the delegated primitive")
                string(fact["downstreamClaim"], f"{fact_path}.downstreamClaim")

            if set(primitives) != used_primitives:
                fail("EXECUTION_BOUNDARY_PRIMITIVE_UNUSED", f"{path}.executionBoundary.delegatedPrimitives", "every declared delegated primitive must support a technical visibility fact")
            if set(exclusions) != used_exclusions:
                fail("EXECUTION_BOUNDARY_EXCLUSION_UNUSED", f"{path}.executionBoundary.sharedExclusions", "every declared shared exclusion must support a reserved-through-dispatch fact")
            declared_shared_exclusions[operation["id"]] = exclusions

            semantics = obj(boundary["authoritySemantics"], f"{path}.executionBoundary.authoritySemantics", {
                "principalRef", "authorityRef", "platformIdentityConveysAuthority",
            })
            semantics_principal = string(semantics["principalRef"], f"{path}.executionBoundary.authoritySemantics.principalRef", nullable=True)
            semantics_authority = string(semantics["authorityRef"], f"{path}.executionBoundary.authoritySemantics.authorityRef", nullable=True)
            if semantics_principal is not None:
                identifier(semantics_principal, f"{path}.executionBoundary.authoritySemantics.principalRef")
            if semantics_authority is not None:
                identifier(semantics_authority, f"{path}.executionBoundary.authoritySemantics.authorityRef")
            if boundary_status == "established" and (semantics_principal is None or semantics_authority is None):
                fail("EXECUTION_BOUNDARY_AUTHORITY_UNRESOLVED", f"{path}.executionBoundary.authoritySemantics", "established execution boundary requires resolved logical principal and authority references")
            if boolean(semantics["platformIdentityConveysAuthority"], f"{path}.executionBoundary.authoritySemantics.platformIdentityConveysAuthority"):
                fail("EXECUTION_BOUNDARY_AUTHORITY_COLLAPSE", f"{path}.executionBoundary.authoritySemantics.platformIdentityConveysAuthority", "platform identity must not be treated as logical authority")

            custody = obj(boundary["outputCustody"], f"{path}.executionBoundary.outputCustody", {
                "writerIdentity", "ownerIdentity", "mode", "pathnameReplacementBoundary",
                "separatedFromObservationPrivilege", "justifiesOperationPrivilege", "receiptRefs", "claim",
            })
            for key in ("writerIdentity", "ownerIdentity", "mode", "pathnameReplacementBoundary", "claim"):
                string(custody[key], f"{path}.executionBoundary.outputCustody.{key}")
            if not boolean(custody["separatedFromObservationPrivilege"], f"{path}.executionBoundary.outputCustody.separatedFromObservationPrivilege"):
                fail("EXECUTION_BOUNDARY_CUSTODY_COLLAPSE", f"{path}.executionBoundary.outputCustody.separatedFromObservationPrivilege", "receipt custody must be declared independently from observation privilege")
            if boolean(custody["justifiesOperationPrivilege"], f"{path}.executionBoundary.outputCustody.justifiesOperationPrivilege"):
                fail("EXECUTION_BOUNDARY_CUSTODY_JUSTIFIES_PRIVILEGE", f"{path}.executionBoundary.outputCustody.justifiesOperationPrivilege", "receipt ownership or custody cannot justify observation privilege")
            custody_receipts = strings(custody["receiptRefs"], f"{path}.executionBoundary.outputCustody.receiptRefs", nonempty=True)
            deferred_boundary_receipt_refs.append((custody_receipts, f"{path}.executionBoundary.outputCustody.receiptRefs"))
            if operation_identity != baseline_identity and custody["writerIdentity"] == operation_identity:
                fail("EXECUTION_BOUNDARY_CUSTODY_JUSTIFIES_PRIVILEGE", f"{path}.executionBoundary.outputCustody.writerIdentity", "an elevated operation identity must not also be selected merely as the receipt writer")

            convention = obj(boundary["campaignConvention"], f"{path}.executionBoundary.campaignConvention", {
                "requirements", "establishesTechnicalRequirement",
            })
            strings(convention["requirements"], f"{path}.executionBoundary.campaignConvention.requirements")
            if boolean(convention["establishesTechnicalRequirement"], f"{path}.executionBoundary.campaignConvention.establishesTechnicalRequirement"):
                fail("EXECUTION_BOUNDARY_CONVENTION_AS_REQUIREMENT", f"{path}.executionBoundary.campaignConvention.establishesTechnicalRequirement", "campaign convention cannot establish a technical privilege requirement")

            alternative = obj(boundary["leastPrivilegeAlternative"], f"{path}.executionBoundary.leastPrivilegeAlternative", {
                "unprivilegedEquivalence", "description", "delegatedPrimitiveRefs", "broaderPrivilegeRefused",
            })
            equivalence = enum(alternative["unprivilegedEquivalence"], f"{path}.executionBoundary.leastPrivilegeAlternative.unprivilegedEquivalence", UNPRIVILEGED_EQUIVALENCE)
            string(alternative["description"], f"{path}.executionBoundary.leastPrivilegeAlternative.description")
            primitive_refs = strings(alternative["delegatedPrimitiveRefs"], f"{path}.executionBoundary.leastPrivilegeAlternative.delegatedPrimitiveRefs")
            if not boolean(alternative["broaderPrivilegeRefused"], f"{path}.executionBoundary.leastPrivilegeAlternative.broaderPrivilegeRefused"):
                fail("EXECUTION_BOUNDARY_BROAD_PRIVILEGE", f"{path}.executionBoundary.leastPrivilegeAlternative.broaderPrivilegeRefused", "the boundary must refuse broader privilege than the declared minimum")
            refs(primitive_refs, set(primitives), f"{path}.executionBoundary.leastPrivilegeAlternative.delegatedPrimitiveRefs")
            if equivalence == "delegated-primitive" and (not primitive_refs or set(primitive_refs) != used_primitives):
                fail("EXECUTION_BOUNDARY_PRIMITIVE_MISSING", f"{path}.executionBoundary.leastPrivilegeAlternative.delegatedPrimitiveRefs", "delegated-primitive equivalence requires every exact structured primitive")
            if equivalence != "delegated-primitive" and primitive_refs:
                fail("EXECUTION_BOUNDARY_PRIMITIVE_UNEXPECTED", f"{path}.executionBoundary.leastPrivilegeAlternative.delegatedPrimitiveRefs", "delegated primitive references are valid only with delegated-primitive equivalence")
            if equivalence in {"exact", "delegated-primitive"} and operation_identity != baseline_identity:
                fail("EXECUTION_BOUNDARY_OVERPRIVILEGED", f"{path}.executionBoundary.operationPlatformIdentity", "an unprivileged equivalent requires the operation to retain its baseline platform identity")
            if equivalence == "exact" and set(operation_capabilities) != set(baseline_capabilities):
                fail("EXECUTION_BOUNDARY_OVERPRIVILEGED", f"{path}.executionBoundary.operationCapabilities", "an exact baseline equivalent must not add operation capabilities")
            if equivalence == "exact" and requires_delegation:
                fail("EXECUTION_BOUNDARY_EQUIVALENCE_FALSE", f"{path}.executionBoundary.leastPrivilegeAlternative.unprivilegedEquivalence", "exact equivalence cannot satisfy a fact that requires a different platform identity or additional capability")
            if equivalence == "delegated-primitive" and (operation_identity != baseline_identity or set(operation_capabilities) != set(baseline_capabilities)):
                fail("EXECUTION_BOUNDARY_OVERPRIVILEGED", f"{path}.executionBoundary.operationPlatformIdentity", "when a bounded delegated primitive suffices, the main operation must retain its baseline identity and capabilities")
            if operation_identity != baseline_identity or set(operation_capabilities) != set(baseline_capabilities):
                fail("EXECUTION_BOUNDARY_OVERPRIVILEGED", f"{path}.executionBoundary.operationPlatformIdentity", "the operation must retain its baseline identity and capabilities; special mechanisms require a bounded primitive or authority-bound executor")
            if execution_class == "source-only":
                fail("SOURCE_ONLY_EXECUTION_BOUNDARY", f"{path}.executionBoundary", "source-only operation must not declare a runtime execution boundary")
        string(operation["purpose"], f"{path}.purpose"); consumer = string(operation["consumer"], f"{path}.consumer")
        if consumer not in consumers: fail("CONSUMER_UNKNOWN", f"{path}.consumer", "consumer is not an intended consumer")
        if not isinstance(operation["credentialRequirements"], list): fail("TYPE_ARRAY", f"{path}.credentialRequirements", "must be an array")
        for req_index, requirement in enumerate(operation["credentialRequirements"]):
            req_path = f"{path}.credentialRequirements[{req_index}]"
            req = obj(requirement, req_path, {"credentialRef", "purpose", "consumer", "requiredAuthorityRef"})
            for key in req: string(req[key], f"{req_path}.{key}")
        for key in ("requiredReceiptRefs", "producedReceiptRefs", "requiredAuthorityRefs", "requiredResourceRuleRefs", "requiredPrivacyRuleRefs"):
            strings(operation[key], f"{path}.{key}")
        if operation["kind"] in {"local-effect", "external-effect", "production-effect"} and not operation["requiredAuthorityRefs"]:
            fail("EFFECT_AUTHORITY_REQUIRED", f"{path}.requiredAuthorityRefs", "effect operation requires at least one explicit existing authority reference")

    for declaring_operation, exclusions in declared_shared_exclusions.items():
        for exclusion_id, exclusion in exclusions.items():
            for producer_id in exclusion["relevantOperationRefs"]:
                producer_exclusion = declared_shared_exclusions.get(producer_id, {}).get(exclusion_id)
                if producer_exclusion is None:
                    fail(
                        "EXECUTION_BOUNDARY_EXCLUSION_PRODUCER_MISSING",
                        f"operations.{declaring_operation}.executionBoundary.sharedExclusions.{exclusion_id}",
                        f"relevant producer {producer_id} does not declare and consume the shared exclusion",
                    )
                for key in ("mechanismIdentity", "attemptBinding", "ownerRef", "acquisition", "hold", "handoff", "release"):
                    if producer_exclusion[key] != exclusion[key]:
                        fail(
                            "EXECUTION_BOUNDARY_EXCLUSION_PRODUCER_MISMATCH",
                            f"operations.{producer_id}.executionBoundary.sharedExclusions.{exclusion_id}.{key}",
                            "all relevant producers must declare the same exclusion identity and lifecycle evidence",
                        )
                if set(producer_exclusion["relevantOperationRefs"]) != set(exclusion["relevantOperationRefs"]):
                    fail("EXECUTION_BOUNDARY_EXCLUSION_PRODUCER_MISMATCH", f"operations.{producer_id}.executionBoundary.sharedExclusions.{exclusion_id}.relevantOperationRefs", "all relevant producers must declare the same exact producer scope")

    gates, gate_by = collection(doc, "gates", {"id", "kind", "ownerRef", "status", "recordedDisposition", "requiredReceiptRefs", "blocks", "doesNotBlock", "timeBoundary"})
    for index, gate in enumerate(gates):
        path = f"gates[{index}]"; enum(gate["kind"], f"{path}.kind", GATE_KINDS); identifier(gate["ownerRef"], f"{path}.ownerRef")
        enum(gate["status"], f"{path}.status", {"satisfied", "unsatisfied", "unresolved"}); string(gate["recordedDisposition"], f"{path}.recordedDisposition")
        required = strings(gate["requiredReceiptRefs"], f"{path}.requiredReceiptRefs")
        blocks = strings(gate["blocks"], f"{path}.blocks", nonempty=True); no_blocks = strings(gate["doesNotBlock"], f"{path}.doesNotBlock")
        if set(blocks) & set(no_blocks): fail("GATE_SCOPE_CONTRADICTION", path, "blocks and doesNotBlock must be disjoint")
        refs(blocks + no_blocks, set(operation_by), path); refs([gate["ownerRef"]], set(owner_by), f"{path}.ownerRef")
        if set(blocks) | set(no_blocks) != set(operation_by): fail("GATE_SCOPE_INCOMPLETE", path, "blocks and doesNotBlock must explicitly partition all operations")
        if gate["status"] == "satisfied" and not required: fail("GATE_EVIDENCE_REQUIRED", f"{path}.requiredReceiptRefs", "satisfied gate requires receipt evidence")
        boundary = gate["timeBoundary"]
        if boundary is not None:
            boundary = obj(boundary, f"{path}.timeBoundary", {"notBefore", "clockContractRef", "assessment"})
            string(boundary["notBefore"], f"{path}.timeBoundary.notBefore"); string(boundary["clockContractRef"], f"{path}.timeBoundary.clockContractRef")
            enum(boundary["assessment"], f"{path}.timeBoundary.assessment", {"reached", "not-reached", "unresolved"})

    credentials, credential_by = collection(doc, "credentials", {"id", "purpose", "readiness", "scopeVerification", "authorizedConsumers", "authorizedPrincipalRefs", "authorityGrantedRefs", "authorityNotGrantedRefs", "evidenceRefs", "sourceRefs"})
    for index, credential in enumerate(credentials):
        path = f"credentials[{index}]"; string(credential["purpose"], f"{path}.purpose")
        enum(credential["readiness"], f"{path}.readiness", {"present", "absent", "unverified"})
        enum(credential["scopeVerification"], f"{path}.scopeVerification", {"verified", "unverified", "failed"})
        authorized = strings(credential["authorizedConsumers"], f"{path}.authorizedConsumers", nonempty=True); refs(authorized, consumers, f"{path}.authorizedConsumers")
        authorized_principals = strings(credential["authorizedPrincipalRefs"], f"{path}.authorizedPrincipalRefs")
        refs(authorized_principals, set(owner_by), f"{path}.authorizedPrincipalRefs")
        granted = strings(credential["authorityGrantedRefs"], f"{path}.authorityGrantedRefs"); denied = strings(credential["authorityNotGrantedRefs"], f"{path}.authorityNotGrantedRefs")
        if set(granted) & set(denied): fail("CREDENTIAL_AUTHORITY_CONTRADICTION", path, "granted and not-granted authority references must be disjoint")
        refs(granted + denied, set(authority_by), path); strings(credential["evidenceRefs"], f"{path}.evidenceRefs")
        refs(strings(credential["sourceRefs"], f"{path}.sourceRefs"), set(source_by), f"{path}.sourceRefs")

    receipts, receipt_by = collection(doc, "receipts", {"id", "schemaType", "issuerOwnerRef", "issuerAuthorityRef", "evidenceBasis", "evidenceBasisStatus", "artifactIdentity", "artifactIdentityStatus", "custody", "custodyStatus", "retention", "downstreamConsumers", "disposition"}, {"semanticRoles"})
    receipt_roles: dict[str, list[dict[str, Any]]] = {}
    for index, receipt in enumerate(receipts):
        path = f"receipts[{index}]"
        for key in ("schemaType", "evidenceBasis", "artifactIdentity", "custody", "retention"): string(receipt[key], f"{path}.{key}")
        identifier(receipt["issuerOwnerRef"], f"{path}.issuerOwnerRef"); refs([receipt["issuerOwnerRef"]], set(owner_by), f"{path}.issuerOwnerRef")
        issuer_authority = identifier(receipt["issuerAuthorityRef"], f"{path}.issuerAuthorityRef")
        refs([issuer_authority], set(authority_by), f"{path}.issuerAuthorityRef")
        if authority_by[issuer_authority]["kind"] != "acceptance":
            fail("RECEIPT_ISSUER_AUTHORITY_KIND", f"{path}.issuerAuthorityRef", "receipt issuer authority must have kind acceptance")
        if authority_by[issuer_authority]["ownerRef"] != receipt["issuerOwnerRef"]:
            fail("RECEIPT_ISSUER_AUTHORITY_OWNER_MISMATCH", f"{path}.issuerAuthorityRef", "receipt issuer authority must belong to issuerOwnerRef")
        fact_states = [
            enum(receipt["evidenceBasisStatus"], f"{path}.evidenceBasisStatus", RECEIPT_FACT_STATES),
            enum(receipt["artifactIdentityStatus"], f"{path}.artifactIdentityStatus", RECEIPT_FACT_STATES),
            enum(receipt["custodyStatus"], f"{path}.custodyStatus", RECEIPT_FACT_STATES),
        ]
        downstream = strings(receipt["downstreamConsumers"], f"{path}.downstreamConsumers"); refs(downstream, set(operation_by), f"{path}.downstreamConsumers")
        disposition = enum(receipt["disposition"], f"{path}.disposition", {"missing", "template", "retained-unverified", "externally-accepted", "failed"})
        if disposition == "externally-accepted" and any(state != "recorded" for state in fact_states):
            fail("RECEIPT_ACCEPTANCE_INCOMPLETE", path, "externally accepted receipt requires recorded basis, artifact identity and custody")
        if not isinstance(receipt.get("semanticRoles", []), list):
            fail("TYPE_ARRAY", f"{path}.semanticRoles", "must be an array")
        if len(receipt.get("semanticRoles", [])) > 1:
            fail("EXECUTION_BOUNDARY_EXCLUSION_ROLE_REUSE", f"{path}.semanticRoles", "one receipt may carry at most one execution-boundary semantic role")
        roles: list[dict[str, Any]] = []
        for role_index, role_value in enumerate(receipt.get("semanticRoles", [])):
            role_path = f"{path}.semanticRoles[{role_index}]"
            kind = string(role_value.get("kind") if isinstance(role_value, dict) else None, f"{role_path}.kind")
            if kind == "operation-attempt-binding":
                role = obj(role_value, role_path, {"kind", "bindingRef", "operationRef", "supervisorOwnerRef", "identitySourceRef", "identityPin"})
                identifier(role["bindingRef"], f"{role_path}.bindingRef")
                operation_ref = identifier(role["operationRef"], f"{role_path}.operationRef")
                refs([operation_ref], set(operation_by), f"{role_path}.operationRef")
                supervisor_ref = identifier(role["supervisorOwnerRef"], f"{role_path}.supervisorOwnerRef")
                refs([supervisor_ref], set(owner_by), f"{role_path}.supervisorOwnerRef")
                source_ref = identifier(role["identitySourceRef"], f"{role_path}.identitySourceRef")
                refs([source_ref], set(source_by), f"{role_path}.identitySourceRef")
                if not re.fullmatch(r"sha256:[0-9a-f]{64}", string(role["identityPin"], f"{role_path}.identityPin")):
                    fail("EXECUTION_BOUNDARY_ATTEMPT_IDENTITY", f"{role_path}.identityPin", "attempt role requires an exact lowercase sha256 pin")
            elif kind == "observation-coverage-domain":
                role = obj(role_value, role_path, {
                    "kind", "operationRef", "factRef", "primitiveRef", "primitiveIdentityPin",
                    "coverageKind", "population", "completeness", "namespaceScope",
                })
                operation_ref = identifier(role["operationRef"], f"{role_path}.operationRef")
                refs([operation_ref], set(operation_by), f"{role_path}.operationRef")
                identifier(role["factRef"], f"{role_path}.factRef")
                identifier(role["primitiveRef"], f"{role_path}.primitiveRef")
                if not re.fullmatch(r"(?:sha256|spki-sha256):[0-9a-f]{64}|service-id:[a-zA-Z0-9][a-zA-Z0-9._:/@+-]*", string(role["primitiveIdentityPin"], f"{role_path}.primitiveIdentityPin")):
                    fail("EXECUTION_BOUNDARY_PRIMITIVE_IDENTITY", f"{role_path}.primitiveIdentityPin", "coverage-domain role requires the exact primitive identity pin")
                enum(role["coverageKind"], f"{role_path}.coverageKind", OBSERVATION_COVERAGE_KINDS)
                enum(role["population"], f"{role_path}.population", {item["population"] for item in OBSERVATION_COVERAGE_PROFILES.values()})
                enum(role["completeness"], f"{role_path}.completeness", {"complete-or-refuse"})
                validate_namespace(role["namespaceScope"], f"{role_path}.namespaceScope")
            else:
                role = obj(role_value, role_path, {
                    "kind", "mechanismRef", "mechanismIdentityPin", "attemptBindingRef", "attemptIdentityPin", "ownerRef", "producerOperationRefs",
                    "phaseOrdinal", "predecessorReceiptRef", "direction", "availability",
                    "producerKind", "producerRef", "predicate",
                })
                enum(role["kind"], f"{role_path}.kind", set(EXCLUSION_RECEIPT_ROLES.values()))
                identifier(role["mechanismRef"], f"{role_path}.mechanismRef")
                if not re.fullmatch(r"sha256:[0-9a-f]{64}", string(role["mechanismIdentityPin"], f"{role_path}.mechanismIdentityPin")):
                    fail("EXECUTION_BOUNDARY_PRIMITIVE_IDENTITY", f"{role_path}.mechanismIdentityPin", "phase role requires the exact mechanism identity pin")
                identifier(role["attemptBindingRef"], f"{role_path}.attemptBindingRef")
                if not re.fullmatch(r"sha256:[0-9a-f]{64}", string(role["attemptIdentityPin"], f"{role_path}.attemptIdentityPin")):
                    fail("EXECUTION_BOUNDARY_ATTEMPT_IDENTITY", f"{role_path}.attemptIdentityPin", "phase role requires the exact attempt identity pin")
                owner_ref = identifier(role["ownerRef"], f"{role_path}.ownerRef")
                refs([owner_ref], set(owner_by), f"{role_path}.ownerRef")
                producer_refs = strings(role["producerOperationRefs"], f"{role_path}.producerOperationRefs", nonempty=True)
                refs(producer_refs, set(operation_by), f"{role_path}.producerOperationRefs")
                ordinal = number(role["phaseOrdinal"], f"{role_path}.phaseOrdinal")
                if type(ordinal) is not int or ordinal not in range(4):
                    fail("EXECUTION_BOUNDARY_EXCLUSION_ROLE", f"{role_path}.phaseOrdinal", "phase ordinal must be an integer from 0 through 3")
                string(role["predecessorReceiptRef"], f"{role_path}.predecessorReceiptRef", nullable=True)
                enum(role["direction"], f"{role_path}.direction", {"current-input", "future-output"})
                enum(role["availability"], f"{role_path}.availability", {"current-accepted", "owed"})
                producer_kind = enum(role["producerKind"], f"{role_path}.producerKind", {"owner", "operation"})
                producer_ref = identifier(role["producerRef"], f"{role_path}.producerRef")
                refs([producer_ref], set(owner_by) if producer_kind == "owner" else set(operation_by), f"{role_path}.producerRef")
                enum(role["predicate"], f"{role_path}.predicate", EXCLUSION_PHASE_PREDICATES)
            roles.append(role)
        if roles:
            expected_schema = {
                "operation-attempt-binding": "constellation.operation-attempt-binding/v1",
                "observation-coverage-domain": "constellation.observation-coverage-domain/v1",
            }.get(roles[0]["kind"], "constellation.shared-exclusion-phase/v1")
            if receipt["schemaType"] != expected_schema:
                fail("EXECUTION_BOUNDARY_EXCLUSION_RECEIPT_SCHEMA", f"{path}.schemaType", f"role requires {expected_schema}")
        receipt_roles[receipt["id"]] = roles

    for boundary_refs, boundary_field in deferred_boundary_receipt_refs:
        refs(boundary_refs, set(receipt_by), boundary_field)
    for expected in deferred_coverage_roles:
        receipt_ref = expected["receiptRef"]
        expected_role = {
            "kind": "observation-coverage-domain", "operationRef": expected["operationRef"],
            "factRef": expected["factRef"], "primitiveRef": expected["primitiveRef"],
            "primitiveIdentityPin": expected["primitiveIdentityPin"],
            "coverageKind": expected["coverageKind"], "population": expected["population"],
            "completeness": expected["completeness"], "namespaceScope": expected["namespaceScope"],
        }
        if receipt_roles.get(receipt_ref) != [expected_role]:
            fail("EXECUTION_BOUNDARY_COVERAGE_ROLE_MISMATCH", f"receipts.{receipt_ref}.semanticRoles", "coverage receipt does not bind the exact all-owner PID/user/procfs domain, primitive, and fact")
    for expected in deferred_evidence_authority_anchors:
        receipt_ref = expected["receiptRef"]
        receipt = receipt_by.get(receipt_ref)
        authority_evidence_ref = expected["authorityEvidenceReceiptRef"]
        authority_evidence = receipt_by.get(authority_evidence_ref)
        if receipt is None or authority_evidence is None:
            continue
        if receipt["issuerOwnerRef"] != expected["issuerOwnerRef"] or receipt["issuerAuthorityRef"] != expected["issuerAuthorityRef"]:
            fail("EXECUTION_BOUNDARY_EVIDENCE_ISSUER_MISMATCH", f"receipts.{receipt_ref}.issuerAuthorityRef", f"{expected['phase']} evidence issuer and authority must equal the exact contract-declared anchor")
        if authority_evidence_ref == receipt_ref or authority_evidence["issuerOwnerRef"] == expected["issuerOwnerRef"]:
            fail("EXECUTION_BOUNDARY_EVIDENCE_AUTHORITY_SELF_ISSUED", f"receipts.{authority_evidence_ref}", "authority evidence must be a distinct receipt externally issued from the expected current-evidence issuer")
        if authority_evidence["disposition"] != "externally-accepted" or any(authority_evidence[field] != "recorded" for field in ("evidenceBasisStatus", "artifactIdentityStatus", "custodyStatus")):
            fail("EXECUTION_BOUNDARY_EVIDENCE_AUTHORITY_UNACCEPTED", f"receipts.{authority_evidence_ref}", "issuer authority requires a distinct current recorded externally accepted evidence receipt")
    for expected in deferred_attempt_bindings:
        receipt_ref = expected["receiptRef"]
        receipt = receipt_by.get(receipt_ref)
        if receipt is None:
            continue
        if receipt["disposition"] != "externally-accepted" or any(receipt[field] != "recorded" for field in ("evidenceBasisStatus", "artifactIdentityStatus", "custodyStatus")):
            fail("EXECUTION_BOUNDARY_ATTEMPT_EVIDENCE_UNACCEPTED", f"receipts.{receipt_ref}", "attempt binding requires current recorded externally accepted evidence")
        if receipt["artifactIdentity"] != expected["identityPin"]:
            fail("EXECUTION_BOUNDARY_ATTEMPT_IDENTITY_MISMATCH", f"receipts.{receipt_ref}.artifactIdentity", "attempt receipt artifact identity must equal the declared attempt identity pin")
        expected_role = {
            "kind": "operation-attempt-binding", "bindingRef": expected["bindingRef"],
            "operationRef": expected["operationRef"], "supervisorOwnerRef": expected["supervisorOwnerRef"],
            "identitySourceRef": expected["identitySourceRef"], "identityPin": expected["identityPin"],
        }
        if receipt_roles[receipt_ref] != [expected_role]:
            fail("EXECUTION_BOUNDARY_ATTEMPT_ROLE_MISMATCH", f"receipts.{receipt_ref}.semanticRoles", "receipt does not bind the exact declared operation attempt")
        if receipt["issuerOwnerRef"] == expected["supervisorOwnerRef"]:
            fail("EXECUTION_BOUNDARY_ATTEMPT_SELF_ISSUED", f"receipts.{receipt_ref}.issuerOwnerRef", "attempt binding must be externally accepted by an owner distinct from the attempt supervisor")
        if not set(expected["producerOperationRefs"]) <= set(receipt["downstreamConsumers"]):
            fail("EXECUTION_BOUNDARY_ATTEMPT_CONSUMER_MISMATCH", f"receipts.{receipt_ref}.downstreamConsumers", "attempt binding must name every relevant producer as a consumer")

    for expected in deferred_exclusion_roles:
        receipt_ref = expected["receiptRef"]
        phase = expected["phase"]
        receipt = receipt_by.get(receipt_ref)
        if receipt is None:
            continue
        if expected["availability"] == "current-accepted":
            if receipt["disposition"] != "externally-accepted" or any(receipt[field] != "recorded" for field in ("evidenceBasisStatus", "artifactIdentityStatus", "custodyStatus")):
                fail("EXECUTION_BOUNDARY_EXCLUSION_EVIDENCE_UNACCEPTED", f"receipts.{receipt_ref}", f"{phase} input requires current recorded externally accepted evidence")
            if receipt["issuerOwnerRef"] == expected["producerRef"]:
                fail("EXECUTION_BOUNDARY_EXCLUSION_EVIDENCE_SELF_ISSUED", f"receipts.{receipt_ref}.issuerOwnerRef", f"{phase} input must be externally accepted by an owner distinct from the attempt supervisor")
        elif receipt["disposition"] != "missing" or receipt["artifactIdentityStatus"] != "missing" or receipt["custodyStatus"] != "missing":
            fail("EXECUTION_BOUNDARY_EXCLUSION_OUTPUT_PREPOPULATED", f"receipts.{receipt_ref}", f"future {phase} evidence must remain an owed missing output before dispatch")
        expected_role = {
            "kind": EXCLUSION_RECEIPT_ROLES[phase], "mechanismRef": expected["mechanismRef"],
            "mechanismIdentityPin": expected["mechanismIdentityPin"],
            "attemptBindingRef": expected["attemptBindingRef"], "attemptIdentityPin": expected["attemptIdentityPin"], "ownerRef": expected["ownerRef"],
            "producerOperationRefs": expected["producerOperationRefs"], "phaseOrdinal": expected["phaseOrdinal"],
            "predecessorReceiptRef": expected["predecessorReceiptRef"], "direction": expected["direction"],
            "availability": expected["availability"], "producerKind": expected["producerKind"],
            "producerRef": expected["producerRef"], "predicate": expected["predicate"],
        }
        if receipt_roles[receipt_ref] != [expected_role]:
            fail("EXECUTION_BOUNDARY_EXCLUSION_ROLE_MISMATCH", f"receipts.{receipt_ref}.semanticRoles", f"receipt does not witness the exact {phase} phase")
        if not set(expected["producerOperationRefs"]) <= set(receipt["downstreamConsumers"]):
            fail("EXECUTION_BOUNDARY_EXCLUSION_CONSUMER_MISMATCH", f"receipts.{receipt_ref}.downstreamConsumers", "phase evidence must name every producer operation as a consumer")

    # Resolve deferred receipt references now that receipt identities are known.
    for name, entries in (("owners", owners), ("authorities", authorities), ("credentials", credentials)):
        for index, entry in enumerate(entries): refs(strings(entry["evidenceRefs"], f"{name}[{index}].evidenceRefs"), set(receipt_by), f"{name}[{index}].evidenceRefs")
    for index, gate in enumerate(gates): refs(gate["requiredReceiptRefs"], set(receipt_by), f"gates[{index}].requiredReceiptRefs")

    resources, resource_by = collection(doc, "resourceRules", {"id", "resource", "purpose", "scope", "minimum", "expectedAllocation", "unit", "applicableOperations", "assessment"})
    for index, rule in enumerate(resources):
        path = f"resourceRules[{index}]"
        for key in ("resource", "purpose", "scope", "unit"): string(rule[key], f"{path}.{key}")
        number(rule["minimum"], f"{path}.minimum"); number(rule["expectedAllocation"], f"{path}.expectedAllocation")
        applicable = strings(rule["applicableOperations"], f"{path}.applicableOperations", nonempty=True); refs(applicable, set(operation_by), f"{path}.applicableOperations")
        assessment = obj(rule["assessment"], f"{path}.assessment", {"status", "observedAvailable", "measuredAt", "provenance"})
        enum(assessment["status"], f"{path}.assessment.status", {"meets", "does-not-meet", "unknown"})
        if assessment["observedAvailable"] is not None: number(assessment["observedAvailable"], f"{path}.assessment.observedAvailable")
        string(assessment["measuredAt"], f"{path}.assessment.measuredAt", nullable=True); string(assessment["provenance"], f"{path}.assessment.provenance", nullable=True)
        if assessment["status"] != "unknown" and (assessment["observedAvailable"] is None or assessment["measuredAt"] is None or assessment["provenance"] is None):
            fail("RESOURCE_PROVENANCE_REQUIRED", f"{path}.assessment", "resolved assessment requires value, time and provenance")

    privacy, privacy_by = collection(doc, "privacyEgress", {"id", "dataClass", "recipients", "purpose", "enrollmentScope", "requiredAuthorityRefs", "retention", "unknowns", "applicableOperations", "status"})
    for index, rule in enumerate(privacy):
        path = f"privacyEgress[{index}]"
        for key in ("dataClass", "purpose", "enrollmentScope", "retention"): string(rule[key], f"{path}.{key}")
        strings(rule["recipients"], f"{path}.recipients", nonempty=True); strings(rule["unknowns"], f"{path}.unknowns")
        required_authorities = strings(rule["requiredAuthorityRefs"], f"{path}.requiredAuthorityRefs", nonempty=True)
        refs(required_authorities, set(authority_by), f"{path}.requiredAuthorityRefs")
        if any(authority_by[authority_id]["kind"] != "privacy" for authority_id in required_authorities):
            fail("PRIVACY_AUTHORITY_KIND", f"{path}.requiredAuthorityRefs", "privacy/egress rules require only privacy authority references")
        refs(strings(rule["applicableOperations"], f"{path}.applicableOperations", nonempty=True), set(operation_by), f"{path}.applicableOperations")
        enum(rule["status"], f"{path}.status", {"satisfied", "unresolved", "denied"})

    repair = obj(doc["repairAuthority"], "repairAuthority", {"sourceRef", "allowedCategories", "protectedBoundaries"})
    refs([identifier(repair["sourceRef"], "repairAuthority.sourceRef")], set(source_by), "repairAuthority.sourceRef")
    allowed_categories = set(strings(repair["allowedCategories"], "repairAuthority.allowedCategories", nonempty=True))
    protected = set(strings(repair["protectedBoundaries"], "repairAuthority.protectedBoundaries", nonempty=True))
    if protected != PROTECTED_BOUNDARIES: fail("REPAIR_BOUNDARY_INCOMPLETE", "repairAuthority.protectedBoundaries", "must list all fixed owner boundaries")
    if allowed_categories & protected:
        fail("REPAIR_CATEGORY_PROTECTED", "repairAuthority.allowedCategories", "protected owner boundaries cannot be autonomous repair categories")
    if allowed_categories - AUTONOMOUS_REPAIR_CATEGORIES:
        fail("REPAIR_CATEGORY_UNKNOWN", "repairAuthority.allowedCategories", "allowed repair categories must use the bounded V1 category set")

    outcomes, _ = collection(doc, "outcomes", {"id", "kind", "definition", "requiredEvidenceRefs"})
    for index, outcome in enumerate(outcomes):
        path = f"outcomes[{index}]"; enum(outcome["kind"], f"{path}.kind", {"success", "refusal", "indeterminate"}); string(outcome["definition"], f"{path}.definition")
        refs(strings(outcome["requiredEvidenceRefs"], f"{path}.requiredEvidenceRefs"), set(receipt_by), f"{path}.requiredEvidenceRefs")
    if {item["kind"] for item in outcomes} != {"success", "refusal", "indeterminate"} or len(outcomes) != 3:
        fail("OUTCOME_SET_INVALID", "outcomes", "must define exactly one success, refusal and indeterminate outcome")

    reconciliation = obj(doc["reconciliation"], "reconciliation", {"retainedIdentities", "redispatchForbidden", "responseLossProcedureRef"})
    strings(reconciliation["retainedIdentities"], "reconciliation.retainedIdentities", nonempty=True); boolean(reconciliation["redispatchForbidden"], "reconciliation.redispatchForbidden")
    refs([identifier(reconciliation["responseLossProcedureRef"], "reconciliation.responseLossProcedureRef")], set(source_by), "reconciliation.responseLossProcedureRef")

    raw = obj(doc["rawEvidence"], "rawEvidence", {"immutable", "interpretationRules"}); boolean(raw["immutable"], "rawEvidence.immutable")
    if not raw["immutable"]: fail("RAW_EVIDENCE_MUTABLE", "rawEvidence.immutable", "raw evidence must remain immutable")
    if not isinstance(raw["interpretationRules"], list): fail("TYPE_ARRAY", "rawEvidence.interpretationRules", "must be an array")
    for index, rule_value in enumerate(raw["interpretationRules"]):
        path = f"rawEvidence.interpretationRules[{index}]"; rule = obj(rule_value, path, {"sourceRef", "scope", "rule"})
        refs([identifier(rule["sourceRef"], f"{path}.sourceRef")], set(source_by), f"{path}.sourceRef"); string(rule["scope"], f"{path}.scope"); string(rule["rule"], f"{path}.rule")

    cleanup, _ = collection(doc, "cleanupRules", {"id", "objectClass", "regenerable", "custodyPrerequisiteReceiptRefs", "operationRefs"})
    for index, rule in enumerate(cleanup):
        path = f"cleanupRules[{index}]"; string(rule["objectClass"], f"{path}.objectClass"); boolean(rule["regenerable"], f"{path}.regenerable")
        refs(strings(rule["custodyPrerequisiteReceiptRefs"], f"{path}.custodyPrerequisiteReceiptRefs", nonempty=True), set(receipt_by), f"{path}.custodyPrerequisiteReceiptRefs")
        refs(strings(rule["operationRefs"], f"{path}.operationRefs", nonempty=True), set(operation_by), f"{path}.operationRefs")

    rollback = obj(doc["rollback"], "rollback", {"reversible", "compensable", "procedureRef", "retainedStateLimits"})
    strings(rollback["reversible"], "rollback.reversible"); strings(rollback["compensable"], "rollback.compensable")
    refs([identifier(rollback["procedureRef"], "rollback.procedureRef")], set(source_by), "rollback.procedureRef"); string(rollback["retainedStateLimits"], "rollback.retainedStateLimits")

    decisions, _ = collection(doc, "ownerDecisions", {"id", "ownerRef", "kind", "missingField", "rationale", "evidenceSearch", "affectedOperations", "choices"})
    for index, decision in enumerate(decisions):
        path = f"ownerDecisions[{index}]"; refs([identifier(decision["ownerRef"], f"{path}.ownerRef")], set(owner_by), f"{path}.ownerRef")
        kind = enum(decision["kind"], f"{path}.kind", {"choice", "owner-supplied-fact"}); string(decision["missingField"], f"{path}.missingField")
        string(decision["rationale"], f"{path}.rationale"); string(decision["evidenceSearch"], f"{path}.evidenceSearch")
        refs(strings(decision["affectedOperations"], f"{path}.affectedOperations", nonempty=True), set(operation_by), f"{path}.affectedOperations")
        choices = strings(decision["choices"], f"{path}.choices")
        if kind == "choice" and len(choices) < 2: fail("OWNER_CHOICES_REQUIRED", f"{path}.choices", "choice requires at least two distinct choices")
        if kind == "owner-supplied-fact" and choices: fail("OWNER_FACT_HAS_CHOICES", f"{path}.choices", "owner-supplied fact must not invent choices")

    repairs, _ = collection(doc, "autonomousRepairs", {"id", "category", "description"})
    for index, repair_item in enumerate(repairs):
        category = enum(repair_item["category"], f"autonomousRepairs[{index}].category", AUTONOMOUS_REPAIR_CATEGORIES)
        if category not in allowed_categories:
            fail("REPAIR_CATEGORY_NOT_ALLOWED", f"autonomousRepairs[{index}].category", "autonomous repair category is not declared by repairAuthority")
        string(repair_item["description"], f"autonomousRepairs[{index}].description")

    imports, _ = collection(doc, "imports", {"id", "integrationId", "objectType", "objectId", "sourceContractRef", "sourceContractPin"})
    for index, imported in enumerate(imports):
        path = f"imports[{index}]"
        for key in ("integrationId", "objectType", "objectId", "sourceContractRef", "sourceContractPin"): string(imported[key], f"{path}.{key}")
    if imports:
        fail("IMPORTS_UNSUPPORTED", "imports", "this bounded V1 implementation rejects imported dependencies rather than claiming to resolve them")

    # Resolve operation references after all target collections exist.
    for index, operation in enumerate(operations):
        path = f"operations[{index}]"
        binding = operation["invocationBinding"]
        if binding is not None:
            refs([binding["principalRef"]], set(owner_by), f"{path}.invocationBinding.principalRef")
            refs([binding["authorityRef"]], set(authority_by), f"{path}.invocationBinding.authorityRef")
        boundary = operation.get("executionBoundary")
        if boundary is not None:
            semantics = boundary["authoritySemantics"]
            if semantics["principalRef"] is not None:
                refs([semantics["principalRef"]], set(owner_by), f"{path}.executionBoundary.authoritySemantics.principalRef")
            if semantics["authorityRef"] is not None:
                refs([semantics["authorityRef"]], set(authority_by), f"{path}.executionBoundary.authoritySemantics.authorityRef")
            for fact_index, fact in enumerate(boundary["technicalVisibilityFacts"]):
                refs(
                    fact["downstreamReceiptRefs"],
                    set(receipt_by),
                    f"{path}.executionBoundary.technicalVisibilityFacts[{fact_index}].downstreamReceiptRefs",
                )
            refs(boundary["outputCustody"]["receiptRefs"], set(receipt_by), f"{path}.executionBoundary.outputCustody.receiptRefs")
        refs(operation["requiredReceiptRefs"], set(receipt_by), f"{path}.requiredReceiptRefs")
        refs(operation["producedReceiptRefs"], set(receipt_by), f"{path}.producedReceiptRefs")
        refs(operation["requiredAuthorityRefs"], set(authority_by), f"{path}.requiredAuthorityRefs")
        refs(operation["requiredResourceRuleRefs"], set(resource_by), f"{path}.requiredResourceRuleRefs")
        refs(operation["requiredPrivacyRuleRefs"], set(privacy_by), f"{path}.requiredPrivacyRuleRefs")
        for req_index, requirement in enumerate(operation["credentialRequirements"]):
            req_path = f"{path}.credentialRequirements[{req_index}]"
            refs([requirement["credentialRef"]], set(credential_by), f"{req_path}.credentialRef")
            refs([requirement["requiredAuthorityRef"]], set(authority_by), f"{req_path}.requiredAuthorityRef")
            if requirement["consumer"] not in consumers: fail("CONSUMER_UNKNOWN", f"{req_path}.consumer", "consumer is not an intended consumer")
            if requirement["consumer"] != operation["consumer"]:
                fail("CREDENTIAL_CONSUMER_MISMATCH", f"{req_path}.consumer", "credential requirement consumer must equal the operation consumer")
            if requirement["requiredAuthorityRef"] not in operation["requiredAuthorityRefs"]:
                fail("CREDENTIAL_AUTHORITY_NOT_REQUIRED", f"{req_path}.requiredAuthorityRef", "credential authority must also be required by the operation")

        expected_effect_kind = EFFECT_AUTHORITY_KINDS.get(operation["kind"])
        if expected_effect_kind is not None and not any(
            authority_by[authority_id]["kind"] == expected_effect_kind
            for authority_id in operation["requiredAuthorityRefs"]
        ):
            fail("OPERATION_AUTHORITY_KIND", f"{path}.requiredAuthorityRefs", f"{operation['kind']} requires an authority of kind {expected_effect_kind}")
        if binding is not None and binding["authorityRef"] not in operation["requiredAuthorityRefs"]:
            fail("INVOCATION_AUTHORITY_NOT_REQUIRED", f"{path}.invocationBinding.authorityRef", "invocation authority must also be required by the operation")
        if binding is not None:
            allowed_kinds = INVOCATION_AUTHORITY_KINDS[operation["kind"]]
            if authority_by[binding["authorityRef"]]["kind"] not in allowed_kinds:
                fail("INVOCATION_AUTHORITY_KIND", f"{path}.invocationBinding.authorityRef", f"{operation['kind']} invocation requires authority kind: {', '.join(sorted(allowed_kinds))}")
        if operation["kind"] == "cleanup" and not any(
            authority_by[authority_id]["kind"] == "cleanup"
            for authority_id in operation["requiredAuthorityRefs"]
        ):
            fail("OPERATION_AUTHORITY_KIND", f"{path}.requiredAuthorityRefs", "cleanup requires an authority of kind cleanup")
        overlap = set(operation["requiredReceiptRefs"]) & set(operation["producedReceiptRefs"])
        if overlap:
            fail("RECEIPT_INPUT_OUTPUT_CONFLICT", path, f"operation cannot require and produce the same receipts: {', '.join(sorted(overlap))}")

        expected_resources = {rule["id"] for rule in resources if operation["id"] in rule["applicableOperations"]}
        if set(operation["requiredResourceRuleRefs"]) != expected_resources:
            fail("RESOURCE_SCOPE_INCONSISTENT", f"{path}.requiredResourceRuleRefs", "operation resource references must exactly match resourceRules applicability")
        expected_privacy = {rule["id"] for rule in privacy if operation["id"] in rule["applicableOperations"]}
        if set(operation["requiredPrivacyRuleRefs"]) != expected_privacy:
            fail("PRIVACY_SCOPE_INCONSISTENT", f"{path}.requiredPrivacyRuleRefs", "operation privacy references must exactly match privacyEgress applicability")

    producers: dict[str, str] = {}
    for operation in operations:
        for receipt_id in operation["producedReceiptRefs"]:
            if receipt_id in producers:
                fail("RECEIPT_MULTIPLE_PRODUCERS", "operations", f"receipt {receipt_id} has multiple declared producers")
            producers[receipt_id] = operation["id"]
    for expected in deferred_attempt_bindings:
        receipt_ref = expected["receiptRef"]
        if receipt_ref in producers:
            fail("EXECUTION_BOUNDARY_ATTEMPT_DIRECTION", f"receipts.{receipt_ref}", "current attempt binding must be externally supplied before dispatch, not produced by the bound operation")
    gate_inputs = {receipt_ref for gate in gates for receipt_ref in gate["requiredReceiptRefs"]}
    operation_inputs = {receipt_ref for operation in operations for receipt_ref in operation["requiredReceiptRefs"]}
    for expected in deferred_exclusion_roles:
        receipt_ref = expected["receiptRef"]
        if expected["direction"] == "current-input":
            if receipt_ref in producers:
                fail("EXECUTION_BOUNDARY_EXCLUSION_DIRECTION", f"receipts.{receipt_ref}", "current exclusion input must be supplied by the declared supervisor owner, not produced by an operation")
        else:
            if producers.get(receipt_ref) != expected["attemptOperationRef"]:
                fail("EXECUTION_BOUNDARY_EXCLUSION_DIRECTION", f"receipts.{receipt_ref}", "future exclusion output must be produced by the exact attempt operation")
            if receipt_ref in gate_inputs or receipt_ref in operation_inputs:
                fail("EXECUTION_BOUNDARY_EXCLUSION_OUTPUT_AS_INPUT", f"receipts.{receipt_ref}", "future exclusion output must not be a current operation or gate prerequisite")
    for gate in gates:
        for operation_id in gate["blocks"]:
            if set(gate["requiredReceiptRefs"]) & set(operation_by[operation_id]["producedReceiptRefs"]):
                fail("GATE_OUTPUT_SELF_DEPENDENCY", f"gates.{gate['id']}", "gate cannot require an output receipt from the operation it blocks")

    if "interfaceClosure" in doc:
        interface_closure = doc["interfaceClosure"]
        closure = obj(interface_closure, "interfaceClosure", INTERFACE_CLOSURE_FIELDS)
        collection_ids = {
            "basisSourceRefs": set(source_by),
            "ownerRefs": set(owner_by),
            "authorityRefs": set(authority_by),
            "operationRefs": set(operation_by),
            "gateRefs": set(gate_by),
            "credentialRefs": set(credential_by),
            "receiptRefs": set(receipt_by),
            "resourceRuleRefs": set(resource_by),
            "privacyRuleRefs": set(privacy_by),
            "cleanupRuleRefs": {item["id"] for item in cleanup},
        }
        for field, expected in collection_ids.items():
            declared = set(strings(closure[field], f"interfaceClosure.{field}", nonempty=field in {"basisSourceRefs", "operationRefs"}))
            refs(list(declared), expected, f"interfaceClosure.{field}")

    assessment = obj(doc["assessment"], "assessment", {"timestamp", "source", "sourcePin", "verification", "limits"})
    string(assessment["timestamp"], "assessment.timestamp"); string(assessment["source"], "assessment.source")
    string(assessment["sourcePin"], "assessment.sourcePin", nullable=True); enum(assessment["verification"], "assessment.verification", {"not-verified", "caller-verified-index"})
    strings(assessment["limits"], "assessment.limits", nonempty=True)
    if assessment["verification"] == "caller-verified-index" and assessment["sourcePin"] is None:
        fail("ASSESSMENT_PIN_REQUIRED", "assessment.sourcePin", "caller-verified index requires a pin")
    return doc
