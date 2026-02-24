# TrafficAnalyzer

TrafficAnalyzer is a tool for analyzing road traffic based on the YOLOv8 object detection model. It can process a set of images to detect vehicles (cars and trucks), calculate metrics like vehicle count and traffic density, and accurately classify the scene type (e.g., Traffic Jam, Heavy Traffic, Sparse Traffic, Single Big Object, Empty).

The project is capable of generating detailed PDF reports with annotated image highlights or dumping analytical data into CSV format for further research.

## Project Structure

- `data/` - Source images for traffic analysis. Place your `.jpg`, `.jpeg`, or `.png` images here.
- `experiments/` - Output directory for the `experiment` mode. Results are saved here as `.csv` files.
- `report_output/` - Output directory for the `report` mode. Detailed PDF reports and annotated image highlights are saved here.
- `tests/` - Contains unit tests to ensure the metrics calculation, scene classification, and highlighting logic work correctly.
- `traffic_analyzer.py` - The main executable script.

## Requirements and Installation

Make sure your environment has Python installed. Install all the required packages using `requirements.txt`:

```bash
pip install -r requirements.txt
```

**Key dependencies:**
- `ultralytics` (YOLOv8)
- `opencv-python`
- `numpy`
- `fpdf2`
- `tqdm`
- `torch`, `torchvision`

*(Optional)* For the best-looking PDF reports, the tool looks for `DejaVu` fonts inside a `ttf/` directory. If not present, it will fallback to the standard Arial font.

## Usage

The `traffic_analyzer.py` script requires you to choose a mode (`experiment` or `report`). You can also specify the confidence threshold for the YOLO model.

```bash
python traffic_analyzer.py <mode> [--conf CONFIDENCE_THRESHOLD]
```

### Modes

1. **`report` mode**
   This mode will perform a full analysis of the images in the `data/` folder. It will categorize the scene, highlight the most distinct examples (densest, most objects), generate visual annotations, and compile everything into a comprehensive PDF report saved in the `report_output/` directory.
   
   *Example:*
   ```bash
   python traffic_analyzer.py report --conf 0.45
   ```

2. **`experiment` mode**
   This mode is meant for rapid statistical analysis. It runs inference on all images in `data/` and saves the resulting metrics to a CSV file in the `experiments/` directory for further analysis. Visual annotations and PDFs are *not* generated in this mode.
   
   *Example:*
   ```bash
   python traffic_analyzer.py experiment --conf 0.45
   ```

### Command Line Arguments

- `mode`: `report` | `experiment`
- `--conf`: Confidence threshold for the YOLO model. Float between 0 and 1. (Default: 0.45)
