"""Test script untuk memverifikasi perbaikan bug scoring engine.

Menjalankan: python test_fix.py
"""
import os
import sys
import numpy as np

# Set environment variables untuk test
os.environ['USE_SCORING'] = 'true'
os.environ['POSTURE_TEMPORAL_WINDOW'] = '10'
os.environ['SITTING_MIN_CONSISTENT_FRAMES'] = '5'

# Import modul yang akan diuji
from track_manager import TrackManager
from scoring_engine import ScoringEngine
from posture_classifier import PostureClassifier
from hand_activity import calculate_hand_activity, is_barber_for_chair
from detector import SimpleByteTrack

# ============================================================
# MOCK TrackObject (sama seperti di detector.py)
# ============================================================
class MockTrackObject:
    def __init__(self, track_id, xyxy):
        self.track_id = track_id
        self.xyxy = xyxy
        self.confidence = 1.0
        self.age = 0

# ============================================================
# TEST 1: identify_barber_for_chair dengan barber di dalam ROI
# ============================================================
def test_barber_inside_roi():
    print("\n=== TEST 1: Barber berdiri DI DALAM ROI ===")
    
    # ROI kursi (kecil/kencang)
    rois = [[100, 200, 200, 400]]  # [x1, y1, x2, y2]
    
    # Barber berdiri di dalam ROI (centroid di dalam ROI)
    barber_box = [120, 210, 180, 390]  # bbox barber
    barber_centroid = ((120+180)/2, (210+390)/2)  # (150, 300) - di dalam ROI
    
    # Customer duduk di dalam ROI (lebih dekat ke bawah kursi)
    customer_box = [110, 250, 190, 400]
    
    tracked_objects = [
        MockTrackObject(1, barber_box),   # Barber
        MockTrackObject(2, customer_box)  # Customer
    ]
    
    tm = TrackManager()
    
    # Simulasikan posture history: barber = STANDING, customer = SITTING
    tm.posture_history[1] = ['STANDING'] * 10
    tm.posture_history[2] = ['SITTING'] * 10
    
    # Panggil identify_barber_for_chair
    barber_tid = tm.identify_barber_for_chair(0, rois, tracked_objects)
    
    print(f"  Barber track_id: {barber_tid}")
    print(f"  Expected: 1 (barber berdiri di dalam ROI)")
    
    assert barber_tid == 1, f"FAIL: Expected 1, got {barber_tid}"
    print("  ✓ PASS: Barber teridentifikasi dengan benar")
    return True

# ============================================================
# TEST 2: identify_barber_for_chair dengan barber di dekat ROI
# ============================================================
def test_barber_near_roi():
    print("\n=== TEST 2: Barber berdiri DEKAT ROI (di luar) ===")
    
    # ROI kursi
    rois = [[100, 200, 200, 400]]
    
    # Barber berdiri di samping ROI (jarak ~50px dari pusat ROI)
    barber_box = [50, 180, 130, 380]  # bbox barber di kiri ROI
    barber_centroid = ((50+130)/2, (180+380)/2)  # (90, 280)
    
    # Customer duduk di dalam ROI
    customer_box = [110, 250, 190, 400]
    
    tracked_objects = [
        MockTrackObject(1, barber_box),   # Barber
        MockTrackObject(2, customer_box)  # Customer
    ]
    
    tm = TrackManager()
    tm.posture_history[1] = ['STANDING'] * 10
    tm.posture_history[2] = ['SITTING'] * 10
    
    barber_tid = tm.identify_barber_for_chair(0, rois, tracked_objects)
    
    print(f"  Barber track_id: {barber_tid}")
    print(f"  Expected: 1 (barber berdiri dekat ROI)")
    
    assert barber_tid == 1, f"FAIL: Expected 1, got {barber_tid}"
    print("  ✓ PASS: Barber teridentifikasi dengan benar")
    return True

# ============================================================
# TEST 3: identify_barber_for_chair dengan hanya customer
# ============================================================
def test_only_customer():
    print("\n=== TEST 3: Hanya customer (tidak ada barber) ===")
    
    rois = [[100, 200, 200, 400]]
    
    # Hanya customer duduk di dalam ROI
    customer_box = [110, 250, 190, 400]
    
    tracked_objects = [
        MockTrackObject(2, customer_box)
    ]
    
    tm = TrackManager()
    tm.posture_history[2] = ['SITTING'] * 10
    
    barber_tid = tm.identify_barber_for_chair(0, rois, tracked_objects)
    
    print(f"  Barber track_id: {barber_tid}")
    print(f"  Expected: None (tidak ada barber)")
    
    assert barber_tid is None, f"FAIL: Expected None, got {barber_tid}"
    print("  ✓ PASS: Tidak ada barber teridentifikasi")
    return True

