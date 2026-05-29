#!/usr/bin/env python3
"""
Unit tests for the job categorization logic in scripts/generate_companies.py.

These tests validate that companies are correctly generated for Greenhouse,
Lever and Workday and that argparse arguments are parsed correctly.
"""

import sys
import os

# Ensure the scripts directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from generate_companies import (
    generate_greenhouse_companies,
    generate_lever_companies,
    generate_workday_companies,
    parse_arguments,
)

def test_parse_arguments_default():
    args = parse_arguments([])
    assert args.greenhouse_count == 4000
    assert args.lever_count == 1900
    assert args.workday_count == 1300

def test_parse_arguments_custom():
    args = parse_arguments(['--greenhouse-count', '100', '--lever-count', '50', '--workday-count', '30'])
    assert args.greenhouse_count == 100
    assert args.lever_count == 50
    assert args.workday_count == 30

def test_parse_arguments_negative():
    try:
        parse_arguments(['--greenhouse-count', '-100'])
        assert False, "Expected SystemExit due to negative count"
    except SystemExit:
        pass

def test_greenhouse_count():
    companies = generate_greenhouse_companies(10)
    assert len(companies) == 10

def test_lever_count():
    companies = generate_lever_companies(10)
    assert len(companies) == 10

def test_workday_count():
    companies = generate_workday_companies(10)
    assert len(companies) == 10

def test_greenhouse_count_zero():
    assert generate_greenhouse_companies(0) == []

def test_lever_count_zero():
    assert generate_lever_companies(0) == []

def test_workday_count_zero():
    assert generate_workday_companies(0) == []
