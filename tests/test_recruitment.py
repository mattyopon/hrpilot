"""採用計画サービスのテスト."""

import pytest

from app.models import (
    BusinessPlan,
    CompanyProfile,
    CompanySize,
    Industry,
    Position,
    RecruitmentPlan,
)
from app.services.recruitment_planner import (
    _estimate_headcount_needs,
    _generate_positions,
    _recommend_channels,
    create_recruitment_plan,
    generate_job_description,
)


@pytest.fixture
def it_startup() -> CompanyProfile:
    return CompanyProfile(
        name="AIスタートアップ", size=CompanySize.STARTUP,
        industry=Industry.IT, employee_count=25,
    )


@pytest.fixture
def large_mfg() -> CompanyProfile:
    return CompanyProfile(
        name="大手メーカー", size=CompanySize.LARGE,
        industry=Industry.MANUFACTURING, employee_count=700,
    )


@pytest.fixture
def basic_plan() -> BusinessPlan:
    return BusinessPlan(
        revenue_target=500000000,
        growth_rate=0.3,
        departments={"エンジニアリング": 10, "営業": 5},
        new_projects=["新規SaaS"],
        budget_for_hiring=10000000,
        timeline_months=12,
    )


@pytest.fixture
def empty_plan() -> BusinessPlan:
    return BusinessPlan(
        revenue_target=100000000,
        growth_rate=0.0,
        departments={},
        new_projects=[],
    )


# ---------------------------------------------------------------------------
# _estimate_headcount_needs
# ---------------------------------------------------------------------------

class TestEstimateHeadcountNeeds:
    def test_growth_based_needs(self, it_startup: CompanyProfile, basic_plan: BusinessPlan) -> None:
        needs = _estimate_headcount_needs(it_startup, basic_plan)
        assert "エンジニアリング" in needs
        assert needs["エンジニアリング"] > 0

    def test_new_project_needs(self, it_startup: CompanyProfile, basic_plan: BusinessPlan) -> None:
        needs = _estimate_headcount_needs(it_startup, basic_plan)
        assert "新規: 新規SaaS" in needs

    def test_startup_project_team_size(self, it_startup: CompanyProfile) -> None:
        plan = BusinessPlan(revenue_target=100000000, growth_rate=0.0, new_projects=["P1"])
        needs = _estimate_headcount_needs(it_startup, plan)
        assert needs["新規: P1"] == 2  # startup = 2

    def test_large_project_team_size(self, large_mfg: CompanyProfile) -> None:
        plan = BusinessPlan(revenue_target=100000000, growth_rate=0.0, new_projects=["P1"])
        needs = _estimate_headcount_needs(large_mfg, plan)
        assert needs["新規: P1"] == 7  # large = 7

    def test_zero_growth_no_dept_needs(self, it_startup: CompanyProfile, empty_plan: BusinessPlan) -> None:
        needs = _estimate_headcount_needs(it_startup, empty_plan)
        assert len(needs) == 0

    def test_negative_growth_no_needs(self, it_startup: CompanyProfile) -> None:
        plan = BusinessPlan(revenue_target=100000000, growth_rate=-0.1, departments={"X": 10})
        needs = _estimate_headcount_needs(it_startup, plan)
        assert len(needs) == 0


# ---------------------------------------------------------------------------
# _generate_positions
# ---------------------------------------------------------------------------

class TestGeneratePositions:
    def test_position_count(self, it_startup: CompanyProfile) -> None:
        needs = {"開発": 3, "営業": 2}
        positions = _generate_positions(it_startup, needs)
        assert len(positions) == 2

    def test_it_skills(self, it_startup: CompanyProfile) -> None:
        positions = _generate_positions(it_startup, {"開発": 3})
        assert "プログラミング" in positions[0].required_skills

    def test_finance_skills(self) -> None:
        p = CompanyProfile(name="X", size=CompanySize.MEDIUM, industry=Industry.FINANCE, employee_count=100)
        positions = _generate_positions(p, {"投資": 2})
        assert "金融知識" in positions[0].required_skills

    def test_manufacturing_skills(self, large_mfg: CompanyProfile) -> None:
        positions = _generate_positions(large_mfg, {"製造": 5})
        assert "品質管理" in positions[0].required_skills

    def test_retail_skills(self) -> None:
        p = CompanyProfile(name="X", size=CompanySize.SMALL, industry=Industry.RETAIL, employee_count=50)
        positions = _generate_positions(p, {"店舗": 3})
        assert "接客スキル" in positions[0].required_skills

    def test_healthcare_skills(self) -> None:
        p = CompanyProfile(name="X", size=CompanySize.MEDIUM, industry=Industry.HEALTHCARE, employee_count=200)
        positions = _generate_positions(p, {"看護": 4})
        assert "医療知識" in positions[0].required_skills

    def test_high_priority_for_large_headcount(self, it_startup: CompanyProfile) -> None:
        positions = _generate_positions(it_startup, {"開発": 10})
        assert positions[0].priority == "high"

    def test_low_priority_for_single(self, it_startup: CompanyProfile) -> None:
        positions = _generate_positions(it_startup, {"総務": 1})
        assert positions[0].priority == "low"


