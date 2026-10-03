"""Tests for the fenced-code-block example checker."""

from pathlib import Path

import pytest
from check_examples import Block, check_bash, check_python, extract_blocks, main

DOC = """\
# Title

```python
x = 1
```

Prose.

```bash
echo "hi"
```

```rust
fn main() {}
```
"""


def test_extract_blocks_returns_python_and_bash_with_fence_lines() -> None:
    blocks = extract_blocks(Path("doc.md"), DOC)

    assert [(b.language, b.line, b.code) for b in blocks] == [
        ("python", 3, "x = 1\n"),
        ("bash", 9, 'echo "hi"\n'),
    ]


def test_extract_blocks_normalizes_language_aliases() -> None:
    text = "```py\nx = 1\n```\n\n```sh\ntrue\n```\n\n```shell\ntrue\n```\n"

    blocks = extract_blocks(Path("doc.md"), text)

    assert [b.language for b in blocks] == ["python", "bash", "bash"]


def test_extract_blocks_skips_block_after_skip_marker() -> None:
    text = "<!-- check-examples: skip -->\n```python\nfragment(\n```\n\n```python\nx = 1\n```\n"

    blocks = extract_blocks(Path("doc.md"), text)

    assert [b.line for b in blocks] == [6]


def test_extract_blocks_ignores_blocks_nested_in_longer_fences() -> None:
    text = "````markdown\n```python\nx = 1\n```\n````\n"

    assert extract_blocks(Path("doc.md"), text) == []


def test_check_python_reports_typealias_at_document_line() -> None:
    code = "from typing import TypeAlias\n\nJson: TypeAlias = dict[str, object]\n"
    block = Block(path=Path("doc.md"), line=10, language="python", code=code)

    findings = check_python([block])

    assert any(f.line == 13 and "UP040" in f.message for f in findings)


def test_check_python_accepts_modern_code() -> None:
    code = (
        "type Json = dict[str, object]\n\n\n"
        "def first[T](items: list[T]) -> T:\n    return items[0]\n"
    )
    block = Block(path=Path("doc.md"), line=1, language="python", code=code)

    assert check_python([block]) == []


def test_check_bash_reports_sc2155_at_document_line() -> None:
    code = 'readonly DIR="$(pwd)"\necho "${DIR}"\n'
    block = Block(path=Path("doc.md"), line=4, language="bash", code=code)

    findings = check_bash([block])

    assert [(f.line, "SC2155" in f.message) for f in findings] == [(5, True)]


def test_check_bash_accepts_clean_script() -> None:
    code = 'dir="$(pwd)"\nreadonly dir\necho "${dir}"\n'
    block = Block(path=Path("doc.md"), line=1, language="bash", code=code)

    assert check_bash([block]) == []


def test_main_returns_one_and_prints_location_for_bad_example(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    doc = tmp_path / "SKILL.md"
    doc.write_text("```python\nfrom typing import TypeAlias\n\nJ: TypeAlias = int\n```\n")

    assert main([str(doc)]) == 1
    assert f"{doc}:4:" in capsys.readouterr().out


def test_main_returns_zero_for_clean_examples(tmp_path: Path) -> None:
    doc = tmp_path / "SKILL.md"
    doc.write_text("```python\ntype J = int\n```\n")

    assert main([str(doc)]) == 0


def test_check_python_raises_when_ruff_cannot_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("check_examples.RUFF_CONFIG", tmp_path / "missing.toml")
    block = Block(path=Path("doc.md"), line=1, language="python", code="x = 1\n")

    with pytest.raises(RuntimeError, match="exit code 2"):
        check_python([block])
