import torch
import re
import requests
from transformers import AutoTokenizer

# Hugging Face API setup
API_TOKEN = "your_hugging_face_token"  # Use your Hugging Face token
MODEL_NAME = "bigcode/starcoder2-7b"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"

# Load the tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# Define known log schema fields
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
    'customerAccountId', 'Party Site Id', 'ArNbr Number', 'Site', 'CustomerAccountId', 'AccountNumber', 'table',
    'startTime', 'recordsFetched', 'processingTime', 'companyCode', 'recordsUpdated', 'Id', 'NumberOfId',
    'FilePattern', 'MatchFound', 'FileStatus', 'FileNamePattern', 'TotalNoOfRecords', 'failures', 'openOrders',
    'success', 'idtype', 'ID', 'flagStatus', 'OrderNumber', 'CPQ_Integration_Status__c',
    'CPQ_Oracle_Integration__c', 'Type', 'AssemblyPartNumber', 'PartNumber', 'Quantity', 'billSequenceId', 'Number',
    'Version', 'ReportPath', 'LastUpdateTo', 'LastUpdateDate', 'schedulerName', 'p_start_date', 'p_end_date',
    'reportAbsolutePath', 'LastUpdatedate', 'query', 'id', 'ScheduleId', 'ItemNumber', 'PartType'
]

# Define the prompt creation for SPL generation
def build_spl_prompt(user_prompt: str) -> str:
    return f"""
You are a Splunk chatbot agent helping users convert natural language questions into efficient SPL queries.

Examples:
Input: Show all failed SSH login attempts in the last 6 hours.
Output: index=auth sourcetype=sshd action=failure earliest=-6h

Input: Count 404 errors from the web server in the past day.
Output: index=web sourcetype=access status=404 earliest=-24h | stats count

Input: Get all error logs from QA that failed due to data issues but exclude end-of-input
Output: index="ei_qa_mule_apps" | spath eventType | search eventType=ERROR failureType=DATA NOT "end-of-input at root"

Input: {user_prompt}
Output:
"""

# Call Hugging Face API to generate SPL query from the model
def generate_spl_query_from_api(user_prompt: str) -> str:
    prompt = build_spl_prompt(user_prompt)
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }

    # Sending the request to Hugging Face API for inference
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
    
    if response.status_code == 200:
        output = response.json()[0]['generated_text']
        return output.strip()
    else:
        print("Error with model request:", response.status_code, response.text)
        return None

# Extract field-value filters and exclusions from the generated SPL query
def extract_field_value_filters(spl_query: str, known_fields: list) -> dict:
    filters = {}
    excludes = []

    # Extract index
    index_match = re.search(r'index\s*=\s*"?(.*?)"?(?=\s|\|)', spl_query)
    if index_match:
        filters['index'] = index_match.group(1)

    # Extract everything after `search` if it exists
    search_match = re.search(r'\|\s*search\s+(.*)', spl_query)
    if search_match:
        search_clause = search_match.group(1)

        # Extract NOT conditions
        excludes = re.findall(r'NOT\s+"([^"]+)"', search_clause)

        # Remove NOTs to simplify parsing of key-value pairs
        search_clause = re.sub(r'NOT\s+"[^"]+"', '', search_clause)

        # Extract key-value pairs
        key_value_pairs = re.findall(r'(\w+)\s*=\s*"?(.*?)"?(?=\s|$)', search_clause)
        for key, value in key_value_pairs:
            if key in known_fields:
                filters[key] = value

    return {
        "filters": filters,
        "excludes": excludes,
        "raw_spl": spl_query
    }

# === Example usage ===
if __name__ == "__main__":
    user_prompt = "Get all error logs from QA that failed due to data issues but exclude end-of-input"
    print(f"User Prompt: {user_prompt}")

    # Call the Hugging Face API to generate SPL query
    spl_query = generate_spl_query_from_api(user_prompt)
    print("\nGenerated SPL Query:\n", spl_query)

    # Extract the filters and exclusions
    if spl_query:
        parsed_filters = extract_field_value_filters(spl_query, column_list)
        print("\nStructured Field Filters:\n", parsed_filters)
