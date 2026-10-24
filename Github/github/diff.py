import difflib


def unified_diff(original: str, updated: str, path: str, context: int = 3) -> str:
    """Return a unified text diff for a staged file change."""
    lines = difflib.unified_diff(
        original.splitlines(),
        updated.splitlines(),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=max(0, context),
        lineterm="",
    )
    return "\n".join(lines)
