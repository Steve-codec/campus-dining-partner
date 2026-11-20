-- 相对执行当天生成测试数据；在空表执行一次。
-- 八个演示账号的统一口令为 Dining123!，password_hash 使用 bcrypt 格式。
-- 发起人报名记录由触发器生成，本脚本只补充普通参与者。
SET NAMES utf8mb4 COLLATE utf8mb4_0900_as_cs;
SET SESSION time_zone = '+08:00';
SET SESSION sql_mode = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
USE `campus_dining_partner`;
SET @seed_day = CURRENT_DATE();
SET @seed_now = CURRENT_TIMESTAMP;
SET @event_created = TIMESTAMP(DATE_SUB(@seed_day, INTERVAL 7 DAY), '09:00:00');
SET @participant_joined = DATE_ADD(@event_created, INTERVAL 1 DAY);
START TRANSACTION;

INSERT INTO users (user_id, username, nickname, password_hash, preferred_slot, created_at) VALUES
  (1, 'alice', '小李', '$2y$10$sY.KBP0nTZH32RE0WQngP.ndsvM3deoFO9tIf2biWRDYx1wNvVQVO', 'LUNCH', TIMESTAMP(DATE_SUB(@seed_day, INTERVAL 30 DAY), '09:00:00')),
  (2, 'bob', '小悦', '$2y$10$7/IppUnTFw.4zMlkdYjN9.u/vEy3yUzBZbWOPJ6kCoVpxf9LFasgm', 'DINNER', TIMESTAMP(DATE_SUB(@seed_day, INTERVAL 30 DAY), '09:00:00')),
  (3, 'carol', '小曹', '$2y$10$Zhj1rrIvnPxXK1mPNlzzJOHUCjf8YEa.rEecMZPXRgmwDE0HcNCC.', 'BREAKFAST', TIMESTAMP(DATE_SUB(@seed_day, INTERVAL 30 DAY), '09:00:00')),
  (4, 'dave', '小陈', '$2y$10$VffoPrdNGd9ma86P9NjhDu2IEAg4JpGBonLJoEShLXiquuOTnX5T6', 'LUNCH', TIMESTAMP(DATE_SUB(@seed_day, INTERVAL 30 DAY), '09:00:00')),
  (5, 'erin', '小周', '$2y$10$LjPBoGMOLBxQzNZcN8hkFOmUnsQsO4Gg3n/0p8nc4WIOzhhY5nYHq', NULL, TIMESTAMP(DATE_SUB(@seed_day, INTERVAL 30 DAY), '09:00:00')),
  (6, 'frank', '小吴', '$2y$10$d1hpbhB.IJ5.0xqK2L9wLOffMiSB1IZZO27Zb1BBxNlj/MEpJ20jG', 'LATE_NIGHT', TIMESTAMP(DATE_SUB(@seed_day, INTERVAL 30 DAY), '09:00:00')),
  (7, 'grace', '小林', '$2y$10$uCK1B2UQZajRRN7XtmrmH.Zt5zQwh5jy5uCyPE/LFa1OWSpt6cv4G', 'DINNER', TIMESTAMP(DATE_SUB(@seed_day, INTERVAL 30 DAY), '09:00:00')),
  (8, 'heidi', '小赵', '$2y$10$Vmh8mp08BWdZJLphV6zbOe6hCtSqW1q3xZxqvr8RZIGE9p22cTVvy', 'LUNCH', TIMESTAMP(DATE_SUB(@seed_day, INTERVAL 30 DAY), '09:00:00'));

INSERT INTO canteens (canteen_id, canteen_name) VALUES (1, '第一食堂'), (2, '第二食堂'), (3, '第三食堂');
INSERT INTO stalls (stall_id, canteen_id, stall_name) VALUES
  (1, 1, '家常小炒'), (2, 1, '麻辣香锅'), (3, 2, '素食轻食'),
  (4, 2, '面点早餐'), (5, 3, '夜宵砂锅'), (6, 3, '特色盖饭');
INSERT INTO taste_tags (tag_id, tag_name) VALUES
  (1, '清淡'), (2, '香辣'), (3, '麻辣'), (4, '甜口'), (5, '咸鲜'), (6, '素食');

