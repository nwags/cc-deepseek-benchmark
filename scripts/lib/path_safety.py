from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Iterator


class PathBoundaryError(ValueError):
    """A candidate path escaped its explicitly approved filesystem boundary."""


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def resolved_workspace(workspace: Path) -> Path:
    resolved = workspace.resolve(strict=True)
    if not resolved.is_dir():
        raise PathBoundaryError("supplied workspace is not a directory")
    return resolved


def ensure_workspace_directory(
    path: Path,
    *,
    workspace: Path,
    create: bool = False,
    label: str = "directory",
) -> Path:
    workspace_resolved = resolved_workspace(workspace)
    candidate = path if path.is_absolute() else workspace_resolved / path
    if candidate.name in {"", ".", ".."}:
        raise PathBoundaryError(f"{label} has an invalid filename")
    lexical = Path(os.path.abspath(candidate))
    if not is_relative_to(lexical, workspace_resolved):
        raise PathBoundaryError(f"{label} is outside the supplied workspace")
    current = workspace_resolved
    for part in lexical.relative_to(workspace_resolved).parts:
        current /= part
        if current.is_symlink():
            raise PathBoundaryError(f"{label} parent must not be a symbolic link")
    resolved_candidate = lexical.resolve(strict=False)
    if not is_relative_to(resolved_candidate, workspace_resolved):
        raise PathBoundaryError(f"{label} resolves outside the supplied workspace")
    if create:
        lexical.mkdir(parents=True, exist_ok=True)
    if not lexical.is_dir():
        raise PathBoundaryError(f"{label} is not a directory")
    return lexical.resolve(strict=True)


def ensure_workspace_output_path(
    path: Path,
    *,
    workspace: Path,
    create_parent: bool = False,
    label: str = "output path",
) -> Path:
    workspace_resolved = resolved_workspace(workspace)
    candidate = path if path.is_absolute() else workspace_resolved / path
    if candidate.name in {"", ".", ".."}:
        raise PathBoundaryError(f"{label} has an invalid filename")
    parent = ensure_workspace_directory(
        candidate.parent,
        workspace=workspace_resolved,
        create=create_parent,
        label=f"{label} parent",
    )
    lexical = parent / candidate.name
    if lexical.is_symlink():
        raise PathBoundaryError(f"{label} must not be a symbolic link")
    resolved = lexical.resolve(strict=False)
    if not is_relative_to(resolved, workspace_resolved):
        raise PathBoundaryError(f"{label} resolves outside the supplied workspace")
    return lexical


def resolve_under(
    path: Path,
    *,
    workspace: Path,
    parent: Path | None = None,
    approved_roots: Iterable[Path] = (),
    reject_symlink: bool = True,
    require_directory: bool = False,
    require_file: bool = False,
    label: str = "path",
) -> Path:
    workspace_resolved = resolved_workspace(workspace)
    candidate = path if path.is_absolute() else workspace_resolved / path
    if reject_symlink and candidate.is_symlink():
        raise PathBoundaryError(f"{label} must not be a symbolic link")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise PathBoundaryError(f"{label} does not exist") from exc
    if not is_relative_to(resolved, workspace_resolved):
        raise PathBoundaryError(f"{label} is outside the supplied workspace")

    if parent is not None:
        parent_resolved = parent.resolve(strict=True)
        if not is_relative_to(parent_resolved, workspace_resolved):
            raise PathBoundaryError(f"{label} parent is outside the supplied workspace")
        if not is_relative_to(resolved, parent_resolved):
            raise PathBoundaryError(f"{label} is outside its approved parent")

    roots = tuple(root.resolve(strict=True) for root in approved_roots)
    if roots and not any(is_relative_to(resolved, root) for root in roots):
        raise PathBoundaryError(f"{label} is outside all approved watch roots")
    if require_directory and not resolved.is_dir():
        raise PathBoundaryError(f"{label} is not a directory")
    if require_file and not resolved.is_file():
        raise PathBoundaryError(f"{label} is not a regular file")
    return resolved


def safe_relative(path: Path, *, root: Path, workspace: Path, label: str = "path") -> str:
    resolved = resolve_under(
        path,
        workspace=workspace,
        parent=root,
        require_file=path.is_file(),
        require_directory=path.is_dir(),
        label=label,
    )
    return resolved.relative_to(root.resolve(strict=True)).as_posix()


def read_json_file(path: Path, *, workspace: Path, parent: Path) -> dict[str, Any]:
    resolved = resolve_under(
        path,
        workspace=workspace,
        parent=parent,
        require_file=True,
        label="JSON file",
    )
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("JSON file is not parseable") from exc
    if not isinstance(value, dict):
        raise ValueError("JSON file root must be an object")
    return value


def iter_allowlisted_files(
    root: Path,
    *,
    workspace: Path,
    names: set[str],
) -> Iterator[Path]:
    root_resolved = resolve_under(
        root,
        workspace=workspace,
        require_directory=True,
        label="artifact root",
    )
    for directory, child_names, file_names in os.walk(root_resolved, followlinks=False):
        current = Path(directory)
        for child_name in tuple(child_names):
            child = current / child_name
            if child.is_symlink():
                child_names.remove(child_name)
                raise PathBoundaryError("artifact directory must not be a symbolic link")
            resolve_under(
                child,
                workspace=workspace,
                parent=root_resolved,
                require_directory=True,
                label="artifact directory",
            )
        for file_name in file_names:
            if file_name not in names:
                continue
            path = current / file_name
            yield resolve_under(
                path,
                workspace=workspace,
                parent=root_resolved,
                require_file=True,
                label="allowlisted artifact",
            )
