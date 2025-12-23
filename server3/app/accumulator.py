# app/accumulator.py
# [설명] : 프레임 누적 및 추론 실행 & 이벤트 트리거
import json
import threading
import time
from collections import deque
import numpy as np
import cv2
import torch
import redis
import os
from constants import REDIS_HOST, REDIS_PORT
import logging
from monitoring import INFERENCE_OUTPUT_PROB_SUMMARY, EVENT_TRIGGERED, EVENT_COOLDOWN_REMAINING, FRAME_BUFFER_LENGTH, BUFFER_ADD_DURATION, EVENT_SAVE_DURATION
from constants import (
    BUFFER_SIZE, DECISION_WINDOW, SAVE_DURATION,
    PRED_THRESHOLD, COOLDOWN_PERIOD, MAX_INTER_FRAME_DELAY, EXPECTED_FPS
)
# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()  
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class FrameAccumulator:
    def __init__(self, serial_number, inference_engine, dispatcher):
        self.serial_number = serial_number
        self.inference_engine = inference_engine
        self.dispatcher = dispatcher
        self.buffer = deque()
        self.pred_history = deque(maxlen=DECISION_WINDOW)
        self.redis_pub = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        self.last_save_time = 0
        self.lock = threading.Lock() 

    # 1) add preprocessed frame[only crop the ROI] in the buffer (30 frames)
    @BUFFER_ADD_DURATION.time()
    def add_frame(self, frame, timestamp):
        timestamp = timestamp / 1000  # 밀리초 -> 초
        recv_time = time.time()  # 초 
        logger.info(f"[{self.serial_number}] Received frame with timestamp: {timestamp}, current recv_time: {recv_time}")

        if self.buffer and (timestamp - self.buffer[-1][1]) > MAX_INTER_FRAME_DELAY:
            logger.warning(f"[{self.serial_number}] Buffer cleared due to delay: Δt = {timestamp - self.buffer[-1][1]:.2f}s")
            self.buffer.clear()  

        self.buffer.append((frame, timestamp))

        FRAME_BUFFER_LENGTH.labels(serial_number=self.serial_number).set(len(self.buffer))

        if len(self.buffer) >= BUFFER_SIZE:
            batch = [f for f, _ in list(self.buffer)[-BUFFER_SIZE:]]
            timestamps = [t for _, t in list(self.buffer)[-BUFFER_SIZE:]]
            self._process_batch(batch, timestamps)

            stride = BUFFER_SIZE // 2
            for _ in range(stride):
                if self.buffer:
                    self.buffer.popleft()

    # 2) determine the result (input to the AI model -> evaluation sum/3)
    def _process_batch(self, frames, timestamps):
        outputs = self.inference_engine.run_batch_inference(frames)
        if outputs is None:
            logger.info(f"[{self.serial_number}] Inference skipped: insufficient frame count.")
            return

        probs = torch.softmax(outputs, dim=1)[:, 1].cpu().numpy()

        for prob in probs:
            self.pred_history.append(prob > PRED_THRESHOLD)
            INFERENCE_OUTPUT_PROB_SUMMARY.labels(serial_number=self.serial_number).observe(prob)

        self.pred_history = list(self.pred_history)[-DECISION_WINDOW:]
        positive_count = sum(self.pred_history)
        logger.info(f"[{self.serial_number}] Prediction probs: {probs.round(3).tolist()} / Over {PRED_THRESHOLD}: {positive_count}/{DECISION_WINDOW}")

        # 딥러닝 확률 임계치 기반 판단만 수행
        if positive_count == DECISION_WINDOW:
            triggered = self._trigger_event(timestamps)
            if triggered:
                self.pred_history.clear()
    
    # 3) When the event triggered, skipped due to cooldown
    def _trigger_event(self, timestamps):
        now = time.time()
        elapsed = now - self.last_save_time
        logger.debug(f"[{self.serial_number}] _trigger_event called. elapsed since last_save_time: {elapsed:.2f}s")

        with self.lock:
            if elapsed < COOLDOWN_PERIOD:
                remaining = COOLDOWN_PERIOD - elapsed
                logger.debug(f"[{self.serial_number}] Event skipped due to cooldown: {remaining:.2f}s remaining.")
                return False
            
            self.last_save_time = now
            logger.debug(f"[{self.serial_number}] Event triggered and last_save_time updated.")

        EVENT_TRIGGERED.inc()
        threading.Thread(target=self._save_alert, args=(timestamps,), daemon=True).start()
        return True

    # 4) When the event triggered, save the video & alarm to the API[center] server
    @EVENT_SAVE_DURATION.time()
    def _save_alert(self, timestamps):
        max_ts = max(timestamps)
        min_ts = max_ts - SAVE_DURATION

        logger.info(f"[{self.serial_number}] Saving alert from {min_ts:.2f} to {max_ts:.2f}")

        frames_with_roi = self.dispatcher.get_frames_in_range(self.serial_number, min_ts, max_ts)

        if not frames_with_roi:
            logger.warning(f"[{self.serial_number}] No frames found in alert range.")
            return

        orig_frames = [frame for frame, _ in frames_with_roi]
        rois = [roi for _, roi in frames_with_roi]

        roi_cropped_frames = []
        for frame, roi in zip(orig_frames, rois):
            x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
            roi_crop = frame[y:y+h, x:x+w].copy()
            roi_cropped_frames.append(roi_crop)

        logger.info(f"[{self.serial_number}] Trying to generate GradCAMs for {len(roi_cropped_frames)} ROI cropped frames")
        _, cams = self.inference_engine.run_batch_inference_with_cam(roi_cropped_frames)

        if cams is None:
            logger.warning(f"[{self.serial_number}] CAM 생성 실패 - cams is None")
            return

        logger.info(f"[{self.serial_number}] CAMs 생성 완료 - {len(cams)}개")

        overlay_images = []
        for frame, cam, roi in zip(orig_frames, cams, rois):
            x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]

            roi_crop = frame[y:y+h, x:x+w]
            heatmap = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
            heatmap = cv2.resize(heatmap, (w, h))

            if roi_crop.shape[:2] != heatmap.shape[:2]:
                logger.warning(f"[{self.serial_number}] Size mismatch: heatmap {heatmap.shape}, roi_crop {roi_crop.shape}, resizing heatmap.")
                heatmap = cv2.resize(heatmap, (roi_crop.shape[1], roi_crop.shape[0]))

            if roi_crop.shape[2] != heatmap.shape[2]:
                if heatmap.shape[2] == 1:
                    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_GRAY2BGR)
                elif roi_crop.shape[2] == 1:
                    roi_crop = cv2.cvtColor(roi_crop, cv2.COLOR_GRAY2BGR)

            overlay_roi = cv2.addWeighted(roi_crop, 0.5, heatmap, 0.5, 0)
            overlayed = frame.copy()
            overlayed[y:y+h, x:x+w] = overlay_roi

            overlay_images.append(overlayed)

        timestamp_now = int(time.time())  # 1회만 호출하여 재사용

        gradcam_dir = f"alerts_gradcam/{self.serial_number}_{timestamp_now}"
        os.makedirs(gradcam_dir, exist_ok=True)
        for idx, overlay in enumerate(overlay_images):
            cv2.imwrite(f"{gradcam_dir}/frame_{idx:03}.jpg", overlay)

        logger.info(f"[{self.serial_number}] GradCAM (ROI only) saved to {gradcam_dir}")

        height, width, _ = orig_frames[0].shape
        out_path = f"alerts/{self.serial_number}_{timestamp_now}.mp4"
        out = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), EXPECTED_FPS, (width, height))
        for frame in orig_frames:
            out.write(frame)
        out.release()

        logger.info(f"[{self.serial_number}] Alert video saved: {out_path}")

        message = {
            "event_type": "fall_detected",
            "serial_number": self.serial_number,
            "video_url": f"/alerts/{self.serial_number}_{timestamp_now}.mp4",
            "timestamp": timestamp_now
        }
        self.redis_pub.publish("event_alert_channel", json.dumps(message))
        logger.info(f"[{self.serial_number}] Event published: {message}")

    # @EVENT_SAVE_DURATION.time()
    # def _save_alert(self, timestamps):
    #     max_ts = max(timestamps)
    #     min_ts = max_ts - SAVE_DURATION

    #     logger.info(f"[{self.serial_number}] Saving alert from {min_ts:.2f} to {max_ts:.2f}")

    #     frames_with_roi = self.dispatcher.get_frames_in_range(self.serial_number, min_ts, max_ts)

    #     if not frames_with_roi:
    #         logger.warning(f"[{self.serial_number}] No frames found in alert range.")
    #         return

    #     # 🔷 원본 프레임과 ROI 정보 분리
    #     orig_frames = [frame for frame, _ in frames_with_roi]
    #     rois = [roi for _, roi in frames_with_roi]

    #     # 🔷 ROI만 crop해서 CAM 생성
    #     roi_cropped_frames = []
    #     for frame, roi in zip(orig_frames, rois):
    #         x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
    #         roi_crop = frame[y:y+h, x:x+w].copy()
    #         roi_cropped_frames.append(roi_crop)

    #     # 🔷 GradCAM 생성 on ROI crop
    #     logger.info(f"[{self.serial_number}] Trying to generate GradCAMs for {len(roi_cropped_frames)} ROI cropped frames")
    #     _, cams = self.inference_engine.run_batch_inference_with_cam(roi_cropped_frames)

    #     if cams is None:
    #         logger.warning(f"[{self.serial_number}] CAM 생성 실패 - cams is None")
    #         return

    #     logger.info(f"[{self.serial_number}] CAMs 생성 완료 - {len(cams)}개")

    #     # 🔷 CAM을 원본 frame 위에 오버레이 (ROI 영역만 CAM 사용)
    #     overlay_images = []
    #     for frame, cam, roi in zip(orig_frames, cams, rois):
    #         x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]

    #         roi_crop = frame[y:y+h, x:x+w]
    #         heatmap = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
    #         heatmap = cv2.resize(heatmap, (w, h))

    #         # 🔸 크기 일치 보장
    #         if roi_crop.shape[:2] != heatmap.shape[:2]:
    #             logger.warning(f"[{self.serial_number}] Size mismatch: heatmap {heatmap.shape}, roi_crop {roi_crop.shape}, resizing heatmap.")
    #             heatmap = cv2.resize(heatmap, (roi_crop.shape[1], roi_crop.shape[0]))

    #         # 🔸 채널 수 일치 보장
    #         if roi_crop.shape[2] != heatmap.shape[2]:
    #             if heatmap.shape[2] == 1:
    #                 heatmap = cv2.cvtColor(heatmap, cv2.COLOR_GRAY2BGR)
    #             elif roi_crop.shape[2] == 1:
    #                 roi_crop = cv2.cvtColor(roi_crop, cv2.COLOR_GRAY2BGR)

    #         overlay_roi = cv2.addWeighted(roi_crop, 0.5, heatmap, 0.5, 0)
    #         overlayed = frame.copy()
    #         overlayed[y:y+h, x:x+w] = overlay_roi

    #         overlay_images.append(overlayed)

    #     # 🔷 GradCAM 시각화 저장
    #     gradcam_dir = f"alerts_gradcam/{self.serial_number}_{int(time.time())}"
    #     os.makedirs(gradcam_dir, exist_ok=True)
    #     for idx, overlay in enumerate(overlay_images):
    #         cv2.imwrite(f"{gradcam_dir}/frame_{idx:03}.jpg", overlay)

    #     logger.info(f"[{self.serial_number}] GradCAM (ROI only) saved to {gradcam_dir}")

    #     # 🔷 원본 영상 저장 (CAM 없이)
    #     height, width, _ = orig_frames[0].shape
    #     out_path = f"alerts/{self.serial_number}_{int(time.time())}.mp4"
    #     out = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), EXPECTED_FPS, (width, height))
    #     for frame in orig_frames:
    #         out.write(frame)
    #     out.release()

    #     logger.info(f"[{self.serial_number}] Alert video saved: {out_path}")

    #     message = {
    #         "event_type": "fall_detected",
    #         "serial_number": self.serial_number,
    #         "video_url": f"/alerts/{self.serial_number}_{int(time.time())}.mp4",
    #         "timestamp": int(time.time())
    #     }
    #     self.redis_pub.publish("event_alert_channel", json.dumps(message))
    #     logger.info(f"[{self.serial_number}] Event published: {message}")