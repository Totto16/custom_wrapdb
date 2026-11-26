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
import argparse
import os
import shutil
import hashlib
import requests
import tempfile
import typing as T
import subprocess
import json

from pathlib import Path
from utils import CIConfig, Releases, is_ci, is_debianlike, read_wrap, write_wrap

class CreateRelease:
    def __init__(self, repo: str, wrapdb_host: str, token: T.Optional[str], tag: str):
        print('Preparing release for:', tag)
        self.tag = tag
        self.name, self.version = self.tag.rsplit('_', 1)
        self.wrapdb_host = wrapdb_host
        self.repo = repo
        self.token = token

        with tempfile.TemporaryDirectory() as self.tempdir:
            self.read_wrap()
            self.find_upload_url()
            self.create_source_fallback()
            self.create_patch_zip()
            self.create_wrap_file()
            self.finalize()

    def warn(self, message: str) -> None:
        if is_ci():
            print(f'::warning file=subprojects/{self.name}.wrap,line=1,title={self.name}::{message}')
        else:
            print(message)

    def read_wrap(self) -> None:
        self.wrap = read_wrap(self.name)
        self.wrap_section = self.wrap[self.wrap.sections()[0]]

    def create_patch_zip(self) -> None:
        patch_directory = self.wrap_section.get('patch_directory')
        if patch_directory is None:
            return

        directory = self.wrap_section.get('directory', self.name)
        srcdir = Path('subprojects', 'packagefiles', patch_directory)
        destdir = Path(self.tempdir, directory)

        generator = Path(srcdir, 'generator.sh')
        if generator.exists():
            try:
                ci = CIConfig.load()
            except json.decoder.JSONDecodeError as ex:
                raise RuntimeError(f'CI config is malformed') from ex

            debian_packages = ci.get(self.name, {}).get('debian_packages', [])
            if debian_packages and is_debianlike():
                if is_ci():
                    subprocess.check_call(['sudo', 'apt-get', 'update'])
                    subprocess.check_call(['sudo', 'apt-get', '-y', 'install'] + debian_packages)
                else:
                    s = ', '.join(debian_packages)
                    print(f'The following packages could be required: {s}')

            subprocess.check_call([generator])

        shutil.copytree(srcdir, destdir)
        # If no specific license is specified, copy wrapdb's
        license_file = destdir / 'LICENSE.build'
        if not license_file.exists():
            shutil.copyfile('COPYING', license_file)

        base_name = Path(self.tempdir, f'{self.tag}_patch')
        shutil.make_archive(base_name.as_posix(), 'zip', root_dir=self.tempdir, base_dir=directory)

        patch_filename = base_name.with_name(f'{base_name.name}.zip')
        self.upload(patch_filename, 'application/zip')

        h = hashlib.sha256()
        h.update(patch_filename.read_bytes())
        patch_hash = h.hexdigest()

        del self.wrap_section['patch_directory']
        self.wrap_section['patch_filename'] = patch_filename.name
        self.wrap_section['patch_url'] = f'https://{self.wrapdb_host}/v2/{self.tag}/get_patch'
        self.wrap_section['patch_fallback_url'] = f'https://github.com/{self.repo}/releases/download/{self.tag}/{patch_filename.name}'
        self.wrap_section['patch_hash'] = patch_hash

    def create_wrap_file(self) -> None:
        self.wrap_section['wrapdb_version'] = self.version

        filename = Path(self.tempdir, f'{self.name}.wrap')
        write_wrap(filename, self.wrap)

        print('Generated wrap file:')
        print(filename.read_text())
        self.upload(filename, 'text/plain')

    def find_upload_url(self) -> None:
        if not self.repo or not self.token:
            return
        api = f'https://api.github.com/repos/{self.repo}/releases'
        headers = { 'Authorization': f'token {self.token}' }
        response = requests.get(api, headers=headers)
        response.raise_for_status()
        for r in response.json():
            if r['tag_name'] == self.tag:
                if r['draft']:
                    delete_api = f'https://api.github.com/repos/{self.repo}/releases/{r["id"]}'
                    response = requests.delete(delete_api, headers=headers)
                    response.raise_for_status()
                    print('Deleted stale release draft:', r['id'])
                else:
                    raise Exception('Refusing to recreate existing release')

        cmd = ['git', 'rev-parse', 'HEAD']
        commit = subprocess.check_output(cmd, text=True).strip()
        content = {
            'tag_name': self.tag,
            'name': self.tag,
            'target_commitish': commit,
            'draft': True,
        }
        response = requests.post(api, headers=headers, json=content)
        response.raise_for_status()
        r = response.json()
        self.release_id = r['id']
        self.upload_url = r['upload_url'].replace('{?name,label}','')
        print('Created release:', self.upload_url)

    def upload(self, path: Path, mimetype: str) -> None:
        if not self.repo or not self.token:
            # Write files locally when not run on CI
            with Path('subprojects', 'packagecache', path.name).open('wb') as f:
                f.write(path.read_bytes())
            return
        headers = {
            'Authorization': f'token {self.token}',
            'Content-Type': mimetype,
        }
        params = { 'name': path.name }
        response = requests.post(self.upload_url, headers=headers, params=params, data=path.read_bytes())
        response.raise_for_status()

    def create_source_fallback(self) -> None:
        for url in (self.wrap_section['source_url'],
                    self.wrap_section.get('source_fallback_url')):
            if url is None:
                continue
            try:
                response = requests.get(url, headers={'User-Agent': 'wrapdb/0'})
                response.raise_for_status()
                digest = hashlib.sha256(response.content).hexdigest()
                if digest != self.wrap_section['source_hash']:
                    raise Exception(f'Hash mismatch for {url} ({len(response.content)} bytes): expected {self.wrap_section["source_hash"]}, found {digest}')
                # we don't rewrite the wrap's source_url, even if we had to
                # use the source_fallback_url instead
                break
            except Exception as ex:
                self.warn(str(ex))
        else:
            self.warn("Couldn't download source archive; skipping creation of source fallback")
            return

        filename = Path(self.tempdir, self.wrap_section['source_filename'])
        filename.write_bytes(response.content)
        self.upload(filename, 'application/zip')
        self.wrap_section['source_fallback_url'] = f'https://{self.wrapdb_host}/v2/{self.tag}/get_source/{filename.name}'

    def finalize(self) -> None:
        if not self.repo or not self.token:
            return
        api = f'https://api.github.com/repos/{self.repo}/releases/{self.release_id}'
        headers = { 'Authorization': f'token {self.token}' }
        content = { 'draft': False }
        response = requests.patch(api, headers=headers, json=content)
        response.raise_for_status()
        print('Published release:', self.upload_url)

