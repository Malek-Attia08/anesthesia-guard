import torch
from PIL import Image
from torchvision import transforms
from model import DEVICE

transform = transforms.Compose([
    transforms.Resize((224,224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],
                         [0.229,0.224,0.225])
])

def predict_image(model, image_path):
    img = Image.open(image_path).convert("RGB")
    img = transform(img).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        output = model(img)
        pred = torch.argmax(output, dim=1).item()
        confidence = torch.softmax(output, dim=1).max().item()

    return pred, confidence
