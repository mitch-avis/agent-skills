"""Lint the Python and Bash code blocks embedded in skill Markdown files.

Python blocks go through ruff with ``examples-ruff.toml``; Bash blocks go through ShellCheck.
Findings are reported against the Markdown file and line, so a broken example can be fixed where
it lives. Put ``<!-- check-examples: skip -->`` on the line before a fence to exempt a block that
is deliberately incomplete.

Usage: ``.venv/bin/python scripts/check_examples.py [FILE ...]``; with no files, every
``SKILL.md`` and reference Markdown file in the repository is checked.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

REPO_ROOT = Path(__file__).resolve().parent.parent
RUFF_CONFIG = Path(__file__).resolve().parent / "examples-ruff.toml"
SKIP_MARKER = "<!-- check-examples: skip -->"
LANGUAGES = {"python": "python", "py": "python", "bash": "bash", "sh": "bash", "shell": "bash"}
SHELLCHECK_EXCLUDES = "SC2034,SC2154"  # unused or externally set variables in fragments
FENCE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})(?P<info>[^`]*)$")


@dataclass(frozen=True)
class Block:
    """A fenced code block taken from a Markdown file.

    Attributes:
        path: The Markdown file the block came from.
        line: The 1-based line number of the opening fence.
        language: The normalized language, ``python`` or ``bash``.
        code: The block's content, ending with a newline.
    """

    path: Path
    line: int
    language: str
    code: str


@dataclass(frozen=True)
class Finding:
    """A lint result mapped back to a Markdown location.

    Attributes:
        path: The Markdown file containing the example.
        line: The 1-based line in that file.
        message: The rule code and description from the linter.
    """

    path: Path
    line: int
    message: str


def extract_blocks(path: Path, text: str) -> list[Block]:
    """Return the top-level Python and Bash fenced blocks in a Markdown document.

    Blocks nested inside a longer fence (for example a ```` ```` ```` Markdown sample) and blocks
    preceded by the skip marker are left out.

    Args:
        path: The file the text came from, recorded on each block.
        text: The Markdown source.

    Returns:
        The matching blocks in document order.
    """
    blocks: list[Block] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        opening = FENCE.match(lines[index])
        if opening is None:
            index += 1
            continue
        fence = opening["fence"]
        language = LANGUAGES.get(opening["info"].strip().split(" ")[0].lower(), "")
        body: list[str] = []
        end = index + 1
        while end < len(lines):
            closing = FENCE.match(lines[end])
            if (
                closing is not None
                and closing["fence"][0] == fence[0]
                and len(closing["fence"]) >= len(fence)
                and not closing["info"].strip()
            ):
                break
            body.append(lines[end])
            end += 1
        if language and not _skipped(lines, index):
            code = "\n".join(body) + "\n"
            blocks.append(Block(path=path, line=index + 1, language=language, code=code))
        index = end + 1
    return blocks


def _skipped(lines: Sequence[str], fence_index: int) -> bool:
    previous = fence_index - 1
    while previous >= 0 and not lines[previous].strip():
        previous -= 1
    return previous >= 0 and lines[previous].strip() == SKIP_MARKER


def check_python(blocks: Iterable[Block]) -> list[Finding]:
    """Run ruff on Python blocks and map its diagnostics to Markdown lines.

    Args:
        blocks: Blocks whose language is ``python``.

    Returns:
        One finding per ruff diagnostic.
    """
    return _run_on_files(blocks, ".py", _ruff_command(), _parse_ruff)


def check_bash(blocks: Iterable[Block]) -> list[Finding]:
    """Run ShellCheck on Bash blocks and map its diagnostics to Markdown lines.

    Args:
        blocks: Blocks whose language is ``bash``.

    Returns:
        One finding per ShellCheck diagnostic at warning severity or above.
    """
    command = [
        _require("shellcheck"),
        "--shell=bash",
        "--severity=warning",
        "--format=json1",
        f"--exclude={SHELLCHECK_EXCLUDES}",
    ]
    return _run_on_files(blocks, ".sh", command, _parse_shellcheck)


type _Parser = Callable[[str], list[tuple[str, int, str]]]


def _require(tool: str) -> str:
    found = shutil.which(tool)
    if found is None:
        msg = f"{tool} not found on PATH"
        raise FileNotFoundError(msg)
    return found


def _ruff_command() -> list[str]:
    local = REPO_ROOT / ".venv" / "bin" / "ruff"
    ruff = str(local) if local.exists() else _require("ruff")
    return [
        ruff,
        "check",
        "--no-cache",
        f"--config={RUFF_CONFIG}",
        "--output-format=json",
    ]


class _RuffLocation(TypedDict):
    row: int


class _RuffDiagnostic(TypedDict):
    code: str | None
    message: str
    filename: str
    location: _RuffLocation


class _ShellCheckComment(TypedDict):
    file: str
    line: int
    code: int
    message: str


class _ShellCheckReport(TypedDict):
    comments: list[_ShellCheckComment]


def _parse_ruff(stdout: str) -> list[tuple[str, int, str]]:
    diagnostics: list[_RuffDiagnostic] = json.loads(stdout or "[]")
    return [
        (
            item["filename"],
            item["location"]["row"],
            f"{item['code'] or 'syntax-error'} {item['message']}",
        )
        for item in diagnostics
    ]


def _parse_shellcheck(stdout: str) -> list[tuple[str, int, str]]:
    report: _ShellCheckReport = json.loads(stdout or '{"comments": []}')
    return [
        (item["file"], item["line"], f"SC{item['code']} {item['message']}")
        for item in report["comments"]
    ]


def _run_on_files(
    blocks: Iterable[Block],
    suffix: str,
    command: list[str],
    parse: _Parser,
) -> list[Finding]:
    by_name: dict[str, Block] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for number, block in enumerate(blocks):
            file = Path(tmp) / f"block_{number}{suffix}"
            file.write_text(block.code)
            by_name[file.name] = block
        if not by_name:
            return []
        result = subprocess.run(  # noqa: S603  # argv is built from fixed tool paths
            [*command, *sorted(str(Path(tmp) / name) for name in by_name)],
            capture_output=True,
            text=True,
            check=False,
        )
    if result.returncode not in {0, 1}:
        msg = f"{command[0]} failed with exit code {result.returncode}: {result.stderr.strip()}"
        raise RuntimeError(msg)
    findings: list[Finding] = []
    for name, row, message in parse(result.stdout):
        block = by_name[Path(name).name]
        findings.append(Finding(path=block.path, line=block.line + row, message=message))
    return findings


def _default_paths() -> list[Path]:
    return sorted(
        path
        for pattern in ("*/SKILL.md", "*/references/**/*.md")
        for path in REPO_ROOT.glob(pattern)
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Check the examples in the given Markdown files, or in every skill when none are given.

    Args:
        argv: Markdown file paths; defaults to the command-line arguments.

    Returns:
        ``0`` when every example is clean, ``1`` when any finding is reported.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    paths = [Path(arg) for arg in args] or _default_paths()
    blocks = [block for path in paths for block in extract_blocks(path, path.read_text())]
    findings = check_python(b for b in blocks if b.language == "python")
    findings += check_bash(b for b in blocks if b.language == "bash")
    for finding in sorted(findings, key=lambda f: (str(f.path), f.line)):
        print(f"{finding.path}:{finding.line}: {finding.message}")  # noqa: T201  # CLI output
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