def generate_frontend(site: Path, wrapdb_host: str, allow_docs_for_other_repo: bool) -> None:
    with tempfile.TemporaryDirectory() as tempdir:
        subprocess.check_call(
            ['python', 'tools/regenerate_docs.py', '--output-dir', tempdir, '--wrapdb-host', wrapdb_host] + (["--allow-docs-for-other-repo"] if allow_docs_for_other_repo else [])
        )

        table_html = Path(tempdir) / "table.html"

        subprocess.check_call(
            ['pnpm', '-C', './frontend', 'exec', 'tsc', '-P', './tsconfig.tools.json']
        )

        subprocess.check_call(
            ['node', './frontend/dist_tools/generate_html.js', table_html]
        )

    # no more need for the temp directory
    subprocess.check_call(
        ['pnpm', '-C', './frontend', 'run', 'build']
    )

    out_dir = Path("./frontend") / "out"

    for root, dirs, files in out_dir.walk():

        for dir in dirs:
            global_dir = root / dir
            dir_to_make = site / global_dir.relative_to(out_dir)
            dir_to_make.mkdir()

        for file in files:
            global_file = root / file
            file_dest = site / global_file.relative_to(out_dir)
            if hasattr(global_file, "copy"):
                global_file.copy(file_dest)
            else:
                import shutil
                shutil.copyfile(global_file, file_dest)



def generate_site(releases: Releases, wrapdb_host: str,allow_docs_for_other_repo: bool) -> None:
    site = Path('_site')  # default path for actions/upload-pages-artifact
    if site.exists():
        shutil.rmtree(site)
    site.mkdir()

    wrapdb = site / "wrapdb"
    wrapdb.mkdir()

    releases.save(dir=wrapdb, compact=True)

    generate_frontend(site, wrapdb_host, allow_docs_for_other_repo)

def run(repo: str, wrapdb_host_opt: T.Optional[str], token: T.Optional[str], allow_docs_for_other_repo: bool) -> None:
    releases = Releases.load()

    wrapdb_host: str

    meta = T.cast(T.Optional[T.Any], releases.get("$meta", None))
    if meta is not None:
        host: str = meta["host"]

        wrapdb_host = host

        if wrapdb_host_opt is not None:
            if wrapdb_host_opt != host:
                if allow_docs_for_other_repo:
                    ## only generate site for that
                    generate_site(releases, wrapdb_host_opt, True)
                    return
                else:
                    raise Exception(f"Got two different hosts from the '$meta' field in the releases.json and the cli: {wrapdb_host_opt} vs. {host}")

    else:
        if wrapdb_host_opt is None:
            raise Exception("WrapDB host not given as cli arg and not detected based on the releases.json")

        wrapdb_host = wrapdb_host_opt


    stdout = subprocess.check_output(['git', 'tag'])
    tags = [t.strip() for t in stdout.decode().splitlines()]
    for name, info in releases.items():
        versions = info['versions']
        latest_tag = f'{name}_{versions[0]}'
        if latest_tag not in tags:
            CreateRelease(repo, wrapdb_host, token, latest_tag)
    generate_site(releases, wrapdb_host, False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate wrapdb static website")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--wrapdb-host", required=False)
    parser.add_argument("--token", required=False, default=None)
    parser.add_argument(
        '-a', '--allow-docs-for-other-repo', action='store_true', default=False,
    )

    args = parser.parse_args()


    run(repo=args.repo, wrapdb_host_opt=args.wrapdb_host, token=args.token, allow_docs_for_other_repo=args.allow_docs_for_other_repo)
