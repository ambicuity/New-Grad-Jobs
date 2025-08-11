# New-Grad-Jobs

You are a meticulous repo scaffolder. Create a new GitHub repository that automatically updates its README every 5 minutes with New Grad jobs (Software, Data, Network, SRE) from public Lever and Greenhouse APIs. Return your answer as four separate file sections with fenced code blocks, in this exact order:

Scrape from Greenhouse, Lever, etc all using their public JSON endpoints (no HTML scraping).

Filter roles whose title contains a new-grad signal (new grad, new graduate, entry-level, graduate) and a track signal (software, data, network, SRE; include common synonyms like “site reliability”, “ML”, etc.).

Keep only postings not older than past 7 days (configurable).

Sort by most recently updated/created.

Use a GitHub Action that runs on a cron */5 * * * * and can be run manually.

Output of readme should be in properly table formatted and all jobs links should be properly active 
