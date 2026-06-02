# Day 04 Lab v2 Report - Research Agent

## Team

- Team: Day04 Research Agent Team
- Members: Vũ Xuân Bách - 2A202600776, Dương Quang Khải - 2A202600708, Nguyễn Hồng Phúc - 2A202600843
- Provider/model: OpenAI / gpt-4o-mini

## Final Metrics

- Final version: v3_toolcheck (v3 prompt + required new tool)
- Final artifact_version: v3_toolcheck+p007cc9b9408a+t39bacf3f6c21
- Best base run file: runs/v3_toolcheck_B_base_openai_20260602T155725712307.json
- Base case accuracy: 1.00
- Base tool routing accuracy: 1.00
- Base argument accuracy: 1.00
- Group eval run file: runs/v3_B_group_openai_20260602T143340265892.json
- Group eval accuracy: 0.90
- Chat transcript file: transcripts/v3_openai_20260602T144925623598.transcript.json

## Version Evidence

Filled from `artifacts/version_log.csv` and `runs/*.json`.

| Version | Changed Artifact | Hypothesis | Metric Before | Metric After | Run File |
|---|---|---|---:|---:|---|
| v0 | baseline | Baseline measures the initial routing/boundary behavior before changes. | N/A | case=0.70; routing=0.75; args=0.70; multiturn=1.00 | runs/v0_B_base_openai_20260602T125759908390.json |
| v1 | artifacts/system_prompt.md | If the prompt forbids guessing and requires clarify/no-tool/send-confirmation boundaries, missing_info/out_of_scope/wrong_boundary failures should improve. | case=0.70; routing=0.75; args=0.70; multiturn=1.00 | case=0.95; routing=0.95; args=0.95; multiturn=0.8333 | runs/v1_B_base_openai_20260602T135152073923.json |
| v2 | artifacts/system_prompt.md | If latest user instruction overrides earlier source choices, M06 should stop calling social_search after switching to web. | case=0.95; routing=0.95; args=0.95; multiturn=0.8333 | case=0.95; routing=1.00; args=0.95; multiturn=1.00 | runs/v2_B_base_openai_20260602T141024271610.json |
| v3 | artifacts/system_prompt.md | If send/post/publish confirmation is forced to yes_no before gathering content, R12 should stop using response_type=text. | case=0.95; routing=1.00; args=0.95; multiturn=1.00 | case=1.00; routing=1.00; args=1.00; multiturn=1.00 | runs/v3_B_base_openai_20260602T144518599527.json |
| v3_toolcheck | tools/extract_keywords + tools/__init__.py + artifacts/tools.yaml | If the new keyword extraction tool is narrowly described, it should satisfy the new-tool requirement without hurting base routing. | case=1.00; routing=1.00; args=1.00; multiturn=1.00 | case=1.00; routing=1.00; args=1.00; multiturn=1.00 | runs/v3_toolcheck_B_base_openai_20260602T155725712307.json |

## Failure Analysis

Actual failures were read from `results[*].result.failures`.

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R08_out_of_scope | out_of_scope | send | Agent called a tool for a math question where no research tool was needed. | v1 added no-tool boundary for non-research tasks. |
| R10_missing_handle | missing_info | timeline(screenname=sama) | Agent guessed a Twitter/X account instead of asking for the handle. | v1 required `clarify` when handle/account is missing. |
| R11_missing_url | missing_info | fetch(url=example.com/article) | Agent invented a URL for "this article". | v1 required `clarify` when URL/article link is missing. |
| R12_confirm_before_send | wrong_boundary | send, then clarify(text) in v2 | Agent sent or asked for content before yes/no confirmation. | v3 made send/post/publish confirmation a yes_no boundary before content gathering. |
| R13_parallel_web_and_tweets | wrong_tool / wrong_arg_value | lookup + social_search | lookup was missing `topic="news"` for "tin AI hom nay". | v1 added news/timeframe routing rules. |
| M06_switch_tool | wrong_tool | lookup + social_search | Agent kept calling social_search after user said to switch from Twitter to web. | v2 added latest-turn override rule for multi-turn source switches. |
| G08_multiturn_still_missing_handle | missing_info | timeline(screenname=newest_tweets_account) | Group eval still exposed a hard missing-handle case where the model guessed a fake handle. | Next improvement: strengthen multi-turn missing-info rule and add this case to future base-style regression checks. |

## Team Eval Cases

`data/eval_group.json` contains 10 cases: 5 single-turn and 5 multi-turn.

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| G01_papers_routing | Scientific paper request should route to arXiv paper search, not generic web lookup. | papers | PASS |
| G02_policy_routing | Internal company policy question should search local policy KB. | policy | PASS |
| G03_timeframe_month | "thang nay" should map to `timeframe=month` and `topic=news`. | lookup(topic=news, timeframe=month) | PASS |
| G04_out_of_scope_translation | Translation request is outside research-agent scope. | no_tool | PASS |
| G05_send_confirmed | User explicitly confirmed content + send action. | send(confirmed=true) | PASS |
| G06_paper_then_paper_text | Multi-turn arXiv link then request full paper text. | paper_text(arxiv_url) | PASS |
| G07_multiturn_search_type_correction | Carry query=Anthropic and correct Latest to Top. | social_search(search_type=Top) | PASS |
| G08_multiturn_still_missing_handle | Even after several turns, missing screenname should still ask user, not guess. | clarify(response_type=text) | FAIL |
| G09_multiturn_followup_meta | Latest turn asks a meta capability question; do not call research tool again. | answer_without_tool | PASS |
| G10_multiturn_confirm_then_send | After final explicit confirmation, send without clarifying again. | send(confirmed=true) | PASS |

