from fastapi import FastAPI, UploadFile, File
from PIL import Image
import torch
import torchvision.transforms as transforms
import io

from model import load_model

app = FastAPI(title="Mallampati Scoring API")

model = load_model()
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

classes = ["Class I", "Class II", "Class III", "Class IV"]

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

@app.post("/predict")
async def predict_mallampati(file: UploadFile = File(...)):
    # Lire l'image
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Preprocess
    img_tensor = transform(image).unsqueeze(0).to(DEVICE)

    # Inference
    with torch.no_grad():
        outputs = model(img_tensor)
        pred_idx = torch.argmax(outputs, dim=1).item()
        confidence = torch.softmax(outputs, dim=1)[0][pred_idx].item()

    # ⚠️ OBLIGATOIRE : retourner un dict
    return {
        "filename": file.filename,
        "mallampati_class": classes[pred_idx],
        "confidence": round(confidence, 3)
    }
