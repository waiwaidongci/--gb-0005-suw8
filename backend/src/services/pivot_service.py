import hashlib,json
from collections import defaultdict
from ..constants.dimensions import BASE_FIELDS,Dimension
from .expression_service import compile_metrics,calculate

def build_report(rows,metrics,dimensions):
    if not rows:raise ValueError("没有可计算的来源明细")
    if not dimensions or len(dimensions)>2 or len(set(dimensions))!=len(dimensions) or not set(dimensions)<=set(Dimension):raise ValueError("请选择一到两个不同的有效维度")
    rows=sorted(rows,key=lambda r:r.source_key)
    trees,order,deps=compile_metrics(metrics)
    if not order:raise ValueError("请先注册指标")
    grouped=defaultdict(list)
    for row in rows:
        group=tuple(row.day[:7] if dim=="month" else getattr(row,dim) for dim in dimensions)
        grouped[group].append(row)
    def aggregate(members):
        base={key:sum(getattr(r,key) for r in members) for key in BASE_FIELDS}
        computed=calculate(base,trees,order)
        reference=sum(r.reference_net for r in members)
        canonical=base['revenue']-base['refunds']
        difference=canonical-reference
        return {"values":computed,"reference_net":round(reference,6),"canonical_net":round(canonical,6),"difference":round(difference,6),"relative_difference":difference/reference if reference else None,"source_count":len(members)}
    cells=[{"dimensions":dict(zip(dimensions,key)),**aggregate(members)} for key,members in sorted(grouped.items())]
    total=aggregate(rows)
    checksum=hashlib.sha256(json.dumps([(r.source_key,r.day,r.channel,r.region,r.revenue,r.refunds,r.cost,r.orders,r.reference_net) for r in rows],sort_keys=True).encode()).hexdigest()
    return {"dimensions":dimensions,"metrics":[{"key":m.key,"name":m.name,"expression":m.expression,"unit":m.unit} for m in metrics],"evaluation_order":order,"dependencies":deps,"cells":cells,"total":total,"affected_cells":sum(abs(c['difference'])>.01 for c in cells),"attribution":sorted([c for c in cells if abs(c['difference'])>.01],key=lambda c:abs(c['difference']),reverse=True),"source_checksum":checksum,"reconciliation_rule":"来源 revenue-refunds 与 reference_net 比较；绝对差异 > 0.01 元标记。比率指标在汇总原始字段后重算，不汇总比率。"}
