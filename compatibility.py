import json
from pathlib import Path

from atom import parse_atom
from versions import (
    compare_versions,
    arch_version_info,
)

BASE = Path(__file__).parent


def load_mappings():
    with (BASE / "config/mappings.json").open() as f:
        return json.load(f)


def compare_constraint(candidate, required, operator, wildcard=False):
    if wildcard:
        return candidate.startswith(required)

    if operator == "~":
        candidate_base = candidate.split("-r", 1)[0]
        required_base = required.split("-r", 1)[0]
        return compare_versions(candidate_base, required_base) == 0

    comparison = compare_versions(candidate, required)

    operators = {
        ">=": comparison >= 0,
        "<=": comparison <= 0,
        ">": comparison > 0,
        "<": comparison < 0,
        "=": comparison == 0,
        "": comparison == 0,
    }

    if operator not in operators:
        raise ValueError(f"Unsupported operator: {operator}")

    return operators[operator]


def version_check(installed, atom):
    if atom.version is None:
        return {
            "result": None,
            "status": "NOT_REQUIRED",
            "normalized": None,
            "lossy": False,
            "reason": "Dependency has no version constraint."
        }

    info = arch_version_info(installed)

    if info is None:
        return {
            "result": None,
            "status": "UNVERIFIED",
            "normalized": None,
            "lossy": True,
            "reason": "Arch version could not be normalized."
        }

    candidate = info["upstream"]

    try:
        matched = compare_constraint(
            candidate,
            atom.version,
            atom.operator,
            atom.wildcard
        )
    except ValueError as error:
        return {
            "result": None,
            "status": "UNVERIFIED",
            "normalized": candidate,
            "lossy": info["lossy"],
            "reason": str(error)
        }

    if info["lossy"]:
        return {
            "result": None,
            "status": "APPROXIMATE",
            "normalized": candidate,
            "lossy": True,
            "reason": (
                "Comparison used a normalized Arch version. "
                "Epoch or Git metadata was discarded; "
                "the result is not authoritative."
            )
        }

    return {
        "result": matched,
        "status": "VERSION_MATCH" if matched else "VERSION_MISMATCH",
        "normalized": candidate,
        "lossy": False,
        "reason": (
            "Upstream version satisfies the constraint."
            if matched
            else "Upstream version does not satisfy the constraint."
        )
    }


def resolve(atom_string, installed):
    atom = parse_atom(atom_string)
    mappings = load_mappings()

    gentoo_name = f"{atom.category}/{atom.package}"

    arch_name = next(
        (
            name for name, target in mappings.items()
            if target == gentoo_name
        ),
        None
    )

    if arch_name is None or arch_name not in installed:
        return None

    arch_version = installed[arch_name]
    version = version_check(arch_version, atom)

    return {
        "arch": arch_name,
        "version": arch_version,
        "gentoo": gentoo_name,
        "required_version": atom.version,
        "operator": atom.operator,
        "slot": atom.slot,
        "version_compatible": version["result"],
        "version_status": version["status"],
        "normalized_version": version["normalized"],
        "lossy": version["lossy"],
        "status": version["status"],
        "reason": version["reason"],
        "abi_verified": False,
    }
