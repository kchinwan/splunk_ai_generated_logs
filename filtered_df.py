import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# === Step 0: Setup ===
filters = {
    'index': 'ei_dev_mule_apps',
    'eventType': 'ERROR',
    'environment': 'dev-us',
    'uid': '1234'
}
excludes = []
error_fields = ['comments', 'failures', 'ValidationErrors', 'error_0_description']  # Added list of error fields

# Load model
model_path = "google/flan-t5-base"  # Change to your actual model path
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSeq2SeqLM.from_pretrained(model_path).to(device)

# === Step 1: Load and filter logs ===
df_logs = pd.read_csv("flatlogs.csv")
column_list = [
    'eventDatetime', 'eventType', 'failureType', 'index', 'comments', 'uniqueId', 'interfaceId',
    'correlationId', 'source', 'target', 'originalClientId', 'originalClientName',
    'appName', 'environment', 'ValidationErrors', 'failures',
    'error_0_description', 'error_0_type', 'error_0_cause', 'error_0_detailedDescription'
]
df_logs = df_logs[column_list]


def apply_filters_to_df(df: pd.DataFrame, filters: dict, excludes: list) -> pd.DataFrame:
    filtered_df = df.copy()
    ignored_filters = {}
    applied_filters = {}

    for key, value in filters.items():
        if key not in filtered_df.columns:
            ignored_filters[key] = f"Column '{key}' not in DataFrame"
            continue

        mask = filtered_df[key].astype(str).str.lower() == str(value).lower()
        if mask.sum() == 0:
            ignored_filters[key] = f"No match for '{value}' in column '{key}'"
            continue

        filtered_df = filtered_df[mask]
        applied_filters[key] = value

    for exclusion in excludes:
        exclusion = exclusion.lower()
        mask = filtered_df.apply(lambda row: exclusion not in str(row).lower(), axis=1)
        filtered_df = filtered_df[mask]

    print(f"\n✅ Applied Filters: {applied_filters}")
    print(f"⚠️ Ignored Filters: {ignored_filters}")
    print(f"📦 Rows after filtering: {filtered_df.shape[0]}")
    return filtered_df


# === Step 2: Chunking ===
def chunk_dataframe(df: pd.DataFrame, chunk_size: int = 25):
    for i in range(0, len(df), chunk_size):
        yield df.iloc[i:i + chunk_size]


# === Step 3: Convert logs to prompt text ===
def dataframe_to_prompt(chunk_df: pd.DataFrame, error_fields: list) -> str:
    logs_text = ""
    for idx, row in chunk_df.iterrows():
        # Extract and combine error information
        error_info = "N/A"
        for field in error_fields:
            if row.get(field):
                error_info = str(row.get(field))
                break  # Use the first available error description
        if len(error_info) > 150:
            error_info = error_info[:150] + "..."

        logs_text += (
            f"{idx + 1}. [{row.get('eventDatetime', 'N/A')}] "
            f"EventType: {row.get('eventType', 'N/A')}, "
            f"FailureType: {row.get('failureType', 'N/A')}, "
            f"Env: {row.get('environment', 'N/A')}, "
            f"App: {row.get('appName', 'N/A')}, "
            f"Interface: {row.get('interfaceId', 'N/A')}, "
            f"UID: {row.get('uniqueId', 'N/A')}, "
            f"Error: {error_info}\n"
        )

    prompt = f"""
You are a support analyst reviewing logs from failed transactions.
Analyze the following log entries and provide a summary of the problems,
recurring issues, and potential root causes. Focus on the errors described
and how they are related to the application, interface, and environment.
Provide a concise summary, limited to 2-3 sentences.

Logs:
{logs_text}

Summary of problems and potential root causes:
""".strip()
    return prompt


# === Step 4: Summarize a chunk of logs ===
def summarize_chunk(chunk_df: pd.DataFrame, error_fields: list) -> str:
    prompt = dataframe_to_prompt(chunk_df, error_fields)
    inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=1024)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(
            inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_length=256,
            num_beams=4,
            pad_token_id=tokenizer.eos_token_id,
        )

    return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()


# === Step 5: Combine chunk summaries ===
def summarize_all_chunks(df: pd.DataFrame, chunk_size: int, error_fields: list) -> str:
    summaries = []
    for chunk in chunk_dataframe(df, chunk_size):
        summary = summarize_chunk(chunk, error_fields)
        if summary and len(summary.split()) > 5:
            summaries.append(summary)

    if not summaries:
        return "No meaningful summaries were generated from the log chunks."

    combined_summary_prompt = (
        "You are a senior support analyst. Based on the following summaries of error log batches, "
        "write a final root cause analysis covering recurring patterns, key issues, and potential root causes. "
        "Combine the information from the individual summaries into a coherent and comprehensive overview. "
        "Provide a concise summary, limited to 3-5 sentences.\n\n"
        "Summaries:\n"
        + "\n".join(f"- {s}" for s in summaries)
        + "\n\nFinal Root Cause Summary:"
    )
    print(combined_summary_prompt)  # Print combined prompt for debugging

    inputs = tokenizer(combined_summary_prompt, return_tensors="pt", padding=True, truncation=True, max_length=1024)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(
            inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_length=300,
            num_beams=4,
            pad_token_id=tokenizer.eos_token_id,
        )

    final_summary = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    return final_summary


# === Run pipeline ===
filtered_logs_df = apply_filters_to_df(df_logs, filters, excludes)

if filtered_logs_df.empty:
    print("❌ No logs to summarize.")
else:
    print(f"\n📊 Summarizing {len(filtered_logs_df)} log entries...")
    final_summary = summarize_all_chunks(filtered_logs_df, chunk_size=25, error_fields=error_fields)
    print("\n✅ Final Log Summary:\n")
    print(final_summary)
