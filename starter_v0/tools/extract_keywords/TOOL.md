---
name: extract_keywords
track: bonus
kind: local_formatter
provider:
requires_env: []
inputs: [text, max_keywords, include_entities]
outputs: [keywords, entities]
side_effect: false
requires_confirmation: false
---

# extract_keywords

Extracts lightweight keywords and named-entity-like phrases from user-provided text.

Use this only when the user explicitly asks to extract keywords/entities, build search terms,
or prepare a research query from an existing passage. Do not use it for ordinary web search,
social search, paper search, URL reading, or formatting.
