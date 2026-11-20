-- 各节可在 DataGrip 单独执行；SESSION 先执行一次。
-- 修改 @verify_user_id 可查看其他用户的推荐；@verify_canteen_id 为 NULL 时统计全部食堂。
-- @section SESSION
SET NAMES utf8mb4 COLLATE utf8mb4_0900_as_cs;
SET SESSION time_zone = '+08:00';
SET SESSION sql_mode = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
USE `campus_dining_partner`;
SET @verify_now = CURRENT_TIMESTAMP;
SET @verify_user_id = 1;
SET @verify_canteen_id = NULL;

-- @section OBJECTS
SELECT 'tables' AS object_type, COUNT(*) AS actual_count FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
UNION ALL SELECT 'columns', COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()
UNION ALL SELECT 'primary_keys', COUNT(*) FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_TYPE = 'PRIMARY KEY'
UNION ALL SELECT 'unique_keys', COUNT(*) FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_TYPE = 'UNIQUE'
UNION ALL SELECT 'foreign_keys', COUNT(*) FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_TYPE = 'FOREIGN KEY'
UNION ALL SELECT 'checks', COUNT(*) FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_TYPE = 'CHECK' AND ENFORCED = 'YES'
UNION ALL SELECT 'indexes', COUNT(*) FROM (SELECT TABLE_NAME, INDEX_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() GROUP BY TABLE_NAME, INDEX_NAME) AS index_names
UNION ALL SELECT 'triggers', COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA = DATABASE();

-- @section ROW_COUNTS
SELECT 'users' AS table_name, COUNT(*) AS actual_count FROM `users`
UNION ALL SELECT 'canteens', COUNT(*) FROM `canteens`
UNION ALL SELECT 'stalls', COUNT(*) FROM `stalls`
UNION ALL SELECT 'dining_events', COUNT(*) FROM `dining_events`
UNION ALL SELECT 'registrations', COUNT(*) FROM `registrations`
UNION ALL SELECT 'taste_tags', COUNT(*) FROM `taste_tags`
UNION ALL SELECT 'user_taste_preferences', COUNT(*) FROM `user_taste_preferences`
UNION ALL SELECT 'event_taste_tags', COUNT(*) FROM `event_taste_tags`
UNION ALL SELECT 'stall_favorites', COUNT(*) FROM `stall_favorites`
UNION ALL SELECT 'event_reviews', COUNT(*) FROM `event_reviews`;

-- @section EVENTS
WITH active_counts AS (
  SELECT event_id, COUNT(*) AS joined_count FROM registrations WHERE registration_status = 'JOINED' GROUP BY event_id
)
SELECT e.event_id, e.title, c.canteen_name, s.stall_name, e.meal_time, e.capacity,
       COALESCE(a.joined_count, 0) AS joined_count, e.capacity - COALESCE(a.joined_count, 0) AS remaining_capacity,
       CASE WHEN e.cancelled_at IS NOT NULL THEN 'CANCELLED' WHEN e.meal_time > @verify_now THEN 'UPCOMING' ELSE 'STARTED' END AS event_status
FROM dining_events AS e JOIN stalls AS s ON s.stall_id = e.stall_id JOIN canteens AS c ON c.canteen_id = s.canteen_id
LEFT JOIN active_counts AS a ON a.event_id = e.event_id ORDER BY e.event_id;

-- @section INVARIANTS
SELECT 'missing_or_changed_host_registration' AS rule_name, COUNT(*) AS violation_count
FROM dining_events AS e LEFT JOIN registrations AS r ON r.event_id = e.event_id AND r.user_id = e.host_user_id
WHERE r.user_id IS NULL OR r.registration_status <> 'JOINED' OR r.last_joined_at <> e.created_at
UNION ALL SELECT 'over_capacity', COUNT(*) FROM dining_events AS e
WHERE (SELECT COUNT(*) FROM registrations AS r WHERE r.event_id = e.event_id AND r.registration_status = 'JOINED') > e.capacity
UNION ALL SELECT 'ineligible_review', COUNT(*) FROM event_reviews AS v JOIN dining_events AS e ON e.event_id = v.event_id
JOIN registrations AS r ON r.event_id = v.event_id AND r.user_id = v.user_id
WHERE e.cancelled_at IS NOT NULL OR e.meal_time > @verify_now OR r.registration_status <> 'JOINED';

