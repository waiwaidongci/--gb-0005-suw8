import random,json
from datetime import datetime,timedelta,timezone,date
from src.config.database import SessionLocal,Base,engine
from src.models import User,Metric,SourceRow,ReportRun,DeliverySchedule,Delivery
from src.utils.security import hash_password
from src.services.pivot_service import build_report

def seed():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for role,name in [("admin","陆知衡 · 口径负责人"),("analyst","宋予 · 经营分析师"),("viewer","叶言 · 渠道阅读者")]:
            email=role+"@hengchi.demo"
            if not db.query(User).filter_by(email=email).first():db.add(User(email=email,name=name,role=role,password_hash=hash_password("Hengchi2026!")))
        for key,name,expression,unit,description in [
            ("net_revenue","净收入","revenue-refunds","元","渠道收入减退款，不扣履约成本。"),
            ("gross_profit","贡献毛利","net_revenue-cost","元","净收入扣除渠道履约成本的贡献。"),
            ("margin_rate","贡献毛利率","gross_profit/net_revenue","比率","先汇总净收入和毛利，再计算比例。"),
            ("net_per_order","每单净收入","net_revenue/orders","元/单","汇总净收入除以有效单数，禁止简单平均。"),
            ("refund_rate","退款率","refunds/revenue","比率","退款金额占渠道原始收入的比例。")]:
            if not db.query(Metric).filter_by(key=key).first():db.add(Metric(key=key,name=name,expression=expression,unit=unit,description=description,owner="陆知衡 · 口径负责人"))
        rng=random.Random(73);existing=set(x[0] for x in db.query(SourceRow.source_key))
        for i in range(1800):
            key=f"HC-{i+1:06}";day=(date(2026,9,1)+timedelta(days=i//30)).isoformat();channel=["直营渠道","书店合作","数字发行"][i%3];region=["华东","华北","华南"][(i//3)%3]
            revenue=round(rng.uniform(150,950),2);refunds=round(revenue*rng.uniform(.01,.12),2);cost=round(revenue*rng.uniform(.35,.6),2);orders=rng.randint(5,24)
            reference=round(revenue-refunds+(2.5 if channel=="书店合作" and day.startswith("2026-10") else 0),2)
            if key not in existing:db.add(SourceRow(source_key=key,day=day,channel=channel,region=region,revenue=revenue,refunds=refunds,cost=cost,orders=orders,reference_net=reference))
        db.flush();schedules=[]
        for name,mins,active in [("经营周报 · 渠道/月",10080,True),("区域午间校对",1440,False)]:
            schedule=db.query(DeliverySchedule).filter_by(name=name).first()
            if not schedule:
                schedule=DeliverySchedule(name=name,dimensions=["channel","month"] if mins==10080 else ["region","month"],interval_minutes=mins,next_run_at=(datetime.now(timezone.utc)+timedelta(days=7)).isoformat(),active=active,owner="陆知衡 · 口径负责人")
                db.add(schedule);db.flush()
            schedules.append(schedule)
        if not db.query(ReportRun).filter_by(name="11月经营口径核对 · 基准").first():
            result=build_report(db.query(SourceRow).order_by(SourceRow.id).all(),db.query(Metric).order_by(Metric.id).all(),["channel","month"])
            run=ReportRun(name="11月经营口径核对 · 基准",dimensions=["channel","month"],status="completed",result=result,owner="宋予 · 经营分析师",schedule_id=schedules[0].id)
            db.add(run);db.flush();db.add(Delivery(schedule_id=schedules[0].id,run_id=run.id,title="经营周报 · 基准交付"))
        db.commit();print(json.dumps({m.__tablename__:db.query(m).count() for m in [User,Metric,SourceRow,ReportRun,DeliverySchedule,Delivery]},ensure_ascii=False))
if __name__=="__main__":seed()
