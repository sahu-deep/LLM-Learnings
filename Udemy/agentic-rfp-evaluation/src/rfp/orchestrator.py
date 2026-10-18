from typing import TypedDict,Any
from langgraph.graph import StateGraph,START,END
from rfp.domain import SupplierMetadata,SupplierEvaluation
from rfp.infrastructure.document_tool import extract_pdf_text
from rfp.infrastructure.llm import evaluate_proposal
from rfp.infrastructure.database import get_active_criteria,create_run,save_supplier_result,complete_run
from rfp.validation import validate_and_normalize
from rfp.services import score_and_rank
class WorkflowState(TypedDict,total=False):
    inputs:list[dict[str,Any]]
    criteria:list[dict[str,Any]]
    api_key:str|None
    model:str|None
    evaluations:list[SupplierEvaluation]
    warnings:list[str]
def run_evaluation_batch(
    inputs: list[dict[str, Any]],
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    if len(inputs)<2: raise ValueError("Upload at least two proposals for peer benchmarking.")
    names=[x["metadata"]["supplier_name"].strip().casefold() for x in inputs]
    if any(not n for n in names) or len(set(names))!=len(names): raise ValueError("Supplier names must be non-empty and unique.")
    criteria=get_active_criteria(); run_id=create_run()
    try:
        final=_graph().invoke({"inputs":inputs,"criteria":criteria,"api_key":api_key,"model":model,"evaluations":[],"warnings":[]})
        for supplier in final["evaluations"]: save_supplier_result(run_id,supplier.model_dump(mode="json"))
        complete_run(run_id,"COMPLETED")
        return {"rfp_run_id":run_id,"status":"COMPLETED","suppliers":[s.model_dump(mode="json") for s in final["evaluations"]],"warnings":final.get("warnings",[])}
    except Exception as exc:
        complete_run(run_id,"FAILED",str(exc)[:1000]); raise
def _graph():
    def evaluate_node(state):
        evaluations=[]; warnings=list(state.get("warnings",[]))
        for item in state["inputs"]:
            name=item["metadata"]["supplier_name"].strip(); text=extract_pdf_text(item["pdf_bytes"])
            raw=evaluate_proposal(name,text,state["criteria"],state.get("api_key"),state.get("model")); result=validate_and_normalize(raw,name,state["criteria"])
            evaluations.append(SupplierEvaluation(metadata=SupplierMetadata.model_validate(item["metadata"]),result=result))
            warnings.extend(f"{name}: {w}" for w in result.warnings)
        return {"evaluations":evaluations,"warnings":warnings}
    def ranking_node(state): return {"evaluations":score_and_rank(state["evaluations"],state["criteria"])}
    graph=StateGraph(WorkflowState); graph.add_node("evaluate_validate",evaluate_node); graph.add_node("score_rank",ranking_node)
    graph.add_edge(START,"evaluate_validate"); graph.add_edge("evaluate_validate","score_rank"); graph.add_edge("score_rank",END)
    return graph.compile()
