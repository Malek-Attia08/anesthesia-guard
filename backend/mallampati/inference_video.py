import cv2
import numpy as np
from inference_image import predict_image
from collections import Counter

def predict_video(model, video_path, num_frames=10):
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frame_ids = np.linspace(0, total_frames-1, num_frames, dtype=int)
    preds = []

    for fid in frame_ids:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fid)
        ret, frame = cap.read()
        if not ret:
            continue

        frame_path = "temp.jpg"
        cv2.imwrite(frame_path, frame)

        pred, _ = predict_image(model, frame_path)
        preds.append(pred)

    cap.release()

    final_pred = Counter(preds).most_common(1)[0][0]
    confidence = preds.count(final_pred) / len(preds)

    return final_pred, confidence
