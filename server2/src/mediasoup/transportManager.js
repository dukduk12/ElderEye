/*
[경로] : server2/src/mediasoup/transportManager.js
[설명]: send & recv [webrtc] transport를 생성한다.
 */

// 1) Send용 Transport
async function createSendTransport(router) {
  const transport = await router.createWebRtcTransport({
    listenInfos: [
      {
        protocol: "udp",
        ip: "0.0.0.0",  
        announcedAddress: "172.20.66.200",  
      },
    ],  
    enableUdp: true,
    enableTcp: true,
    preferUdp: true,
    initialAvailableOutgoingBitrate: 1000000,
  });

  console.log(`🚚 Created Send Transport [id: ${transport.id}]`);
  transport.on("dtlsstatechange", (dtlsState) => {
    if (dtlsState === "closed") console.warn("⚠️ Transport DTLS state closed");
  });
  transport.on("close", () => {
    console.log("🛑 Send Transport closed");
  });

  return transport;
}

// 2) Recv용 Transport
async function createRecvTransport(router) {
  const transport = await router.createWebRtcTransport({
    listenInfos: [
      {
        protocol: "udp",
        ip: "0.0.0.0",  
        announcedAddress: "172.20.66.200",  
      },
    ], 
    enableUdp: true,
    enableTcp: true,
    preferUdp: true,
    initialAvailableOutgoingBitrate: 1000000,
  });

  console.log(`📦 Created Recv Transport [id: ${transport.id}]`);
  transport.on("dtlsstatechange", (dtlsState) => {
    if (dtlsState === "closed") console.warn("⚠️ Transport DTLS state closed");
  });
  transport.on("close", () => {
    console.log("🛑 Recv Transport closed");
  });

  return transport;
}


module.exports = {
  createSendTransport,
  createRecvTransport,   
};
