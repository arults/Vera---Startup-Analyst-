"""Unit tests for the fail-closed multi-source gate."""
from src.phase1d.multi_source_gate import check_multi_source_gate, assert_gate_or_raise

def test_missing_matrix_fails():
    result = check_multi_source_gate(None, "closure")
    assert not result.passed
    assert "missing_coverage_matrix" in result.reasons

def test_incomplete_matrix_fails():
    coverage = {"platform_regulatory": {"status": "searched"}}
    result = check_multi_source_gate(coverage, "closure")
    assert not result.passed
    assert any("not_searched" in r for r in result.reasons)

def test_complete_matrix_passes():
    coverage = {
        "platform_regulatory": {"status": "searched"},
        "independent_news": {"status": "searched"},
        "discussion_forums": {"status": "searched_not_found"},
        "youtube_longform": {"status": "searched_not_found"},
        "multi_engine": {
            "google": {"status": "searched"},
            "bing": {"status": "searched"},
            "duckduckgo": {"status": "searched"},
        },
    }
    result = check_multi_source_gate(coverage, "closure")
    assert result.passed
    assert result.reasons == ()

def test_assert_raises_on_fail():
    try:
        assert_gate_or_raise(None, "closure")
        assert False, "should have raised"
    except ValueError as e:
        assert "multi_source_gate_failed" in str(e)
