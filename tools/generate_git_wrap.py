#!/usr/bin/env python3

import argparse
from pathlib import Path
import requests
from hashlib import sha256


def get_hash_for_url(url: str) -> str:
    # update source hash
    resp = requests.get(
        url,
        stream=True,
        headers={
            "User-Agent": "wrapdb/0",
        },
    )
    resp.raise_for_status()
    hash = sha256()
    while True:
        buf = resp.raw.read(1 << 20)
        if not buf:
            break
        hash.update(buf)

    return hash.hexdigest()


def generate_git_wrap(name: str, repo: str, hash: str) -> None:
    subprojects_dir = Path("subprojects")

    if not subprojects_dir.exists():
        raise Exception("'subprojects' dir doesn't exist")

    dest = subprojects_dir / f"{name}.wrap"

    if dest.exists():
        raise Exception(f"{dest} already exists")

    repo_url = f"https://github.com/{repo}/archive/{hash}.tar.gz"

    source_hash = get_hash_for_url(repo_url)

    with dest.open("w") as f:
        f.write(f"""[wrap-file]
directory = {name}-{hash}
source_url = {repo_url}
source_filename = {name}-{hash}.tar.gz
source_hash = {source_hash}

[provide]
dependency_names = {name}
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate wrap from github but it's  a wrap-file"
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--hash", required=True)

    args = parser.parse_args()

    generate_git_wrap(name=args.name, repo=args.repo, hash=args.hash)
