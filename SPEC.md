# Spec

A Python console tool that runs the YOLOv8 detector over still road images in `data/`, counts cars and trucks, sorts each scene into one of five traffic types, and writes either a CSV of per-image metrics or a PDF report in Russian.

Every `##` section below is one task. `Status` is one of To Do, In Progress, In Review, Done. The whole file is one ticket in Jira project KAN (the `Jira` line below), where every task is a checkbox: tick it there and the sync marks the task Done here; add one there and it is appended here.

Jira: KAN-58

## Find readable images in the source folder
Status: Done

`get_valid_image_paths` in `traffic_analyzer.py` lists a folder in sorted order and keeps only files with a `.jpg`, `.jpeg` or `.png` extension (any case) that OpenCV can open, so other files and broken images are skipped. An empty folder raises an exception. `tests/test_get_valid_image_paths.py` checks a copy of it against `tests/test_sandbox/`.

## Measure vehicles in each image
Status: Done

`analyze_image_metrics` in `traffic_analyzer.py` walks the detections of the YOLOv8n model (yolov8n.pt, which ultralytics fetches on first use; run at the `--conf` threshold, 0.45 by default), counts the target classes `car` and `truck`, and returns `total_vehicles`, `density` (summed vehicle box area divided by image area), `avg_bbox_area` and one count per class. An image with no vehicles gets 0 for density and average area instead of a division by zero.

## Classify each scene into five types
Status: Done

`classify_scene` in `traffic_analyzer.py` returns Empty, Traffic Jam, Single Big Object, Heavy Traffic or Sparse Traffic, checked in that order against the `THRESHOLDS` dict in the `report` branch: a jam needs at least 10 vehicles and density 0.3, a single big object at most 2 vehicles above density 0.15, heavy traffic at least 5 vehicles. The rules are documented in `docs/manual.md`.

## Write per-image metrics to CSV in experiment mode
Status: Done

`traffic_analyzer.py experiment --conf <t>` (or `.\recipe.ps1 run experiment`) runs the detector on every readable image in `data/` and writes one row per image to `experiments/analysis_conf_<t>.csv`, creating the folder if needed. A file that fails during processing is reported on the console and skipped. Runs at 0.25, 0.45, 0.5 and 0.7 are kept in `experiments/`.

## Build the PDF traffic report in report mode
Status: Done

`traffic_analyzer.py report` classifies every image, picks the top three by vehicle count and then density (`find_highlight_examples`), redraws their detections with the scene type and saves them as `report_output/highlight_<name>` (`generate_visualizations`). `PDFReport`, an `FPDF` subclass that uses the DejaVu fonts in `ttf/` and falls back to Arial, then writes `report_output/traffic_analysis_report.pdf` with a summary of vehicle totals and scene counts and one page per highlighted image.

## Build, test and lint through recipe.ps1
Status: Done

`recipe.ps1` holds the project's verbs: `run` starts the tool with `uv run --frozen`, `build` packs a wheel with `uv build`, `publish` copies it under `$env:LAB_SHARE`, and `test` checks that `$Version` matches `pyproject.toml`, points git at `.claude/hooks/git`, then runs pytest, mypy, `ruff check` and `ruff format`. The toolchain is pinned in `pyproject.toml` and `uv.lock`, and `.gitea/workflows/test.yaml` runs the same `test` and `build` verbs.

## Test the real module instead of copies
Status: To Do

Each of the five tool tests in `tests/` carries its own copy of the functions it checks, so the suite never imports `traffic_analyzer.py` and the coverage floor in `pyproject.toml` is 0 (the R-12 exception, #10). The copies have drifted (`analyze_image_metrics` in `tests/test_analyze_image_metrics.py` and `tests/test_classify_scene.py` lacks the zero-vehicle guard), both those files load the YOLOv8n weights and read `data/` at import time, and `tests/test_generate_visualizations.py` has no test function at all, only a `__main__` block. Done when the tests import from `traffic_analyzer`, no test downloads weights, and `--cov-fail-under` is raised above 0.

## Keep density within the frame
Status: To Do

`analyze_image_metrics` adds up the areas of all vehicle boxes, so overlapping boxes count twice and `density`, which `docs/manual.md` calls the share of the frame the vehicles cover, can exceed 1: `experiments/analysis_conf_0.45.csv` has 1.0277 for `33.png` and 1.8377 for `img1.jpg`. Done when density is computed from the union of the vehicle boxes and a test with two overlapping boxes gets a density no greater than 1.

## Fail clearly on missing input or output folders
Status: To Do

`get_valid_image_paths` raises a bare `Exception` whose message, "files is None or len(files) > 0", states the opposite of its condition, and a missing `data/` surfaces as a raw `FileNotFoundError`. The `report` branch never creates `report_output/`, so without that folder the unchecked `cv2.imwrite` in `generate_visualizations` writes nothing and `add_image_section` then crashes on the missing image, and an empty result calls `exit()` with code 0. Done when an empty or missing `data/` exits with a readable message and a non-zero code, and `report` creates `report_output/` itself.

## Write manual tests for both modes
Status: To Do

`tests/manual/tests.json` holds an empty `tests` list, so the manual round that `CONTRIBUTING.md` puts before `test` merges into `release` has nothing to check, and the manual gate in `.gitea/workflows/release-gate.yaml` passes it as "no manual tests defined". Done when it has at least one entry each for `experiment` and `report`, with steps and an expected result (the CSV has one row per readable image in `data/`; the PDF has a summary page and one page per highlighted image), and `tests/test_manual_list.py` still passes.
