#!/usr/bin/env python3
"""Generate and serve a review page for eval results.

Reads the workspace directory, discovers runs (directories with outputs/), embeds all output data
into a self-contained HTML page, and serves it via a tiny HTTP server. Feedback auto-saves to
feedback.json in the workspace.

Usage:
    # Live server (opens browser automatically):

    python generate_review.py <workspace> [--port PORT] [--skill-name NAME]

    # Write a standalone HTML file instead of starting a server:

    python generate_review.py <workspace> --static <output.html>

    # Include previous iteration's outputs and feedback for comparison:

    python generate_review.py <workspace> --previous-workspace <prev-workspace>

    # Embed benchmark results in the Benchmark tab:

    python generate_review.py <workspace> --benchmark <benchmark.json>

No dependencies beyond the Python stdlib are required.
"""

import argparse
import base64
import contextlib
import json
import mimetypes
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

type JSONValue = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]
type JSONDict = dict[str, JSONValue]
type EvalID = str | int


class TextOutput(TypedDict):
    """Text file output representation."""

    name: str
    type: Literal["text"]
    content: str


class ImageOutput(TypedDict):
    """Image file output representation."""

    name: str
    type: Literal["image"]
    mime: str
    data_uri: str


class PdfOutput(TypedDict):
    """PDF file output representation."""

    name: str
    type: Literal["pdf"]
    data_uri: str


class XlsxOutput(TypedDict):
    """Excel spreadsheet output representation."""

    name: str
    type: Literal["xlsx"]
    data_b64: str


class BinaryOutput(TypedDict):
    """Binary file output representation."""

    name: str
    type: Literal["binary"]
    mime: str
    data_uri: str


class ErrorOutput(TypedDict):
    """Error output representation."""

    name: str
    type: Literal["error"]
    content: str


type EmbeddedFile = TextOutput | ImageOutput | PdfOutput | XlsxOutput | BinaryOutput | ErrorOutput


class RunRecord(TypedDict):
    """Evaluation run record with metadata and outputs."""

    id: str
    prompt: str
    eval_id: EvalID | None
    outputs: list[EmbeddedFile]
    grading: JSONDict | None


class PreviousRunData(TypedDict):
    """Previous iteration's feedback and outputs."""

    feedback: str
    outputs: list[EmbeddedFile]


# Files to exclude from output listings
METADATA_FILES = {"transcript.md", "user_notes.md", "metrics.json"}

# Extensions we render as inline text
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".csv",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".css",
    ".sh",
    ".rb",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".sql",
    ".r",
    ".toml",
}

# Extensions we render as inline images
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

