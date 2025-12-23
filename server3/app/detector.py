# app/detector.py
# [설명] : 딥러닝 모델 추론
import torch
import numpy as np
from torchvision import transforms
from PIL import Image
import cv2
from models.model import CNNAE_LSTM_Transformer
from monitoring import INFERENCE_DURATION, INFERENCE_REQUESTS
import logging
from gradcam import GradCAM, overlay_cam_on_image

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()   
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class InferenceEngine:
    def __init__(self, model_path, device='cpu', buffer_size=10):
        self.device = torch.device(device)
        self.buffer_size = buffer_size

        # 모델 로딩
        self.model = CNNAE_LSTM_Transformer(
            ae_latent_dim=128,
            gru_hidden_dim=256,
            lstm_num_layers=2,
            transformer_d_model=256,
            transformer_nhead=4,
            transformer_num_layers=1,
            num_classes=2,
            cnn_feature_dim=256
        ).to(self.device)

        self.model.load_state_dict(torch.load(model_path, map_location=self.device), strict=False)
        self.model.eval()

        self.gradcam = GradCAM(self.model.cnn, target_layer_name="conv2")

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def preprocess(self, frame):
        if not isinstance(frame, np.ndarray):
            raise ValueError(f"Invalid frame type: {type(frame)}")
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        return self.transform(pil)

    def run_batch_inference_with_cam(self, frames):
        if len(frames) < self.buffer_size:
            return None, None
        
        tensor_seq = torch.stack([self.preprocess(f) for f in frames[-self.buffer_size:]]).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            logits, _, _ = self.model(tensor_seq)

        # 시퀀스 각 프레임에 대해 CAM 생성
        cams = []
        for t in range(self.buffer_size):
            frame = tensor_seq[0, t].unsqueeze(0)
            cam = self.gradcam.generate_cam(frame)[0]
            cam = cv2.resize(cam, (frames[0].shape[1], frames[0].shape[0]))
            cams.append(cam)

        cams = np.array(cams)
        return logits, cams

    def get_cam_overlay_images(self, frames, cams, alpha=0.5):
        overlays = []
        for frame, cam in zip(frames[-self.buffer_size:], cams):
            overlay = overlay_cam_on_image(frame, cam, alpha)
            overlays.append(overlay)
        return overlays
    
    @INFERENCE_DURATION.time()
    def run_batch_inference(self, frames):
        INFERENCE_REQUESTS.inc()
        if len(frames) < self.buffer_size:
            return None
        tensor_seq = torch.stack([self.preprocess(f) for f in frames[-self.buffer_size:]]).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits, _, _ = self.model(tensor_seq)
        return logits