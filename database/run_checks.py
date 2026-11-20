"""Execute the project SQL and check it against the original seed fixtures."""

import argparse
import csv
import getpass
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
SPEC = json.loads((ROOT.parent / "docs/数据库实现规格.json").read_text())
DB = SPEC["database"]["name"]
SETUP = (
    "SET NAMES utf8mb4 COLLATE utf8mb4_0900_as_cs;\n"
    "SET SESSION time_zone = '+08:00';\n"
    "SET SESSION sql_mode = '" + SPEC["database"]["sql_mode"] + "';\n"
    "SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;\n"
)
EXPECTED_ROWS = {
    "users": 8, "canteens": 3, "stalls": 6, "dining_events": 12,
    "registrations": 25, "taste_tags": 6, "user_taste_preferences": 12,
    "event_taste_tags": 17, "stall_favorites": 8, "event_reviews": 3,
}
EXPECTED_OBJECTS = {
    "tables": 10, "columns": 39, "primary_keys": 10, "unique_keys": 2,
    "foreign_keys": 12, "checks": 13, "indexes": 21, "triggers": 1,
}


def quoted(value):
    return "'" + str(value).replace("'", "''") + "'"


class SqlError(RuntimeError):
    def __init__(self, message):
        super().__init__(message)
        match = re.search(r"ERROR (\d+)", message)
        self.code = int(match.group(1)) if match else None


class MySQL:
    def __init__(self, args):
        executable = shutil.which(args.mysql)
        if not executable:
            raise RuntimeError("没有找到 mysql 客户端，请通过 --mysql 指定路径。")
        self.command = [
            executable, "--protocol=TCP", "--host=" + args.host,
            "--port=" + str(args.port), "--user=" + args.user,
            "--connect-timeout=5", "--default-character-set=utf8mb4",
            "--batch", "--raw", "--column-names", "--skip-force",
        ]
        self.env = dict(os.environ)
        if args.prompt_password:
            self.env["MYSQL_PWD"] = getpass.getpass("MySQL password: ")

    def execute(self, sql, use_database=True):
        prefix = SETUP + ("USE " + DB + ";\n" if use_database else "")
        process = subprocess.run(
            self.command, input=prefix + sql, text=True,
            encoding="utf-8", capture_output=True, env=self.env,
        )
        if process.returncode:
            raise SqlError(process.stderr.strip())
        return process.stdout

    def rows(self, sql):
        output = self.execute(sql)
        return list(csv.DictReader(io.StringIO(output), delimiter="\t"))


def sections():
    text = (ROOT / "verify.sql").read_text()
    chunks = re.split(r"^-- @section ([A-Z_]+)\s*$", text, flags=re.M)
    return {chunks[i]: chunks[i + 1].strip() for i in range(1, len(chunks), 2)}


