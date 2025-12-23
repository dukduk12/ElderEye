/*
[경로] : server2/src/socket/socketHandler.js
[설명]: 클라이언트 signaling 처리를 위한 socket.io 핸들러
*/
const { getRoom, createRoom } = require("../mediasoup/roomManager");
const {
  createSendTransport,
  createRecvTransport,
} = require("../mediasoup/transportManager");
const db = require("../utils/db");
const fs = require('fs');
const path = require('path');
const { activeProducers, activeConsumers, streamingLatency, packetLoss, rtt } = require('../prometheus'); // Prometheus 메트릭 가져오기

const peers = new Map();

// 에러 로그를 DB에 기록하는 함수
async function logErrorToDB(error, socketId, roomId, eventType) {
  await db.query(
    `INSERT INTO error_logs (socket_id, room_id, event_type, error_message) VALUES (?, ?, ?, ?)`,
    [socketId, roomId, eventType, error.message]
  );
}

// 에러 로그를 파일에 기록하는 함수
function logErrorToFile(error, socketId, roomId, eventType) {
  const logMessage = `${new Date().toISOString()} - [socketId: ${socketId}, roomId: ${roomId}, event: ${eventType}] - ${error.stack || error.message}\n`;
  const logFilePath = path.join(__dirname, 'error_logs.txt');
  fs.appendFileSync(logFilePath, logMessage);
}

