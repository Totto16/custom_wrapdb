#!/usr/bin/env python3

# Copyright 2021 Xavier Claessens <xclaesse@gmail.com>

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from pathlib import Path
import subprocess
import sys
from utils import Releases, format_meson, format_wrap, read_wrap

FORMAT_FILES = {'meson.build', 'meson_options.txt', 'meson.options'}

def main() -> int:
    releases = Releases.load()
    tags = set(subprocess.check_output(['git', 'tag', '--merged'], text=True).splitlines())

    files = []
    failed = 0
    for name, info in releases.items():
        # skip $schema, $meta and similar
        if name.startswith("$"):
            continue

        if f'{name}_{info["versions"][0]}' not in tags:
            format_wrap(name)
            config = read_wrap(name)
            wrap_file = config['wrap-file'] if config.has_section('wrap-file') else None
            if wrap_file is None:
                failed += 1
                print(f"WARNING: Can't determine files from non 'wrap-file' wrap file {name}", file=sys.stderr)
                continue

            patch_dir_name = wrap_file.get('patch_directory')
            if patch_dir_name:
                patch_dir = Path('subprojects', 'packagefiles', patch_dir_name)
                files += [f for f in patch_dir.rglob('*') if f.name in FORMAT_FILES]

    format_meson(files)
    Releases.format()
    return failed


if __name__ == '__main__':
    failed = main()
    sys.exit(1 if failed > 0 else 0)
