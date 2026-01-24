from pathlib import Path
from unittest.mock import Mock

from pytest_mock import MockerFixture

from code_references.fetch import fetch_feature_names, main


def test_fetch_feature_names__returns_names_from_api(
    mocker: MockerFixture,
) -> None:
    # Given
    mock_response = Mock()
    mock_response.json.return_value = {
        "results": [{"name": "flag_a"}, {"name": "flag_b"}],
    }
    mock_get = mocker.patch(
        "code_references.fetch.requests.get",
        return_value=mock_response,
    )

    # When
    result = fetch_feature_names(
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


def test_main__outputs_feature_names(
    tmp_path: Path,
    monkeypatch,
    mocker: MockerFixture,
    capsys,
) -> None:
    # Given
    github_output = tmp_path / "github_output"
    github_output.touch()

    monkeypatch.setenv("FLAGSMITH_ADMIN_API_URL", "https://api.flagsmith.com")
    monkeypatch.setenv("FLAGSMITH_ADMIN_API_KEY", "ser.test_key")
    monkeypatch.setenv("FLAGSMITH_PROJECT_ID", "123")
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))

    mock_response = Mock()
    mock_response.json.return_value = {
        "results": [{"name": "flag_a"}, {"name": "flag_b"}],
    }
    mocker.patch("code_references.fetch.requests.get", return_value=mock_response)

    # When
    main()

    # Then
    captured = capsys.readouterr()
    assert "Fetched 2 feature names." in captured.out
    assert 'feature_names=["flag_a", "flag_b"]' in github_output.read_text()
