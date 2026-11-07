import pytest
from pydantic import ValidationError

from app.api.knowledge import RuleCreate
from app.models.entities import ClaimFinding, Rule


def test_rule_api_accepts_only_current_severity_values():
    assert RuleCreate(title="Evidence", text="Use source documents.").severity == "major"
    for severity in ("critical", "major", "advisory"):
        assert RuleCreate(
            title="Evidence",
            text="Use source documents.",
            severity=severity,
        ).severity == severity
    with pytest.raises(ValidationError):
        RuleCreate(
            title="Evidence",
            text="Use source documents.",
            severity="warning",
        )


def test_models_normalize_legacy_severity_without_storing_warning():
    assert Rule(severity="warning").severity == "major"
    assert ClaimFinding(severity="warning").severity == "major"
    with pytest.raises(ValueError, match="critical, major, or advisory"):
        Rule(severity="urgent")
