import re

file_path = "/Users/ritesh/Downloads/submission_folder/New-Grad-Jobs/config.yml"
with open(file_path, "r") as f:
    lines = f.readlines()

fake_patterns = [
    r"TechCompany",
    r"StartupVenture",
    r"Trade Marketplace",
    r"Community Consumer",
    r"Manufacturing Technologies",
    r"Technology Corporation",
    r"Smart Carbon",
    r"Digital Insure",
    r"Next Organic Tech",
    r"Green Tech \d+",
    r"Eco Innovators",
    r"Cyber Security \d+",
    r"Financial Services \d+",
    r"Healthcare Solutions \d+",
    r"Retail Commerce \d+",
    r"Media Entertainment \d+",
    r"Education Learning \d+",
    r"Manufacturing Production \d+",
    r"Logistics Supply Chain \d+",
    r"Real Estate Property \d+",
    r"Travel Hospitality \d+",
    r"Agriculture Farming \d+",
    r"Energy Utilities \d+",
    r"Automotive Transport \d+",
    r"Aerospace Defense \d+",
    r"Telecommunications Network \d+",
    r"Construction Building \d+",
    r"Food Beverage \d+",
    r"Apparel Fashion \d+",
    r"Beauty Cosmetics \d+",
    r"Sports Fitness \d+",
    r"Art Design \d+",
    r"Music Audio \d+",
    r"Gaming Esports \d+",
    r"Blockchain Crypto \d+",
    r"Artificial Intelligence \d+",
    r"Machine Learning \d+",
    r"Data Science \d+",
    r"Cloud Computing \d+",
    r"Internet of Things \d+",
    r"Robotics Automation \d+",
    r"Quantum Computing \d+",
    r"Biotechnology Genomics \d+",
    r"Nanotechnology Materials \d+",
    r"Space Exploration \d+",
    r"Clean Energy \d+",
    r"Smart City \d+",
    r"Autonomous Vehicle \d+",
    r"Virtual Reality \d+",
    r"Augmented Reality \d+",
    r"Mixed Reality \d+",
    r"Metaverse Virtual World \d+",
    r"Web3 Decentralized \d+",
    r"DeFi Finance \d+",
    r"NFT Collectibles \d+",
    r"DAO Governance \d+",
    r"^Data\w+ \d+$",
    r"Sustainable \w+",
    r"Manufacturing Enterprises",
    r"Technology Industries",
    r"Software Solutions \d+",
    r"Data Analytics \d+",
    r"Cloud Services \d+",
    r"Professional \w+",
    r"Technology \w+ \d+",
    r"Manufacturing \w+ \d+"
]

regexes = [re.compile(p) for p in fake_patterns]
deleted_count = 0
new_lines = []

delete_mode = False
delete_indent = 0

for line in lines:
    stripped = line.lstrip()
    indent = len(line) - len(stripped)
    
    # Empty line or comment
    if not stripped or stripped.startswith("#"):
        if delete_mode:
            continue
        else:
            new_lines.append(line)
            continue
            
    # If the line has same or less indent than the delete block, we exit delete_mode
    if delete_mode and indent <= delete_indent:
        delete_mode = False
        
    if not delete_mode:
        if stripped.startswith("- name:"):
            # Try to extract the name. Sometimes it's `- name: "Name"`
            parts = stripped.split("name:", 1)
            if len(parts) == 2:
                name_val = parts[1].strip().strip("\"'")
                
                is_fake = False
                for r in regexes:
                    if r.search(name_val):
                        is_fake = True
                        break
                
                if is_fake:
                    delete_mode = True
                    delete_indent = indent
                    deleted_count += 1
                    continue
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

print(f"Deleted {deleted_count} fake companies.")

with open(file_path, "w") as f:
    f.writelines(new_lines)
