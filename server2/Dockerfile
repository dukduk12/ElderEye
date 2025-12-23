FROM node:22.1.0

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    make \
    g++ \
    libvips-dev \
    libtool \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# package.json 복사 후 설치
COPY package*.json ./
RUN npm install

# 코드 복사
COPY . .

# mediasoup 재빌드
RUN rm -rf /app/node_modules/mediasoup/worker/out/Release
RUN npm rebuild mediasoup --build-from-source

EXPOSE 5000

CMD ["node", "server.js"]
