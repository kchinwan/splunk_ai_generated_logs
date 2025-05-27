import streamlit as st
from llm_query_generator import generate_spl_query_from_api, extract_field_value_filters
from filtered_df import summarize  # Ensure you're importing the correct summarize function

st.set_page_config(page_title="Splunk Query Assistant", layout="wide")

st.title("🧠 Splunk Query Assistant")
st.markdown("Enter a natural language query to generate a Splunk SPL query and extract relevant fields.")

column_list = [
    'eventDatetime', 'eventType', 'failureType', 'index', 'step', 'comments', 'uniqueId', 'interfaceId',
    'correlationId', 'source', 'target', 'originalClientId', 'originalClientName', 'businessObject',
    'appName', 'environment', 'sourceBusinessServiceId', 'targetBusinessServiceId', 'businessIntegrationNumber',
    'businessUnit', 'Resource', 'Source', 'Target', 'WorkOrderNumber', 'IdType', 'InterfaceId', 'BiNumber',
    'BusinessObject', 'validationErrors', 'XX_SO_HEADER_ID', 'XX_SO_ORDER_KEY', 'XX_WO_ID', 'DebriefNumbers',
    'SalesOrderNumbers', 'XX_SO_ORDER_NUMBER', 'XX_SO_LINE_NUMBER', 'ValidationErrors',
    'ReleasePauseValidationErrors', 'error_0_description', 'error_0_type', 'error_0_cause',
    'error_0_detailedDescription', 'XX_DEBRIEF_NUMBER', 'XX_SO_FULFILL_LINE_ID', 'OrderKey',
    'SalesOrderValidationErrors', 'XX_WO_OPERATION_ID', 'XX_WO_OPERATION_MATERIAL_ID', 'XX_WO_OPERATION_RESOURCE_ID',
    'customerAccountId', 'Party Site Id', 'ArNbr Number  ', 'Site', 'CustomerAccountId', 'AccountNumber', 'table',
    'startTime', 'recordsFetched', 'processingTime', 'companyCode', 'recordsUpdated', 'Id', 'NumberOfId',
    'FilePattern', 'MatchFound', 'FileStatus', 'FileNamePattern', 'TotalNoOfRecords', 'failures', 'openOrders',
    'success', 'idtype', 'ID', 'flagStatus', 'OrderNumber', 'CPQ_Integration_Status__c',
    'CPQ_Oracle_Integration__c', 'Type', 'AssemblyPartNumber', 'PartNumber', 'Quantity', 'billSequenceId', 'Number',
    'Version', 'ReportPath', 'LastUpdateTo', 'LastUpdateDate', 'schedulerName', 'p_start_date', 'p_end_date',
    'reportAbsolutePath', 'LastUpdatedate', 'query', 'id', 'ScheduleId', 'ItemNumber', 'PartType'
]

# User input
user_prompt = st.text_area("🔍 Your Query", height=100, placeholder="E.g., Show all error logs in QA with data issues but exclude 'end-of-input'")

if st.button("Generate"):
    if user_prompt.strip():
        with st.spinner("Generating SPL query..."):
            spl_query = generate_spl_query_from_api(user_prompt)
            fields = extract_field_value_filters(spl_query, column_list)

        st.subheader("✅ Generated SPL Query")
        st.code(spl_query, language="bash")

        # Call the summarize function from filtered_df.py to generate the log summary
        st.subheader("📋 Log Summary")

        # Placeholder for streaming output
        summary_placeholder = st.empty()
        cumulative_summary = ""  # This will store the entire summary content

        # Show the spinner while summarizing
        with st.spinner("Summarizing logs... This may take a moment"):
            # Use the summarize generator to stream output incrementally
            for line in summarize():  # summarize() now uses yield for streaming
                cumulative_summary += line + "\n"  # Append new content to the cumulative summary
                summary_placeholder.text(cumulative_summary)  # Update the placeholder with the full content

    else:
        st.warning("Please enter a query.")
