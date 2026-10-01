"""Deterministic scoped preflight. This module never performs an effect."""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from .types import Diagnostic
from .validator import ContractValidationError, PROTECTED_BOUNDARIES, validate_contract


RFC3339 = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?P<offset>Z|(?P<sign>[+-])(?P<offset_hour>[0-9]{2}):(?P<offset_minute>[0-9]{2}))$"
)

# Declaration wiring is independently repairable from the recorded facts that
# determine readiness. Keep this explicit so new readiness diagnostics cannot
# accidentally turn honest unknown facts into an incomplete integration.
INTEGRATION_BLOCKER_CODES = frozenset({
    "INTERFACE_CLOSURE_INCOMPLETE",
    "INTERFACE_CLOSURE_MISSING",
    "INVOCATION_BINDING_MISSING",
    "EXECUTION_BOUNDARY_MISSING",
    "EXECUTION_BOUNDARY_AUTHORITY_MISMATCH",
    "EVIDENCE_SCOPE_GATE_MISSING",
    "EVIDENCE_SCOPE_GATE_INCOMPLETE",
    "EVIDENCE_CONSUMER_SCOPE_MISMATCH",
    "EVIDENCE_ISSUER_AUTHORITY_CYCLE",
    "CLEANUP_RULE_MISSING",
})


def _qualified(integration_id: str, local_id: str) -> str:
    return f"{integration_id}/{local_id}"


