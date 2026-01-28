"""Scan code references for Flagsmith feature flags."""

import json
import logging
import os
import re
import subprocess
from collections import defaultdict, deque
from collections.abc import Generator
from pathlib import Path

from code_references.types import CodeReferenceSubmit

type FeatureName = str

logger = logging.getLogger(__name__)


def should_skip_file(file_path: Path) -> bool:
    """Whether to skip a file likely irrelevant to feature reference scanning."""
    if not file_path.is_file():
        return True
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


def list_repository_files(repository_path: Path) -> list[Path]:
    """List all tracked files in the git repository."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repository_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return [repository_path / line for line in result.stdout.splitlines() if line]


def scan_code_references(
    feature_names: list[FeatureName],
    repository_path: Path,
) -> Generator[CodeReferenceSubmit]:
    """Search for references to a feature name in the codebase."""
    all_files = list_repository_files(repository_path)
    for path in all_files:
        if should_skip_file(path):
            logger.info(f"{path}: skipped")
            continue
        context: deque[str] = deque(maxlen=2)
        with path.open("r", encoding="utf-8", errors="ignore") as file:
            references_count = 0
            for line_number, line in enumerate(file, start=1):
                context.append(line)
                for feature_name in feature_names:
                    if feature_name not in line:
                        continue
                    pattern = rf"""(?i:(?:feature|flag)\w*\(\s*(["']){
                        re.escape(feature_name)
                    })\1"""
                    if re.search(pattern, "".join(context)):
                        references_count += 1
                        yield {
                            "feature_name": feature_name,
                            "file_path": str(path.relative_to(repository_path)),
                            "line_number": line_number,
                        }
            logger.info(f"{path}: {references_count} references found")


def main() -> None:
    """CLI entry point for scanning code references."""
    feature_names = json.loads(os.environ["FEATURE_NAMES"])
    repository_path = Path(os.environ["GIT_REPOSITORY_PATH"])

    if not repository_path.is_dir():
        raise SystemExit(f"GIT_REPOSITORY_PATH is not a directory: {repository_path}")

    code_references = list(
        scan_code_references(feature_names, repository_path),
    )

    json_references = json.dumps(code_references)
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as gh_output:
            print(f"code_references={json_references}", file=gh_output)

    if not code_references:
        print("No code references found.")
        return

    references_by_feature: defaultdict[FeatureName, list[CodeReferenceSubmit]] = (
        defaultdict(
            list,
        )
    )
    sorted_code_references = sorted(
        code_references,
        key=lambda ref: (ref["feature_name"], ref["file_path"], ref["line_number"]),
    )
    for ref in sorted_code_references:
        references_by_feature[ref["feature_name"]].append(ref)

    print("Code References:")
    for feature_name, references in references_by_feature.items():
        print(f"\nFeature: {feature_name}")
        for ref in references:
            print(f"  - {ref['file_path']}:{ref['line_number']}")


if __name__ == "__main__":
    main()
