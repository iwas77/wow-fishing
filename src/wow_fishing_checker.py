"""World of Warcraft fishing bobber detector and controller."""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import sys
import time

import cv2
import numpy as np
import pyautogui
import win32api
import win32con
import win32gui
import win32ui
from PIL import Image, ImageDraw

from util import Rect


# title of the WoW window
WOW_WINDOW_TITLE = "월드 오브 워크래프트"
PULL_DELAY = 5
CAPTURE_DELAY = 0.02
CASTING_DELAY = 1
CASTING_SLOT_NUMBER = "1"
MISSING_BOBBER_TIMEOUT = 3
MINIMUM_DISTANCE_COUNT = 5
DISTANCE_HISTORY_SIZE = 20
DISTANCE_MULTIPLIER = 6
MINIMUM_MOVEMENT_RATIO = 1.0
REQUIRED_MOVEMENT_FRAMES = 2
# IMPROVEMENT: Enable the live capture/detection preview by default for tuning.
SHOW_DETECTION_STATUS = True

# IMPROVEMENT: Resolve resources from this file rather than the launch directory.
SOURCE_DIR = Path(__file__).resolve().parent
MODEL_PATH = SOURCE_DIR / "Data" / "Model_Weights" / "trained_weights_final.h5"
ANCHORS_PATH = SOURCE_DIR / "Data" / "Model_Weights" / "yolo_anchors.txt"
CLASSES_PATH = SOURCE_DIR / "Data" / "Model_Weights" / "data_classes.txt"

# IMPROVEMENT: Use the checked-out YOLO source when it is present in the project.
YOLO_SOURCE_DIR = SOURCE_DIR.parent / "TrainYourOwnYOLO-master" / "2_Training" / "src" / "keras_yolo3"
if YOLO_SOURCE_DIR.is_dir():
    sys.path.insert(0, str(YOLO_SOURCE_DIR))

from yolo import YOLO


yolo_model = None


@dataclass
class BobberInfo:
    """A single bobber observation."""

    # IMPROVEMENT: Instance fields avoid the shared mutable class defaults.
    box: Rect
    at: datetime = field(default_factory=datetime.now)


def find_target_window(title):
    """Return the first visible window whose title contains ``title``."""
    matches = []

    def callback(hwnd, hwnd_list):
        if win32gui.IsWindowVisible(hwnd) and title in win32gui.GetWindowText(hwnd):
            hwnd_list.append(hwnd)
        return True

    win32gui.EnumWindows(callback, matches)
    return matches[0] if matches else None


def capture_target_window(title):
    """Capture a window and return its image, handle, and screen origin."""
    hwnd = find_target_window(title)
    if hwnd is None or not win32gui.IsWindow(hwnd):
        raise RuntimeError(f"Target window was not found: {title}")

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        raise RuntimeError("Target window has an invalid size")

    desktop = win32gui.GetDesktopWindow()
    desktop_dc = win32gui.GetWindowDC(desktop)
    mfc_dc = save_dc = bitmap = None
    try:
        mfc_dc = win32ui.CreateDCFromHandle(desktop_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)
        # IMPROVEMENT: pywin32 BitBlt returns None on success; failures raise an exception.
        # Checking its return value incorrectly treated every successful capture as a failure.
        save_dc.BitBlt((0, 0), (width, height), mfc_dc, (left, top), win32con.SRCCOPY)

        info = bitmap.GetInfo()
        pixels = bitmap.GetBitmapBits(True)
        image = Image.frombuffer(
            "RGB", (info["bmWidth"], info["bmHeight"]), pixels, "raw", "BGRX", 0, 1
        )
        # IMPROVEMENT: Preserve the capture origin for a reliable screen-coordinate conversion.
        return image, hwnd, (left, top)
    finally:
        # IMPROVEMENT: Always release Windows GDI resources, including on capture failure.
        if bitmap is not None:
            win32gui.DeleteObject(bitmap.GetHandle())
        if save_dc is not None:
            save_dc.DeleteDC()
        if mfc_dc is not None:
            mfc_dc.DeleteDC()
        win32gui.ReleaseDC(desktop, desktop_dc)


