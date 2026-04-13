"""Upload code references to Flagsmith."""

import json
import os

import requests

from code_references.types import CodeReferenceSubmit


def upload_code_references(
    code_references: list[CodeReferenceSubmit],
    *,
    api_url: str,
    api_key: str,
    project_id: str,
    repository_url: str,
    revision: str,
    vcs_provider: str = "github",
) -> int:
    """Upload code references to Flagsmith API. Returns count of uploaded references."""
    if not code_references:
        return 0

    response = requests.post(
        f"{api_url}/api/v1/projects/{project_id}/code-references/",
        headers={"Authorization": f"Api-Key {api_key}"},
        json={
            "repository_url": repository_url,
            "revision": revision,
            "code_references": code_references,
            "vcs_provider": vcs_provider,
        },
    )
    if not response.ok:
        raise SystemExit(
            f"Failed to upload code references: {response.status_code} {response.text}",
        )
    return len(code_references)


def main() -> None:
    """CLI entry point for uploading code references."""
    code_references = json.loads(os.environ["CODE_REFERENCES"])
    count = upload_code_references(
        code_references,
        api_url=os.environ["FLAGSMITH_ADMIN_API_URL"],
        api_key=os.environ["FLAGSMITH_ADMIN_API_KEY"],
        project_id=os.environ["FLAGSMITH_PROJECT_ID"],
        repository_url=os.environ["REPOSITORY_URL"],
        revision=os.environ["REVISION"],
        vcs_provider=os.environ.get("VCS_PROVIDER", "github"),
    )
    if count:
        print(f"Uploaded {count} code references.")
    else:
        print("No code references to upload.")


if __name__ == "__main__":
    main()
