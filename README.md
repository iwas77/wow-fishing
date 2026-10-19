# wow-fishing
Machine Learning–Based WoW Auto Fishing

## Description
A machine learning-based automatic fishing program for World of Warcraft.

For a complete first-time setup, training, WoW configuration, and runtime guide,
read [userguide.md](userguide.md).

## Build Environment
- CPython 3.12.x on Windows (required; do not use Python 3.14)

## Requirements
```
ultralytics>=8.3.0
Pillow>=10.4.0,<12
PyAutoGUI==0.9.53
PyGetWindow==0.0.9
PyMsgBox==1.0.9
opencv-python>=4.10.0.84
pywin32>=306
```

## Installation & Setup

### 1. Environment Setup
1. Create and activate Conda environment
   ```bash
   conda create -n wow python=3.12
   conda activate wow
   ```

2. Clone the project
   ```bash
   git clone ...
   ```

3. Install dependencies
   ```bash
   python --version  # must report Python 3.12.x
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

### 2. Game Configuration
4. Launch World of Warcraft
5. Resize game client: Set to 1/4 of screen size
6. Action bar setup: Place fishing cast button in slot '1'
7. Game settings: Enable Auto Loot
8. Adjust camera view: Position camera so the fishing bobber is clearly visible

### 3. Run the Program
9. Navigate to source directory
    ```bash
    cd src
    ```

10. Run the program
    ```bash
    python fishing_controller.py
    ```

11. Adjust sub-window positions as needed

<img width="2784" height="1680" alt="Image" src="https://github.com/user-attachments/assets/43100f55-ba96-486f-9aec-9a282b076d7d" />

https://www.youtube.com/watch?v=5MDABw8fMuM

## YOLO11 training and runtime

For a detailed Korean explanation of the training pipeline, inference flow,
metrics, and improvement work, see [the YOLO11 training guide](docs/yolo11_training_guide.ko.md).

The application now runs the self-contained `models/bobber/best.pt`
checkpoint. It does not use `TrainYourOwnYOLO-master` at runtime.

1. Source images and their VoTT labels are stored in `data/bobber/raw`.
2. From the project root, prepare and train the YOLO11 model:
   ```bash
   python src/train_bobber_detector.py
   ```
   Use `--prepare-only` to validate the conversion without training.
3. The script converts VoTT pixel boxes to YOLO labels, creates
   `data/bobber/yolo11`, trains `yolo11s`, and copies the selected checkpoint
   to `models/bobber/best.pt`.
4. The training and runtime paths are independent of the removed legacy YOLOv3 repository.