def send_key(hwnd, key):
    """Send a key press after validating the target window."""
    if hwnd is None or not win32gui.IsWindow(hwnd):
        raise RuntimeError("Target window is no longer available")
    win32gui.SetForegroundWindow(hwnd)
    win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, ord(key), 0)
    time.sleep(0.1)
    win32api.SendMessage(hwnd, win32con.WM_KEYUP, ord(key), 0)


def init_yolo():
    """Load the model after validating the locally resolved weight file."""
    global yolo_model
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Model weights not found: {MODEL_PATH}")
    yolo_model = YOLO(
        model_path=str(MODEL_PATH), anchors_path=str(ANCHORS_PATH), classes_path=str(CLASSES_PATH)
    )


def detect_bobber(image):
    """Return raw YOLO detections, or ``None`` when no bobber is detected."""
    if yolo_model is None:
        raise RuntimeError("YOLO model has not been initialized")
    detections = yolo_model.detect_image(image, show_stats=False)[0]
    return detections if len(detections) else None


def select_bobber_box(detections, previous_box=None):
    """Pick the detection nearest to the previously tracked bobber."""
    boxes = [Rect(*detection[:4]) for detection in detections if len(detection) >= 4]
    if not boxes:
        return None
    if previous_box is None:
        return boxes[0]

    # IMPROVEMENT: Do not switch bobbers when multi-object detections change order.
    previous_center = previous_box.center()
    return min(boxes, key=lambda box: previous_center.dist(box.center()))


def pull_force(bobber_info, capture_origin):
    """Right-click the bobber using the coordinate system of the captured image."""
    center = bobber_info.box.center()
    # IMPROVEMENT: Avoid fragile title-bar constants by converting directly to screen coordinates.
    point = (int(capture_origin[0] + center.x), int(capture_origin[1] + center.y))
    print(f">> pulling at {point}")
    pyautogui.moveTo(*point)
    pyautogui.rightClick()
    time.sleep(PULL_DELAY)


def casting():
    """Cast a fishing line, returning False when the game window is unavailable."""
    hwnd = find_target_window(WOW_WINDOW_TITLE)
    if hwnd is None:
        print(">> ERROR :: target window not found; will retry")
        return False
    send_key(hwnd, CASTING_SLOT_NUMBER)
    time.sleep(CASTING_DELAY)
    return True


def show_detect_status(image, info, status_lines=None):
    """Display the debug frame only when explicitly enabled."""
    if not SHOW_DETECTION_STATUS:
        return
    draw = ImageDraw.Draw(image)
    if info is not None:
        draw.rectangle(info.box.list(), outline=(255, 128, 128))
        draw.rectangle(Rect.from_point(info.box.center(), 2).list(), fill=(0, 255, 0))
    # IMPROVEMENT: Overlay live detection and movement metrics on the preview frame.
    if status_lines:
        text = "\n".join(status_lines)
        text_bounds = draw.multiline_textbbox((10, 10), text, spacing=2)
        draw.rectangle(text_bounds, fill=(0, 0, 0))
        draw.multiline_text((10, 10), text, fill=(255, 255, 0), spacing=2)
    cv2.imshow("bobber detection", cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR))
    cv2.waitKeyEx(1)


def is_something_happened(current_ratio, history):
    """Return whether movement exceeds a robust, recent baseline."""
    if len(history) < MINIMUM_DISTANCE_COUNT:
        return False
    baseline = float(np.median(history))
    threshold = max(MINIMUM_MOVEMENT_RATIO, baseline * DISTANCE_MULTIPLIER)
    print(f">> check dist info = {current_ratio:.3f}, baseline = {baseline:.3f}")
    return current_ratio > threshold


