from __future__ import annotations


def filter_records_by_query(records: list[dict[str, object]], query: str, fields: list[str]) -> list[dict[str, object]]:
    lowered = query.lower()
    filtered = []
    for record in records:
        haystack = " ".join(str(record.get(field, "")) for field in fields).lower()
        if lowered in haystack or any(token in haystack for token in lowered.split()):
            filtered.append(record)
    return filtered or records
