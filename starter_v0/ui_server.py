from __future__ import annotations

import argparse
import json
import re
import threading
import uuid
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from chat import run_model_tool_loop, trim_history, write_transcript
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"


UI_LANGUAGE_INSTRUCTION = """

UI demo language rule:
- Luôn trả lời người dùng bằng tiếng Việt tự nhiên, rõ ràng.
- Nếu tool trả về nội dung tiếng Anh, hãy tóm tắt và diễn giải lại bằng tiếng Việt.
- Giữ link, tên paper, tên nguồn, tên tài khoản và mã định danh ở dạng gốc.
- Khi cần hỏi lại, hỏi bằng tiếng Việt.
"""


HTML = """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Research Agent v3</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101316;
      --panel: #181d22;
      --panel-soft: #20262d;
      --line: #313b45;
      --text: #eef4f2;
      --muted: #9fa9ad;
      --accent: #42c7b7;
      --gold: #f5b85a;
      --user: #2d7577;
      --agent: #232a32;
      --error: #e06a6a;
      --shadow: 0 18px 60px rgba(0, 0, 0, .36);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      overflow: hidden;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px),
        linear-gradient(180deg, rgba(255,255,255,.025) 1px, transparent 1px),
        var(--bg);
      background-size: 34px 34px;
      color: var(--text);
    }

    .shell {
      width: min(1180px, calc(100vw - 32px));
      height: calc(100vh - 32px);
      min-height: 0;
      margin: 16px auto;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 318px;
      align-items: stretch;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(24, 29, 34, .95);
      box-shadow: var(--shadow);
    }

    .main {
      min-width: 0;
      min-height: 0;
      height: calc(100vh - 32px);
      max-height: calc(100vh - 32px);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border-right: 1px solid var(--line);
    }

    .topbar {
      height: 68px;
      flex: 0 0 68px;
      padding: 0 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      border-bottom: 1px solid var(--line);
      background: rgba(16, 19, 22, .82);
    }

    .brand {
      min-width: 0;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .mark {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      display: grid;
      place-items: center;
      flex: 0 0 auto;
      background: conic-gradient(from 210deg, var(--accent), #7f8cff, var(--gold), var(--accent));
      color: #07100f;
      font-weight: 900;
      letter-spacing: 0;
    }

    h1 {
      margin: 0;
      font-size: 17px;
      line-height: 1.2;
      letter-spacing: 0;
    }

    .subtitle {
      margin-top: 3px;
      max-width: 56vw;
      color: var(--muted);
      font-size: 12px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .status {
      min-height: 34px;
      padding: 0 11px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #15191d;
      color: var(--muted);
      font-size: 12px;
    }

    .pulse {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 0 0 rgba(66, 199, 183, .6);
      animation: ping 1.8s infinite;
    }

    @keyframes ping {
      70% { box-shadow: 0 0 0 9px rgba(66, 199, 183, 0); }
      100% { box-shadow: 0 0 0 0 rgba(66, 199, 183, 0); }
    }

    .messages {
      flex: 1 1 auto;
      padding: 18px;
      min-height: 0;
      height: 100%;
      overflow: auto;
      scroll-behavior: smooth;
      overscroll-behavior: contain;
    }

    .message-row {
      display: flex;
      gap: 10px;
      margin-bottom: 14px;
      animation: bubbleIn .22s ease-out both;
    }

    .message-row.user { justify-content: flex-end; }

    @keyframes bubbleIn {
      from { opacity: 0; transform: translateY(8px) scale(.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    .avatar {
      width: 30px;
      height: 30px;
      border-radius: 7px;
      display: grid;
      place-items: center;
      flex: 0 0 auto;
      border: 1px solid var(--line);
      background: #11161a;
      color: var(--accent);
      font-size: 12px;
      font-weight: 800;
    }

    .agent-stack {
      width: min(760px, 88%);
      display: grid;
      gap: 8px;
    }

    .bubble {
      max-width: min(720px, 82%);
      padding: 12px 14px;
      border: 1px solid transparent;
      border-radius: 8px;
      line-height: 1.5;
      font-size: 14px;
      white-space: pre-wrap;
      transition: transform .16s ease, border-color .16s ease, background .16s ease;
    }

    .message-row.agent .bubble {
      max-width: 100%;
      background: var(--agent);
      border-color: #303943;
    }

    .message-row.user .bubble {
      background: var(--user);
      color: #f5fffd;
      border-color: #3b858a;
    }

    .bubble:hover {
      transform: translateY(-1px);
      border-color: rgba(66, 199, 183, .72);
    }

    .tool-log {
      overflow: hidden;
      border: 1px solid #343f4a;
      border-radius: 8px;
      background: #141a1f;
      transition: transform .16s ease, border-color .16s ease;
    }

    .tool-log:hover {
      transform: translateY(-1px);
      border-color: rgba(245, 184, 90, .72);
    }

    .tool-log summary {
      min-height: 38px;
      padding: 0 12px;
      display: flex;
      align-items: center;
      gap: 9px;
      cursor: pointer;
      color: #e9f3f0;
      font-size: 13px;
      list-style: none;
      user-select: none;
    }

    .tool-log summary::-webkit-details-marker { display: none; }

    .log-icon {
      width: 24px;
      height: 24px;
      border-radius: 7px;
      display: grid;
      place-items: center;
      flex: 0 0 auto;
      background: rgba(245, 184, 90, .18);
      border: 1px solid rgba(245, 184, 90, .4);
      color: #ffd98f;
    }

    .log-count {
      margin-left: auto;
      color: var(--muted);
      font-size: 12px;
    }

    .log-body {
      padding: 10px 12px 12px;
      display: grid;
      gap: 10px;
      border-top: 1px solid #303943;
    }

    .round-card {
      padding: 10px;
      border: 1px solid #303943;
      border-radius: 8px;
      background: #101519;
    }

    .round-title {
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
      color: #dce8e6;
      font-size: 13px;
      font-weight: 750;
    }

    .step {
      margin-top: 8px;
      padding: 9px 10px;
      border-left: 2px solid var(--accent);
      border-radius: 0 8px 8px 0;
      background: #161d22;
    }

    .step-title {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #f4faf8;
      font-size: 13px;
      font-weight: 750;
    }

    .step-action {
      margin-top: 3px;
      color: var(--muted);
      font-size: 12px;
    }

    .json-block {
      margin: 8px 0 0;
      padding: 9px;
      overflow-x: auto;
      border: 1px solid #2d3741;
      border-radius: 8px;
      background: #0d1115;
      color: #d8e1e0;
      white-space: pre-wrap;
      font: 12px/1.45 Consolas, "SFMono-Regular", monospace;
    }

    .composer {
      flex: 0 0 auto;
      padding: 14px;
      border-top: 1px solid var(--line);
      background: rgba(16, 19, 22, .82);
    }

    .quick {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 10px;
    }

    .quick button,
    .send {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #171c21;
      color: var(--text);
      cursor: pointer;
      transition: transform .16s ease, border-color .16s ease, background .16s ease;
    }

    .quick button {
      min-height: 32px;
      padding: 0 10px;
      color: #d7dddf;
      font-size: 12px;
      white-space: nowrap;
    }

    .quick button:hover,
    .send:hover {
      transform: translateY(-1px);
      border-color: var(--accent);
      background: #202930;
    }

    .input-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 46px;
      gap: 10px;
      align-items: end;
    }

    textarea {
      width: 100%;
      min-height: 48px;
      max-height: 140px;
      padding: 13px 14px;
      resize: vertical;
      border: 1px solid #3a4550;
      border-radius: 8px;
      background: #11161a;
      color: var(--text);
      outline: none;
      font: inherit;
      line-height: 1.45;
    }

    textarea:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(66, 199, 183, .12);
    }

    .send {
      height: 48px;
      background: var(--accent);
      color: #07100f;
      border-color: transparent;
      font-size: 18px;
      font-weight: 900;
    }

    .send:disabled {
      opacity: .62;
      cursor: wait;
      transform: none;
    }

    aside {
      min-width: 0;
      min-height: 0;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      background: #15191d;
    }

    .side-head {
      padding: 16px;
      border-bottom: 1px solid var(--line);
    }

    .side-title {
      margin: 0;
      color: #cbd4d6;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }

    .meta {
      padding: 14px 16px;
      display: grid;
      gap: 10px;
      overflow: auto;
    }

    .metric {
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #101519;
      transition: transform .16s ease, border-color .16s ease;
    }

    .metric:hover {
      transform: translateY(-1px);
      border-color: #53616e;
    }

    .metric span {
      display: block;
      margin-bottom: 6px;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }

    .metric strong {
      display: block;
      overflow-wrap: anywhere;
      font-size: 13px;
      line-height: 1.35;
    }

    .typing {
      display: inline-flex;
      gap: 5px;
      padding: 4px 0;
    }

    .typing i {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--accent);
      animation: typing 1s infinite ease-in-out;
    }

    .typing i:nth-child(2) { animation-delay: .14s; }
    .typing i:nth-child(3) { animation-delay: .28s; }

    @keyframes typing {
      0%, 80%, 100% { transform: translateY(0); opacity: .45; }
      40% { transform: translateY(-5px); opacity: 1; }
    }

    .error {
      color: #ffd7d7;
      border-color: rgba(224, 106, 106, .55) !important;
      background: rgba(224, 106, 106, .12) !important;
    }

    @media (max-width: 860px) {
      .shell {
        width: 100vw;
        height: 100vh;
        min-height: 0;
        margin: 0;
        grid-template-columns: 1fr;
        border-radius: 0;
      }

      aside { display: none; }
      .main { border-right: 0; }
      .main {
        height: 100vh;
        max-height: 100vh;
      }
      .subtitle { max-width: 58vw; }
      .bubble { max-width: 88%; }
      .agent-stack { width: 92%; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <main class="main">
      <header class="topbar">
        <div class="brand">
          <div class="mark">V3</div>
          <div>
            <h1>Research Agent</h1>
            <div class="subtitle" id="artifact">Đang tải artifact...</div>
          </div>
        </div>
        <div class="status"><span class="pulse"></span><span id="statusText">Sẵn sàng</span></div>
      </header>

      <section class="messages" id="messages" aria-live="polite"></section>

      <section class="composer">
        <div class="quick">
          <button type="button" data-prompt="Tìm trên web tin AI hôm nay và tìm thêm tweet về AI.">AI web + tweets</button>
          <button type="button" data-prompt="Tóm tắt 5 tweet mới nhất giúp mình">Thiếu handle</button>
          <button type="button" data-prompt="Đăng bản tin này lên Telegram giúp mình">Xác nhận gửi</button>
          <button type="button" data-prompt="Tóm tắt bài báo này https://arxiv.org/abs/2604.03501">Tóm tắt paper</button>
          <button type="button" data-prompt="Hãy rút 5 keyword chính từ đoạn này: OpenAI and DeepMind released new AI safety research for Gemini and GPT-4 models.">Rút keyword</button>
        </div>
        <form class="input-row" id="chatForm">
          <textarea id="prompt" placeholder="Nhập yêu cầu research..." autocomplete="off"></textarea>
          <button class="send" id="send" type="submit" title="Gửi">›</button>
        </form>
      </section>
    </main>

    <aside>
      <div class="side-head">
        <p class="side-title">Phiên demo</p>
      </div>
      <div class="meta">
        <div class="metric"><span>Provider</span><strong id="provider">openai</strong></div>
        <div class="metric"><span>Version</span><strong id="version">v3</strong></div>
        <div class="metric"><span>Model</span><strong id="model">Đang tải...</strong></div>
        <div class="metric"><span>Tool rounds</span><strong id="rounds">0</strong></div>
      </div>
    </aside>
  </div>

  <script>
    const state = {
      sessionId: localStorage.getItem("researchAgentSession") || crypto.randomUUID(),
      turns: []
    };
    localStorage.setItem("researchAgentSession", state.sessionId);
    const historyKey = `researchAgentTurns:${state.sessionId}`;

    const messages = document.querySelector("#messages");
    const form = document.querySelector("#chatForm");
    const input = document.querySelector("#prompt");
    const send = document.querySelector("#send");
    const statusText = document.querySelector("#statusText");

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, ch => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
      }[ch]));
    }

    function setStatus(text) {
      statusText.textContent = text;
    }

    function safeJson(value) {
      try {
        return JSON.stringify(value ?? {}, null, 2);
      } catch {
        return String(value ?? "");
      }
    }

    function toolAction(name) {
      const actions = {
        clarify: "Hỏi lại người dùng để lấy thông tin còn thiếu hoặc xác nhận.",
        timeline: "Lấy các bài đăng gần đây của một tài khoản.",
        social_search: "Tìm bài đăng mạng xã hội theo từ khóa.",
        lookup: "Tra cứu web/tin tức theo truy vấn.",
        fetch: "Đọc nội dung từ một URL cụ thể.",
        format: "Định dạng các item đã có thành bản tóm tắt.",
        send: "Gửi nội dung ra kênh ngoài sau khi đã xác nhận.",
        policy: "Tìm trong tài liệu chính sách nội bộ.",
        papers: "Tìm paper trên arXiv.",
        paper_text: "Trích nội dung text từ paper arXiv.",
        extract_keywords: "Rút keyword và cụm entity từ đoạn text đã cung cấp."
      };
      return actions[name] || "Thực thi công cụ đã chọn.";
    }

    function summarizeResult(event) {
      const result = event?.result;
      if (!result) return "Không có result.";
      if (result.error) return `${result.error}: ${result.message || "Tool lỗi."}`;
      if (result.awaiting_user) return `Đang chờ người dùng: ${result.question || ""}`;
      if (Array.isArray(result.items)) return `Trả về ${result.items.length} item.`;
      if (result.text) return String(result.text).slice(0, 220);
      if (result.content) return String(result.content).slice(0, 220);
      return safeJson(result).slice(0, 320);
    }

    function buildToolLog(rounds = []) {
      const totalCalls = rounds.reduce((sum, round) => sum + (round.tool_calls || []).length, 0);
      if (!totalCalls) return "";

      const roundHtml = rounds.map((round, index) => {
        const calls = round.tool_calls || [];
        const results = round.tool_results || [];
        const steps = calls.map((call, callIndex) => {
          const result = results[callIndex];
          return `
            <div class="step">
              <div class="step-title">🔧 ${escapeHtml(call.name)}</div>
              <div class="step-action">${escapeHtml(toolAction(call.name))}</div>
              <pre class="json-block">Arguments\n${escapeHtml(safeJson(call.args))}</pre>
              <pre class="json-block">Result\n${escapeHtml(summarizeResult(result))}</pre>
            </div>
          `;
        }).join("") || `<div class="step-action">Không gọi công cụ ở vòng này.</div>`;
        return `
          <div class="round-card">
            <div class="round-title">▾ Vòng ${escapeHtml(round.round || index + 1)}</div>
            ${steps}
          </div>
        `;
      }).join("");

      return `
        <details class="tool-log">
          <summary>
            <span class="log-icon">▣</span>
            <strong>Log công cụ</strong>
            <span class="log-count">${totalCalls} tool call · ${rounds.length} vòng</span>
          </summary>
          <div class="log-body">${roundHtml}</div>
        </details>
      `;
    }

    function addMessage(role, text, options = {}) {
      const row = document.createElement("div");
      row.className = `message-row ${role}`;
      if (role === "agent") {
        row.innerHTML = `
          <div class="avatar">AI</div>
          <div class="agent-stack">
            ${buildToolLog(options.rounds || [])}
            <div class="bubble ${options.error ? "error" : ""}">${escapeHtml(text)}</div>
          </div>
        `;
      } else {
        row.innerHTML = `<div class="bubble ${options.error ? "error" : ""}">${escapeHtml(text)}</div>`;
      }
      messages.appendChild(row);
      messages.scrollTop = messages.scrollHeight;
      return row;
    }

    function addTyping() {
      const row = addMessage("agent", "");
      const bubble = row.querySelector(".bubble");
      bubble.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
      return row;
    }

    function updateAgentRow(row, data, error = false) {
      const stack = row.querySelector(".agent-stack");
      stack.innerHTML = `
        ${buildToolLog(data.rounds || [])}
        <div class="bubble ${error ? "error" : ""}">${escapeHtml(data.assistant_text || "(Không có nội dung trả lời)")}</div>
      `;
      messages.scrollTop = messages.scrollHeight;
    }

    function saveTurn(turn) {
      state.turns.push(turn);
      localStorage.setItem(historyKey, JSON.stringify(state.turns.slice(-40)));
    }

    function restoreTurns() {
      try {
        state.turns = JSON.parse(localStorage.getItem(historyKey) || "[]");
      } catch {
        state.turns = [];
      }
      for (const turn of state.turns) {
        addMessage("user", turn.user);
        addMessage("agent", turn.assistant_text, { rounds: turn.rounds || [], error: turn.error });
      }
      if (state.turns.length) setStatus(`Đã khôi phục ${state.turns.length} lượt`);
    }

    async function loadStatus() {
      const res = await fetch("/api/status");
      const data = await res.json();
      document.querySelector("#artifact").textContent = data.artifact_version;
      document.querySelector("#provider").textContent = data.provider;
      document.querySelector("#version").textContent = data.version;
      document.querySelector("#model").textContent = data.model || "default";
      setStatus("Sẵn sàng");
      restoreTurns();
      if (!state.turns.length) {
        addMessage("agent", "Xin chào, mình đang chạy bản v3. Gửi một yêu cầu research để demo tool routing và log công cụ.");
      }
    }

    async function sendPrompt(text) {
      addMessage("user", text);
      const row = addTyping();
      send.disabled = true;
      setStatus("Đang suy nghĩ");
      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json; charset=utf-8" },
          body: JSON.stringify({ session_id: state.sessionId, message: text })
        });
        const data = await res.json();
        const isError = !res.ok || data.error;
        updateAgentRow(row, data, isError);
        document.querySelector("#rounds").textContent = String((data.rounds || []).length);
        setStatus(data.status || "Xong");
        saveTurn({
          user: text,
          assistant_text: data.assistant_text || data.error || "",
          rounds: data.rounds || [],
          transcript_path: data.transcript_path,
          error: isError
        });
      } catch (error) {
        const data = { assistant_text: `UI error: ${error.message}`, rounds: [] };
        updateAgentRow(row, data, true);
        saveTurn({ user: text, assistant_text: data.assistant_text, rounds: [], error: true });
        setStatus("Lỗi");
      } finally {
        send.disabled = false;
        input.focus();
      }
    }

    form.addEventListener("submit", event => {
      event.preventDefault();
      const text = input.value.trim();
      if (!text || send.disabled) return;
      input.value = "";
      sendPrompt(text);
    });

    document.querySelectorAll("[data-prompt]").forEach(button => {
      button.addEventListener("click", () => {
        input.value = button.dataset.prompt;
        input.focus();
      });
    });

    input.addEventListener("keydown", event => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    loadStatus().catch(error => {
      setStatus("Lỗi");
      addMessage("agent", `Không tải được trạng thái UI: ${error.message}`, { error: true });
    });
  </script>
</body>
</html>
"""


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "run"