-- @section RECOMMENDATIONS
WITH active_counts AS (
  SELECT event_id, COUNT(*) AS joined_count FROM registrations WHERE registration_status = 'JOINED' GROUP BY event_id
), shared_tags AS (
  SELECT et.event_id, COUNT(*) AS shared_count FROM event_taste_tags AS et
  JOIN user_taste_preferences AS p ON p.tag_id = et.tag_id AND p.user_id = @verify_user_id GROUP BY et.event_id
)
SELECT e.event_id, e.title, e.meal_time, e.capacity - COALESCE(a.joined_count, 0) AS remaining_capacity,
       3 * COALESCE(t.shared_count, 0) + 2 * IF(f.user_id IS NULL, 0, 1) +
       IF(u.preferred_slot = CASE
         WHEN TIME(e.meal_time) >= '06:00:00' AND TIME(e.meal_time) < '10:00:00' THEN 'BREAKFAST'
         WHEN TIME(e.meal_time) >= '10:00:00' AND TIME(e.meal_time) < '15:00:00' THEN 'LUNCH'
         WHEN TIME(e.meal_time) >= '15:00:00' AND TIME(e.meal_time) < '21:00:00' THEN 'DINNER'
         ELSE 'LATE_NIGHT' END, 1, 0) AS match_score
FROM dining_events AS e JOIN users AS u ON u.user_id = @verify_user_id
LEFT JOIN active_counts AS a ON a.event_id = e.event_id LEFT JOIN shared_tags AS t ON t.event_id = e.event_id
LEFT JOIN stall_favorites AS f ON f.user_id = @verify_user_id AND f.stall_id = e.stall_id
WHERE e.cancelled_at IS NULL AND e.meal_time > @verify_now AND COALESCE(a.joined_count, 0) < e.capacity
  AND NOT EXISTS (SELECT 1 FROM registrations AS own WHERE own.event_id = e.event_id AND own.user_id = @verify_user_id AND own.registration_status = 'JOINED')
ORDER BY match_score DESC, e.meal_time ASC, e.event_id ASC LIMIT 10;

-- @section PERSONAL_STATS
SELECT u.user_id, u.username,
  (SELECT COUNT(*) FROM dining_events AS e WHERE e.host_user_id = u.user_id AND e.cancelled_at IS NULL) AS initiated_count,
  (SELECT COUNT(*) FROM registrations AS r JOIN dining_events AS e ON e.event_id = r.event_id
   WHERE r.user_id = u.user_id AND r.registration_status = 'JOINED' AND e.cancelled_at IS NULL AND e.meal_time <= @verify_now) AS participated_count
FROM users AS u ORDER BY u.user_id;

-- @section HEATMAP
WITH RECURSIVE weekdays AS (SELECT 1 AS weekday_no UNION ALL SELECT weekday_no + 1 FROM weekdays WHERE weekday_no < 7),
hours AS (SELECT 0 AS hour_no UNION ALL SELECT hour_no + 1 FROM hours WHERE hour_no < 23),
event_counts AS (
  SELECT WEEKDAY(e.meal_time) + 1 AS weekday_no, HOUR(e.meal_time) AS hour_no, COUNT(*) AS event_count
  FROM dining_events AS e JOIN stalls AS s ON s.stall_id = e.stall_id
  WHERE e.cancelled_at IS NULL AND (@verify_canteen_id IS NULL OR s.canteen_id = @verify_canteen_id)
  GROUP BY WEEKDAY(e.meal_time) + 1, HOUR(e.meal_time)
)
SELECT w.weekday_no, h.hour_no, COALESCE(c.event_count, 0) AS event_count
FROM weekdays AS w CROSS JOIN hours AS h LEFT JOIN event_counts AS c ON c.weekday_no = w.weekday_no AND c.hour_no = h.hour_no
ORDER BY w.weekday_no, h.hour_no;

-- @section PLAN_PUBLIC
EXPLAIN SELECT event_id, meal_time FROM dining_events WHERE cancelled_at IS NULL AND meal_time > @verify_now ORDER BY meal_time, event_id LIMIT 10;

-- @section PLAN_STALL
EXPLAIN SELECT event_id, meal_time FROM dining_events WHERE stall_id = 3 AND cancelled_at IS NULL AND meal_time > @verify_now ORDER BY meal_time, event_id;

-- @section PLAN_COUNTS
EXPLAIN SELECT COUNT(*) FROM registrations WHERE event_id = 1 AND registration_status = 'JOINED';

-- @section PLAN_USER
EXPLAIN SELECT event_id, registration_status FROM registrations WHERE user_id = 1;
