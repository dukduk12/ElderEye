# app/constants.py
# 1) Redis Queue 에 최대로 넣은 크기
MAX_QUEUE_LEN = 500

# 2) inference을 하기 위한 최대 크기 -> detector 의 buffer_size 인자만 바꾸면 됨됨
BUFFER_SIZE = 10

# 3) 최종 결정을 최근 2개로 판단
DECISION_WINDOW = 2

# 4) 영상 저장 기간을 앞뒤로 n초로 제한
SAVE_DURATION = 8

# 4-1) iot grpc fps (초당 30 frame)
EXPECTED_FPS = 4

# 5) 딥러닝 추론 임계값을 90%
PRED_THRESHOLD = 0.90

# 6) 감지 후 30초 정도 쿨다운 시간 부여
COOLDOWN_PERIOD = 60

# 7) 딜레이가 n초 되면 버리기
MAX_INTER_FRAME_DELAY = 10

# 8) redis 설정값
REDIS_HOST = "redis"
REDIS_PORT = 6379