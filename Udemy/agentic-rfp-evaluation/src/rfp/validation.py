from rfp.domain import EvaluationResult
def validate_and_normalize(raw,supplier_name,criteria):
    warnings=[]; by_id={}
    for item in raw.get("criteria",[]) if isinstance(raw,dict) else []:
        if not isinstance(item,dict): warnings.append("Ignored malformed assessment."); continue
        try: cid=int(item.get("criterion_id"))
        except (TypeError,ValueError): warnings.append("Ignored invalid criterion ID."); continue
        if cid in by_id: warnings.append(f"Duplicate criterion {cid}; first retained."); continue
        by_id[cid]=item
    normalized=[]
    for c in criteria:
        cid=int(c["criterion_id"]); maximum=float(c["max_score"]); item=by_id.get(cid)
        if item is None: warnings.append(f"Missing criterion {cid} ({c['name']}); score set to zero."); item={}
        try: score=float(item.get("score",0))
        except (ValueError,TypeError): score=0.; warnings.append(f"Invalid score for criterion {cid}; set to zero.")
        if score<0 or score>maximum: warnings.append(f"Score for criterion {cid} clipped."); score=min(maximum,max(0.,score))
        normalized.append({"criterion_id":cid,"score":score,"max_score":maximum,"justification":str(item.get("justification","No justification supplied."))[:2000],"evidence":str(item.get("evidence",""))[:1000]})
    unknown=set(by_id)-{int(c["criterion_id"]) for c in criteria}
    if unknown: warnings.append(f"Ignored unknown/inactive criterion IDs: {sorted(unknown)}.")
    return EvaluationResult(supplier_name=supplier_name,criteria=normalized,risks=raw.get("risks",[]) if isinstance(raw.get("risks",[]),list) else [],overall_summary=str(raw.get("overall_summary",""))[:3000],warnings=warnings)