def insert_sql(table, values):
    return (
        "INSERT INTO " + table + " (" + ", ".join(values) + ") VALUES ("
        + ", ".join(values.values()) + ");"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--mysql", default="mysql")
    parser.add_argument("--prompt-password", action="store_true")
    parser.add_argument("--initialize", action="store_true", help="Create schema and seed in an empty project database")
    parser.add_argument("--environment-label", default="本地 MySQL")
    args = parser.parse_args()
    client = MySQL(args)
    result_dir = ROOT / "results"
    result_dir.mkdir(exist_ok=True)
    env_rows = client.rows(
        "SELECT VERSION() AS mysql_version, CURRENT_TIMESTAMP AS executed_at, "
        "@@session.time_zone AS time_zone, @@session.transaction_isolation AS isolation_level, "
        "@@session.collation_connection AS collation;"
    ) if not args.initialize else None
    if args.initialize:
        occupied = client.execute(
            "SELECT COUNT(*) AS table_count FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = " + quoted(DB) + ";", use_database=False,
        )
        if int(occupied.strip().splitlines()[-1]):
            raise RuntimeError("业务库已有表；--initialize 只用于空库，现有表未修改。")
        client.execute((ROOT / "schema.sql").read_text(), use_database=False)
        print("schema.sql 执行成功。", flush=True)
        client.execute((ROOT / "seed.sql").read_text())
        print("seed.sql 执行成功。", flush=True)
        env_rows = client.rows(
            "SELECT VERSION() AS mysql_version, CURRENT_TIMESTAMP AS executed_at, "
            "@@session.time_zone AS time_zone, @@session.transaction_isolation AS isolation_level, "
            "@@session.collation_connection AS collation;"
        )
    tests, evidence = [], {}
    sql_sections = sections()
    prefix = sql_sections["SESSION"] + "\n"

    def query_section(name, user_id=1, canteen_id=None):
        params = (
            "\nSET @verify_user_id = " + str(user_id) + ";\n"
            "SET @verify_canteen_id = " + ("NULL" if canteen_id is None else str(canteen_id)) + ";\n"
        )
        return client.rows(prefix + params + sql_sections[name])

    def run(name, callback):
        started = time.monotonic()
        item = {"name": name}
        try:
            item["evidence"] = callback()
            item["passed"] = True
        except (AssertionError, SqlError, KeyError, ValueError) as error:
            item["passed"] = False
            item["error"] = str(error) or "结果与预期不符"
        item["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        tests.append(item)
        print(("PASS " if item["passed"] else "FAIL ") + name, flush=True)

    def metadata():
        columns = client.rows(
            "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA, ORDINAL_POSITION "
            "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME, ORDINAL_POSITION;"
        )
        indexes = client.rows(
            "SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, INDEX_TYPE, SEQ_IN_INDEX, COLUMN_NAME "
            "FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;"
        )
        fks = client.rows(
            "SELECT k.TABLE_NAME, k.CONSTRAINT_NAME, k.COLUMN_NAME, k.REFERENCED_TABLE_NAME, k.REFERENCED_COLUMN_NAME, k.ORDINAL_POSITION, r.UPDATE_RULE, r.DELETE_RULE "
            "FROM information_schema.KEY_COLUMN_USAGE AS k JOIN information_schema.REFERENTIAL_CONSTRAINTS AS r "
            "ON r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME "
            "WHERE k.CONSTRAINT_SCHEMA = DATABASE() ORDER BY k.TABLE_NAME, k.CONSTRAINT_NAME, k.ORDINAL_POSITION;"
        )
        checks = client.rows(
            "SELECT TABLE_NAME, CONSTRAINT_NAME, ENFORCED FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_TYPE = 'CHECK';"
        )
        for table in SPEC["tables"]:
            name = table["table"]
            actual_columns = [c for c in columns if c["TABLE_NAME"] == name]
            assert [c["COLUMN_NAME"] for c in actual_columns] == [c["name"] for c in table["columns"]], name
            for actual, expected in zip(actual_columns, table["columns"]):
                assert actual["COLUMN_TYPE"].lower() == expected["type"].lower().replace("(0)", ""), (name, expected["name"], actual)
                assert (actual["IS_NULLABLE"] == "YES") == expected["nullable"]
                assert ("auto_increment" in actual["EXTRA"]) == expected["auto_increment"]
                wanted = expected["default_sql"]
                wanted = "NULL" if wanted is None or wanted == "NULL" else wanted.strip("'").lower().replace("()", "")
                got = actual["COLUMN_DEFAULT"]
                got = got if got == "NULL" else got.lower().replace("()", "")
                assert got == wanted, (name, expected["name"], got, wanted)
            expected_indexes = [table["primary_key"]] + table["unique_keys"] + table["indexes"]
            actual_names = {i["INDEX_NAME"] for i in indexes if i["TABLE_NAME"] == name}
            assert actual_names == {i["name"] for i in expected_indexes}, name
            for index in expected_indexes:
                actual = [i for i in indexes if i["TABLE_NAME"] == name and i["INDEX_NAME"] == index["name"]]
                assert [i["COLUMN_NAME"] for i in actual] == index["columns"]
                assert all(i["INDEX_TYPE"] == "BTREE" for i in actual)
                expected_unique = index in [table["primary_key"]] + table["unique_keys"]
                assert all((i["NON_UNIQUE"] == "0") == expected_unique for i in actual)
            actual_fk_names = {f["CONSTRAINT_NAME"] for f in fks if f["TABLE_NAME"] == name}
            assert actual_fk_names == {f["name"] for f in table["foreign_keys"]}
            for fk in table["foreign_keys"]:
                actual = [f for f in fks if f["TABLE_NAME"] == name and f["CONSTRAINT_NAME"] == fk["name"]]
                assert [f["COLUMN_NAME"] for f in actual] == fk["columns"]
                assert [f["REFERENCED_COLUMN_NAME"] for f in actual] == fk["reference_columns"]
                assert all(f["REFERENCED_TABLE_NAME"] == fk["reference_table"] and f["DELETE_RULE"] == fk["on_delete"] and f["UPDATE_RULE"] == fk["on_update"] for f in actual)
            assert {c["CONSTRAINT_NAME"] for c in checks if c["TABLE_NAME"] == name} == {c["name"] for c in table["checks"]}
        assert all(c["ENFORCED"] == "YES" for c in checks)
        table_settings = client.rows(
            "SELECT ENGINE, TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE();"
        )
        assert all(t["ENGINE"] == "InnoDB" and t["TABLE_COLLATION"] == "utf8mb4_0900_as_cs" for t in table_settings)
        trigger = client.rows(
            "SELECT TRIGGER_NAME, EVENT_MANIPULATION, ACTION_TIMING, EVENT_OBJECT_TABLE FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA = DATABASE();"
        )
        assert trigger == [{
            "TRIGGER_NAME": "trg_dining_events_ai_host_registration", "EVENT_MANIPULATION": "INSERT",
            "ACTION_TIMING": "AFTER", "EVENT_OBJECT_TABLE": "dining_events",
        }]
        return {"columns": len(columns), "foreign_keys": len({f["CONSTRAINT_NAME"] for f in fks}), "checks": len(checks), "index_names": sum(len(t["indexes"]) + len(t["unique_keys"]) + 1 for t in SPEC["tables"])}

    def expected_map(section, key, value, expected):
        rows = query_section(section)
        actual = {r[key]: int(r[value]) for r in rows}
        assert actual == expected, (actual, expected)
        evidence[section] = rows
        return actual

    run("元数据与实现规格一致", metadata)
    run("数据库对象数量", lambda: expected_map("OBJECTS", "object_type", "actual_count", EXPECTED_OBJECTS))
    run("测试数据行数", lambda: expected_map("ROW_COUNTS", "table_name", "actual_count", EXPECTED_ROWS))
    run("发起人占位、人数与评价数据一致", lambda: expected_map("INVARIANTS", "rule_name", "violation_count", {
        "missing_or_changed_host_registration": 0, "over_capacity": 0, "ineligible_review": 0,
    }))

    def recommendations(user_id, expected_ids, expected_scores):
        rows = query_section("RECOMMENDATIONS", user_id=user_id)
        assert [int(r["event_id"]) for r in rows] == expected_ids, rows
        assert [int(r["match_score"]) for r in rows] == expected_scores, rows
        evidence["recommendations_user_" + str(user_id)] = rows
        return rows

    run("alice 推荐排序与排除条件", lambda: recommendations(1, [2, 1, 5, 6, 10, 12], [9, 6, 0, 0, 0, 0]))
    run("erin 无偏好用户推荐", lambda: recommendations(5, [4, 1, 2, 6, 10, 11], [0, 0, 0, 0, 0, 0]))

    def stats():
        rows = query_section("PERSONAL_STATS")
        actual = {int(r["user_id"]): [int(r["initiated_count"]), int(r["participated_count"])] for r in rows}
        expected = {1: [2, 1], 2: [1, 1], 3: [2, 0], 4: [2, 1], 5: [1, 0], 6: [1, 0], 7: [1, 1], 8: [1, 1]}
        assert actual == expected, actual
        evidence["PERSONAL_STATS"] = rows
        return actual
    run("八个用户的个人统计", stats)

    def heatmap(canteen, expected_total):
        rows = query_section("HEATMAP", canteen_id=canteen)
        assert len(rows) == 168
        keys = {(int(r["weekday_no"]), int(r["hour_no"])) for r in rows}
        assert keys == {(d, h) for d in range(1, 8) for h in range(24)}
        assert sum(int(r["event_count"]) for r in rows) == expected_total
        nonzero = [r for r in rows if int(r["event_count"])]
        evidence["heatmap_" + str(canteen)] = nonzero
        return {"cells": len(rows), "total_events": expected_total, "nonzero_cells": nonzero}
    run("全部食堂热力图", lambda: heatmap(None, 11))
    run("第一食堂热力图", lambda: heatmap(1, 3))
    run("第二食堂热力图", lambda: heatmap(2, 5))
    run("第三食堂热力图", lambda: heatmap(3, 3))

    bases = {
        "users": {"username": "'check_user'", "nickname": "'测试用户'", "password_hash": "'validation-only-hash'", "created_at": "@case_time"},
        "canteens": {"canteen_name": "'测试食堂'"},
        "stalls": {"canteen_id": "1", "stall_name": "'测试档口'"},
        "dining_events": {"host_user_id": "5", "stall_id": "1", "title": "'测试饭局'", "meal_time": "DATE_ADD(@case_time, INTERVAL 1 DAY)", "capacity": "3", "created_at": "@case_time"},
        "registrations": {"event_id": "12", "user_id": "6", "registration_status": "'JOINED'", "last_joined_at": "@case_time"},
        "taste_tags": {"tag_name": "'清淡'"},
        "user_taste_preferences": {"user_id": "5", "tag_id": "1"},
        "event_taste_tags": {"event_id": "12", "tag_id": "1"},
        "stall_favorites": {"user_id": "5", "stall_id": "1", "favorited_at": "@case_time"},
        "event_reviews": {"event_id": "7", "user_id": "7", "rating": "4", "reviewed_at": "@case_time"},
    }

    def reject(sql, error_code, constraint=None):
        try:
            client.execute("SET @case_time = CURRENT_TIMESTAMP;\nSTART TRANSACTION;\n" + sql + "\nROLLBACK;")
        except SqlError as error:
            assert error.code == error_code, (error_code, error.code, str(error))
            if constraint:
                assert constraint in str(error), (constraint, str(error))
            return {"expected_error": error_code, "actual_error": error.code, "constraint": constraint}
        raise AssertionError("写入未被拒绝")

    def invalid(name, table, changes, code, constraint=None):
        values = {**bases[table], **changes}
        run(name, lambda: reject(insert_sql(table, values), code, constraint))

    for table in SPEC["tables"]:
        for column in table["columns"]:
            if not column["nullable"] and not column["auto_increment"]:
                invalid("非空 " + table["table"] + "." + column["name"], table["table"], {column["name"]: "NULL"}, 1048)

    duplicate_keys = {
        "users": {"user_id": "1"}, "canteens": {"canteen_id": "1"}, "stalls": {"stall_id": "1"},
        "dining_events": {"event_id": "1"}, "registrations": {"event_id": "1", "user_id": "2"},
        "taste_tags": {"tag_id": "1"}, "user_taste_preferences": {"user_id": "1", "tag_id": "1"},
        "event_taste_tags": {"event_id": "1", "tag_id": "1"},
        "stall_favorites": {"user_id": "1", "stall_id": "1"}, "event_reviews": {"event_id": "7", "user_id": "1"},
    }
    for table, changes in duplicate_keys.items():
        invalid("主键重复 " + table, table, changes, 1062)
    invalid("用户名唯一", "users", {"username": "'alice'"}, 1062, "uq_users_username")
    invalid("标签名称唯一", "taste_tags", {}, 1062, "uq_taste_tags_name")
    for table in SPEC["tables"]:
        for fk in table["foreign_keys"]:
            changes = {fk["columns"][0]: "4000000000"} if len(fk["columns"]) == 1 else {"event_id": "1", "user_id": "7"}
            invalid("外键 " + fk["name"], table["table"], changes, 1452, fk["name"])

    check_cases = [
        ("users", {"username": "' alice'"}, "ck_users_username"),
        ("users", {"nickname": "'  '"}, "ck_users_nickname"),
        ("users", {"preferred_slot": "'SNACK'"}, "ck_users_preferred_slot"),
        ("canteens", {"canteen_name": "'  '"}, "ck_canteens_name"),
        ("stalls", {"stall_name": "'  '"}, "ck_stalls_name"),
        ("dining_events", {"title": "'  '"}, "ck_events_title"),
        ("dining_events", {"capacity": "1"}, "ck_events_capacity"),
        ("dining_events", {"meal_time": "@case_time"}, "ck_events_meal_time"),
        ("dining_events", {"cancelled_at": "DATE_ADD(@case_time, INTERVAL 1 DAY)"}, "ck_events_cancel_time"),
        ("registrations", {"registration_status": "'WAIT'"}, "ck_registrations_status"),
        ("registrations", {"registration_status": "'EXITED'", "last_exited_at": "NULL"}, "ck_registrations_exit_time"),
        ("taste_tags", {"tag_name": "'甜辣'"}, "ck_taste_tags_name"),
        ("event_reviews", {"rating": "6"}, "ck_reviews_rating"),
    ]
    for table, changes, constraint in check_cases:
        invalid("CHECK " + constraint, table, changes, 3819, constraint)
    for table in SPEC["tables"]:
        for column in table["columns"]:
            size = re.fullmatch(r"VARCHAR\((\d+)\)", column["type"])
            if size:
                invalid("长度 " + table["table"] + "." + column["name"], table["table"], {
                    column["name"]: "REPEAT('x', " + str(int(size.group(1)) + 1) + ")",
                }, 1406)
    invalid("报名状态区分大小写", "registrations", {"registration_status": "'joined'"}, 3819, "ck_registrations_status")
    invalid("偏好时段区分大小写", "users", {"preferred_slot": "'lunch'"}, 3819, "ck_users_preferred_slot")
    invalid("人数上限超过整数范围", "dining_events", {"capacity": "65536"}, 1264)
    invalid("评分不能写负数", "event_reviews", {"rating": "-1"}, 1264)
    for name, sql in [
        ("食堂删除引用限制", "DELETE FROM canteens WHERE canteen_id = 1;"),
        ("档口删除引用限制", "DELETE FROM stalls WHERE stall_id = 3;"),
        ("饭局删除引用限制", "DELETE FROM dining_events WHERE event_id = 7;"),
        ("评价引用的报名记录删除限制", "DELETE FROM registrations WHERE event_id = 7 AND user_id = 1;"),
    ]:
        run(name, lambda sql=sql: reject(sql, 1451))

    def positive(sql, expected):
        rows = client.rows("SET @case_time = CURRENT_TIMESTAMP;\nSTART TRANSACTION;\n" + sql + "\nROLLBACK;")
        assert rows == expected, rows
        return rows

    new_event = insert_sql("dining_events", bases["dining_events"]) + "\nSET @new_event = LAST_INSERT_ID();\n"
    run("发起人报名触发器", lambda: positive(new_event + """
        SELECT COUNT(*) AS host_rows FROM registrations AS r JOIN dining_events AS e ON e.event_id = r.event_id
        WHERE e.event_id = @new_event AND r.user_id = e.host_user_id AND r.registration_status = 'JOINED'
          AND r.last_joined_at = e.created_at AND r.last_exited_at IS NULL;
    """, [{"host_rows": "1"}]))
    run("退出后重新报名复用记录", lambda: positive("""
        UPDATE registrations SET registration_status = 'EXITED', last_exited_at = @case_time WHERE event_id = 1 AND user_id = 4;
        UPDATE registrations SET registration_status = 'JOINED', last_joined_at = @case_time WHERE event_id = 1 AND user_id = 4;
        SELECT COUNT(*) AS row_count, MIN(registration_status) AS registration_status,
               SUM(last_exited_at = @case_time) AS retained_exit_time
        FROM registrations WHERE event_id = 1 AND user_id = 4;
    """, [{"row_count": "1", "registration_status": "JOINED", "retained_exit_time": "1"}]))
    run("取消保留报名记录", lambda: positive("""
        UPDATE dining_events SET cancelled_at = @case_time WHERE event_id = 1;
        SELECT COUNT(*) AS row_count, SUM(registration_status = 'JOINED') AS joined_count FROM registrations WHERE event_id = 1;
    """, [{"row_count": "2", "joined_count": "2"}]))
    run("无人报名饭局的关联删除顺序", lambda: positive(new_event + """
        INSERT INTO event_taste_tags (event_id, tag_id) VALUES (@new_event, 1);
        DELETE FROM event_taste_tags WHERE event_id = @new_event;
        DELETE FROM registrations WHERE event_id = @new_event;
        DELETE FROM dining_events WHERE event_id = @new_event;
        SELECT COUNT(*) AS event_count FROM dining_events WHERE event_id = @new_event;
    """, [{"event_count": "0"}]))
    run("已退出用户仍影响删除资格", lambda: positive("""
        SELECT COUNT(*) AS prior_other_registration FROM registrations AS r JOIN dining_events AS e ON e.event_id = r.event_id
        WHERE e.event_id = 5 AND r.user_id <> e.host_user_id;
    """, [{"prior_other_registration": "1"}]))
    run("用户名区分大小写", lambda: positive(insert_sql("users", {
        **bases["users"], "username": "'Alice'",
    }) + "\nSELECT COUNT(*) AS user_count FROM users WHERE username IN ('alice', 'Alice');", [{"user_count": "2"}]))
    run("验证后原始测试数据行数保持一致", lambda: expected_map("ROW_COUNTS", "table_name", "actual_count", EXPECTED_ROWS))
    run("验证后业务数据仍一致", lambda: expected_map("INVARIANTS", "rule_name", "violation_count", {
        "missing_or_changed_host_registration": 0, "over_capacity": 0, "ineligible_review": 0,
    }))

    plans = []
    for name in ("PLAN_PUBLIC", "PLAN_STALL", "PLAN_COUNTS", "PLAN_USER"):
        try:
            rows = query_section(name)
            plans.append({"section": name, "rows": rows})
            tests.append({"name": "执行计划 " + name, "passed": True, "evidence": rows})
        except SqlError as error:
            tests.append({"name": "执行计划 " + name, "passed": False, "error": str(error)})
    full_output = client.execute((ROOT / "verify.sql").read_text())
    (result_dir / "verify-output.txt").write_text(full_output)
    (result_dir / "explain.json").write_text(json.dumps(plans, ensure_ascii=False, indent=2) + "\n")
    evidence["EVENTS"] = query_section("EVENTS")
    report = {
        "environment_label": args.environment_label,
        "connection": {"host": args.host, "port": args.port, "user": args.user, "database": DB},
        "environment": env_rows[0], "scope": "数据库结构与 SQL 规则验证；后端接口与并发联调属于 step11",
        "total": len(tests), "passed": sum(t["passed"] for t in tests),
        "failed": sum(not t["passed"] for t in tests), "tests": tests, "query_evidence": evidence,
    }
    (result_dir / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("验证结果：" + str(report["passed"]) + "/" + str(report["total"]) + " 通过。", flush=True)
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
