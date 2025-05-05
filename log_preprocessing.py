import json

def extract_custom_metadata(custom_metadata):
    """Flatten customMetadata list of dicts into a single dict."""
    flat = {}
    for item in custom_metadata:
        if isinstance(item, dict):
            name = item.get("Name")
            value = item.get("Value")
            if name:
                flat[name] = value
        else:
            print(f"Skipping non-dict customMetadata item: {item}")
    return flat


def extract_validation_errors(custom_metadata):
    """Extract validation errors from the custom metadata."""
    for item in custom_metadata:
        if isinstance(item, dict) and item.get("Name") == "ValidationErrors":
            value = item.get("Value")
            if isinstance(value, dict):
                return value.get("Errors", [])
            else:
                print(f"Invalid ValidationErrors format: {value}")
    return []


def flatten_log_entry(log):
    """Flatten nested fields from a log entry."""
    flattened = {
        "eventDatetime": log.get("eventDatetime"),
        "eventType": log.get("eventType"),
        "failureType": log.get("failureType", None),
        "index": log.get("index")
    }

    metadata = log.get("metadata", {})
    if isinstance(metadata, dict):
        for k, v in metadata.items():
            if k != "customMetadata" and not isinstance(v, (dict, list)):
                flattened[k] = v

        custom_metadata = metadata.get("customMetadata", [])
        if isinstance(custom_metadata, list):
            flattened.update(extract_custom_metadata(custom_metadata))
            flattened["validationErrors"] = extract_validation_errors(custom_metadata)
        else:
            print(f"Invalid customMetadata format: {custom_metadata}")
    else:
        print(f"Invalid metadata format: {metadata}")

    errors = log.get("errors", [])
    if isinstance(errors, list):
        for i, error in enumerate(errors):
            if isinstance(error, dict):
                for k, v in error.items():
                    flattened[f"error_{i}_{k}"] = v
            else:
                print(f"Invalid error entry: {error}")

    return flattened
