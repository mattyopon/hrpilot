"""評価制度設計サービスのテスト."""

import pytest

from app.models import (
    CompanyProfile,
    CompanySize,
    EvaluationDesign,
    EvaluationType,
    Industry,
)
from app.services.evaluation_designer import (
    _build_evaluation_criteria,
    _generate_recommendations,
    _get_demotion_criteria,
    _get_interview_questions,
    _get_promotion_criteria,
    _recommend_evaluation_type,
    design_evaluation_system,
    get_available_evaluation_types,
)


@pytest.fixture
def it_startup() -> CompanyProfile:
    return CompanyProfile(
        name="テックスタートアップ", size=CompanySize.STARTUP,
        industry=Industry.IT, employee_count=20,
    )


@pytest.fixture
def large_finance() -> CompanyProfile:
    return CompanyProfile(
        name="大手金融", size=CompanySize.LARGE,
        industry=Industry.FINANCE, employee_count=800,
    )


@pytest.fixture
def medium_service() -> CompanyProfile:
    return CompanyProfile(
        name="中堅サービス", size=CompanySize.MEDIUM,
        industry=Industry.SERVICE, employee_count=200,
    )


@pytest.fixture
def enterprise_mfg() -> CompanyProfile:
    return CompanyProfile(
        name="大企業製造", size=CompanySize.ENTERPRISE,
        industry=Industry.MANUFACTURING, employee_count=3000,
    )


# ---------------------------------------------------------------------------
# _recommend_evaluation_type
# ---------------------------------------------------------------------------

class TestRecommendEvaluationType:
    def test_it_startup_okr(self, it_startup: CompanyProfile) -> None:
        assert _recommend_evaluation_type(it_startup) == EvaluationType.OKR

    def test_finance_mbo(self, large_finance: CompanyProfile) -> None:
        assert _recommend_evaluation_type(large_finance) == EvaluationType.MBO

    def test_medium_service_competency(self, medium_service: CompanyProfile) -> None:
        assert _recommend_evaluation_type(medium_service) == EvaluationType.COMPETENCY

    def test_enterprise_mbo(self, enterprise_mfg: CompanyProfile) -> None:
        assert _recommend_evaluation_type(enterprise_mfg) == EvaluationType.MBO

    def test_small_it_okr(self) -> None:
        p = CompanyProfile(name="X", size=CompanySize.SMALL, industry=Industry.IT, employee_count=50)
        assert _recommend_evaluation_type(p) == EvaluationType.OKR

    def test_startup_other_okr(self) -> None:
        p = CompanyProfile(name="X", size=CompanySize.STARTUP, industry=Industry.OTHER, employee_count=10)
        assert _recommend_evaluation_type(p) == EvaluationType.OKR


# ---------------------------------------------------------------------------
# _build_evaluation_criteria
# ---------------------------------------------------------------------------

class TestBuildEvaluationCriteria:
    def test_mbo_criteria(self, large_finance: CompanyProfile) -> None:
        criteria = _build_evaluation_criteria(EvaluationType.MBO, large_finance)
        assert len(criteria) == 4

    def test_okr_criteria(self, it_startup: CompanyProfile) -> None:
        criteria = _build_evaluation_criteria(EvaluationType.OKR, it_startup)
        assert len(criteria) == 4

    def test_competency_criteria(self, medium_service: CompanyProfile) -> None:
        criteria = _build_evaluation_criteria(EvaluationType.COMPETENCY, medium_service)
        assert len(criteria) == 6

    def test_weights_sum_to_1(self, it_startup: CompanyProfile) -> None:
        for eval_type in EvaluationType:
            criteria = _build_evaluation_criteria(eval_type, it_startup)
            total = sum(c.weight for c in criteria)
            assert abs(total - 1.0) < 0.01

    def test_criteria_have_rating_scale(self, it_startup: CompanyProfile) -> None:
        criteria = _build_evaluation_criteria(EvaluationType.OKR, it_startup)
        for c in criteria:
            assert len(c.rating_scale) > 0


# ---------------------------------------------------------------------------
# Interview questions
# ---------------------------------------------------------------------------

