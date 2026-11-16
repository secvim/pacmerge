#!/usr/bin/env python3

import argparse
import json
import subprocess
from collections import defaultdict


def get_files(package):
    result = subprocess.run(
        ["pacman", "-Qlq", "--", package],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.splitlines()


def get_package_owner(path):
    result = subprocess.run(
        ["pacman", "-Qo", path],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def inspect(package):
    files = get_files(package)

    capabilities = defaultdict(list)

    for path in files:
        if path.endswith((".h", ".hpp", ".hh")):
            capabilities["headers"].append(path)

        elif ".so" in path.split("/")[-1]:
            capabilities["shared_libraries"].append(path)

        elif path.endswith(".a"):
            capabilities["static_libraries"].append(path)

        elif path.startswith(("/usr/bin/", "/usr/sbin/")):
            capabilities["executables"].append(path)

    return {
        "package": package,
        "file_count": len(files),
        "capabilities": dict(capabilities)
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("packages", nargs="+")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--find", metavar="PATTERN")

    args = parser.parse_args()

    for package in args.packages:
        data = inspect(package)

        if args.find:
            matches = []

            for category, paths in data["capabilities"].items():
                matches.extend(
                    (category, path)
                    for path in paths
                    if args.find.lower() in path.lower()
                )

            print(f"\n{package}: {len(matches)} matches")

            for category, path in matches:
                print(f"[{category}] {path}")

        elif args.json:
            print(json.dumps(data, indent=2))

        else:
            print(f"\nPackage: {package}")
            print(f"Files: {data['file_count']}")

            for category, paths in data["capabilities"].items():
                print(f"\n{category}: {len(paths)}")

                for path in paths[:15]:
                    print(f"  {path}")


if __name__ == "__main__":
    main()
