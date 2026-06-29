import json
import cv2

def load_config(filename='config.json'):
    try:
        with open(filename, 'r') as f:
            return json.load(f).get("rois", [])
    except:
        return []

def save_config(rois, filename='config.json'):
    with open(filename, 'w') as f:
        json.dump({"rois": rois}, f)

# State internal untuk mouse (disimpan dalam dictionary agar mudah diakses)
mouse_state = {
    "drawing": False,
    "is_dragging": False,
    "ix": -1, "iy": -1,
    "selected_roi_idx": -1
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
                if i < len(last_status): last_status.pop(i)
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
            chair_config[state["selected_roi_idx"]] = [roi[0]+dx, roi[1]+dy, roi[2]+dx, roi[3]+dy]
            state["ix"], state["iy"] = x, y
            detector.update_rois(chair_config)

    elif event == cv2.EVENT_LBUTTONUP:
        if state["drawing"]:
            new_roi = [min(state["ix"], x), min(state["iy"], y), max(state["ix"], x), max(state["iy"], y)]
            if abs(state["ix"] - x) > 10:
                chair_config.append(new_roi)
                last_status.append(False)
        
        state["drawing"] = False
        state["is_dragging"] = False
        state["selected_roi_idx"] = -1
        detector.update_rois(chair_config)
        save_config(chair_config)