class TestInterviewQuestions:
    def test_base_questions(self, medium_service: CompanyProfile) -> None:
        questions = _get_interview_questions(EvaluationType.MBO, medium_service)
        assert len(questions) >= 6

    def test_it_adds_tech_question(self, it_startup: CompanyProfile) -> None:
        questions = _get_interview_questions(EvaluationType.OKR, it_startup)
        assert any("技術" in q for q in questions)

    def test_finance_adds_compliance_question(self, large_finance: CompanyProfile) -> None:
        questions = _get_interview_questions(EvaluationType.MBO, large_finance)
        assert any("コンプライアンス" in q for q in questions)

    def test_startup_adds_growth_question(self, it_startup: CompanyProfile) -> None:
        questions = _get_interview_questions(EvaluationType.OKR, it_startup)
        assert any("成長" in q for q in questions)

    def test_healthcare_adds_safety_question(self) -> None:
        p = CompanyProfile(name="X", size=CompanySize.MEDIUM, industry=Industry.HEALTHCARE, employee_count=100)
        questions = _get_interview_questions(EvaluationType.COMPETENCY, p)
        assert any("安全" in q for q in questions)


# ---------------------------------------------------------------------------
# Promotion / Demotion
# ---------------------------------------------------------------------------

class TestPromotionDemotion:
    def test_startup_fast_track(self, it_startup: CompanyProfile) -> None:
        criteria = _get_promotion_criteria(it_startup)
        assert any("S" in c for c in criteria)

    def test_large_standard(self, large_finance: CompanyProfile) -> None:
        criteria = _get_promotion_criteria(large_finance)
        assert any("滞留年数" in c for c in criteria)

    def test_demotion_criteria_exist(self) -> None:
        criteria = _get_demotion_criteria()
        assert len(criteria) >= 4


# ---------------------------------------------------------------------------
# _generate_recommendations
# ---------------------------------------------------------------------------

class TestGenerateRecommendations:
    def test_okr_recommendations(self, it_startup: CompanyProfile) -> None:
        recs = _generate_recommendations(it_startup, EvaluationType.OKR)
        assert any("OKR" in r for r in recs)

    def test_mbo_recommendations(self, large_finance: CompanyProfile) -> None:
        recs = _generate_recommendations(large_finance, EvaluationType.MBO)
        assert any("SMART" in r or "MBO" in r for r in recs)

    def test_competency_recommendations(self, medium_service: CompanyProfile) -> None:
        recs = _generate_recommendations(medium_service, EvaluationType.COMPETENCY)
        assert any("コンピテンシー" in r or "360" in r for r in recs)


# ---------------------------------------------------------------------------
# design_evaluation_system (integration)
# ---------------------------------------------------------------------------

class TestDesignEvaluationSystem:
    def test_returns_evaluation_design(self, it_startup: CompanyProfile) -> None:
        result = design_evaluation_system(it_startup)
        assert isinstance(result, EvaluationDesign)

    def test_auto_type(self, it_startup: CompanyProfile) -> None:
        result = design_evaluation_system(it_startup)
        assert result.evaluation_type == EvaluationType.OKR

    def test_preferred_type(self, it_startup: CompanyProfile) -> None:
        result = design_evaluation_system(it_startup, preferred_type=EvaluationType.MBO)
        assert result.evaluation_type == EvaluationType.MBO

    def test_has_criteria(self, it_startup: CompanyProfile) -> None:
        result = design_evaluation_system(it_startup)
        assert len(result.evaluation_sheet.criteria) > 0

    def test_has_questions(self, it_startup: CompanyProfile) -> None:
        result = design_evaluation_system(it_startup)
        assert len(result.evaluation_sheet.interview_questions) > 0

    def test_has_promotion_criteria(self, it_startup: CompanyProfile) -> None:
        result = design_evaluation_system(it_startup)
        assert len(result.evaluation_sheet.promotion_criteria) > 0

    def test_has_demotion_criteria(self, it_startup: CompanyProfile) -> None:
        result = design_evaluation_system(it_startup)
        assert len(result.evaluation_sheet.demotion_criteria) > 0

    def test_has_recommendations(self, it_startup: CompanyProfile) -> None:
        result = design_evaluation_system(it_startup)
        assert len(result.recommendations) > 0


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

class TestUtility:
    def test_available_types(self) -> None:
        types = get_available_evaluation_types()
        assert "mbo" in types
        assert "okr" in types
        assert "competency" in types
