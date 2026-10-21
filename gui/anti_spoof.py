import cv2
import numpy as np
import onnxruntime as ort

from utils import resource_path

SESSION = ort.InferenceSession(
    str(resource_path("models/MiniFASNetV2.onnx")),
    providers=["CPUExecutionProvider"],
)
INPUT_NAME = SESSION.get_inputs()[0].name


def is_face_real(image, bbox):
    x1, y1, x2, y2 = map(int, bbox)

    # Convert bbox [x1, y1, x2, y2] to [x, y, width, height]
    x = x1
    y = y1
    width = x2 - x1
    height = y2 - y1

    # MiniFASNet preprocessing
    image_height, image_width = image.shape[:2]

    scale = min((image_height - 1) / height, (image_width - 1) / width, 2.7)

    new_width = width * scale
    new_height = height * scale

    center_x = x + width / 2
    center_y = y + height / 2

    crop_x1 = max(0, int(center_x - new_width / 2))
    crop_y1 = max(0, int(center_y - new_height / 2))
    crop_x2 = min(image_width - 1, int(center_x + new_width / 2))
    crop_y2 = min(image_height - 1, int(center_y + new_height / 2))

    face = image[crop_y1 : crop_y2 + 1, crop_x1 : crop_x2 + 1]

    # Model expects 80x80
    face = cv2.resize(face, (80, 80))

    # HWC -> CHW, add batch dimension
    face = np.ascontiguousarray(face.transpose(2, 0, 1)[None], dtype=np.float32)

    logits = SESSION.run(None, {INPUT_NAME: face})[0][0]
    e = np.exp(logits - logits.max())
    probabilities = e / e.sum()

    class_id = int(np.argmax(probabilities))
    confidence = float(probabilities[class_id])

    label = "Real" if class_id == 1 else "Fake"
    return label, confidence
