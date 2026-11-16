
import re
from dataclasses import dataclass


@dataclass
class GentooAtom:
    operator: str
    category: str
    package: str
    version: str | None
    slot: str | None
    wildcard: bool


def parse_atom(atom: str) -> GentooAtom:
    atom = atom.strip()

    operator = ""

    for op in (">=", "<=", "=", "~", ">", "<"):
        if atom.startswith(op):
            operator = op
            atom = atom[len(op):]
            break

    category, separator, rest = atom.partition("/")

    if not separator:
        raise ValueError(f"Invalid Gentoo atom: {atom}")

    slot = None

    if ":" in rest:
        rest, slot = rest.split(":", 1)

    match = re.match(
        r"^(.+?)-([0-9].*)$",
        rest
    )

    version = None
    wildcard = False

    if match:
        package = match.group(1)
        version = match.group(2)

        if version.endswith("*"):
            version = version[:-1]
            wildcard = True
    else:
        package = rest

    return GentooAtom(
        operator=operator,
        category=category,
        package=package,
        version=version,
        slot=slot,
        wildcard=wildcard
    )


if __name__ == "__main__":
    examples = [
        ">=sys-libs/glibc-2.40",
        "dev-lang/python:3.14",
        "virtual/libc",
        "=dev-lang/perl-5.44*"
    ]

    for example in examples:
        print(example)
        print(parse_atom(example))
        print()

