# Knowledge base

Markdown files in this folder are chunked, embedded and stored in ChromaDB (`make ingest`). The agent's
`search_dmrc_info` tool retrieves from them, so the chatbot can only answer DMRC policy questions
using what is written here.

- Write plain facts, one topic per `##` heading (the splitter breaks on headings first).
- Keep a **Sources** line and a **Last checked** date in every file, and re-check before relying on it.
  DMRC fares, rules and timings change.
- This `README.md` is skipped by the ingest script.
- After editing any file, run `make ingest` again.
