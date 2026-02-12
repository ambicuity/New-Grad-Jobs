#!/usr/bin/env python3
import yaml
import sys

try:
    with open('config.yml', 'r') as f:
        config = yaml.safe_load(f)
    
    gh = len(config['apis']['greenhouse']['companies'])
    lever = len(config['apis']['lever']['companies'])
    workday = len(config['apis'].get('workday', {}).get('companies', []))
    
    print(f"✅ YAML loaded successfully!")
    print(f"Greenhouse: {gh} companies")
    print(f"Lever: {lever} companies")
    print(f"Workday: {workday} companies")
    print(f"TOTAL: {gh + lever + workday} companies")
    
    if gh + lever + workday < 10000:
        print(f"\n⚠️  WARNING: Expected ~10,000 companies but only loaded {gh + lever + workday}!")
        sys.exit(1)
    else:
        print(f"\n✅ All companies loaded correctly!")
        sys.exit(0)
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
