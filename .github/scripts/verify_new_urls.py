import sys
import subprocess
import re
from pathlib import Path
from urllib.parse import urlparse

# Add repo root to import path so we can import from scripts/update_jobs.py
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts.update_jobs import create_optimized_session


def get_new_urls_from_diff(diff_text):
    """
    Extracts URLs that are literally added (lines starting with +) in config.yml.
    """
    urls = []
    # Only look at added lines that aren't diff headers
    added_lines = [line for line in diff_text.splitlines() if line.startswith('+') and not line.startswith('+++')]

    for line in added_lines:
        # Looking for: url: "https://..."
        match = re.search(r'url:\s*["\']( https?://[^"\']+)["\']', line)
        if match:
            urls.append(match.group(1).strip())

    return list(set(urls))


# ATS API hostnames that must return JSON — substring check is insufficient;
# use urlparse().netloc to compare the actual hostname and avoid path-based bypasses.
_ATS_JSON_HOSTNAMES = frozenset({
    'boards-api.greenhouse.io',
    'api.lever.co',
})


def verify_url(session, url):
    """
    Performs a GET request to verify the URL exists.
    Returns (success_bool, status_code_or_err_msg)
    """
    try:
        # We use GET because some ATS endpoints reject HEAD requests.
        # Timeout of 10 s prevents hanging on slow endpoints.
        response = session.get(url, timeout=10)
    except Exception as e:
        return False, str(e)

    # If the endpoint is a known ATS JSON API but returned HTML, treat as failure.
    # Compare against the parsed hostname — NOT a substring of the full URL — to
    # prevent path-based bypasses (e.g. http://evil.com/boards-api.greenhouse.io/…).
    hostname = urlparse(url).netloc.lower()
    content_type = response.headers.get('content-type', '')
    if response.status_code == 200 and 'json' not in content_type:
        if hostname in _ATS_JSON_HOSTNAMES:
            return False, f"{response.status_code} but returned {content_type} (expected JSON)"

    # 200 OK or 401 Unauthorized (auth required but endpoint exists)
    if response.status_code in [200, 401]:
        return True, response.status_code

    return False, response.status_code


def main():
    try:
        # Get the diff for config.yml against the target branch
        result = subprocess.run(
            ["git", "diff", "origin/main...HEAD", "--", "config.yml"],
            capture_output=True, text=True, check=True
        )
        diff_text = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Failed to get git diff for config.yml: {e}")
        return 1

    if not diff_text.strip():
        print("No changes to config.yml found. Skipping verification.")
        return 0

    new_urls = get_new_urls_from_diff(diff_text)
    if not new_urls:
        print("✅ No new URLs found in config.yml diff. Skipping verification.")
        return 0

    print(f"🔍 Found {len(new_urls)} new URLs in config.yml. Verifying...")

    session = create_optimized_session()
    failures = []

    for i, url in enumerate(new_urls, 1):
        print(f"[{i}/{len(new_urls)}] Testing: {url} ... ", end="")
        sys.stdout.flush()

        success, info = verify_url(session, url)

        if success:
            print(f"✅ OK ({info})")
        else:
            print(f"❌ FAILED ({info})")
            failures.append((url, info))

    if failures:
        print("\n" + "="*50)
        print("🚨 URL VERIFICATION FAILED 🚨")
        print("="*50)
        with open(".url_failures", "w") as f:
            for url, info in failures:
                msg = f"- {url} ({info})"
                print(msg)
                f.write(msg + "\n")
        print("\nPlease fix or remove these URLs before merging.")
        return 1

    print("\n✅ All new URLs verified successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
