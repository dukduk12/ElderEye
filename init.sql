-- init.sql
-- 1) stream_logger에서 오로지 write만 가진 user를 만들기
CREATE USER 'write_user'@'%' IDENTIFIED BY 'eldereye';
GRANT INSERT ON StreamLogger.* TO 'write_user'@'%';
FLUSH PRIVILEGES;