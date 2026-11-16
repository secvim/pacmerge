#!/usr/bin/env python3

import argparse
import json
import re
import subprocess
import sys


def pacman_query(args):
    result = subprocess.run(
        ["pacman"] + args,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout


def get_package_info(package):
    output = pacman_query(["-Qi", "--", package])

    info = {}

    for line in output.splitlines():
        match = re.match(r"^(.+?)\s{2,}:\s*(.*)$", line)

        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            info[key] = value

    return info


def get_package_files(package):
    output = pacman_query(["-Qlq", "--", package])
    return sorted(set(output.splitlines()))


def classify_file(path):
    name = path.rsplit("/", 1)[-1]

    if re.search(r"\.so(?:\.|$)", name):
        return "shared_library"

    if name.endswith(".a"):
        return "static_library"

    if name.endswith((".h", ".hh", ".hpp", ".hxx", ".inc")):
        return "header"

    if path.startswith((
        "/usr/bin/",
        "/usr/sbin/",
        "/bin/",
        "/sbin/"
    )):
        return "executable_path"

    return "other"


def scan_package(package):
    info = get_package_info(package)
    files = get_package_files(package)

    categories = {
        "shared_library": [],
        "static_library": [],
        "header": [],
        "executable_path": [],
        "other": []
    }

    for path in files:
        category = classify_file(path)
        categories[category].append(path)

    return {
        "name": info.get("Name", package),
        "version": info.get("Version"),
        "architecture": info.get("Architecture"),
        "description": info.get("Description"),
        "depends_on": info.get("Depends On"),
        "provides": info.get("Provides"),
        "files": categories,
        "file_count": len(files)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Pacman package metadata scanner"
    )

    parser.add_argument(
        "packages",
        nargs="+",
        help="Arch package names to inspect"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON"
    )

    parser.add_argument(
        "--sample",
        type=int,
        default=10,
        help="Maximum files displayed per category"
    )

    args = parser.parse_args()

    results = []

    for package in args.packages:
        try:
            results.append(scan_package(package))
        except RuntimeError as error:
            print(
                f"Error scanning {package}: {error}",
                file=sys.stderr
            )

    if args.json:
        print(json.dumps(results, indent=2))
        return

    for result in results:
        print("=" * 65)
        print(f"Package:      {result['name']}")
        print(f"Version:      {result['version']}")
        print(f"Architecture: {result['architecture']}")
        print(f"Description:  {result['description']}")
        print(f"Depends on:   {result['depends_on']}")
        print(f"Provides:     {result['provides']}")
        print(f"Total files:  {result['file_count']}")

        for category, files in result["files"].items():
            print(f"\n{category}: {len(files)}")

            for path in files[:args.sample]:
                print(f"  {path}")

            if len(files) > args.sample:
                print(f"  ... and {len(files) - args.sample} more")


if __name__ == "__main__":
    main()
