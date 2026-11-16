#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path


def inspect_elf(path):
    result = subprocess.run(
        ["readelf", "-h", path],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    output = result.stdout

    def extract(label):
        for line in output.splitlines():
            if label in line:
                return line.split(":", 1)[1].strip()
        return None

    dynamic = subprocess.run(
        ["readelf", "-d", path],
        capture_output=True,
        text=True
    )

    dyn = dynamic.stdout

    soname = None
    needed = []

    for line in dyn.splitlines():
        if "(SONAME)" in line:
            soname = line.split("[")[-1].split("]")[0]

        if "(NEEDED)" in line:
            needed.append(
                line.split("[")[-1].split("]")[0]
            )

    versions_result = subprocess.run(
        ["readelf", "--version-info", path],
        capture_output=True,
        text=True
    )

    version_info = versions_result.stdout

    import re

    symbol_versions = sorted(set(
        re.findall(
            r"\b(?:GLIBC|GLIBCXX|CXXABI|GCC|GFORTRAN)_[0-9][A-Za-z0-9_.]*",
            version_info
        )
    ))

    return {
        "symbol_versions": symbol_versions,
        "class": extract("Class:"),
        "machine": extract("Machine:"),
        "endianness": extract("Data:"),
        "soname": soname,
        "needed": sorted(set(needed))
    }


def get_elf_files(package):
    result = subprocess.run(
        ["pacman", "-Qlq", "--", package],
        capture_output=True,
        text=True,
        check=True
    )

    files = []

    for path in result.stdout.splitlines():
        if ".so" not in Path(path).name:
            continue

        if not Path(path).is_file():
            continue

        files.append(path)

    return files


def inspect_package(package):
    files = get_elf_files(package)

    results = []

    for path in files:
        info = inspect_elf(path)

        if info is None:
            continue

        info["path"] = path
        results.append(info)

    return results


def compare_elf(reference, candidate):
    checks = {
        "class": reference["class"] == candidate["class"],
        "machine": reference["machine"] == candidate["machine"],
        "endianness": (
            reference["endianness"] == candidate["endianness"]
        ),
    }

    return {
        "checks": checks,
        "compatible": all(checks.values())
    }


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("package")
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    results = inspect_package(args.package)

    if args.json:
        print(json.dumps(results, indent=2))
        return

    print(f"Package: {args.package}")
    print(f"ELF files inspected: {len(results)}")

    architectures = {}

    for item in results:
        key = (
            item["class"],
            item["machine"],
            item["endianness"]
        )

        architectures[key] = architectures.get(key, 0) + 1

    for architecture, count in architectures.items():
        print()
        print("Architecture:", architecture)
        print("Files:", count)

    print()
    print("SONAME inventory:")

    for item in results:
        if item["soname"]:
            print(f"  {item['soname']}")

    print()
    print("Required shared libraries:")

    needed = sorted({
        lib
        for item in results
        for lib in item["needed"]
    })

    for lib in needed:
        print(f"  {lib}")


if __name__ == "__main__":
    main()
