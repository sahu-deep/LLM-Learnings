import json
from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st
from pypdf import PdfReader

from src.rfp.config import get_local_api_key
from src.rfp.infrastructure.database import (
    initialize_database,
    save_evaluation,
    create_rfp_run,
    save_run_results,
    get_previous_runs,
    get_run_results,
)
from src.rfp.infrastructure.llm_client import evaluate_supplier
from src.rfp.services.ranking import benchmark_and_rank
from src.rfp.services.scoring import (
    CRITERIA_WEIGHTS,
    calculate_weighted_score,
)


# --------------------------------------------------
# Page configuration and original UI styling
# --------------------------------------------------

st.set_page_config(
    page_title="Agentic RFP Evaluation",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f5f7ff 0%, #f0fbfa 100%);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #172554 0%, #164e63 100%);
    }
    [data-testid="stSidebar"] * {
        color: #ffffff;
    }
    h1 {
        color: #172554;
        font-weight: 800;
    }
    h2, h3 {
        color: #1e3a8a;
        font-weight: 700;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #dbeafe;
        border-radius: 14px;
        padding: 18px;
        box-shadow: 0 4px 14px rgba(30, 58, 138, 0.07);
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #2563eb, #0891b2);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        padding: 0.65rem 1.2rem;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(90deg, #1d4ed8, #0e7490);
        border: none;
    }
    div[data-testid="stExpander"] {
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #dbeafe;
    }
    div[data-testid="stTabs"] button {
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

initialize_database()

st.title("📊 Agentic RFP Evaluation")
st.caption(
    "AI-powered supplier evaluation, peer benchmarking "
    "and explainable ranking"
)


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract selectable text from a PDF."""
    reader = PdfReader(BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if not text:
        raise ValueError(
            "No readable text found in this PDF. Scanned PDFs require OCR."
        )
    return text


def build_leaderboard(results: list[dict]) -> pd.DataFrame:
    """Create the standard supplier leaderboard."""
    return pd.DataFrame(
        [
            {
                "Rank": item["final_rank"],
                "Supplier": item["supplier_name"],
                "Weighted Score": item["weighted_score"],
                "PPI (%)": item["ppi"],
                "Submission Date": item["submission_date"],
                "Experience": item["experience_rating"],
            }
            for item in results
        ]
    )


def render_dashboard(results: list[dict], run_id: str | None, source_label: str):
    """Render KPI cards and interactive charts for one comparison run."""
    st.subheader("Executive Overview")
    if run_id:
        st.caption(f"{source_label} · Run ID: {run_id}")
    else:
        st.caption(source_label)

    if not results:
        st.info(
            "No evaluation results are available yet. Run an evaluation or "
            "open a saved run from Previous Evaluations."
        )
        return

    scores = [float(item["weighted_score"]) for item in results]
    ppis = [float(item.get("ppi", 0)) for item in results]
    average_score = sum(scores) / len(scores)
    average_ppi = sum(ppis) / len(ppis)
    highest_score = max(scores)
    lowest_score = min(scores)
    winner = results[0]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Suppliers Evaluated", len(results))
    k2.metric("Recommended Supplier", winner["supplier_name"])
    k3.metric("Highest Weighted Score", f"{highest_score:.2f}/10")
    k4.metric("Average PPI", f"{average_ppi:.1f}%")

    k5, k6, k7 = st.columns(3)
    k5.metric("Average Weighted Score", f"{average_score:.2f}/10")
    k6.metric("Score Spread", f"{highest_score - lowest_score:.2f}")
    k7.metric("Highest PPI", f"{max(ppis):.1f}%")

    st.divider()
    left, right = st.columns([1.15, 1])

    with left:
        st.markdown("### 🏆 Weighted Score by Supplier")
        score_chart = pd.DataFrame(
            {
                "Supplier": [item["supplier_name"] for item in results],
                "Weighted Score": [item["weighted_score"] for item in results],
            }
        ).set_index("Supplier")
        st.bar_chart(score_chart, y="Weighted Score", height=320)

    with right:
        st.markdown("### 📈 PPI by Supplier")
        ppi_chart = pd.DataFrame(
            {
                "Supplier": [item["supplier_name"] for item in results],
                "PPI (%)": [item.get("ppi", 0) for item in results],
            }
        ).set_index("Supplier")
        st.bar_chart(ppi_chart, y="PPI (%)", height=320)

    st.markdown("### 🎯 Criterion-Level Comparison")
    criteria = list(CRITERIA_WEIGHTS.keys())
    comparison_rows = []
    for item in results:
        row = {"Supplier": item["supplier_name"]}
        for criterion in criteria:
            row[criterion] = item.get("scores", {}).get(criterion, 0)
        comparison_rows.append(row)

    criterion_frame = pd.DataFrame(comparison_rows).set_index("Supplier")
    st.bar_chart(criterion_frame, height=360)

    st.markdown("### 📋 Leaderboard")
    st.dataframe(build_leaderboard(results), use_container_width=True, hide_index=True)

    # A compact heatmap-like table: color is applied to criterion scores only.
    st.markdown("### 🧭 Score Matrix")
    styled_matrix = criterion_frame.style.background_gradient(
        cmap="YlGnBu", axis=None, vmin=0, vmax=10
    ).format("{:.1f}")
    st.dataframe(styled_matrix, use_container_width=True)

    with st.expander("How to read this dashboard"):
        st.markdown(
            """
            - **Weighted Score** is calculated in Python using the configured criterion weights.
            - **PPI** is the relative performance index calculated by the ranking service.
            - **Criterion comparison** helps identify supplier strengths and gaps.
            - Charts describe the selected comparison run; they do not make the final procurement decision.
            """
        )


def render_supplier_comparison(results: list[dict], key_prefix: str = "comparison"):
    """Render an interactive, color-coded side-by-side supplier comparison."""
    st.subheader("🔬 Interactive Supplier Comparison")
    if not results:
        st.info("Evaluate suppliers or load a saved run to compare suppliers here.")
        return

    supplier_names = [item["supplier_name"] for item in results]
    default_selection = supplier_names[: min(3, len(supplier_names))]
    selected_names = st.multiselect(
        "Choose suppliers to compare",
        options=supplier_names,
        default=default_selection,
        key=f"{key_prefix}_supplier_selection",
        help="Select two or more suppliers for a meaningful side-by-side comparison.",
    )

    if not selected_names:
        st.info("Select at least one supplier to display the comparison.")
        return

    selected = [item for item in results if item["supplier_name"] in selected_names]
    criteria = list(CRITERIA_WEIGHTS.keys())

    st.markdown("### 📊 Criterion Score Matrix")
    st.caption("Scores range from 0 to 10. Higher scores indicate stronger alignment with the criterion.")
    matrix_rows = []
    for criterion in criteria:
        row = {"Criterion": criterion, "Weight": f"{CRITERIA_WEIGHTS[criterion] * 100:.0f}%"}
        for item in selected:
            row[item["supplier_name"]] = item.get("scores", {}).get(criterion, 0)
        matrix_rows.append(row)

    matrix = pd.DataFrame(matrix_rows).set_index("Criterion")
    score_columns = [item["supplier_name"] for item in selected]
    styled = matrix.style.map(
        lambda value: (
            "background-color: #dcfce7; color: #166534; font-weight: 700;"
            if isinstance(value, (int, float)) and value >= 8
            else "background-color: #fef3c7; color: #92400e;"
            if isinstance(value, (int, float)) and value >= 6
            else "background-color: #fee2e2; color: #991b1b;"
            if isinstance(value, (int, float))
            else ""
        ),
        subset=score_columns,
    ).format({name: "{:.1f}" for name in score_columns})
    st.dataframe(styled, use_container_width=True)

    st.markdown("### 🏆 Overall Comparison")
    overview_rows = []
    for item in selected:
        overview_rows.append({
            "Rank": item.get("final_rank", "—"),
            "Supplier": item["supplier_name"],
            "Weighted Score (/10)": item.get("weighted_score", 0),
            "PPI (%)": item.get("ppi", 0),
            "Submission Date": item.get("submission_date", "N/A"),
            "Experience Rating": item.get("experience_rating", "N/A"),
        })
    overview = pd.DataFrame(overview_rows)
    st.dataframe(
        overview.style.background_gradient(
            subset=["Weighted Score (/10)", "PPI (%)"], cmap="YlGnBu"
        ).format({"Weighted Score (/10)": "{:.2f}", "PPI (%)": "{:.1f}%"}),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### 💡 Strengths and Areas for Improvement")
    strength_columns = st.columns(min(3, len(selected)))
    for index, item in enumerate(selected):
        with strength_columns[index % len(strength_columns)]:
            st.markdown(f"#### {item['supplier_name']}")
            st.metric("Weighted Score", f"{float(item.get('weighted_score', 0)):.2f}/10")
            assessments_by_criterion = {
                assessment.get("criterion"): assessment
                for assessment in item.get("evaluations", [])
            }
            scored_criteria = [
                (criterion, float(item.get("scores", {}).get(criterion, 0)))
                for criterion in criteria
            ]
            strengths = sorted(scored_criteria, key=lambda pair: pair[1], reverse=True)
            strong_items = [pair for pair in strengths if pair[1] >= 8][:3]
            weak_items = [pair for pair in strengths if pair[1] < 6]

            st.markdown("**Strengths (score ≥ 8)**")
            if strong_items:
                for criterion, score in strong_items:
                    assessment = assessments_by_criterion.get(criterion, {})
                    st.markdown(f"- **{criterion}: {score:.1f}/10**")
                    justification = assessment.get("justification")
                    if justification:
                        st.caption(justification)
            else:
                st.caption("No criterion scored 8 or above.")

            st.markdown("**Areas for improvement (score < 6)**")
            if weak_items:
                for criterion, score in weak_items:
                    assessment = assessments_by_criterion.get(criterion, {})
                    st.markdown(f"- **{criterion}: {score:.1f}/10**")
                    justification = assessment.get("justification")
                    if justification:
                        st.caption(justification)
            else:
                st.caption("No criterion scored below 6.")

    with st.expander("Scoring color legend"):
        st.markdown(
            "🟩 **8.0–10:** Strong · 🟨 **6.0–7.9:** Moderate · "
            "🟥 **Below 6.0:** Needs attention. These labels are display aids; "
            "they do not change the configured scoring or ranking logic."
        )


def render_supplier_details(results: list[dict], key_prefix: str):
    """Display detailed criterion scores, explanations, and evidence."""
    st.subheader("🔎 Detailed Supplier Scorecards")

    for item in results:
        with st.expander(
            f"#{item['final_rank']} — {item['supplier_name']} "
            f"(Score: {item['weighted_score']:.2f}/10)"
        ):
            st.write(f"**PPI:** {item['ppi']}%")
            st.write(f"**Submission date:** {item['submission_date']}")
            st.write(f"**Experience rating:** {item['experience_rating']}")
            st.write(f"**Evaluation ID:** {item.get('evaluation_id', 'N/A')}")

            detail_rows = []
            for assessment in item.get("evaluations", []):
                criterion = assessment["criterion"]
                detail_rows.append(
                    {
                        "Criterion": criterion,
                        "Score": assessment["score"],
                        "Weight": f"{CRITERIA_WEIGHTS[criterion] * 100:.0f}%",
                        "Benchmark": item.get("benchmarks", {}).get(criterion, 0),
                        "Gap": item.get("gaps", {}).get(criterion, 0),
                        "Relative Performance (%)": item.get(
                            "relative_performance", {}
                        ).get(criterion, 0),
                    }
                )
            st.dataframe(
                pd.DataFrame(detail_rows),
                use_container_width=True,
                hide_index=True,
            )

            for assessment in item.get("evaluations", []):
                st.markdown(f"**{assessment['criterion']}**")
                st.write(f"**Score:** {assessment['score']}/10")
                st.write(
                    f"**Justification:** "
                    f"{assessment.get('justification', 'Not provided')}"
                )
                st.write(
                    f"**Evidence:** {assessment.get('evidence', 'Not provided')}"
                )


def render_json_download(results: list[dict], model_name: str, filename: str, key: str):
    export_data = {
        "export_date": date.today().isoformat(),
        "model": model_name,
        "supplier_count": len(results),
        "results": results,
    }
    st.download_button(
        "📥 Download Results as JSON",
        data=json.dumps(export_data, indent=2, ensure_ascii=False, default=str),
        file_name=filename,
        mime="application/json",
        key=key,
    )


# --------------------------------------------------
# Sidebar: API key and model
# --------------------------------------------------

with st.sidebar:
    st.header("⚙️ AI Configuration")

    user_api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        help="Your key is used to make OpenAI API calls.",
    )
    local_api_key = get_local_api_key()

    if user_api_key.strip():
        api_key = user_api_key.strip()
        key_source = "Streamlit input"
    elif local_api_key:
        api_key = local_api_key
        key_source = "Local .env"
    else:
        api_key = ""
        key_source = "No key"

    model = st.selectbox(
        "OpenAI Model",
        ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"],
    )

    if api_key:
        st.success(f"API key available: {key_source}")
    else:
        st.warning("Enter an OpenAI API key to evaluate proposals.")

    st.caption(
        "Proposal text is sent to the selected OpenAI model for evaluation."
    )


# --------------------------------------------------
# Load dashboard data before rendering tabs
# --------------------------------------------------

current_results = st.session_state.get("ranked_results", [])
current_run_id = st.session_state.get("current_run_id")
dashboard_results = current_results
dashboard_run_id = current_run_id
dashboard_source = "Current session results"

if not dashboard_results:
    try:
        saved_runs_for_dashboard = get_previous_runs()
        if saved_runs_for_dashboard:
            latest_run = saved_runs_for_dashboard[0]
            dashboard_results = get_run_results(latest_run["rfp_run_id"])
            dashboard_run_id = latest_run["rfp_run_id"]
            dashboard_source = "Latest saved comparison"
        else:
            dashboard_source = "No saved evaluations yet"
    except Exception as exc:
        dashboard_source = f"Unable to load saved results: {exc}"


dashboard_tab, comparison_tab, new_tab, history_tab = st.tabs(
    ["📊 Executive Dashboard", "🔬 Supplier Comparison", "🆕 New Evaluation", "🕘 Previous Evaluations"]
)


# --------------------------------------------------
# Executive dashboard
# --------------------------------------------------

with dashboard_tab:
    if dashboard_source.startswith("Unable to"):
        st.warning(dashboard_source)
    render_dashboard(dashboard_results, dashboard_run_id, dashboard_source)
    if dashboard_results:
        render_json_download(
            dashboard_results,
            st.session_state.get("evaluation_model", model),
            "rfp_dashboard_results.json",
            "dashboard_json_export",
        )


# --------------------------------------------------
# Interactive supplier comparison
# --------------------------------------------------

with comparison_tab:
    if dashboard_results:
        st.caption(f"Comparing suppliers from: {dashboard_source}")
    render_supplier_comparison(dashboard_results, "main_comparison")
    if dashboard_results:
        render_json_download(
            dashboard_results,
            st.session_state.get("evaluation_model", model),
            "rfp_supplier_comparison.json",
            "comparison_json_export",
        )


# --------------------------------------------------
# New evaluation
# --------------------------------------------------

with new_tab:
    st.subheader("📋 Evaluation Criteria")
    criteria_rows = [
        {"Criterion": name, "Weight": f"{weight * 100:.0f}%"}
        for name, weight in CRITERIA_WEIGHTS.items()
    ]
    st.dataframe(pd.DataFrame(criteria_rows), use_container_width=True, hide_index=True)

    st.subheader("📄 Upload Supplier Proposals")
    uploaded_files = st.file_uploader(
        "Upload one or more supplier PDF proposals",
        type=["pdf"],
        accept_multiple_files=True,
        key="proposal_uploader",
    )

    supplier_metadata = {}
    if uploaded_files:
        st.write("Enter the details for each supplier.")
        for index, uploaded_file in enumerate(uploaded_files):
            default_name = uploaded_file.name.rsplit(".", 1)[0].replace("_", " ")
            with st.expander(default_name, expanded=False):
                supplier_metadata[uploaded_file.name] = {
                    "supplier_name": st.text_input(
                        "Supplier name",
                        value=default_name,
                        key=f"name_{index}",
                    ),
                    "submission_date": st.date_input(
                        "Submission date",
                        value=date.today(),
                        key=f"date_{index}",
                    ),
                    "experience_rating": st.number_input(
                        "Historical experience rating (0–10)",
                        min_value=0.0,
                        max_value=10.0,
                        value=5.0,
                        step=0.5,
                        key=f"experience_{index}",
                    ),
                }

    st.caption(
        "The LLM assesses proposal content. Python validates scores and calculates "
        "weighted scores, benchmarks, gaps, PPI and ranking."
    )

    if st.button(
        "🚀 Evaluate Suppliers",
        type="primary",
        disabled=not uploaded_files or not api_key,
    ):
        results = []
        errors = []
        progress = st.progress(0)
        status_area = st.empty()

        for index, uploaded_file in enumerate(uploaded_files):
            metadata = supplier_metadata[uploaded_file.name]
            supplier_name = metadata["supplier_name"].strip()

            try:
                if not supplier_name:
                    raise ValueError("Supplier name cannot be blank.")

                status_area.info(f"Evaluating {supplier_name}...")
                proposal_text = extract_pdf_text(uploaded_file.getvalue())

                evaluation = evaluate_supplier(
                    proposal_text=proposal_text,
                    api_key=api_key,
                    model=model,
                )

                scores = {
                    item.criterion: item.score
                    for item in evaluation.evaluations
                }
                weighted_score = calculate_weighted_score(scores)
                assessments = [item.model_dump() for item in evaluation.evaluations]

                evaluation_id = save_evaluation(
                    supplier_name=supplier_name,
                    weighted_score=weighted_score,
                    assessments=assessments,
                    submission_date=metadata["submission_date"].isoformat(),
                    experience_rating=metadata["experience_rating"],
                    overall_summary=getattr(evaluation, "overall_summary", None),
                )

                results.append(
                    {
                        "evaluation_id": evaluation_id,
                        "supplier_name": supplier_name,
                        "submission_date": metadata["submission_date"].isoformat(),
                        "experience_rating": metadata["experience_rating"],
                        "weighted_score": weighted_score,
                        "scores": scores,
                        "evaluations": assessments,
                    }
                )
            except Exception as exc:
                errors.append({"file": uploaded_file.name, "error": str(exc)})

            progress.progress((index + 1) / len(uploaded_files))

        status_area.empty()
        progress.empty()

        if results:
            ranked_results = benchmark_and_rank(results)
            run_id = create_rfp_run()
            save_run_results(run_id, ranked_results)

            st.session_state["ranked_results"] = ranked_results
            st.session_state["evaluation_errors"] = errors
            st.session_state["evaluation_model"] = model
            st.session_state["current_run_id"] = run_id
            st.success(
                f"Evaluation completed: {len(ranked_results)} supplier(s). "
                f"Saved run ID: {run_id}"
            )
        else:
            st.session_state["ranked_results"] = []
            st.session_state["evaluation_errors"] = errors
            st.error("No supplier proposals could be evaluated successfully.")

        # Rerun once so the executive dashboard immediately reflects this run.
        st.rerun()

    ranked_results = st.session_state.get("ranked_results", [])
    errors = st.session_state.get("evaluation_errors", [])

    if ranked_results:
        st.success(f"Successfully evaluated {len(ranked_results)} supplier(s).")
        st.caption(f"Saved comparison run: {st.session_state.get('current_run_id', 'N/A')}")
        render_supplier_details(ranked_results, "current")
        render_json_download(
            ranked_results,
            st.session_state.get("evaluation_model", model),
            "rfp_evaluation_results.json",
            "current_json_export",
        )

    if errors:
        st.subheader("⚠️ Processing Errors")
        for error in errors:
            st.error(f"{error['file']}: {error['error']}")

    if not ranked_results and not errors:
        st.info(
            "Upload supplier PDF proposals, configure your API key, "
            "and click Evaluate Suppliers to begin."
        )


# --------------------------------------------------
# Previous evaluation history
# --------------------------------------------------

with history_tab:
    st.subheader("🕘 Previous Evaluation Runs")
    st.write("Open a saved comparison without running the LLM again.")

    try:
        previous_runs = get_previous_runs()
    except Exception as exc:
        previous_runs = []
        st.error(f"Unable to load evaluation history: {exc}")

    if not previous_runs:
        st.info(
            "No saved comparison runs yet. Evaluate suppliers in the New Evaluation tab first."
        )
    else:
        history_table = pd.DataFrame(
            [
                {
                    "Run ID": run["rfp_run_id"],
                    "Created At": run["created_at"],
                    "Status": run["status"],
                    "Supplier Count": run["supplier_count"],
                    "Top Supplier": run["top_supplier"] or "N/A",
                }
                for run in previous_runs
            ]
        )
        st.dataframe(history_table, use_container_width=True, hide_index=True)

        run_ids = [run["rfp_run_id"] for run in previous_runs]
        selected_run = st.selectbox(
            "Select a previous run",
            run_ids,
            key="history_run_selector",
        )

        if st.button(
            "📂 Load Previous Results",
            type="primary",
            key="load_history_results",
        ):
            try:
                st.session_state["history_results"] = get_run_results(selected_run)
                st.session_state["history_loaded_run_id"] = selected_run
            except Exception as exc:
                st.error(f"Unable to load results for {selected_run}: {exc}")

        history_results = st.session_state.get("history_results", [])
        loaded_run_id = st.session_state.get("history_loaded_run_id")

        if history_results and loaded_run_id == selected_run:
            st.caption(f"Viewing saved comparison: {loaded_run_id}")
            render_dashboard(history_results, loaded_run_id, "Historical comparison")
            render_supplier_details(history_results, f"history_{loaded_run_id}")
            render_json_download(
                history_results,
                st.session_state.get("evaluation_model", model),
                f"{loaded_run_id.lower()}_results.json",
                f"download_history_{loaded_run_id}",
            )