## Live Chat Evidence

Use `transcripts/*.transcript.json`.

| Turn | User Request | Tool Calls | Version Evidence | Outcome |
|---|---|---|---|---|
| 1 | Tin tuc AI noi bat hom nay la gi? | lookup | v3+p007cc9b9408a+t6cdb53d5d7b8 | Correctly selected web/news lookup; live tool returned a technical issue, which was surfaced to the user. |
| 2 | Tom tat may tweet moi nhat giup minh | none | v3+p007cc9b9408a+t6cdb53d5d7b8 | Correctly asked for a Twitter/X handle instead of guessing. |
| 3 | Cua Sam Altman nhe | timeline | v3+p007cc9b9408a+t6cdb53d5d7b8 | Correctly used timeline after the missing handle was provided; live API returned a technical issue. |
| 4 | Dang ban tin AI hom nay len Telegram giup minh | none | v3+p007cc9b9408a+t6cdb53d5d7b8 | Correctly asked for confirmation before delivery action. |
| 5 | U minh xac nhan, dang luon di nhe | clarify | v3+p007cc9b9408a+t6cdb53d5d7b8 | Guardrail held: agent still asked for concrete content before sending because content was not available in context. |

Additional UI transcript evidence:

| Turn | User Request | Tool Calls | Version Evidence | Outcome |
|---|---|---|---|---|
| 1 | Tim tren web tin AI hom nay va tim them tweet ve AI. | lookup, social_search | v3+p007cc9b9408a+t39bacf3f6c21 | UI called both web/news and social tools, displayed expandable tool logs, and answered in Vietnamese. |
| 2 | tom tat bai bao https://arxiv.org/pdf/2403.17881 | fetch | v3+p007cc9b9408a+t39bacf3f6c21 | UI displayed fetch tool log and surfaced a live timeout gracefully. |
| 1 | Hay rut 5 keyword chinh... | extract_keywords | v3+p007cc9b9408a+t39bacf3f6c21 | New tool was selected for explicit keyword extraction and returned Vietnamese output. |

## Bonus Evidence

| Bonus | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| send (Telegram) | runs/v3_B_base_openai_20260602T144518599527.json; transcripts/v3_openai_20260602T144925623598.transcript.json | v3 passes R12 confirm-before-send and G10 confirmed-send behavior. | Delivery actions require yes_no confirmation and `confirmed=true`; content is not sent when missing. |
| arXiv/company policy | runs/v3_B_group_openai_20260602T143340265892.json | G01 routed paper requests to `papers`; G02 routed policy requests to `policy`; G06 routed arXiv text extraction to `paper_text`. | Tool descriptions separate paper/policy sources from generic lookup. |
| UI | ui_server.py; transcripts/v3_openai_ui_5e98972d_20260602T160229175582.transcript.json | Browser UI runs version v3, answers in Vietnamese, shows expandable per-turn tool logs, and preserves chat history in localStorage plus transcript JSON. | UI does not bypass backend guardrails; it calls the same registered tools and transcript writer. |
| new tool | tools/extract_keywords/TOOL.md; tools/extract_keywords/tool.py; runs/v3_toolcheck_B_base_openai_20260602T155725712307.json | Added required `extract_keywords` tool and kept base eval at 20/20. | Tool declaration is narrow: only use when user explicitly asks for keyword/entity extraction. |

## Reflection

- Which fixes belonged in `system_prompt.md`?
  - Missing-information boundaries, no-tool out-of-scope behavior, send/post/publish confirmation, news/timeframe conventions, and multi-turn latest-instruction override belonged in the system prompt because they are global routing policies.

- Which fixes belonged in `tools.yaml`?
  - Tool-specific descriptions and argument schemas belonged in `tools.yaml`, especially the new `extract_keywords` declaration. This keeps the model aware of the available tool without changing eval cases or implementation code.

- Which failure needed manual review instead of automatic grading?
  - Live tool/provider failures needed manual review. In live chat, `lookup` and `timeline` were selected correctly, but external API/tool execution returned technical issues. The eval score should separate routing correctness from live API availability.
  - G08 also needs manual review because it is a deliberately hard multi-turn missing-info case that catches fake-handle guessing.

- What would you improve next?
  - Strengthen the missing-handle rule for multi-turn contexts and add G08-style regressions to future base checks.
  - Add a small UI control for clearing local chat history and exporting the current transcript.
  - Add one or two more group cases specifically for the new `extract_keywords` tool so the new tool has its own measured coverage.
