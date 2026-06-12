# CLAP Spatial Sonification — Desktop App

Cross-platform desktop application that runs **MS-CLAP** and **LAION-CLAP**
audio-text embedding comparisons and visualises the cosine similarity results
as an interactive spatial sonification.

Built with **pywebview** — a thin native window wrapping the app HTML/JS,
with a Python API bridge for filesystem access and model inference.

---

## Requirements

- Python 3.10+
- macOS 11+, Windows 10+, or Linux with GTK3/WebKit2

---

## Install & run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the app
python main.py
```

On first run, CLAP model checkpoints are downloaded automatically (~1–3 GB each).

---

## Usage

### Configure tab (sidebar)

| Control | Description |
|---------|-------------|
| **Audio directory** | Browse to a folder containing `.wav`, `.mp3`, `.flac`, etc. The app scans recursively and lists all found files. |
| **Text tags** | Comma-separated descriptions to compare against each audio file, e.g. `dog barking, rain, speech, music`. |
| **File extensions** | Which extensions to include in the scan (editable). |
| **Models** | Toggle MS-CLAP and/or LAION-CLAP. Running both enables the diff view. |
| **Save results to** | Optional output path for the JSON export. Leave blank to only view in-app. |
| **Run analysis** | Starts inference in a background thread. Progress bars update live. |
| **Open JSON** | Load a previously saved `clap_results.json` directly. |

### Visualise tab

- **Dual spatial fields** — MS-CLAP and LAION-CLAP side by side
- **Filter chips** — toggle any tag or file to update all views
- **Sonification controls** — tune base frequency, duration, interval, waveform, play mode
- **Play modes**:
  - `sequential` — MS-CLAP pairs first, then LAION
  - `simultaneous` — both models 80 ms apart so you hear the delta
  - `diff-only` — most-disagreed pairs first

### Matrix tab

Heatmap of every `file × tag` combination. Click any cell to sonify that single pair immediately. Switch between MS-CLAP and LAION-CLAP views.

### Model diff tab

Every shared `(file, tag)` pair ranked by `|MS-CLAP − LAION-CLAP|`. Bars turn amber above 0.1, red above 0.2. Each row has a ▶ button to sonify both models simultaneously.

---

## Spatial mapping

| Parameter | Formula | Sonic meaning |
|-----------|---------|---------------|
| Stereo pan | `sim` | `+1` = hard right (high similarity), `−1` = hard left |
| Y position | `1 − |sim|` | Near centre ring = high similarity, outer = dissimilar |
| Frequency | `base × (0.5 + sim×1.5)` | Brighter/higher pitch for more similar pairs |
| Amplitude | `0.3 + max(0,sim)×0.5` | Louder when semantically close |

Two tones per pair: sine (audio embedding) and a quieter triangle wave 120 ms later (text tag).

---

## Project structure

```
clap-desktop/
├── main.py          ← Python entry point + CLAPBridge API
├── requirements.txt
├── README.md
└── src/
    └── index.html   ← All HTML/CSS/JS (single-file frontend)
```

---

## Packaging to a standalone executable

### macOS / Windows / Linux — PyInstaller

```bash
pip install pyinstaller
pyinstaller --onedir --windowed \
    --add-data "src:src" \
    --name "CLAP Sonification" \
    main.py
```

### macOS — py2app

```bash
pip install py2app
py2app -A main.py
```

The resulting `dist/` folder is a self-contained app — no Python installation needed on the target machine (though model checkpoints still need to be downloaded on first run or bundled manually).

---

## Troubleshooting

**"No module named 'msclap'"** — `pip install msclap`

**"No module named 'laion_clap'"** — `pip install laion-clap`

**Blank window on Linux** — install WebKit2 GTK: `sudo apt install python3-gi gir1.2-webkit2-4.0`

**Model download fails** — check internet connection; checkpoints are fetched from Hugging Face Hub on first use.
