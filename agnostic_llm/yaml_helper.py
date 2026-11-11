"""Lightweight pure-Python YAML parser fallback for config files.
Used when pyyaml is not installed so the package works out-of-the-box.
"""
from __future__ import annotations
import json
import re
from typing import Any


def _parse_scalar(val: str) -> Any:
    val = val.strip()
    if val.startswith(('"', "'")) and val.endswith(('"', "'")) and len(val) >= 2:
        return val[1:-1]
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if val.lower() in ("null", "none", "~"):
        return None
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        pass
    # Inline lists like [a, b, c]
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        parts = [p.strip() for p in inner.split(",")]
        return [_parse_scalar(p) for p in parts if p]
    return val


def parse_yaml_text(text: str) -> dict[str, Any]:
    """Parse common subset of YAML (dictionaries, nested dictionaries, inline and block lists)."""
    lines = text.splitlines()
    root: dict[str, Any] = {}
    # stack holds (current_container, indent_level, key_or_index_in_parent)
    stack: list[tuple[Any, int]] = [(root, -1)]

    for raw_line in lines:
        # Strip comments
        line_no_comment = raw_line.split("#", 1)[0].rstrip()
        if not line_no_comment.strip():
            continue

        indent = len(line_no_comment) - len(line_no_comment.lstrip())
        content = line_no_comment.strip()

        # Pop from stack until we find the parent with smaller indent
        while len(stack) > 1 and indent <= stack[-1][1]:
            stack.pop()

        parent, _ = stack[-1]

        # Block list item: - value or - key: value
        if content.startswith("- "):
            item_text = content[2:].strip()
            if isinstance(parent, list):
                if ":" in item_text and not item_text.startswith(("{", "[")):
                    k, v = item_text.split(":", 1)
                    k, v = k.strip(), v.strip()
                    d = {k: _parse_scalar(v) if v else {}}
                    parent.append(d)
                    if not v:
                        stack.append((d[k], indent + 2))
                else:
                    parent.append(_parse_scalar(item_text))
            continue

        # Key-value or Key-block
        if ":" in content:
            key, sep, val = content.partition(":")
            key = key.strip()
            val = val.strip()

            if isinstance(parent, dict):
                if not val:
                    # New nested structure (dict by default)
                    new_obj: dict[str, Any] = {}
                    parent[key] = new_obj
                    stack.append((new_obj, indent))
                else:
                    parent[key] = _parse_scalar(val)

    return root


def load_config_data(path_or_str: str) -> dict[str, Any]:
    """Load config from YAML/JSON file path or string, using PyYAML if present or pure-Python fallback."""
    content = path_or_str
    if "\n" not in path_or_str and (path_or_str.endswith(".yaml") or path_or_str.endswith(".yml") or path_or_str.endswith(".json")):
        with open(path_or_str, "r", encoding="utf-8") as f:
            content = f.read()

    # Try JSON
    stripped = content.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            return json.loads(stripped)
        except Exception:
            pass

    # Try PyYAML
    try:
        import yaml
        res = yaml.safe_load(content)
        if isinstance(res, dict):
            return res
    except ImportError:
        pass
    except Exception:
        pass

    # Pure Python fallback
    return parse_yaml_text(content)

