from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
from huggingface_hub import login
import os
import re

# Login to Hugging Face (consider storing the token in an env variable)

model_path = "./flan-lora-splunk"
device = torch.device("cpu")

# Load model and tokenizer
model = AutoModelForSeq2SeqLM.from_pretrained(model_path).to(device)
tokenizer = AutoTokenizer.from_pretrained(model_path)

# Your Splunk log schema
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


def generate_spl_query(user_prompt: str) -> str:
    prompt = build_spl_prompt(user_prompt)
    inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(
            inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_length=256,
            do_sample=False,
            no_repeat_ngram_size=2,
            pad_token_id=tokenizer.eos_token_id
        )

    return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()


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

        # Extract key=value pairs
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

    spl_query = generate_spl_query(user_prompt)
    print("\nGenerated SPL Query:\n", spl_query)

    parsed_filters = extract_field_value_filters(spl_query, column_list)
    print("\nStructured Field Filters:\n", parsed_filters)
