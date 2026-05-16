"""Tests for admin cache-stats command."""

import json

SAMPLE_CACHE_STATS = {
    "total_hits": 1250,
    "total_misses": 340,
    "hit_rate": 78.6,
    "keys_cached": 42,
}


def test_cache_stats(invoke, mock_api):
    mock_api.get("/api/v1/admin/debug/cache-stats").respond(200, json=SAMPLE_CACHE_STATS)
    result = invoke(["admin", "cache-stats"])
    assert result.exit_code == 0
    assert "Cache Statistics" in result.output
    assert "1250" in result.output


def test_cache_stats_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/debug/cache-stats").respond(200, json=SAMPLE_CACHE_STATS)
    result = invoke(["admin", "cache-stats", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["total_hits"] == 1250
    assert parsed["hit_rate"] == 78.6


def test_cache_stats_api_error(invoke, mock_api):
    """API 500 returns exit code 1."""
    mock_api.get("/api/v1/admin/debug/cache-stats").respond(500, json={"detail": "Internal error"})
    result = invoke(["admin", "cache-stats"])
    assert result.exit_code == 1
    assert "500" in result.output


def test_cache_stats_api_error_json(invoke, mock_api):
    """API error with --json returns structured JSON error."""
    mock_api.get("/api/v1/admin/debug/cache-stats").respond(500, json={"detail": "Internal error"})
    result = invoke(["admin", "cache-stats", "--json"])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 500
