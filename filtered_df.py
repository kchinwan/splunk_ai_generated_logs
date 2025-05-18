import google.generativeai as genai
import urllib3
import re

# === Gemini API Setup ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#incldue key here
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="models/gemini-2.0-flash-lite")

# === Known Log Schema Fields ===
column_list = [
    "eventDatetime", "eventType", "failureType", "index", "step", "comments", "uniqueId", "interfaceId",
    "correlationId", "source", "target", "originalClientId", "originalClientName", "businessObject", "appName",
    "environment", "sourceBusinessServiceId", "targetBusinessServiceId", "businessIntegrationNumber", "businessUnit",
    "Resource", "WorkOrderNumber", "IdType", "ValidationErrors", "error_0_description", "error_0_type",
    "error_0_cause", "OrderNumber", "FilePattern", "CPQ_Oracle_Integration__c", "Type", "AssemblyPartNumber",
    "PartNumber", "Quantity", "billSequenceId", "ReportPath", "LastUpdateTo", "LastUpdateDate", "schedulerName",
    "p_start_date", "p_end_date", "ScheduleId", "ItemNumber", "PartType"
]

# === Prompt for New Query ===
def build_spl_prompt(user_prompt: str) -> str:
    examples = """
Examples:
Input: Order 807563904 did not reach OTM from SAP, can you check for any failures?
Output: index="ei_prod_mule_apps" "0807563904" "metadata.source"="Oracle TMS" "metadata.target"=SAP

Input: Can you please check how this idoc made through mulesoft layer. Ideally if this value is missing it will never made to WMS  system. 0000000116455369 0000000116459644
Output: index="ei_prod_mule_apps" "0000000116455369" "0000000116459644" "metadata.target"=WMSBTS

Input: Lot many vouchers that are triggered from OTM did not reach TRAX system even though triggered them multiple times. Could you please help us investigate for below vouchers?
Output: index="ei_prod_mule_apps" "20240923-0059" OR "20240923-0064" "metadata.source"="Oracle TMS" "metadata.target"="IntelligentAudit, Trax"
"""

    return f"""
You are a Splunk assistant. Convert the following natural language request into a valid, efficient SPL query.

Here are instructions to follow:
- Always use index="ei_prod_mule_apps" unless the user mentions another index.
- Extract key entities such as IDs, order numbers, voucher numbers, system names, and use them in double quotes.
- If the user implies a direction like SAP → OTM, map to "metadata.source"="SAP" and "metadata.target"="OTM".
- Support OR filters when multiple IDs or values are provided.
- Only use fields from this schema when necessary: {', '.join(column_list)}

{examples}

Now convert the following request:
Request: {user_prompt}
SPL Query:
""".strip()


# === Prompt for Refinement ===
def build_refinement_prompt(user_input: str, chat_history: list, current_spl: str) -> str:
    history = "\n".join([f"User: {u}\nAgent: {a}" for u, a in chat_history[-3:]])

    return f"""
You are a Splunk assistant helping refine a previous SPL query.

Always include:
- index (default to index="ei_prod_mule_apps" unless changed)
- field filters based on user instructions
- quoted IDs or values where relevant
- logical operators (AND, OR) where needed

Known schema fields: {', '.join(column_list)}

Previous SPL:
{current_spl or "None"}

Conversation History:
{history}

New instruction from user:
{user_input}

Refined SPL Query:
""".strip()

def clean_spl_query(spl: str) -> str:
    # 1. Remove quotes around field names: "OrderNumber"= => OrderNumber=
    spl = re.sub(r'"(\w+)"\s*=', r'\1=', spl)

    # 2. Remove quotes around ID-like values (numbers or alphanumeric strings without spaces)
    # Capture pattern: FieldName="value" or FieldName='value'
    # Remove quotes only if value is alphanumeric or digits only (no spaces, no special chars)
    def unquote_id_value(match):
        field = match.group(1)
        val = match.group(2)
        # Check if val is purely alphanumeric or digits (adjust if you want to allow some symbols)
        if re.fullmatch(r'[A-Za-z0-9]+', val):
            # For purely digits, strip leading zeros but keep '0' if all zeros
            if val.isdigit():
                val = val.lstrip('0') or '0'
            return f'{field}={val}'
        else:
            # Keep quotes for complex values (with spaces or special chars)
            return match.group(0)

    spl = re.sub(r'(\w+)=["\']([^"\']+)["\']', unquote_id_value, spl)

    return spl

# === Gemini Wrapper ===
def generate_spl_query_from_api(prompt: str) -> str:
    try:
        full_prompt = f"{prompt}\n\nNote: Schema fields to consider include:\n{', '.join(column_list)}"
        response = model.generate_content(full_prompt)
        clean_result = clean_spl_query(response.text.strip())
        return clean_result
    except Exception as e:
        return f"Error: {e}"

# === Optional Standalone Test ===
if __name__ == "__main__":
    user_input = "Get all error logs from QA that failed due to data issues but exclude end-of-input"
    full_prompt = build_spl_prompt(user_input)
    spl_query = generate_spl_query_from_api(full_prompt)
    print("\nSPL Query:\n", spl_query)
