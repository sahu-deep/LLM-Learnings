from rfp.domain import SupplierEvaluation
def score_and_rank(suppliers:list[SupplierEvaluation],criteria:list[dict]):
    if not suppliers: return []
    total=sum(float(c["weight"]) for c in criteria)
    if abs(total-100)>0.01: raise ValueError("Active criterion weights must total 100%.")
    benchmarks={int(c["criterion_id"]):max((a.score for s in suppliers for a in s.result.criteria if a.criterion_id==int(c["criterion_id"])),default=0) for c in criteria}
    for s in suppliers:
        by_id={a.criterion_id:a for a in s.result.criteria}; absolute=0.; ppi_sum=0.; metrics=[]
        for c in criteria:
            cid=int(c["criterion_id"]); weight=float(c["weight"]); maximum=float(c["max_score"]); a=by_id[cid]; score=float(a.score); best=float(benchmarks[cid])
            relative=score/best*100 if best>0 else 0.
            absolute+=score/maximum*weight; ppi_sum+=relative*weight
            metrics.append({"criterion_id":cid,"criterion_name":c["name"],"weight":weight,"score":score,"max_score":maximum,"benchmark":best,"gap":score-best,"relative_performance_pct":relative,"justification":a.justification,"evidence":a.evidence})
        s.absolute_score=round(absolute,4); s.ppi=round(ppi_sum/total,4); s.criterion_metrics=metrics
    suppliers.sort(key=lambda s:(-s.ppi,s.metadata.submission_date,-s.metadata.experience_rating,s.metadata.supplier_name.casefold()))
    for rank,s in enumerate(suppliers,1): s.final_rank=rank
    return suppliers
