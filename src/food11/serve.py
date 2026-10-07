import io
import os

import mlflow
import mlflow.pyfunc
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image

CATEGORIES = [
    "Bread", "Dairy product", "Dessert", "Egg", "Fried food", "Meat",
    "Noodles-Pasta", "Rice", "Seafood", "Soup", "Vegetable-Fruit",
]
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 3, 1, 1)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 3, 1, 1)

mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
model = mlflow.pyfunc.load_model("models:/food11@champion")  # loaded once at startup

app = FastAPI(title="food11-api")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        img = Image.open(io.BytesIO(await file.read())).convert("RGB").resize((128, 128))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read image")

    x = np.asarray(img, dtype=np.float32) / 255.0
    x = x.transpose(2, 0, 1)[None]
    x = ((x - MEAN) / STD).astype(np.float32)

    logits = np.asarray(model.predict(x))[0]
    e = np.exp(logits - logits.max())
    probs = e / e.sum()
    idx = int(probs.argmax())
    return {"category": CATEGORIES[idx], "class_index": idx, "confidence": float(probs[idx])}