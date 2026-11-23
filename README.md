# 双台架振动复检工作台

泵组检修车间的白班技师登记具名频带的正交试读。主管固定指定修订并将证据件交给夜班。两座站库关闭后，质控员按实收号复检相干能量，班组凭签报和回执安排补测。勘误产生新来源，既有签报可按原号复领。

## 运行

使用 Python 3.11 标准库。在项目根目录执行完整正常回归和实算演示。

```text
python3 -B check_project.py
python3 -B -m examples.shift
```

第一条命令使用工作台运行平台提供的入口。也可直接使用 `python3 -B -m unittest discover -s tests -t . -p 'test_*.py'`。演示输入位于 `examples/shift.py`，在独立临时库内完成录入、出件、实收、停源签报、勘误、重开和复领。库在演示结束时删除。

## 公开调用

调用者用 `sqlite3.connect` 管理连接和关闭。每台架通常单独使用站库，夜班使用独立中心库。对空闲连接调用 `phase_evidence.initialize_station(conn)` 或 `review.initialize_center(conn)` 建表并启用外键。重复初始化保全现有记录。业务写入自行管理事务，调用时连接须无待提交事务。

| 角色 | 调用 | 结果 |
| --- | --- | --- |
| 技师 | `measurements.record(station_db, station, run, rows, previous_revision_id=None)` | 新修订号。`rows` 是按输入顺序排列的 `(频带名, I, Q)` 记录。勘误前件必须属于同台架、同测次。 |
| 主管 | `measurements.get_revision(station_db, revision_id)`、`measurements.read_revision_lineage(station_db, revision_id)` | 读取原测以及从本修订向前的勘误链。 |
| 主管 | `calibration.freeze(station_db, revision_id, reference=None)` | `FixedAnalysis` 含 `analysis_id`、来源、站内参考记录以及 `inspection` 的响应、资格和能量。`calibration.get_fixed_analysis` 按号领取。 |
| 主管 | `phase_evidence.issue(station_db, analysis_id)` | `IssuedArtifact` 含 `artifact_id`、来源和 `exchange` 交运文本。`phase_evidence.get_issued_artifact` 按原件号复取。 |
| 夜班 | `receiving.accept(center_db, exchange, declared_artifact_id)` | `Receipt` 含 `receipt_id` 和 `artifact_id`。`receiving.lookup_received` 按号读取实际留存的原件、来源、证据及回执。 |
| 夜班 | `receiving.collect_pair(center_db, (left_id, right_id))` | 依指定顺序领取来自不同台架的两个实收件，适用于关站后的资料核对。 |
| 质控员 | `review.sign(center_db, (left_id, right_id), weights)` | `SignedReport` 含 `report_id`、规范化的原请求、输入顺序的父件、`outcome` 和成功回执。`weights` 是频带名到有理数的映射。 |
| 班组 | `review.get_report(center_db, report_id)` | 读取原签存快照。读取路径直接使用报告账及其成功回执。 |

台架、测次和带名使用非空文本，按原拼写精确匹配。正交分量和权重接受整数、`Fraction` 及可由 `Fraction` 解析的有理数字串。布尔、浮点和非法分数拒绝。原读数同单位 U。`calibration.ReferenceRecord(revision_id, (实部, 虚部))` 表示已由上游核准的公共参考校正，因子的模平方必须精确为 1。`ReferenceRecord(revision_id, None)` 表示存在候选记录但缺有效相位。直接传入 `None` 表示缺候选记录。校正后单站能量为各带模平方之和。

## 交班与裁决

交运文本是 V1 JSON，外层含 `version`、`artifact_id`、`source` 和 `body`。来源包含 `station`、`revision_id`、`analysis_id`。正文携带布尔参考资格 `anchored` 和 `bands` 列表，列表项为带名及有理实虚部文本。计算身份时按带名排序，并将数字规范化。身份用于核对声明与收到的内容。复投同一身份须再次通过核验，成功后复用原实收号，保全首次合法提交的交运文本。站库保管原测和参考记录。

复检按名称对齐两件，各请求带均须存在，包括权重为零的带。权重无量纲，非负且至少一带为正。已锚定件使用公共参考，未锚定件的全部带共用一次未知单位相位转动，两件缺参考时转动可各自独立。中心把同名带响应相加，计算模平方后加权。整项在所有相容相位下恒定时，`outcome.status` 为 `exact`，`outcome.energy` 为 `Fraction`，包括确定的零。整项随相位变化时状态为 `undetermined`，能量为 `None`。单位为 U²。

输入错误由 `ValueError` 表达。单号读取找不到记录时返回 `None`，无起始修订时勘误链为空。SQLite 签存异常由原数据库异常报告，报告与成功回执一并回滚。重新打开数据库后，旧报告沿原号指向原有签存快照。

## 样例核对

甲在低带和高带的响应分别为 1、−1，缺公共参考。乙已锚定，两带响应都是 1。两带等权时相位相关的交叉项相消，签出 4 U²。只查低带时能量随相位变化。甲勘误为两带均为 1 后，新双带报告也为不可确定，原报告仍按原号签存为 4 U²。
