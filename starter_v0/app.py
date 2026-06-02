"""Streamlit UI cho Research Agent (bonus deploy theo README).

Tái sử dụng đúng tool-loop của `chat.py` (multi-round tool calling) nên UI và
CLI có cùng hành vi routing/boundary. Mỗi tin nhắn của user = 1 turn.

Chạy local:
    cd starter_v0
    streamlit run app.py

Deploy Streamlit Community Cloud: trỏ tới file này, đặt OPENAI_API_KEY (và các
key tool) trong phần Secrets của app.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

# Tái dùng nguyên logic từ chat.py (import này cũng tự load .env qua load_lab_env).
from chat import ARTIFACTS_DIR, run_model_tool_loop, trim_history
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import build_artifact_version

PROMPT_PATH = ARTIFACTS_DIR / "system_prompt.md"
TOOLS_PATH = ARTIFACTS_DIR / "tools.yaml"

st.set_page_config(page_title="Research Agent", page_icon="🔎", layout="centered")


@st.cache_resource(show_spinner=False)
def load_runtime(provider_name: str, version: str, prompt_mtime: float, tools_mtime: float):
    """Provider + tool declarations. mtime args invalidate cache khi artifact đổi."""
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    openai_tools = to_openai_tools(load_tool_declarations(TOOLS_PATH))
    provider = make_provider(provider_name)
    artifact = build_artifact_version(version, PROMPT_PATH, TOOLS_PATH)
    return system_prompt, openai_tools, provider, artifact


# ----------------------------- Sidebar config -----------------------------
st.sidebar.title("⚙️ Cấu hình")
provider_name = st.sidebar.selectbox("Provider", ["openai", "openrouter", "anthropic", "gemini"], index=0)
version = st.sidebar.text_input("Version", "v3")
history_window = st.sidebar.slider("History window (cặp lượt giữ lại)", 1, 10, 5)
max_tool_rounds = st.sidebar.slider("Max tool rounds / lượt", 1, 6, 4)
if st.sidebar.button("🗑️ Xoá hội thoại"):
    st.session_state.history = []
    st.session_state.display = []
    st.rerun()

system_prompt, openai_tools, provider, artifact = load_runtime(
    provider_name, version, PROMPT_PATH.stat().st_mtime, TOOLS_PATH.stat().st_mtime
)
default_model = getattr(provider, "default_model", None)

st.title("🔎 Research Agent")
st.caption(f"artifact_version = `{artifact.artifact_version}` · model = `{default_model}`")

# ----------------------------- State -----------------------------
if "history" not in st.session_state:
    st.session_state.history = []   # [{role, content}] truyền vào model
    st.session_state.display = []   # [{role, content, tool_calls}] để render

# Render lịch sử
for msg in st.session_state.display:
    with st.chat_message(msg["role"]):
        for tc in msg.get("tool_calls", []):
            st.code(f"🔧 {tc['name']}({tc['args']})", language="json")
        st.markdown(msg["content"])

# ----------------------------- Turn handling -----------------------------
user_text = st.chat_input("Hỏi gì đó… (vd: Tin AI hôm nay có gì?)")
if user_text:
    with st.chat_message("user"):
        st.markdown(user_text)
    st.session_state.display.append({"role": "user", "content": user_text, "tool_calls": []})

    messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state.history, history_window),
        {"role": "user", "content": user_text},
    ]

    with st.chat_message("assistant"):
        with st.spinner("Đang suy nghĩ và gọi tool…"):
            try:
                result = run_model_tool_loop(
                    provider=provider,
                    messages=messages,
                    tools=openai_tools,
                    model=None,
                    max_tool_rounds=max_tool_rounds,
                )
                assistant_text = result["assistant_text"]
                status = result["status"]
            except Exception as exc:  # noqa: BLE001 — surface lỗi provider ra UI
                assistant_text = f"⚠️ Lỗi: {type(exc).__name__}: {exc}"
                status = "provider_error"
                result = {"rounds": []}

        calls = [c for r in result.get("rounds", []) for c in r.get("tool_calls", [])]
        for tc in calls:
            st.code(f"🔧 {tc['name']}({tc['args']})", language="json")
        if status == "waiting_for_user":
            st.info("Agent đang chờ bạn bổ sung thông tin ⤵️")
        st.markdown(assistant_text)

    st.session_state.display.append({"role": "assistant", "content": assistant_text, "tool_calls": calls})
    st.session_state.history.append({"role": "user", "content": user_text})
    st.session_state.history.append({"role": "assistant", "content": assistant_text})
