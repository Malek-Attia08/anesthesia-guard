import torch
import torch.nn as nn
import torchvision.models as models

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
NUM_CLASSES = 4

def load_model():
    model = models.efficientnet_b0(weights=None)
    num_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_features, NUM_CLASSES)

    model.load_state_dict(
        torch.load("weights/mallampati_model.pth", map_location=DEVICE)
    )

    model.to(DEVICE)
    model.eval()
    return model