def run_fishing_cycle():
    """Track one cast until its bobber disappears or is pulled."""
    try:
        image, _, _ = capture_target_window(WOW_WINDOW_TITLE)
    except RuntimeError as error:
        print(f">> ERROR :: {error}")
        return

    initial_detections = detect_bobber(image.copy())
    if initial_detections is None:
        show_detect_status(image, None, ["Detection: none", "Action: casting"])
        print(">> bobber not detected; casting")
        casting()
        return

    initial_box = select_bobber_box(initial_detections)
    if initial_box is None:
        show_detect_status(image, None, ["Detection: invalid", "Action: casting"])
        print(">> invalid bobber detection; casting")
        casting()
        return

    # IMPROVEMENT: Retain the initial detection so a following missing frame has a timeout baseline.
    previous_info = BobberInfo(initial_box)
    last_seen_at = previous_info.at
    # IMPROVEMENT: Show the first captured frame, including its selected bobber box.
    show_detect_status(image, previous_info, ["Detection: found", "Distance: -- (initial frame)"])
    distance_history = deque(maxlen=DISTANCE_HISTORY_SIZE)
    movement_frames = 0

    while True:
        time.sleep(CAPTURE_DELAY)
        try:
            image, _, capture_origin = capture_target_window(WOW_WINDOW_TITLE)
        except RuntimeError as error:
            print(f">> ERROR :: {error}")
            return

        detections = detect_bobber(image.copy())
        if detections is None:
            show_detect_status(image, None, ["Detection: none", "Distance: --"])
            # IMPROVEMENT: Start the disappearance timeout only after a real prior observation.
            if last_seen_at and (datetime.now() - last_seen_at).total_seconds() >= MISSING_BOBBER_TIMEOUT:
                return
            continue

        box = select_bobber_box(detections, previous_info.box if previous_info else None)
        if box is None:
            continue
        current_info = BobberInfo(box)
        last_seen_at = current_info.at

        if previous_info is None:
            # IMPROVEMENT: The first valid frame initializes the tracker; it is not movement.
            show_detect_status(image, current_info, ["Detection: found", "Distance: -- (initial frame)"])
            previous_info = current_info
            continue

        union_box = previous_info.box.union(current_info.box)
        if union_box.height() <= 0:
            show_detect_status(image, current_info, ["Detection: found", "Distance: invalid box height"])
            previous_info = current_info
            continue
        distance = previous_info.box.center().dist(current_info.box.center())
        distance_ratio = distance / union_box.height() * 100.0

        movement_detected = is_something_happened(distance_ratio, distance_history)
        baseline = float(np.median(distance_history)) if distance_history else None
        threshold = (
            max(MINIMUM_MOVEMENT_RATIO, baseline * DISTANCE_MULTIPLIER)
            if baseline is not None and len(distance_history) >= MINIMUM_DISTANCE_COUNT
            else None
        )
        preview_lines = [
            "Detection: found",
            f"Distance: {distance_ratio:.3f}%",
            f"Baseline: {baseline:.3f}%" if baseline is not None else "Baseline: collecting samples",
            f"Threshold: {threshold:.3f}%" if threshold is not None else "Threshold: collecting samples",
            f"Samples: {len(distance_history)}/{MINIMUM_DISTANCE_COUNT}",
            f"Movement frames: {movement_frames}/{REQUIRED_MOVEMENT_FRAMES}",
        ]
        # IMPROVEMENT: Draw the metrics after calculating this frame's distance.
        show_detect_status(image, current_info, preview_lines)

        if movement_detected:
            movement_frames += 1
            if movement_frames >= REQUIRED_MOVEMENT_FRAMES:
                pull_force(current_info, capture_origin)
                return
        else:
            movement_frames = 0
            # IMPROVEMENT: Keep a bounded baseline of normal motion only.
            distance_history.append(distance_ratio)

        previous_info = current_info


def start():
    """Initialize dependencies and repeatedly run fishing cycles."""
    init_yolo()
    while True:
        run_fishing_cycle()
        time.sleep(1)


if __name__ == "__main__":
    start()
