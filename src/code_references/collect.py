"""Collect code references for Flagsmith feature flags."""

import json
import os
import re
from collections import defaultdict, deque
from collections.abc import Generator
from dataclasses import asdict, dataclass
from pathlib import Path

type FeatureName = str


@dataclass(frozen=True, slots=True)
class CodeReference:
    feature_name: FeatureName
    file_path: str
    line_number: int


def should_skip_file(file_path: Path) -> bool:
    """Whether to skip a file based on its size or content."""
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
    scan_path: Path | None = None,
) -> Generator[CodeReference]:
    """Search for references to a feature name in the codebase."""
    exclude_patterns = [p for p in (exclude_patterns or []) if p]
    base_path = scan_path or Path(".")
    all_files = base_path.glob("**/*")
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
                    pattern = rf"""(?i:(?:feature|flag)\w*\(\s*(["']){
                        re.escape(feature_name)
                    })\1"""
                    if re.search(pattern, "".join(context)):
                        relative_path = path.relative_to(base_path)
                        yield CodeReference(
                            feature_name,
                            str(relative_path),
                            line_number,
                        )


def main() -> None:
    """CLI entry point for scanning code references."""
    feature_names = json.loads(os.environ["FEATURE_NAMES"])
    exclude_patterns = (
        os.environ.get("EXCLUDE_PATTERNS", "").replace(" ", "").split(",")
    )
    scan_path_str = os.environ.get("SCAN_PATH")
    scan_path = Path(scan_path_str) if scan_path_str else None

    code_references = list(find_references(feature_names, exclude_patterns, scan_path))

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
