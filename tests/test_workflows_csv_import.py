"""Tests for workflow csv-parse command."""

import json

SAMPLE_PARSE_RESPONSE = {
    "companies": [
        {
            "name": "Acme Corp",
            "website": "https://acme.com",
            "industry": "SaaS",
            "location": "SF",
            "source_type": "csv",
        },
        {
            "name": "Beta Inc",
            "website": None,
            "industry": "Fintech",
            "location": "NYC",
            "source_type": "crm",
        },
    ],
    "total_rows": 2,
    "truncated": False,
}


def test_csv_parse(invoke, mock_api, tmp_path):
    mock_api.post("/api/v1/workflows/csv/parse-companies").respond(200, json=SAMPLE_PARSE_RESPONSE)
    csv_file = tmp_path / "companies.csv"
    csv_file.write_text(
        "name,website,industry\nAcme Corp,https://acme.com,SaaS\nBeta Inc,,Fintech\n"
    )
    result = invoke(["workflows", "csv-parse", str(csv_file)])
    assert result.exit_code == 0
    assert "Acme Corp" in result.output
    assert "Parsed 2 rows" in result.output


def test_csv_parse_json(invoke, mock_api, tmp_path):
    mock_api.post("/api/v1/workflows/csv/parse-companies").respond(200, json=SAMPLE_PARSE_RESPONSE)
    csv_file = tmp_path / "companies.csv"
    csv_file.write_text("name,website\nAcme Corp,https://acme.com\n")
    result = invoke(["workflows", "csv-parse", str(csv_file), "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert len(parsed["companies"]) == 2
    assert parsed["total_rows"] == 2


def test_csv_parse_file_not_found(invoke, mock_api):
    result = invoke(["workflows", "csv-parse", "/nonexistent/file.csv"])
    assert result.exit_code == 1
    assert "File not found" in result.output


def test_csv_parse_not_csv(invoke, mock_api, tmp_path):
    txt_file = tmp_path / "data.txt"
    txt_file.write_text("some data")
    result = invoke(["workflows", "csv-parse", str(txt_file)])
    assert result.exit_code == 1
    assert ".csv" in result.output


def test_csv_parse_api_error(invoke, mock_api, tmp_path):
    """API 400 returns exit code 1."""
    mock_api.post("/api/v1/workflows/csv/parse-companies").respond(
        400, json={"detail": "CSV must include a name column"}
    )
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("email,phone\na@b.com,123\n")
    result = invoke(["workflows", "csv-parse", str(csv_file)])
    assert result.exit_code == 1
    assert "400" in result.output


def test_csv_parse_api_error_json(invoke, mock_api, tmp_path):
    """API error with --json returns structured JSON error."""
    mock_api.post("/api/v1/workflows/csv/parse-companies").respond(
        400, json={"detail": "CSV must include a name column"}
    )
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("email,phone\na@b.com,123\n")
    result = invoke(["workflows", "csv-parse", str(csv_file), "--json"])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 400
