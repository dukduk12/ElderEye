/*
[경로] : server2/src/mediasoup/roomManager.js
[설명]: 방 및 peer 등록 관리하는 코드이다. 1 producer에 1 room(router)으로 설정하고 1 worker에 최대 25 room으로 제한한다.
 */
const { getWorkers } = require("./workerManager");
const { createWebSocketTransport } = require("./transportManager");
const rooms = new Map();

const maxRoutersPerWorker = 25;
let nextWorkerIndex = 0;

function getNextWorker() {
  const workers = getWorkers();
  const worker = workers[nextWorkerIndex];
  nextWorkerIndex = (nextWorkerIndex + 1) % workers.length;
  return worker;
}

async function createRoom(roomId) {
  if (rooms.has(roomId)) return rooms.get(roomId);

  const worker = getNextWorker();

  const currentRouterCount = worker.routers ? worker.routers.length : 0;

  if (currentRouterCount >= maxRoutersPerWorker) {
    throw new Error(
      `Worker reached maximum router limit of ${maxRoutersPerWorker}.`
    );
  }

  const router = await worker.createRouter({
    mediaCodecs: [
      {
        kind: "video",
        mimeType: "video/VP8",
        clockRate: 90000,
      },
      {
        kind: "video",
        mimeType: "video/H264",
        clockRate: 90000,
      },
      {
        kind: "video",
        mimeType: "video/VP9",
        clockRate: 90000,
      },
    ],
  });

  if (!worker.routers) {
    worker.routers = [];
  }
  worker.routers.push(router);

  const room = {
    roomId,
    router,
    peers: new Map(),
  };

  rooms.set(roomId, room);
  console.log(`✅ Room ${roomId} created on worker ${worker.id}`);
  return room;
}

function getRoom(roomId) {
  return rooms.get(roomId);
}

module.exports = {
  createRoom,
  getRoom,
};