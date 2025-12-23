# app/monitoring.py
from prometheus_client import Histogram, Summary, Counter, Gauge

# 추론 시간
INFERENCE_DURATION = Summary('inference_duration_seconds', 'Time spent in inference')

# 총 추론 호출 수
INFERENCE_REQUESTS = Counter('inference_requests_total', 'Total number of inference calls')

# 이벤트 발생 횟수
EVENT_TRIGGERED = Counter('event_triggered_total', 'Total number of fall events detected')

# Redis 대기열 길이
REDIS_QUEUE_LENGTH = Gauge('redis_queue_length', 'Current Redis frame queue length per device', ['serial_number'])
REDIS_QUEUE_PUSH_DURATION = Summary('redis_queue_push_duration_seconds', 'Time taken to push a frame to Redis queue')

# 추론 결과 평균 확률 기록 (fall=1 class 기준)
INFERENCE_OUTPUT_PROB_SUMMARY = Summary(
    'inference_output_prob_seconds',
    'Probability output of fall class (label=1) over time per device',
    ['serial_number']
)
# 프레임 버퍼 길이 (FrameAccumulator 단위)
FRAME_BUFFER_LENGTH = Gauge('frame_buffer_length', 'Current frame buffer size per device', ['serial_number'])
BUFFER_ADD_DURATION = Summary('buffer_add_duration_seconds', 'Time taken to add frame to buffer and process')

# 장치별 쿨다운 남은 시간
EVENT_SAVE_DURATION = Summary('event_save_duration_seconds', 'Time taken to save alert video and publish event')
EVENT_COOLDOWN_REMAINING = Gauge('event_cooldown_remaining_seconds', 'Cooldown time remaining per device', ['serial_number'])

# Optical Flow 처리 시간 (현재 미사용)
# OPTICALFLOW_DURATION = Summary('opticalflow_duration_seconds', 'Time spent calculating optical flow')

# gRPC 수신 지연 (iot to server)
# FRAME_ARRIVAL_DELAY = Summary('frame_arrival_delay_seconds', 'Delay from device to server (network + encoder)')
