import json
from datetime import date
import pandas as pd
import streamlit as st
from rfp.config import settings
from rfp.infrastructure.database import initialize_database,get_active_criteria,get_recent_runs
from rfp.orchestrator import run_evaluation_batch
st.set_page_config(page_title="Agentic RFP Evaluation",page_icon="📑",layout="wide")
initialize_database()
st.title("Agentic RFP Evaluation & Supplier Ranking")
st.caption("Evidence-grounded assessment with deterministic, explainable ranking.")
with st.sidebar:
    st.header("LLM settings")
    entered_api_key=st.text_input("OpenAI API key",type="password",help="Used for this app session only. Leave blank to use OPENAI_API_KEY from .env.")
    model_options=list(dict.fromkeys([settings.model,"gpt-4.1-mini","gpt-4.1","gpt-4o-mini","gpt-4o"]))
    selected_model=st.selectbox("Chat model",model_options,index=model_options.index(settings.model))
api_key=entered_api_key.strip() or settings.api_key
if settings.demo_mode and not api_key: st.warning("DEMO MODE: keyword heuristic, not LLM evaluation. Do not use demo scores for procurement decisions.")
criteria=get_active_criteria()
with st.expander("Active criteria",expanded=True):
    st.dataframe(pd.DataFrame(criteria)[["criterion_id","name","description","weight","max_score"]],hide_index=True,use_container_width=True)
    st.caption(f"Total active weight: {sum(c['weight'] for c in criteria):.1f}%")
st.header("Supplier input")
uploads=st.file_uploader("Upload at least two text-based supplier PDFs",type=["pdf"],accept_multiple_files=True)
inputs=[]
for i,f in enumerate(uploads or []):
    with st.container(border=True):
        st.subheader(f.name); default=f.name.rsplit(".",1)[0].replace("_"," ").replace("-"," ").title()
        a,b,c=st.columns([2,1,1]); name=a.text_input("Supplier name",value=default,key=f"name{i}")
        submitted=b.date_input("Submission date",value=date.today(),key=f"date{i}")
        experience=c.number_input("Experience rating (0-10)",min_value=0.,max_value=10.,value=5.,step=.5,key=f"exp{i}")
        inputs.append({"pdf_bytes":f.getvalue(),"metadata":{"supplier_name":name.strip(),"submission_date":submitted.isoformat(),"experience_rating":experience}})
if st.button("Evaluate batch",type="primary",disabled=len(inputs)<2,use_container_width=True):
    try:
        with st.spinner("Evaluating and ranking suppliers..."): st.session_state["result"]=run_evaluation_batch(inputs,api_key=api_key,model=selected_model)
        st.success(f"Run completed: {st.session_state['result']['rfp_run_id']}")
    except Exception as exc: st.error(f"Evaluation failed: {exc}")
result=st.session_state.get("result")
if result:
    st.header("Leaderboard")
    rows=[{"Rank":s["final_rank"],"Supplier":s["metadata"]["supplier_name"],"Absolute score / 100":s["absolute_score"],"PPI (%)":s["ppi"],"Submission date":s["metadata"]["submission_date"],"Experience":s["metadata"]["experience_rating"]} for s in result["suppliers"]]
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    for s in result["suppliers"]:
        with st.expander(f"Rank {s['final_rank']} — {s['metadata']['supplier_name']}"):
            st.write(s["result"]["overall_summary"]); st.markdown("**Risks**")
            for risk in s["result"]["risks"]: st.write(f"- {risk}")
            st.markdown("**Criterion scorecard**"); st.dataframe(pd.DataFrame(s["criterion_metrics"]),hide_index=True,use_container_width=True)
            if s["result"]["warnings"]: st.warning("; ".join(s["result"]["warnings"]))
    if result["warnings"]:
        with st.expander("Batch warnings"):
            for w in result["warnings"]: st.write(f"- {w}")
    st.download_button("Download complete result as JSON",data=json.dumps(result,indent=2,ensure_ascii=False,default=str),file_name=f"rfp_run_{result['rfp_run_id']}.json",mime="application/json")
with st.expander("Recent runs"):
    runs=get_recent_runs()
    if runs: st.dataframe(pd.DataFrame(runs),hide_index=True,use_container_width=True)
    else: st.info("No runs yet.")
