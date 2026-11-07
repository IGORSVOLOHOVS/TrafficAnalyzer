# Install

1. Install [uv](https://docs.astral.sh/uv/) and Python 3.12. Python 3.13 will not do: the pinned `torch` and `numpy` have no Windows wheels for it.
2. Install [Git LFS](https://git-lfs.com/): the images and PDFs are stored in it.
3. Clone this repository and run `uv sync --frozen` at its root.

The first run downloads the YOLOv8 weights, `yolov8n.pt`, into the working folder, so it needs a network connection. The file is ignored by git. Two of the test files load the same weights when they are collected, so `.\recipe.ps1 test` needs the connection too.

`.\recipe.ps1 build` packs the module into a wheel in `dist\`. Installed that way it runs as `python -m traffic_analyzer`, and it reads `data/` from the folder it is started in.
