# wow-fishing
Machine Learning–Based WoW Auto Fishing

## Description
A machine learning-based automatic fishing program for World of Warcraft.

## Build Environment
- Python 3.7.16

## Requirements
```
tensorflow==2.3
keras==2.4
Pillow==9.3.0
matplotlib==3.5.3
PyAutoGUI==0.9.53
PyGetWindow==0.0.9
PyMsgBox==1.0.9
opencv-python==4.6.0.66
pywin32==305
```

## Installation & Setup

### 1. Environment Setup
1. Create and activate Conda environment
   ```bash
   conda create -n wow python=3.7.16
   conda activate wow
   ```

2. Clone the project
   ```bash
   git clone ...
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

### 2. Model Weights Preparation
4. Extract RAR files
   - Extract `src\Data\Model_Weights\*.rar` files to generate `trained_weights_final.h5`

5. Download TrainYourOwnYOLO
   - From the project root directory, clone the repository:
     ```bash
     git clone https://github.com/iwas77/TrainYourOwnYOLO.git
     ```
   - This places the source in `TrainYourOwnYOLO` under the project root.

6. Configure `src\wow_fishing_checker.py`
   - Set `MODEL_PATH`, `ANCHORS_PATH`, and `CLASSES_PATH` to the corresponding files under `src\Data\Model_Weights`. With the program launched from the `src` directory, the existing relative paths are:
     ```python
     MODEL_PATH = './Data/Model_Weights/trained_weights_final.h5'
     ANCHORS_PATH = './Data/Model_Weights/yolo_anchors.txt'
     CLASSES_PATH = './Data/Model_Weights/data_classes.txt'
     ```
   - Update both `sys.path.append(...)` entries to the `keras_yolo3` directory in the downloaded source. Replace `<PROJECT_ROOT>` with the actual path to your project:
     ```python
     sys.path.append('<PROJECT_ROOT>\\TrainYourOwnYOLO\\2_Training\\src\\keras_yolo3')
     sys.path.append('<PROJECT_ROOT>\\TrainYourOwnYOLO\\2_Training\\src\\keras_yolo3')
     ```

### 3. Game Configuration
7. Launch World of Warcraft
8. Resize game client: Set to 1/4 of screen size
9. Action bar setup: Place fishing cast button in slot '1'
10. Game settings: Enable Auto Loot
11. Adjust camera view: Position camera so the fishing bobber is clearly visible

### 4. Run the Program
12. Navigate to source directory
    ```bash
    cd src
    ```

13. Run the program
    ```bash
    python wow_fishing_checker.py
    ```

14. Adjust sub-window positions as needed

<img width="2784" height="1680" alt="Image" src="https://github.com/user-attachments/assets/43100f55-ba96-486f-9aec-9a282b076d7d" />

https://www.youtube.com/watch?v=5MDABw8fMuM