class UISession:
    def __init__(self, session_id: str, app: "UIApp") -> None:
        self.session_id = session_id
        self.app = app
        self.history: list[dict[str, str]] = []
        self.turn_index = 0
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        transcript_id = "_".join([
            safe_slug(app.version),
            safe_slug(app.provider_name),
            "ui",
            safe_slug(session_id[:8]),
            timestamp,
        ])
        self.transcript_path = app.transcripts_dir / f"{transcript_id}.transcript.json"
        self.transcript: dict[str, Any] = {
            "transcript_id": transcript_id,
            **artifact_version_dict(app.artifact_version),
            "provider": app.provider_name,
            "model": app.selected_model,
            "system_prompt": str(app.system_prompt_path),
            "tools": str(app.tools_path),
            "history_window": app.history_window,
            "max_tool_rounds": app.max_tool_rounds,
            "ui": True,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "turns": [],
        }
        write_transcript(self.transcript_path, self.transcript)


class UIApp:
    def __init__(
        self,
        *,
        provider_name: str,
        model: str | None,
        version: str,
        system_prompt_path: Path,
        tools_path: Path,
        transcripts_dir: Path,
        history_window: int,
        max_tool_rounds: int,
    ) -> None:
        self.provider_name = provider_name
        self.version = version
        self.system_prompt_path = system_prompt_path
        self.tools_path = tools_path
        self.transcripts_dir = transcripts_dir
        self.history_window = history_window
        self.max_tool_rounds = max_tool_rounds
        self.provider = make_provider(provider_name)
        self.selected_model = model or getattr(self.provider, "default_model", None)
        self.model = model
        base_prompt = system_prompt_path.read_text(encoding="utf-8")
        self.system_prompt = base_prompt + UI_LANGUAGE_INSTRUCTION
        self.tool_declarations = load_tool_declarations(tools_path)
        self.openai_tools = to_openai_tools(self.tool_declarations)
        self.artifact_version = build_artifact_version(version, system_prompt_path, tools_path)
        self.sessions: dict[str, UISession] = {}
        self.lock = threading.Lock()

    def session(self, session_id: str) -> UISession:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                session = UISession(session_id, self)
                self.sessions[session_id] = session
            return session


