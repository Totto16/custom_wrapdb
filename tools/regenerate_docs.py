#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2018 The Meson development team

"""
Regenerate markdown docs by using `meson.py` from the root dir
"""

import argparse

import json
from pathlib import Path
from typing import Any, Optional
from urllib.request import urlopen


def get_releases(wrapdb_host_opt: Optional[str], allow_docs_for_other_repo: bool) -> tuple[Any, str]:
    with Path("releases.json").open("r", encoding="utf-8") as f:
        releases: Any = json.load(f)

        wrapdb_host: str

        # if we have a meta entry we check if we want to use that host or we specified another one
        meta = releases.get("$meta", None)
        if meta is not None:
            host: str = meta["host"]

            wrapdb_host = host

            if wrapdb_host_opt is not None:
                if wrapdb_host_opt != host:
                    if allow_docs_for_other_repo:
                        wrapdb_host = wrapdb_host_opt
                        url = urlopen(f"https://{wrapdb_host}/v2/releases.json")
                        releases = json.loads(url.read().decode())
                    else:
                        raise Exception(f"Got two different hosts from the '$meta' field in the releases.json and the cli: {wrapdb_host} vs. {host}")
        else:
            if wrapdb_host_opt is None:
                raise Exception("WrapDB host not given as cli arg and not detected based on the releases.json")

            wrapdb_host = wrapdb_host_opt

        return releases, wrapdb_host


def generate_wrapdb_table(output_dir: Path, wrapdb_host_opt: Optional[str],allow_docs_for_other_repo: bool) -> None:
    with open(output_dir / "table.html", "w", encoding="utf-8") as f:

        releases, wrapdb_host = get_releases(wrapdb_host_opt, allow_docs_for_other_repo)

        f.write('<table id="projects">\n')
        f.write(
            '<tr class="table-header"> <th class="proj">Project</th> <th class="version">Versions</th> <th class="deps">Provided dependencies</th> <th class="programs">Provided programs</th> </tr>\n'
        )
        for name, info in releases.items():

            name_str = f'<div class="wrap-name" filter-data="{name}">{name}</div>'

            versions: list[str] = []
            added_tags: set[str] = set()
            for v in info["versions"]:
                tag, build = v.rsplit("-", 1)
                if tag not in added_tags:
                    added_tags.add(tag)
                    versions.append(
                        f'<a href="https://{wrapdb_host}/v2/{name}_{v}/{name}.wrap" class="wrap-link" filter-data="{v}">{v}</a>'
                    )
            # Highlight latest version.
            versions_str = f'<div class="versions-div"> <div class="versions-number">{'</div> <div class="versions-number">'.join(
                versions
            )} </div> </div>'

            dependency_names: list[str] = info.get("dependency_names", [])
            dependency_names_str = (
                f'<div class="deps-div"> {" ".join(
                [f'<div class="deps-name" filter-data="{dep}">{dep}</div>' for dep in dependency_names]
                )} </div>'
                if len(dependency_names) != 0
                else '<div class="deps-div empty-deps"> </div>'
            )
            program_names: list[str] = info.get("program_names", [])
            program_names_str = (
                f'<div class="programs-div"> {" ".join(
                [f'<div class="programs-name" filter-data="{program}">{program}</div>' for program in program_names]
                )} </div>'
                if len(program_names) != 0
                else '<div class="programs-div empty-programs"> </div>'
            )

            f.write(
                f'<tr class="table-entry"> <td class="proj">{name_str}</td> <td class="version">{versions_str}</td> <td class="deps">{dependency_names_str}</td> <td class="programs">{program_names_str}</td> </tr>\n'
            )

        f.write(
            '<tr class="no-entries" style="display: none;"> <td class="entries" colspan="4"> <div class="no-entries-div">No entries found</div> </td> </tr>\n'
        )
        f.write("</table>\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate wrapdb static website")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--wrapdb-host", required=False)
    parser.add_argument(
        '-a', '--allow-docs-for-other-repo', action='store_true', default=False,
    )

    args = parser.parse_args()

    generate_wrapdb_table(
        output_dir=Path(args.output_dir), wrapdb_host_opt=args.wrapdb_host,
        allow_docs_for_other_repo=args.allow_docs_for_other_repo
    )