# ============================================================
# TEST 4: is_barber_for_chair di hand_activity.py
# ============================================================
def test_is_barber_for_chair():
    print("\n=== TEST 4: is_barber_for_chair (hand_activity.py) ===")
    
    rois = [[100, 200, 200, 400]]
    
    # Barber berdiri di dalam ROI
    barber_box = [120, 210, 180, 390]
    
    tracked_objects = [
        MockTrackObject(1, barber_box)
    ]
    
    # Keypoints dummy (17 titik, format [x, y, conf])
    kpts = np.zeros((17, 3))
    for i in range(17):
        kpts[i] = [150, 300, 0.9]  # Semua titik di tengah dengan conf tinggi
    
    posture_history = {1: ['STANDING'] * 10}
    
    is_barber = is_barber_for_chair(
        kpts=kpts,
        track_id=1,
        chair_id=0,
        rois=rois,
        tracked_objects=tracked_objects,
        posture_history=posture_history
    )
    
    print(f"  is_barber: {is_barber}")
    print(f"  Expected: True (barber berdiri di dalam ROI)")
    
    assert is_barber is True, f"FAIL: Expected True, got {is_barber}"
    print("  ✓ PASS: Barber terdeteksi sebagai barber")
    return True

# ============================================================
# TEST 5: ScoringEngine.calculate dengan tracked_objects
# ============================================================
def test_scoring_engine():
    print("\n=== TEST 5: ScoringEngine.calculate dengan tracked_objects ===")
    
    rois = [[100, 200, 200, 400]]
    
    # Barber berdiri di dalam ROI
    barber_box = [120, 210, 180, 390]
    # Customer duduk di dalam ROI
    customer_box = [110, 250, 190, 400]
    
    tracked_objects = [
        MockTrackObject(1, barber_box),
        MockTrackObject(2, customer_box)
    ]
    
    tm = TrackManager()
    
    # Simulasikan data tracking (10 titik trajectory untuk stabilitas)
    barber_centroid = ((120+180)/2, (210+390)/2)   # (150, 300)
    customer_centroid = ((110+190)/2, (250+400)/2) # (150, 325)
    tm.trajectories[1] = [barber_centroid] * 10   # Barber
    tm.trajectories[2] = [customer_centroid] * 10 # Customer
    
    tm.posture_history[1] = ['STANDING'] * 10
    tm.posture_history[2] = ['SITTING'] * 10
    
    # Simulasikan hand activity: barber aktif, customer tidak
    tm.hand_activity[1] = [3, 4, 5, 3, 4]  # Barber aktif
    tm.hand_activity[2] = [0, 0, 0, 0, 0]  # Customer tidak
    
    engine = ScoringEngine()
    
    score, breakdown = engine.calculate(
        chair_id=0,
        track_manager=tm,
        rois=rois,
        duration=200,  # > 180 detik
        tracked_objects=tracked_objects
    )
    
    print(f"  Total score: {score}")
    print(f"  Breakdown: {breakdown}")
    print(f"  Expected: score > 0 (bukan 0)")
    
    assert score > 0, f"FAIL: Expected score > 0, got {score}"
    print("  ✓ PASS: Score > 0")
    
    # Verifikasi komponen
    assert breakdown['hand_activity'] > 0, "FAIL: hand_activity harus > 0"
    print(f"  ✓ PASS: hand_activity = {breakdown['hand_activity']} > 0")
    
    assert breakdown['posture'] > 0, "FAIL: posture harus > 0"
    print(f"  ✓ PASS: posture = {breakdown['posture']} > 0")
    
    assert breakdown['person_count'] > 0, "FAIL: person_count harus > 0"
    print(f"  ✓ PASS: person_count = {breakdown['person_count']} > 0")
    
    return True

