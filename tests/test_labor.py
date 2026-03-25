"""労務コンプライアンスチェックサービスのテスト."""

import pytest

from app.models import (
    Article36Agreement,
    CompanyProfile,
    CompanySize,
    ComplianceReport,
    Industry,
    LaborConditions,
    RiskLevel,
)
from app.services.labor_compliance import (
    _check_article36,
    _check_childcare_nursing,
    _check_equal_pay,
    _check_harassment,
    _check_leave_and_welfare,
    _check_safety_health,
    _check_working_hours,
    check_compliance,
    get_checked_law_names,
)


@pytest.fixture
def good_conditions() -> LaborConditions:
    return LaborConditions(
        weekly_hours=40.0,
        overtime_monthly_avg=20.0,
        overtime_monthly_max=40.0,
        has_health_check=True,
        has_stress_check=True,
        has_harassment_policy=True,
        has_childcare_leave=True,
        has_nursing_care_leave=True,
        has_equal_pay_policy=True,
        paid_leave_days=20,
        paid_leave_taken_rate=0.7,
        article36=Article36Agreement(has_agreement=True),
    )


@pytest.fixture
def bad_conditions() -> LaborConditions:
    return LaborConditions(
        weekly_hours=50.0,
        overtime_monthly_avg=80.0,
        overtime_monthly_max=120.0,
        has_health_check=False,
        has_stress_check=False,
        has_harassment_policy=False,
        has_childcare_leave=False,
        has_nursing_care_leave=False,
        has_equal_pay_policy=False,
        paid_leave_days=5,
        paid_leave_taken_rate=0.2,
        article36=None,
    )


@pytest.fixture
def large_company() -> CompanyProfile:
    return CompanyProfile(
        name="大企業", size=CompanySize.LARGE,
        industry=Industry.IT, employee_count=500,
    )


# ---------------------------------------------------------------------------
# _check_working_hours
# ---------------------------------------------------------------------------

class TestCheckWorkingHours:
    def test_normal_hours_no_issues(self) -> None:
        cond = LaborConditions(weekly_hours=40.0, overtime_monthly_max=30.0)
        issues = _check_working_hours(cond)
        assert len(issues) == 0

    def test_over_40_hours_critical(self) -> None:
        cond = LaborConditions(weekly_hours=45.0)
        issues = _check_working_hours(cond)
        assert any(i.risk_level == RiskLevel.CRITICAL for i in issues)

    def test_overtime_over_100_critical(self) -> None:
        cond = LaborConditions(overtime_monthly_max=110.0)
        issues = _check_working_hours(cond)
        assert any(i.risk_level == RiskLevel.CRITICAL for i in issues)

    def test_overtime_over_80_high(self) -> None:
        cond = LaborConditions(overtime_monthly_max=90.0)
        issues = _check_working_hours(cond)
        assert any(i.risk_level == RiskLevel.HIGH for i in issues)

    def test_overtime_over_45_medium(self) -> None:
        cond = LaborConditions(overtime_monthly_max=50.0)
        issues = _check_working_hours(cond)
        assert any(i.risk_level == RiskLevel.MEDIUM for i in issues)

    def test_overtime_45_no_issue(self) -> None:
        cond = LaborConditions(overtime_monthly_max=45.0)
        issues = _check_working_hours(cond)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# _check_article36
# ---------------------------------------------------------------------------

class TestCheckArticle36:
    def test_none_returns_medium(self) -> None:
        issues = _check_article36(None)
        assert len(issues) == 1
        assert issues[0].risk_level == RiskLevel.MEDIUM

    def test_no_agreement_critical(self) -> None:
        a36 = Article36Agreement(has_agreement=False)
        issues = _check_article36(a36)
        assert any(i.risk_level == RiskLevel.CRITICAL for i in issues)

    def test_valid_agreement_no_issues(self) -> None:
        a36 = Article36Agreement(has_agreement=True, overtime_limit_monthly=45, overtime_limit_yearly=360)
        issues = _check_article36(a36)
        assert len(issues) == 0

    def test_monthly_over_45_high(self) -> None:
        a36 = Article36Agreement(has_agreement=True, overtime_limit_monthly=50)
        issues = _check_article36(a36)
        assert any(i.risk_level == RiskLevel.HIGH for i in issues)

    def test_yearly_over_360_high(self) -> None:
        a36 = Article36Agreement(has_agreement=True, overtime_limit_yearly=400)
        issues = _check_article36(a36)
        assert any(i.risk_level == RiskLevel.HIGH for i in issues)

    def test_special_clause_over_720_critical(self) -> None:
        a36 = Article36Agreement(
            has_agreement=True, special_clause=True, special_limit_yearly=800,
        )
        issues = _check_article36(a36)
        assert any(i.risk_level == RiskLevel.CRITICAL for i in issues)

    def test_special_clause_monthly_100_critical(self) -> None:
        a36 = Article36Agreement(
            has_agreement=True, special_clause=True, special_limit_monthly=100,
        )
        issues = _check_article36(a36)
        assert any(i.risk_level == RiskLevel.CRITICAL for i in issues)

    def test_special_clause_over_6_months_critical(self) -> None:
        a36 = Article36Agreement(
            has_agreement=True, special_clause=True, special_months_per_year=7,
        )
        issues = _check_article36(a36)
        assert any(i.risk_level == RiskLevel.CRITICAL for i in issues)


