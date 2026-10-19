# WoW Fishing: Complete User Guide

This guide starts from the same place as a new user: you downloaded or cloned
this repository and have nothing else configured. Follow the sections in order.

> Important: this software automates input in a game window. Make sure its use
> is permitted by the game's current rules and by the rules of the server where
> you play. You are responsible for using it appropriately.

## 1. What this project does

The project trains a YOLO11 object-detection model to find a fishing bobber in
World of Warcraft screenshots. The runtime program then captures the WoW window,
detects the bobber, watches it move, and performs a right-click after the
configured movement rule is met.

There are two separate jobs:

1. **Training** teaches a new model from labeled images. It creates
   `models/bobber/best.pt`.
2. **Runtime detection** loads that model while WoW is open and uses it to find
   the bobber continuously.

Training is required only when no `best.pt` model exists or when you want a
better model. Runtime detection needs only the completed `best.pt` checkpoint.

## 2. Repository layout

```text
wow-fishing/
├─ data/
│  └─ bobber/
│     ├─ raw/
│     │  ├─ annotations.csv       # Original VoTT annotations; source of truth
│     │  └─ images/               # Images named by annotations.csv
│     └─ yolo11/                  # Generated training/validation dataset
├─ docs/
│  └─ yolo11_training_guide.ko.md # Detailed Korean technical guide
├─ models/
│  └─ bobber/
│     └─ best.pt                  # Generated trained model; absent before training
├─ runs/
│  └─ yolo11/bobber/              # Generated Ultralytics logs, charts, checkpoints
├─ src/
│  ├─ train_bobber_detector.py    # Converts labels and trains YOLO11
│  ├─ geometry.py                 # Small geometry helpers
│  └─ fishing_controller.py       # Captures WoW and runs detection/tracking
├─ requirements.txt                # Python packages to install
├─ README.md                       # Short project overview
└─ userguide.md                    # This complete setup guide
```

### Which directories should you keep?

- Keep `data/bobber/raw`. It contains the original images and annotations used
  to reproduce or improve training.
- Keep `models/bobber/best.pt` after a successful training run. It is the model
  used by the runtime program.
- `data/bobber/yolo11` and `runs/yolo11` are generated folders. The training
  script recreates the dataset folder each time; the runs folder is useful for
  comparing training attempts.
- The root-level `yolo11s.pt`, if present, is Ultralytics' downloaded pretrained
  starting checkpoint. It may be downloaded automatically during training if it
  is absent and the machine has internet access.

## 3. Install Python

Use **CPython 3.12.x on Windows**. Do not use Python 3.14 for this project.
The package versions in `requirements.txt` are selected for Python 3.12.

1. Install a Python 3.12.x release from the official Python website.
2. In the Python installer, select **Add python.exe to PATH**.
3. Open a new PowerShell or Command Prompt window in the repository root.
4. Confirm the version:

```powershell
py -3.12 --version
```

The output must begin with `Python 3.12`.

### Optional: use a virtual environment

A virtual environment keeps this project's packages separate from other Python
projects on your computer.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

After activation, `python --version` must show Python 3.12.x. If PowerShell
blocks activation, run the commands in Command Prompt instead:

```bat
.venv\Scripts\activate.bat
```

## 4. Install Python modules

From the repository root, run:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The important packages are:

- `ultralytics`: YOLO11 training and object detection.
- `Pillow`: reads images and their dimensions while labels are converted.
- `opencv-python`: displays the live detection preview window.
- `pywin32`: captures the Windows game window and sends keyboard input.
- `PyAutoGUI`: moves the mouse and right-clicks the detected bobber.

The first installation can take time because Ultralytics installs PyTorch and
its supporting packages. For NVIDIA GPU acceleration, install an NVIDIA driver
compatible with the PyTorch build selected by pip.

## 5. Check the training images and annotations

The project expects these two items:

```text
data/bobber/raw/annotations.csv
data/bobber/raw/images/
```

`annotations.csv` must contain these columns:

```text
image,xmin,ymin,xmax,ymax,label
```

Each `image` value must match a file name somewhere under `images`. The current
dataset contains 80 annotated bobber images and one class named `bb`.

Run this command to check the number of image files:

```powershell
Get-ChildItem .\data\bobber\raw\images -Recurse -File |
  Where-Object { $_.Extension -in '.jpg', '.jpeg', '.png', '.bmp', '.webp' } |
  Measure-Object
```

The `Count` should be at least the number of unique image names in the CSV.
The training script performs the same filename check and stops with a clear
error if any annotated image is missing.

### Adding more images

More varied images usually improve the model more than changing model settings.
Add screenshots with different lighting, water colors, camera distances, weather,
UI layouts, and fishing locations. Every image that should be used for training
must have an annotation row in `annotations.csv`.

Do not simply copy an unlabeled image into `images` and expect this script to
train on it: the current script intentionally uses only image names listed in
the CSV. Label new images with a VoTT-compatible CSV row before training.

## 6. Prepare the YOLO dataset

Before spending time on training, validate the input data:

```powershell
python src\train_bobber_detector.py --prepare-only
```

This command does the following:

1. Finds all supported images under `data/bobber/raw/images`.
2. Reads the original pixel-coordinate rectangles from `annotations.csv`.
3. Checks that every CSV image exists.
4. Splits the image names into training and validation groups. The default split
   is approximately 80% training and 20% validation.
5. Converts each rectangle to YOLO's normalized label format.
6. Creates `data/bobber/yolo11/data.yaml`, image copies, and label files.

