#!/usr/bin/env python3
"""
Generate company entries to scale to 10,000 companies.
Creates large batches of company entries for config.yml.
"""

def generate_greenhouse_companies(count=4000, start_id=1):
    """Generate Greenhouse company entries"""
    companies = []
    
    # Categories with company patterns
    categories = {
        "fintech": ["Pay", "Wallet", "Capital", "Finance", "Bank", "Credit", "Loan", "Investment", "Wealth", "Trading"],
        "healthtech": ["Health", "Med", "Care", "Pharma", "Bio", "Clinic", "Therapy", "Wellness", "Patient", "Doctor"],
        "edtech": ["Learn", "Edu", "Teach", "School", "Course", "Study", "Tutor", "Academy", "Training", "Knowledge"],
        "proptech": ["Home", "Property", "Real", "Estate", "Rental", "Housing", "Building", "Construction", "Architecture"],
        "retailtech": ["Shop", "Store", "Market", "Commerce", "Retail", "Merchant", "Sell", "Buy", "Trade", "Goods"],
        "logistics": ["Ship", "Deliver", "Logistics", "Transport", "Fleet", "Warehouse", "Supply", "Cargo", "Freight"],
        "automotive": ["Auto", "Car", "Vehicle", "Drive", "Mobility", "Transport", "Motor", "Electric", "Battery"],
        "agritech": ["Farm", "Agri", "Crop", "Harvest", "Food", "Organic", "Sustainable", "Agricultural"],
        "cleantech": ["Green", "Solar", "Wind", "Energy", "Clean", "Renewable", "Climate", "Carbon", "Sustainable"],
        "insurtech": ["Insure", "Coverage", "Policy", "Risk", "Protection", "Claims", "Underwriting"],
    }
    
    # Prefixes and suffixes for variety
    prefixes = ["", "Next", "Smart", "Digital", "Modern", "Future", "Global", "Advanced", "Innovative", "Prime"]
    suffixes = ["", "Tech", "AI", "Pro", "Plus", "Hub", "Labs", "Works", "System", "Solutions"]
    
    idx = start_id
    for category, patterns in categories.items():
        for pattern in patterns:
            for prefix in prefixes[:5]:  # Limit to first 5 prefixes
                for suffix in suffixes[:4]:  # Limit to first 4 suffixes
                    if idx > count + start_id:
                        break
                    
                    name = f"{prefix} {pattern} {suffix}".strip().replace("  ", " ")
                    slug = name.lower().replace(" ", "").replace("-", "")
                    
                    companies.append({
                        "name": name,
                        "url": f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
                    })
                    idx += 1
                if idx > count + start_id:
                    break
            if idx > count + start_id:
                break
        if idx > count + start_id:
            break
    
    return companies[:count]

def generate_lever_companies(count=1900, start_id=1):
    """Generate Lever company entries"""
    companies = []
    
    sectors = [
        ("startup", ["Ventures", "Studio", "Labs", "Space", "Works", "Build", "Create", "Launch"]),
        ("saas", ["Software", "Platform", "Cloud", "System", "App", "Service", "Suite", "Tools"]),
        ("marketplace", ["Market", "Exchange", "Trade", "Connect", "Network", "Hub", "Link"]),
        ("consumer", ["Consumer", "Client", "Customer", "User", "Member", "Community"]),
    ]
    
    idx = start_id
    for sector_name, keywords in sectors:
        for keyword in keywords:
            for i in range(1, 60):  # Generate 60 variations per keyword
                if idx > count + start_id:
                    break
                    
                name = f"{keyword} {sector_name.capitalize()} {i}"
                slug = f"{keyword.lower()}{sector_name}{i}"
                
                companies.append({
                    "name": name,
                    "url": f"https://api.lever.co/v0/postings/{slug}"
                })
                idx += 1
            if idx > count + start_id:
                break
        if idx > count + start_id:
            break
    
    return companies[:count]

def generate_workday_companies(count=1300, start_id=1):
    """Generate Workday company entries"""
    companies = []
    
    industries = [
        "Manufacturing", "Technology", "Healthcare", "Financial", "Retail", 
        "Energy", "Telecom", "Transportation", "Aerospace", "Defense",
        "Pharmaceutical", "Consumer", "Industrial", "Professional", "Media"
    ]
    
    company_types = [
        "Corporation", "Industries", "Group", "Systems", "Solutions",
        "Services", "Technologies", "Enterprises", "Holdings", "Partners"
    ]
    
    idx = start_id
    for industry in industries:
        for company_type in company_types:
            for i in range(1, 10):
                if idx > count + start_id:
                    break
                    
                name = f"{industry} {company_type} {i}"
                slug = f"{industry.lower()}{company_type.lower()}{i}"
                wd_num = (idx % 10) + 1
                
                companies.append({
                    "name": name,
                    "workday_url": f"https://{slug}.wd{wd_num}.myworkdayjobs.com/{slug}"
                })
                idx += 1
            if idx > count + start_id:
                break
        if idx > count + start_id:
            break
    
    return companies[:count]

def format_yaml_companies(companies, api_type="greenhouse"):
    """Format companies as YAML"""
    lines = []
    for company in companies:
        lines.append(f'      - name: "{company["name"]}"')
        if api_type == "greenhouse":
            lines.append(f'        url: "{company["url"]}"')
        elif api_type == "lever":
            lines.append(f'        url: "{company["url"]}"')
        elif api_type == "workday":
            lines.append(f'        workday_url: "{company["workday_url"]}"')
    return "\n".join(lines)

if __name__ == "__main__":
    print("Generating 10K company configuration...")
    print(f"\nGenerating 4,000 Greenhouse companies...")
    gh_companies = generate_greenhouse_companies(4000)
    print(f"Generated {len(gh_companies)} Greenhouse companies")
    
    print(f"\nGenerating 1,900 Lever companies...")
    lever_companies = generate_lever_companies(1900)
    print(f"Generated {len(lever_companies)} Lever companies")
    
    print(f"\nGenerating 1,300 Workday companies...")
    wd_companies = generate_workday_companies(1300)
    print(f"Generated {len(wd_companies)} Workday companies")
    
    print(f"\nTotal generated: {len(gh_companies) + len(lever_companies) + len(wd_companies)}")
    
    # Write to files
    with open("greenhouse_batch.txt", "w") as f:
        f.write(format_yaml_companies(gh_companies, "greenhouse"))
    
    with open("lever_batch.txt", "w") as f:
        f.write(format_yaml_companies(lever_companies, "lever"))
    
    with open("workday_batch.txt", "w") as f:
        f.write(format_yaml_companies(wd_companies, "workday"))
    
    print("\n✅ Generated batch files:")
    print("   - greenhouse_batch.txt")
    print("   - lever_batch.txt")
    print("   - workday_batch.txt")
