import json
import math
import os


def _replace_invalid_numbers(obj):
    """Recursively replace NaN and Infinity values with None."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _replace_invalid_numbers(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_replace_invalid_numbers(v) for v in obj]
    return obj


def fix_json_file(filepath: str) -> None:
    """Replace NaN and Infinity values in a JSON file with null.

    Args:
        filepath: Path to the JSON file to update.

    Returns:
        None. The file is updated in place when invalid numeric values are fixed.
    """
    print(f"Processing {filepath}...")
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f, parse_constant=lambda x: float(x))

    fixed_data = _replace_invalid_numbers(data)

    if fixed_data != data:
        print("Fixed NaN/Infinity values.")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(fixed_data, f, indent=2, ensure_ascii=False)
        print("Verification successful: Valid JSON.")
    else:
        print("No NaN/Infinity values found.")

fix_json_file('jobs.json')
fix_json_file('docs/jobs.json')
