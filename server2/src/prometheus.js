const client = require('prom-client');

client.collectDefaultMetrics({ timeout: 5000 });

const activeProducers = new client.Gauge({
  name: 'active_producers',
  help: '현재 연결된 producer 수'
});

const activeConsumers = new client.Gauge({
  name: 'active_consumers',
  help: '현재 연결된 consumer 수'
});

const packetLoss = new client.Gauge({
  name: 'packet_loss',
  help: '패킷 손실 비율 (%)',
  labelNames: ['peer_id', 'producer_or_consumer']  
});

const rtt = new client.Gauge({
  name: 'rtt',
  help: 'RTT (ms)',
  labelNames: ['peer_id', 'producer_or_consumer']  
});

const streamingLatency = new client.Gauge({
  name: 'streaming_latency',
  help: '스트리밍 지연 (ms)',
  labelNames: ['peer_id', 'direction']  
});

async function setupPrometheus(app) {
  app.get('/metrics', async (req, res) => {
    res.set('Content-Type', client.register.contentType);
    res.end(await client.register.metrics());
  });
}

module.exports = {
  activeProducers,
  activeConsumers,
  packetLoss,
  rtt,
  streamingLatency,
  setupPrometheus
};