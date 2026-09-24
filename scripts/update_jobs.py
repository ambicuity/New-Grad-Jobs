#!/usr/bin/env python3
"""New Grad Jobs aggregator — CLI entrypoint.

Scrapes Greenhouse, Lever, Ashby, Workday, JobSpy (and optionally Google
Careers / GraphQL) and writes the public artifacts (jobs.json,
jobs-index.json, descriptions/, feed.xml, health.json) to $NGJ_OUTPUT_DIR
(default: site/public). The implementation lives in the ``ngj`` package;
running this file puts scripts/ on sys.path so ``ngj`` resolves.
"""

import sys

from ngj.pipeline import main

if __name__ == '__main__':
    sys.exit(main())
