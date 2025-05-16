import pandas as pd
import google.generativeai as genai
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === Gemini API Setup ===
GEMINI_API_KEY = ""  # 
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-2.0-flash-lite")

# === Filters and Config ===
filters = {
    'index': 'ei_dev_mule_apps',
    'eventType': 'ERROR',
    #'uniqueId': 'b1cfc47b-3ec0-4637-ab9f-0264b98cb7fb',
    'failureType':'DATA',
    'environment':'dev-us',
    'Resource':'patchSalesOrders'
}
excludes = []
error_fields = ['comments', 'failures', 'ValidationErrors', 'error_0_description']

# === Load CSV logs ===
df_logs = pd.read_csv("flatlogs.csv")
column_list = [
    'eventDatetime', 'eventType', 'failureType', 'index', 'comments', 'uniqueId', 'interfaceId',
    'correlationId', 'source', 'target', 'originalClientId', 'originalClientName', 'appName', 
    'environment', 'ValidationErrors', 'failures', 'error_0_description', 'error_0_type', 'error_0_cause', 'error_0_detailedDescription'
]
df_logs = df_logs[column_list]

def apply_filters_to_df(df: pd.DataFrame, filters: dict, excludes: list) -> pd.DataFrame:
    filtered_df = df.copy()
    for key, value in filters.items():
        if key in filtered_df.columns:
            mask = filtered_df[key].astype(str).str.lower() == str(value).lower()
            filtered_df = filtered_df[mask]
    for exclusion in excludes:
        mask = filtered_df.apply(lambda row: exclusion.lower() not in str(row).lower(), axis=1)
        filtered_df = filtered_df[mask]
    return filtered_df

# === Step 2: Chunking ===
def chunk_dataframe(df: pd.DataFrame, chunk_size: int = 25):
    for i in range(0, len(df), chunk_size):
        yield df.iloc[i:i + chunk_size]

# === Step 3: Optimized Prompt ===
def dataframe_to_prompt(chunk_df: pd.DataFrame, error_fields: list) -> str:
    logs_text = ""
    for idx, row in chunk_df.iterrows():
        error_info = []
        for field in error_fields:
            if row.get(field):
                error_info.append(str(row.get(field)))
        error_info = " | ".join(error_info) if error_info else "N/A"

        logs_text += (
            f"{idx + 1}. [{row.get('eventDatetime', 'N/A')}] "
            f"App: {row.get('appName', 'N/A')}, "
            f"Env: {row.get('environment', 'N/A')}, "
            f"Interface: {row.get('interfaceId', 'N/A')}, "
            f"Error: {error_info}\n"
        )

    prompt = f"""
You are a support analyst reviewing logs from failed transactions.
Analyze the following log entries and focus on key problems and recurring errors.

Logs:
{logs_text}

Provide a concise summary with identified issues and recurring patterns.
"""
    return prompt

# === Step 4: Streaming Gemini call for small or chunked logs ===
def summarize_chunk_streaming(chunk_df: pd.DataFrame, error_fields: list):
    prompt = dataframe_to_prompt(chunk_df, error_fields)
    try:
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text  # Yield each chunk as it comes in
    except Exception as e:
        yield f"Error during streaming summarization: {e}"

# === Step 5: Combine chunk summaries and stream final summary ===
def summarize_all_chunks_streaming(df: pd.DataFrame, chunk_size: int, error_fields: list):
    summaries = []
    previous_summary = ""

    for chunk in chunk_dataframe(df, chunk_size):
        summary = summarize_chunk_streaming(chunk, error_fields)
        for line in summary:  # Yield each line of summary from streaming
            if summary and len(line.split()) > 5 and line != previous_summary:
                summaries.append(line)
                previous_summary = line

    if not summaries:
        yield "No meaningful summaries were generated from the log chunks."

    combined_prompt = (
        "You are a senior support analyst. Based on the following summaries of error log batches, "
        "write a final root cause analysis covering recurring patterns, key issues, and potential root causes. "
        "Combine the information from the individual summaries into a coherent and comprehensive overview. "
        "Provide actionable insights."
        "Ensure the summary is well structured.\n\n"
        "Summaries:\n"
        + "\n".join(f"- {s}" for s in summaries)
        + "\n\n Concise Final Root Cause Summary in few points: "
    )

    try:
        response = model.generate_content(combined_prompt, stream=True)
        for chunk in response:  # Stream the final summary in chunks
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"Error during final streaming summarization: {e}"

# === Step 6: Main driver with conditional chunking ===
def summarize():
    filtered_logs_df = apply_filters_to_df(df_logs, filters, excludes)
    total_rows = len(filtered_logs_df)

    if total_rows == 0:
        yield "No logs to summarize."

    elif total_rows <= 10:
        # Directly summarize if there are fewer than or equal to 10 logs
        yield from summarize_chunk_streaming(filtered_logs_df, error_fields)

    else:
        # Summarize in chunks if there are more than 10 logs
        yield from summarize_all_chunks_streaming(filtered_logs_df, chunk_size=25, error_fields=error_fields)
