import json
import cv2
import os
import numpy as np


def load_config(filename="config.json"):
    base_dir = os.path.dirname(os.path.abspath(__file__))  # core/services/
    filepath = os.path.join(base_dir, filename)
    try:
        with open(filepath, "r") as f:
            return json.load(f).get("rois", [])
    except:
        return []


def save_config(rois, filename="config.json"):
    base_dir = os.path.dirname(os.path.abspath(__file__))  # core/services/
    filepath = os.path.join(base_dir, filename)
    with open(filepath, "w") as f:
        json.dump({"rois": rois}, f)


# State internal untuk mouse (disimpan dalam dictionary agar mudah diakses)
mouse_state = {
    "drawing": False,
    "is_dragging": False,
    "ix": -1,
    "iy": -1,
    "selected_roi_idx": -1,
}


def draw_roi_event(event, x, y, flags, param):
    # param berisi [CHAIR_CONFIG, last_status, detector] yang dikirim dari main
    chair_config, last_status, detector = param
    state = mouse_state

    # --- KLIK KANAN: HAPUS ---
    if event == cv2.EVENT_RBUTTONDOWN:
        for i, roi in enumerate(chair_config):
            if roi[0] < x < roi[2] and roi[1] < y < roi[3]:
                chair_config.pop(i)
                if i < len(last_status):
                    last_status.pop(i)
                detector.update_rois(chair_config)
                save_config(chair_config)
                break

    # --- KLIK KIRI: GESER/BUAT ---
    elif event == cv2.EVENT_LBUTTONDOWN:
        state["selected_roi_idx"] = -1
        for i, roi in enumerate(chair_config):
            if roi[0] < x < roi[2] and roi[1] < y < roi[3]:
                state["selected_roi_idx"] = i
                state["is_dragging"] = True
                state["ix"], state["iy"] = x, y
                break

        if not state["is_dragging"]:
            state["drawing"] = True
            state["ix"], state["iy"] = x, y

    elif event == cv2.EVENT_MOUSEMOVE:
        if state["is_dragging"] and state["selected_roi_idx"] != -1:
            dx, dy = x - state["ix"], y - state["iy"]
            roi = chair_config[state["selected_roi_idx"]]
            chair_config[state["selected_roi_idx"]] = [
                roi[0] + dx,
                roi[1] + dy,
                roi[2] + dx,
                roi[3] + dy,
            ]
            state["ix"], state["iy"] = x, y
            detector.update_rois(chair_config)

    elif event == cv2.EVENT_LBUTTONUP:
        if state["drawing"]:
            new_roi = [
                min(state["ix"], x),
                min(state["iy"], y),
                max(state["ix"], x),
                max(state["iy"], y),
            ]
            if abs(state["ix"] - x) > 10:
                chair_config.append(new_roi)
                last_status.append(False)

        state["drawing"] = False
        state["is_dragging"] = False
        state["selected_roi_idx"] = -1
        detector.update_rois(chair_config)
        save_config(chair_config)


def compute_iou(box1, box2):
    """Compute Intersection over Union between two bounding boxes.
    
    Args:
        box1, box2: arrays of [x1, y1, x2, y2]
        
    Returns:
        float: IoU value
    """
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = box1_area + box2_area - inter_area
    
    return inter_area / union_area if union_area > 0 else 0.0


def match_keypoints_to_tracked(yolo_boxes, yolo_keypoints, tracked_objects, iou_threshold=0.3):
    """Mencocokkan deteksi YOLO (dengan titik kunci) dengan objek yang dilacak ByteTrack menggunakan IoU.

        Argumen:
        yolo_boxes: array numpy dengan bentuk (N, 4) berisi kotak deteksi YOLO
        yolo_keypoints: array numpy dengan bentuk (N, 17, 3) berisi titik kunci
        tracked_objects: daftar objek ByteTrack
        iou_threshold: IoU minimum untuk mempertimbangkan kecocokan

        Hasil:
        dict: track_id -> array titik kunci untuk objek yang cocok
        """
    matched = {}
    used_yolo = set()
    
    for obj in tracked_objects:
        track_id = obj.track_id
        track_box = obj.xyxy  # [x1, y1, x2, y2]
        best_iou = 0
        best_idx = -1
        
        for j, yolo_box in enumerate(yolo_boxes):
            if j in used_yolo:
                continue
            iou = compute_iou(track_box, yolo_box)
            if iou > best_iou:
                best_iou = iou
                best_idx = j
        
        if best_iou >= iou_threshold and best_idx != -1:
            matched[track_id] = yolo_keypoints[best_idx]
            used_yolo.add(best_idx)
    
    return matched
