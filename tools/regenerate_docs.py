#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2018 The Meson development team

"""
Regenerate markdown docs by using `meson.py` from the root dir
"""

import argparse

import json
from pathlib import Path
from urllib.request import urlopen


def generate_wrapdb_table(output_dir: Path, hostname: str) -> None:
    url = urlopen(f"https://{hostname}/v2/releases.json")
    releases = json.loads(url.read().decode())
    with open(output_dir / "wrapdb-table.md", "w", encoding="utf-8") as f:
        f.write("| Project | Versions | Provided dependencies | Provided programs |\n")
        f.write("| ------- | -------- | --------------------- | ----------------- |\n")
        for name, info in releases.items():
            versions = []
            added_tags = set()
            for v in info["versions"]:
                tag, build = v.rsplit("-", 1)
                if tag not in added_tags:
                    added_tags.add(tag)
                    versions.append(
                        f"[{v}](https://wrapdb.mesonbuild.com/v2/{name}_{v}/{name}.wrap)"
                    )
            # Highlight latest version.
            versions_str = f"<big>**{versions[0]}**</big><br/>" + ", ".join(
                versions[1:]
            )
            dependency_names = info.get("dependency_names", [])
            dependency_names_str = ", ".join(dependency_names)
            program_names = info.get("program_names", [])
            program_names_str = ", ".join(program_names)
            f.write(
                f"| {name} | {versions_str} | {dependency_names_str} | {program_names_str} |\n"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate meson docs")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--hostname", required=True)

    args = parser.parse_args()

    generate_wrapdb_table(output_dir=args.output_dir, hostname=args.hostname)
