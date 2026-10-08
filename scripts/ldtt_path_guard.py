#!/usr/bin/env python3
"""Resolve a repo-relative path and keep it inside --root.

Usage (cwd = repo root):
  python3 scripts/ldtt_path_guard.py --root stamps|trust --path REL [--must-exist]

Prints one resolved path on stdout and exits 0. Exit 2 (stderr) if the path
is absolute, a ".." segment leaves --root, a symlink resolves outside --root,
the resolved path is outside --root, or --must-exist and the path is missing.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def is_absolute_path(raw: str) -> bool:
    if raw.startswith(("/", "\\")):
        return True
    # Drive-absolute or drive-relative (C:\..., C:foo). Both can leave the repo.
    if len(raw) >= 2 and raw[0].isalpha() and raw[1] == ":":
        return True
    return False


def segments(raw: str) -> list[str]:
    return raw.replace("\\", "/").split("/")


def inside(cursor: list[str], root_parts: list[str]) -> bool:
    return len(cursor) >= len(root_parts) and cursor[: len(root_parts)] == root_parts


def lexical_parts(path: str, root: str) -> tuple[list[str], list[str]]:
    """Return (root_parts, path_parts) or exit 2.

    ".." is applied lexically. Path.resolve() is not used here: it would
    collapse ".." and follow links before the escape is visible.
    """
    if is_absolute_path(path):
        fail(f"absolute path: {path}")
    if is_absolute_path(root):
        fail(f"absolute --root: {root}")

    root_parts: list[str] = []
    for seg in segments(root):
        if seg in ("", "."):
            continue
        if seg == "..":
            fail(".. escapes --root")
        root_parts.append(seg)
    if not root_parts:
        fail("empty --root")

    cursor: list[str] = []
    for seg in segments(path):
        if seg in ("", "."):
            continue
        if seg == "..":
            if not cursor:
                fail(".. escapes --root")
            parent = cursor[:-1]
            if inside(cursor, root_parts) and not inside(parent, root_parts):
                fail(".. escapes --root")
            cursor = parent
            continue
        if "\x00" in seg:
            fail("invalid path")
        cursor.append(seg)

    if not inside(cursor, root_parts):
        fail(f"path is outside --root: {path}")
    return root_parts, cursor


def plain(path: Path) -> Path:
    """Drop a Windows \\\\?\\ prefix so containment checks share one path form."""
    text = str(path)
    if text.startswith("\\\\?\\"):
        rest = text[4:]
        if rest.startswith("UNC\\") or rest.startswith("UNC/"):
            rest = "\\\\" + rest[4:]
        return Path(rest)
    return path


def is_under(path: Path, root: Path) -> bool:
    try:
        path_r = os.path.normcase(str(plain(path.resolve(strict=False))))
        root_r = os.path.normcase(str(plain(root.resolve(strict=False))))
    except OSError:
        return False
    if path_r == root_r:
        return True
    prefix = root_r if root_r.endswith(os.sep) else root_r + os.sep
    return path_r.startswith(prefix)


def symlink_target(link: Path) -> Path:
    raw = plain(Path(os.readlink(link)))
    if not raw.is_absolute():
        raw = link.parent / raw
    return raw.resolve(strict=False)


def resolved_line(cwd: Path, final: Path, cursor: list[str]) -> str:
    try:
        resolved = plain(final.resolve(strict=False))
        return resolved.relative_to(plain(cwd.resolve())).as_posix()
    except (ValueError, OSError):
        return "/".join(cursor)


def guard(root: str, path: str, must_exist: bool) -> str:
    _root_parts, cursor = lexical_parts(path, root)
    cwd = Path.cwd()
    root_fs = cwd.joinpath(*_root_parts)
    root_resolved = root_fs.resolve(strict=False)

    current = cwd
    for part in cursor:
        current = current / part
        try:
            linked = current.is_symlink()
        except OSError as exc:
            fail(f"symlink escapes --root: {exc}")
        if not linked:
            continue
        try:
            target = symlink_target(current)
        except OSError as exc:
            fail(f"symlink escapes --root: {exc}")
        if not is_under(target, root_resolved):
            fail(f"symlink escapes --root: {path}")

    final = cwd.joinpath(*cursor)
    resolved = final.resolve(strict=False)
    if not is_under(resolved, root_resolved):
        fail(f"path is outside --root: {path}")
    if must_exist and not final.exists():
        fail(f"path does not exist: {path}")
    return resolved_line(cwd, resolved, cursor)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Keep a path inside stamps/ or trust/.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--must-exist", action="store_true")
    args = parser.parse_args(argv)
    print(guard(args.root, args.path, args.must_exist))
    return 0


if __name__ == "__main__":
    sys.exit(main())
