/*
[경로] : server2/src/index.js
[설명] : Express + Socket.io + mediasoup 초기화 + Prometheus 모니터링
*/
const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const { initializeMediasoup } = require('./mediasoup/workerManager');
const socketHandler = require('./signaling/socketHandler');
const { setupPrometheus, activeProducers, activeConsumers } = require('./prometheus');  // prometheus.js에서 메트릭과 setupPrometheus 가져오기

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});
 
setupPrometheus(app);
 
async function boot() {
  try {
    await initializeMediasoup();  

    socketHandler(io, { activeProducers, activeConsumers });

    const PORT = process.env.PORT || 5000;
    server.listen(PORT, () => {
      console.log(`🚀 SFU Server running at http://localhost:${PORT}`);
    });
  } catch (err) {
    console.error('❗ Failed to initialize SFU Server:', err);
    process.exit(1);
  }
}

boot();