function socketHandler(io) {
  io.on("connection", (socket) => {
    console.log(`🔌 Client connected [id: ${socket.id}]`);

    // 1) 방 참가
    socket.on("joinRoom", async ({ roomId }, callback) => {
      console.log(`➡️ joinRoom - socketId: ${socket.id}, roomId: ${roomId}`);
      try {
        let room = getRoom(roomId);
        if (!room) {
          room = await createRoom(roomId);
        }

        await db.query(
          `INSERT INTO connection_logs (socket_id, event_type, room_id) VALUES (?, ?, ?)`,
          [socket.id, 'connected', roomId]
        );

        peers.set(socket.id, {
          roomId,
          transports: [],
          producers: [],
          consumers: [],
          producerSerialCounter: 0,
        });

        callback(room.router.rtpCapabilities);
      } catch (err) {
        console.error(`❌ joinRoom error: ${err}`);
        await logErrorToDB(err, socket.id, roomId, 'joinRoom');
        logErrorToFile(err, socket.id, roomId, 'joinRoom');
        callback({ error: err.message });
      }
    });

    // 2) send / recv transport 생성
    socket.on("createTransport", async ({ roomId, direction }, callback) => {
      console.log(`➡️ createTransport - ${direction}, socketId: ${socket.id}`);
      try {
        const room = getRoom(roomId);
        let transport;

        if (direction === "send") {
          transport = await createSendTransport(room.router);
        } else if (direction === "recv") {
          transport = await createRecvTransport(room.router);
        } else {
          throw new Error("Invalid transport direction");
        }

        const peer = peers.get(socket.id);
        peer.transports.push(transport);

        await db.query(
          `INSERT INTO transport_logs (socket_id, room_id, transport_id, direction, status) VALUES (?, ?, ?, ?, ?)`,
          [socket.id, roomId, transport.id, direction, 'created']
        );

        callback({
          id: transport.id,
          iceParameters: transport.iceParameters,
          iceCandidates: transport.iceCandidates,
          dtlsParameters: transport.dtlsParameters,
        });
      } catch (err) {
        console.error(`❌ createTransport error: ${err}`);
        await logErrorToDB(err, socket.id, roomId, 'createTransport');
        logErrorToFile(err, socket.id, roomId, 'createTransport');
        callback({ error: err.message });
      }
    });

    // 3) Transport 연결 요청
    socket.on("connectTransport", async ({ transportId, dtlsParameters }, callback) => {
      console.log(`➡️ connectTransport - ${transportId}`);
      try {
        const peer = peers.get(socket.id);
        const transport = peer.transports.find((t) => t.id === transportId);
        await transport.connect({ dtlsParameters });

        await db.query(
          `INSERT INTO transport_logs (socket_id, room_id, transport_id, direction, status) VALUES (?, ?, ?, ?, ?)`,
          [socket.id, peer.roomId, transportId, 'send', 'connected']
        );

        callback({ connected: true });
      } catch (err) {
        console.error("❌ connectTransport error", err);
        await logErrorToDB(err, socket.id, peer.roomId, 'connectTransport');
        logErrorToFile(err, socket.id, peer.roomId, 'connectTransport');
        callback({ error: err.message });
      }
    });

    // 4) 수신(Recv) Transport 연결 요청 
    socket.on("connectRecvTransport", async ({ transportId, dtlsParameters }, callback) => {
      console.log(`➡️ connectRecvTransport - ${transportId}`);
      try {
        const peer = peers.get(socket.id);
        if (!peer) {
          throw new Error('Peer not found for socket id');
        }
        const transport = peer.transports.find((t) => t.id === transportId);
        if (!transport) {
          throw new Error('Transport not found for given transport id');
        }
        await transport.connect({ dtlsParameters });
    
        await db.query(
          `INSERT INTO transport_logs (socket_id, room_id, transport_id, direction, status) VALUES (?, ?, ?, ?, ?)`,
          [socket.id, peer.roomId, transportId, 'recv', 'connected']
        );
    
        console.log(`✅ Recv Transport ${transportId} connected successfully`);
        callback({ connected: true });
      } catch (err) {
        console.error("❌ connectRecvTransport error", err);
        const roomId = peers.get(socket.id)?.roomId || 'unknown';
        await logErrorToDB(err, socket.id, roomId, 'connectRecvTransport');
        logErrorToFile(err, socket.id, roomId, 'connectRecvTransport');
        callback({ error: err.message });
      }
    });
    

    // 5) Producer 생성
    socket.on("produce", async ({ transportId, kind, rtpParameters, serialId }, callback) => {
      try {
        const peer = peers.get(socket.id);
        const transport = peer.transports.find((t) => t.id === transportId);

        const producer = await transport.produce({ kind, rtpParameters });

        peer.producerSerialCounter += 1;
        const generatedSerialId = serialId || peer.producerSerialCounter;

        peer.producers.push({ producer, serialId: generatedSerialId });

        await db.query(
          `INSERT INTO producer_logs (socket_id, room_id, producer_id, serial_id, kind) VALUES (?, ?, ?, ?, ?)`,
          [socket.id, peer.roomId, producer.id, generatedSerialId, kind]
        );

        activeProducers.inc();   

        packetLoss.set({ peer_id: socket.id, producer_or_consumer: 'producer' }, 0);  
        rtt.set({ peer_id: socket.id, producer_or_consumer: 'producer' }, 50);  
        streamingLatency.set({ peer_id: socket.id, direction: 'send' }, 100);  

        callback({ id: producer.id, serialId: generatedSerialId });
      } catch (err) {
        console.error("❌ produce error", err);
        await logErrorToDB(err, socket.id, peer.roomId, 'produce');
        logErrorToFile(err, socket.id, peer.roomId, 'produce');
        callback({ error: err.message });
      }
    });

    // 6) Consumer 생성
    socket.on("consume", async ({ serialId, rtpCapabilities, transportId }, callback) => {
      try {
        const peer = peers.get(socket.id);
        const transport = peer.transports.find((t) => t.id === transportId);
        const room = getRoom(peer.roomId);

        const allPeers = [...peers.entries()].filter(([_, p]) => p.roomId === peer.roomId);
        const matchedProducer = allPeers
          .flatMap(([_, p]) => p.producers)
          .find((p) => p.serialId === serialId);

        if (!matchedProducer)
          throw new Error("Producer not found for given serialId");

        if (!room.router.canConsume({
          producerId: matchedProducer.producer.id,
          rtpCapabilities,
        })) {
          throw new Error("Cannot consume this producer");
        }

        const consumer = await transport.consume({
          producerId: matchedProducer.producer.id,
          rtpCapabilities,
          paused: true,
        });

        peer.consumers.push(consumer);

        await db.query(
          `INSERT INTO consumer_logs (socket_id, room_id, consumer_id, uuid, producer_id) VALUES (?, ?, ?, ?, ?)`,
          [socket.id, peer.roomId, consumer.id, serialId, matchedProducer.producer.id]
        );

        activeConsumers.inc();   

        packetLoss.set({ peer_id: socket.id, producer_or_consumer: 'consumer' }, 0);   
        rtt.set({ peer_id: socket.id, producer_or_consumer: 'consumer' }, 50);  
        streamingLatency.set({ peer_id: socket.id, direction: 'recv' }, 100);  

        callback({
          id: consumer.id,
          producerId: matchedProducer.producer.id,
          kind: consumer.kind,
          rtpParameters: consumer.rtpParameters,
        });
      } catch (err) {
        console.error("❌ consume error", err);
        await logErrorToDB(err, socket.id, peer.roomId, 'consume');
        logErrorToFile(err, socket.id, peer.roomId, 'consume');
        callback({ error: err.message });
      }
    });

    // 7) Consumer resume
    socket.on("resumeConsumer", async ({ consumerId }, callback) => {
      try {
        const peer = peers.get(socket.id);
        const consumer = peer.consumers.find((c) => c.id === consumerId);
        if (!consumer) throw new Error("Consumer not found");

        await consumer.resume();
        console.log(`▶️ resumed consumer [id: ${consumerId}]`);
        callback({ resumed: true });
      } catch (err) {
        console.error("❌ resumeConsumer error", err);
        await logErrorToDB(err, socket.id, peer.roomId, 'resumeConsumer');
        logErrorToFile(err, socket.id, peer.roomId, 'resumeConsumer');
        callback({ error: err.message });
      }
    });


    // 8) 연결 해제
    socket.on("disconnect", async () => {
      const peer = peers.get(socket.id);
      if (peer) {
        try {
          await db.query(
            `INSERT INTO connection_logs (socket_id, event_type, room_id) VALUES (?, ?, ?)`,
            [socket.id, 'disconnected', peer.roomId]
          );

          for (const transport of peer.transports) {
            await transport.close();
          }

          for (const p of peer.producers) {
            await p.producer.close();
            activeProducers.dec();
          }

          for (const consumer of peer.consumers) {
            await consumer.close();
            activeConsumers.dec();
          }

          peers.delete(socket.id);
          console.log(`✅ Cleaned up peer and resources for socket ${socket.id}`);
        } catch (err) {
          console.error(`❌ Error during disconnect cleanup for socket ${socket.id}`, err);
        }
      }
    });
  });
}

module.exports = socketHandler;