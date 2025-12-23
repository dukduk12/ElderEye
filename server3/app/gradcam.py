import torch
import torch.nn.functional as F
import numpy as np
import cv2

class GradCAM:
    def __init__(self, model, target_layer_name):
        self.model = model
        self.target_layer_name = target_layer_name
        self.gradients = None
        self.activations = None
        self._register_hooks()

    def _find_target_layer(self):
        # 모델이 CNNAE_LSTM_Transformer인지 판단 후 cnn 서브모듈 접근
        if hasattr(self.model, 'cnn'):
            module = self.model.cnn
        else:
            module = self.model
        
        target_layer = None
        for name, layer in module.named_modules():
            if name == self.target_layer_name:
                target_layer = layer
                break
        if target_layer is None:
            raise ValueError(f"Layer {self.target_layer_name} not found")
        return target_layer

    def _register_hooks(self):
        def backward_hook(module, grad_in, grad_out):
            self.gradients = grad_out[0]

        def forward_hook(module, input, output):
            self.activations = output
        
        target_layer = self._find_target_layer()
        target_layer.register_forward_hook(forward_hook)
        target_layer.register_full_backward_hook(backward_hook)

    def generate_cam(self, input_tensor, class_idx=None):
        if input_tensor.ndim != 4:
            raise ValueError(f"입력 텐서는 (B, C, H, W) 여야 합니다. 현재 shape: {input_tensor.shape}")

        self.model.zero_grad()
        logits = self.model(input_tensor)

        if class_idx is None:
            class_idx = logits.argmax(dim=1)

        one_hot = torch.zeros_like(logits)
        for i, idx in enumerate(class_idx):
            one_hot[i, idx] = 1

        logits.backward(gradient=one_hot, retain_graph=True)

        gradients = self.gradients.detach()
        activations = self.activations.detach()
        weights = gradients.mean(dim=(2, 3), keepdim=True)
        cam = (weights * activations).sum(dim=1)
        cam = torch.relu(cam)

        cam_min = cam.amin(dim=(1, 2), keepdim=True)
        cam_max = cam.amax(dim=(1, 2), keepdim=True)
        cam_norm = (cam - cam_min) / (cam_max - cam_min + 1e-8)

        return cam_norm.cpu().numpy()

def overlay_cam_on_image(img, cam, alpha=0.5):
    heatmap = cv2.applyColorMap(np.uint8(255*cam), cv2.COLORMAP_JET)
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
    overlay = heatmap * alpha + img * (1 - alpha)
    overlay = overlay.astype(np.uint8)
    return overlay

def overlay_roi_cam_on_full_frame(full_frame, roi, cam, alpha=0.5):
    x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
    if w == 0 or h == 0:  # ROI 정보 이상 시 전체 frame 사용
        x, y, w, h = 0, 0, full_frame.shape[1], full_frame.shape[0]

    cam_resized = cv2.resize(cam, (w, h))
    roi_region = full_frame[y:y+h, x:x+w]
    overlay_roi = overlay_cam_on_image(roi_region, cam_resized, alpha)
    result = full_frame.copy()
    result[y:y+h, x:x+w] = overlay_roi
    return result
