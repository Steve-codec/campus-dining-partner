-- 校园饭搭子数据库建表脚本；在空业务库执行一次。
-- 规格来源：docs/数据库实现规格.json
SET NAMES utf8mb4 COLLATE utf8mb4_0900_as_cs;
SET SESSION time_zone = '+08:00';
SET SESSION sql_mode = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
CREATE DATABASE IF NOT EXISTS `campus_dining_partner` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs;
USE `campus_dining_partner`;

CREATE TABLE `users` (
  `user_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户编号',
  `username` VARCHAR(32) NOT NULL COMMENT '登录用户名，去除首尾普通空格，区分大小写和重音，用户间唯一',
  `nickname` VARCHAR(32) NOT NULL COMMENT '昵称，允许重名，不能只含普通空格',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '后端生成的密码摘要',
  `preferred_slot` VARCHAR(10) NULL DEFAULT NULL COMMENT 'BREAKFAST、LUNCH、DINNER、LATE_NIGHT；NULL 表示无偏好',
  `created_at` DATETIME(0) NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间，创建后不刷新',
  PRIMARY KEY USING BTREE (`user_id`),
  UNIQUE KEY `uq_users_username` USING BTREE (`username`),
  CONSTRAINT `ck_users_username` CHECK (CHAR_LENGTH(TRIM(username)) > 0 AND username = TRIM(username)) ENFORCED,
  CONSTRAINT `ck_users_nickname` CHECK (CHAR_LENGTH(TRIM(nickname)) > 0) ENFORCED,
  CONSTRAINT `ck_users_preferred_slot` CHECK (preferred_slot IS NULL OR preferred_slot IN ('BREAKFAST', 'LUNCH', 'DINNER', 'LATE_NIGHT')) ENFORCED
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs COMMENT='用户';

CREATE TABLE `canteens` (
  `canteen_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '食堂编号',
  `canteen_name` VARCHAR(64) NOT NULL COMMENT '食堂显示名称，不能只含普通空格',
  PRIMARY KEY USING BTREE (`canteen_id`),
  CONSTRAINT `ck_canteens_name` CHECK (CHAR_LENGTH(TRIM(canteen_name)) > 0) ENFORCED
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs COMMENT='食堂';

CREATE TABLE `stalls` (
  `stall_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '档口编号',
  `canteen_id` INT UNSIGNED NOT NULL COMMENT '食堂编号',
  `stall_name` VARCHAR(64) NOT NULL COMMENT '档口显示名称，不能只含普通空格',
  PRIMARY KEY USING BTREE (`stall_id`),
  KEY `idx_stalls_canteen` USING BTREE (`canteen_id`),
  CONSTRAINT `fk_stalls_canteen` FOREIGN KEY (`canteen_id`) REFERENCES `canteens` (`canteen_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `ck_stalls_name` CHECK (CHAR_LENGTH(TRIM(stall_name)) > 0) ENFORCED
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs COMMENT='档口';

CREATE TABLE `dining_events` (
  `event_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '饭局编号',
  `host_user_id` INT UNSIGNED NOT NULL COMMENT '发起人编号，引用 users.user_id',
  `stall_id` INT UNSIGNED NOT NULL COMMENT '档口编号',
  `title` VARCHAR(100) NOT NULL COMMENT '饭局标题，不能只含普通空格',
  `meal_time` DATETIME(0) NOT NULL COMMENT '北京时间的计划就餐时间',
  `capacity` SMALLINT UNSIGNED NOT NULL COMMENT '包含发起人的总人数上限，范围为 2 至 65535',
  `description` VARCHAR(500) NULL DEFAULT NULL COMMENT '饭局说明，未填写时为 NULL',
  `cancelled_at` DATETIME(0) NULL DEFAULT NULL COMMENT '取消时间，未取消时为 NULL',
  `created_at` DATETIME(0) NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间，创建后不刷新',
  PRIMARY KEY USING BTREE (`event_id`),
  KEY `idx_events_active_time` USING BTREE (`cancelled_at`, `meal_time`),
  KEY `idx_events_stall_active_time` USING BTREE (`stall_id`, `cancelled_at`, `meal_time`),
  KEY `idx_events_host_time` USING BTREE (`host_user_id`, `meal_time`),
  CONSTRAINT `fk_events_host` FOREIGN KEY (`host_user_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_events_stall` FOREIGN KEY (`stall_id`) REFERENCES `stalls` (`stall_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `ck_events_title` CHECK (CHAR_LENGTH(TRIM(title)) > 0) ENFORCED,
  CONSTRAINT `ck_events_capacity` CHECK (capacity >= 2) ENFORCED,
  CONSTRAINT `ck_events_meal_time` CHECK (meal_time > created_at) ENFORCED,
  CONSTRAINT `ck_events_cancel_time` CHECK (cancelled_at IS NULL OR (cancelled_at >= created_at AND cancelled_at < meal_time)) ENFORCED
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs COMMENT='饭局';

CREATE TABLE `registrations` (
  `event_id` INT UNSIGNED NOT NULL COMMENT '饭局编号',
  `user_id` INT UNSIGNED NOT NULL COMMENT '用户编号',
  `registration_status` VARCHAR(6) NOT NULL DEFAULT 'JOINED' COMMENT 'JOINED 表示已报名；EXITED 表示已退出',
  `last_joined_at` DATETIME(0) NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '最近一次报名时间；发起人取饭局 created_at',
  `last_exited_at` DATETIME(0) NULL DEFAULT NULL COMMENT '最近一次退出时间，从未退出时为 NULL',
  PRIMARY KEY USING BTREE (`event_id`, `user_id`),
  KEY `idx_registrations_event_status` USING BTREE (`event_id`, `registration_status`),
  KEY `idx_registrations_user_status` USING BTREE (`user_id`, `registration_status`),
  CONSTRAINT `fk_registrations_event` FOREIGN KEY (`event_id`) REFERENCES `dining_events` (`event_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_registrations_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `ck_registrations_status` CHECK (registration_status IN ('JOINED', 'EXITED')) ENFORCED,
  CONSTRAINT `ck_registrations_exit_time` CHECK (registration_status <> 'EXITED' OR last_exited_at IS NOT NULL) ENFORCED
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs COMMENT='报名记录';

CREATE TABLE `taste_tags` (
  `tag_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '口味标签编号',
  `tag_name` VARCHAR(16) NOT NULL COMMENT '六个固定口味标签中的一个，名称唯一',
  PRIMARY KEY USING BTREE (`tag_id`),
  UNIQUE KEY `uq_taste_tags_name` USING BTREE (`tag_name`),
  CONSTRAINT `ck_taste_tags_name` CHECK (tag_name IN ('清淡', '香辣', '麻辣', '甜口', '咸鲜', '素食')) ENFORCED
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs COMMENT='口味标签';

CREATE TABLE `user_taste_preferences` (
  `user_id` INT UNSIGNED NOT NULL COMMENT '用户编号',
  `tag_id` INT UNSIGNED NOT NULL COMMENT '口味标签编号',
  PRIMARY KEY USING BTREE (`user_id`, `tag_id`),
  KEY `idx_user_preferences_tag` USING BTREE (`tag_id`),
  CONSTRAINT `fk_user_preferences_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_user_preferences_tag` FOREIGN KEY (`tag_id`) REFERENCES `taste_tags` (`tag_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs COMMENT='用户口味偏好';

CREATE TABLE `event_taste_tags` (
  `event_id` INT UNSIGNED NOT NULL COMMENT '饭局编号',
  `tag_id` INT UNSIGNED NOT NULL COMMENT '口味标签编号',
  PRIMARY KEY USING BTREE (`event_id`, `tag_id`),
  KEY `idx_event_tags_tag` USING BTREE (`tag_id`),
  CONSTRAINT `fk_event_tags_event` FOREIGN KEY (`event_id`) REFERENCES `dining_events` (`event_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_event_tags_tag` FOREIGN KEY (`tag_id`) REFERENCES `taste_tags` (`tag_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs COMMENT='饭局标签';

CREATE TABLE `stall_favorites` (
  `user_id` INT UNSIGNED NOT NULL COMMENT '用户编号',
  `stall_id` INT UNSIGNED NOT NULL COMMENT '档口编号',
  `favorited_at` DATETIME(0) NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '当前收藏关联的建立时间',
  PRIMARY KEY USING BTREE (`user_id`, `stall_id`),
  KEY `idx_stall_favorites_stall` USING BTREE (`stall_id`),
  CONSTRAINT `fk_stall_favorites_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_stall_favorites_stall` FOREIGN KEY (`stall_id`) REFERENCES `stalls` (`stall_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs COMMENT='档口收藏';

CREATE TABLE `event_reviews` (
  `event_id` INT UNSIGNED NOT NULL COMMENT '饭局编号',
  `user_id` INT UNSIGNED NOT NULL COMMENT '用户编号',
  `rating` TINYINT UNSIGNED NOT NULL COMMENT '1 至 5 的整数评分',
  `content` VARCHAR(500) NULL DEFAULT NULL COMMENT '评价内容，未填写时为 NULL',
  `reviewed_at` DATETIME(0) NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评价提交时间',
  PRIMARY KEY USING BTREE (`event_id`, `user_id`),
  CONSTRAINT `fk_reviews_registration` FOREIGN KEY (`event_id`, `user_id`) REFERENCES `registrations` (`event_id`, `user_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `ck_reviews_rating` CHECK (rating BETWEEN 1 AND 5) ENFORCED
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs COMMENT='饭局评价';

CREATE TRIGGER `trg_dining_events_ai_host_registration`
AFTER INSERT ON `dining_events`
FOR EACH ROW
  INSERT INTO `registrations` (`event_id`, `user_id`, `registration_status`, `last_joined_at`, `last_exited_at`)
  VALUES (NEW.event_id, NEW.host_user_id, 'JOINED', NEW.created_at, NULL);
