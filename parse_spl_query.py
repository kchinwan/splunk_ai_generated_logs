import re
from typing import Dict, List, Union

def parse_spl_query(spl: str) -> Dict[str, Union[str, List[str], Dict[str, str]]]:
    """
    Parses SPL into structured filters including index, time range, standard fields,
    and potential metadata/customMetadata filters like order ID, correlation ID.
    """
    filters = {
        "index": None,
        "time": {},
        "fields": {},
        "customMetadata": {},
        "exclude": []
    }

    # Index
    index_match = re.search(r'index="?([\w\-]+)"?', spl)
    if index_match:
        filters["index"] = index_match.group(1)

    # Time filters
    earliest_match = re.search(r"earliest=([^\s|]+)", spl)
    if earliest_match:
        filters["time"]["earliest"] = earliest_match.group(1)

    latest_match = re.search(r"latest=([^\s|]+)", spl)
    if latest_match:
        filters["time"]["latest"] = latest_match.group(1)

    # Key=value filters
    for match in re.findall(r"(\w+)=([^\s|]+)", spl):
        key, value = match
        # Known custom metadata keys
        if key.upper() in {
            "XX_SO_ORDER_NUMBER", "XX_SO_LINE_NUMBER", "XX_WO_ID",
            "XX_SO_HEADER_ID", "BI_NUMBER", "ORDERID", "TRANSACTIONID"
        }:
            filters["customMetadata"][key] = value
        else:
            filters["fields"][key] = value

    # Negation / Exclusions
    not_matches = re.findall(r'NOT\s+"([^"]+)"', spl)
    if not_matches:
        filters["exclude"].extend(not_matches)

    return filters
