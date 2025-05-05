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
