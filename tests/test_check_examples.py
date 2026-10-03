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
    # Act
    blocks = extract_blocks(Path("doc.md"), DOC)

    # Assert
    assert [(b.language, b.line, b.code) for b in blocks] == [
        ("python", 3, "x = 1\n"),
        ("bash", 9, 'echo "hi"\n'),
    ]


def test_extract_blocks_normalizes_language_aliases() -> None:
    # Arrange
    text = "```py\nx = 1\n```\n\n```sh\ntrue\n```\n\n```shell\ntrue\n```\n"

    # Act
    blocks = extract_blocks(Path("doc.md"), text)

    # Assert
    assert [b.language for b in blocks] == ["python", "bash", "bash"]


def test_extract_blocks_skips_block_after_skip_marker() -> None:
    # Arrange
    text = "<!-- check-examples: skip -->\n```python\nfragment(\n```\n\n```python\nx = 1\n```\n"

    # Act
    blocks = extract_blocks(Path("doc.md"), text)

    # Assert
    assert [b.line for b in blocks] == [6]


def test_extract_blocks_ignores_blocks_nested_in_longer_fences() -> None:
    # Arrange
    text = "````markdown\n```python\nx = 1\n```\n````\n"

    # Act
    blocks = extract_blocks(Path("doc.md"), text)

    # Assert
    assert blocks == []


def test_check_python_reports_typealias_at_document_line() -> None:
    # Arrange
    code = "from typing import TypeAlias\n\nJson: TypeAlias = dict[str, object]\n"
    block = Block(path=Path("doc.md"), line=10, language="python", code=code)

    # Act
    findings = check_python([block])

    # Assert
    assert any(f.line == 13 and "UP040" in f.message for f in findings)


def test_check_python_accepts_modern_code() -> None:
    # Arrange
    code = (
        "type Json = dict[str, object]\n\n\n"
        'def first[T](items: list[T]) -> T:\n    """Return the first item."""\n'
        "    return items[0]\n"
    )
    block = Block(path=Path("doc.md"), line=1, language="python", code=code)

    # Act
    findings = check_python([block])

    # Assert
    assert findings == []


def test_check_bash_reports_sc2155_at_document_line() -> None:
    # Arrange
    code = 'readonly DIR="$(pwd)"\necho "${DIR}"\n'
    block = Block(path=Path("doc.md"), line=4, language="bash", code=code)

    # Act
    findings = check_bash([block])

    # Assert
    assert [(f.line, "SC2155" in f.message) for f in findings] == [(5, True)]


def test_check_bash_accepts_clean_script() -> None:
    # Arrange
    code = 'dir="$(pwd)"\nreadonly dir\necho "${dir}"\n'
    block = Block(path=Path("doc.md"), line=1, language="bash", code=code)

    # Act
    findings = check_bash([block])

    # Assert
    assert findings == []


def test_main_returns_one_and_prints_location_for_bad_example(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange
    doc = tmp_path / "SKILL.md"
    doc.write_text("```python\nfrom typing import TypeAlias\n\nJ: TypeAlias = int\n```\n")

    # Act
    status = main([str(doc)])

    # Assert
    assert status == 1
    assert f"{doc}:4:" in capsys.readouterr().out


def test_main_returns_zero_for_clean_examples(tmp_path: Path) -> None:
    # Arrange
    doc = tmp_path / "SKILL.md"
    doc.write_text("```python\ntype J = int\n```\n")

    # Act
    status = main([str(doc)])

    # Assert
    assert status == 0


def test_check_python_raises_when_ruff_cannot_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    monkeypatch.setattr("check_examples.RUFF_CONFIG", tmp_path / "missing.toml")
    block = Block(path=Path("doc.md"), line=1, language="python", code="x = 1\n")

    # Act & Assert
    with pytest.raises(RuntimeError, match="exit code 2"):
        check_python([block])


def test_check_python_unformatted_block_reports_format_finding() -> None:
    # Arrange
    code = 'x = {  "a":1 }\n'
    block = Block(path=Path("doc.md"), line=7, language="python", code=code)

    # Act
    findings = check_python([block])

    # Assert
    assert [(f.line, f.message.split(" ")[0]) for f in findings] == [(8, "ruff-format")]


def test_check_python_test_block_allows_assert_and_missing_docstring() -> None:
    # Arrange
    code = "def test_total_is_five() -> None:\n    assert compute() == 5\n"
    block = Block(path=Path("doc.md"), line=1, language="python", code=code)

    # Act
    findings = check_python([block])

    # Assert
    assert findings == []


def test_check_python_non_test_block_requires_docstring() -> None:
    # Arrange
    code = "def compute() -> int:\n    return 5\n"
    block = Block(path=Path("doc.md"), line=1, language="python", code=code)

    # Act
    findings = check_python([block])

    # Assert
    assert [f.message.split(" ")[0] for f in findings] == ["D103"]
