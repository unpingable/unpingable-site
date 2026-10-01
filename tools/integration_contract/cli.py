#!/usr/bin/env python3
"""CLI for bounded validation, preflight, and repair declaration queries."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .parser import ContractParseError, load_contract
from .preflight import preflight, repair_query
from .validator import ContractValidationError, validate_contract


def _emit(value: Any, human: bool) -> None:
    if not human:
        print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
        return
    if "operations" in value:
        print(f"Integration: {value['integration']}")
        print(f"Interface closure declared: {str(value['interfaceClosure']['declared']).lower()}")
        print(f"Integration complete (declared interface closure and wiring): {str(value['integrationComplete']).lower()}")
        print(f"Integration blockers: {len(value['integrationBlockers'])}; readiness holds: {len(value['readinessHolds'])}")
        print(value["authorityStatement"])
        operation_ids = {operation["operation"] for operation in value["operations"]}
        global_blockers = [
            blocker for blocker in value["integrationBlockers"]
            if blocker.get("operation") not in operation_ids
        ]
        for blocker in global_blockers:
            print(f"- GLOBAL: {blocker['code']} [{blocker['field']}]: {blocker['message']}")
        for operation in value["operations"]:
            boundary = operation.get("executionBoundary")
            boundary_status = (
                "missing" if not operation["executionBoundaryDeclared"]
                else "source-only-null" if operation["executionClass"] == "source-only" and boundary is None
                else "missing" if boundary is None
                else boundary["status"]
            )
            print(f"- {operation['operation']}: {operation['disposition']} (execution boundary: {boundary_status})")
            if boundary is not None:
                print(
                    "  baseline: " + boundary["baselinePlatformIdentity"]
                    + f"; delegated observations: {len(boundary['delegatedPrimitives'])}"
                    + f"; delegated effects: {len(boundary['delegatedExecutors'])}"
                    + f"; shared exclusions: {len(boundary['sharedExclusions'])}"
                )
            for blocker in operation["blockers"]:
                print(f"  {blocker['code']} [{blocker['field']}]: {blocker['message']}")
    elif "allowedByDeclaredStandingRepairAuthority" in value:
        print(f"Integration: {value['integration']}")
        print(f"Allowed by declared standing repair authority: {str(value['allowedByDeclaredStandingRepairAuthority']).lower()}")
        print(value["statement"])
    else:
        print(f"valid: {value['valid']}")
        print("This validation grants no effect authority.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--human", action="store_true", help="emit concise text rather than resolved JSON")
    commands = parser.add_subparsers(dest="command", required=True)
    validate_cmd = commands.add_parser("validate"); validate_cmd.add_argument("contract")
    preflight_cmd = commands.add_parser("preflight"); preflight_cmd.add_argument("contract"); preflight_cmd.add_argument("--assessment-time", required=True)
    repair_cmd = commands.add_parser("repair-query"); repair_cmd.add_argument("contract"); repair_cmd.add_argument("--category", required=True); repair_cmd.add_argument("--changes", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        document = load_contract(args.contract)
        if args.command == "validate":
            validated = validate_contract(document)
            result = {"apiVersion": validated["apiVersion"], "integration": validated["integration"]["id"], "valid": True, "grantsEffectAuthority": False}
        elif args.command == "preflight":
            result = preflight(document, assessment_timestamp=args.assessment_time)
        else:
            changed = [item for group in args.changes for item in group.split(",") if item]
            result = repair_query(document, category=args.category, changed_boundaries=changed)
        _emit(result, args.human)
        return 0
    except (ContractParseError, ContractValidationError) as error:
        result = {"valid": False, "grantsEffectAuthority": False, "error": {"code": error.code, "message": str(error)}}
        if isinstance(error, ContractValidationError): result["error"]["field"] = error.field
        _emit(result, False)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
