import yaml

file_path = "/Users/ritesh/Downloads/submission_folder/New-Grad-Jobs/config.yml"

with open(file_path, 'r') as f:
    config = yaml.safe_load(f)

companies = []

if 'apis' in config:
    if 'greenhouse' in config['apis'] and 'companies' in config['apis']['greenhouse']:
        companies.extend([c['name'] for c in config['apis']['greenhouse']['companies']])

    if 'lever' in config['apis'] and 'companies' in config['apis']['lever']:
        companies.extend([c['name'] for c in config['apis']['lever']['companies']])

if 'workday' in config and 'companies' in config['workday']:
    companies.extend([c['name'] for c in config['workday']['companies']])

print(f"Total companies extracted: {len(companies)}")

suspicious = []
for n in companies:
    # Check if number at the end
    if " " in n and n.split()[-1].isdigit() and n not in ["37signals", "Take-Two Interactive", "C3.ai", "H2O.ai"]:
        suspicious.append(n)
    elif any(word in n.lower() for word in ["techcompany", "startupventure", "consumer", "marketplace", "sustainable"]):
        if n not in ["Consumer Reports", "Sustainable Coastlines"]:
            suspicious.append(n)

if suspicious:
    print(f"\nFound {len(suspicious)} potentially suspicious names:")
    for s in suspicious:
        print(f" - {s}")
else:
    print("\n✅ Verification Passed: No automatically generated or hallucinated company names found.")
