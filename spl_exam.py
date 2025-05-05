import random
import json

# Provided indexes mapped to environments
indexes_by_env = {
    "prod": [
        "ei_prod_mule_apps", "ei_prod_tms", "ei_prod_oic_apps"
    ],
    "qa": [
        "ei_qa_wmb", "ei_qa_mule_apps", "ei_qa_oic_apps"
    ],
    "dev": [
        "ei_dev_mule_apps", "ei_dev_axway_apps", "ei_dev_oic_apps", "ei_wmb_idx"
    ]
}

# All interfaces and app prefixes
iface_ids = ['I10020', 'PA00002', 'PA00021', 'SA00015']
app_prefixes = ['oracle31', 'i10025', 'CI_I_117', 'ea10037', 'I_110-1']

# Template list of natural language queries and corresponding SPL patterns
examples = [
    ("Get all error logs from {env} environment related to data failures, excluding end-of-input errors.",
     'index="{index}" | spath eventType | search eventType=ERROR, failureType=DATA NOT "end-of-input at root"'),

    ("Show system failures in the {env} environment.",
     'index="{index}" | spath eventType | search eventType=ERROR, failureType=SYSTEM, "metadata.environment"="{env}*", "notificationDetails.enabled"=*'),

    ("List error logs from {env} Mule apps.",
     'index="{index}" | spath eventType | search eventType=ERROR'),

    ("Find error logs from {env} with any failure type.",
     'index="{index}" | spath eventType | search eventType=ERROR, failureType=*'),

    ("Get logs with message 'No space left on device' in all sources.",
     'index=* "No space left on device" source="http:SPLUNK_HEC_MULE_APPS_PROD_EVENTS"'),

    ("Get all logs for app starting with {app_prefix} in {env}.",
     'index="{index}" "metadata.appName"="{app_prefix}*"'),

    ("Show logs with interface ID {iface} in {env}.",
     'index="{index}" "metadata.interfaceId"={iface}'),

    ("Find logs where notification is enabled in {env}.",
     'index="{index}" | spath eventType | search "notificationDetails.enabled"=*'),

    ("Retrieve logs with error type SYSTEM but exclude interface IDs PA00002, PA00021 in {env}.",
     'index="{index}" * extracted_eventType=ERROR failureType=SYSTEM "metadata.interfaceId" != "PA00002" "metadata.interfaceId" != "PA00021"'),

    ("Summarize error logs by interface ID and app name in {env}.",
     'index="{index}" | stats count by metadata.interfaceId, metadata.appName')
]

# Generate 50 examples
data = []
for _ in range(50):
    template, spl_template = random.choice(examples)

    # Determine environment based on template content
    if "in all sources" in template:
        env = random.choice(["prod", "qa", "dev"])
        index = "*"
    else:
        env = random.choice(list(indexes_by_env.keys()))
        index = random.choice(indexes_by_env[env])

    # Fill placeholders
    iface = random.choice(iface_ids)
    app_prefix = random.choice(app_prefixes)

    input_text = template.format(env=env, index=index, iface=iface, app_prefix=app_prefix)
    output_text = spl_template.format(env=env, index=index, iface=iface, app_prefix=app_prefix)

    data.append({"input": input_text, "output": output_text})

# Write to JSONL file
with open("splunk_query_data.json", "w") as f:
    for item in data:
        f.write(json.dumps(item) + "\n")
