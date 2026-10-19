
import json
from datetime import date
from io import BytesIO

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
# Page configuration and styling
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
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Application initialization
# --------------------------------------------------

st.title("📊 Agentic RFP Evaluation")
st.caption(
    "AI-powered supplier evaluation, peer benchmarking "
    "and explainable ranking"
)

initialize_database()


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
        [
            "gpt-4.1-mini",
            "gpt-4.1",
            "gpt-4o-mini",
        ],
    )

    if api_key:
        st.success(f"API key available: {key_source}")
    else:
        st.warning("Enter an OpenAI API key to evaluate proposals.")

    st.caption(
        "Proposal text is sent to the selected OpenAI model "
        "for evaluation."
    )



# --------------------------------------------------
# Evaluation tabs
# --------------------------------------------------

new_tab, history_tab = st.tabs(["🆕 New Evaluation", "🕘 Previous Evaluations"])

with new_tab:
    # --------------------------------------------------
    # Evaluation criteria
    # --------------------------------------------------

    st.subheader("📋 Evaluation Criteria")

    criteria_rows = [
        {
            "Criterion": name,
            "Weight": f"{weight * 100:.0f}%",
        }
        for name, weight in CRITERIA_WEIGHTS.items()
    ]

    st.dataframe(
        criteria_rows,
        use_container_width=True,
        hide_index=True,
    )


    # --------------------------------------------------
    # Upload proposals and collect supplier metadata
    # --------------------------------------------------

    st.subheader("📄 Upload Supplier Proposals")

    uploaded_files = st.file_uploader(
        "Upload one or more supplier PDF proposals",
        type=["pdf"],
        accept_multiple_files=True,
    )

    supplier_metadata = {}

    if uploaded_files:
        st.write("Enter the details for each supplier.")

        for index, uploaded_file in enumerate(uploaded_files):
            default_name = uploaded_file.name.rsplit(".", 1)[0]

            with st.expander(default_name.replace("_", " "), expanded=False):
                supplier_metadata[uploaded_file.name] = {
                    "supplier_name": st.text_input(
                        "Supplier name",
                        value=default_name.replace("_", " "),
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


    # --------------------------------------------------
    # Evaluate all uploaded proposals
    # --------------------------------------------------

    if st.button(
        "🚀 Evaluate Suppliers",
        type="primary",
        disabled=not uploaded_files or not api_key,
    ):
        # Remove previous results so they cannot be mistaken
        # for results from this new evaluation run.
        st.session_state.pop("ranked_results", None)
        st.session_state.pop("evaluation_errors", None)

        results = []
        errors = []

        progress = st.progress(0)

        for index, uploaded_file in enumerate(uploaded_files):
            metadata = supplier_metadata[uploaded_file.name]
            supplier_name = metadata["supplier_name"].strip()

            try:
                if not supplier_name:
                    raise ValueError("Supplier name cannot be blank.")

                # Extract text from the uploaded PDF.
                reader = PdfReader(BytesIO(uploaded_file.getvalue()))

                page_texts = [
                    page.extract_text() or ""
                    for page in reader.pages
                ]

                proposal_text = "\n".join(page_texts).strip()

                if not proposal_text:
                    raise ValueError(
                        "No readable text found in this PDF. "
                        "Scanned PDFs require OCR."
                    )

                # LLM evaluates proposal content.
                evaluation = evaluate_supplier(
                    proposal_text=proposal_text,
                    api_key=api_key,
                    model=model,
                )

                # Python validates the criterion set and calculates
                # the weighted score.
                scores = {
                    item.criterion: item.score
                    for item in evaluation.evaluations
                }

                weighted_score = calculate_weighted_score(scores)

                assessments = [
                    item.model_dump()
                    for item in evaluation.evaluations
                ]

                # Save the evaluation in SQLite.
                evaluation_id = save_evaluation(
                    supplier_name=supplier_name,
                    weighted_score=weighted_score,
                    assessments=assessments,
                    submission_date=metadata[
                        "submission_date"
                    ].isoformat(),
                    experience_rating=metadata[
                        "experience_rating"
                    ],
                    overall_summary=getattr(
                        evaluation,
                        "overall_summary",
                        None,
                    ),
                )

                results.append(
                    {
                        "evaluation_id": evaluation_id,
                        "supplier_name": supplier_name,
                        "submission_date": metadata[
                            "submission_date"
                        ].isoformat(),
                        "experience_rating": metadata[
                            "experience_rating"
                        ],
                        "weighted_score": weighted_score,
                        "scores": scores,
                        "evaluations": assessments,
                    }
                )

            except Exception as exc:
                errors.append(
                    {
                        "file": uploaded_file.name,
                        "error": str(exc),
                    }
                )

            progress.progress((index + 1) / len(uploaded_files))

        # Benchmark and rank only successfully evaluated suppliers.
        if results:
            ranked_results = benchmark_and_rank(results)

            # Save this comparison as a persistent history run.
            run_id = create_rfp_run()
            save_run_results(run_id, ranked_results)

            st.session_state["ranked_results"] = ranked_results
            st.session_state["evaluation_errors"] = errors
            st.session_state["evaluation_model"] = model
            st.session_state["current_run_id"] = run_id

        else:
            st.session_state["ranked_results"] = []
            st.session_state["evaluation_errors"] = errors

        if errors:
            st.warning(
                f"{len(errors)} proposal(s) could not be evaluated."
            )


    # --------------------------------------------------
    # Display KPI cards, leaderboard and scorecards
    # --------------------------------------------------

    ranked_results = st.session_state.get("ranked_results", [])
    errors = st.session_state.get("evaluation_errors", [])

    if ranked_results:
        st.success(
            f"Successfully evaluated {len(ranked_results)} supplier(s)."
        )
        current_run_id = st.session_state.get("current_run_id")
        if current_run_id:
            st.caption(f"Saved comparison run: {current_run_id}")

        # KPI dashboard
        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Suppliers Evaluated",
            len(ranked_results),
        )

        col2.metric(
            "Top Supplier",
            ranked_results[0]["supplier_name"],
        )

        col3.metric(
            "Highest Score",
            f"{ranked_results[0]['weighted_score']:.2f}/10",
        )

        average_score = sum(
            item["weighted_score"]
            for item in ranked_results
        ) / len(ranked_results)

        col4.metric(
            "Average Score",
            f"{average_score:.2f}/10",
        )

        # Leaderboard
        st.subheader("🏆 Supplier Leaderboard")

        leaderboard = [
            {
                "Rank": item["final_rank"],
                "Supplier": item["supplier_name"],
                "Weighted Score": item["weighted_score"],
                "PPI (%)": item["ppi"],
                "Submission Date": item["submission_date"],
                "Experience": item["experience_rating"],
            }
            for item in ranked_results
        ]

        st.dataframe(
            leaderboard,
            use_container_width=True,
            hide_index=True,
        )

        # Detailed scorecards
        st.subheader("🔎 Detailed Supplier Scorecards")

        for item in ranked_results:
            with st.expander(
                f"#{item['final_rank']} — {item['supplier_name']} "
                f"(Score: {item['weighted_score']:.2f}/10)"
            ):
                st.write(f"**PPI:** {item['ppi']}%")
                st.write(f"**Evaluation ID:** {item['evaluation_id']}")

                details = []

                for assessment in item["evaluations"]:
                    criterion = assessment["criterion"]

                    details.append(
                        {
                            "Criterion": criterion,
                            "Score": assessment["score"],
                            "Weight": (
                                f"{CRITERIA_WEIGHTS[criterion] * 100:.0f}%"
                            ),
                            "Benchmark": item["benchmarks"][criterion],
                            "Gap": item["gaps"][criterion],
                            "Relative Performance (%)": (
                                item["relative_performance"][criterion]
                            ),
                        }
                    )

                st.dataframe(
                    details,
                    use_container_width=True,
                    hide_index=True,
                )

                for assessment in item["evaluations"]:
                    st.markdown(f"**{assessment['criterion']}**")
                    st.write(
                        f"**Score:** {assessment['score']}/10"
                    )
                    st.write(
                        f"**Justification:** {assessment['justification']}"
                    )
                    st.write(
                        f"**Evidence:** {assessment['evidence']}"
                    )

        # JSON export
        export_data = {
            "run_date": date.today().isoformat(),
            "model": st.session_state.get(
                "evaluation_model",
                model,
            ),
            "supplier_count": len(ranked_results),
            "results": ranked_results,
            "errors": errors,
        }

        st.download_button(
            "📥 Download Results as JSON",
            data=json.dumps(
                export_data,
                indent=2,
                ensure_ascii=False,
            ),
            file_name="rfp_evaluation_results.json",
            mime="application/json",
        )


    # --------------------------------------------------
    # Processing and validation errors
    # --------------------------------------------------

    if errors:
        st.subheader("⚠️ Processing Errors")

        for error in errors:
            st.error(
                f"{error['file']}: {error['error']}"
            )


    # --------------------------------------------------
    # Initial state
    # --------------------------------------------------

    if not ranked_results and not errors:
        st.info(
            "Upload supplier PDF proposals, configure your API key, "
            "and click **Evaluate Suppliers** to begin."
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
        st.info("No saved comparison runs yet. Evaluate suppliers in the New Evaluation tab first.")
    else:
        st.dataframe(
            [
                {
                    "Run ID": run["rfp_run_id"],
                    "Created At": run["created_at"],
                    "Status": run["status"],
                    "Supplier Count": run["supplier_count"],
                    "Top Supplier": run["top_supplier"] or "N/A",
                }
                for run in previous_runs
            ],
            use_container_width=True,
            hide_index=True,
        )

        run_ids = [run["rfp_run_id"] for run in previous_runs]
        selected_run = st.selectbox("Select a previous run", run_ids, key="history_run_selector")

        if st.button("📂 Load Previous Results", type="primary", key="load_history_results"):
            try:
                st.session_state["history_results"] = get_run_results(selected_run)
                st.session_state["history_loaded_run_id"] = selected_run
            except Exception as exc:
                st.error(f"Unable to load results for {selected_run}: {exc}")

        history_results = st.session_state.get("history_results", [])
        loaded_run_id = st.session_state.get("history_loaded_run_id")

        if history_results and loaded_run_id == selected_run:
            st.caption(f"Viewing saved comparison: {loaded_run_id}")
            # Reuse the same scorecard layout and original visual styling.
            st.dataframe(
                [
                    {
                        "Rank": item["final_rank"],
                        "Supplier": item["supplier_name"],
                        "Weighted Score": item["weighted_score"],
                        "PPI (%)": item["ppi"],
                        "Submission Date": item["submission_date"],
                        "Experience": item["experience_rating"],
                    }
                    for item in history_results
                ],
                use_container_width=True,
                hide_index=True,
            )

            for item in history_results:
                with st.expander(
                    f"#{item['final_rank']} — {item['supplier_name']} "
                    f"(Score: {item['weighted_score']:.2f}/10)",
                ):
                    st.write(f"**PPI:** {item['ppi']}%")
                    st.write(f"**Submission date:** {item['submission_date']}")
                    st.write(f"**Experience rating:** {item['experience_rating']}")
                    detail_rows = []
                    for assessment in item.get("evaluations", []):
                        criterion = assessment["criterion"]
                        detail_rows.append(
                            {
                                "Criterion": criterion,
                                "Score": assessment["score"],
                                "Weight": f"{CRITERIA_WEIGHTS[criterion] * 100:.0f}%",
                                "Benchmark": item["benchmarks"][criterion],
                                "Gap": item["gaps"][criterion],
                                "Relative Performance (%)": item["relative_performance"][criterion],
                            }
                        )
                    st.dataframe(detail_rows, use_container_width=True, hide_index=True)
                    for assessment in item.get("evaluations", []):
                        st.markdown(f"**{assessment['criterion']}**")
                        st.write(f"**Score:** {assessment['score']}/10")
                        st.write(f"**Justification:** {assessment.get('justification', '')}")
                        st.write(f"**Evidence:** {assessment.get('evidence', '')}")

            st.download_button(
                "📥 Download Previous Results as JSON",
                data=json.dumps(history_results, indent=2, ensure_ascii=False),
                file_name=f"{loaded_run_id.lower()}_results.json",
                mime="application/json",
                key=f"download_history_{loaded_run_id}",
            )
