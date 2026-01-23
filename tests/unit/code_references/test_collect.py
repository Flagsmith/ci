from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from code_references.collect import (
    CodeReference,
    find_references,
    main,
    retrieve_feature_names,
    should_skip_file,
)


def test_retrieve_feature_names__returns_names_from_api(
    mocker: MockerFixture,
) -> None:
    # Given
    mock_response = Mock()
    mock_response.json.return_value = {
        "results": [{"name": "flag_a"}, {"name": "flag_b"}],
    }
    mock_get = mocker.patch(
        "code_references.collect.requests.get",
        return_value=mock_response,
    )

    # When
    result = retrieve_feature_names(
        api_url="https://api.flagsmith.com",
        api_key="ser.test_key",
        project_id="123",
    )

    # Then
    assert result == ["flag_a", "flag_b"]
    mock_get.assert_called_once_with(
        "https://api.flagsmith.com/api/v1/projects/123/features/?page_size=1000",
        headers={"Authorization": "Api-Key ser.test_key"},
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
def test_find_references__flag_referenced__yields_code_reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_code: str,
) -> None:
    # Given
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text(source_code)

    # When
    results = list(find_references(["my_flag"]))

    # Then
    assert results == [
        CodeReference(feature_name="my_flag", file_path="app.py", line_number=1),
    ]


def test_find_references__multiline_reference__yields_code_reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text(
        dedent("""\
        get_feature(
            "my_flag"
        )
    """),
    )

    # When
    results = list(find_references(["my_flag"]))

    # Then
    assert results == [
        CodeReference(feature_name="my_flag", file_path="app.py", line_number=2),
    ]


@pytest.mark.parametrize(
    "source_code",
    [
        pytest.param('get_feature("other_flag")', id="different_flag"),
        pytest.param('"my_flag" in config', id="string_literal"),
        pytest.param("my_flag = True", id="variable_name"),
    ],
)
def test_find_references__flag_not_referenced__yields_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_code: str,
) -> None:
    # Given
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text(source_code)

    # When
    results = list(find_references(["my_flag"]))

    # Then
    assert results == []


def test_find_references__excluded_path__skips_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    monkeypatch.chdir(tmp_path)
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "app.py").write_text('get_feature("my_flag")')

    # When
    results = list(find_references(["my_flag"], exclude_patterns=["venv"]))

    # Then
    assert results == []


def test_find_references__directory__skips(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    monkeypatch.chdir(tmp_path)
    (tmp_path / "subdir").mkdir()
    (tmp_path / "app.py").write_text('get_feature("my_flag")')

    # When
    results = list(find_references(["my_flag"]))

    # Then
    assert results == [
        CodeReference(feature_name="my_flag", file_path="app.py", line_number=1),
    ]


@pytest.mark.parametrize(
    "exclude_patterns",
    [
        pytest.param([], id="empty_list"),
        pytest.param([""], id="list_with_empty_string"),
    ],
)
def test_find_references__empty_exclude_patterns__finds_references(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exclude_patterns: list[str],
) -> None:
    # Given
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text('get_feature("my_flag")')

    # When
    results = list(find_references(["my_flag"], exclude_patterns=exclude_patterns))

    # Then
    assert results == [
        CodeReference(feature_name="my_flag", file_path="app.py", line_number=1),
    ]


def test_find_references__multiple_flags__yields_all(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text(
        dedent("""\
        get_feature("flag_a")
        is_flag_enabled("flag_b")
    """),
    )

    # When
    results = set(find_references(["flag_a", "flag_b"]))

    # Then
    assert results == {
        CodeReference(feature_name="flag_a", file_path="app.py", line_number=1),
        CodeReference(feature_name="flag_b", file_path="app.py", line_number=2),
    }


def test_main__with_references__prints_and_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text('get_feature("my_flag")')
    github_output = tmp_path / "github_output"
    github_output.touch()

    monkeypatch.setenv("FLAGSMITH_ADMIN_API_URL", "https://api.flagsmith.com")
    monkeypatch.setenv("FLAGSMITH_ADMIN_API_KEY", "ser.test_key")
    monkeypatch.setenv("FLAGSMITH_PROJECT_ID", "123")
    monkeypatch.setenv("EXCLUDE_PATTERNS", "")
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))

    mock_response = Mock()
    mock_response.json.return_value = {"results": [{"name": "my_flag"}]}
    mocker.patch("code_references.collect.requests.get", return_value=mock_response)

    # When
    main()

    # Then
    captured = capsys.readouterr()
    assert "Feature: my_flag" in captured.out
    assert "app.py:1" in captured.out
    assert "code_references=" in github_output.read_text()


def test_main__no_references__prints_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("# no flags here")

    monkeypatch.setenv("FLAGSMITH_ADMIN_API_URL", "https://api.flagsmith.com")
    monkeypatch.setenv("FLAGSMITH_ADMIN_API_KEY", "ser.test_key")
    monkeypatch.setenv("FLAGSMITH_PROJECT_ID", "123")
    monkeypatch.setenv("EXCLUDE_PATTERNS", "")
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    mock_response = Mock()
    mock_response.json.return_value = {"results": [{"name": "my_flag"}]}
    mocker.patch("code_references.collect.requests.get", return_value=mock_response)

    # When
    main()

    # Then
    captured = capsys.readouterr()
    assert "No code references found." in captured.out