# ============================================================
# TEST 6: SimpleByteTrack - track bertahan antar frame
# ============================================================
def test_simple_byte_track_persistence():
    print("\n=== TEST 6: SimpleByteTrack - track bertahan antar frame ===")
    
    tracker = SimpleByteTrack()
    
    # Simulasikan 2 orang terdeteksi di 5 frame berurutan
    # dengan bbox hampir identik (gerakan kecil antar frame)
    person1_slight_move = [
        [100, 200, 200, 400],
        [101, 200, 201, 400],
        [102, 200, 202, 400],
        [103, 200, 203, 400],
        [104, 200, 204, 400],
    ]
    person2_slight_move = [
        [300, 200, 400, 400],
        [301, 200, 401, 400],
        [302, 200, 402, 400],
        [303, 200, 403, 400],
        [304, 200, 404, 400],
    ]
    
    boxes_per_frame = [
        np.array([person1_slight_move[i], person2_slight_move[i]], dtype=np.float32)
        for i in range(5)
    ]
    
    previous_track_ids = None
    for frame_idx, boxes in enumerate(boxes_per_frame):
        tracked = tracker.update(boxes)
        track_ids = sorted([obj.track_id for obj in tracked])
        print(f"  Frame {frame_idx + 1}: {len(tracked)} tracked objects, IDs={track_ids}")
        
        # Frame 1: harus ada 2 track baru
        if frame_idx == 0:
            assert len(tracked) == 2, f"FAIL: Frame 1 harus punya 2 track, got {len(tracked)}"
        else:
            # Frame berikutnya: track harus BERTAHAN (bukan 0)
            assert len(tracked) == 2, (
                f"FAIL: Frame {frame_idx + 1} harus punya 2 track, got {len(tracked)}. "
                f"Bug: track dihapus terlalu cepat!"
            )
            # Track ID harus konsisten (tidak berganti-ganti)
            assert track_ids == previous_track_ids, (
                f"FAIL: Track ID berubah! Frame {frame_idx}: {track_ids}, "
                f"Frame {frame_idx + 1}: {previous_track_ids}"
            )
        
        previous_track_ids = track_ids
    
    print("  ✓ PASS: Track bertahan konsisten selama 5 frame")
    return True

# ============================================================
# TEST 7: update_tracks meneruskan chair_id ke hand_activity
# ============================================================
def test_update_tracks_chair_id():
    print("\n=== TEST 7: update_tracks meneruskan chair_id ===")
    
    rois = [[100, 200, 200, 400]]
    
    # Barber berdiri di dalam ROI
    barber_box = [120, 210, 180, 390]
    
    tracked_objects = [
        MockTrackObject(1, barber_box)
    ]
    
    # Keypoints dummy untuk barber (berdiri - bahu tinggi, pinggul rendah)
    kpts = np.zeros((17, 3))
    # Bahu di y=250, pinggul di y=350 (berdiri)
    kpts[5] = [140, 250, 0.9]   # LEFT_SHOULDER
    kpts[6] = [160, 250, 0.9]   # RIGHT_SHOULDER
    kpts[11] = [140, 350, 0.9]  # LEFT_HIP
    kpts[12] = [160, 350, 0.9]  # RIGHT_HIP
    kpts[0] = [150, 220, 0.9]   # NOSE
    kpts[9] = [130, 260, 0.9]   # LEFT_WRIST
    kpts[10] = [170, 260, 0.9]  # RIGHT_WRIST
    
    keypoints_per_track = {1: kpts}
    
    tm = TrackManager()
    pc = PostureClassifier()
    
    # Track apakah chair_id diteruskan ke hand_activity_func
    captured_chair_id = [None]
    
    def mock_hand_activity(kpts, prev_kpts, frame_height, **kwargs):
        captured_chair_id[0] = kwargs.get('chair_id')
        return 3  # Return dummy points
    
    tm.update_tracks(
        tracked_objects=tracked_objects,
        keypoints_per_track=keypoints_per_track,
        rois=rois,
        frame_height=480,
        posture_classifier=pc,
        hand_activity_func=mock_hand_activity,
        current_frame=1
    )
    
    print(f"  chair_id diteruskan: {captured_chair_id[0]}")
    print(f"  Expected: 0 (bukan None)")
    
    assert captured_chair_id[0] == 0, f"FAIL: Expected chair_id=0, got {captured_chair_id[0]}"
    print("  ✓ PASS: chair_id diteruskan dengan benar")
    
    # Verifikasi posture history
    assert 1 in tm.posture_history, "FAIL: posture_history tidak terisi"
    print(f"  ✓ PASS: posture_history terisi: {tm.posture_history[1]}")
    
    # Verifikasi hand_activity
    assert 1 in tm.hand_activity, "FAIL: hand_activity tidak terisi"
    print(f"  ✓ PASS: hand_activity terisi: {tm.hand_activity[1]}")
    
    return True

