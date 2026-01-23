from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture
from requests import HTTPError

from code_references.upload import upload_code_references


def test_upload_code_references__empty_list__skips_api_call(
    mocker: MockerFixture,
) -> None:
    # Given
    mock_post = mocker.patch("code_references.upload.requests.post")

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
        "code_references.upload.requests.post",
        return_value=mock_response,
    )
    references = [
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
        "code_references.upload.requests.post",
        return_value=mock_response,
    )

    # When / Then
    with pytest.raises(HTTPError):
        upload_code_references(
            [{"feature_name": "f", "file_path": "a.py", "line_number": 1}],
            api_url="https://api.flagsmith.com",
            api_key="bad_key",
            project_id="123",
            repository_url="https://github.com/acme/repo",
            revision="abc123",
        )
