# 衡尺 · 指标交付簿

在一份经营底稿中固定指标表达式，按维度核对来源差异，再把周期重算的报表交到站内收件箱。

## 模拟业务

衡尺文化发行社有20位经营分析与渠道同事。过去每周复制各渠道结算表，分析师各自定义净收入，再人工逐份发送。指标依赖不透明、维度差异找不到根源、定时交付没有证据是主要痛点。上游为合成渠道结算明细，本应用替代口径定义、透视重算和核对交付段，下游是站内阅读者；无外部邮件或真实财务操作。

来源 `hengchi-settlement-202611.csv` 对应1800条固定seed 73合成数据，覆盖2026-09/10、直营渠道/书店合作/数字发行、华东/华北/华南。参考账本在书店合作2026-10的300条明细中各多计2.5元，用于展示可解释的750元差异，非真实客户数据。

| 角色 | 页面与权限 | 典型动作 |
|---|---|---|
| admin / 口径负责人 | 六页读写；登记指标、创建/启停计划、计算报表 | 维护统一定义与交付周期 |
| analyst / 经营分析师 | 六页阅读，创建报表和导出 | 编制渠道/月透视，定位差异 |
| viewer / 渠道阅读者 | 只读、导出 | 打开站内交付并读取快照 |

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
docker compose exec -T backend python -m scripts.seed_demo
```

前端 [localhost:18204](http://localhost:18204)，后端文档 [localhost:19204/docs](http://localhost:19204/docs)。Nginx去掉 `/api/` 后代理给FastAPI，直接后端调用不加 `/api`。

| 邮箱 | 密码 | 角色 |
|---|---|---|
| admin@hengchi.demo | Hengchi2026! | admin |
| analyst@hengchi.demo | Hengchi2026! | analyst |
| viewer@hengchi.demo | Hengchi2026! | viewer |

首次启动 `SEED_DEMO=true` 自动seed；自然键为用户邮箱、指标key、来源source_key、计划名称和基准报表名。重复执行只补缺失行，不覆盖已有数据。两份seed计划分别是启用但7天后首次运行的“经营周报 · 渠道/月”，以及暂停的“区域午间校对”，另有基准报表与真实算法生成的站内交付。

## 一天的工作剧本

1. 09:00 宋予以analyst登录，检查1800条来源与基准透视。
2. 09:05 在来源核对发现书店合作2026-10的参考账本多计750元，查看300条来源的归因。
3. 09:10 陆知衡以admin登录，在指标口径登记 `profit_per_order = gross_profit / orders`，说明先汇总再计算。
4. 09:15 宋予创建“11月渠道经营核对”，选择渠道×月份，提交异步计算。
5. worker消费队列，按冻结口径和来源生成6个维度单元及重算合计，结果保存表达式快照与来源SHA256。
6. 09:20 阅读毛利、每单净收入、差异并下载CSV；比率不简单累加。
7. 陆知衡登记“渠道晨间校对”，首次5秒后，演示周期每1分钟。
8. worker在时间到期时独立创建新运行、重算并生成Delivery；第2周期再生成另一份记录。
9. 叶言以viewer打开站内交付箱，查看对应报表并导出，无法创建计划或修改口径。
10. 演示后暂停分钟计划，在校对留痕检查schedule.due与report.delivered记录。

## 真实计算

**指标表达式与依赖DAG**：`backend/src/services/expression_service.py` 使用Python `ast.parse`，只允许字段、有限数值常量、括号、加减乘除、正负号。禁止eval/exec、函数调用、属性访问、下标、幂和布尔常量；最多50语法节点。来源字段仅revenue/cost/refunds/orders，派生指标不能覆盖来源。深度优先拓扑排序检测环路，未知引用在登记阶段422拒绝；还会用现有渠道/月与区域/月数据试算，零分母当场422拒绝。逐节点执行算术，分母绝对值小于1e-12或结果非有限/超范围时明确失败。

**透视与差异归因**：`pivot_service.py` 先按1–2个不重复维度（channel/month/region）分组，把原始金额、单数加总，再沿DAG计算派生指标。总计行重新汇总原始字段计算，绝不累加或简单平均比率。差异为来源`sum(revenue)-sum(refunds)`减`sum(reference_net)`；绝对差异大于0.01元的单元按绝对值降序归因。source_count和SHA256支持复算，输出保留6位小数。

五项种子定义：net_revenue=revenue-refunds；gross_profit=net_revenue-cost；margin_rate=gross_profit/net_revenue；net_per_order=net_revenue/orders；refund_rate=refunds/revenue。比率单位为小数，界面显示4位。

**定时交付**：独立worker每轮扫描到期且启用的DeliverySchedule，持久化新的ReportRun并推入Redis队列，完成计算后创建唯一run_id的Delivery。没有手动投递接口，分钟周期可用真实等待验证。计划以UTC存储，界面按浏览器时区显示；周期从实际执行时间向后推，不补发停机期间每次错过的周期。

## 页面与架构

六页为交付总览、指标口径、来源核对、透视报表、定时交付、校对留痕。核心实体Metric、SourceRow、ReportRun、DeliverySchedule、Delivery分别贯穿SQLAlchemy模型、schema、service、route、前端API、store和页面。`MetricFormula`跨总览与口径页共用；`PivotTable`封装快照透视，`DataTable`、`Notice`、`StatusBadge`跨页共用；hooks分离异步动作与自动刷新。

| 部分 | 技术 |
|---|---|
| Backend | Python3.11 / FastAPI / SQLAlchemy / PyJWT |
| Frontend | React18 / TypeScript / Vite / Noto Serif SC + Noto Sans SC |
| 数据 | PostgreSQL16 / Redis7 AOF |
| 部署 | 恰好frontend/backend/worker/db/redis五服务，Nginx |

```
backend/src/{models,schemas,services,controllers,routes,middlewares,utils,constants,config}
backend/src/{main.py,worker.py}
backend/scripts/seed_demo.py
backend/migrations/001_initial.sql
frontend/src/{api,stores,types,components,hooks,pages,router,utils,constants}
```

共享角色枚举：`backend/src/constants/roles.py` / `frontend/src/constants/enums.ts`；运行状态枚举：`backend/src/constants/status.py` / 前述前端文件；维度枚举：`backend/src/constants/dimensions.py` / 前端enums。后端路由、schema和worker使用枚举，不信任前端授权。JWT有效8小时，密码PBKDF2-SHA256，权限每次查数据库。审计覆盖登录、定义登记、报表排队完成、计划启停/到期及交付。错误和登录限流两个中间件独立。

## 环境与运维

| 环境变量 | 默认 | 说明 |
|---|---|---|
| COMPOSE_PROJECT_NAME | metric-ledger | 容器/网络名称 |
| FRONTEND_PORT | 18204 | 前端 |
| BACKEND_PORT | 19204 | 后端 |
| DB_PORT | 17704 | 数据库宿主端口 |
| JWT_SECRET | local-metric-ledger-change-this-key | 本地演示签名密钥，部署前更换 |
| SEED_DEMO | true | 启动自动seed |

三个命名卷：db-data、redis-data、artifacts；backend与worker共享产物JSON。所有五服务有健康检查，worker2秒循环刷新心跳；frontend依赖backend，backend/worker依赖healthy数据库与Redis。首次建表用SQLAlchemy metadata，迁移目录提供索引示例，后续schema变更需审查迁移。

```bash
docker compose down -v --remove-orphans
```

本地开发：Python3.11安装`backend/requirements.txt`，设置DATABASE_URL/REDIS_URL，`cd backend && uvicorn src.main:app --reload`；另起`python -m src.worker`。前端`npm install && npm run dev`，开发时为`/api`配置后端代理。标准启动以Compose为准。

## 验证与边界

外置测试与截图位于`../../test-artifacts/gb-0005/`，含算法、API、真实周期和浏览器证据。源码不含截图/测试报告/日志，`.env`与日志不提交。

目前面向本地合成研究：无文件上传/外部邮件/多租户隔离；仅支持算术口径，不支持任意SQL或函数。单worker调度不提供多实例分布式锁；running任务崩溃需重新提交，数据库事务与Redis入队之间无事务outbox。金额采用浮点并在输出舍入，非财务总账记账引擎。表达式以当前定义计算且结果保存快照；未提供已注册指标编辑/删除，现有数据试算通过后才能登记，后续来源变化仍可能造成任务失败，结果页会显示错误。来源页最多预览100行，计算用全部来源。Google Fonts无网络会回退字体。

## License

MIT，见LICENSE。
