from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture
from requests import HTTPError

from code_references.cli.upload_code_references import main, upload_code_references
from code_references.types import CodeReferenceSubmit


def test_upload_code_references__empty_list__skips_api_call(
    mocker: MockerFixture,
) -> None:
    # Given
    mock_post = mocker.patch("code_references.cli.upload_code_references.requests.post")

    # When
    result = upload_code_references(
        [],
        api_url="https://api.flagsmith.com",
        api_key="ser.test_key",
        project_id="123",
        repository_url="https://github.com/acme/repo",
        revision="abc123",
    )

    # Then
    assert result == 0
    mock_post.assert_not_called()


def test_upload_code_references__posts_references_to_api(
    mocker: MockerFixture,
) -> None:
    # Given
    mock_response = Mock()
    mock_post = mocker.patch(
        "code_references.cli.upload_code_references.requests.post",
        return_value=mock_response,
    )
    references: list[CodeReferenceSubmit] = [
        {"feature_name": "flag_a", "file_path": "app.py", "line_number": 10},
    ]

    # When
    result = upload_code_references(
        references,
        api_url="https://api.flagsmith.com",
        api_key="ser.test_key",
        project_id="123",
        repository_url="https://github.com/acme/repo",
        revision="abc123",
    )

    # Then
    assert result == 1
    mock_post.assert_called_once_with(
        "https://api.flagsmith.com/api/v1/projects/123/code-references/",
        headers={"Authorization": "Api-Key ser.test_key"},
        json={
            "repository_url": "https://github.com/acme/repo",
            "revision": "abc123",
            "code_references": references,
        },
    )


def test_upload_code_references__api_error__raises(mocker: MockerFixture) -> None:
    # Given
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = HTTPError("401")
    mocker.patch(
        "code_references.cli.upload_code_references.requests.post",
        return_value=mock_response,
    )

    references: list[CodeReferenceSubmit] = [
        {"feature_name": "f", "file_path": "a.py", "line_number": 1},
    ]

    # When / Then
    with pytest.raises(HTTPError):
        upload_code_references(
            references,
            api_url="https://api.flagsmith.com",
            api_key="bad_key",
            project_id="123",
            repository_url="https://github.com/acme/repo",
            revision="abc123",
        )


def test_main__with_references__uploads_and_prints(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given
    references = '[{"feature_name": "flag_a", "file_path": "app.py", "line_number": 1}]'
    monkeypatch.setenv("CODE_REFERENCES", references)
    monkeypatch.setenv("FLAGSMITH_ADMIN_API_URL", "https://api.flagsmith.com")
    monkeypatch.setenv("FLAGSMITH_ADMIN_API_KEY", "ser.test_key")
    monkeypatch.setenv("FLAGSMITH_PROJECT_ID", "123")
    monkeypatch.setenv("REPOSITORY_URL", "https://github.com/acme/repo")
    monkeypatch.setenv("REVISION", "abc123")

    mock_response = Mock()
    mocker.patch(
        "code_references.cli.upload_code_references.requests.post",
        return_value=mock_response,
    )

    # When
    main()

    # Then
    captured = capsys.readouterr()
    assert "Uploaded 1 code references." in captured.out


def test_main__no_references__prints_message(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given
    monkeypatch.setenv("CODE_REFERENCES", "[]")
    monkeypatch.setenv("FLAGSMITH_ADMIN_API_URL", "https://api.flagsmith.com")
    monkeypatch.setenv("FLAGSMITH_ADMIN_API_KEY", "ser.test_key")
    monkeypatch.setenv("FLAGSMITH_PROJECT_ID", "123")
    monkeypatch.setenv("REPOSITORY_URL", "https://github.com/acme/repo")
    monkeypatch.setenv("REVISION", "abc123")

    mock_post = mocker.patch("code_references.cli.upload_code_references.requests.post")

    # When
    main()

    # Then
    captured = capsys.readouterr()
    assert "No code references to upload." in captured.out
    mock_post.assert_not_called()
