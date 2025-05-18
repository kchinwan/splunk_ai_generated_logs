import streamlit as st
from datetime import datetime
from typing import Optional
from llm_query_generator import (
    build_spl_prompt,
    build_refinement_prompt,
    generate_spl_query_from_api
)

# === Streamlit Config ===
st.set_page_config(page_title="Splunk Query Assistant", layout="wide")
st.title("🧠 Splunk Query Assistant")

# === Examples for user guidance ===
with st.expander("📘 Examples (click to expand)"):
    st.markdown("""
**Input:** Order 807563904 did not reach OTM from SAP, can you check for any failures?  
**Output:** `index="ei_prod_mule_apps" "0807563904" "metadata.source"="Oracle TMS" "metadata.target"=SAP`  

**Input:** Can you please check how this IDoc made through Mulesoft layer? Ideally, if this value is missing it will never make it to WMS. 0000000116455369 0000000116459644  
**Output:** `index="ei_prod_mule_apps" "0000000116455369" "metadata.target"=WMSBTS`  

**Input:** A lot of vouchers that are triggered from OTM did not reach TRAX system even though we triggered them multiple times.  
**Output:** `index="ei_prod_mule_apps" "20240923-0059" OR "20240923-0064" "metadata.source"="Oracle TMS" "metadata.target"="IntelligentAudit, Trax"`  
""")

# === Session State Initialization ===
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_spl" not in st.session_state:
    st.session_state.current_spl = ""
if "is_spl_confirmed" not in st.session_state:
    st.session_state.is_spl_confirmed = False
if "show_refinement" not in st.session_state:
    st.session_state.show_refinement = False

# === Timestamp Inputs (optional) ===
start_time = st.sidebar.date_input("Start Date (optional)", value=None)
start_time_time = st.sidebar.time_input("Start Time (optional)", value=None)
end_time = st.sidebar.date_input("End Date (optional)", value=None)
end_time_time = st.sidebar.time_input("End Time (optional)", value=None)

def combine_date_time(date_obj, time_obj) -> Optional[datetime]:
    if date_obj is None:
        return None
    if time_obj is None:
        # default to midnight if no time given
        time_obj = datetime.min.time()
    return datetime.combine(date_obj, time_obj)

start_datetime = combine_date_time(start_time, start_time_time)
end_datetime = combine_date_time(end_time, end_time_time)

# === Function to append time filter to SPL ===
def append_time_filter(spl: str, start: Optional[datetime], end: Optional[datetime]) -> str:
    conditions = []
    if start:
        conditions.append(f'eventDatetime>="{start.strftime("%Y-%m-%d %H:%M:%S")}"')
    if end:
        conditions.append(f'eventDatetime<="{end.strftime("%Y-%m-%d %H:%M:%S")}"')
    if not conditions:
        return spl
    time_filter = " AND ".join(conditions)
    # Add time filter with AND if spl already has content
    if spl.strip():
        return f"{spl} AND {time_filter}"
    else:
        return time_filter

# === Initial Query Input ===
if not st.session_state.current_spl:
    user_prompt = st.text_input("🔍 Enter your query:", placeholder="E.g., Get all error logs from QA excluding 'end-of-input'")
    if st.button("Generate"):
        if user_prompt.strip():
            with st.spinner("Generating SPL query..."):
                full_prompt = build_spl_prompt(user_prompt)
                spl_query = generate_spl_query_from_api(full_prompt)
                # Append time filters if selected
                spl_query = append_time_filter(spl_query, start_datetime, end_datetime)

            st.session_state.current_spl = spl_query
            st.session_state.chat_history.append((user_prompt, spl_query))
        else:
            st.warning("Please enter a query.")

# === Display SPL Query + Ask for Confirmation ===
if st.session_state.current_spl and not st.session_state.is_spl_confirmed:
    st.subheader("✅ Generated SPL Query")
    st.code(st.session_state.current_spl, language="spl")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👍 Yes, Finalised Query"):
            st.session_state.is_spl_confirmed = True
            st.success("SPL query confirmed.")
    with col2:
        if st.button("👎 No, I want to modify it"):
            st.session_state.show_refinement = True

# === Refinement Input ===
if st.session_state.show_refinement:
    refinement_input = st.text_input("🔧 Enter what you'd like to change or add:", placeholder="e.g., Add environment=QA and exclude error='timeout'")
    if st.button("Refine Query"):
        if refinement_input.strip():
            with st.spinner("Refining SPL query..."):
                refinement_prompt = build_refinement_prompt(
                    user_input=refinement_input,
                    chat_history=st.session_state.chat_history,
                    current_spl=st.session_state.current_spl
                )
                refined_query = generate_spl_query_from_api(refinement_prompt)
                # Append time filters again if needed
                refined_query = append_time_filter(refined_query, start_datetime, end_datetime)

            st.session_state.current_spl = refined_query
            st.session_state.chat_history.append((refinement_input, refined_query))
            st.session_state.show_refinement = False
        else:
            st.warning("Please describe the change you'd like to make.")

# === Reset Option ===
if st.button("Reset"):
    st.session_state.chat_history = []
    st.session_state.current_spl = ""
    st.session_state.is_spl_confirmed = False
    st.session_state.show_refinement = False
    st.experimental_rerun()
