# TrafficAnalyzer: Software Requirements Specification

Reverse-engineered from commit `9027764` (2026-11-17) of branch `ta-58/docs/spec-md`, which is `origin/test` (`1ea51d9`, 2026-11-07) plus the commit that added the first version of this file. Every requirement describes behaviour present in that tree; sources are `path:line`. `origin/release` (`434c0f1`, tag `v1.0.0`) has the same tree except that it lacks `CHANGELOG.md` and `SPEC.md`. `origin/dev` (`37240bf`, 2026-02-24) has the same program logic, before formatting under ruff and with an unused `numpy` import, and none of `pyproject.toml`, `uv.lock`, `recipe.ps1`, `.gitea/`, `docs/` or `LICENSE`; it is not covered. Documentation hub: [docs/README.md](docs/README.md).

The task list of this file mirrors Jira ticket KAN-58: its six done tasks are subsections 3.2 to 3.7 and its four open tasks are the last four rows of the table in section 3.8, under the same titles. The sync reads every `### 3.N` subsection of section 3 up to 3.7 as a done task and every row of that table as an open one, so 3.1 and the first three rows of 3.8, which are not in the ticket, would be added to it.

<!-- jira-sync:start -->
Jira: KAN-58

## Tasks

This list is one ticket in Jira project KAN, [KAN-58](https://igorsvolohovs.atlassian.net/browse/KAN-58). Each line is a checkbox there: tick it in Jira and the sync ticks it here; add a checkbox there and it is appended here. Done items are the features described in section 3; open items are what the project declares but the code does not do yet.

- [x] Command line (section 3.1) <!-- spec-command-line -->
- [x] Find readable images in the source folder (section 3.2) <!-- spec-find-readable-images-in-the-source-folder -->
- [x] Measure vehicles in each image (section 3.3) <!-- spec-measure-vehicles-in-each-image -->
- [x] Classify each scene into five types (section 3.4) <!-- spec-classify-each-scene-into-five-types -->
- [x] Write per-image metrics to CSV in experiment mode (section 3.5) <!-- spec-write-per-image-metrics-to-csv-in-experiment-mode -->
- [x] Build the PDF traffic report in report mode (section 3.6) <!-- spec-build-the-pdf-traffic-report-in-report-mode -->
- [x] Build, test and lint through recipe.ps1 (section 3.7) <!-- spec-build-test-and-lint-through-recipe-ps1 -->
- [ ] Highlights picked per criterion (most vehicles, densest) (declared, not implemented) <!-- spec-highlights-picked-per-criterion-most-vehicles-dens -->
- [ ] `--conf` limited to a number from 0 to 1 (declared, not implemented) <!-- spec-conf-limited-to-a-number-from-0-to-1 -->
- [ ] Fallback to a standard font when the DejaVu fonts are missing (declared, not implemented) <!-- spec-fallback-to-a-standard-font-when-the-dejavu-fonts- -->
- [ ] Test the real module instead of copies (declared, not implemented) <!-- spec-test-the-real-module-instead-of-copies -->
- [ ] Keep density within the frame (declared, not implemented) <!-- spec-keep-density-within-the-frame -->
- [ ] Fail clearly on missing input or output folders (declared, not implemented) <!-- spec-fail-clearly-on-missing-input-or-output-folders -->
- [ ] Write manual tests for both modes (declared, not implemented) <!-- spec-write-manual-tests-for-both-modes -->

<!-- jira-sync:end -->

## 1. Purpose and scope

The system detects cars and trucks on still road images with a YOLOv8n model, computes per-image metrics, and either writes the metrics to CSV (`experiment` mode) or classifies each image into a scene type and produces a PDF report in Russian with annotated examples (`report` mode).

In scope:

- Discovery of readable `.jpg`, `.jpeg`, `.png` files in `data/`.
- Detection with the pretrained `yolov8n.pt` weights at a user-given confidence threshold.
- Metrics: vehicle count per class, total count, summed box area relative to image area, average box area.
- Rule-based scene classification into five types.
- CSV export; PDF report with summary statistics and three annotated highlight images.
- The developer verbs of `recipe.ps1`: run, test and lint, build and publish a wheel (section 3.7).

Out of scope (absent from the code):

- Video and camera streams (`data/webmfile.webm` is skipped by the extension filter, `traffic_analyzer.py:15`, `23`).
- Training or fine-tuning the model; any class other than `car` and `truck`.
- Object tracking, speed measurement, geolocation, time series.
- Any network service, GUI or persistent database.

## 2. Context

Actors:

- Operator who runs the tool from a shell and reads the CSV or PDF. Who this person is is not stated (section 9).
- Contributor who opens an issue, branches from `test`, runs `.\recipe.ps1 test` and opens a pull request into `test` (`CONTRIBUTING.md:3-12`).

External systems and components:

| Component | Role | Source |
|---|---|---|
| ultralytics `YOLO` | Loads `yolov8n.pt`, runs detection, draws boxes | `traffic_analyzer.py:10`, `240`, `281`, `249`, `289`, `101`, `104` |
| OpenCV (`cv2`) | Decodes images, draws the scene label, writes PNG/JPEG | `traffic_analyzer.py:6`, `25`, `246`, `287`, `107-110` |
| fpdf2 (`FPDF`) | Builds the PDF | `traffic_analyzer.py:7-8`, `149-212` |
| tqdm | Console progress bar | `traffic_analyzer.py:9`, `244`, `285` |
| uv | Installs the locked environment and runs every tool | `docs/install.md:3`, `5`; `recipe.ps1:49`, `61`, `99-106` |
| Gitea Actions | Run `recipe.ps1` on pull requests and pushes | `.gitea/workflows/` (FR-36) |
| File system | Input `data/`, outputs `experiments/`, `report_output/`, `dist/`, fonts `ttf/`, weights `yolov8n.pt` | section 4 |

Runtime environment:

- Python 3.12 only: `requires-python = ">=3.12,<3.13"` (`pyproject.toml:22`), locked as `==3.12.*` (`uv.lock:3`). The reason given is that the pinned `torch` and `numpy` have no Windows wheels for 3.13 (`pyproject.toml:20-21`, `docs/install.md:3`).
- OS: the workflows run on `windows` runners (`.gitea/workflows/test.yaml:16`) and the recipe is a PowerShell script. Other systems are not declared; the lock resolves for macOS, Linux and Windows markers (`uv.lock:4-10`). Paths are built with `os.path.join` (`traffic_analyzer.py:24`, `99`, `109`, `154-155`, `261`, `332`). Inference: the `.vscode/launch.json` debug configuration (type `debugpy`) indicates VS Code was used for development.
- Hardware: not declared; no `device` argument is passed to the model (`traffic_analyzer.py:249`, `289`).
- Working directory: must be the repository root, because every path is relative (NFR-6).

## 3. Functional requirements

### 3.1 Command line

- **FR-1.** The system shall accept one positional argument `mode` with the values `experiment` or `report` and reject other values. Source: `traffic_analyzer.py:220-226`. Verification: no test.
- **FR-2.** The system shall accept an optional `--conf` float, default `0.45`, and pass it as the detection confidence threshold to every model call. Source: `traffic_analyzer.py:227-229`, `249`, `289`, `302`. Verification: no test.
- **FR-3.** The system shall print the mode name (`experiment mode` or `report mode`) and show a tqdm progress bar while processing images. Source: `traffic_analyzer.py:234`, `244`, `269`, `285`. Verification: no test.

### 3.2 Find readable images in the source folder

- **FR-4.** The system shall list the source directory in sorted file-name order and keep only files whose extension, lower-cased, is `.jpg`, `.jpeg` or `.png`. Source: `traffic_analyzer.py:15`, `21-23`. Verification: `tests/test_get_valid_image_paths.py::test_get_valid_image_paths` (tests an AST-identical copy against `tests/test_sandbox/`).
- **FR-5.** The system shall skip files with an accepted extension that OpenCV cannot decode. Source: `traffic_analyzer.py:25-26`. Verification: no test (the sandbox has no undecodable file with an accepted extension).
- **FR-6.** The system shall raise an exception when the source directory is empty. Source: `traffic_analyzer.py:17-19`. Verification: no test.

### 3.3 Measure vehicles in each image

- **FR-7.** The system shall load the weights `yolov8n.pt` from the working directory and run detection on each discovered image with `verbose=False`. Source: `traffic_analyzer.py:240`, `249`, `281`, `289`. `docs/install.md:7` states that the first run downloads the file into the working folder; not verified here. Verification: no test.
- **FR-8.** The system shall count, per image, the detections whose class name is in `TARGET_CLASSES = ["car", "truck"]`, returning a count per class and a total `total_vehicles`. Source: `traffic_analyzer.py:34`, `49-56`, `60`, `236`, `277`. Verification: `tests/test_analyze_image_metrics.py::test_analyze_image_metrics` (tests a copy without the zero guards of lines 62 and 64).
- **FR-9.** The system shall compute `density` as the sum of `w*h` of target-class boxes divided by image width times height, rounded to 4 decimals. Source: `traffic_analyzer.py:44-46`, `54`, `62`, `68`, `247`, `251`, `288`, `290`. Verification: `tests/test_analyze_image_metrics.py::test_analyze_image_metrics` (expects 0.0525, `tests/test_analyze_image_metrics.py:122`).
- **FR-10.** The system shall compute `avg_bbox_area` as the summed target-class box area divided by the target-class count, rounded to 2 decimals. Source: `traffic_analyzer.py:64`, `69`. Verification: `tests/test_analyze_image_metrics.py::test_analyze_image_metrics` (expects 17500.0, `tests/test_analyze_image_metrics.py:128`).
- **FR-11.** The system shall return `density = 0` and `avg_bbox_area = 0` when no target-class box is found. Source: `traffic_analyzer.py:62`, `64`. Verification: no test (the tested copy lacks this guard).
- **FR-12.** The system shall add the image file name (`filename`) to each metrics record. Source: `traffic_analyzer.py:254`, `293`. Verification: no test.
- **FR-13.** The system shall catch any exception raised while processing one image, print the file path and the error, and continue with the next image. Source: `traffic_analyzer.py:245-257`, `286-296`. Verification: no test.

### 3.4 Classify each scene into five types

- **FR-14.** The system shall classify each record by the first matching rule: `Empty` if `total_vehicles == 0`; `Traffic Jam` if `total_vehicles >= jam_count` and `density >= jam_density`; `Single Big Object` if `total_vehicles <= 2` and `density > single_density`; `Heavy Traffic` if `total_vehicles >= heavy_count`; otherwise `Sparse Traffic`. Source: `traffic_analyzer.py:125-146`; the same rules, in the same order and with the same values, are written for the operator in `docs/manual.md:17-25`. Verification: `tests/test_classify_scene.py::test_classify_scene` (10 cases, AST-identical copy).
- **FR-15.** In `report` mode the system shall use the thresholds `jam_count = 10`, `jam_density = 0.3`, `heavy_count = 5`, `single_density = 0.15` and store the result in the record as `scene_type`. Source: `traffic_analyzer.py:271-276`, `292`. Verification: no test of the main block; the test uses the same values (`tests/test_classify_scene.py:122-127`).

### 3.5 Write per-image metrics to CSV in experiment mode

- **FR-16.** In `experiment` mode the system shall write all records to `experiments/analysis_conf_{conf}.csv` (UTF-8, header from the keys of the first record), creating `experiments/` if missing and overwriting an existing file of the same name. Source: `traffic_analyzer.py:259-266`. Verification: no test; manual comparison with the committed CSV files (section 8).
- **FR-17.** In `experiment` mode the system shall not classify scenes, draw annotations or build a PDF. Source: `traffic_analyzer.py:233-266`. Verification: no test.
- **FR-18.** The system shall write no CSV when no record was produced. Source: `traffic_analyzer.py:259`. Verification: no test.

### 3.6 Build the PDF traffic report in report mode

- **FR-19.** The system shall select highlight examples by sorting records by `(total_vehicles, density)` in descending order and taking the first `top_n = 3`; when fewer than `top_n` records exist, all are returned. Source: `traffic_analyzer.py:76-92`, `301`. Verification: `tests/test_find_highlight_examples.py::test_find_highlight_examples` (AST-identical copy).
- **FR-20.** For each highlight the system shall re-run detection on `data/{filename}` at `--conf`, draw the detections, write the scene type at pixel (10, 40) in green, and save the image as `report_output/highlight_{filename}`. Source: `traffic_analyzer.py:98-110`, `302`. Verification: no test.
- **FR-21.** For each highlight the system shall build a text block with file name, scene type, total vehicles, car and truck counts, density as a percentage with 2 decimals, and average box area in whole pixels. Source: `traffic_analyzer.py:112-120`. Verification: no test.
- **FR-22.** The system shall build the PDF with `PDFReport`, a subclass of `FPDF`, which prints on every page a centred header `Аналитический отчёт по дорожной обстановке` with the generation date in `DD.MM.YYYY`, and a footer `Страница {n}`. Source: `traffic_analyzer.py:149`, `166-186`. Verification: no test.
- **FR-23.** The system shall write a summary section with the number of processed images, the threshold used, total vehicles, cars, trucks, and the number of images per scene type. Source: `traffic_analyzer.py:307-323`. Verification: no test.
- **FR-24.** The system shall add one page per highlight, ordered by `density` descending, titled `Пример #{i}: {filename}`, with the annotated image 100 units wide, centred, followed by the text block of FR-21. Source: `traffic_analyzer.py:200-212`, `325-330`. Verification: no test.
- **FR-25.** The system shall save the PDF as `report_output/traffic_analysis_report.pdf` and print its path. Source: `traffic_analyzer.py:332-335`. Verification: no test.
- **FR-26.** The system shall use `ttf/DejaVuSans.ttf` and `ttf/DejaVuSans-Bold.ttf` as the PDF font when both files exist, and set the font family to `Arial` otherwise. Source: `traffic_analyzer.py:154-164`. Verification: no test.
- **FR-27.** In `report` mode the system shall exit without producing output when no record was produced. Source: `traffic_analyzer.py:298-299`. Verification: no test.

### 3.7 Build, test and lint through recipe.ps1

- **FR-28.** `recipe.ps1` shall accept one verb out of `build`, `install`, `uninstall`, `clean`, `run`, `publish`, `info`, `test`, reject any other, and run the verb from the repository root. Source: `recipe.ps1:1-7`, `29`, `45-47`. Verification: not run here.
- **FR-29.** The verb `run` shall start `uv run --frozen python traffic_analyzer.py` with the arguments that follow the verb and exit with its exit code. Source: `recipe.ps1:5-6`, `60-63`; usage in `README.md:12-13` and `docs/manual.md:4`. Verification: not run here.
- **FR-30.** The verb `test` shall stop with exit code 1 and the message `Version mismatch` when `$Version` (`recipe.ps1:13`) differs from the `[project]` version in `pyproject.toml` (`pyproject.toml:16`); otherwise it shall set git's `core.hooksPath` to `.claude/hooks/git`, then run pytest, mypy, `ruff check .` and `ruff format .` through `uv run --frozen`, stopping at the first non-zero exit code. `ruff format` rewrites files in place. Source: `recipe.ps1:82-109`. Verification: not run here.
- **FR-31.** pytest shall collect `tests/test_*.py` with `-q --cov=. --cov-report=term --cov-fail-under=0`; mypy shall check `traffic_analyzer.py` and `tools/` for Python 3.12, ignoring missing imports only for `fpdf`, `tqdm` and `ultralytics`; ruff shall apply the rule sets `E4`, `E7`, `E9`, `F` and `I` at line length 120 and format with LF line endings, leaving `.claude/`, `tests/manual/serve.py` and `tools/wiki.py` unformatted. Source: `pyproject.toml:52-92`. Verification: not run here.
- **FR-32.** The verb `build` shall write a wheel to `dist` with `uv build --wheel --out-dir dist`; the wheel carries the single module `traffic_analyzer`, built by setuptools 80.9.0. Source: `recipe.ps1:19`, `48-51`; `pyproject.toml:7-11`, `44-46`. Verification: not run here.
- **FR-33.** The verb `publish` shall exit with code 1 and the message `LAB_SHARE is not set, so there is nowhere to publish to` when `LAB_SHARE` is unset; otherwise it shall build the wheel and copy it to `$env:LAB_SHARE\needs\traffic-analyzer\v1.0.0`. Source: `recipe.ps1:11`, `13`, `64-73`. Verification: not run here.
- **FR-34.** The verb `clean` shall delete `dist`, `build`, `out` and `.coverage`; `install` and `uninstall` shall print that there is nothing to do and exit 0; `info` shall print the name, code, version, summary and provided files. Source: `recipe.ps1:52-59`, `74-81`. Verification: not run here.
- **FR-35.** Before any verb, the recipe shall load the `NAME=value` lines of `.claude/.env`, when that file exists, into environment variables that are not already set. Source: `recipe.ps1:34-43`; the file is ignored by git (`.gitignore:24`). Verification: not run here.
- **FR-36.** The workflow `test` shall run on every push to `test`, on the schedule `0 3 * * *` and on manual start, and shall run `.\recipe.ps1 test`, fail when that leaves a change in the tree (`git diff --exit-code`), and then run `.\recipe.ps1 build`. The workflows `propose` (pull requests into `test`) and `release-gate` (pull requests into `release`) run the same `test` verb and the same diff check. Source: `.gitea/workflows/test.yaml:1-7`, `54-60`; `.gitea/workflows/propose.yaml:1-5`, `144-152`; `.gitea/workflows/release-gate.yaml:1-5`, `49-53`. Verification: no workflow run observed.

### 3.8 Declared but not implemented

Claims made in the repository that the code does not meet (the first three rows), and the tasks proposed in Jira KAN-58 that are not done yet (the last four rows, one open task of the ticket each).

| Item | Description | Source |
|---|---|---|
| Highlights picked per criterion (most vehicles, densest) | The docstring and comment of `find_highlight_examples` speak of choosing the top images per criterion, but the code sorts once by `(total_vehicles, density)`, so density only breaks ties and an image with the highest density but a low count is not selected. | Claim `traffic_analyzer.py:80`, `89`; code `traffic_analyzer.py:90` |
| `--conf` limited to a number from 0 to 1 | The manual gives the range 0 to 1, but argparse checks only the type, so `--conf 2` is accepted. | Claim `docs/manual.md:13`; code `traffic_analyzer.py:227-229` |
| Fallback to a standard font when the DejaVu fonts are missing | The code switches the font family to `Arial` under a comment saying the standard font is used; inference from fpdf2 behaviour, not run: core fonts cannot encode the Cyrillic header, so the PDF step most likely fails instead. | Claim `traffic_analyzer.py:163`; code `traffic_analyzer.py:162-164`, `172` |
| Test the real module instead of copies | The five tool tests carry their own, partly drifted copies of the functions instead of importing `traffic_analyzer.py`, two of them load the YOLOv8n weights and read `data/` at import time, one has no test function, and the coverage floor is 0; done when the tests import the module, download no weights and the floor is above 0. | Jira KAN-58 (task proposed 2026-11-17) |
| Keep density within the frame | `density` sums the areas of all vehicle boxes, so overlaps count twice and values above 1 occur in `experiments/analysis_conf_0.45.csv`; done when it is computed from the union of the boxes and a test with two overlapping boxes stays at or below 1. | Jira KAN-58 (task proposed 2026-11-17) |
| Fail clearly on missing input or output folders | An empty `data/` raises a bare `Exception` whose message contradicts its condition, a missing one raises a raw `FileNotFoundError`, `report` never creates `report_output/`, and an empty result exits with code 0; done when both cases exit non-zero with a readable message and `report` creates its output folder. | Jira KAN-58 (task proposed 2026-11-17) |
| Write manual tests for both modes | `tests/manual/tests.json` has an empty `tests` list, so the release gate passes the manual round as "no manual tests defined"; done when it has at least one entry each for `experiment` and `report` with steps and an expected result, and `tests/test_manual_list.py` still passes. | Jira KAN-58 (task proposed 2026-11-17) |

## 4. Interfaces

### 4.1 CLI

| Element | Type | Values / default | Source |
|---|---|---|---|
| `mode` | positional | `experiment` \| `report` | `traffic_analyzer.py:220-226` |
| `--conf` | float option | default `0.45`, no range check (section 3.8) | `traffic_analyzer.py:227-229` |
| `-h`, `--help` | argparse built-in | help text in Russian | `traffic_analyzer.py:216-229` |

Exit behaviour: an empty `data/` raises an uncaught exception (FR-6) and a missing `data/` raises `FileNotFoundError` from `os.listdir` (`traffic_analyzer.py:17`); report mode with no records calls `exit()` (FR-27), which ends with status 0; otherwise the script ends normally. No explicit exit codes are set.

### 4.2 Input files

| Path | Format | Rule | Source |
|---|---|---|---|
| `data/*` | image files | extension `.jpg`, `.jpeg`, `.png` in any case, decodable by `cv2.imread` | `traffic_analyzer.py:15-27` |
| `yolov8n.pt` | ultralytics weights | working directory; not in the repository (`.gitignore:27`) | `traffic_analyzer.py:240`, `281` |
| `ttf/DejaVuSans.ttf`, `ttf/DejaVuSans-Bold.ttf` | TrueType | optional | `traffic_analyzer.py:154-157` |

### 4.3 Output files

| Path | Mode | Format | Source |
|---|---|---|---|
| `experiments/analysis_conf_{conf}.csv` | experiment | CSV, UTF-8, comma; columns `total_vehicles, density, avg_bbox_area, car, truck, filename` | `traffic_analyzer.py:261-266`; header seen in `experiments/analysis_conf_0.45.csv:1` |
| `report_output/highlight_{filename}` | report | image in the format of the source extension | `traffic_analyzer.py:109-110` |
| `report_output/traffic_analysis_report.pdf` | report | PDF, Russian text | `traffic_analyzer.py:332-333` |
| `dist/*.whl` | `recipe.ps1 build`, `publish` | wheel with the module `traffic_analyzer` | `recipe.ps1:49`, `67`; `pyproject.toml:46` |

`{conf}` is Python's `str()` of the parsed float, for example `0.45`, `0.5` (`traffic_analyzer.py:261`).

### 4.4 PDF layout

| Part | Content | Source |
|---|---|---|
| Header (each page) | Title, bold 15; `Дата генерации: DD.MM.YYYY`, size 8 | `traffic_analyzer.py:166-180` |
| Section "1. Общая сводка по проанализированным данным" | Image count, threshold, vehicle totals, scene counts with Russian labels: Traffic Jam = `Пробка/Затор`, Heavy Traffic = `Плотное движение`, Sparse Traffic = `Свободная дорога`, Single Big Object = `Аномалии (крупный объект)`, Empty = `Пустые сцены` | `traffic_analyzer.py:307-323` |
| Heading "Примеры показательных сцен" | Printed once on the summary page | `traffic_analyzer.py:325-326` |
| Example pages | One per highlight, FR-24 | `traffic_analyzer.py:327-330` |
| Footer (each page) | `Страница {n}`, bold 8 | `traffic_analyzer.py:182-186` |

### 4.5 Console

| Output | When | Source |
|---|---|---|
| `experiment mode` / `report mode` | start | `traffic_analyzer.py:234`, `269` |
| tqdm bar `Анализ [conf=...]` / `Анализ изображений` | image loop | `traffic_analyzer.py:244`, `285` |
| `Критическая ошибка при обработке файла {path}: {e}` | per-image exception | `traffic_analyzer.py:257`, `296` |
| `Результат сохранён в: {pdf path}` | report finished | `traffic_analyzer.py:335` |

### 4.6 Recipe verbs

| Verb | What it does | Source |
|---|---|---|
| `run [args]` | Runs the tool in the locked environment (FR-29) | `recipe.ps1:60-63` |
| `test` | Version check, git hooks path, pytest, mypy, ruff check, ruff format (FR-30) | `recipe.ps1:82-109` |
| `build` | Wheel into `dist` (FR-32) | `recipe.ps1:48-51` |
| `publish` | Wheel into `$env:LAB_SHARE` (FR-33) | `recipe.ps1:64-73` |
| `clean`, `install`, `uninstall`, `info` | FR-34 | `recipe.ps1:52-59`, `74-81` |

## 5. Data

Metrics record (Python `dict`, one per image), built in `traffic_analyzer.py:66-71` and extended in the main block:

| Key | Type | Meaning | Source |
|---|---|---|---|
| `total_vehicles` | int | Number of `car` + `truck` detections | `traffic_analyzer.py:60`, `67` |
| `density` | float, 4 decimals | Summed vehicle box area / image area; can exceed 1 | `traffic_analyzer.py:62`, `68` |
| `avg_bbox_area` | float, 2 decimals | Mean vehicle box area in pixels | `traffic_analyzer.py:64`, `69` |
| `car`, `truck` | int | Count per target class | `traffic_analyzer.py:34`, `70` |
| `scene_type` | str | Report mode only, FR-14 | `traffic_analyzer.py:292` |
| `filename` | str | Base name of the image file | `traffic_analyzer.py:254`, `293` |

Highlight entry (`generate_visualizations` result, `traffic_analyzer.py:121`): `path` (annotated image path), `report` (the metrics record), `stats` (text block of FR-21).

Manual test list: `tests/manual/tests.json` holds `version` 1 and an empty `tests` list (`tests/manual/tests.json:1-4`). `tests/test_manual_list.py:36-49` fixes what an entry must carry: `id`, `title`, `expected`, `steps`, and optionally `issue`, `blocking`, `needs`.

Storage: plain files only (section 4.3); nothing persists between runs except those files, which are overwritten on the next run with the same name.

Committed sample data: 27 images in `data/`; CSV results at `--conf` 0.25, 0.45, 0.5 and 0.7 in `experiments/` (27 rows per file); and in `report_output/` a PDF with 4 pages (creation date 2026-02-24 in its metadata) and the three images `highlight_11.png`, `highlight_22.png`, `highlight_33.png`. `experiments/analysis_conf_0.25.csv` has an extra `scene` column not written by the current code; inference: produced by the earlier experiment branch preserved in `tests/test_generate_visualizations.py:201`. In `experiments/analysis_conf_0.45.csv`, 2 of 27 rows have a density above 1 (`33.png` 1.0277, `img1.jpg` 1.8377).

## 6. Non-functional requirements

- **NFR-1.** Every runtime, development and build dependency is pinned to one version, and `uv.lock` fixes the resolved set (66 `[[package]]` entries, the project included); the recipe runs every tool with `uv run --frozen`. Source: `pyproject.toml:10`, `23-31`, `36-42`; `uv.lock:1-3`; `recipe.ps1:61`, `99-106`.
- **NFR-2.** A failure on one image does not stop the batch (FR-13). Source: `traffic_analyzer.py:245-257`, `286-296`.
- **NFR-3.** CSV output is written in UTF-8 with `newline=""`. Source: `traffic_analyzer.py:263`.
- **NFR-4.** Inference in the main loop runs with `verbose=False`; the highlight re-inference uses the ultralytics default verbosity. Source: `traffic_analyzer.py:249`, `289`, `101`.
- **NFR-5.** Cyrillic text in the PDF depends on the bundled Unicode TrueType fonts. Source: `traffic_analyzer.py:154-161`.
- **NFR-6.** All file paths are relative to the working directory, so the tool must run from the repository root; the recipe changes to that folder before every verb. Source: `traffic_analyzer.py:154-155`, `238`, `240`, `260-261`, `278-281`, `332`; `recipe.ps1:29`, `45`.
- **NFR-7.** No timeouts, retries, size limits, parallelism or device selection are defined in the code. Source: absence in `traffic_analyzer.py`.
- **NFR-8.** The program reads no environment variables, credentials or secrets and opens no network connections of its own. Source: `traffic_analyzer.py:1-10` (imports), whole file. The weights download on first use is stated in `docs/install.md:7`, not verified here. The tooling around it reads `LAB_SHARE` (`recipe.ps1:66`) and `.claude/.env` (`recipe.ps1:34-43`), and `tests/manual/serve.py:5-6` adds a `GITEA_TOKEN` to the calls it forwards; no key is committed (`.gitignore:24`, `CLAUDE.md:20-24`).
- **NFR-9.** The code runs on Python 3.12 only, and the linters target that version. Source: `pyproject.toml:22`, `55`, `84`; `uv.lock:3`.

## 7. Constraints and dependencies

From `pyproject.toml:23-31` (runtime) and `pyproject.toml:36-42` (development group), locked in `uv.lock`:

| Package | Version | Used for |
|---|---|---|
| `torch` | 2.5.1 | Backend of ultralytics (not imported directly) |
| `torchvision` | 0.20.1 | Backend of ultralytics (not imported directly) |
| `ultralytics` | 8.0.196 | `YOLO` model (`traffic_analyzer.py:10`) |
| `opencv-python` | 4.8.1.78 | `cv2` (`traffic_analyzer.py:6`) |
| `tqdm` | 4.66.1 | progress bar (`traffic_analyzer.py:9`) |
| `numpy` | 1.26.0 | not imported by the module; imported by `tests/test_analyze_image_metrics.py:4` |
| `fpdf2` | 2.7.6 | `FPDF`, `XPos`, `YPos` (`traffic_analyzer.py:7-8`) |
| `ruff` | 0.16.1 | lint and format (development) |
| `mypy` | 2.3.0 | type check (development) |
| `pytest`, `pytest-cov`, `coverage` | 8.4.2, 5.0.0, 7.15.2 | tests and coverage (development) |

Build backend: `setuptools==80.9.0` (`pyproject.toml:10`).

Other constraints:

- Model: YOLOv8n with COCO class names (`model.names`), only `car` and `truck` counted (`traffic_analyzer.py:50`, `236`, `277`).
- Git LFS is required: PDF, PNG, JPG, ZIP and 7z files are stored in it (`.gitattributes:8-12`, `docs/install.md:4`). `.jpeg` is not in the list, so `data/img2.jpeg` is a normal blob (`git lfs ls-files`).
- Line endings: LF everywhere except `.ps1`, `.bat` and `.cmd`, which are CRLF (`.gitattributes:1-4`).
- Licence: MIT (`LICENSE:1`, `pyproject.toml:19`). The licence of the images in `data/` and of the bundled DejaVu fonts is not stated.
- Process: branch names `<code>-<issue>/<type>/<slug>` from `test`, commits `<type>(<scope>): <what changed>` with sign-off (`CONTRIBUTING.md:4-8`); the project code is `ta` (`recipe.ps1:12`) and the allowed types and scopes are listed in `recipe.ps1:21-23`. `README.md:30` states compliance with revision 4.0.0 of the lab requirements except R-02, R-09, R-12, R-37, R-41 and R-42; the R-12 exception is the coverage floor of 0 (`pyproject.toml:74`).

## 8. Acceptance

Test command: `.\recipe.ps1 test` (`README.md:16`, FR-30). The four tool-test files that have a test function also call it at module level, so collecting them runs the test once more (for example `tests/test_get_valid_image_paths.py:50`).

| Test | Covers | Caveat |
|---|---|---|
| `tests/test_get_valid_image_paths.py::test_get_valid_image_paths` | FR-4 | Tests a copy; relative path `tests/test_sandbox` (`tests/test_get_valid_image_paths.py:26`) |
| `tests/test_analyze_image_metrics.py::test_analyze_image_metrics` | FR-8, FR-9, FR-10 | Copy lacks FR-11 guards; module loads YOLO and runs on `data/` at import (`tests/test_analyze_image_metrics.py:71-85`) |
| `tests/test_classify_scene.py::test_classify_scene` | FR-14 | Tests a copy; module loads YOLO at import (`tests/test_classify_scene.py:96-116`) |
| `tests/test_find_highlight_examples.py::test_find_highlight_examples` | FR-19 | Tests a copy |
| `tests/test_manual_list.py::test_the_list_has_a_known_shape`, `::test_every_entry_is_complete` | the manual test list (section 5) | Run for this document with the system Python 3.13 and pytest 9.1.1, outside the pinned environment and without the coverage options: 2 passed |

`tests/test_generate_visualizations.py` holds no test function; `generate_visualizations` (FR-20, FR-21) is not tested.

Manual checks (not run for this document):

1. `.\recipe.ps1 run experiment --conf 0.45` (`README.md:12`) produces `experiments/analysis_conf_0.45.csv` with 27 data rows and the header of section 4.3; compare with the committed file.
2. `.\recipe.ps1 run report --conf 0.45` (`README.md:13`) produces `report_output/traffic_analysis_report.pdf` with 4 pages and three `highlight_*` images. In the committed CSV at 0.45 the top three by vehicle count are `22.png` (24), `33.png` (19), `11.png` (9), which matches the committed `report_output/highlight_*` files.
3. `.\recipe.ps1 run report --conf 2` is accepted by argparse (section 3.8); `.\recipe.ps1 run other` is rejected (FR-1).
4. Run with `ttf/` renamed to observe FR-26 and the font row of section 3.8.
5. Run with an empty `data/` to observe FR-6.
6. `.\recipe.ps1 test` in a fresh clone exits 0 (FR-30); it needs network access on the first run, because two test files load the weights (`docs/install.md:7`).

## 9. Open questions

- Who the users are and what the results are used for (coursework, research, operations) is not stated anywhere.
- Target OS: only Windows runners appear in the workflows (`.gitea/workflows/test.yaml:16`); whether macOS or Linux, for which `uv.lock:4-10` also resolves, are meant to work is not stated.
- How the threshold values 10, 0.3, 5, 0.15 were chosen, and whether they were validated against labelled images.
- Partly answered: `README.md:3`, `docs/manual.md:15` and the comment at `traffic_analyzer.py:61` describe `density` as the share of the frame the vehicles cover, and the open task in section 3.8 proposes computing it from the union of the boxes. Open: whether the committed CSV and PDF results are to be regenerated afterwards.
- Whether highlights should be the union of top-by-count and top-by-density, as the docstring and test comments suggest (`traffic_analyzer.py:80`, `tests/test_find_highlight_examples.py:115-128`), or the current single sort. The test's assertion (`tests/test_find_highlight_examples.py:133`, `138`) expects the four highest by count, which is the current single sort, not the union (it leaves out `dense.jpg`, the density leader).
- Whether the Arial fallback was ever expected to work with the Russian PDF text.
- Partly answered: `README.md:22` states that the tests do not exercise `traffic_analyzer.py`, and the open task in section 3.8 proposes that they import it. Open: when the coverage floor is to be raised, and to what value.
- Origin and licence of the images in `data/`; purpose of the non-image files `data/txtfile` and `data/webmfile.webm` (inference: negative cases for the extension filter).
- Target hardware (CPU or GPU) and expected processing time per image.
- Partly answered: `recipe.ps1 publish` copies the wheel under `$env:LAB_SHARE` (FR-33), and `.gitea/workflows/release.yaml:1-4` runs on every push to `release`. Open: who installs the wheel and how it is run there. Installed, it reads `data/` from the folder it is started in (`docs/install.md:9`), and `ttf/` the same way (`traffic_analyzer.py:154-155`), while the wheel carries only the module (`pyproject.toml:46`).
- Partly answered: `CONTRIBUTING.md:4` names `test` as the branch to start from, and `release` is the remote default branch (`origin/HEAD`) carrying tag `v1.0.0`. Open: whether `dev` is still maintained.
