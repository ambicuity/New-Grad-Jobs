import json
import re
import os

def fix_json_file(filepath):
    print(f"Processing {filepath}...")
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for NaN
    if 'NaN' not in content:
        print("No NaN found.")
        return

    # Replace NaN with null
    # We use regex to be safe about not replacing text inside strings if possible, 
    # but strictly speaking `NaN` as a value is distinct from `"NaN"`.
    # However, simply string replacing ` NaN,` with ` null,` might be safer or `: NaN`
    
    # Regex for key: NaN pattern
    # Matches ": NaN" or ": NaN," or ": NaN}"
    content_fixed = re.sub(r':\s*NaN([,\}\s])', r': null\1', content)
    
    # Also handle infinite
    content_fixed = re.sub(r':\s*Infinity([,\}\s])', r': null\1', content_fixed)
    content_fixed = re.sub(r':\s*-Infinity([,\}\s])', r': null\1', content_fixed)

    if content != content_fixed:
        print("Fixed NaN/Infinity values.")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content_fixed)
            
        # Verify it parses
        try:
            json.loads(content_fixed)
            print("Verification successful: Valid JSON.")
        except json.JSONDecodeError as e:
            print(f"Warning: Result is still not valid JSON: {e}")
    else:
        print("No changes made via regex (maybe NaN is inside strings?)")

fix_json_file('jobs.json')
fix_json_file('docs/jobs.json')
