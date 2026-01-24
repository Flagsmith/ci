"""Fetch feature names from Flagsmith."""

import json
import os

import requests


def fetch_feature_names(
    *,
    api_url: str,
    api_key: str,
    project_id: str,
) -> list[str]:
    """Fetch feature names from the Flagsmith API."""
    response = requests.get(
        f"{api_url}/api/v1/projects/{project_id}/features/?page_size=1000",
        headers={"Authorization": f"Api-Key {api_key}"},
    )
    response.raise_for_status()
    return [feature["name"] for feature in response.json()["results"]]


def main() -> None:
    """CLI entry point for fetching feature names."""
    api_url = os.environ["FLAGSMITH_ADMIN_API_URL"]
    api_key = os.environ["FLAGSMITH_ADMIN_API_KEY"]
    project_id = os.environ["FLAGSMITH_PROJECT_ID"]

    feature_names = fetch_feature_names(
        api_url=api_url,
        api_key=api_key,
        project_id=project_id,
    )

    json_feature_names = json.dumps(feature_names)
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as gh_output:
            print(f"feature_names={json_feature_names}", file=gh_output)

    print(f"Fetched {len(feature_names)} feature names.")


if __name__ == "__main__":
    main()
