#!/usr/bin/env python3

import argparse
import re
import subprocess


VERSIONED_SYMBOL = re.compile(
    r"^(.*?)@{1,2}"
    r"((?:GLIBC|GLIBCXX|CXXABI|GCC|GFORTRAN)_[A-Za-z0-9_.]+)"
    r"(?:\s+\(\d+\))?$"
)


def inspect_symbols(path):
    result = subprocess.run(
        ["readelf", "--dyn-syms", "--wide", path],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Cannot inspect {path}: {result.stderr.strip()}"
        )

    required = set()
    provided = set()

    for line in result.stdout.splitlines():
        parts = line.split(None, 7)

        if len(parts) < 8:
            continue

        binding = parts[4]
        section = parts[6]
        name = parts[7]

        match = VERSIONED_SYMBOL.match(name)

        if not match:
            continue

        symbol = match.group(1)
        version = match.group(2)

        if section == "UND":
            required.add((symbol, version))

        elif binding in ("GLOBAL", "WEAK"):
            provided.add((symbol, version))

    return {
        "file": path,
        "required": required,
        "provided": provided
    }


def compare_symbols(consumer, provider):
    missing = consumer["required"] - provider["provided"]

    return {
        "checked": len(consumer["required"]),
        "matched": len(consumer["required"]) - len(missing),
        "missing": sorted(missing)
    }


def main():
    parser = argparse.ArgumentParser(
        description="ELF symbol compatibility inspector"
    )

    parser.add_argument("consumer")
    parser.add_argument("--provider")

    args = parser.parse_args()

    try:
        consumer = inspect_symbols(args.consumer)

        print("Consumer:", consumer["file"])
        print("Required versioned symbols:", len(consumer["required"]))

        if not args.provider:
            print("\nRequired symbols:")

            for symbol, version in sorted(consumer["required"]):
                print(f"  {symbol} [{version}]")

            print("\nProvided symbols:")

            for symbol, version in sorted(consumer["provided"]):
                print(f"  {symbol} [{version}]")

            return

        provider = inspect_symbols(args.provider)

        result = compare_symbols(consumer, provider)

        print("\nProvider:", provider["file"])
        print("Required symbols:", result["checked"])
        print("Matched symbols:", result["matched"])
        print("Missing symbols:", len(result["missing"]))

        if result["missing"]:
            print("\nMissing symbol/version pairs:")

            for symbol, version in result["missing"]:
                print(f"  {symbol} [{version}]")

        else:
            print("\nAll inspected versioned symbol references matched.")

    except RuntimeError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
