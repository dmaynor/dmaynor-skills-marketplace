#!/usr/bin/env python3
"""Check a static walkthrough folder and optional ZIP without executing content."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import zipfile
from urllib.parse import unquote, urlsplit


class Dependencies(HTMLParser):
    """Collect ordinary HTML dependencies; browser QA remains required."""

    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == 'base':
            self.urls.append(values.get('href') or '/')
        for key in (('src', 'poster', 'data') if tag == 'object' else ('src', 'poster')):
            if values.get(key):
                self.urls.append(values[key] or '')
        if tag == 'link' and values.get('href'):
            self.urls.append(values['href'] or '')


def verify(folder: Path, entry: str, archive: Path | None = None) -> list[str]:
    """Return bounded diagnostics, never suspected credential values."""
    root = folder.resolve()
    errors: list[str] = []
    start = (root / entry).resolve()
    if not start.is_relative_to(root) or not start.is_file():
        return ['Entrypoint is missing or outside the package.']
    files: dict[str, bytes] = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            errors.append('Package contains a symlink; package regular files instead.')
            continue
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        content = path.read_bytes()
        files[name] = content
        if path.name.startswith('.env'):
            errors.append('Package contains an environment file.')
        if path.suffix.lower() in {'.html', '.htm', '.json', '.md', '.txt', '.js', '.css', '.log'}:
            text = content.decode('utf-8', errors='replace')
            patterns = [r'eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',
                        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                        r'(?i)[?&](?:access_token|reset_token|token|ticket)=[^\s"<>]+']
            if any(re.search(pattern, text) for pattern in patterns):
                errors.append('Possible credential in a text asset; inspect privately.')
        if path.suffix.lower() not in {'.html', '.htm'}:
            continue
        parser = Dependencies()
        parser.feed(content.decode('utf-8'))
        for url in parser.urls:
            parts = urlsplit(url)
            relative = unquote(parts.path)
            if parts.scheme or parts.netloc or relative.startswith(('/', '\\')) or '\\' in relative:
                errors.append('HTML dependency is not a portable relative URL.')
                continue
            target = (path.parent / relative).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                errors.append('HTML dependency is missing or outside the package.')
    if archive:
        try:
            with zipfile.ZipFile(archive) as bundle:
                names = [item.filename for item in bundle.infolist() if not item.is_dir()]
                if len(names) != len(set(names)):
                    errors.append('ZIP contains duplicate member names.')
                if bundle.testzip() is not None:
                    errors.append('ZIP CRC validation failed.')
                # Accept contents at archive root or in a folder named after root.
                prefix = root.name + '/' if set(names) == {root.name + '/' + n for n in files} else ''
                if set(names) != {prefix + n for n in files}:
                    errors.append('ZIP member set differs from the extracted folder.')
                else:
                    for name, content in files.items():
                        if bundle.read(prefix + name) != content:
                            errors.append('ZIP bytes differ from the extracted folder.')
                            break
        except (OSError, zipfile.BadZipFile, RuntimeError):
            errors.append('ZIP could not be validated.')
    return errors


def main() -> int:
    """Print JSON diagnostics and return nonzero for failed validation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--entry', default='index.html')
    parser.add_argument('--zip', dest='archive', type=Path)
    args = parser.parse_args()
    try:
        errors = verify(args.folder, args.entry, args.archive)
    except (OSError, UnicodeError, ValueError):
        errors = ['Package could not be read or parsed.']
    print(json.dumps({'passed': not errors, 'errors': errors,
                      'browser_and_sensitive_image_review_required': True}, indent=2))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
