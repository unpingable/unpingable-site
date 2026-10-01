from __future__ import annotations

import copy
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from .parser import ContractParseError, load_contract, loads_contract
from .preflight import preflight, repair_query
from .validator import ContractValidationError, validate_contract
from .cli import _emit


ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "constellation/integration-contracts/v1/vectors"


def replace_pointer(document, pointer: str, value) -> None:
    parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]]
    target = document
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    last = parts[-1]
    if isinstance(target, list): target[int(last)] = value
    else: target[last] = value


def refresh_interface_closure(document) -> None:
    """Keep unrelated mutation vectors focused on their named qualification case."""
    closure = document.setdefault("interfaceClosure", {})
    for field, collection in (
        ("basisSourceRefs", "sources"),
        ("ownerRefs", "owners"),
        ("authorityRefs", "authorities"),
        ("operationRefs", "operations"),
        ("gateRefs", "gates"),
        ("credentialRefs", "credentials"),
        ("receiptRefs", "receipts"),
        ("resourceRuleRefs", "resourceRules"),
        ("privacyRuleRefs", "privacyEgress"),
        ("cleanupRuleRefs", "cleanupRules"),
    ):
        closure[field] = [item["id"] for item in document[collection]]


def establish_execution_boundary(document, operation_id: str) -> None:
    """Add an explicit ordinary-identity boundary to a synthetic test operation."""
    operation = next(item for item in document["operations"] if item["id"] == operation_id)
    binding = operation["invocationBinding"]
    if operation["executionClass"] != "runtime" or binding is None:
        raise ValueError("fixture operation must be a bound runtime operation")
    receipt_ref = (operation["producedReceiptRefs"] or operation["requiredReceiptRefs"] or [document["receipts"][0]["id"]])[0]
    identity = "synthetic ordinary runtime identity"
    operation["executionBoundary"] = {
        "status": "established", "unresolvedReason": None,
        "baselinePlatformIdentity": identity, "operationPlatformIdentity": identity,
        "baselineCapabilities": [], "operationCapabilities": [], "platformMediation": "direct synthetic runtime invocation",
        "delegatedPrimitives": [], "delegatedExecutors": [], "sharedExclusions": [],
        "technicalVisibilityFacts": [{
            "id": "runtime-input-visibility", "fact": "declared runtime inputs are readable",
            "interfaces": [f"{operation['consumer']} synthetic runtime interface"],
            "requiredPlatformIdentity": identity, "requiredCapabilities": [],
            "visibilityPurpose": "observation-input",
            "claimKind": "input-state",
            "coverage": {"kind": "declared-inputs", "population": "declared-input-set", "completeness": "complete-or-refuse", "namespaceScope": {"pidNamespace": "operation-pid-namespace", "userNamespace": "operation-user-namespace", "procfsVisibility": "not-applicable"}, "bindingReceiptRefs": []},
            "delegatedPrimitiveRef": None,
            "temporalScope": "point-in-time", "sharedExclusionRef": None,
            "establishesExclusion": False, "onIncomplete": "refuse",
            "downstreamReceiptRefs": [receipt_ref],
            "downstreamClaim": "the named fixture claim uses complete declared inputs and establishes no resource exclusion",
        }],
        "authoritySemantics": {
            "principalRef": binding["principalRef"], "authorityRef": binding["authorityRef"],
            "platformIdentityConveysAuthority": False,
        },
        "outputCustody": {
            "writerIdentity": identity, "ownerIdentity": "synthetic receipt custodian",
            "mode": "synthetic custody contract", "pathnameReplacementBoundary": "synthetic custody contract",
            "separatedFromObservationPrivilege": True, "justifiesOperationPrivilege": False,
            "receiptRefs": [receipt_ref],
            "claim": "custody is independent from runtime visibility",
        },
        "campaignConvention": {"requirements": [], "establishesTechnicalRequirement": False},
        "leastPrivilegeAlternative": {
            "unprivilegedEquivalence": "exact", "description": "ordinary fixture identity has complete visibility",
            "delegatedPrimitiveRefs": [], "broaderPrivilegeRefused": True,
        },
    }


def bind_all_owner_coverage_receipt(document, operation_id: str) -> None:
    """Attach the typed exact-domain role required by an all-owner census."""
    operation = next(item for item in document["operations"] if item["id"] == operation_id)
    boundary = operation["executionBoundary"]
    fact = boundary["technicalVisibilityFacts"][0]
    primitive = next(item for item in boundary["delegatedPrimitives"] if item["id"] == fact["delegatedPrimitiveRef"])
    coverage = fact["coverage"]
    role = {
        "kind": "observation-coverage-domain", "operationRef": operation_id,
        "factRef": fact["id"], "primitiveRef": primitive["id"],
        "primitiveIdentityPin": primitive["identity"]["identityPin"],
        "coverageKind": coverage["kind"], "population": coverage["population"],
        "completeness": coverage["completeness"],
        "namespaceScope": copy.deepcopy(coverage["namespaceScope"]),
    }
    for receipt_ref in coverage["bindingReceiptRefs"]:
        receipt = next(item for item in document["receipts"] if item["id"] == receipt_ref)
        receipt["schemaType"] = "constellation.observation-coverage-domain/v1"
        receipt["semanticRoles"] = [copy.deepcopy(role)]


class ContractConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = load_contract(VECTORS / "base-valid.json")
        cls.golden = load_contract(VECTORS / "golden-vectors.json")
        cls.negative = load_contract(VECTORS / "negative-vectors.json")

    def mutated(self, case):
        document = copy.deepcopy(self.base)
        for mutation in case.get("mutations", []):
            replace_pointer(document, mutation["pointer"], mutation["value"])
        # Existing invocation vectors predate executionBoundary. Keep their
        # otherwise unrelated mutation focused on invocation-kind semantics.
        if not any(mutation["pointer"].startswith("/operations/") and "/executionBoundary" in mutation["pointer"] for mutation in case.get("mutations", [])):
            for operation in document["operations"]:
                if operation.get("executionClass") == "runtime" and operation.get("executionBoundary") is not None and operation.get("invocationBinding") is not None:
                    operation["executionBoundary"]["authoritySemantics"]["principalRef"] = operation["invocationBinding"]["principalRef"]
                    operation["executionBoundary"]["authoritySemantics"]["authorityRef"] = operation["invocationBinding"]["authorityRef"]
        refresh_interface_closure(document)
        return document

    def result_operation(self, result, local_id):
        return next(item for item in result["operations"] if item["operation"].endswith("/" + local_id))

    def test_shared_golden_vectors(self):
        self.assertGreaterEqual(len(self.golden["cases"]), 12)
        for case in self.golden["cases"]:
            with self.subTest(case=case["id"]):
                document = self.mutated(case)
                if "repairQuery" in case:
                    query = case["repairQuery"]
                    result = repair_query(document, category=query["category"], changed_boundaries=query["changedBoundaries"])
                    for key, value in case["expected"].items(): self.assertEqual(result[key], value)
                    continue
                result = preflight(document, assessment_timestamp="2030-01-02T00:00:00Z")
                expected = case["expected"]
                if "integrationComplete" in expected:
                    self.assertEqual(result["integrationComplete"], expected["integrationComplete"])
                if "integrationBlockerCodes" in expected:
                    self.assertEqual({item["code"] for item in result["integrationBlockers"]}, set(expected["integrationBlockerCodes"]))
                if "qualifiedGate" in expected:
                    self.assertEqual(result["gateDispositions"][0]["gate"], expected["qualifiedGate"])
                    self.assertNotEqual(result["gateDispositions"][0]["gate"], expected["mustDifferFrom"])
                for operation_id, disposition in expected.get("operationDispositions", {}).items():
                    self.assertEqual(self.result_operation(result, operation_id)["disposition"], disposition)
                if "operation" in expected:
                    operation = self.result_operation(result, expected["operation"])
                    self.assertEqual(operation["disposition"], expected["disposition"])
                    codes = {item["code"] for item in operation["blockers"]}
                    self.assertTrue(set(expected.get("blockerCodes", [])) <= codes)
                    self.assertFalse(set(expected.get("absentBlockerCodes", [])) & codes)
                elif expected.get("blockerCodes"):
                    codes = {item["code"] for item in result["diagnostics"]}
                    self.assertTrue(set(expected["blockerCodes"]) <= codes)

    def test_negative_vectors(self):
        self.assertGreaterEqual(len(self.negative["cases"]), 7)
        for case in self.negative["cases"]:
            with self.subTest(case=case["id"]):
                if case["id"] == "duplicate-json-key":
                    with self.assertRaises(ContractParseError) as caught:
                        loads_contract('{"apiVersion":"a","apiVersion":"b"}')
                elif case["id"] == "non-json-infinity":
                    with self.assertRaises(ContractParseError) as caught:
                        loads_contract('{"value":Infinity}')
                elif case["id"] == "post-parse-nonfinite-number":
                    raw = json.dumps(self.base).replace('"minimum": 100', '"minimum": 1e999')
                    document = loads_contract(raw)
                    with self.assertRaises(ContractValidationError) as caught:
                        validate_contract(document)
                elif case["id"] in {
                    "non-rfc3339-week-date", "invalid-rfc3339-offset-minute",
                    "invalid-rfc3339-offset-hour", "unknown-rfc3339-negative-zero-offset",
                }:
                    timestamp = {
                        "non-rfc3339-week-date": "2030-W01-2T00:00:00Z",
                        "invalid-rfc3339-offset-minute": "2030-01-01T00:00:00+00:60",
                        "invalid-rfc3339-offset-hour": "2030-01-01T00:00:00+24:00",
                        "unknown-rfc3339-negative-zero-offset": "2030-01-01T00:00:00-00:00",
                    }[case["id"]]
                    with self.assertRaises(ContractValidationError) as caught:
                        preflight(self.base, assessment_timestamp=timestamp)
                else:
                    document = self.mutated(case)
                    if case["id"] == "unknown-field": document["unexpected"] = True
                    with self.assertRaises(ContractValidationError) as caught:
                        validate_contract(document)
                self.assertEqual(caught.exception.code, case["errorCode"])

    def test_self_declared_accepted_never_becomes_effect_grant(self):
        result = preflight(self.base, assessment_timestamp="2030-01-02T00:00:00Z")
        self.assertFalse(result["grantsEffectAuthority"])
        effect_operations = [item for item in result["operations"] if item["kind"] in {"local-effect", "external-effect", "production-effect"}]
        self.assertTrue(effect_operations)
        self.assertTrue(all(not item["effectAuthorityGranted"] for item in effect_operations))
        self.assertEqual(self.result_operation(result, "produce")["disposition"], "ready-for-existing-authority-check")

    def test_invocation_binding_does_not_infer_authority_owner(self):
        effect = self.base["operations"][1]
        authority = next(item for item in self.base["authorities"] if item["id"] == effect["invocationBinding"]["authorityRef"])
        self.assertNotEqual(effect["invocationBinding"]["principalRef"], authority["ownerRef"])
        result = preflight(self.base, assessment_timestamp="2030-01-02T00:00:00Z")
        resolved = self.result_operation(result, "effect")
        self.assertEqual(resolved["invocationBinding"]["principal"], "vector/invoker")
        self.assertEqual(resolved["disposition"], "permitted-by-declared-contract")
        self.assertFalse(resolved["effectAuthorityGranted"])

    def test_execution_boundary_shared_vectors(self):
        vectors = load_contract(VECTORS / "execution-boundary-vectors.json")
        for case in vectors["cases"]:
            with self.subTest(case=case["id"]):
                document = copy.deepcopy(self.base)
                operation = next(item for item in document["operations"] if item["id"] == vectors["operation"])
                mutation = case["mutation"]
                if mutation == "remove":
                    operation.pop("executionBoundary")
                else:
                    operation["executionBoundary"] = copy.deepcopy(vectors["boundedCensusBoundary"])
                    bind_all_owner_coverage_receipt(document, vectors["operation"])
                    fact = operation["executionBoundary"]["technicalVisibilityFacts"][0]
                    if mutation == "point-census-claims-exclusion": fact["establishesExclusion"] = True
                    elif mutation == "authority-mismatch": operation["executionBoundary"]["authoritySemantics"]["authorityRef"] = "production-effect"
                    elif mutation == "reservation-without-mechanism":
                        fact["temporalScope"] = "reserved-through-dispatch"; fact["establishesExclusion"] = True
                    elif mutation == "elevate-whole-observer": operation["executionBoundary"]["operationPlatformIdentity"] = "uid:0"
                    elif mutation == "self-label-effect-interface":
                        operation["executionBoundary"]["operationPlatformIdentity"] = "uid:0"
                        fact["visibilityPurpose"] = "effect-interface"
                    elif mutation == "claim-exact-equivalence":
                        operation["executionBoundary"]["leastPrivilegeAlternative"]["unprivilegedEquivalence"] = "exact"
                        operation["executionBoundary"]["leastPrivilegeAlternative"]["delegatedPrimitiveRefs"] = []
                    elif mutation == "allow-incomplete": fact["onIncomplete"] = "continue"
                    elif mutation == "collapse-custody": operation["executionBoundary"]["outputCustody"]["separatedFromObservationPrivilege"] = False
                    elif mutation == "collapse-authority": operation["executionBoundary"]["authoritySemantics"]["platformIdentityConveysAuthority"] = True
                    elif mutation == "convention-as-requirement": operation["executionBoundary"]["campaignConvention"]["establishesTechnicalRequirement"] = True
                    elif mutation == "custody-only-elevation":
                        boundary = operation["executionBoundary"]
                        boundary["operationPlatformIdentity"] = "uid:0 whole observer"
                        boundary["operationCapabilities"] = ["create root-owned receipt"]
                        boundary["leastPrivilegeAlternative"].update({"unprivilegedEquivalence": "none", "delegatedPrimitiveRefs": []})
                    elif mutation == "arbitrary-exclusion-reference":
                        fact.update({"temporalScope": "reserved-through-dispatch", "sharedExclusionRef": "point-census-receipt", "establishesExclusion": True})
                    elif mutation == "incomplete-producer-honoring":
                        operation["executionBoundary"]["sharedExclusions"] = [{
                            "id": "producer-slot", "mechanismIdentity": {"kind": "filesystem-lock", "reference": "/run/fixture.lock", "identityPin": "sha256:" + "1" * 64, "sourceRef": "policy"},
                            "attemptBinding": {"id": "attempt-1", "operationRef": "effect", "supervisorOwnerRef": "invoker", "identitySourceRef": "policy", "identityPin": "sha256:" + "4" * 64, "receiptRef": "accepted-record"},
                            "ownerRef": "invoker", "relevantOperationRefs": ["effect", "produce"], "honoringOperationRefs": ["effect"],
                            "acquisition": {"predicate": "before-observation", "receiptRef": "accepted-record", "direction": "current-input", "availability": "current-accepted", "predecessorReceiptRef": None},
                            "hold": {"predicate": "through-dispatch-handoff", "receiptRef": "custody-record", "direction": "current-input", "availability": "current-accepted", "predecessorReceiptRef": "accepted-record"},
                            "handoff": {"predicate": "to-declared-operation", "targetOperationRef": "effect", "receiptRef": "effect-result", "direction": "future-output", "availability": "owed", "predecessorReceiptRef": "custody-record"},
                            "release": {"predicate": "after-dispatch-handoff", "receiptRef": "release-result", "direction": "future-output", "availability": "owed", "predecessorReceiptRef": "effect-result"},
                        }]
                        fact.update({"temporalScope": "reserved-through-dispatch", "sharedExclusionRef": "producer-slot", "establishesExclusion": True})
                    elif mutation == "primitive-principal-mismatch":
                        operation["executionBoundary"]["delegatedPrimitives"][0]["invokingPlatformPrincipal"] = "uid:0"
                    elif mutation == "primitive-principal-missing":
                        operation["executionBoundary"]["delegatedPrimitives"][0].pop("invokingPlatformPrincipal")
                    elif mutation == "primitive-capability-mismatch":
                        operation["executionBoundary"]["delegatedPrimitives"][0]["requiredCapabilities"] = ["different capability"]
                    elif mutation == "primitive-capability-missing":
                        operation["executionBoundary"]["delegatedPrimitives"][0].pop("requiredCapabilities")
                    elif mutation == "primitive-namespace-mismatch":
                        operation["executionBoundary"]["delegatedPrimitives"][0]["coverage"]["namespaceScope"]["pidNamespace"] = "operation-pid-namespace"
                    elif mutation == "primitive-namespace-missing":
                        operation["executionBoundary"]["delegatedPrimitives"][0]["coverage"].pop("namespaceScope")
                    elif mutation == "primitive-coverage-narrowed":
                        operation["executionBoundary"]["delegatedPrimitives"][0]["coverage"]["kind"] = "invoking-owner-processes"
                    elif mutation == "primitive-identity-floating":
                        operation["executionBoundary"]["delegatedPrimitives"][0]["identity"]["identityPin"] = "whatever-is-installed"
                    elif mutation == "service-identity-floating":
                        primitive = operation["executionBoundary"]["delegatedPrimitives"][0]
                        primitive["identity"].update({"kind": "service-endpoint", "reference": "https://fixture.invalid/census", "identityPin": "whatever-service-is-running"})
                        primitive["command"] = None
                if case["kind"] == "validation":
                    with self.assertRaises(ContractValidationError) as caught: validate_contract(document)
                    self.assertEqual(caught.exception.code, case["expectedCode"])
                else:
                    result = preflight(document, assessment_timestamp=vectors["assessmentTime"])
                    codes = {item["code"] for item in self.result_operation(result, vectors["operation"])["blockers"]}
                    if "expectedCode" in case: self.assertIn(case["expectedCode"], codes)
                    self.assertFalse(set(case.get("absentCodes", [])) & codes)
                    self.assertFalse(result["grantsEffectAuthority"])

    def test_all_uid_coverage_profile_cannot_self_relabel(self):
        vectors = load_contract(VECTORS / "execution-boundary-vectors.json")
        cases = (
            ("uid1000-population", lambda coverage: coverage.update({"population": "invoking-owner-uid"}), "EXECUTION_BOUNDARY_COVERAGE_PROFILE"),
            ("partial-procfs", lambda coverage: coverage["namespaceScope"].update({"procfsVisibility": "invoking-owner-pids-or-refuse"}), "EXECUTION_BOUNDARY_COVERAGE_PROFILE"),
            ("operation-pid-namespace", lambda coverage: coverage["namespaceScope"].update({"pidNamespace": "operation-pid-namespace"}), "EXECUTION_BOUNDARY_COVERAGE_PROFILE"),
            ("missing-domain-binding", lambda coverage: coverage.update({"bindingReceiptRefs": []}), "EXECUTION_BOUNDARY_COVERAGE_BINDING"),
            ("contradictory-prose-field", lambda coverage: coverage.update({"subjectSetRef": "only UID 1000"}), "FIELD_UNKNOWN"),
        )
        for name, mutate, expected in cases:
            with self.subTest(name=name):
                document = copy.deepcopy(self.base)
                boundary = copy.deepcopy(vectors["boundedCensusBoundary"])
                operation = next(item for item in document["operations"] if item["id"] == vectors["operation"])
                operation["executionBoundary"] = boundary
                bind_all_owner_coverage_receipt(document, vectors["operation"])
                for coverage in (boundary["technicalVisibilityFacts"][0]["coverage"], boundary["delegatedPrimitives"][0]["coverage"]):
                    mutate(coverage)
                with self.assertRaises(ContractValidationError) as caught:
                    validate_contract(document)
                self.assertEqual(caught.exception.code, expected)

        document = copy.deepcopy(self.base)
        operation = next(item for item in document["operations"] if item["id"] == vectors["operation"])
        operation["executionBoundary"] = copy.deepcopy(vectors["boundedCensusBoundary"])
        bind_all_owner_coverage_receipt(document, vectors["operation"])
        boundary = operation["executionBoundary"]
        for coverage in (boundary["technicalVisibilityFacts"][0]["coverage"], boundary["delegatedPrimitives"][0]["coverage"]):
            coverage["bindingReceiptRefs"] = ["accepted-record"]
        boundary["technicalVisibilityFacts"][0]["downstreamReceiptRefs"] = ["accepted-record"]
        boundary["delegatedPrimitives"][0]["receiptRefs"] = ["accepted-record"]
        with self.assertRaises(ContractValidationError) as caught:
            validate_contract(document)
        self.assertEqual(caught.exception.code, "EXECUTION_BOUNDARY_COVERAGE_ROLE_MISMATCH")

        for field, value in (("factRef", "other-fact"), ("primitiveRef", "other-primitive")):
            with self.subTest(typed_binding=field):
                changed = copy.deepcopy(self.base)
                next(item for item in changed["operations"] if item["id"] == vectors["operation"])["executionBoundary"] = copy.deepcopy(vectors["boundedCensusBoundary"])
                bind_all_owner_coverage_receipt(changed, vectors["operation"])
                next(item for item in changed["receipts"] if item["id"] == "effect-result")["semanticRoles"][0][field] = value
                with self.assertRaises(ContractValidationError) as caught:
                    validate_contract(changed)
                self.assertEqual(caught.exception.code, "EXECUTION_BOUNDARY_COVERAGE_ROLE_MISMATCH")

    def test_shared_exclusion_requires_identical_cross_producer_lifecycle(self):
        document = copy.deepcopy(self.base)
        attempt_pin = "sha256:" + "4" * 64
        exclusion = {
            "id": "fixture-dispatch-slot", "mechanismIdentity": {"kind": "filesystem-lock", "reference": "/run/fixture-dispatch.lock", "identityPin": "sha256:" + "2" * 64, "sourceRef": "policy"},
            "attemptBinding": {"id": "attempt-1", "operationRef": "effect", "supervisorOwnerRef": "invoker", "identitySourceRef": "policy", "identityPin": attempt_pin, "receiptRef": "attempt-binding", "issuerOwnerRef": "issuer", "issuerAuthorityRef": "exclusion-evidence-acceptance", "authorityEvidenceReceiptRef": "issuer-authority-anchor"},
            "ownerRef": "invoker",
            "relevantOperationRefs": ["effect", "produce"], "honoringOperationRefs": ["effect", "produce"],
            "acquisition": {"predicate": "before-observation", "receiptRef": "exclusion-acquire", "direction": "current-input", "availability": "current-accepted", "predecessorReceiptRef": None, "issuerOwnerRef": "issuer", "issuerAuthorityRef": "exclusion-evidence-acceptance", "authorityEvidenceReceiptRef": "issuer-authority-anchor"},
            "hold": {"predicate": "through-dispatch-handoff", "receiptRef": "exclusion-hold", "direction": "current-input", "availability": "current-accepted", "predecessorReceiptRef": "exclusion-acquire", "issuerOwnerRef": "issuer", "issuerAuthorityRef": "exclusion-evidence-acceptance", "authorityEvidenceReceiptRef": "issuer-authority-anchor"},
            "handoff": {"predicate": "to-declared-operation", "targetOperationRef": "effect", "receiptRef": "exclusion-handoff", "direction": "future-output", "availability": "owed", "predecessorReceiptRef": "exclusion-hold"},
            "release": {"predicate": "after-dispatch-handoff", "receiptRef": "exclusion-release", "direction": "future-output", "availability": "owed", "predecessorReceiptRef": "exclusion-handoff"},
        }
        template = copy.deepcopy(document["receipts"][0])
        document["authorities"].append({
            "id": "root-acceptance", "ownerRef": "root", "kind": "acceptance",
            "boundary": "fixture external authority anchor issuance", "status": "established",
            "authorizedPrincipalRefs": [], "evidenceRefs": [],
        })
        document["authorities"].append({
            "id": "exclusion-evidence-acceptance", "ownerRef": "issuer", "kind": "acceptance",
            "boundary": "fixture attempt and current exclusion evidence acceptance", "status": "established",
            "authorizedPrincipalRefs": [], "evidenceRefs": ["issuer-authority-anchor"],
        })
        authority_anchor = copy.deepcopy(template)
        authority_anchor.update({
            "id": "issuer-authority-anchor", "schemaType": "fixture.external-authority-anchor/v1",
            "issuerOwnerRef": "root", "issuerAuthorityRef": "root-acceptance",
            "artifactIdentity": "sha256:fixture-issuer-authority-anchor",
            "downstreamConsumers": ["effect", "produce"], "semanticRoles": [],
        })
        document["receipts"].append(authority_anchor)
        attempt_receipt = copy.deepcopy(template)
        attempt_receipt.update({
            "id": "attempt-binding", "schemaType": "constellation.operation-attempt-binding/v1",
            "issuerAuthorityRef": "exclusion-evidence-acceptance",
            "artifactIdentity": attempt_pin, "downstreamConsumers": ["effect", "produce"],
            "semanticRoles": [{"kind": "operation-attempt-binding", "bindingRef": "attempt-1", "operationRef": "effect", "supervisorOwnerRef": "invoker", "identitySourceRef": "policy", "identityPin": attempt_pin}],
        })
        document["receipts"].append(attempt_receipt)
        roles = (
            ("exclusion-acquire", "shared-exclusion-acquire", "before-observation", "current-input", "current-accepted", "owner", "invoker", None),
            ("exclusion-hold", "shared-exclusion-hold", "through-dispatch-handoff", "current-input", "current-accepted", "owner", "invoker", "exclusion-acquire"),
            ("exclusion-handoff", "shared-exclusion-handoff", "to-declared-operation", "future-output", "owed", "operation", "effect", "exclusion-hold"),
            ("exclusion-release", "shared-exclusion-release", "after-dispatch-handoff", "future-output", "owed", "operation", "effect", "exclusion-handoff"),
        )
        for ordinal, (receipt_id, role_kind, predicate, direction, availability, producer_kind, producer_ref, predecessor) in enumerate(roles):
            receipt = copy.deepcopy(template)
            receipt.update({
                "id": receipt_id, "schemaType": "constellation.shared-exclusion-phase/v1",
                "downstreamConsumers": ["effect", "produce"],
                "semanticRoles": [{"kind": role_kind, "mechanismRef": "fixture-dispatch-slot", "mechanismIdentityPin": "sha256:" + "2" * 64, "attemptBindingRef": "attempt-1", "attemptIdentityPin": attempt_pin, "ownerRef": "invoker", "producerOperationRefs": ["effect", "produce"], "phaseOrdinal": ordinal, "predecessorReceiptRef": predecessor, "direction": direction, "availability": availability, "producerKind": producer_kind, "producerRef": producer_ref, "predicate": predicate}],
            })
            if availability == "current-accepted":
                receipt["issuerAuthorityRef"] = "exclusion-evidence-acceptance"
            if availability == "owed":
                receipt.update({"disposition": "missing", "artifactIdentity": "not yet produced", "artifactIdentityStatus": "missing", "custody": "not yet retained", "custodyStatus": "missing"})
            document["receipts"].append(receipt)
        document["gates"][0]["requiredReceiptRefs"].extend(["issuer-authority-anchor", "attempt-binding", "exclusion-acquire", "exclusion-hold"])
        for operation_id in ("effect", "produce"):
            next(item for item in document["operations"] if item["id"] == operation_id)["requiredReceiptRefs"].append("issuer-authority-anchor")
        next(item for item in document["operations"] if item["id"] == "effect")["producedReceiptRefs"].extend(["exclusion-handoff", "exclusion-release"])
        for operation_id in ("effect", "produce"):
            operation = next(item for item in document["operations"] if item["id"] == operation_id)
            operation["executionBoundary"]["sharedExclusions"] = [copy.deepcopy(exclusion)]
            fact = operation["executionBoundary"]["technicalVisibilityFacts"][0]
            fact.update({
                "temporalScope": "reserved-through-dispatch",
                "sharedExclusionRef": "fixture-dispatch-slot",
                "establishesExclusion": True,
            })
        refresh_interface_closure(document)
        validate_contract(document)
        result = preflight(document, assessment_timestamp="2030-01-02T00:00:00Z")
        self.assertTrue(result["integrationComplete"])
        self.assertFalse(result["grantsEffectAuthority"])
        effect_outputs = next(item for item in result["producedEvidence"] if item["operation"] == "vector/effect")["owedReceiptRefs"]
        self.assertIn("vector/exclusion-handoff", effect_outputs)
        self.assertIn("vector/exclusion-release", effect_outputs)

        def substitute_current_evidence_anchor(item, phases):
            item["owners"].append({
                "id": "substitute-issuer", "name": "Substitute issuer", "status": "resolved",
                "boundary": "local substitution fixture", "evidenceRefs": ["substitute-authority-anchor"],
            })
            item["authorities"].append({
                "id": "substitute-acceptance", "ownerRef": "substitute-issuer", "kind": "acceptance",
                "boundary": "local substitution fixture", "status": "established",
                "authorizedPrincipalRefs": [], "evidenceRefs": ["substitute-authority-anchor"],
            })
            anchor = copy.deepcopy(next(receipt for receipt in item["receipts"] if receipt["id"] == "issuer-authority-anchor"))
            anchor.update({"id": "substitute-authority-anchor", "artifactIdentity": "sha256:substitute-authority-anchor"})
            item["receipts"].append(anchor)
            for operation_id in ("effect", "produce"):
                exclusion_item = next(operation for operation in item["operations"] if operation["id"] == operation_id)["executionBoundary"]["sharedExclusions"][0]
                for phase in phases:
                    declaration = exclusion_item["attemptBinding"] if phase == "attempt" else exclusion_item[phase]
                    declaration.update({
                        "issuerOwnerRef": "substitute-issuer",
                        "issuerAuthorityRef": "substitute-acceptance",
                        "authorityEvidenceReceiptRef": "substitute-authority-anchor",
                    })
            receipt_ids = {"attempt": "attempt-binding", "acquisition": "exclusion-acquire", "hold": "exclusion-hold"}
            for phase in phases:
                evidence = next(receipt for receipt in item["receipts"] if receipt["id"] == receipt_ids[phase])
                evidence.update({"issuerOwnerRef": "substitute-issuer", "issuerAuthorityRef": "substitute-acceptance"})
            for operation_id in ("effect", "produce"):
                operation = next(operation for operation in item["operations"] if operation["id"] == operation_id)
                operation["requiredReceiptRefs"] = ["substitute-authority-anchor" if ref == "issuer-authority-anchor" else ref for ref in operation["requiredReceiptRefs"]]
            for gate in item["gates"]:
                gate["requiredReceiptRefs"] = ["substitute-authority-anchor" if ref == "issuer-authority-anchor" else ref for ref in gate["requiredReceiptRefs"]]
            refresh_interface_closure(item)

        def move_acquisition_after_observation(item):
            for operation_id in ("effect", "produce"):
                next(operation for operation in item["operations"] if operation["id"] == operation_id)["executionBoundary"]["sharedExclusions"][0]["acquisition"]["predicate"] = "before-dispatch"
            next(receipt for receipt in item["receipts"] if receipt["id"] == "exclusion-acquire")["semanticRoles"][0]["predicate"] = "before-dispatch"

        controls = (
            ("arbitrary-phase-prose", lambda item: item["operations"][1]["executionBoundary"]["sharedExclusions"][0]["acquisition"].update({"predicate": "whenever it seems safe"}), "VALUE_ENUM"),
            ("point-census-schema-is-not-exclusion", lambda item: next(receipt for receipt in item["receipts"] if receipt["id"] == "exclusion-acquire").update({"schemaType": "constellation.process-census/v1"}), "EXECUTION_BOUNDARY_EXCLUSION_RECEIPT_SCHEMA"),
            ("missing-future-output-is-not-current-witness", lambda item: [op["executionBoundary"]["sharedExclusions"][0]["acquisition"].update({"receiptRef": "effect-result"}) or op["executionBoundary"]["sharedExclusions"][0]["hold"].update({"predecessorReceiptRef": "effect-result"}) for op in item["operations"] if op["id"] in {"effect", "produce"}] + [next(receipt for receipt in item["receipts"] if receipt["id"] == "effect-result").update({"issuerAuthorityRef": "exclusion-evidence-acceptance"})], "EXECUTION_BOUNDARY_EXCLUSION_EVIDENCE_UNACCEPTED"),
            ("role-attempt-must-match", lambda item: next(receipt for receipt in item["receipts"] if receipt["id"] == "exclusion-hold")["semanticRoles"][0].update({"attemptBindingRef": "other-attempt"}), "EXECUTION_BOUNDARY_EXCLUSION_ROLE_MISMATCH"),
            ("mechanism-pin-must-be-exact", lambda item: item["operations"][1]["executionBoundary"]["sharedExclusions"][0]["mechanismIdentity"].update({"identityPin": "whatever lock is present"}), "EXECUTION_BOUNDARY_PRIMITIVE_IDENTITY"),
            ("future-output-cannot-be-prepopulated", lambda item: next(receipt for receipt in item["receipts"] if receipt["id"] == "exclusion-handoff").update({"disposition": "externally-accepted", "artifactIdentityStatus": "recorded", "custodyStatus": "recorded"}), "EXECUTION_BOUNDARY_EXCLUSION_OUTPUT_PREPOPULATED"),
            ("unrelated-handoff-target", lambda item: [op["executionBoundary"]["sharedExclusions"][0]["handoff"].update({"targetOperationRef": "prepare"}) for op in item["operations"] if op["id"] in {"effect", "produce"}], "EXECUTION_BOUNDARY_EXCLUSION_HANDOFF_TARGET"),
            ("broken-phase-chain", lambda item: [op["executionBoundary"]["sharedExclusions"][0]["release"].update({"predecessorReceiptRef": "exclusion-hold"}) for op in item["operations"] if op["id"] in {"effect", "produce"}], "EXECUTION_BOUNDARY_EXCLUSION_ORDER"),
            ("attempt-role-substitution", lambda item: next(receipt for receipt in item["receipts"] if receipt["id"] == "attempt-binding")["semanticRoles"][0].update({"operationRef": "produce"}), "EXECUTION_BOUNDARY_ATTEMPT_ROLE_MISMATCH"),
            ("attempt-self-issued", lambda item: [op["executionBoundary"]["sharedExclusions"][0]["attemptBinding"].update({"supervisorOwnerRef": "issuer"}) for op in item["operations"] if op["id"] in {"effect", "produce"}] + [next(receipt for receipt in item["receipts"] if receipt["id"] == "attempt-binding")["semanticRoles"][0].update({"supervisorOwnerRef": "issuer"})], "EXECUTION_BOUNDARY_ATTEMPT_SELF_ISSUED"),
            ("attempt-issuer-substitution", lambda item: next(receipt for receipt in item["receipts"] if receipt["id"] == "attempt-binding").update({"issuerOwnerRef": "root", "issuerAuthorityRef": "root-acceptance"}), "EXECUTION_BOUNDARY_EVIDENCE_ISSUER_MISMATCH"),
            ("current-phase-issuer-substitution", lambda item: [next(receipt for receipt in item["receipts"] if receipt["id"] == receipt_id).update({"issuerOwnerRef": "root", "issuerAuthorityRef": "root-acceptance"}) for receipt_id in ("exclusion-acquire", "exclusion-hold")], "EXECUTION_BOUNDARY_EVIDENCE_ISSUER_MISMATCH"),
            ("current-authority-anchor-removed", lambda item: next(authority for authority in item["authorities"] if authority["id"] == "exclusion-evidence-acceptance").update({"evidenceRefs": []}), "EXECUTION_BOUNDARY_EVIDENCE_AUTHORITY_UNANCHORED"),
            ("attempt-artifact-substitution", lambda item: next(receipt for receipt in item["receipts"] if receipt["id"] == "attempt-binding").update({"artifactIdentity": "sha256:" + "9" * 64}), "EXECUTION_BOUNDARY_ATTEMPT_IDENTITY_MISMATCH"),
            ("stale-phase-attempt-identity", lambda item: next(receipt for receipt in item["receipts"] if receipt["id"] == "exclusion-hold")["semanticRoles"][0].update({"attemptIdentityPin": "sha256:" + "9" * 64}), "EXECUTION_BOUNDARY_EXCLUSION_ROLE_MISMATCH"),
            ("substituted-phase-mechanism-identity", lambda item: next(receipt for receipt in item["receipts"] if receipt["id"] == "exclusion-hold")["semanticRoles"][0].update({"mechanismIdentityPin": "sha256:" + "9" * 64}), "EXECUTION_BOUNDARY_EXCLUSION_ROLE_MISMATCH"),
            ("one-receipt-cannot-carry-two-phases", lambda item: next(receipt for receipt in item["receipts"] if receipt["id"] == "exclusion-acquire")["semanticRoles"].append(copy.deepcopy(next(receipt for receipt in item["receipts"] if receipt["id"] == "exclusion-hold")["semanticRoles"][0])), "EXECUTION_BOUNDARY_EXCLUSION_ROLE_REUSE"),
            ("phase-receipt-identity-cannot-be-reused", lambda item: [(op["executionBoundary"]["sharedExclusions"][0]["hold"].update({"receiptRef": "exclusion-acquire"}), op["executionBoundary"]["sharedExclusions"][0]["handoff"].update({"predecessorReceiptRef": "exclusion-acquire"})) for op in item["operations"] if op["id"] in {"effect", "produce"}], "EXECUTION_BOUNDARY_EXCLUSION_RECEIPT_REUSE"),
            ("reservation-acquired-after-observation", move_acquisition_after_observation, "EXECUTION_BOUNDARY_EXCLUSION_OBSERVATION_ORDER"),
            ("future-output-cannot-be-current-gate-input", lambda item: item["gates"][0]["requiredReceiptRefs"].append("exclusion-handoff"), "EXECUTION_BOUNDARY_EXCLUSION_OUTPUT_AS_INPUT"),
        )
        for case, mutate, expected in controls:
            with self.subTest(case=case):
                changed = copy.deepcopy(document)
                mutate(changed)
                with self.assertRaises(ContractValidationError) as caught:
                    validate_contract(changed)
                self.assertEqual(caught.exception.code, expected)

        # A coherent rewrite of the accepted contract may select another
        # externally accepted anchor. V1 validates that declaration but does
        # not authenticate it or grant effect authority; the accepted source
        # identity and independent review remain the substitution boundary.
        coherent = copy.deepcopy(document)
        substitute_current_evidence_anchor(coherent, ("attempt", "acquisition", "hold"))
        validate_contract(coherent)
        coherent_result = preflight(coherent, assessment_timestamp="2030-01-02T00:00:00Z")
        self.assertFalse(coherent_result["grantsEffectAuthority"])
        self.assertTrue(any("does not authenticate issuers" in limit for limit in coherent_result["assessmentLimits"]))

        document["operations"][2]["executionBoundary"]["sharedExclusions"][0]["hold"]["receiptRef"] = "exclusion-acquire"
        with self.assertRaises(ContractValidationError) as caught:
            validate_contract(document)
        self.assertEqual(caught.exception.code, "EXECUTION_BOUNDARY_EXCLUSION_ORDER")

    def test_delegated_effect_executor_is_authority_bound_not_operation_elevation(self):
        document = copy.deepcopy(self.base)
        operation = next(item for item in document["operations"] if item["id"] == "effect")
        boundary = operation["executionBoundary"]
        boundary["delegatedExecutors"] = [{
            "id": "fixture-effect-executor",
            "identity": {"kind": "package-artifact", "reference": "pkg:fixture-effect@1", "identityPin": "sha256:" + "3" * 64, "sourceRef": "policy"},
            "command": ["fixture-effect", "--attempt", "exact-attempt"],
            "invokingPlatformPrincipal": boundary["baselinePlatformIdentity"],
            "executionPlatformIdentity": "bounded fixture effect service",
            "requiredCapabilities": ["perform the declared fixture effect"],
            "authorityRef": "local-effect", "operationRef": "effect",
            "onFailure": "indeterminate", "receiptRefs": ["effect-result"],
        }]
        validate_contract(document)
        self.assertEqual(boundary["operationPlatformIdentity"], boundary["baselinePlatformIdentity"])
        self.assertEqual(boundary["operationCapabilities"], boundary["baselineCapabilities"])

        changed = copy.deepcopy(document)
        changed["operations"][1]["executionBoundary"]["delegatedExecutors"][0]["authorityRef"] = "cleanup"
        with self.assertRaises(ContractValidationError) as caught:
            validate_contract(changed)
        self.assertEqual(caught.exception.code, "EXECUTION_BOUNDARY_EXECUTOR_AUTHORITY")

        changed = copy.deepcopy(document)
        changed["operations"][1]["executionBoundary"]["delegatedExecutors"][0]["receiptRefs"] = ["accepted-record"]
        with self.assertRaises(ContractValidationError) as caught:
            validate_contract(changed)
        self.assertEqual(caught.exception.code, "EXECUTION_BOUNDARY_EXECUTOR_RECEIPT_MISMATCH")

    def test_q2_partition_covers_named_runtime_consumers(self):
        document = copy.deepcopy(self.base)
        renamed = {"effect": "Q5b", "produce": "Q6c", "reconcile": "phlogiston-prerequisite"}
        for operation in document["operations"]:
            operation["id"] = renamed.get(operation["id"], operation["id"])
        for collection, keys in (
            (document["gates"], ("blocks", "doesNotBlock")),
            (document["receipts"], ("downstreamConsumers",)),
            (document["resourceRules"], ("applicableOperations",)),
            (document["privacyEgress"], ("applicableOperations",)),
            (document["cleanupRules"], ("operationRefs",)),
        ):
            for item in collection:
                for key in keys:
                    item[key] = [renamed.get(value, value) for value in item[key]]
        prerequisite = next(item for item in document["operations"] if item["id"] == "phlogiston-prerequisite")
        prerequisite["requiredReceiptRefs"] = ["accepted-record"]
        document["receipts"][0]["downstreamConsumers"].append("phlogiston-prerequisite")
        document["gates"][0]["blocks"].append("phlogiston-prerequisite")
        document["gates"][0]["doesNotBlock"].remove("phlogiston-prerequisite")
        refresh_interface_closure(document)

        result = preflight(document, assessment_timestamp="2030-01-02T00:00:00Z")
        self.assertEqual(self.result_operation(result, "prepare")["disposition"], "permitted-by-declared-contract")
        for operation_id in ("Q5b", "Q6c", "phlogiston-prerequisite"):
            codes = {item["code"] for item in self.result_operation(result, operation_id)["blockers"]}
            self.assertFalse({"EVIDENCE_SCOPE_GATE_MISSING", "EVIDENCE_SCOPE_GATE_INCOMPLETE"} & codes)
        self.assertFalse(result["grantsEffectAuthority"])

    def test_invocation_scope_shared_vectors(self):
        vectors = load_contract(VECTORS / "invocation-scope-vectors.json")
        # Reuse the existing normative mutation/expectation runners so these
        # regression vectors have exactly the same semantics as the old corpus.
        runner = ContractConformance("test_shared_golden_vectors")
        runner.base = self.base
        runner.golden = {"cases": vectors["goldenCases"]}
        runner.negative = {"cases": vectors["negativeCases"]}
        runner.test_shared_golden_vectors()
        runner.test_negative_vectors()
        for case in vectors["goldenCases"]:
            with self.subTest(no_effect_grant=case["id"]):
                result = preflight(runner.mutated(case), assessment_timestamp=vectors["assessmentTime"])
                self.assertFalse(result["grantsEffectAuthority"])
                self.assertTrue(all(not op["effectAuthorityGranted"] for op in result["operations"]))

    def test_unresolved_gate_owner_blocks_even_satisfied_label(self):
        document = copy.deepcopy(self.base); document["owners"][0]["status"] = "unresolved"; document["gates"][0]["ownerRef"] = "root"
        result = preflight(document, assessment_timestamp="2030-01-02T00:00:00Z")
        codes = {item["code"] for item in self.result_operation(result, "effect")["blockers"]}
        self.assertIn("GATE_OWNER_UNRESOLVED", codes)

    def test_cleanup_requires_rule_regenerability_and_full_custody(self):
        missing_rule = copy.deepcopy(self.base); missing_rule["cleanupRules"] = []; refresh_interface_closure(missing_rule)
        codes = {item["code"] for item in self.result_operation(preflight(missing_rule, assessment_timestamp="2030-01-02T00:00:00Z"), "cleanup")["blockers"]}
        self.assertIn("CLEANUP_RULE_MISSING", codes)
        nonregenerable = copy.deepcopy(self.base); nonregenerable["cleanupRules"][0]["regenerable"] = False
        codes = {item["code"] for item in self.result_operation(preflight(nonregenerable, assessment_timestamp="2030-01-02T00:00:00Z"), "cleanup")["blockers"]}
        self.assertIn("CLEANUP_NOT_REGENERABLE", codes)
        unresolved_issuer = copy.deepcopy(self.base); unresolved_issuer["owners"][1]["status"] = "unresolved"
        codes = {item["code"] for item in self.result_operation(preflight(unresolved_issuer, assessment_timestamp="2030-01-02T00:00:00Z"), "cleanup")["blockers"]}
        self.assertTrue({"EVIDENCE_ISSUER_UNRESOLVED", "CLEANUP_CUSTODY_UNSATISFIED"} <= codes)

    def test_owner_decision_blocks_only_affected_operation(self):
        document = copy.deepcopy(self.base)
        document["ownerDecisions"] = [{"id": "route", "ownerRef": "root", "kind": "choice", "missingField": "route", "rationale": "evidence does not choose", "evidenceSearch": "fixture", "affectedOperations": ["produce"], "choices": ["a", "b"]}]
        result = preflight(document, assessment_timestamp="2030-01-02T00:00:00Z")
        self.assertEqual(self.result_operation(result, "prepare")["disposition"], "permitted-by-declared-contract")
        codes = {item["code"] for item in self.result_operation(result, "produce")["blockers"]}
        self.assertIn("OWNER_DECISION_UNRESOLVED", codes)

    def test_time_boundary_uses_explicit_time_and_supported_clock_only(self):
        document = copy.deepcopy(self.base)
        document["gates"][0]["timeBoundary"] = {"notBefore": "2030-02-01T00:00:00Z", "clockContractRef": "rfc3339-utc", "assessment": "reached"}
        early = preflight(document, assessment_timestamp="2030-01-02T00:00:00Z")
        self.assertIn("TIME_NOT_REACHED", {item["code"] for item in self.result_operation(early, "effect")["blockers"]})
        document["gates"][0]["timeBoundary"]["clockContractRef"] = "fixture-owner-clock"
        unsupported = preflight(document, assessment_timestamp="2030-03-02T00:00:00Z")
        self.assertIn("TIME_CLOCK_UNSUPPORTED", {item["code"] for item in self.result_operation(unsupported, "effect")["blockers"]})

    def test_present_credential_with_unverified_scope_blocks(self):
        document = copy.deepcopy(self.base); document["credentials"][0]["scopeVerification"] = "unverified"
        result = preflight(document, assessment_timestamp="2030-01-02T00:00:00Z")
        self.assertIn("CREDENTIAL_SCOPE_UNVERIFIED", {item["code"] for item in self.result_operation(result, "effect")["blockers"]})

    def test_assessment_time_requires_explicit_rfc3339_offset(self):
        for timestamp in ("2030-01-02", "2030-W01-2T00:00:00Z", "2030-01-02T00:00:00"):
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(ContractValidationError) as caught:
                    preflight(self.base, assessment_timestamp=timestamp)
                self.assertEqual(caught.exception.code, "ASSESSMENT_TIME_INVALID")

    def test_issuer_authority_cycle_is_scoped_and_fail_closed(self):
        document = copy.deepcopy(self.base)
        document["authorities"][5]["evidenceRefs"] = ["accepted-record"]
        result = preflight(document, assessment_timestamp="2030-01-02T00:00:00Z")
        effect_codes = {item["code"] for item in self.result_operation(result, "effect")["blockers"]}
        self.assertIn("EVIDENCE_ISSUER_AUTHORITY_CYCLE", effect_codes)

    def test_issuer_authority_evidence_dependencies_are_bounded_and_checked(self):
        missing_dependency = copy.deepcopy(self.base)
        missing_dependency["authorities"][5]["evidenceRefs"] = ["effect-result"]
        result = preflight(missing_dependency, assessment_timestamp="2030-01-02T00:00:00Z")
        for operation_id in ("effect", "produce", "cleanup"):
            codes = {item["code"] for item in self.result_operation(result, operation_id)["blockers"]}
            self.assertIn("EVIDENCE_NOT_EXTERNALLY_ACCEPTED", codes)
        self.assertEqual(self.result_operation(result, "prepare")["disposition"], "permitted-by-declared-contract")

        two_receipt_cycle = copy.deepcopy(self.base)
        two_receipt_cycle["authorities"].append({
            "id": "other-acceptance", "ownerRef": "issuer", "kind": "acceptance",
            "boundary": "second existing fixture acceptance boundary", "status": "established",
            "authorizedPrincipalRefs": [],
            "evidenceRefs": ["accepted-record"],
        })
        two_receipt_cycle["authorities"][5]["evidenceRefs"] = ["custody-record"]
        two_receipt_cycle["receipts"][1]["issuerAuthorityRef"] = "other-acceptance"
        result = preflight(two_receipt_cycle, assessment_timestamp="2030-01-02T00:00:00Z")
        codes = {item["code"] for item in self.result_operation(result, "effect")["blockers"]}
        self.assertIn("EVIDENCE_ISSUER_AUTHORITY_CYCLE", codes)

    def test_privacy_authority_evidence_is_checked(self):
        document = copy.deepcopy(self.base)
        document["authorities"][3]["evidenceRefs"] = ["effect-result"]
        result = preflight(document, assessment_timestamp="2030-01-02T00:00:00Z")
        codes = {item["code"] for item in self.result_operation(result, "produce")["blockers"]}
        self.assertIn("EVIDENCE_NOT_EXTERNALLY_ACCEPTED", codes)




    def test_parser_refuses_symlink_and_bounds_size(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); regular = root / "contract.json"; link = root / "link.json"
            regular.write_text("{}")
            link.symlink_to(regular)
            with self.assertRaises(ContractParseError) as symlink_error: load_contract(link)
            self.assertEqual(symlink_error.exception.code, "READ_NOT_REGULAR")
            large = root / "large.json"; large.write_bytes(b" " * (1_048_576 + 1))
            with self.assertRaises(ContractParseError) as size_error: load_contract(large)
            self.assertEqual(size_error.exception.code, "PARSE_SIZE_LIMIT")


if __name__ == "__main__":
    unittest.main()