# ---------------------------------------------------------------------------
# _recommend_channels
# ---------------------------------------------------------------------------

class TestRecommendChannels:
    def test_returns_all_channels(self, it_startup: CompanyProfile) -> None:
        channels = _recommend_channels(it_startup, 5)
        assert len(channels) == 6

    def test_sorted_by_effectiveness(self, it_startup: CompanyProfile) -> None:
        channels = _recommend_channels(it_startup, 5)
        scores = [c.effectiveness_score for c in channels]
        assert scores == sorted(scores, reverse=True)

    def test_effectiveness_between_0_1(self, it_startup: CompanyProfile) -> None:
        channels = _recommend_channels(it_startup, 5)
        for c in channels:
            assert 0.0 <= c.effectiveness_score <= 1.0

    def test_startup_referral_boosted(self, it_startup: CompanyProfile) -> None:
        channels = _recommend_channels(it_startup, 5)
        referral = next(c for c in channels if c.channel.value == "referral")
        assert referral.effectiveness_score >= 0.85  # base 0.85 + 0.10 boost


# ---------------------------------------------------------------------------
# generate_job_description
# ---------------------------------------------------------------------------

class TestGenerateJobDescription:
    def test_contains_position_title(self, it_startup: CompanyProfile) -> None:
        pos = Position(title="エンジニア", department="開発", headcount=2)
        jd = generate_job_description(pos, it_startup)
        assert "エンジニア" in jd

    def test_contains_company_name(self, it_startup: CompanyProfile) -> None:
        pos = Position(title="営業", department="営業", headcount=1)
        jd = generate_job_description(pos, it_startup)
        assert "AIスタートアップ" in jd

    def test_contains_skills(self, it_startup: CompanyProfile) -> None:
        pos = Position(title="X", department="X", headcount=1, required_skills=["Python", "AI"])
        jd = generate_job_description(pos, it_startup)
        assert "Python" in jd
        assert "AI" in jd

    def test_no_skills(self, it_startup: CompanyProfile) -> None:
        pos = Position(title="X", department="X", headcount=1, required_skills=[])
        jd = generate_job_description(pos, it_startup)
        assert "特になし" in jd


# ---------------------------------------------------------------------------
# create_recruitment_plan (integration)
# ---------------------------------------------------------------------------

class TestCreateRecruitmentPlan:
    def test_returns_plan(self, it_startup: CompanyProfile, basic_plan: BusinessPlan) -> None:
        result = create_recruitment_plan(it_startup, basic_plan)
        assert isinstance(result, RecruitmentPlan)

    def test_plan_has_positions(self, it_startup: CompanyProfile, basic_plan: BusinessPlan) -> None:
        result = create_recruitment_plan(it_startup, basic_plan)
        assert len(result.positions) > 0

    def test_plan_has_channels(self, it_startup: CompanyProfile, basic_plan: BusinessPlan) -> None:
        result = create_recruitment_plan(it_startup, basic_plan)
        assert len(result.channel_recommendations) > 0

    def test_budget_constraint(self, it_startup: CompanyProfile) -> None:
        plan = BusinessPlan(
            revenue_target=500000000, growth_rate=0.5,
            departments={"開発": 50}, budget_for_hiring=1000000,
        )
        result = create_recruitment_plan(it_startup, plan)
        assert result.total_estimated_cost <= 1000000

    def test_summary_not_empty(self, it_startup: CompanyProfile, basic_plan: BusinessPlan) -> None:
        result = create_recruitment_plan(it_startup, basic_plan)
        assert len(result.summary) > 0

    def test_empty_plan_zero_cost(self, it_startup: CompanyProfile, empty_plan: BusinessPlan) -> None:
        result = create_recruitment_plan(it_startup, empty_plan)
        assert result.total_estimated_cost == 0