def _rfc3339_utc(value: str) -> datetime | None:
    if not isinstance(value, str):
        return None
    match = RFC3339.fullmatch(value)
    if match is None:
        return None
    if match.group("offset") != "Z":
        offset_hour = int(match.group("offset_hour"))
        offset_minute = int(match.group("offset_minute"))
        if offset_hour > 23 or offset_minute > 59:
            return None
        if match.group("sign") == "-" and offset_hour == 0 and offset_minute == 0:
            return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def preflight(document: Any, *, assessment_timestamp: str) -> dict[str, Any]:
    contract = validate_contract(document)
    integration_id = contract["integration"]["id"]
    owners = {item["id"]: item for item in contract["owners"]}
    authorities = {item["id"]: item for item in contract["authorities"]}
    credentials = {item["id"]: item for item in contract["credentials"]}
    receipts = {item["id"]: item for item in contract["receipts"]}
    resources = {item["id"]: item for item in contract["resourceRules"]}
    privacy = {item["id"]: item for item in contract["privacyEgress"]}
    gates = contract["gates"]
    explicit_assessment_time = _rfc3339_utc(assessment_timestamp)
    if explicit_assessment_time is None:
        raise ContractValidationError("ASSESSMENT_TIME_INVALID", "--assessment-time", "must be RFC3339 with an explicit UTC offset")

    def receipt_diagnostics(
        receipt_id: str,
        field: str,
        operation_id: str,
        *,
        active: tuple[str, ...] = (),
        seen: set[str] | None = None,
    ) -> list[Diagnostic]:
        receipt = receipts[receipt_id]
        qualified_op = _qualified(integration_id, operation_id)
        if receipt_id in active:
            return [Diagnostic(
                "EVIDENCE_ISSUER_AUTHORITY_CYCLE", field,
                f"issuer acceptance evidence cycle reaches {_qualified(integration_id, receipt_id)}", qualified_op,
                _qualified(integration_id, receipt["issuerOwnerRef"]),
            )]
        if seen is None:
            seen = set()
        if receipt_id in seen:
            return []
        seen.add(receipt_id)
        result: list[Diagnostic] = []
        if receipt["disposition"] != "externally-accepted":
            result.append(Diagnostic(
                "EVIDENCE_NOT_EXTERNALLY_ACCEPTED", field,
                f"{_qualified(integration_id, receipt_id)} is recorded as {receipt['disposition']}", qualified_op,
                _qualified(integration_id, receipt["issuerOwnerRef"]),
            ))
        issuer = owners[receipt["issuerOwnerRef"]]
        if issuer["status"] != "resolved":
            result.append(Diagnostic(
                "EVIDENCE_ISSUER_UNRESOLVED", field,
                f"issuer for {_qualified(integration_id, receipt_id)} is unresolved", qualified_op,
                _qualified(integration_id, receipt["issuerOwnerRef"]),
            ))
        issuer_authority = authorities[receipt["issuerAuthorityRef"]]
        if issuer_authority["status"] != "established" or owners[issuer_authority["ownerRef"]]["status"] != "resolved":
            result.append(Diagnostic(
                "EVIDENCE_ISSUER_AUTHORITY_UNRESOLVED", field,
                f"issuer acceptance authority for {_qualified(integration_id, receipt_id)} is unresolved", qualified_op,
                _qualified(integration_id, issuer_authority["ownerRef"]),
            ))
        for evidence_receipt_id in issuer_authority["evidenceRefs"]:
            result.extend(receipt_diagnostics(
                evidence_receipt_id,
                f"authorities.{receipt['issuerAuthorityRef']}.evidenceRefs",
                operation_id,
                active=active + (receipt_id,),
                seen=seen,
            ))
        if operation_id not in receipt["downstreamConsumers"]:
            result.append(Diagnostic(
                "EVIDENCE_CONSUMER_SCOPE_MISMATCH", field,
                f"{_qualified(integration_id, receipt_id)} does not name this operation as a consumer", qualified_op,
                _qualified(integration_id, receipt["issuerOwnerRef"]),
            ))
        return result

    def prerequisite_receipts(operation: dict[str, Any]) -> set[str]:
        """Collect consumed receipts, including applicable runtime gate inputs."""
        result = set(operation["requiredReceiptRefs"])
        # Source-only independent prerequisites stay gate-free: a gate cannot
        # justify broadening its own scope to otherwise unrelated preparation.
        if operation["executionClass"] == "runtime":
            for gate in gates:
                if operation["id"] in gate["blocks"]:
                    result.update(gate["requiredReceiptRefs"])
        authority_ids = set(operation["requiredAuthorityRefs"])
        for requirement in operation["credentialRequirements"]:
            credential = credentials[requirement["credentialRef"]]
            result.update(credential["evidenceRefs"])
            authority_ids.add(requirement["requiredAuthorityRef"])
        for rule in contract["privacyEgress"]:
            if operation["id"] in rule["applicableOperations"]:
                authority_ids.update(rule["requiredAuthorityRefs"])
        for authority_id in authority_ids:
            result.update(authorities[authority_id]["evidenceRefs"])
        binding = operation["invocationBinding"]
        if binding is not None:
            result.update(authorities[binding["authorityRef"]]["evidenceRefs"])
        if operation["kind"] == "cleanup":
            for rule in contract["cleanupRules"]:
                if operation["id"] in rule["operationRefs"]:
                    result.update(rule["custodyPrerequisiteReceiptRefs"])
        boundary = operation.get("executionBoundary")
        if boundary is not None:
            for exclusion in boundary["sharedExclusions"]:
                result.add(exclusion["attemptBinding"]["receiptRef"])
                for phase in ("acquisition", "hold"):
                    result.add(exclusion[phase]["receiptRef"])

        # Issuer-authority evidence is itself a prerequisite. Bound this walk by
        # receipt identity so a declaration cycle cannot loop qualification.
        pending = list(result)
        while pending:
            receipt_id = pending.pop()
            issuer_authority = authorities[receipts[receipt_id]["issuerAuthorityRef"]]
            for dependency in issuer_authority["evidenceRefs"]:
                if dependency not in result:
                    result.add(dependency)
                    pending.append(dependency)
        return result

    operation_results: list[dict[str, Any]] = []
    all_diagnostics: list[dict[str, Any]] = []
    for operation in contract["operations"]:
        operation_id = operation["id"]
        qualified_op = _qualified(integration_id, operation_id)
        blockers: list[Diagnostic] = []
        checked_receipts: set[str] = set()

        if "executionBoundary" not in operation:
            missing_boundary = Diagnostic(
                "EXECUTION_BOUNDARY_MISSING", f"operations.{operation_id}.executionBoundary",
                "operation does not explicitly declare a runtime execution boundary or null for source-only work",
                qualified_op if operation["executionClass"] == "runtime" else _qualified(integration_id, "__interface__"),
            )
            if operation["executionClass"] == "runtime":
                blockers.append(missing_boundary)
            else:
                all_diagnostics.append(missing_boundary.as_dict())
        if operation["executionClass"] == "runtime":
            boundary = operation.get("executionBoundary")
            if "executionBoundary" in operation and boundary is None:
                blockers.append(Diagnostic(
                    "EXECUTION_BOUNDARY_MISSING", f"operations.{operation_id}.executionBoundary",
                    "runtime operation does not declare technical visibility, logical authority, output custody, campaign convention, and least-privilege boundaries",
                    qualified_op,
                ))
            elif boundary is not None and boundary["status"] != "established":
                blockers.append(Diagnostic(
                    "EXECUTION_BOUNDARY_UNRESOLVED", f"operations.{operation_id}.executionBoundary",
                    boundary["unresolvedReason"], qualified_op,
                ))
            binding = operation["invocationBinding"]
            if boundary is not None and binding is not None:
                semantics = boundary["authoritySemantics"]
                if (
                    semantics["principalRef"] != binding["principalRef"]
                    or semantics["authorityRef"] != binding["authorityRef"]
                ):
                    blockers.append(Diagnostic(
                        "EXECUTION_BOUNDARY_AUTHORITY_MISMATCH", f"operations.{operation_id}.executionBoundary.authoritySemantics",
                        "execution-boundary authority semantics do not match the logical invocation binding", qualified_op,
                    ))
            if binding is None:
                blockers.append(Diagnostic(
                    "INVOCATION_BINDING_MISSING", f"operations.{operation_id}.invocationBinding",
                    "runtime operation does not declare its invoking principal and authority", qualified_op,
                ))
            else:
                principal_id = binding["principalRef"]
                authority_id = binding["authorityRef"]
                principal = owners[principal_id]
                authority = authorities[authority_id]
                principal_name = _qualified(integration_id, principal_id)
                if principal["status"] != "resolved":
                    blockers.append(Diagnostic(
                        "INVOCATION_PRINCIPAL_UNRESOLVED", f"operations.{operation_id}.invocationBinding.principalRef",
                        f"invoking principal {principal_name} is unresolved", qualified_op, principal_name,
                    ))
                if authority["status"] != "established" or owners[authority["ownerRef"]]["status"] != "resolved":
                    blockers.append(Diagnostic(
                        "INVOCATION_AUTHORITY_UNRESOLVED", f"operations.{operation_id}.invocationBinding.authorityRef",
                        "invocation authority or its owner is unresolved", qualified_op,
                        _qualified(integration_id, authority["ownerRef"]),
                    ))
                if principal_id not in authority["authorizedPrincipalRefs"]:
                    blockers.append(Diagnostic(
                        "INVOCATION_PRINCIPAL_UNAUTHORIZED", f"operations.{operation_id}.invocationBinding",
                        f"invocation authority does not authorize principal {principal_name}", qualified_op, principal_name,
                    ))

        # Declare the acceptance scope before the evidence arrives. Every
        # consumed receipt must eventually be externally accepted to satisfy a
        # prerequisite; missing/template/prepared evidence is no scope waiver.
        if operation["executionClass"] == "runtime":
            for receipt_id in sorted(prerequisite_receipts(operation)):
                receipt_gates = [
                    gate for gate in gates
                    if gate["kind"] == "required-evidence" and receipt_id in gate["requiredReceiptRefs"]
                ]
                if not receipt_gates:
                    blockers.append(Diagnostic(
                        "EVIDENCE_SCOPE_GATE_MISSING", f"receipts.{receipt_id}.downstreamConsumers",
                        f"runtime prerequisite {_qualified(integration_id, receipt_id)} has no required-evidence gate for its eventual acceptance", qualified_op,
                        _qualified(integration_id, receipts[receipt_id]["issuerOwnerRef"]),
                    ))
                elif not any(
                    operation_id in gate["blocks"]
                    and all(
                        candidate["id"] not in gate["blocks"]
                        for candidate in contract["operations"]
                        if candidate["executionClass"] == "source-only"
                        and receipt_id not in prerequisite_receipts(candidate)
                    )
                    for gate in receipt_gates
                ):
                    blockers.append(Diagnostic(
                        "EVIDENCE_SCOPE_GATE_INCOMPLETE", f"receipts.{receipt_id}.downstreamConsumers",
                        f"required-evidence gate for {_qualified(integration_id, receipt_id)} does not cover this dependent runtime operation while excluding unrelated source-only preparation", qualified_op,
                        _qualified(integration_id, receipts[receipt_id]["issuerOwnerRef"]),
                    ))

        for gate in contract["gates"]:
            if operation_id not in gate["blocks"]:
                continue
            owner = _qualified(integration_id, gate["ownerRef"])
            if owners[gate["ownerRef"]]["status"] != "resolved":
                blockers.append(Diagnostic(
                    "GATE_OWNER_UNRESOLVED", f"gates.{gate['id']}.ownerRef",
                    f"owner for {_qualified(integration_id, gate['id'])} is unresolved", qualified_op, owner,
                ))
            if gate["status"] != "satisfied":
                blockers.append(Diagnostic(
                    "GATE_" + gate["status"].upper(), f"gates.{gate['id']}",
                    f"{_qualified(integration_id, gate['id'])} is recorded as {gate['status']}", qualified_op, owner,
                ))
            for receipt_id in gate["requiredReceiptRefs"]:
                blockers.extend(receipt_diagnostics(receipt_id, f"gates.{gate['id']}.requiredReceiptRefs", operation_id))
                checked_receipts.add(receipt_id)
            boundary = gate["timeBoundary"]
            if boundary is not None:
                field = f"gates.{gate['id']}.timeBoundary"
                if boundary["clockContractRef"] != "rfc3339-utc":
                    blockers.append(Diagnostic("TIME_CLOCK_UNSUPPORTED", field, "V1 cannot interpret this clock contract; defer to its owner", qualified_op, owner))
                else:
                    not_before = _rfc3339_utc(boundary["notBefore"])
                    if explicit_assessment_time is None or not_before is None:
                        blockers.append(Diagnostic("TIME_FORMAT_UNRESOLVED", field, "assessment or not-before time is not interpretable RFC3339 with an offset", qualified_op, owner))
                    elif explicit_assessment_time < not_before:
                        blockers.append(Diagnostic("TIME_NOT_REACHED", field, "explicit assessment time precedes the not-before boundary", qualified_op, owner))
                    elif boundary["assessment"] != "reached":
                        blockers.append(Diagnostic("TIME_RECORDED_" + boundary["assessment"].replace("-", "_").upper(), field, "contract does not record the supported boundary as reached", qualified_op, owner))

        for requirement in operation["credentialRequirements"]:
            credential = credentials[requirement["credentialRef"]]
            field = f"operations.{operation_id}.credentialRequirements.{credential['id']}"
            if credential["readiness"] != "present":
                blockers.append(Diagnostic("CREDENTIAL_NOT_PRESENT", field, f"credential is {credential['readiness']}", qualified_op))
            if credential["scopeVerification"] != "verified":
                blockers.append(Diagnostic("CREDENTIAL_SCOPE_UNVERIFIED", field, f"credential scope verification is {credential['scopeVerification']}", qualified_op))
            if credential["purpose"] != requirement["purpose"] or requirement["consumer"] not in credential["authorizedConsumers"]:
                blockers.append(Diagnostic("CREDENTIAL_SCOPE_MISMATCH", field, "credential purpose or consumer does not match the requirement", qualified_op))
            binding = operation["invocationBinding"]
            if binding is not None and binding["principalRef"] not in credential["authorizedPrincipalRefs"]:
                blockers.append(Diagnostic("CREDENTIAL_PRINCIPAL_MISMATCH", field, "credential does not authorize the declared invoking principal", qualified_op, _qualified(integration_id, binding["principalRef"])))
            required_authority = requirement["requiredAuthorityRef"]
            if required_authority not in credential["authorityGrantedRefs"] or required_authority in credential["authorityNotGrantedRefs"]:
                blockers.append(Diagnostic("CREDENTIAL_AUTHORITY_MISMATCH", field, "recorded credential scope does not include the required authority", qualified_op))
            authority = authorities[required_authority]
            if authority["status"] != "established" or owners[authority["ownerRef"]]["status"] != "resolved":
                blockers.append(Diagnostic("CREDENTIAL_AUTHORITY_UNRESOLVED", field, "required existing authority boundary is unresolved", qualified_op, _qualified(integration_id, authority["ownerRef"])))
            for receipt_id in credential["evidenceRefs"]:
                blockers.extend(receipt_diagnostics(receipt_id, f"credentials.{credential['id']}.evidenceRefs", operation_id))

        for receipt_id in operation["requiredReceiptRefs"]:
            if receipt_id in checked_receipts:
                continue
            blockers.extend(receipt_diagnostics(receipt_id, f"operations.{operation_id}.requiredReceiptRefs", operation_id))

        for authority_id in operation["requiredAuthorityRefs"]:
            authority = authorities[authority_id]
            if authority["status"] != "established" or owners[authority["ownerRef"]]["status"] != "resolved":
                blockers.append(Diagnostic(
                    "AUTHORITY_UNRESOLVED", f"operations.{operation_id}.requiredAuthorityRefs",
                    f"existing authority {_qualified(integration_id, authority_id)} is unresolved", qualified_op,
                    _qualified(integration_id, authority["ownerRef"]),
                ))
            for receipt_id in authority["evidenceRefs"]:
                blockers.extend(receipt_diagnostics(receipt_id, f"authorities.{authority_id}.evidenceRefs", operation_id))

        if contract["assessment"]["verification"] != "caller-verified-index" and operation["kind"] in {"local-effect", "cleanup"}:
            blockers.append(Diagnostic(
                "ASSESSMENT_UNVERIFIED", "assessment.verification",
                "an unverified assessment cannot report a local effect or cleanup operation permitted", qualified_op,
            ))

        for rule in contract["resourceRules"]:
            if operation_id not in rule["applicableOperations"]:
                continue
            rule_id = rule["id"]
            assessment = rule["assessment"]
            sufficient = (
                assessment["status"] == "meets"
                and assessment["observedAvailable"] is not None
                and assessment["observedAvailable"] >= rule["minimum"] + rule["expectedAllocation"]
            )
            if not sufficient:
                blockers.append(Diagnostic(
                    "RESOURCE_UNRESOLVED" if assessment["status"] == "unknown" else "RESOURCE_INSUFFICIENT",
                    f"resourceRules.{rule_id}.assessment", f"resource rule {_qualified(integration_id, rule_id)} is not met with recorded measurement provenance", qualified_op,
                ))

        for rule in contract["privacyEgress"]:
            if operation_id not in rule["applicableOperations"]:
                continue
            privacy_id = rule["id"]
            if rule["status"] != "satisfied":
                blockers.append(Diagnostic(
                    "PRIVACY_" + rule["status"].upper(), f"privacyEgress.{privacy_id}",
                    f"privacy/egress rule {_qualified(integration_id, privacy_id)} is {rule['status']}", qualified_op,
                ))
            for authority_id in rule["requiredAuthorityRefs"]:
                authority = authorities[authority_id]
                if authority["status"] != "established" or owners[authority["ownerRef"]]["status"] != "resolved":
                    blockers.append(Diagnostic("PRIVACY_AUTHORITY_UNRESOLVED", f"privacyEgress.{privacy_id}.requiredAuthorityRefs", "privacy authority is unresolved", qualified_op, _qualified(integration_id, authority["ownerRef"])))
                for receipt_id in authority["evidenceRefs"]:
                    blockers.extend(receipt_diagnostics(receipt_id, f"authorities.{authority_id}.evidenceRefs", operation_id))

        if operation["kind"] == "cleanup":
            applicable_cleanup = [rule for rule in contract["cleanupRules"] if operation_id in rule["operationRefs"]]
            if not applicable_cleanup:
                blockers.append(Diagnostic("CLEANUP_RULE_MISSING", f"operations.{operation_id}", "cleanup operation has no applicable cleanup rule", qualified_op))
            for rule in applicable_cleanup:
                if not rule["regenerable"]:
                    blockers.append(Diagnostic("CLEANUP_NOT_REGENERABLE", f"cleanupRules.{rule['id']}", "object class is not declared regenerable", qualified_op))
                for receipt_id in rule["custodyPrerequisiteReceiptRefs"]:
                    custody_diagnostics = receipt_diagnostics(receipt_id, f"cleanupRules.{rule['id']}", operation_id)
                    blockers.extend(custody_diagnostics)
                    if any(item.code.startswith("EVIDENCE_") for item in custody_diagnostics):
                        receipt = receipts[receipt_id]
                        blockers.append(Diagnostic("CLEANUP_CUSTODY_UNSATISFIED", f"cleanupRules.{rule['id']}", f"custody prerequisite {_qualified(integration_id, receipt_id)} is not satisfied", qualified_op, _qualified(integration_id, receipt["issuerOwnerRef"])))

        for decision in contract["ownerDecisions"]:
            if operation_id in decision["affectedOperations"]:
                blockers.append(Diagnostic(
                    "OWNER_DECISION_UNRESOLVED", f"ownerDecisions.{decision['id']}",
                    f"owner decision {_qualified(integration_id, decision['id'])} remains unresolved", qualified_op,
                    _qualified(integration_id, decision["ownerRef"]),
                ))

        # Stable ordering and de-duplication make outputs cross-implementation friendly.
        unique = {(item.code, item.field, item.message, item.operation, item.owner): item for item in blockers}
        blockers = [unique[key] for key in sorted(unique)]
        external = operation["kind"] in {"external-effect", "production-effect"}
        if blockers:
            disposition = "blocked"
        elif external:
            disposition = "ready-for-existing-authority-check"
        else:
            disposition = "permitted-by-declared-contract"
        result = {
            "operation": qualified_op,
            "kind": operation["kind"],
            "executionClass": operation["executionClass"],
            "invocationBinding": None if operation["invocationBinding"] is None else {
                "principal": _qualified(integration_id, operation["invocationBinding"]["principalRef"]),
                "authority": _qualified(integration_id, operation["invocationBinding"]["authorityRef"]),
            },
            "executionBoundary": operation.get("executionBoundary"),
            "executionBoundaryDeclared": "executionBoundary" in operation,
            "disposition": disposition,
            "permittedByDeclaredContract": not blockers and not external,
            "effectAuthorityGranted": False,
            "blockers": [item.as_dict() for item in blockers],
            "remainingAuthorityRequirements": [
                _qualified(integration_id, item) for item in operation["requiredAuthorityRefs"]
            ] if operation["kind"] in {"local-effect", "external-effect", "production-effect"} else [],
        }
        operation_results.append(result)
        all_diagnostics.extend(result["blockers"])

    interface_closure_missing: dict[str, list[str]] = {}
    if "interfaceClosure" not in contract:
        all_diagnostics.append(Diagnostic(
            "INTERFACE_CLOSURE_MISSING", "interfaceClosure",
            "the source-derived finite interface closure is not declared; wiring checks cannot establish a complete integration",
            _qualified(integration_id, "__interface__"),
        ).as_dict())
    else:
        closure_collections = {
            "basisSourceRefs": contract["sources"],
            "ownerRefs": contract["owners"],
            "authorityRefs": contract["authorities"],
            "operationRefs": contract["operations"],
            "gateRefs": contract["gates"],
            "credentialRefs": contract["credentials"],
            "receiptRefs": contract["receipts"],
            "resourceRuleRefs": contract["resourceRules"],
            "privacyRuleRefs": contract["privacyEgress"],
            "cleanupRuleRefs": contract["cleanupRules"],
        }
        for field, entries in closure_collections.items():
            omitted = sorted({item["id"] for item in entries} - set(contract["interfaceClosure"][field]))
            if omitted:
                interface_closure_missing[field] = omitted
                all_diagnostics.append(Diagnostic(
                    "INTERFACE_CLOSURE_INCOMPLETE", f"interfaceClosure.{field}",
                    f"declared contract objects are absent from the source-derived interface closure: {', '.join(omitted)}",
                    _qualified(integration_id, "__interface__"),
                ).as_dict())

    gate_dispositions = [{
        "gate": _qualified(integration_id, gate["id"]),
        "recordedStatus": gate["status"],
        "recordedDisposition": gate["recordedDisposition"],
        "blocks": [_qualified(integration_id, item) for item in gate["blocks"]],
        "doesNotBlock": [_qualified(integration_id, item) for item in gate["doesNotBlock"]],
        "v1VerifiedAcceptance": False,
    } for gate in contract["gates"]]

    diagnostics = sorted(all_diagnostics, key=lambda item: (item["operation"], item["code"], item["field"]))
    integration_blockers = [item for item in diagnostics if item["code"] in INTEGRATION_BLOCKER_CODES]

    interface_closure = contract.get("interfaceClosure")
    resolved_interface_closure = {
        "declared": interface_closure is not None,
        "complete": interface_closure is not None and not interface_closure_missing,
        "missingDeclaredObjects": interface_closure_missing,
        "statement": (
            "The declared source-derived interface closure inventories every object in this contract; V1 does not prove that prose sources omitted no relevant interface element."
            if interface_closure is not None and not interface_closure_missing else
            "The declared source-derived interface closure is partial; inspect missingDeclaredObjects and repair it from the pinned target sources."
            if interface_closure is not None else
            "No source-derived interface closure is declared; this contract remains an incomplete draft."
        ),
    }
    if interface_closure is not None:
        for field, values in interface_closure.items():
            resolved_interface_closure[field] = [
                _qualified(integration_id, item) for item in values
            ]

    return {
        "apiVersion": contract["apiVersion"],
        "integration": integration_id,
        "assessmentTimestamp": assessment_timestamp,
        "declarationValid": True,
        "integrationComplete": not integration_blockers,
        "integrationBlockers": integration_blockers,
        "readinessHolds": [item for item in diagnostics if item["code"] not in INTEGRATION_BLOCKER_CODES],
        "grantsEffectAuthority": False,
        "authorityStatement": "This declarative preflight grants no effect authority and does not override any permission or owner boundary.",
        "assessmentProvenance": contract["assessment"],
        "assessmentLimits": [
            "V1 validates declarations and recorded facts only; it does not authenticate issuers or execute legacy verifiers.",
            "Externally accepted is a provenance-limited legacy disposition, not a V1 acceptance verdict.",
            "Owner-choice validation checks distinct encoded strings but cannot prove philosophical materiality.",
            "Logical principal declarations and allowlists do not authenticate an OS account, session or credential.",
            "Integration completeness checks the declared source-derived interface closure and its wiring; it does not introspect prose, prove runtime readiness, handoff custody or external acceptance.",
        ],
        "interfaceClosure": resolved_interface_closure,
        "qualifiedIdentities": {
            name: [_qualified(integration_id, item["id"]) for item in contract[name]]
            for name in ("owners", "operations", "gates", "credentials", "receipts", "authorities", "resourceRules", "privacyEgress")
        },
        "gateDispositions": gate_dispositions,
        "invocationChecklist": [{
            "operation": _qualified(integration_id, item["id"]),
            "executionClass": item["executionClass"],
            "principal": None if item["invocationBinding"] is None else _qualified(integration_id, item["invocationBinding"]["principalRef"]),
            "authority": None if item["invocationBinding"] is None else _qualified(integration_id, item["invocationBinding"]["authorityRef"]),
        } for item in contract["operations"]],
        "executionBoundaryChecklist": [{
            "operation": _qualified(integration_id, item["id"]),
            "executionClass": item["executionClass"],
            "declared": "executionBoundary" in item,
            "boundary": item.get("executionBoundary"),
        } for item in contract["operations"]],
        "operations": operation_results,
        "credentialChecklist": [{
            "credential": _qualified(integration_id, item["id"]), "purpose": item["purpose"],
            "readiness": item["readiness"], "authorizedConsumers": item["authorizedConsumers"],
            "authorizedPrincipals": [_qualified(integration_id, ref) for ref in item["authorizedPrincipalRefs"]],
            "scopeVerification": item["scopeVerification"],
            "recordedAuthorityScope": [_qualified(integration_id, ref) for ref in item["authorityGrantedRefs"]],
            "explicitlyNotGranted": [_qualified(integration_id, ref) for ref in item["authorityNotGrantedRefs"]],
        } for item in contract["credentials"]],
        "evidenceChecklist": [{
            "receipt": _qualified(integration_id, item["id"]), "schemaType": item["schemaType"],
            "issuer": _qualified(integration_id, item["issuerOwnerRef"]),
            "issuerAuthority": _qualified(integration_id, item["issuerAuthorityRef"]), "disposition": item["disposition"],
            "artifactIdentity": item["artifactIdentity"], "custody": item["custody"],
            "evidenceBasisStatus": item["evidenceBasisStatus"],
            "artifactIdentityStatus": item["artifactIdentityStatus"], "custodyStatus": item["custodyStatus"],
            "v1Verified": False,
        } for item in contract["receipts"]],
        "producedEvidence": [{
            "operation": _qualified(integration_id, operation["id"]),
            "owedReceiptRefs": [_qualified(integration_id, item) for item in operation["producedReceiptRefs"]],
        } for operation in contract["operations"] if operation["producedReceiptRefs"]],
        "ownerDecisions": [{**item, "id": _qualified(integration_id, item["id"]), "ownerRef": _qualified(integration_id, item["ownerRef"])} for item in contract["ownerDecisions"]],
        "autonomousRepairs": [{**item, "id": _qualified(integration_id, item["id"])} for item in contract["autonomousRepairs"]],
        "resourceChecklist": contract["resourceRules"],
        "cleanupRestrictions": contract["cleanupRules"],
        "diagnostics": diagnostics,
    }


def repair_query(document: Any, *, category: str, changed_boundaries: list[str]) -> dict[str, Any]:
    contract = validate_contract(document)
    protected = set(contract["repairAuthority"]["protectedBoundaries"])
    declared = set(changed_boundaries)
    owner_boundaries = sorted((declared & protected) | ({category} if category in protected else set()))
    known_autonomous = {"implementation", "composition", "test", "documentation"}
    unknown_boundaries = sorted(declared - protected - known_autonomous)
    allowed_category = category in contract["repairAuthority"]["allowedCategories"]
    allowed = allowed_category and not owner_boundaries and not unknown_boundaries
    return {
        "integration": contract["integration"]["id"],
        "category": category,
        "changedBoundaries": sorted(declared),
        "allowedByDeclaredStandingRepairAuthority": allowed,
        "requiresExistingOwnerDecision": bool(owner_boundaries) or bool(unknown_boundaries) or not allowed_category,
        "ownerDecisionBoundaries": owner_boundaries,
        "unknownBoundaries": unknown_boundaries,
        "statement": "Declaration check only; this result does not inspect code, establish caller honesty, or grant effect authority.",
        "grantsEffectAuthority": False,
    }
