
#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from pathlib import Path

from pacman import get_installed_packages
from compatibility import resolve

BASE = Path(__file__).parent
MAPPING_FILE = BASE / "config" / "mappings.json"


def load_mappings():
    with MAPPING_FILE.open() as f:
        return json.load(f)


def run_tool(script, *args):
    result = subprocess.run(
        [sys.executable, str(BASE / script), *args],
        text=True,
        capture_output=True
    )

    if result.stdout:
        print(result.stdout, end="")

    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    return result.returncode


def resolve_atom(atom, installed):
    result = resolve(atom, installed)

    print(f"Gentoo dependency: {atom}")

    if result is None:
        print("No installed Arch package matches this atom.")
        return

    print("\nArch candidate:")
    print(f"  Package: {result['arch']}")
    print(f"  Installed: {result['version']}")
    print(f"  Gentoo atom: {result['gentoo']}")
    print(f"  Required version: {result['required_version']}")
    print(f"  Slot: {result['slot']}")
    print(f"\nStatus: {result['status']}")
    print(result["reason"])


def audit(installed, mappings):
    results = []

    for arch, gentoo in mappings.items():
        if arch not in installed:
            continue

        results.append({
            "arch": arch,
            "version": installed[arch],
            "gentoo": gentoo,
            "status": "UNVERIFIED",
            "reason": "ABI and build compatibility not established"
        })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Pacman-Portage compatibility bridge"
    )

    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--resolve", metavar="ATOM")

    parser.add_argument("--inspect", metavar="PACKAGE")
    parser.add_argument("--abi", metavar="PACKAGE")
    parser.add_argument("--dependencies", metavar="PACKAGE")

    parser.add_argument("--report", metavar="PACKAGE")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    try:
        installed = get_installed_packages()
        mappings = load_mappings()

        if args.resolve:
            result = resolve(args.resolve, installed)

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                resolve_atom(args.resolve, installed)

            return

        if args.inspect:
            run_tool(
                "arch_metadata.py",
                args.inspect
            )
            return

        if args.abi:
            run_tool(
                "abi.py",
                args.abi
            )
            return

        if args.dependencies:
            run_tool(
                "elf_inspector.py",
                args.dependencies
            )
            return

        if args.report:
            report = {
                "package": args.report,
                "installed_version": installed.get(args.report),
                "inspect": "arch_metadata.py",
                "abi": "abi.py",
                "dependencies": "elf_inspector.py",
                "status": "UNVERIFIED"
            }

            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print(json.dumps(report, indent=2))

            return

        if args.audit or args.check:
            results = audit(installed, mappings)

            if args.json:
                print(json.dumps(results, indent=2))
                return

            print(f"Installed packages: {len(installed)}")
            print(f"Mapped packages: {len(results)}")

            for item in results:
                print(
                    f"[{item['status']:<10}] "
                    f"{item['arch']:<15} "
                    f"{item['version']:<25} "
                    f"-> {item['gentoo']}"
                )

            return

        print(f"Installed Arch packages: {len(installed)}")

        results = audit(installed, mappings)

        print(f"Mapped packages found: {len(results)}")

        for item in results:
            print(
                f"[{item['status']:<10}] "
                f"{item['arch']:<15} "
                f"{item['version']:<25} "
                f"-> {item['gentoo']}"
            )

    except (subprocess.CalledProcessError, OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

