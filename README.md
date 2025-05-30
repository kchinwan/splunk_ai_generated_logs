#  Splunk GenAI Assistant - PoC

A Generative AI Assistant that transforms natural language questions into optimized SPL (Search Processing Language) queries, executes them (simulated using a Splunk log Excel dump), analyzes logs, and generates human-readable summaries — all in a simple Streamlit UI.

---

## Project Goals

✅ Convert user queries (in plain English) into accurate SPL queries  
✅ Simulate query execution on a local Excel log dump  
✅ Analyze filtered logs to detect patterns, errors, spikes  
✅ Summarize insights in natural language (optionally with charts)

---

## Architecture Overview

```text
         ┌────────────────────────┐
         │   Streamlit Frontend   │  <- Natural language query input
         └──────────┬─────────────┘
                    │
                    ▼
         ┌────────────────────────┐
         │  LLM (Free API/Model)  │  <- Translates to SPL
         └──────────┬─────────────┘
                    │
                    ▼
         ┌────────────────────────┐
         │  Log Dump (Excel/CSV)  │  <- Simulates Splunk output
         └──────────┬─────────────┘
                    │
                    ▼
         ┌────────────────────────┐
         │ Log Analysis + Summary │  <- Insights via LLM or rules
         └──────────┬─────────────┘
                    │
                    ▼
         ┌────────────────────────┐
         │ Streamlit Response Box │  <- Summarized results + SPL + visuals
         └────────────────────────┘




splunk_ai_assistant/
├── main.py                          # Entry point (Streamlit UI or CLI)
├── core/
│   ├── prompt_engine.py            # Builds prompts for Gemini (initial + refinement)
│   ├── spl_generator.py            # Calls Gemini + parses response
│   ├── entity_extraction.py        # Extracts IDs, system names, fields from NL input
│   ├── spl_composer.py             # Modular SPL builder (combines index + filters)
│   ├── memory.py                   # Stores chat history, handles follow-ups
├── config/
│   ├── schema_fields.py            # List of known schema fields
│   ├── examples.py                 # Prompt examples (pre-defined SPL + NL)
├── utils/
│   ├── cleaner.py                  # Cleans/normalizes generated SPL
│   ├── helpers.py                  # Misc utility functions
├── assets/
│   └── icon.png                    # (optional) logo for UI
├── requirements.txt                # All dependencies
└── README.md
