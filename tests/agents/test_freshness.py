from datetime import datetime, timedelta, timezone

import pytest

from src.agents.state import CaseState, Freshness, PolicyMatch

NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def aged(kind, days, **kw):
    return Freshness(kind=kind, subject="s", as_of=NOW - timedelta(days=days), source="test", **kw)


@pytest.mark.parametrize(
    "kind,days,expected",
    [
        ("member_eligibility", 10, "fresh"),
        ("member_eligibility", 23, "aging"),  # >= 0.75 * 30
        ("member_eligibility", 31, "stale"),
        ("provider_affiliation", 181, "stale"),
        ("policy", 300, "aging"),
        ("clinical_evidence", 30, "fresh"),
    ],
)
def test_status_uses_kind_default_limit(kind, days, expected):
    assert aged(kind, days).status(NOW) == expected


def test_explicit_max_age_overrides_default():
    assert aged("policy", 40, max_age_days=30).status(NOW) == "stale"


def test_unknown_when_no_date_and_action_present():
    f = Freshness.unknown("provider_affiliation", "physician_information", note="no NPI")
    assert f.status(NOW) == "unknown"
    assert f.age_days(NOW) is None
    assert f.action()


def test_naive_datetime_treated_as_utc_and_future_clamped():
    naive = Freshness(kind="policy", subject="p", as_of=datetime(2026, 5, 31))
    assert naive.age_days(NOW) == 1
    future = Freshness(kind="policy", subject="p", as_of=NOW + timedelta(days=5))
    assert future.age_days(NOW) == 0
    assert future.status(NOW) == "fresh"


@pytest.mark.parametrize(
    "value",
    ["2026-05-01T10:00:00Z", "2026-05-01T10:00:00.1234567Z", "2026-05-01T10:00:00.5+00:00"],
)
def test_from_value_parses_search_timestamps(value):
    f = Freshness.from_value("policy", "p", value, "search.last_modified")
    assert f.as_of is not None
    assert f.age_days(NOW) == 30
    assert f.source == "search.last_modified"


def test_from_value_bad_string_is_unknown():
    f = Freshness.from_value("policy", "p", "not a date", "search.last_modified")
    assert f.status(NOW) == "unknown"
    assert "search.last_modified" in f.note


def test_report_shape():
    r = aged("policy", 400).report(NOW)
    assert r["status"] == "stale"
    assert r["age_days"] == 400
    assert r["max_age_days"] == 365
    assert r["as_of"].startswith("2025-")
    assert set(r) == {
        "kind", "subject", "as_of", "age_days", "max_age_days", "status", "source", "note", "action",
    }


def test_ensure_defaults_is_idempotent_and_only_for_present_sections():
    state = CaseState(case_id="c", physician_information={"physician_name": "Dr. X"})
    state.ensure_freshness_defaults()
    state.ensure_freshness_defaults()
    assert [f.kind for f in state.freshness] == ["provider_affiliation"]


def test_ensure_defaults_keeps_verified_entries():
    state = CaseState(case_id="c", patient_information={"patient_name": "A"})
    state.freshness.append(aged("member_eligibility", 2))
    state.ensure_freshness_defaults()
    assert len(state.freshness) == 1
    assert state.freshness[0].status(NOW) == "fresh"


def test_stale_signals_include_policy_freshness():
    state = CaseState(
        case_id="c",
        policies=[PolicyMatch(blob_url="u", freshness=aged("policy", 500))],
        freshness=[aged("clinical_evidence", 5), Freshness.unknown("member_eligibility", "p")],
    )
    assert [f.kind for f in state.stale_signals(NOW)] == ["policy"]
    flagged = state.stale_signals(NOW, include_unknown=True)
    assert {f.kind for f in flagged} == {"policy", "member_eligibility"}
    assert len(state.freshness_report(NOW)) == 3
