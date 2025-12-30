"""Streamlit UI wrapper for the CLI tool."""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import streamlit as st

# Ensure project root is importable when running via `streamlit run ui/app.py`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.executor import CommandExecutor
from core.llm_client import LLMClient
from core.planner import LongTaskPlanner


def run_task(task: str, use_long: bool, auto_confirm: bool, dry_run: bool) -> str:
    """Execute the underlying CLI logic while capturing stdout/stderr."""
    buffer = io.StringIO()

    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        llm_client = LLMClient()
        if use_long:
            planner = LongTaskPlanner(llm_client)
            planner.execute_long_task(task, auto_confirm, dry_run)
        else:
            executor = CommandExecutor(llm_client)
            executor.execute_quick_task(task, auto_confirm, dry_run)

    return buffer.getvalue()


st.set_page_config(page_title="AI Command Helper", page_icon="🛠️", layout="wide")
st.title("AI-powered Linux Command Helper")

st.write("Use the toggles below to control planning mode, confirmation, and dry run.")

task_description = st.text_area(
    "Describe the task",
    height=140,
    placeholder="e.g., find all pdf files in current directory",
)

col1, col2, col3 = st.columns(3)
use_long = col1.toggle("Long-form planning (-l)", value=False)
auto_confirm = col2.toggle("Auto-confirm (-y)", value=True)
dry_run = col3.toggle("Dry run (show only)", value=True)

run_btn = st.button("Generate and run")

if run_btn:
    if not task_description.strip():
        st.warning("Please enter a task description.")
    else:
        with st.spinner("Working..."):
            try:
                output = run_task(task_description.strip(), use_long, auto_confirm, dry_run)
                if output:
                    st.code(output, language="bash")
                else:
                    st.info("No output returned.")
            except Exception as exc:  # surface any unexpected errors
                st.error(f"Error: {exc}")

st.caption(
    "Tip: Leave auto-confirm on to avoid interactive prompts inside the CLI flow. "
    "Use dry run to preview commands without executing them."
)
