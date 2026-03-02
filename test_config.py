#!/usr/bin/env python3
import sys

import yaml


def validate_config(config_path: str = "config.yml") -> int:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        apis = config["apis"]
        gh = len(apis["greenhouse"]["companies"])
        lever = len(apis["lever"]["companies"])
        workday = len(apis.get("workday", {}).get("companies", []))

        print("✅ YAML loaded successfully!")
        print(f"Greenhouse: {gh} companies")
        print(f"Lever: {lever} companies")
        print(f"Workday: {workday} companies")

        total = gh + lever + workday
        print(f"TOTAL: {total} companies")

        if total < 10000:
            print(f"\n⚠️  WARNING: Expected ~10,000 companies but only loaded {total}!")
            return 1

        print("\n✅ All companies loaded correctly!")
        return 0

    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return 1
    except yaml.YAMLError as err:
        print(f"❌ Invalid YAML in {config_path}: {err}")
        return 1
    except KeyError as err:
        print(f"❌ Missing required config key: {err}")
        return 1
    except TypeError as err:
        print(f"❌ Invalid config structure in {config_path}: {err}")
        return 1


def main() -> int:
    return validate_config("config.yml")


if __name__ == "__main__":
    sys.exit(main())
