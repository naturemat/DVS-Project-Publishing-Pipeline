import re
import subprocess


def _run(cmd):
    return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()


def _last_tag():
    tags = _run(["git", "tag", "--list", "v[0-9]*"]).splitlines()

    def key(tag):
        return tuple(int(x) for x in re.findall(r"\d+", tag)[:3])

    if not tags:
        return (0, 0, 0)
    return key(sorted(tags, key=key)[-1])


def _subjects_since(version):
    if version == (0, 0, 0):
        return _run(["git", "log", "--pretty=%s"]).splitlines()
    tag = "v" + ".".join(map(str, version))
    return _run(["git", "log", f"{tag}..HEAD", "--pretty=%s"]).splitlines()


def _next_version(version, subjects):
    major = minor = patch = False
    for subject in subjects:
        if subject.startswith("Merge"):
            continue
        head = subject.split(":", 1)[0].strip()
        kind = head.split("(", 1)[0].strip("!")
        if "!" in head or "breaking change" in subject.lower():
            major = True
        elif kind.lower() == "feat":
            minor = True
        else:
            patch = True
    ma, mi, pa = version
    if major:
        return (ma + 1, 0, 0)
    if minor:
        return (ma, mi + 1, 0)
    return (ma, mi, pa + 1)


def main():
    version = _last_tag()
    next_version = _next_version(version, _subjects_since(version))
    print("v" + ".".join(map(str, next_version)))


if __name__ == "__main__":
    main()