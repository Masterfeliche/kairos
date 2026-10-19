"""Extraction tests against the real source PDF (Phase 2 DoD)."""
from __future__ import annotations

import pytest

from app.extraction import normalise, parse_pdf, session_identity_key, validate_session


@pytest.fixture(scope="module")
def parsed(pdf_path):
    return parse_pdf(pdf_path)


def test_volume(parsed):
    assert len(parsed) > 1900
    with_code = [s for s in parsed if s.course_code]
    assert len(with_code) >= 1800


def test_page2_known_sessions(parsed):
    page2 = [s for s in parsed if s.page == 2]
    by_day_time = {(s.day, s.start_time): s for s in page2}
    expected = {
        ("Tuesday", "08:00"): "CEU 08109",
        ("Thursday", "10:00"): "CEU 08111",
        ("Tuesday", "11:00"): "CEU 08108",
        ("Wednesday", "12:00"): "CEU 08116",
        ("Thursday", "12:00"): "CEU 08113",
        ("Tuesday", "13:00"): "CEU 08115",
        ("Friday", "16:00"): "CEU 08104",
        ("Tuesday", "17:00"): "CEU 08106",
    }
    for key, code in expected.items():
        assert key in by_day_time, f"missing {key}"
        assert by_day_time[key].course_code == code


def test_page147_shared_session(parsed):
    shared = [s for s in parsed if s.page == 147 and len(s.cohorts) > 1]
    assert shared, "expected a shared-cohort session on page 147"
    assert any("OD26CST-1" in s.cohorts and "OD26ERE-1" in s.cohorts for s in shared)


def test_g_prefixed_codes_parsed(parsed):
    codes = {s.course_code for s in parsed}
    assert any(c and c.split()[1].startswith("G") for c in codes)


def test_multi_hour_blocks_detected(parsed):
    multi = [s for s in parsed if s.multi_hour]
    assert multi, "expected some multi-hour (merged) sessions"
    for s in multi:
        assert s.end_time > s.start_time


def test_missing_code_is_flagged(parsed):
    for s in parsed:
        if not s.course_code:
            assert "MISSING_CODE" in s.reasons
            assert s.confidence == "low"


def test_normalise_and_validate(parsed):
    sample = next(s for s in parsed if s.course_code and s.cohorts)
    norm = normalise(sample)
    assert norm["day_of_week"] in (1, 2, 3, 4, 5)
    assert norm["start_time"] is not None
    assert norm["course_code_raw"] == norm["course_code_raw"].upper()
    assert session_identity_key(norm)
    issues = validate_session(norm)
    assert isinstance(issues, list)