INSERT INTO dining_events (event_id, host_user_id, stall_id, title, meal_time, capacity, description, cancelled_at, created_at) VALUES
  (1, 2, 1, '家常午餐拼桌', TIMESTAMP(DATE_ADD(@seed_day, INTERVAL 1 DAY), '12:00:00'), 4, '演示饭局：家常午餐拼桌', NULL, @event_created),
  (2, 3, 3, '清淡素食午餐', TIMESTAMP(DATE_ADD(@seed_day, INTERVAL 1 DAY), '12:30:00'), 4, '演示饭局：清淡素食午餐', NULL, @event_created),
  (3, 4, 2, '香锅双人饭局', TIMESTAMP(DATE_ADD(@seed_day, INTERVAL 1 DAY), '18:00:00'), 2, '演示饭局：香锅双人饭局', NULL, @event_created),
  (4, 1, 4, '早餐面点约饭', TIMESTAMP(DATE_ADD(@seed_day, INTERVAL 1 DAY), '08:00:00'), 3, '演示饭局：早餐面点约饭', NULL, @event_created),
  (5, 5, 2, '晚餐香锅小队', TIMESTAMP(DATE_ADD(@seed_day, INTERVAL 2 DAY), '18:30:00'), 4, '演示饭局：晚餐香锅小队', NULL, @event_created),
  (6, 6, 5, '夜宵砂锅拼桌', TIMESTAMP(DATE_ADD(@seed_day, INTERVAL 2 DAY), '22:00:00'), 3, '演示饭局：夜宵砂锅拼桌', NULL, @event_created),
  (7, 7, 3, '昨日素食午餐', TIMESTAMP(DATE_ADD(@seed_day, INTERVAL -1 DAY), '12:00:00'), 4, '演示饭局：昨日素食午餐', NULL, @event_created),
  (8, 8, 6, '前日盖饭晚餐', TIMESTAMP(DATE_ADD(@seed_day, INTERVAL -2 DAY), '18:00:00'), 3, '演示饭局：前日盖饭晚餐', NULL, @event_created),
  (9, 2, 1, '已取消的午餐', TIMESTAMP(DATE_ADD(@seed_day, INTERVAL 3 DAY), '12:00:00'), 4, '演示饭局：已取消的午餐', DATE_SUB(@seed_now, INTERVAL 1 HOUR), @event_created),
  (10, 4, 6, '退出后可再报名', TIMESTAMP(DATE_ADD(@seed_day, INTERVAL 4 DAY), '19:00:00'), 4, '演示饭局：退出后可再报名', NULL, @event_created),
  (11, 1, 3, '本人发起的素食饭局', TIMESTAMP(DATE_ADD(@seed_day, INTERVAL 5 DAY), '13:00:00'), 3, '演示饭局：本人发起的素食饭局', NULL, @event_created),
  (12, 3, 4, '下周早餐拼桌', TIMESTAMP(DATE_ADD(@seed_day, INTERVAL 6 DAY), '08:30:00'), 3, '演示饭局：下周早餐拼桌', NULL, @event_created);

INSERT INTO registrations (event_id, user_id, registration_status, last_joined_at, last_exited_at) VALUES
  (1, 4, 'JOINED', @participant_joined, NULL),
  (2, 8, 'JOINED', @participant_joined, NULL),
  (3, 6, 'JOINED', @participant_joined, NULL),
  (4, 3, 'JOINED', @participant_joined, NULL),
  (5, 2, 'EXITED', @participant_joined, DATE_ADD(@participant_joined, INTERVAL 1 HOUR)),
  (6, 2, 'JOINED', @participant_joined, NULL),
  (7, 1, 'JOINED', @participant_joined, NULL),
  (7, 4, 'JOINED', @participant_joined, NULL),
  (8, 1, 'EXITED', @participant_joined, DATE_ADD(@participant_joined, INTERVAL 1 HOUR)),
  (8, 2, 'JOINED', @participant_joined, NULL),
  (9, 1, 'JOINED', @participant_joined, NULL),
  (10, 1, 'EXITED', @participant_joined, DATE_ADD(@participant_joined, INTERVAL 1 HOUR)),
  (12, 5, 'JOINED', @participant_joined, NULL);

INSERT INTO user_taste_preferences (user_id, tag_id) VALUES (1, 1), (1, 6), (2, 2), (2, 3), (3, 4), (4, 1), (4, 5), (6, 2), (6, 3), (7, 1), (7, 6), (8, 5);
INSERT INTO event_taste_tags (event_id, tag_id) VALUES (1, 1), (1, 5), (2, 1), (2, 6), (3, 2), (3, 3), (4, 4), (5, 2), (5, 3), (6, 3), (7, 1), (7, 6), (8, 5), (9, 1), (10, 5), (11, 6), (12, 4);
INSERT INTO stall_favorites (user_id, stall_id, favorited_at) VALUES
  (1, 1, DATE_ADD(@event_created, INTERVAL 2 DAY)),
  (1, 3, DATE_ADD(@event_created, INTERVAL 2 DAY)),
  (2, 2, DATE_ADD(@event_created, INTERVAL 2 DAY)),
  (3, 4, DATE_ADD(@event_created, INTERVAL 2 DAY)),
  (4, 3, DATE_ADD(@event_created, INTERVAL 2 DAY)),
  (6, 5, DATE_ADD(@event_created, INTERVAL 2 DAY)),
  (7, 6, DATE_ADD(@event_created, INTERVAL 2 DAY)),
  (8, 1, DATE_ADD(@event_created, INTERVAL 2 DAY));

INSERT INTO event_reviews (event_id, user_id, rating, content, reviewed_at)
SELECT event_id, 1, 5, '时间地点清楚，饭搭子体验很好。', DATE_ADD(meal_time, INTERVAL 1 HOUR) FROM dining_events WHERE event_id = 7;
INSERT INTO event_reviews (event_id, user_id, rating, content, reviewed_at)
SELECT event_id, 4, 4, '口味合适，交流愉快。', DATE_ADD(meal_time, INTERVAL 2 HOUR) FROM dining_events WHERE event_id = 7;
INSERT INTO event_reviews (event_id, user_id, rating, content, reviewed_at)
SELECT event_id, 2, 4, NULL, DATE_ADD(meal_time, INTERVAL 1 HOUR) FROM dining_events WHERE event_id = 8;

COMMIT;