# ============================================================
# TEST 8: PostureClassifier - fallback lokasi customer dengan cape
# ============================================================
def test_posture_location_fallback():
    print("\n=== TEST 8: PostureClassifier - fallback lokasi customer dengan cape ===")
    
    pc = PostureClassifier()
    
    # ROI kursi
    roi = [100, 200, 200, 400]
    
    # --- Kasus 1: Customer dengan cape (keypoints body TIDAK reliable) DI DALAM ROI → SITTING ---
    # Keypoints: wajah terdeteksi (nose/eyes/ears), tapi body TIDAK (cape menutupi)
    kpts_cape = np.zeros((17, 3))
    kpts_cape[0] = [150, 220, 0.9]   # NOSE - terdeteksi
    kpts_cape[1] = [145, 220, 0.9]   # LEFT_EYE - terdeteksi
    kpts_cape[2] = [155, 220, 0.9]   # RIGHT_EYE - terdeteksi
    kpts_cape[3] = [140, 225, 0.9]   # LEFT_EAR - terdeteksi
    kpts_cape[4] = [160, 225, 0.9]   # RIGHT_EAR - terdeteksi
    # Body keypoints (5-12) TIDAK terdeteksi (conf=0.05) karena cape
    
    # Bbox customer di dalam ROI
    bbox_inside = np.array([110, 250, 190, 400], dtype=np.float32)
    
    result = pc.classify(
        kpts=kpts_cape,
        bbox=bbox_inside,
        roi=roi,
        frame_height=480,
        chair_id=0,
        track_id=200
    )
    print(f"  Customer cape di dalam ROI: {result}")
    assert result == 'SITTING', f"FAIL: Expected SITTING, got {result}"
    print("  ✓ PASS: Customer dengan cape di dalam ROI → SITTING")
    
    # --- Kasus 2: Barber (keypoints body TIDAK reliable) DI LUAR ROI → STANDING ---
    # Bbox di luar ROI (tidak overlap > 30% dengan ROI [100, 200, 200, 400])
    bbox_outside = np.array([10, 180, 80, 380], dtype=np.float32)
    
    result = pc.classify(
        kpts=kpts_cape,
        bbox=bbox_outside,
        roi=roi,
        frame_height=480,
        chair_id=0,
        track_id=201
    )
    print(f"  Barber di luar ROI (cape): {result}")
    assert result == 'STANDING', f"FAIL: Expected STANDING, got {result}"
    print("  ✓ PASS: Barber di luar ROI → STANDING")
    
    # --- Kasus 3: Keypoints body reliable → pakai logika existing (area_ratio) ---
    # Barber dengan tubuh terlihat jelas (bahu + pinggul terdeteksi)
    kpts_reliable = np.zeros((17, 3))
    kpts_reliable[0] = [150, 200, 0.9]   # NOSE
    kpts_reliable[5] = [140, 250, 0.9]   # LEFT_SHOULDER
    kpts_reliable[6] = [160, 250, 0.9]   # RIGHT_SHOULDER
    kpts_reliable[11] = [140, 350, 0.9]  # LEFT_HIP
    kpts_reliable[12] = [160, 350, 0.9]  # RIGHT_HIP
    
    # Bbox tinggi (berdiri) → area_ratio kecil → STANDING
    bbox_standing = np.array([100, 150, 200, 450], dtype=np.float32)
    
    result = pc.classify(
        kpts=kpts_reliable,
        bbox=bbox_standing,
        roi=roi,
        frame_height=480,
        chair_id=0,
        track_id=202
    )
    print(f"  Keypoints body reliable (berdiri): {result}")
    assert result == 'STANDING', f"FAIL: Expected STANDING, got {result}"
    print("  ✓ PASS: Keypoints body reliable → pakai logika existing")
    
    # --- Kasus 4: kpts=None di dalam ROI → SITTING (fallback lokasi) ---
    result = pc.classify(
        kpts=None,
        bbox=bbox_inside,
        roi=roi,
        frame_height=480,
        chair_id=0,
        track_id=203
    )
    print(f"  kpts=None di dalam ROI: {result}")
    assert result == 'SITTING', f"FAIL: Expected SITTING, got {result}"
    print("  ✓ PASS: kpts=None di dalam ROI → SITTING")
    
    return True

