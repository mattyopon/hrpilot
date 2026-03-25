"""人事制度設計サービスのテスト."""

import pytest

from app.models import (
    CompanyProfile,
    CompanySize,
    GradeSystemType,
    HRSystemDesign,
    Industry,
)
from app.services.hr_system_designer import (
    _apply_industry_multiplier,
    _apply_size_multiplier,
    _build_grade_definitions,
    _build_salary_tables,
    _recommend_grade_system_type,
    design_hr_system,
    get_available_grade_systems,
    get_compensation_components,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def startup_it() -> CompanyProfile:
    return CompanyProfile(
        name="テックスタートアップ", size=CompanySize.STARTUP,
        industry=Industry.IT, employee_count=20,
    )


@pytest.fixture
def large_manufacturing() -> CompanyProfile:
    return CompanyProfile(
        name="大手製造", size=CompanySize.LARGE,
        industry=Industry.MANUFACTURING, employee_count=800,
        has_union=True,
    )


@pytest.fixture
def medium_finance() -> CompanyProfile:
    return CompanyProfile(
        name="中堅金融", size=CompanySize.MEDIUM,
        industry=Industry.FINANCE, employee_count=200,
    )


@pytest.fixture
def enterprise_it() -> CompanyProfile:
    return CompanyProfile(
        name="大企業IT", size=CompanySize.ENTERPRISE,
        industry=Industry.IT, employee_count=2000,
    )


@pytest.fixture
def small_retail() -> CompanyProfile:
    return CompanyProfile(
        name="小売チェーン", size=CompanySize.SMALL,
        industry=Industry.RETAIL, employee_count=80,
    )


# ---------------------------------------------------------------------------
# _recommend_grade_system_type
# ---------------------------------------------------------------------------

class TestRecommendGradeSystemType:
    def test_it_startup_returns_role_based(self, startup_it: CompanyProfile) -> None:
        assert _recommend_grade_system_type(startup_it) == GradeSystemType.ROLE_BASED

    def test_it_enterprise_returns_job_based(self, enterprise_it: CompanyProfile) -> None:
        assert _recommend_grade_system_type(enterprise_it) == GradeSystemType.JOB_BASED

    def test_finance_returns_job_based(self, medium_finance: CompanyProfile) -> None:
        assert _recommend_grade_system_type(medium_finance) == GradeSystemType.JOB_BASED

    def test_large_manufacturing_returns_skill_based(self, large_manufacturing: CompanyProfile) -> None:
        assert _recommend_grade_system_type(large_manufacturing) == GradeSystemType.SKILL_BASED

    def test_small_retail_returns_skill_based(self, small_retail: CompanyProfile) -> None:
        assert _recommend_grade_system_type(small_retail) == GradeSystemType.SKILL_BASED

    def test_startup_other_returns_role_based(self) -> None:
        p = CompanyProfile(name="X", size=CompanySize.STARTUP, industry=Industry.OTHER, employee_count=10)
        assert _recommend_grade_system_type(p) == GradeSystemType.ROLE_BASED

    def test_large_service_returns_role_based(self) -> None:
        p = CompanyProfile(name="X", size=CompanySize.LARGE, industry=Industry.SERVICE, employee_count=500)
        assert _recommend_grade_system_type(p) == GradeSystemType.ROLE_BASED

    def test_enterprise_manufacturing_returns_skill_based(self) -> None:
        p = CompanyProfile(name="X", size=CompanySize.ENTERPRISE, industry=Industry.MANUFACTURING, employee_count=2000)
        assert _recommend_grade_system_type(p) == GradeSystemType.SKILL_BASED

    def test_medium_healthcare_returns_skill_based(self) -> None:
        p = CompanyProfile(name="X", size=CompanySize.MEDIUM, industry=Industry.HEALTHCARE, employee_count=150)
        assert _recommend_grade_system_type(p) == GradeSystemType.SKILL_BASED


# ---------------------------------------------------------------------------
# Multipliers
# ---------------------------------------------------------------------------

class TestMultipliers:
    def test_size_startup(self, startup_it: CompanyProfile) -> None:
        assert _apply_size_multiplier(startup_it) == 0.90

    def test_size_enterprise(self, enterprise_it: CompanyProfile) -> None:
        assert _apply_size_multiplier(enterprise_it) == 1.15

    def test_size_medium(self, medium_finance: CompanyProfile) -> None:
        assert _apply_size_multiplier(medium_finance) == 1.00

    def test_industry_it(self, startup_it: CompanyProfile) -> None:
        assert _apply_industry_multiplier(startup_it) == 1.10

    def test_industry_finance(self, medium_finance: CompanyProfile) -> None:
        assert _apply_industry_multiplier(medium_finance) == 1.15

    def test_industry_retail(self, small_retail: CompanyProfile) -> None:
        assert _apply_industry_multiplier(small_retail) == 0.90


# ---------------------------------------------------------------------------
# _build_grade_definitions
# ---------------------------------------------------------------------------

class TestBuildGradeDefinitions:
    def test_skill_based_has_6_grades(self) -> None:
        grades = _build_grade_definitions(GradeSystemType.SKILL_BASED, 1.0, 1.0)
        assert len(grades) == 6

    def test_job_based_has_6_grades(self) -> None:
        grades = _build_grade_definitions(GradeSystemType.JOB_BASED, 1.0, 1.0)
        assert len(grades) == 6

    def test_role_based_has_6_grades(self) -> None:
        grades = _build_grade_definitions(GradeSystemType.ROLE_BASED, 1.0, 1.0)
        assert len(grades) == 6

    def test_multiplier_applied(self) -> None:
        grades_base = _build_grade_definitions(GradeSystemType.SKILL_BASED, 1.0, 1.0)
        grades_high = _build_grade_definitions(GradeSystemType.SKILL_BASED, 1.5, 1.0)
        assert grades_high[0].salary_min > grades_base[0].salary_min

    def test_grade_levels_ascending(self) -> None:
        grades = _build_grade_definitions(GradeSystemType.JOB_BASED, 1.0, 1.0)
        levels = [g.level for g in grades]
        assert levels == sorted(levels)

    def test_salary_min_less_than_max(self) -> None:
        for sys_type in GradeSystemType:
            grades = _build_grade_definitions(sys_type, 1.0, 1.0)
            for g in grades:
                assert g.salary_min <= g.salary_max


# ---------------------------------------------------------------------------
# _build_salary_tables
# ---------------------------------------------------------------------------

class TestBuildSalaryTables:
    def test_startup_has_commute_allowance_only(self, startup_it: CompanyProfile) -> None:
        grades = _build_grade_definitions(GradeSystemType.ROLE_BASED, 1.0, 1.0)
        tables = _build_salary_tables(grades, startup_it)
        for t in tables:
            assert "通勤手当" in t.allowances
            assert "役職手当" not in t.allowances

    def test_medium_has_allowances(self, medium_finance: CompanyProfile) -> None:
        grades = _build_grade_definitions(GradeSystemType.JOB_BASED, 1.0, 1.0)
        tables = _build_salary_tables(grades, medium_finance)
        for t in tables:
            assert "通勤手当" in t.allowances
            assert "役職手当" in t.allowances
            assert "住宅手当" in t.allowances

    def test_table_count_matches_grades(self, startup_it: CompanyProfile) -> None:
        grades = _build_grade_definitions(GradeSystemType.ROLE_BASED, 1.0, 1.0)
        tables = _build_salary_tables(grades, startup_it)
        assert len(tables) == len(grades)


# ---------------------------------------------------------------------------
# design_hr_system (integration)
# ---------------------------------------------------------------------------

class TestDesignHRSystem:
    def test_returns_hr_system_design(self, startup_it: CompanyProfile) -> None:
        result = design_hr_system(startup_it)
        assert isinstance(result, HRSystemDesign)

    def test_preferred_system_overrides(self, startup_it: CompanyProfile) -> None:
        result = design_hr_system(startup_it, preferred_system=GradeSystemType.SKILL_BASED)
        assert result.grade_system.system_type == GradeSystemType.SKILL_BASED

    def test_auto_recommendation(self, medium_finance: CompanyProfile) -> None:
        result = design_hr_system(medium_finance)
        assert result.grade_system.system_type == GradeSystemType.JOB_BASED

    def test_has_grades(self, startup_it: CompanyProfile) -> None:
        result = design_hr_system(startup_it)
        assert len(result.grade_system.grades) > 0

    def test_has_salary_tables(self, startup_it: CompanyProfile) -> None:
        result = design_hr_system(startup_it)
        assert len(result.salary_tables) > 0

    def test_has_recommendations(self, startup_it: CompanyProfile) -> None:
        result = design_hr_system(startup_it)
        assert len(result.recommendations) > 0

    def test_union_recommendation(self, large_manufacturing: CompanyProfile) -> None:
        result = design_hr_system(large_manufacturing)
        assert any("労働組合" in r for r in result.recommendations)

    def test_it_recommendation(self, startup_it: CompanyProfile) -> None:
        result = design_hr_system(startup_it)
        assert any("IT" in r or "エンジニア" in r for r in result.recommendations)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

class TestUtilityFunctions:
    def test_get_available_grade_systems(self) -> None:
        systems = get_available_grade_systems()
        assert "skill_based" in systems
        assert "job_based" in systems
        assert "role_based" in systems

    def test_get_compensation_components(self) -> None:
        comps = get_compensation_components()
        assert len(comps) > 0
        names = [c.name for c in comps]
        assert "基本給" in names
