/*
[경로] : server2/src/mediasoup/workerManager.js
[설명]: worker를 관리한다. 최대 21개의 worker를 생성할 수 있으나, 오버스펙임으로 현재 4개로 제한한다.
 */
const mediasoup = require('mediasoup');
const os = require('os');

let workers = [];

async function createWorkers() {
  const numCores = Math.min(os.cpus().length, 4);

  for (let i = 0; i < numCores; i++) {
    const worker = await mediasoup.createWorker({
      logLevel: 'warn',
      rtcMinPort: 40000,
      rtcMaxPort: 40100,
    });

    worker.on('died', () => {
      console.error('❌ mediasoup worker died');
      process.exit(1);
    });

    console.log(`✅ Worker ${i} created`);
    workers.push(worker);
  }
}

function getWorkers() {
  return workers;
}

async function initializeMediasoup() {
  await createWorkers();
}

module.exports = {
  initializeMediasoup,
  getWorkers,
};