class Handler(BaseHTTPRequestHandler):
    app: UIApp

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self) -> None:
        body = HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send_html()
            return
        if self.path == "/api/status":
            self._send_json({
                "provider": self.app.provider_name,
                "version": self.app.version,
                "model": self.app.selected_model,
                "artifact_version": self.app.artifact_version.artifact_version,
                "prompt_hash": self.app.artifact_version.prompt_hash,
                "tools_hash": self.app.artifact_version.tools_hash,
            })
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self._read_json()
            session_id = str(payload.get("session_id") or uuid.uuid4())
            user_text = str(payload.get("message") or "").strip()
            if not user_text:
                self._send_json({"error": "message is required"}, HTTPStatus.BAD_REQUEST)
                return

            session = self.app.session(session_id)
            session.turn_index += 1
            messages = [
                {"role": "system", "content": self.app.system_prompt},
                *trim_history(session.history, self.app.history_window),
                {"role": "user", "content": user_text},
            ]
            turn_record: dict[str, Any] = {
                "turn_index": session.turn_index,
                "started_at": now_iso(),
                "user": user_text,
                "status": "started",
                "assistant_text": None,
                "rounds": [],
                "tool_events": [],
            }

            try:
                result = run_model_tool_loop(
                    provider=self.app.provider,
                    messages=messages,
                    tools=self.app.openai_tools,
                    model=self.app.model,
                    max_tool_rounds=self.app.max_tool_rounds,
                )
                turn_record.update(result)
                assistant_text = str(result.get("assistant_text") or "")
                session.history.append({"role": "user", "content": user_text})
                session.history.append({"role": "assistant", "content": assistant_text})
            except Exception as exc:
                turn_record.update({
                    "status": "provider_error",
                    "assistant_text": "",
                    "error": f"{type(exc).__name__}: {exc}",
                })

            turn_record["ended_at"] = now_iso()
            session.transcript["turns"].append(turn_record)
            write_transcript(session.transcript_path, session.transcript)
            response = {
                **turn_record,
                "transcript_path": str(session.transcript_path),
            }
            status = HTTPStatus.OK if turn_record["status"] != "provider_error" else HTTPStatus.INTERNAL_SERVER_ERROR
            self._send_json(response, status)
        except Exception as exc:
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Browser UI for the v3 research agent.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "gemini"], default="openai")
    parser.add_argument("--model", default=None)
    parser.add_argument("--version", default="v3")
    parser.add_argument("--system-prompt", type=Path, default=ARTIFACTS_DIR / "system_prompt.md")
    parser.add_argument("--tools", type=Path, default=ARTIFACTS_DIR / "tools.yaml")
    parser.add_argument("--transcripts-dir", type=Path, default=TRANSCRIPTS_DIR)
    parser.add_argument("--history-window", type=int, default=5)
    parser.add_argument("--max-tool-rounds", type=int, default=4)
    args = parser.parse_args()

    load_lab_env(ROOT)
    app = UIApp(
        provider_name=args.provider,
        model=args.model,
        version=args.version,
        system_prompt_path=args.system_prompt,
        tools_path=args.tools,
        transcripts_dir=args.transcripts_dir,
        history_window=args.history_window,
        max_tool_rounds=args.max_tool_rounds,
    )
    Handler.app = app
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Research Agent UI running at http://{args.host}:{args.port}")
    print(f"artifact_version={app.artifact_version.artifact_version}")
    server.serve_forever()


if __name__ == "__main__":
    main()
