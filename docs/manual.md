# Manual

```powershell
.\recipe.ps1 run <mode> [--conf <threshold>]
```

Put `.jpg`, `.jpeg` or `.png` images in `data/` first. Other files there are skipped, and so is an image that cannot be read.

| argument | what it does |
| --- | --- |
| `experiment` | run the detector on every image and write the metrics to `experiments/analysis_conf_<threshold>.csv` |
| `report` | run the detector, classify each scene, draw the most telling images into `report_output/` and write `report_output/traffic_analysis_report.pdf` |
| `--conf <threshold>` | the detector's confidence threshold, a number from 0 to 1; 0.45 by default |

The CSV has one row per image: `total_vehicles`, `density` (the share of the frame the vehicles cover), `avg_bbox_area`, one count per class, and `filename`.

`report` classifies each scene with thresholds fixed in the program, in this order:

| scene | when |
| --- | --- |
| Empty | no vehicles |
| Traffic Jam | at least 10 vehicles and a density of at least 0.3 |
| Single Big Object | at most 2 vehicles and a density above 0.15 |
| Heavy Traffic | at least 5 vehicles |
| Sparse Traffic | anything else |
