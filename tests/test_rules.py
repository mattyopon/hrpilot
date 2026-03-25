"""就業規則チェックサービスのテスト."""

import pytest

from app.models import (
    CompanyProfile,
    CompanySize,
    Industry,
    RiskLevel,
    RulesCheckReport,
    WorkRulesInput,
)
from app.services.rules_checker import (
    _check_keywords_in_text,
    check_all_rules,
    check_equal_pay,
    check_harassment_prevention,
    check_mandatory_items,
    check_optional_items,
    check_telework_rules,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GOOD_RULES_TEXT = """
就業規則

第1章 総則
第1条 本規則は、株式会社テストの就業に関する事項を定める。

第2章 労働時間・休憩・休日
第2条 始業時刻は9時00分、終業時刻は18時00分とする。
第3条 休憩時間は12時00分から13時00分までの1時間とする。
第4条 休日は毎週土曜日及び日曜日、国民の祝日とする。
第5条 年次有給休暇は労働基準法の定めるところにより付与する。特別休暇として慶弔休暇を設ける。

第3章 賃金
第6条 賃金は月給制とし、基本給及び諸手当で構成する。給与は毎月25日に支給する。
第7条 賃金の締切日は毎月末日とし、支払日は翌月25日とする。
第8条 昇給は毎年4月に行う。ベースアップは会社業績に応じて決定する。
第9条 賞与は6月及び12月に支給する。ボーナスの額は業績に連動する。

第4章 退職
第10条 定年は満60歳とする。退職届は30日前までに提出すること。解雇の事由は別途定める。
第11条 退職金は勤続3年以上の者に支給する。退職手当の計算方法は別途定める。

第5章 安全衛生
第12条 会社は安全衛生に関する措置を講じ、定期健康診断を実施する。

第6章 教育
第13条 会社は従業員の研修・教育・訓練を計画的に実施する。OJTを基本とする。

第7章 災害補償
第14条 業務上の災害補償は労災保険法の定めるところによる。通勤災害も同様とする。

第8章 表彰・懲戒
第15条 会社は功績のあった者を表彰する。服務規律に違反した者は懲戒処分とする。減給の制裁は法令の範囲内とする。

第9章 ハラスメント防止
第16条 パワーハラスメント、セクシュアルハラスメント、マタニティハラスメントを禁止する。
第17条 ハラスメントに関する相談窓口を設置する。事後の調査及び再発防止措置を講じる。

第10章 同一労働同一賃金
第18条 正社員と非正規社員の基本給、賞与、各種手当、福利厚生について均等・均衡待遇を確保する。
第19条 待遇差について説明義務を果たす。

第11章 テレワーク
第20条 テレワーク（在宅勤務・リモートワーク）に関する規定を定める。
第21条 テレワーク時の勤怠管理（始業・終業の報告）を義務付ける。
第22条 テレワーク時の通信費及び光熱費は会社が手当として支給する。
第23条 テレワーク時の情報セキュリティ対策及び個人情報の取扱いについて定める。
第24条 テレワーク時の安全衛生確保及び労災適用について定める。

第12章 育児・介護
第25条 シフト勤務者の勤務交替については別途定める。
"""

MINIMAL_RULES_TEXT = """
就業規則

第1条 勤務時間は9時から18時とする。
"""


@pytest.fixture
def good_input() -> WorkRulesInput:
    return WorkRulesInput(rules_text=GOOD_RULES_TEXT)


@pytest.fixture
def minimal_input() -> WorkRulesInput:
    return WorkRulesInput(rules_text=MINIMAL_RULES_TEXT)


# ---------------------------------------------------------------------------
# _check_keywords_in_text
# ---------------------------------------------------------------------------

class TestCheckKeywords:
    def test_found(self) -> None:
        assert _check_keywords_in_text("始業は9時", ["始業"])

    def test_not_found(self) -> None:
        assert not _check_keywords_in_text("テスト文書", ["始業"])

    def test_case_insensitive(self) -> None:
        assert _check_keywords_in_text("ABC", ["abc"])

    def test_multiple_keywords_any(self) -> None:
        assert _check_keywords_in_text("休憩時間は1時間", ["休日", "休憩"])

    def test_empty_keywords(self) -> None:
        assert not _check_keywords_in_text("テスト", [])

    def test_empty_text(self) -> None:
        assert not _check_keywords_in_text("", ["始業"])


# ---------------------------------------------------------------------------
# check_mandatory_items
# ---------------------------------------------------------------------------

class TestCheckMandatoryItems:
    def test_good_rules_all_compliant(self) -> None:
        items = check_mandatory_items(GOOD_RULES_TEXT)
        mandatory = [i for i in items if i.risk_level != RiskLevel.INFO]
        # Good rules text should have all mandatory items
        non_compliant = [i for i in items if not i.is_compliant]
        assert len(non_compliant) == 0

    def test_minimal_rules_missing_items(self) -> None:
        items = check_mandatory_items(MINIMAL_RULES_TEXT)
        non_compliant = [i for i in items if not i.is_compliant]
        assert len(non_compliant) > 0

    def test_critical_for_missing_mandatory(self) -> None:
        items = check_mandatory_items(MINIMAL_RULES_TEXT)
        critical = [i for i in items if i.risk_level == RiskLevel.CRITICAL]
        assert len(critical) > 0

    def test_items_have_legal_basis(self) -> None:
        items = check_mandatory_items(GOOD_RULES_TEXT)
        for item in items:
            assert item.legal_basis != ""


# ---------------------------------------------------------------------------
# check_optional_items
# ---------------------------------------------------------------------------

class TestCheckOptionalItems:
    def test_good_rules_has_optional(self) -> None:
        items = check_optional_items(GOOD_RULES_TEXT)
        compliant = [i for i in items if i.is_compliant]
        assert len(compliant) > 0

    def test_minimal_rules_missing_optional(self) -> None:
        items = check_optional_items(MINIMAL_RULES_TEXT)
        non_compliant = [i for i in items if not i.is_compliant]
        assert len(non_compliant) > 0

    def test_optional_missing_is_medium(self) -> None:
        items = check_optional_items(MINIMAL_RULES_TEXT)
        non_compliant = [i for i in items if not i.is_compliant]
        for item in non_compliant:
            assert item.risk_level == RiskLevel.MEDIUM


# ---------------------------------------------------------------------------
# check_equal_pay
# ---------------------------------------------------------------------------

class TestCheckEqualPay:
    def test_good_rules_compliant(self) -> None:
        items = check_equal_pay(GOOD_RULES_TEXT)
        compliant = [i for i in items if i.is_compliant]
        assert len(compliant) >= 3

    def test_minimal_rules_non_compliant(self) -> None:
        items = check_equal_pay(MINIMAL_RULES_TEXT)
        non_compliant = [i for i in items if not i.is_compliant]
        assert len(non_compliant) > 0


# ---------------------------------------------------------------------------
# check_harassment_prevention
# ---------------------------------------------------------------------------

class TestCheckHarassment:
    def test_good_rules_compliant(self) -> None:
        items = check_harassment_prevention(GOOD_RULES_TEXT)
        compliant = [i for i in items if i.is_compliant]
        assert len(compliant) >= 4

    def test_minimal_rules_non_compliant(self) -> None:
        items = check_harassment_prevention(MINIMAL_RULES_TEXT)
        non_compliant = [i for i in items if not i.is_compliant]
        assert len(non_compliant) > 0


# ---------------------------------------------------------------------------
# check_telework_rules
# ---------------------------------------------------------------------------

class TestCheckTelework:
    def test_good_rules_compliant(self) -> None:
        items = check_telework_rules(GOOD_RULES_TEXT)
        compliant = [i for i in items if i.is_compliant]
        assert len(compliant) >= 4

    def test_minimal_rules_non_compliant(self) -> None:
        items = check_telework_rules(MINIMAL_RULES_TEXT)
        non_compliant = [i for i in items if not i.is_compliant]
        assert len(non_compliant) == 5  # all 5 telework items missing


# ---------------------------------------------------------------------------
# check_all_rules (integration)
# ---------------------------------------------------------------------------

class TestCheckAllRules:
    def test_returns_report(self, good_input: WorkRulesInput) -> None:
        report = check_all_rules(good_input)
        assert isinstance(report, RulesCheckReport)

    def test_good_rules_high_score(self, good_input: WorkRulesInput) -> None:
        report = check_all_rules(good_input)
        assert report.compliance_score >= 80.0

    def test_minimal_rules_low_score(self, minimal_input: WorkRulesInput) -> None:
        report = check_all_rules(minimal_input)
        assert report.compliance_score < 50.0

    def test_summary_not_empty(self, good_input: WorkRulesInput) -> None:
        report = check_all_rules(good_input)
        assert len(report.summary) > 0

    def test_total_items_positive(self, good_input: WorkRulesInput) -> None:
        report = check_all_rules(good_input)
        assert report.total_items > 0

    def test_non_compliant_count(self, minimal_input: WorkRulesInput) -> None:
        report = check_all_rules(minimal_input)
        assert report.non_compliant_count > 0

    def test_with_company_profile(self) -> None:
        profile = CompanyProfile(name="テスト", size=CompanySize.MEDIUM, industry=Industry.IT, employee_count=100)
        inp = WorkRulesInput(rules_text=GOOD_RULES_TEXT, company_profile=profile)
        report = check_all_rules(inp)
        assert isinstance(report, RulesCheckReport)

    def test_score_0_to_100(self, good_input: WorkRulesInput) -> None:
        report = check_all_rules(good_input)
        assert 0.0 <= report.compliance_score <= 100.0

    def test_empty_rules_all_non_compliant(self) -> None:
        inp = WorkRulesInput(rules_text="")
        report = check_all_rules(inp)
        assert report.non_compliant_count == report.total_items
