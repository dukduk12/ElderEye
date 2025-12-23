# app/main.py
# [설명] : 서버 시작 메인
import grpc
import time
import logging
import torch
import numpy as np
import cv2
from concurrent import futures
from collections import defaultdict
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), 'protos'))
from protos import streaming_pb2_grpc, streaming_pb2

from dispatcher import Dispatcher
from detector import InferenceEngine
from accumulator import FrameAccumulator

# Prometheus HTTP endpoint
from prometheus_client import start_http_server

from constants import REDIS_HOST, REDIS_PORT, BUFFER_SIZE

start_http_server(8000)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FrameStreamerServicer(streaming_pb2_grpc.FrameStreamerServicer):
    def __init__(self):
        self.dispatcher = Dispatcher()
        self.frame_accumulators = defaultdict(lambda: None)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, "checkpoints", "cnn_ae_gru_transformer_fast30.pth")
        # model_path = os.path.join(base_dir, "checkpoints", "cnn_ae_lstm_transformer_lightcnn_v5_seq30_epoch100.pth")
        self.inference_engine = InferenceEngine(
            model_path=model_path,
            device="cuda" if torch.cuda.is_available() else "cpu",
            buffer_size=BUFFER_SIZE
        )

    def SendFrame(self, request, context):
        serial_number = request.serial_number
        frame_id = request.frame_id
        logger.info(f"Received frame_id {frame_id} from serial_number: {serial_number}")

        try:
            self.dispatcher.add_to_queue(serial_number, request)

            if self.frame_accumulators[serial_number] is None:
                self.frame_accumulators[serial_number] = FrameAccumulator(
                    serial_number=serial_number,
                    inference_engine=self.inference_engine,
                    dispatcher=self.dispatcher
                )

            frame = self.preprocess_frame(
                request.image,
                request.roi_x,
                request.roi_y,
                request.roi_w,
                request.roi_h
            )
            timestamp = request.timestamp
            self.frame_accumulators[serial_number].add_frame(frame, timestamp)

            return streaming_pb2.Response(status="Frame received and queued")

        except Exception as e:
            logger.exception(f"Error processing frame from serial_number {serial_number}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Frame processing failed')
            return streaming_pb2.Response(status="Frame processing failed")

    def preprocess_frame(self, frame_bytes, roi_x, roi_y, roi_w, roi_h):
        np_frame = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_frame, cv2.IMREAD_COLOR)

        if frame is None:
            raise ValueError("cv2.imdecode failed: frame is None")

        if roi_w > 0 and roi_h > 0:
            if roi_x + roi_w <= frame.shape[1] and roi_y + roi_h <= frame.shape[0]:
                frame = frame[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]

        return frame

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    streaming_pb2_grpc.add_FrameStreamerServicer_to_server(FrameStreamerServicer(), server)
    server.add_insecure_port('[::]:6000')
    server.start()
    logger.info("gRPC server running on port 6000...")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()