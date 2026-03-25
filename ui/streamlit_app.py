"""HRPilot Streamlit UI - 人事コンサルAI."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from app.models import (
    Article36Agreement,
    BusinessPlan,
    CompanyProfile,
    CompanySize,
    EvaluationType,
    GradeSystemType,
    Industry,
    LaborConditions,
    WorkRulesInput,
)
from app.services.evaluation_designer import design_evaluation_system
from app.services.hr_system_designer import design_hr_system
from app.services.labor_compliance import check_compliance
from app.services.recruitment_planner import create_recruitment_plan, generate_job_description
from app.services.rules_checker import check_all_rules

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="HRPilot", page_icon="👔", layout="wide")

SIZE_OPTIONS = {
    "スタートアップ (~30名)": CompanySize.STARTUP,
    "小規模 (31-100名)": CompanySize.SMALL,
    "中規模 (101-300名)": CompanySize.MEDIUM,
    "大規模 (301-1000名)": CompanySize.LARGE,
    "エンタープライズ (1001名~)": CompanySize.ENTERPRISE,
}

INDUSTRY_OPTIONS = {
    "IT": Industry.IT,
    "製造業": Industry.MANUFACTURING,
    "小売・流通": Industry.RETAIL,
    "金融": Industry.FINANCE,
    "医療・ヘルスケア": Industry.HEALTHCARE,
    "建設": Industry.CONSTRUCTION,
    "サービス": Industry.SERVICE,
    "その他": Industry.OTHER,
}


def _get_company_profile(prefix: str = "") -> CompanyProfile:
    """共通の企業プロファイル入力."""
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("企業名", value="サンプル株式会社", key=f"{prefix}_name")
        size_label = st.selectbox("企業規模", list(SIZE_OPTIONS.keys()), key=f"{prefix}_size")
        industry_label = st.selectbox("業種", list(INDUSTRY_OPTIONS.keys()), key=f"{prefix}_industry")
    with col2:
        employee_count = st.number_input("従業員数", min_value=1, value=100, key=f"{prefix}_emp")
        has_union = st.checkbox("労働組合あり", key=f"{prefix}_union")

    return CompanyProfile(
        name=name,
        size=SIZE_OPTIONS[size_label],
        industry=INDUSTRY_OPTIONS[industry_label],
        employee_count=employee_count,
        has_union=has_union,
    )


# ---------------------------------------------------------------------------
# 1. 人事制度設計
# ---------------------------------------------------------------------------

def page_hr_system() -> None:
    """人事制度設計ページ."""
    st.header("人事制度設計AI")
    st.markdown("企業プロファイルに基づいて、等級制度・報酬制度を自動設計します。")

    profile = _get_company_profile("hr")

    grade_options = {"自動推奨": None, "職能等級制": GradeSystemType.SKILL_BASED, "職務等級制": GradeSystemType.JOB_BASED, "役割等級制": GradeSystemType.ROLE_BASED}
    grade_label = st.selectbox("等級制度", list(grade_options.keys()))

    if st.button("設計を実行", key="hr_run"):
        result = design_hr_system(profile, grade_options[grade_label])

        st.subheader("等級制度")
        st.info(f"**{result.grade_system.system_type.value}**: {result.grade_system.description}")

        st.subheader("等級一覧")
        grade_data = []
        for g in result.grade_system.grades:
            grade_data.append({
                "等級": g.grade_name,
                "レベル": g.level,
                "説明": g.description,
                "月給下限": f"¥{g.salary_min:,}",
                "月給上限": f"¥{g.salary_max:,}",
            })
        st.table(grade_data)

        st.subheader("賃金テーブル")
        salary_data = []
        for s in result.salary_tables:
            allowance_str = ", ".join(f"{k}: ¥{v:,}" for k, v in s.allowances.items() if v > 0)
            salary_data.append({
                "等級": s.grade_name,
                "基本給下限": f"¥{s.base_salary_min:,}",
                "基本給上限": f"¥{s.base_salary_max:,}",
                "手当": allowance_str,
            })
        st.table(salary_data)

        st.subheader("推奨事項")
        for r in result.recommendations:
            st.markdown(f"- {r}")


# ---------------------------------------------------------------------------
# 2. 労務コンプライアンスチェック
# ---------------------------------------------------------------------------

def page_compliance() -> None:
    """労務コンプライアンスチェックページ."""
    st.header("労務コンプライアンスチェック")
    st.markdown("労働条件を入力し、法令遵守状況をチェックします。")

    profile = _get_company_profile("comp")

    st.subheader("労働条件")
    col1, col2 = st.columns(2)
    with col1:
        weekly_hours = st.number_input("週の所定労働時間", value=40.0, step=0.5)
        overtime_avg = st.number_input("月間平均残業時間", value=20.0, step=1.0)
        overtime_max = st.number_input("月間最大残業時間", value=40.0, step=1.0)
        paid_leave_days = st.number_input("有給休暇付与日数", value=10, min_value=0)
        paid_leave_rate = st.slider("有給休暇取得率", 0.0, 1.0, 0.5, 0.05)
    with col2:
        has_health = st.checkbox("健康診断実施", value=True)
        has_stress = st.checkbox("ストレスチェック実施")
        has_harassment = st.checkbox("ハラスメント防止方針あり")
        has_childcare = st.checkbox("育児休業制度あり")
        has_nursing = st.checkbox("介護休業制度あり")
        has_equal_pay = st.checkbox("同一労働同一賃金対応済")
        has_a36 = st.checkbox("36協定あり")

    article36 = None
    if has_a36:
        article36 = Article36Agreement(has_agreement=True)

    if st.button("チェック実行", key="comp_run"):
        conditions = LaborConditions(
            weekly_hours=weekly_hours, overtime_monthly_avg=overtime_avg,
            overtime_monthly_max=overtime_max, has_health_check=has_health,
            has_stress_check=has_stress, has_harassment_policy=has_harassment,
            has_childcare_leave=has_childcare, has_nursing_care_leave=has_nursing,
            has_equal_pay_policy=has_equal_pay, paid_leave_days=paid_leave_days,
            paid_leave_taken_rate=paid_leave_rate, article36=article36,
        )
        report = check_compliance(conditions, profile)

        st.subheader("チェック結果")
        st.markdown(f"**{report.summary}**")

        col1, col2, col3 = st.columns(3)
        col1.metric("総指摘数", report.total_issues)
        col2.metric("CRITICAL", report.critical_count)
        col3.metric("HIGH", report.high_count)

        for issue in report.issues:
            color = {"critical": "red", "high": "orange", "medium": "blue"}.get(issue.risk_level.value, "gray")
            st.markdown(f":{color}[**{issue.risk_level.value.upper()}**] {issue.law_name} {issue.article}: {issue.description}")
            st.markdown(f"  → {issue.recommendation}")


# ---------------------------------------------------------------------------
# 3. 採用計画
# ---------------------------------------------------------------------------

def page_recruitment() -> None:
    """採用計画ページ."""
    st.header("採用計画AI")
    st.markdown("事業計画から必要人員を算出し、採用チャネルを推奨します。")

    profile = _get_company_profile("rec")

    st.subheader("事業計画")
    revenue = st.number_input("売上目標 (円)", value=500000000, step=10000000)
    growth = st.slider("成長率", 0.0, 1.0, 0.2, 0.05)

    st.subheader("部門別現在人数")
    dept_text = st.text_area("部門名:人数 (1行1部門)", value="エンジニアリング:10\n営業:5\n管理:3")
    departments = {}
    for line in dept_text.strip().split("\n"):
        if ":" in line:
            parts = line.split(":")
            departments[parts[0].strip()] = int(parts[1].strip())

    new_projects = st.text_input("新規プロジェクト (カンマ区切り)", value="")
    projects = [p.strip() for p in new_projects.split(",") if p.strip()] if new_projects else []

    budget = st.number_input("採用予算 (円)", value=0, step=1000000)
    timeline = st.number_input("採用期間 (月)", value=12, min_value=1)

    if st.button("計画作成", key="rec_run"):
        plan = BusinessPlan(
            revenue_target=revenue, growth_rate=growth,
            departments=departments, new_projects=projects,
            budget_for_hiring=budget, timeline_months=timeline,
        )
        result = create_recruitment_plan(profile, plan)

        st.subheader("採用計画サマリー")
        st.markdown(f"**{result.summary}**")

        st.subheader("採用ポジション")
        pos_data = []
        for p in result.positions:
            pos_data.append({
                "ポジション": p.title,
                "部門": p.department,
                "人数": p.headcount,
                "優先度": p.priority,
                "必要スキル": ", ".join(p.required_skills),
            })
        st.table(pos_data)

        st.subheader("推奨チャネル")
        ch_data = []
        for c in result.channel_recommendations:
            ch_data.append({
                "チャネル": c.channel.value,
                "理由": c.reason,
                "採用単価": f"¥{c.estimated_cost_per_hire:,}",
                "期間(日)": c.estimated_time_days,
                "適合度": f"{c.effectiveness_score:.0%}",
            })
        st.table(ch_data)

        # JD生成
        if result.positions:
            st.subheader("職務記述書 (JD) サンプル")
            jd = generate_job_description(result.positions[0], profile)
            st.markdown(jd)


# ---------------------------------------------------------------------------
# 4. 評価制度設計
# ---------------------------------------------------------------------------

def page_evaluation() -> None:
    """評価制度設計ページ."""
    st.header("評価制度設計AI")
    st.markdown("企業に最適な評価制度を設計します。")

    profile = _get_company_profile("eval")

    eval_options = {"自動推奨": None, "MBO (目標管理)": EvaluationType.MBO, "OKR": EvaluationType.OKR, "コンピテンシー評価": EvaluationType.COMPETENCY}
    eval_label = st.selectbox("評価制度", list(eval_options.keys()))

    if st.button("設計を実行", key="eval_run"):
        result = design_evaluation_system(profile, eval_options[eval_label])

        st.subheader(f"評価制度: {result.evaluation_type.value.upper()}")

        st.subheader("評価基準")
        criteria_data = []
        for c in result.evaluation_sheet.criteria:
            criteria_data.append({
                "項目": c.name,
                "説明": c.description,
                "ウェイト": f"{c.weight:.0%}",
                "評価尺度": " / ".join(c.rating_scale),
            })
        st.table(criteria_data)

        st.subheader("評価面談質問")
        for q in result.evaluation_sheet.interview_questions:
            st.markdown(f"- {q}")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("昇格基準")
            for c in result.evaluation_sheet.promotion_criteria:
                st.markdown(f"- {c}")
        with col2:
            st.subheader("降格基準")
            for c in result.evaluation_sheet.demotion_criteria:
                st.markdown(f"- {c}")

        st.subheader("推奨事項")
        for r in result.recommendations:
            st.markdown(f"- {r}")


# ---------------------------------------------------------------------------
# 5. 就業規則チェック
# ---------------------------------------------------------------------------

def page_rules() -> None:
    """就業規則チェックページ."""
    st.header("就業規則チェックAI")
    st.markdown("就業規則テキストを入力し、法定記載事項の充足確認を行います。")

    rules_text = st.text_area(
        "就業規則テキスト",
        height=300,
        placeholder="就業規則の全文をここに貼り付けてください...",
    )

    if st.button("チェック実行", key="rules_run"):
        if not rules_text.strip():
            st.error("就業規則テキストを入力してください。")
            return

        work_rules = WorkRulesInput(rules_text=rules_text)
        report = check_all_rules(work_rules)

        st.subheader("チェック結果")
        st.markdown(f"**{report.summary}**")

        col1, col2, col3 = st.columns(3)
        col1.metric("スコア", f"{report.compliance_score:.1f}/100")
        col2.metric("総項目数", report.total_items)
        col3.metric("要対応", report.non_compliant_count)

        st.progress(report.compliance_score / 100)

        st.subheader("詳細結果")
        for item in report.items:
            icon = "✅" if item.is_compliant else "❌"
            color = "green" if item.is_compliant else ("red" if item.risk_level.value == "critical" else "orange")
            st.markdown(f"{icon} **[{item.category}]** {item.item_name}")
            if not item.is_compliant:
                st.markdown(f"  :{color}[{item.risk_level.value.upper()}] {item.recommendation}")
                st.markdown(f"  法的根拠: {item.legal_basis}")


# ---------------------------------------------------------------------------
# Main navigation
# ---------------------------------------------------------------------------

def main() -> None:
    """メインアプリケーション."""
    st.sidebar.title("HRPilot")
    st.sidebar.markdown("人事コンサルAI")

    pages = {
        "人事制度設計": page_hr_system,
        "労務コンプライアンス": page_compliance,
        "採用計画": page_recruitment,
        "評価制度設計": page_evaluation,
        "就業規則チェック": page_rules,
    }

    page = st.sidebar.radio("メニュー", list(pages.keys()))
    pages[page]()


if __name__ == "__main__":
    main()
