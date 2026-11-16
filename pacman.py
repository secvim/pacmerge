import subprocess


def get_installed_packages():
    result = subprocess.run(
        ["pacman", "-Q"],
        capture_output=True,
        text=True,
        check=True
    )

    packages = {}

    for line in result.stdout.splitlines():
        name, version = line.split(maxsplit=1)
        packages[name] = version

    return packages
