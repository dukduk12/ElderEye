<p align="center">
  <img src="./docs/images/eldereye-logo.png" width="180" alt="ElderEye Logo"/>
</p>

<h1 align="center">👁️‍🗨️ ElderEye: Family-Centered IoT Smart Care System</h1>
<p align="center">
  <b>Real-time elderly monitoring platform combining live video streaming and anomaly detection</b><br/>
  <i>Providing peace of mind for families and caregivers — anytime, anywhere.</i>
</p>

## 📌 Overview

**ElderEye** is a modular smart care system designed to continuously monitor the safety and well-being of elderly family members.  
It seamlessly integrates **real-time video streaming**, **deep learning-powered behavior anomaly detection**, and **instant mobile alerts** to act as a reliable "eye and ear" for families and caregivers.

Built on a **Hybrid Microservice Architecture**, ElderEye ensures scalability, modularity, and robust observability.  
Each service can be deployed independently, with comprehensive system monitoring enabled via **Prometheus** and **Grafana**.

---
## ⚙️ System Architecture
<p align="center">
  <img src="./docs/images/eldereye-architecture.png" alt="System Architecture" width="700"/>
</p>
This architecture diagram illustrates the interaction among the mobile frontend, backend microservices, gRPC-based machine learning inference server, and IoT devices deployed in the elderly’s environment.

---

## 🚀 Key Features

- [1] **Family-Centered Real-Time Video Streaming:** Low-latency, multi-party video streaming using Mediasoup SFU to keep family members connected.  
- [2] **Behavior Anomaly Detection:** Integration with an external deep learning model via gRPC for intelligent anomaly recognition.  
- [3] **Persistent Event Logging:** Reliable CRUD operations and event storage powered by MySQL.  
- [4] **Instant Mobile Alerts:** Timely notifications to caregivers through a React Native mobile app.  
- [5] **Modular Microservices:** Independent deployment and scalability of backend services.  
- [6] **Full Observability:** System health and metrics tracking with Prometheus and Grafana.
- [7] **Data Privacy:** Sensitive personal data securely encrypted at rest in the database using AES-256.  
- [8] **Authentication:** User authentication and authorization managed via JWT (JSON Web Tokens).
- [9] **Access Control:** Principle of Least Privilege (POLP) enforced to restrict permissions to only what is necessary for each user and service.

---

## 🛠️ Technologies Used

- Backend: FastAPI, Mediasoup, gRPC  
- Frontend: React Native  
- Database: MySQL  
- ML: PyTorch (pre-trained model integrated for inference; no training performed)
- Monitoring: Prometheus, Grafana

---
## 📸 Screenshots

| App Home Screen       | Live Streaming Screen  | Alert Tab Screen      | Notification Detected Screen |
|----------------------|-----------------------|----------------------|-----------------------------|
| <img src="./docs/images/app-home.png" alt="ElderEye App Home Screen" width="250"/> | <img src="./docs/images/app-stream.png" alt="ElderEye Live Streaming Screen" width="250"/> | <img src="./docs/images/app-alert.png" alt="ElderEye Alert Tab Screen" width="250"/> | <img src="./docs/images/app-notification.png" alt="ElderEye Notification Detected Screen" width="250"/> |
| Home Dashboard       | Real-Time Video Streaming | Alert Tab View       | Detected Notification View   |

---
## 🗂️ Directory Structure

```plaintext
📁 ElderEye/
├── 📁 BE/                   # 🖥️ Backend services
│   ├── 📁 server1/          # 🧾 FastAPI – CRUD operations, event logging, alerts (MySQL)
│   ├── 📁 server2/          # 📡 Node.js + Mediasoup SFU – real-time media streaming
│   ├── 📁 server3/          # 🧠 gRPC service – deep learning inference integration
│   ├── 📄 docker-compose.dev.yml      # Development environment configuration
│   ├── 📄 docker-compose.prod.yml     # Production environment configuration
│   ├── 📄 init.sql                    # Database initialization & permission setup
│   └── 📁 monitoring/                # 📊 Prometheus / Grafana configuration
│
├── 📁 docs/                 # 📚 Documentation and assets
│   └── 📁 images/           # 🖼️ Architecture diagrams, system flow, visuals
│
└── 📄 README.md             # Project overview and setup instructions