# ---------------------------------------------------------------------------
# _check_leave_and_welfare
# ---------------------------------------------------------------------------

class TestCheckLeaveAndWelfare:
    def test_insufficient_leave_high(self) -> None:
        cond = LaborConditions(paid_leave_days=5)
        issues = _check_leave_and_welfare(cond)
        assert any(i.risk_level == RiskLevel.HIGH for i in issues)

    def test_low_taken_rate_high(self) -> None:
        cond = LaborConditions(paid_leave_days=20, paid_leave_taken_rate=0.3)
        issues = _check_leave_and_welfare(cond)
        assert any(i.risk_level == RiskLevel.HIGH for i in issues)

    def test_good_leave_no_issues(self) -> None:
        cond = LaborConditions(paid_leave_days=20, paid_leave_taken_rate=0.7)
        issues = _check_leave_and_welfare(cond)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# _check_safety_health
# ---------------------------------------------------------------------------

class TestCheckSafetyHealth:
    def test_no_health_check_critical(self) -> None:
        cond = LaborConditions(has_health_check=False)
        issues = _check_safety_health(cond, None)
        assert any(i.risk_level == RiskLevel.CRITICAL for i in issues)

    def test_large_no_stress_check_high(self, large_company: CompanyProfile) -> None:
        cond = LaborConditions(has_stress_check=False)
        issues = _check_safety_health(cond, large_company)
        assert any(i.risk_level == RiskLevel.HIGH for i in issues)

    def test_small_no_stress_check_ok(self) -> None:
        small = CompanyProfile(name="X", size=CompanySize.SMALL, industry=Industry.IT, employee_count=30)
        cond = LaborConditions(has_stress_check=False)
        issues = _check_safety_health(cond, small)
        # 50人未満なのでストレスチェック義務なし
        assert not any("ストレスチェック" in i.description for i in issues)


# ---------------------------------------------------------------------------
# Other checks
# ---------------------------------------------------------------------------

class TestOtherChecks:
    def test_no_childcare_leave_high(self) -> None:
        cond = LaborConditions(has_childcare_leave=False)
        issues = _check_childcare_nursing(cond)
        assert any(i.risk_level == RiskLevel.HIGH for i in issues)

    def test_no_nursing_leave_medium(self) -> None:
        cond = LaborConditions(has_nursing_care_leave=False)
        issues = _check_childcare_nursing(cond)
        assert any(i.risk_level == RiskLevel.MEDIUM for i in issues)

    def test_no_harassment_policy_high(self) -> None:
        cond = LaborConditions(has_harassment_policy=False)
        issues = _check_harassment(cond)
        assert any(i.risk_level == RiskLevel.HIGH for i in issues)

    def test_no_equal_pay_medium(self) -> None:
        cond = LaborConditions(has_equal_pay_policy=False)
        issues = _check_equal_pay(cond)
        assert any(i.risk_level == RiskLevel.MEDIUM for i in issues)


# ---------------------------------------------------------------------------
# check_compliance (integration)
# ---------------------------------------------------------------------------

class TestCheckCompliance:
    def test_returns_report(self, good_conditions: LaborConditions) -> None:
        report = check_compliance(good_conditions)
        assert isinstance(report, ComplianceReport)

    def test_bad_conditions_has_criticals(self, bad_conditions: LaborConditions) -> None:
        report = check_compliance(bad_conditions)
        assert report.critical_count > 0

    def test_good_conditions_no_criticals(self, good_conditions: LaborConditions) -> None:
        report = check_compliance(good_conditions)
        assert report.critical_count == 0

    def test_sorted_by_risk(self, bad_conditions: LaborConditions) -> None:
        report = check_compliance(bad_conditions)
        risk_order = {RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 3, RiskLevel.INFO: 4}
        levels = [risk_order[i.risk_level] for i in report.issues]
        assert levels == sorted(levels)

    def test_with_profile(self, good_conditions: LaborConditions, large_company: CompanyProfile) -> None:
        report = check_compliance(good_conditions, large_company)
        assert report.company_name == "大企業"

    def test_without_profile(self, good_conditions: LaborConditions) -> None:
        report = check_compliance(good_conditions)
        assert report.company_name == "未指定"

    def test_checked_laws_not_empty(self, good_conditions: LaborConditions) -> None:
        report = check_compliance(good_conditions)
        assert len(report.checked_laws) > 0

    def test_get_checked_law_names(self) -> None:
        names = get_checked_law_names()
        assert len(names) > 0
