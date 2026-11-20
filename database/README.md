# 数据库初始化与验证

本目录实现 step8 至 step10。脚本已在独立的 MySQL 8.0.46 临时实例中完成建表、导入和 108 项验证；现有 `localhost:3306` 因 root 鉴权未通过，尚未执行本次导入。临时实例的结果见[数据库运行验证记录](../docs/数据库运行验证记录.md)。

## 1 运行环境

- 业务库：`campus_dining_partner`。
- MySQL：8.0.46，存储引擎 InnoDB。
- 字符集与排序规则：`utf8mb4`、`utf8mb4_0900_as_cs`。
- 会话时区：`+08:00`；事务隔离级别：`REPEATABLE READ`。
- 每个 SQL 文件均设置会话参数与业务库，直接使用已有的 MySQL 连接执行。

## 2 在 DataGrip 中执行

1. 打开已连接的 `@localhost` 数据源，使用你保存的 MySQL 连接凭据。
2. 在该数据源的查询控制台中，执行 [schema.sql](./schema.sql) 的全部语句，创建业务库、十张表、约束、索引和触发器。
3. 上一步执行完成后，再执行 [seed.sql](./seed.sql) 的全部语句，导入测试数据。
4. 执行 [verify.sql](./verify.sql) 的全部语句，查看结构数量、记录数量、饭局状态、推荐、统计、热力图和执行计划。
5. 刷新数据库列表，勾选 `campus_dining_partner` 架构，展开表列表查看数据。

schema.sql 与 seed.sql 各执行一次，verify.sql 可以重复执行。SQL 文件不包含清空库或清空表的语句。

verify.sql 中的 `SESSION` 节设置查询参数。默认 `@verify_user_id = 1`，`@verify_canteen_id = NULL`；查看其他用户或单个食堂时，执行 SESSION 后修改对应变量，再执行目标查询节。

## 3 在终端执行

在仓库根目录执行，`-p` 后由 MySQL 客户端提示输入数据库密码：

```bash
mysql -h 127.0.0.1 -P 3306 -u root -p --default-character-set=utf8mb4 < database/schema.sql
mysql -h 127.0.0.1 -P 3306 -u root -p --default-character-set=utf8mb4 < database/seed.sql
mysql -h 127.0.0.1 -P 3306 -u root -p --default-character-set=utf8mb4 < database/verify.sql
```

也可以使用自动化入口一次完成空库初始化和完整验证：

```bash
python3 database/run_checks.py --initialize --prompt-password
```

已经执行 schema.sql 和 seed.sql 时，使用以下命令校验原始测试数据：

```bash
python3 database/run_checks.py --prompt-password
```

验证脚本只依赖 Python 3 标准库和 mysql 命令行客户端；可通过 `--host`、`--port`、`--user`、`--mysql` 指定连接与客户端位置。`--initialize` 只接受没有表的业务库。完整验证针对原始 seed 数据，联调新增或修改业务记录后，预期行数和预期推荐结果需要随数据调整。

## 4 测试数据

日期按 seed.sql 执行当天生成。未来饭局安排在次日至第六天，历史饭局安排在前一日和前两日；所有记录使用北京时间。

| 表 | 记录数 |
| --- | --- |
| users | 8 |
| canteens | 3 |
| stalls | 6 |
| dining_events | 12 |
| registrations | 25 |
| taste_tags | 6 |
| user_taste_preferences | 12 |
| event_taste_tags | 17 |
| stall_favorites | 8 |
| event_reviews | 3 |

共 100 条记录，其中 12 条发起人报名记录由触发器生成。seed.sql 只写入另外 13 条参与者报名记录。

| 饭局编号 | 场景 |
| --- | --- |
| 1 | 家常午餐，2 人报名、剩余 2 个名额 |
| 2 | 清淡素食午餐，alice 的最高分推荐 |
| 3 | 香锅双人局，已满员 |
| 4、11 | alice 本人发起的未来饭局 |
| 5 | 曾有其他用户报名并退出，只允许取消 |
| 6 | 夜宵时段，2 人报名、剩余 1 个名额 |
| 7、8 | 已开始的历史饭局，包含评价与退出记录 |
| 9 | 已取消，保留报名记录，不计入推荐和热力图 |
| 10 | alice 已退出，可以重新报名和获得推荐 |
| 12 | 早餐时段，erin 已报名 |

## 5 应用演示账号

用户名为 alice、bob、carol、dave、erin、frank、grace、heidi，用户编号依次为 1 至 8。应用演示口令统一为 `Dining123!`，数据库字段保存 bcrypt 摘要。后端认证模块按 bcrypt 格式校验这些种子账号。

DataGrip 的 root 是 MySQL 连接账号；alice 是业务库中的应用用户。应用演示口令用于后端登录联调。

## 6 验证内容与结果文件

- 元数据：十张表的字段顺序、类型、默认值、可空性、自增属性、主外键、索引和触发器。
- 约束实测：29 项非空、10 项主键、2 项唯一、12 项外键、13 项 CHECK、11 项字符串长度。
- 业务数据：推荐分与排序、无偏好推荐、个人统计、168 格热力图、发起人占位、退出重报、取消保留和删除关联顺序。
- 执行计划：公开饭局列表、档口饭局列表、报名人数统计、本人报名记录四项查询。

约束与业务写入用例在事务中验证后回滚，保留原始测试记录。自增编号会被测试消耗，记录数量保持不变。后端接口、权限处理与并发抢名额的联调留在 step11。

- [verification.json](./results/verification.json)：108 项验证明细、执行环境和查询证据。
- [verify-output.txt](./results/verify-output.txt)：verify.sql 的完整实际输出。
- [explain.json](./results/explain.json)：四项查询的实际执行计划。

重新运行 run_checks.py 会更新这三份结果文件；文件内的执行环境和时间标识本次结果来源。
