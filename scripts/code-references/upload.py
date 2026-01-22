# /// script
# dependencies = ["requests"]
# ///
"""Upload code references to Flagsmith."""

import json
import os

import requests

FLAGSMITH_ADMIN_API_URL = os.environ["FLAGSMITH_ADMIN_API_URL"]
FLAGSMITH_ADMIN_API_KEY = os.environ["FLAGSMITH_ADMIN_API_KEY"]
FLAGSMITH_PROJECT_ID = os.environ["FLAGSMITH_PROJECT_ID"]
CODE_REFERENCES = os.environ["CODE_REFERENCES"]
REPOSITORY_URL = os.environ["REPOSITORY_URL"]
REVISION = os.environ["REVISION"]


def main() -> None:
    code_references = json.loads(CODE_REFERENCES)
    if not code_references:
        print("No code references to upload.")
        return

    response = requests.post(
        f"{FLAGSMITH_ADMIN_API_URL}/api/v1/projects/{FLAGSMITH_PROJECT_ID}/code-references/",
        headers={"Authorization": f"Api-Key {FLAGSMITH_ADMIN_API_KEY}"},
        json={
            "repository_url": REPOSITORY_URL,
            "revision": REVISION,
            "code_references": code_references,
        },
    )
    response.raise_for_status()
    print(f"Uploaded {len(code_references)} code references.")


if __name__ == "__main__":
    main()
