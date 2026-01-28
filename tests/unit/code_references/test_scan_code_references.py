from pathlib import Path
from textwrap import dedent

import pytest
from pytest_mock import MockerFixture

from code_references.cli.scan_code_references import (
    list_repository_files,
    main,
    scan_code_references,
    should_skip_file,
)


@pytest.mark.parametrize(
    "file_content",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"x" * (1024 * 1024 + 1), id="over_1mb"),
        pytest.param(b"has\x00null\x00bytes", id="binary"),
        pytest.param(b"\xff\xfe not utf-8", id="non_utf8"),
    ],
)
def test_should_skip_file__non_text_file__returns_true(
    tmp_path: Path,
    file_content: bytes,
) -> None:
    # Given
    file_path = tmp_path / "file"
    file_path.write_bytes(file_content)

    # When
    result = should_skip_file(file_path)

    # Then
    assert result is True


def test_should_skip_file__text_file__returns_false(tmp_path: Path) -> None:
    # Given
    file_path = tmp_path / "file.py"
    file_path.write_text("print('hello')")

    # When
    result = should_skip_file(file_path)

    # Then
    assert result is False


def test_list_repository_files__returns_tracked_files(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Given
    mocker.patch("subprocess.run").return_value.stdout = "app.py\nlib/utils.py"

    # When
    result = list_repository_files(tmp_path)

    # Then
    assert result == [tmp_path / "app.py", tmp_path / "lib/utils.py"]


@pytest.mark.parametrize(
    "source_code",
    [
        pytest.param('get_feature("my_flag")', id="get_feature"),
        pytest.param("read_flag('my_flag')", id="read_flag"),
        pytest.param('is_feature_enabled("my_flag")', id="is_feature_enabled"),
        pytest.param('hasFeature("my_flag")', id="hasFeature"),
        pytest.param('check_flag("my_flag")', id="check_flag"),
    ],
)
def test_scan_code_references__flag_referenced__yields_code_reference(
    tmp_path: Path,
    mocker: MockerFixture,
    source_code: str,
) -> None:
    # Given
    (tmp_path / "app.py").write_text(source_code)
    mocker.patch("subprocess.run").return_value.stdout = "app.py"

    # When
    results = list(scan_code_references(["my_flag"], tmp_path))

    # Then
    assert results == [
        {"feature_name": "my_flag", "file_path": "app.py", "line_number": 1},
    ]


def test_scan_code_references__multiline_reference__yields_code_reference(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Given
    (tmp_path / "app.py").write_text(
        dedent("""\
        get_feature(
            "my_flag"
        )
    """),
    )
    mocker.patch("subprocess.run").return_value.stdout = "app.py"

    # When
    results = list(scan_code_references(["my_flag"], tmp_path))

    # Then
    assert results == [
        {"feature_name": "my_flag", "file_path": "app.py", "line_number": 2},
    ]


@pytest.mark.parametrize(
    "source_code",
    [
        pytest.param('get_feature("other_flag")', id="different_flag"),
        pytest.param('"my_flag" in config', id="string_literal"),
        pytest.param("my_flag = True", id="variable_name"),
    ],
)
def test_scan_code_references__flag_not_referenced__yields_nothing(
    tmp_path: Path,
    mocker: MockerFixture,
    source_code: str,
) -> None:
    # Given
    (tmp_path / "app.py").write_text(source_code)
    mocker.patch("subprocess.run").return_value.stdout = "app.py"

    # When
    results = list(scan_code_references(["my_flag"], tmp_path))

    # Then
    assert results == []


def test_scan_code_references__untracked_file__skips_file(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Given
    (tmp_path / "tracked.py").write_text('get_feature("my_flag")')
    (tmp_path / "untracked.py").write_text('get_feature("my_flag")')
    mocker.patch("subprocess.run").return_value.stdout = "tracked.py"

    # When
    results = list(scan_code_references(["my_flag"], tmp_path))

    # Then
    assert results == [
        {"feature_name": "my_flag", "file_path": "tracked.py", "line_number": 1},
    ]


def test_scan_code_references__nonexistent_file__skips_file(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Given
    (tmp_path / "app.py").write_text('get_feature("my_flag")')
    mocker.patch("subprocess.run").return_value.stdout = "app.py\ndeleted.py"

    # When
    results = list(scan_code_references(["my_flag"], tmp_path))

    # Then
    assert results == [
        {"feature_name": "my_flag", "file_path": "app.py", "line_number": 1},
    ]


def test_scan_code_references__binary_file__skips_file(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Given
    (tmp_path / "app.py").write_text('get_feature("my_flag")')
    (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02")
    mocker.patch("subprocess.run").return_value.stdout = "app.py\nbinary.bin"

    # When
    results = list(scan_code_references(["my_flag"], tmp_path))

    # Then
    assert results == [
        {"feature_name": "my_flag", "file_path": "app.py", "line_number": 1},
    ]


def test_scan_code_references__multiple_flags__yields_all(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Given
    (tmp_path / "app.py").write_text(
        dedent("""\
        get_feature("flag_a")
        is_flag_enabled("flag_b")
    """),
    )
    mocker.patch("subprocess.run").return_value.stdout = "app.py"

    # When
    results = list(scan_code_references(["flag_a", "flag_b"], tmp_path))

    # Then
    assert sorted(results, key=lambda r: r["line_number"]) == [
        {"feature_name": "flag_a", "file_path": "app.py", "line_number": 1},
        {"feature_name": "flag_b", "file_path": "app.py", "line_number": 2},
    ]


def test_main__with_references__prints_and_outputs(
    tmp_path: Path,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given
    (tmp_path / "app.py").write_text('get_feature("my_flag")')
    github_output = tmp_path / "github_output"
    github_output.touch()

    mocker.patch("subprocess.run").return_value.stdout = "app.py"
    mocker.patch.dict(
        "os.environ",
        {
            "FEATURE_NAMES": '["my_flag"]',
            "GIT_REPOSITORY_PATH": str(tmp_path),
            "GITHUB_OUTPUT": str(github_output),
        },
    )

    # When
    main()

    # Then
    captured = capsys.readouterr()
    assert "Feature: my_flag" in captured.out
    assert "app.py:1" in captured.out
    assert "code_references=" in github_output.read_text()


def test_main__no_references__prints_message(
    tmp_path: Path,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given
    (tmp_path / "app.py").write_text("# no flags here")

    mocker.patch("subprocess.run").return_value.stdout = "app.py"
    mocker.patch.dict(
        "os.environ",
        {
            "FEATURE_NAMES": '["my_flag"]',
            "GIT_REPOSITORY_PATH": str(tmp_path),
        },
        clear=True,
    )

    # When
    main()

    # Then
    captured = capsys.readouterr()
    assert "No code references found." in captured.out


def test_main__invalid_repository_path__raises_system_exit(
    mocker: MockerFixture,
) -> None:
    # Given
    mocker.patch.dict(
        "os.environ",
        {
            "FEATURE_NAMES": '["my_flag"]',
            "GIT_REPOSITORY_PATH": "/nonexistent/path",
        },
    )

    # When / Then
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert "not a directory" in str(exc_info.value)
