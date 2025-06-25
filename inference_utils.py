import numpy as np
import onnxruntime as ort
from PIL import Image

session = ort.InferenceSession("bird_image_classifier.onnx", providers=["CPUExecutionProvider"])
input_name = session.get_inputs()[0].name
input_shape = session.get_inputs()[0].shape  # e.g., [1, 3, 640, 640]


def load_class_names(filepath="class_names.txt"):
    with open(filepath, "r") as f:
        return [line.strip() for line in f.readlines()]

CLASS_NAMES = load_class_names()


def preprocess_image(image: Image.Image):
    image = image.resize((input_shape[2], input_shape[3]))
    img_np = np.array(image).astype(np.float32) / 255.0
    img_np = np.transpose(img_np, (2, 0, 1))
    img_np = np.expand_dims(img_np, axis=0)
    return img_np


def nms(boxes, scores, iou_threshold=0.5):
    x1 = boxes[:,0]
    y1 = boxes[:,1]
    x2 = boxes[:,2]
    y2 = boxes[:,3]

    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep = []

    while order.size > 0:
        i = order[0]
        keep.append(i)

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0, xx2 - xx1)
        h = np.maximum(0, yy2 - yy1)
        inter = w * h

        iou = inter / (areas[i] + areas[order[1:]] - inter)

        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]

    return keep


def postprocess(output, conf_threshold=0.25, iou_threshold=0.5):
    preds = output[0]
    boxes, scores, class_ids = [], [], []

    for pred in preds[0]:
        conf = float(pred[4])
        if conf < conf_threshold:
            continue

        class_probs = pred[5:]
        class_id = int(np.argmax(class_probs))
        class_conf = class_probs[class_id] * conf

        if class_conf < conf_threshold:
            continue

        x_min, y_min, x_max, y_max = pred[0], pred[1], pred[2], pred[3]

        boxes.append([x_min, y_min, x_max, y_max])
        scores.append(class_conf)
        class_ids.append(class_id)

    if not boxes:
        return []

    boxes = np.array(boxes)
    scores = np.array(scores)
    class_ids = np.array(class_ids)

    final_class_ids = []

    unique_classes = np.unique(class_ids)
    for cls in unique_classes:
        cls_mask = class_ids == cls
        cls_boxes = boxes[cls_mask]
        cls_scores = scores[cls_mask]

        keep_indices = nms(cls_boxes, cls_scores, iou_threshold)

        if len(keep_indices) > 0:
            final_class_ids.append(cls)

    detected_species = [CLASS_NAMES[cid] for cid in final_class_ids]
    return detected_species


def perform_inference(image: Image.Image):
    input_tensor = preprocess_image(image)
    outputs = session.run(None, {input_name: input_tensor})
    results = postprocess(outputs)
    return results
