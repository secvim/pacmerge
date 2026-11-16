import re

GENTOO_VERSION = re.compile(
    r"^(\d+(?:\.\d+)*)([a-z])?"
    r"((?:_(?:alpha|beta|pre|rc|p)\d*)*)"
    r"(?:-r(\d+))?$"
)

SUFFIX_ORDER = {
    "alpha": -4,
    "beta": -3,
    "pre": -2,
    "rc": -1,
    "p": 1
}


def parse_version(version):
    match = GENTOO_VERSION.fullmatch(version)

    if not match:
        raise ValueError(f"Unsupported version: {version}")

    numbers = tuple(
        int(x) for x in match.group(1).split(".")
    )

    letter = match.group(2)
    letter_value = (
        ord(letter) - ord("a") - 26
        if letter else 0
    )

    suffixes = []

    for suffix in re.finditer(
        r"_(alpha|beta|pre|rc|p)(\d*)",
        match.group(3)
    ):
        suffixes.append((
            SUFFIX_ORDER[suffix.group(1)],
            int(suffix.group(2) or 0)
        ))

    revision = int(match.group(4) or 0)

    return numbers, letter_value, tuple(suffixes), revision


def compare_versions(left, right):
    a = parse_version(left)
    b = parse_version(right)

    length = max(len(a[0]), len(b[0]))

    an = a[0] + (0,) * (length - len(a[0]))
    bn = b[0] + (0,) * (length - len(b[0]))

    if an != bn:
        return (an > bn) - (an < bn)

    if a[1] != b[1]:
        return (a[1] > b[1]) - (a[1] < b[1])

    suffix_count = max(len(a[2]), len(b[2]))

    asuffix = a[2] + ((0, 0),) * (
        suffix_count - len(a[2])
    )

    bsuffix = b[2] + ((0, 0),) * (
        suffix_count - len(b[2])
    )

    if asuffix != bsuffix:
        return (asuffix > bsuffix) - (asuffix < bsuffix)

    return (a[3] > b[3]) - (a[3] < b[3])


def arch_version_info(version):
    """
    Extract upstream version from an Arch package version.

    Arch format:
        [epoch:]pkgver-pkgrel

    Git metadata is stripped for approximate comparison.
    Epochs and stripped metadata are recorded because
    normalization is not proof of version equivalence.
    """

    original = version
    epoch = None
    pkgrel = None
    metadata = None

    if ":" in version:
        epoch, version = version.split(":", 1)

    upstream, separator, release = version.rpartition("-")

    if separator and re.fullmatch(r"\d+(?:\.\d+)*", release):
        version = upstream
        pkgrel = release

    if "+" in version:
        version, metadata = version.split("+", 1)

    try:
        parse_version(version)
    except ValueError:
        return None

    return {
        "original": original,
        "upstream": version,
        "epoch": epoch,
        "pkgrel": pkgrel,
        "metadata": metadata,
        "lossy": bool(epoch or metadata)
    }


def arch_to_upstream(version):
    """
    Return an approximate upstream version.

    WARNING:
    This is normalization, not proof of Gentoo compatibility.
    """

    info = arch_version_info(version)

    if info is None:
        return None

    return info["upstream"]
