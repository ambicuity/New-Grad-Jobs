#!/usr/bin/env python3
import logging
import sys

import yaml

MIN_EXPECTED_COMPANIES = 200
logger = logging.getLogger(__name__)


def validate_config(config_path: str = "config.yml") -> int:
    """Validate job source configuration and company totals.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        int: Exit-style status code.
            - 0 when config is valid and total companies meet threshold.
            - 1 for warning threshold miss or any validation error.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        apis = config["apis"]
        gh = len(apis["greenhouse"]["companies"])
        lever = len(apis["lever"]["companies"])
        workday = len(apis.get("workday", {}).get("companies", []))

        logger.info("✅ YAML loaded successfully!")
        logger.info("Greenhouse: %s companies", gh)
        logger.info("Lever: %s companies", lever)
        logger.info("Workday: %s companies", workday)

        total = gh + lever + workday
        logger.info("TOTAL: %s companies", total)

        if total < MIN_EXPECTED_COMPANIES:
            logger.warning(
                "⚠️  WARNING: Expected ~%s companies but only loaded %s!",
                f"{MIN_EXPECTED_COMPANIES:,}",
                total,
            )
            return 1

        logger.info("✅ All companies loaded correctly!")
        return 0

    except FileNotFoundError:
        logger.error("❌ Config file not found: %s", config_path)
        return 1
    except yaml.YAMLError as err:
        logger.error("❌ Invalid YAML in %s: %s", config_path, err)
        return 1
    except KeyError as err:
        logger.error("❌ Missing required config key: %s", err)
        return 1
    except TypeError as err:
        logger.error("❌ Invalid config structure in %s: %s", config_path, err)
        return 1


def main() -> int:
    """Run config validation using the default config path.

    Returns:
        int: Exit-style status code from ``validate_config``.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return validate_config("config.yml")


if __name__ == "__main__":
    sys.exit(main())
