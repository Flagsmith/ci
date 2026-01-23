# /// script
# dependencies = ["requests"]
# ///
"""Collect code references for Flagsmith feature flags."""

import json
import os
import re
from collections import defaultdict, deque
from collections.abc import Generator
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

type FeatureName = str


@dataclass(frozen=True, slots=True)
class CodeReference:
    feature_name: FeatureName
    file_path: str
    line_number: int


def should_skip_file(file_path: Path) -> bool:
    """Whether to skip a file based on its size or content"""
    file_size = file_path.stat().st_size
    if file_size == 0:  # Empty files are irrelevant
        return True
    if file_size > 1024 * 1024:  # Large files are likely binary
        return True
    with file_path.open("rb") as file:
        chunk = file.read(4096)  # A text file rarely contains null bytes
        if b"\0" in chunk:
            return True
        try:
            chunk.decode("utf-8")
        except UnicodeDecodeError:  # Decoding likely fails for binary files
            return True
    return False


def find_references(
    feature_names: list[FeatureName],
    exclude_patterns: list[str] | None = None,
) -> Generator[CodeReference]:
    """Search for references to a feature name in the codebase."""
    exclude_patterns = exclude_patterns or []
    all_files = Path(".").glob("**/*")
    for path in all_files:
        if any(pattern in str(path).lower() for pattern in exclude_patterns):
            continue
        if not path.is_file():
            continue
        if should_skip_file(path):
            continue
        context: deque[str] = deque(maxlen=2)
        with path.open("r", encoding="utf-8", errors="ignore") as file:
            for line_number, line in enumerate(file, start=1):
                context.append(line)
                for feature_name in feature_names:
                    if feature_name not in line:
                        continue
                    # Match function calls like feature("name") or flag("name")
                    pattern = rf"""(?i:(?:feature|flag)\w*\(\s*(["']){
                        re.escape(feature_name)
                    })\1"""
                    if re.search(pattern, "".join(context)):
                        yield CodeReference(feature_name, str(path), line_number)
                    # TODO: Add more sophisticated matching,
                    # e.g. feature names defined as constants


def retrieve_feature_names(
    *,
    api_url: str,
    api_key: str,
    project_id: str,
) -> list[FeatureName]:
    """Fetch feature names from the Flagsmith API."""
    response = requests.get(  # TODO: Make better use of pagination
        f"{api_url}/api/v1/projects/{project_id}/features/?page_size=1000",
        headers={"Authorization": f"Api-Key {api_key}"},
    )
    response.raise_for_status()
    return [feature["name"] for feature in response.json()["results"]]


def main() -> None:
    api_url = os.environ["FLAGSMITH_ADMIN_API_URL"]
    api_key = os.environ["FLAGSMITH_ADMIN_API_KEY"]
    project_id = os.environ["FLAGSMITH_PROJECT_ID"]
    exclude_patterns = (
        os.environ.get("EXCLUDE_PATTERNS", "").replace(" ", "").split(",")
    )

    # Fetch visible features
    feature_names = retrieve_feature_names(
        api_url=api_url,
        api_key=api_key,
        project_id=project_id,
    )

    # Find code references
    code_references = list(find_references(feature_names, exclude_patterns))

    # Output to GHA
    json_references = json.dumps([asdict(ref) for ref in code_references])
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as gh_output:
            print(f"code_references={json_references}", file=gh_output)

    if not code_references:
        print("No code references found.")
        return

    references_by_feature: defaultdict[FeatureName, list[CodeReference]] = defaultdict(
        list,
    )
    sorted_code_references = sorted(
        code_references,
        key=lambda ref: (ref.feature_name, ref.file_path, ref.line_number),
    )
    for ref in sorted_code_references:
        references_by_feature[ref.feature_name].append(ref)

    print("Code References:")
    for feature_name, references in references_by_feature.items():
        print(f"\nFeature: {feature_name}")
        for ref in references:
            print(f"  - {ref.file_path}:{ref.line_number}")


if __name__ == "__main__":
    main()