It does **not** train the neural network when `--prepare-only` is present.

> Warning: `data/bobber/yolo11` is a generated directory. The script deletes
> and recreates it on each preparation run. Do not place your only original
> images or annotations in that directory.

## 7. Train the model

Run the normal training command after preparation succeeds:

```powershell
python src\train_bobber_detector.py
```

The default configuration is:

```text
base model:  yolo11s.pt
epochs:      100
image size:  1280 x 1280
validation:  20%
batch size:  automatic (-1)
```

The first run can download `yolo11s.pt`; leave internet access enabled for that
step. If an NVIDIA GPU is available, Ultralytics normally selects it
automatically. To force CPU mode for a troubleshooting run, use:

```powershell
python src\train_bobber_detector.py --device cpu
```

CPU training can take a long time. GPU training is strongly recommended.

## 8. Understand the generated model and results

After a successful training run, look for these outputs:

```text
runs/yolo11/bobber/weights/best.pt   # Best checkpoint from the run
models/bobber/best.pt                # Copy used by the fishing runtime
```

`best.pt` is a PyTorch model checkpoint. It contains the learned YOLO11 weights
for the `bb` class. The runtime program loads only `models/bobber/best.pt`; it
does not need the old YOLOv3 repository or H5 files.

The `runs/yolo11/bobber` directory also contains charts and validation outputs.
Use them to compare separate training attempts. Important values include:

- **Precision**: how often a reported bobber is truly a bobber.
- **Recall**: how many real bobbers were found.
- **mAP50** and **mAP50-95**: combined bounding-box accuracy scores.
- **Loss curves**: whether the model continued learning or began overfitting.

Do not assume a fixed accuracy before you train. With only 80 labeled images,
the validation set is small, so one or two unusual images can noticeably change
the reported score. Test the final model in actual game scenes as well.

## 9. Configure World of Warcraft

Before running the automation:

1. Start World of Warcraft and log into the character used for fishing.
2. Use a stable, non-minimized game window. A window around one quarter of the
   screen is a practical starting point because it reduces capture cost.
3. Set the camera so that the bobber is clearly visible and has enough empty
   water around it. Do not change the camera while testing a model.
4. Put the fishing-cast ability in action-bar slot **1**. The runtime sends the
   `1` key by default.
5. Enable **Auto Loot** in the game settings.
6. Ensure the window title matches `WOW_WINDOW_TITLE` in
   `src/fishing_controller.py`. Edit that constant if your WoW client uses a
   different localized title.
7. Keep the game window visible. The application captures the visible desktop
   pixels, so a fully hidden or covered window may not produce reliable images.

If you change the hotkey, update `CASTING_SLOT_NUMBER` in the same source file.

## 10. Run automatic detection and fishing

First confirm that `models/bobber/best.pt` exists. Then run:

```powershell
python src\fishing_controller.py
```

The program performs this cycle:

1. Finds the WoW window by title.
2. Captures the visible window pixels.
3. Runs YOLO11 at an input size of 1280 with a confidence threshold of 0.25.
4. Keeps class `0` (`bb`) detections and selects the candidate nearest to the
   bobber from the previous frame.
5. Measures the bobber's vertical movement against recent normal movement.
6. Right-clicks after the movement threshold is met for the required consecutive
   frames.
7. Starts another cycle.

Stop the program with `Ctrl+C` in the terminal.

## 11. Confirm the result

When the runtime starts, it opens a window named **bobber detection**. This is
the most useful first check.

Expected preview information:

- A colored rectangle around the detected bobber.
- `Detection: found` when YOLO11 sees a bobber.
- `Distance`, `Baseline`, and `Threshold` values after several frames.
- `Detection: none` if no valid bobber was found.
- `Action: casting` when no bobber is available and the program sends the cast
  key.

Expected terminal information:

- A model-load message from Ultralytics.
- Distance and baseline logs while tracking.
- `pulling at (...)` immediately before an automated right-click.

If the preview rectangle is wrong, do not immediately lower the confidence
threshold. First collect and label screenshots that look like the failing game
scene, then train again. This is usually the most reliable improvement.

## 12. Troubleshooting

### `No module named 'PIL'` or another missing module

You are probably using the wrong Python installation or did not finish package
installation. Activate the Python 3.12 environment, then run:

```powershell
python -m pip install -r requirements.txt
```

### Pillow fails to install

Check `python --version`. It must be Python 3.12.x, not Python 3.14. Then update
pip and install the requirements again.

### `YOLO11 checkpoint not found`

Run the training script successfully first. Confirm that
`models/bobber/best.pt` was created.

### No WoW window is found

Start WoW, keep its window visible, and compare its exact title with
`WOW_WINDOW_TITLE` in `src/fishing_controller.py`.

### The detection window is black, frozen, or wrong

Keep WoW visible and uncovered. Try windowed mode, reduce other overlays, and
verify that the selected window is the game client rather than a launcher.

### The model detects the wrong object

Add representative screenshots of that scene, label the bobber precisely, and
retrain. Also inspect whether the `bb` class is still class number 0.

## 13. Additional reading

- [Detailed Korean YOLO11 training guide](docs/yolo11_training_guide.ko.md)
- [Ultralytics YOLO11 documentation](https://docs.ultralytics.com/models/yolo11/)
- [Ultralytics training documentation](https://docs.ultralytics.com/modes/train/)
- [Ultralytics prediction documentation](https://docs.ultralytics.com/modes/predict/)
- [PyTorch installation guide](https://pytorch.org/get-started/locally/)
