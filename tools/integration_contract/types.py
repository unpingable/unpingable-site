"""Small public result types; contracts remain immutable JSON mappings."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, TypedDict


ExecutionClass = Literal["source-only", "runtime"]


class InvocationBinding(TypedDict):
    """Logical invocation provenance; these are contract IDs, not OS identities."""

    principalRef: str
    authorityRef: str


class TechnicalVisibilityFact(TypedDict):
    """One load-bearing observed fact and its fail-closed visibility boundary."""

    id: str
    fact: str
    interfaces: list[str]
    requiredPlatformIdentity: str
    requiredCapabilities: list[str]
    visibilityPurpose: Literal["observation-input"]
    claimKind: Literal["producer-absence", "input-state", "endpoint-state"]
    coverage: Mapping[str, Any]
    delegatedPrimitiveRef: str | None
    temporalScope: Literal["point-in-time", "continuous-observation", "reserved-through-dispatch"]
    sharedExclusionRef: str | None
    establishesExclusion: bool
    onIncomplete: Literal["refuse"]
    downstreamReceiptRefs: list[str]
    downstreamClaim: str


class ExecutionBoundary(TypedDict):
    """Runtime platform facts kept separate from logical authority and custody."""

    status: Literal["established", "unresolved"]
    unresolvedReason: str | None
    baselinePlatformIdentity: str
    baselineCapabilities: list[str]
    operationPlatformIdentity: str
    operationCapabilities: list[str]
    platformMediation: str
    delegatedPrimitives: list[Mapping[str, Any]]
    delegatedExecutors: list[Mapping[str, Any]]
    sharedExclusions: list[Mapping[str, Any]]
    technicalVisibilityFacts: list[TechnicalVisibilityFact]
    authoritySemantics: Mapping[str, Any]
    outputCustody: Mapping[str, Any]
    campaignConvention: Mapping[str, Any]
    leastPrivilegeAlternative: Mapping[str, Any]


@dataclass(frozen=True)
class Diagnostic:
    code: str
    field: str
    message: str
    operation: str | None = None
    owner: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "field": self.field,
            "message": self.message,
        }
        if self.operation is not None:
            result["operation"] = self.operation
        if self.owner is not None:
            result["owner"] = self.owner
        return result


Contract = Mapping[str, Any]
