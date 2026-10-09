import cv2
import numpy as np
import torch

from models.fastnet import MiniFASNetV2


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

MODEL = MiniFASNetV2()

MODEL.load_state_dict(
    torch.load(
        "models/MiniFASNetV2.pth",
        map_location=DEVICE,
        weights_only=True
    )
)

MODEL.to(DEVICE)
MODEL.eval()


def is_face_real(image, bbox):

    x1, y1, x2, y2 = map(int, bbox)

    # Convert YOLO bbox: [x1, y1, x2, y2]
    # to [x, y, width, height]
    x = x1
    y = y1
    width = x2 - x1
    height = y2 - y1

    # MiniFASNet preprocessing
    image_height, image_width = image.shape[:2]

    scale = min(
        (image_height - 1) / height,
        (image_width - 1) / width,
        2.7
    )

    new_width = width * scale
    new_height = height * scale

    center_x = x + width / 2
    center_y = y + height / 2

    crop_x1 = max(0, int(center_x - new_width / 2))
    crop_y1 = max(0, int(center_y - new_height / 2))

    crop_x2 = min(
        image_width - 1,
        int(center_x + new_width / 2)
    )

    crop_y2 = min(
        image_height - 1,
        int(center_y + new_height / 2)
    )

    face = image[
        crop_y1:crop_y2 + 1,
        crop_x1:crop_x2 + 1
    ]

    # Model expects 80x80
    face = cv2.resize(face, (80, 80))

    # HWC -> CHW
    face = torch.from_numpy(
        face.transpose(2, 0, 1)
    ).float()

    # Add batch dimension and move to GPU/CPU
    face = face.unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        output = MODEL(face)
        probabilities = torch.softmax(output, dim=1)

    class_id = int(torch.argmax(probabilities, dim=1).item())
    confidence = float(probabilities[0, class_id].item())

    label = "Real" if class_id == 1 else "Fake"

    return label, confidence