# ============================================================
# TEST 9: PostureScore - butuh customer SITTING + barber STANDING
# ============================================================
def test_posture_score_requires_both():
    print("\n=== TEST 9: PostureScore - butuh customer SITTING + barber STANDING ===")
    
    rois = [[100, 200, 200, 400]]
    engine = ScoringEngine()
    
    # --- Kasus 1: Customer SITTING + Barber STANDING → posture_score = 100 ---
    tm = TrackManager()
    tm.trajectories[1] = [(150, 300)] * 10  # Barber (di dalam ROI tapi STANDING)
    tm.trajectories[2] = [(150, 300)] * 10  # Customer (di dalam ROI, SITTING)
    tm.posture_history[1] = ['STANDING'] * 10
    tm.posture_history[2] = ['SITTING'] * 10
    
    tracked_objects = [
        MockTrackObject(1, [120, 210, 180, 390]),  # Barber
        MockTrackObject(2, [110, 250, 190, 400])   # Customer
    ]
    
    score = engine.calculate_posture_score(0, tm, rois, tracked_objects)
    print(f"  Customer SITTING + Barber STANDING: {score}")
    assert score == 100, f"FAIL: Expected 100, got {score}"
    print("  ✓ PASS: Customer SITTING + Barber STANDING → 100")
    
    # --- Kasus 2: 2 orang STANDING (ngobrol) → posture_score = 0 ---
    tm2 = TrackManager()
    tm2.trajectories[1] = [(150, 300)] * 10  # Person 1
    tm2.trajectories[2] = [(150, 300)] * 10  # Person 2
    tm2.posture_history[1] = ['STANDING'] * 10
    tm2.posture_history[2] = ['STANDING'] * 10
    
    tracked_objects2 = [
        MockTrackObject(1, [120, 210, 180, 390]),
        MockTrackObject(2, [110, 250, 190, 400])
    ]
    
    score = engine.calculate_posture_score(0, tm2, rois, tracked_objects2)
    print(f"  2 orang STANDING (ngobrol): {score}")
    assert score == 0, f"FAIL: Expected 0, got {score}"
    print("  ✓ PASS: 2 orang STANDING → 0")
    
    # --- Kasus 3: Customer SITTING saja (tanpa barber) → posture_score = 0 ---
    tm3 = TrackManager()
    tm3.trajectories[2] = [(150, 300)] * 10  # Customer
    tm3.posture_history[2] = ['SITTING'] * 10
    
    tracked_objects3 = [
        MockTrackObject(2, [110, 250, 190, 400])
    ]
    
    score = engine.calculate_posture_score(0, tm3, rois, tracked_objects3)
    print(f"  Customer SITTING saja: {score}")
    assert score == 0, f"FAIL: Expected 0, got {score}"
    print("  ✓ PASS: Customer SITTING saja → 0")
    
    # --- Kasus 4: Barber STANDING saja (tanpa customer) → posture_score = 0 ---
    tm4 = TrackManager()
    tm4.trajectories[1] = [(150, 300)] * 10  # Barber
    tm4.posture_history[1] = ['STANDING'] * 10
    
    tracked_objects4 = [
        MockTrackObject(1, [120, 210, 180, 390])
    ]
    
    score = engine.calculate_posture_score(0, tm4, rois, tracked_objects4)
    print(f"  Barber STANDING saja: {score}")
    assert score == 0, f"FAIL: Expected 0, got {score}"
    print("  ✓ PASS: Barber STANDING saja → 0")
    
    return True

# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("TEST PERBAIKAN BUG SCORING ENGINE")
    print("=" * 60)
    
    tests = [
        test_barber_inside_roi,
        test_barber_near_roi,
        test_only_customer,
        test_is_barber_for_chair,
        test_scoring_engine,
        test_simple_byte_track_persistence,
        test_update_tracks_chair_id,
        test_posture_location_fallback,
        test_posture_score_requires_both
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"  ✗ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"HASIL: {passed} PASS, {failed} FAIL")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("SEMUA TEST LULUS!")