# traffic-analyzer

A console tool that analyses road traffic in still images with the YOLOv8 object detector. It counts cars and trucks in each image, measures how much of the frame they cover, and sorts the scene into one of five types: Traffic Jam, Heavy Traffic, Sparse Traffic, Single Big Object or Empty.

It reads the images in `data/` and has two modes. `experiment` writes the metrics of every image to a CSV file in `experiments/`. `report` also picks the most telling images, draws the detections on them and builds a PDF in `report_output/`.

The program's own messages and the PDF are in Russian. The PDF uses the DejaVu fonts in `ttf/`.

## Use

```powershell
.\recipe.ps1 run experiment --conf 0.45
.\recipe.ps1 run report --conf 0.45
```

`docs/install.md` says what to install and `docs/manual.md` describes both modes. `.\recipe.ps1 test` runs the tests, mypy and ruff.

## What is here

- `traffic_analyzer.py` is the whole program.
- `data/` holds the source images, `experiments/` and `report_output/` the results of earlier runs.
- `tests/` holds the tests. Each one carries its own copy of the functions it checks, so they do not exercise `traffic_analyzer.py` itself.

## Licence

MIT, see `LICENSE`.

## Lab requirements

This repository complies with [revision 4.0.0](http://127.0.0.1:3000/igors-lab/software-requirements/src/tag/v4.0.0/BEST_REQUIREMENTS.md) of the lab requirements, except R-02 (#8), R-09 (#9), R-12 (#10), R-37 (#11), R-41 (#12), R-42 (#13).
