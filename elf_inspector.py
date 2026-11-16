#!/usr/bin/env python3

import argparse
import re
import subprocess
import json


def run_readelf(*args):
    result = subprocess.run(
        ["readelf", *args],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    return result.stdout


def inspect_elf(path):
    header = run_readelf("-h", path)

    if header is None or "ELF" not in header:
        return None

    dynamic = run_readelf("-d", path) or ""
    symbols = run_readelf("--dyn-syms", "--wide", path) or ""

    def extract(pattern, source):
        return re.findall(pattern, source)

    machine = extract(r"Machine:\s*(.+)", header)
    elf_class = extract(r"Class:\s*(.+)", header)
    endian = extract(r"Data:\s*(.+)", header)

    soname = extract(
        r"\(SONAME\).*?\[(.*?)\]",
        dynamic
    )

    needed = extract(
        r"\(NEEDED\).*?\[(.*?)\]",
        dynamic
    )

    exported = []

    for line in symbols.splitlines():
        parts = line.split()

        if len(parts) < 8:
            continue

        # Defined global or weak dynamic symbols.
        if (
            parts[4] in ("GLOBAL", "WEAK")
            and parts[6] != "UND"
            and parts[7] != ""
        ):
            exported.append(parts[7].split("@")[0])

    return {
        "path": path,
        "class": elf_class[0].strip() if elf_class else None,
        "machine": machine[0].strip() if machine else None,
        "endianness": endian[0].strip() if endian else None,
        "soname": soname[0] if soname else None,
        "needed": sorted(set(needed)),
        "exported_symbols": sorted(set(exported)),
        "exported_symbol_count": len(set(exported))
    }


def get_package_files(package):
    result = subprocess.run(
        ["pacman", "-Qlq", "--", package],
        capture_output=True,
        text=True,
        check=True
    )

    return result.stdout.splitlines()


def main():
    parser = argparse.ArgumentParser(
        description="ELF metadata inspector"
    )

    parser.add_argument("packages", nargs="+")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--find", metavar="SONAME")

    args = parser.parse_args()

    results = []

    for package in args.packages:
        print(f"Scanning {package}...", flush=True)

        for path in get_package_files(package):
            name = path.rsplit("/", 1)[-1]

            if ".so" not in name:
                continue

            info = inspect_elf(path)

            if info is None:
                continue

            info["package"] = package
            results.append(info)

    if args.find:
        results = [
            item for item in results
            if args.find.lower() in (
                (item["soname"] or "") + " " + item["path"]
            ).lower()
        ]

    if args.json:
        print(json.dumps(results, indent=2))
        return

    for item in results:
        print("\n" + "=" * 65)
        print("Package:", item["package"])
        print("File:", item["path"])
        print("ELF class:", item["class"])
        print("Machine:", item["machine"])
        print("Endianness:", item["endianness"])
        print("SONAME:", item["soname"])
        print("Required libraries:", ", ".join(item["needed"]))
        print("Exported symbols:", item["exported_symbol_count"])

        for symbol in item["exported_symbols"][:10]:
            print("  ", symbol)

        if item["exported_symbol_count"] > 10:
            print("  ...")


if __name__ == "__main__":
    main()
