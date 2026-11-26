#!/usr/bin/env python3

import argparse
from pathlib import Path
import requests
from hashlib import sha256
from utils import read_wrap
from typing import Optional
import re
from urllib.parse import urlparse


def is_valid_git_hash(value: str) -> bool:
    return bool(re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", value))


def extract_github_repo(url: str) -> tuple[str, str]:
    url_parsed = urlparse(url)
    if url_parsed.hostname != "github.com":
        raise Exception(f"Only github urls are supported atm but got: {url}")
    path = url_parsed.path.strip("/")
    username, repo = path.removesuffix(".git").split("/", 1)
    return username, repo


username, repo = extract_github_repo("https://github.com/Totto16/trc.git")


def get_hash_for_url(url: str) -> str:
    # update source hash
    resp: requests.Response = requests.get(
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


def generate_git_wrap(
    name: str, repo: str, hash: str, dep_names: Optional[str]
) -> None:
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
dependency_names = {dep_names if dep_names is not None else name}
""")


def add_func(args: argparse.Namespace) -> None:
    generate_git_wrap(
        name=args.name, repo=args.repo, hash=args.hash, dep_names=args.dep_names
    )


def migrate_func(args: argparse.Namespace) -> None:
    subprojects_dir = Path("subprojects")

    if not subprojects_dir.exists():
        raise Exception("'subprojects' dir doesn't exist")

    dest = subprojects_dir / f"{args.name}.wrap"

    if not dest.exists():
        raise Exception(f"{dest} doesn't exists")

    config = read_wrap(args.name)

    if not config.has_section("wrap-git"):
        raise Exception(f"{args.name} is not a git wrap")

    wrap_git = config["wrap-git"]

    revision = wrap_git["revision"]

    # TODO: resolve revision to hash or support it in generate_git_wrap
    if not is_valid_git_hash(revision):
        raise Exception(f"{revision} is not a valid git hash")

    url = wrap_git["url"]

    username, repo_name = extract_github_repo(url)

    repo = f"{username}/{repo_name}"

    if not config.has_section("provide"):
        raise Exception(f"{args.name} has no provide section")

    provide = config["provide"]

    dependency_names = provide["dependency_names"]

    dest.unlink()
    generate_git_wrap(
        name=args.name, repo=repo, hash=revision, dep_names=dependency_names
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="wrap_utils.py", description="Manage wraps.")

    subparsers = parser.add_subparsers(metavar="subcommand", required=True)

    add_by_git = subparsers.add_parser(
        "add", help="Generate wrap from github but it's of type 'wrap-file'"
    )
    add_by_git.add_argument("--name", required=True)
    add_by_git.add_argument("--repo", required=True)
    add_by_git.add_argument("--hash", required=True)
    add_by_git.add_argument("--dep-names")
    add_by_git.set_defaults(func=add_func)

    migrate_from_git = subparsers.add_parser(
        "migrate", help="Migrate wrap from github 'wrap-git' to 'wrap-file'"
    )
    migrate_from_git.add_argument("name")
    migrate_from_git.set_defaults(func=migrate_func)

    args = parser.parse_args()
    args.func(args)