# MIME type overrides for common types
MIME_OVERRIDES = {
    ".svg": "image/svg+xml",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def get_mime_type(path: Path) -> str:
    """Return the best-effort MIME type for the given path."""
    ext = path.suffix.lower()
    if ext in MIME_OVERRIDES:
        return MIME_OVERRIDES[ext]
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _read_json_object(path: Path) -> JSONDict | None:
    """Read a JSON file and return it only when it is a top-level object."""
    with contextlib.suppress(json.JSONDecodeError, OSError):
        raw = json.loads(path.read_text())
        if isinstance(raw, dict):
            return cast(JSONDict, raw)
    return None


def _run_sort_key(run: RunRecord) -> tuple[int, str, str]:
    """Sort runs by eval_id (if present) and then by stable run id."""
    eval_id = run["eval_id"]
    if eval_id is None:
        return (1, "", run["id"])
    return (0, str(eval_id), run["id"])


def find_runs(workspace: Path) -> list[RunRecord]:
    """Recursively find directories that contain an outputs/ subdirectory."""
    runs: list[RunRecord] = []
    _find_runs_recursive(workspace, workspace, runs)
    runs.sort(key=_run_sort_key)
    return runs


def _find_runs_recursive(root: Path, current: Path, runs: list[RunRecord]) -> None:
    if not current.is_dir():
        return

    outputs_dir = current / "outputs"
    if outputs_dir.is_dir():
        run = build_run(root, current)
        if run:
            runs.append(run)
        return

    skip = {"node_modules", ".git", "__pycache__", "skill", "inputs"}
    for child in sorted(current.iterdir()):
        if child.is_dir() and child.name not in skip:
            _find_runs_recursive(root, child, runs)


def build_run(root: Path, run_dir: Path) -> RunRecord | None:
    """Build a run dict with prompt, outputs, and grading data."""
    prompt = ""
    eval_id: EvalID | None = None

    # Try eval_metadata.json
    for candidate in [
        run_dir / "eval_metadata.json",
        run_dir.parent / "eval_metadata.json",
    ]:
        metadata = _read_json_object(candidate)
        if metadata is not None:
            prompt_value = metadata.get("prompt")
            if isinstance(prompt_value, str):
                prompt = prompt_value
            eval_id_value = metadata.get("eval_id")
            if isinstance(eval_id_value, (str, int)):
                eval_id = eval_id_value
            if prompt:
                break

    # Fall back to transcript.md
    if not prompt:
        for candidate in [
            run_dir / "transcript.md",
            run_dir / "outputs" / "transcript.md",
        ]:
            if candidate.exists():
                try:
                    text = candidate.read_text()
                    match = re.search(r"## Eval Prompt\n\n([\s\S]*?)(?=\n##|$)", text)
                    if match:
                        prompt = match.group(1).strip()
                except OSError:
                    pass
                if prompt:
                    break

    if not prompt:
        prompt = "(No prompt found)"

    run_id = str(run_dir.relative_to(root)).replace("/", "-").replace("\\", "-")

    # Collect output files
    outputs_dir = run_dir / "outputs"
    output_files: list[EmbeddedFile] = []
    if outputs_dir.is_dir():
        for f in sorted(outputs_dir.iterdir()):
            if f.is_file() and f.name not in METADATA_FILES:
                output_files.append(embed_file(f))

    # Load grading if present
    grading: JSONDict | None = None
    for candidate in [run_dir / "grading.json", run_dir.parent / "grading.json"]:
        grading_candidate = _read_json_object(candidate)
        if grading_candidate is not None:
            grading = grading_candidate
            if grading:
                break

    return {
        "id": run_id,
        "prompt": prompt,
        "eval_id": eval_id,
        "outputs": output_files,
        "grading": grading,
    }


def embed_file(path: Path) -> EmbeddedFile:
    """Read a file and return an embedded representation."""
    ext = path.suffix.lower()
    mime = get_mime_type(path)

    if ext in TEXT_EXTENSIONS:
        try:
            content = path.read_text(errors="replace")
        except OSError:
            content = "(Error reading file)"
        return {
            "name": path.name,
            "type": "text",
            "content": content,
        }
    elif ext in IMAGE_EXTENSIONS:
        try:
            raw = path.read_bytes()
            b64 = base64.b64encode(raw).decode("ascii")
        except OSError:
            return {
                "name": path.name,
                "type": "error",
                "content": "(Error reading file)",
            }
        return {
            "name": path.name,
            "type": "image",
            "mime": mime,
            "data_uri": f"data:{mime};base64,{b64}",
        }
    elif ext == ".pdf":
        try:
            raw = path.read_bytes()
            b64 = base64.b64encode(raw).decode("ascii")
        except OSError:
            return {
                "name": path.name,
                "type": "error",
                "content": "(Error reading file)",
            }
        return {
            "name": path.name,
            "type": "pdf",
            "data_uri": f"data:{mime};base64,{b64}",
        }
    elif ext == ".xlsx":
        try:
            raw = path.read_bytes()
            b64 = base64.b64encode(raw).decode("ascii")
        except OSError:
            return {
                "name": path.name,
                "type": "error",
                "content": "(Error reading file)",
            }
        return {
            "name": path.name,
            "type": "xlsx",
            "data_b64": b64,
        }
    else:
        # Binary / unknown — base64 download link
        try:
            raw = path.read_bytes()
            b64 = base64.b64encode(raw).decode("ascii")
        except OSError:
            return {
                "name": path.name,
                "type": "error",
                "content": "(Error reading file)",
            }
        return {
            "name": path.name,
            "type": "binary",
            "mime": mime,
            "data_uri": f"data:{mime};base64,{b64}",
        }


def load_previous_iteration(workspace: Path) -> dict[str, PreviousRunData]:
    """Load previous iteration's feedback and outputs.

    Returns a map of run_id -> {"feedback": str, "outputs": list[EmbeddedFile]}.
    """
    result: dict[str, PreviousRunData] = {}

    # Load feedback
    feedback_map: dict[str, str] = {}
    feedback_path = workspace / "feedback.json"
    if feedback_path.exists():
        data = _read_json_object(feedback_path)
        reviews = data.get("reviews") if data else None
        if isinstance(reviews, list):
            for review in reviews:
                if not isinstance(review, dict):
                    continue
                run_id = review.get("run_id")
                feedback = review.get("feedback")
                if isinstance(run_id, str) and isinstance(feedback, str) and feedback.strip():
                    feedback_map[run_id] = feedback

    # Load runs (to get outputs)
    prev_runs = find_runs(workspace)
    for run in prev_runs:
        result[run["id"]] = {
            "feedback": feedback_map.get(run["id"], ""),
            "outputs": run["outputs"],
        }

    # Also add feedback for run_ids that had feedback but no matching run
    for run_id, fb in feedback_map.items():
        if run_id not in result:
            result[run_id] = {"feedback": fb, "outputs": []}

    return result


def generate_html(
    runs: list[RunRecord],
    skill_name: str,
    previous: dict[str, PreviousRunData] | None = None,
    benchmark: JSONDict | None = None,
) -> str:
    """Generate the complete standalone HTML page with embedded data."""
    template_path = Path(__file__).parent / "viewer.html"
    template = template_path.read_text()

    # Build previous_feedback and previous_outputs maps for the template
    previous_feedback: dict[str, str] = {}
    previous_outputs: dict[str, list[EmbeddedFile]] = {}
    if previous:
        for run_id, data in previous.items():
            if data["feedback"]:
                previous_feedback[run_id] = data["feedback"]
            if data["outputs"]:
                previous_outputs[run_id] = data["outputs"]

    embedded: dict[str, object] = {
        "skill_name": skill_name,
        "runs": runs,
        "previous_feedback": previous_feedback,
        "previous_outputs": previous_outputs,
    }
    if benchmark:
        embedded["benchmark"] = benchmark

    data_json = json.dumps(embedded)

    return template.replace("/*__EMBEDDED_DATA__*/", f"const EMBEDDED_DATA = {data_json};")


# ---------------------------------------------------------------------------
# HTTP server (stdlib only, zero dependencies)
# ---------------------------------------------------------------------------


def _kill_port(port: int) -> None:
    """Kill any process listening on the given port."""
    try:
        lsof_path = shutil.which("lsof")
        if lsof_path is None:
            print("Note: lsof not found, cannot check if port is in use", file=sys.stderr)
            return

        # lsof path is resolved via shutil.which and command arguments are fixed.
        result = subprocess.run(  # noqa: S603
            [lsof_path, "-ti", f":{port}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for pid_str in result.stdout.strip().split("\n"):
            if pid_str.strip():
                with contextlib.suppress(ProcessLookupError, ValueError):
                    os.kill(int(pid_str.strip()), signal.SIGTERM)
        if result.stdout.strip():
            time.sleep(0.5)
    except subprocess.TimeoutExpired:
        pass


class ReviewHandler(BaseHTTPRequestHandler):
    """Serves the review HTML and handles feedback saves.

    Regenerates the HTML on each page load so that refreshing the browser picks up new eval outputs
    without restarting the server.
    """

    def __init__(
        self,
        workspace: Path,
        skill_name: str,
        feedback_path: Path,
        previous: dict[str, PreviousRunData],
        benchmark_path: Path | None,
        *args: Any,
        **kwargs: Any,
    ):
        """Initialize a request handler bound to the current workspace state."""
        self.workspace = workspace
        self.skill_name = skill_name
        self.feedback_path = feedback_path
        self.previous = previous
        self.benchmark_path = benchmark_path
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        """Serve the review page and current feedback JSON."""
        if self.path == "/" or self.path == "/index.html":
            # Regenerate HTML on each request (re-scans workspace for new outputs)
            runs = find_runs(self.workspace)
            benchmark: JSONDict | None = None
            if self.benchmark_path and self.benchmark_path.exists():
                benchmark = _read_json_object(self.benchmark_path)
            html = generate_html(runs, self.skill_name, self.previous, benchmark)
            content = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == "/api/feedback":
            data = b"{}"
            if self.feedback_path.exists():
                data = self.feedback_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        """Persist feedback payloads sent by the browser UI."""
        if self.path == "/api/feedback":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body)
                if not isinstance(payload, dict) or "reviews" not in payload:
                    raise ValueError("Expected JSON object with 'reviews' key")
                self.feedback_path.write_text(json.dumps(payload, indent=2) + "\n")
                resp = b'{"ok":true}'
                self.send_response(200)
            except (json.JSONDecodeError, OSError, ValueError) as e:
                resp = json.dumps({"error": str(e)}).encode()
                self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
        else:
            self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        """Suppress default request logs to keep terminal output focused."""
        # Suppress request logging to keep terminal clean
        pass


def main() -> None:
    """Parse arguments, generate the review page, and run the local HTTP server."""
    parser = argparse.ArgumentParser(description="Generate and serve eval review")
    parser.add_argument("workspace", type=Path, help="Path to workspace directory")
    parser.add_argument("--port", "-p", type=int, default=3117, help="Server port (default: 3117)")
    parser.add_argument("--skill-name", "-n", type=str, default=None, help="Skill name for header")
    parser.add_argument(
        "--previous-workspace",
        type=Path,
        default=None,
        help="Path to previous iteration's workspace (shows old outputs and feedback as context)",
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=None,
        help="Path to benchmark.json to show in the Benchmark tab",
    )
    parser.add_argument(
        "--static",
        "-s",
        type=Path,
        default=None,
        help="Write standalone HTML to this path instead of starting a server",
    )
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        print(f"Error: {workspace} is not a directory", file=sys.stderr)
        sys.exit(1)

    runs = find_runs(workspace)
    if not runs:
        print(f"No runs found in {workspace}", file=sys.stderr)
        sys.exit(1)

    skill_name = args.skill_name or workspace.name.replace("-workspace", "")
    feedback_path = workspace / "feedback.json"

    previous: dict[str, PreviousRunData] = {}
    if args.previous_workspace:
        previous = load_previous_iteration(args.previous_workspace.resolve())

    benchmark_path = args.benchmark.resolve() if args.benchmark else None
    benchmark: JSONDict | None = None
    if benchmark_path and benchmark_path.exists():
        benchmark = _read_json_object(benchmark_path)

    if args.static:
        html = generate_html(runs, skill_name, previous, benchmark)
        args.static.parent.mkdir(parents=True, exist_ok=True)
        args.static.write_text(html)
        print(f"\n  Static viewer written to: {args.static}\n")
        sys.exit(0)

    # Kill any existing process on the target port
    port = args.port
    _kill_port(port)
    handler = partial(ReviewHandler, workspace, skill_name, feedback_path, previous, benchmark_path)
    try:
        server = HTTPServer(("127.0.0.1", port), handler)
    except OSError:
        # Port still in use after kill attempt — find a free one
        server = HTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]

    url = f"http://localhost:{port}"
    print("\n  Eval Viewer")
    print("  ─────────────────────────────────")
    print(f"  URL:       {url}")
    print(f"  Workspace: {workspace}")
    print(f"  Feedback:  {feedback_path}")
    if previous:
        print(f"  Previous:  {args.previous_workspace} ({len(previous)} runs)")
    if benchmark_path:
        print(f"  Benchmark: {benchmark_path}")
    print("\n  Press Ctrl+C to stop.\n")

    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
