# app/dispatcher.py
# [설명] : Redis Queue에 프레임 저장 [FIFO]
import redis
import pickle
import threading
import logging
import numpy as np
import cv2
from monitoring import REDIS_QUEUE_LENGTH, REDIS_QUEUE_PUSH_DURATION
from constants import REDIS_HOST, REDIS_PORT, MAX_QUEUE_LEN, EXPECTED_FPS 
import time

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler() 
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class Dispatcher:
    def __init__(self):
        self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        self.lock = threading.Lock()
        self.max_queue_len = MAX_QUEUE_LEN

    @REDIS_QUEUE_PUSH_DURATION.time()
    def add_to_queue(self, serial_number, frame_message):
        with self.lock:
            data = {
                "timestamp": frame_message.timestamp / 1000,  
                "frame_id": frame_message.frame_id,
                "image": frame_message.image,
                "roi": {
                    "x": frame_message.roi_x,
                    "y": frame_message.roi_y,
                    "w": frame_message.roi_w,
                    "h": frame_message.roi_h
                }
            }
            key = f"stream:{serial_number}"
            self.redis.rpush(key, pickle.dumps(data))
            self.redis.ltrim(key, -self.max_queue_len, -1)
            REDIS_QUEUE_LENGTH.labels(serial_number=serial_number).set(self.redis.llen(key))

    def get_frame_by_timestamp(self, serial_number, target_timestamp):
        key = f"stream:{serial_number}"
        target_timestamp_ms = int(target_timestamp * 1000)  # 밀리초로 변환

        for item in self.redis.lrange(key, 0, -1):
            data = pickle.loads(item)
            if abs(data["timestamp"] - target_timestamp_ms) < 10:  # 밀리초 차이로 비교
                return cv2.imdecode(np.frombuffer(data["image"], dtype=np.uint8), cv2.IMREAD_COLOR)
        return None

    def get_frames_in_range(self, serial_number, start_ts, end_ts):
        key = f"stream:{serial_number}"
        frames_with_roi = []
        candidates = []

        expected_frame_count = int((end_ts - start_ts) * EXPECTED_FPS)

        for item in reversed(self.redis.lrange(key, -self.max_queue_len, -1)):
            data = pickle.loads(item)
            ts = data["timestamp"]
            candidates.append((abs((start_ts + end_ts) / 2 - ts), data))

            if start_ts <= ts <= end_ts:
                frame = cv2.imdecode(np.frombuffer(data["image"], dtype=np.uint8), cv2.IMREAD_COLOR)
                roi = data.get("roi", {"x": 0, "y": 0, "w": frame.shape[1], "h": frame.shape[0]})
                frames_with_roi.append((frame, roi))
                if len(frames_with_roi) >= expected_frame_count:
                    break

        if not frames_with_roi and candidates:
            _, nearest_data = min(candidates, key=lambda x: x[0])
            frame = cv2.imdecode(np.frombuffer(nearest_data["image"], dtype=np.uint8), cv2.IMREAD_COLOR)
            roi = nearest_data.get("roi", {"x": 0, "y": 0, "w": frame.shape[1], "h": frame.shape[0]})
            frames_with_roi.append((frame, roi))

        return list(reversed(frames_with_roi))


    # def get_frames_in_range(self, serial_number, start_ts, end_ts):
    #     key = f"stream:{serial_number}"
    #     frames = []
    #     candidates = []

    #     expected_frame_count = int((end_ts - start_ts) * EXPECTED_FPS)

    #     for item in reversed(self.redis.lrange(key, -self.max_queue_len, -1)):
    #         data = pickle.loads(item)
    #         ts = data["timestamp"]   
    #         candidates.append((abs((start_ts + end_ts) / 2 - ts), data))

    #         if start_ts <= ts <= end_ts:
    #             frame = cv2.imdecode(np.frombuffer(data["image"], dtype=np.uint8), cv2.IMREAD_COLOR)
    #             frames.append(frame)
    #             if len(frames) >= expected_frame_count:
    #                 break

    #     if not frames and candidates:
    #         _, nearest_data = min(candidates, key=lambda x: x[0])
    #         nearest_frame = cv2.imdecode(np.frombuffer(nearest_data["image"], dtype=np.uint8), cv2.IMREAD_COLOR)
    #         logger.warning(f"[{serial_number}] No exact frames in range, using nearest timestamp frame: {nearest_data['timestamp']:.2f}")
    #         frames.append(nearest_frame)

    #     return list(reversed(frames))  
