import json
import os


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

    has_invalid_constants = False

    def handle_constant(val: str) -> None:
        nonlocal has_invalid_constants
        has_invalid_constants = True
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f, parse_constant=handle_constant)

    if has_invalid_constants:
        print("Fixed NaN/Infinity values.")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Verification successful: Valid JSON.")
    else:
        print("No NaN/Infinity values found.")


fix_json_file('jobs.json')
fix_json_file('docs/jobs.json')
