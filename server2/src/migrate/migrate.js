/*
[경로] : server2/src/migrate/migrate.js
[설명]: StreamLogger DB 테이블 마이그레이션 파일. 로그 테이블 생성 (DROP 포함)
*/
const mysql = require('mysql2/promise');

const pool = mysql.createPool({
  host: 'db-streamlogger',  
  user: 'root',              
  password: 'jinlib1906!!',  
  database: 'StreamLogger',
});

async function migrate() {
  const connection = await pool.getConnection();
  try {
    await connection.beginTransaction();

    await connection.query(`DROP TABLE IF EXISTS consumer_logs;`);
    await connection.query(`DROP TABLE IF EXISTS producer_logs;`);
    await connection.query(`DROP TABLE IF EXISTS transport_logs;`);
    await connection.query(`DROP TABLE IF EXISTS connection_logs;`);
    await connection.query(`DROP TABLE IF EXISTS error_logs;`);  

    // 1) connection_logs 테이블
    await connection.query(`
      CREATE TABLE connection_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        socket_id VARCHAR(255) NOT NULL,
        event_type ENUM('connected', 'disconnected') NOT NULL,
        room_id VARCHAR(255) NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);

    // 2) transport_logs 테이블
    await connection.query(`
      CREATE TABLE transport_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        socket_id VARCHAR(255) NOT NULL,
        room_id VARCHAR(255) NOT NULL,
        transport_id VARCHAR(255) NOT NULL,
        direction ENUM('send', 'recv') NOT NULL,
        status ENUM('created', 'connected') NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);

    // 3) producer_logs 테이블
    await connection.query(`
      CREATE TABLE producer_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        socket_id VARCHAR(255) NOT NULL,
        room_id VARCHAR(255) NOT NULL,
        producer_id VARCHAR(255) NOT NULL,
        serial_id VARCHAR(255),
        kind ENUM('audio', 'video') NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);

    // 4) consumer_logs 테이블
    await connection.query(`
      CREATE TABLE consumer_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        socket_id VARCHAR(255) NOT NULL,
        room_id VARCHAR(255) NOT NULL,
        consumer_id VARCHAR(255) NOT NULL,
        uuid INT,
        producer_id VARCHAR(255) NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);

    // 5) error_logs 테이블 추가
    await connection.query(`
      CREATE TABLE error_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        socket_id VARCHAR(255) NOT NULL,
        room_id VARCHAR(255) NOT NULL,
        component ENUM('transport', 'producer', 'consumer', 'room', 'socket', 'media', 'ETC') DEFAULT 'ETC' NOT NULL,
        error_code VARCHAR(100) NOT NULL,
        error_message TEXT NOT NULL,
        context JSON,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);

    await connection.commit();
    console.log('✅ 마이그레이션 완료 (DROP 후 재생성)');
  } catch (err) {
    await connection.rollback();
    console.error('❌ 마이그레이션 실패:', err);
  } finally {
    connection.release();
  }
}

migrate();
