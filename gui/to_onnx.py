import torch
from models.fastnet import MiniFASNetV2

m = MiniFASNetV2()
m.load_state_dict(torch.load("models/MiniFASNetV2.pth", map_location="cpu", weights_only=True))
m.eval()
torch.onnx.export(
    m, torch.zeros(1, 3, 80, 80), "models/MiniFASNetV2.onnx",
    input_names=["input"], output_names=["output"],
    opset_version=17, dynamo=False,
)
print("done")