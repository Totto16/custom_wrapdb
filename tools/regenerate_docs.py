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


def generate_wrapdb_table(output_dir: Path, wrapdb_host: str) -> None:
    url = urlopen(f"https://{wrapdb_host}/v2/releases.json")
    releases = json.loads(url.read().decode())
    with open(output_dir / "table.html", "w", encoding="utf-8") as f:
        f.write('<table id="projects">\n')
        f.write('<tr class="table-header"> <th class="proj">Project</th> <th class="version">Versions</th> <th class="deps">Provided dependencies</th> <th class="programs">Provided programs</th> </tr>\n')
        for name, info in releases.items():

            name_str = f'<div class="wrap-name" filter-data="{name}">{name}</div>'

            versions:list[str] = []
            added_tags:set[str] = set()
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

            dependency_names = info.get("dependency_names", [])
            dependency_names_str = f'<div class="deps-div"> <div class="deps-name">{'</div> <div class="deps-name">'.join(
                dependency_names
            )} </div> </div>'
            program_names = info.get("program_names", [])
            program_names_str = f'<div class="programs-div"> <div class="programs-name">{'</div> <div class="programs-name">'.join(
                program_names
            )} </div> </div>'
            f.write(f'<tr class="table-entry"> <th class="proj">{name_str}</th> <th class="version">{versions_str}</th> <th class="deps">{dependency_names_str}</th> <th class="programs">{program_names_str}</th> </tr>\n')

        f.write('</table>\n')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate wrapdb static website")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--wrapdb-host", required=True)

    args = parser.parse_args()

    generate_wrapdb_table(output_dir=Path(args.output_dir), wrapdb_host=args.wrapdb_host)
