
# VasoAnalyzer 2.0

[![Download macOS App](https://img.shields.io/badge/Download-macOS-blue?logo=apple&style=for-the-badge)](https://github.com/vr-oj/VasoAnalyzer_2.0/releases/download/v2.0.0/VasoAnalyzer_macOS.zip)
[![Download Windows App](https://img.shields.io/badge/Download-Windows-blue?logo=windows&style=for-the-badge)](https://github.com/vr-oj/VasoAnalyzer_2.0/releases/download/v2.0.0/VasoAnalyzer_Windows.zip)

✨ *Bladder Vasculature Analysis Toolkit (Python Edition)* ✨  
Developed by **Osvaldo J. Vega Rodríguez** at the **Tykocki Lab**, Michigan State University

---

## 🌟 Overview

**VasoAnalyzer 2.0** is a lightweight Python desktop application for visualizing, annotating, and analyzing vascular pressure myography trace data. It automates event-based diameter extraction, and simplifies data export.

---

## ⚙️ Key Features

- **Load and visualize** pressure myography traces (`.csv` format)
- **Display event markers** from `.csv` or `.txt` files
- **View synchronized snapshots** from experiment TIFF files
- **Interactive trace plot** with zoom, pan, and auto-positioned event labels
- **One-click export**:
  - Event-based diameter tables (`eventDiameters_output.csv`)
  - Editable trace plots (`tracePlot_output.fig.pickle`)
- **Modern, responsive UI** (PyQt5 + Matplotlib)

---

## 🚀 Installation

### Option 1: Standalone Apps (No Python Required)

- [⬇️ Download VasoAnalyzer v2.0.0 for macOS](https://github.com/vr-oj/VasoAnalyzer_2.0/releases/download/v2.0.0/VasoAnalyzer_macOS.zip)
- [⬇️ Download VasoAnalyzer v2.0.0 for Windows](https://github.com/vr-oj/VasoAnalyzer_2.0/releases/download/v2.0.0/VasoAnalyzer_Windows.zip)

After downloading:
- **macOS**:
  - Unzip the file.
  - Open `VasoAnalyzer.app`.
  - If a security warning appears, right-click the app and select **Open** to bypass Gatekeeper.
- **Windows**:
  - Unzip the file.
  - Open `VasoAnalyzer.exe`.

> macOS version works on **Intel** and **Apple Silicon** Macs!

---

### Option 2: Run from Source (Python 3.10+ Required)

```bash
# Clone the repository
git clone https://github.com/vr-oj/VasoAnalyzer_2.0.git

# Navigate into the folder
cd VasoAnalyzer_2.0

# (Optional) Create a virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Launch the app
python main.py
```

---

## 🎯 Usage Guide

After launching:

1. **Load Trace File**: Import your `.csv` file containing diameter traces.
2. **Load Event File**: Select your `.csv` or `.txt` file with event timings and labels.
3. **Load Snapshot File** *(optional)*: Choose a multi-frame `.tiff` image sequence.
4. **Explore**:
   - Inspect vessel behavior via an interactive trace plot.
   - Scroll through synchronized snapshots with the slider.
   - Click table events to jump directly to key trace locations.
5. **Export Results**:
   - Save the event-based diameter table (`eventDiameters_output.csv`).
   - Save an editable trace figure (`tracePlot_output.fig.pickle`).

---

## 🗂️ File Structure

```
VasoAnalyzer_2.0/
│
├── main.py                 # Main launcher
├── vasoanalyzer/            # App logic and modules
│   ├── vasotracker_ui.py
│   ├── plot_handler.py
│   ├── trace_loader.py
│   ├── event_loader.py
│   ├── snapshot_loader.py
│   └── utils.py
├── requirements.txt         # Python package list
└── README.md                # (this file)
```

---

## 🛡️ License

This project is licensed for **non-commercial academic research use**.  
For other uses, please contact the **Tykocki Lab**.

---

## 👨‍🔬 Acknowledgements

Developed with passion by **Osvaldo J. Vega Rodríguez** at the **Tykocki Lab**, Michigan State University.

---
