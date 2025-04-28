# VasoAnalyzer 2.0

**Bladder Vasculature Analysis Toolkit (Python Edition)**  
Developed by Osvaldo Vega Rodríguez in the Tykocki Lab.

---

## Overview

VasoAnalyzer 2.0 is a lightweight Python desktop application for visualizing, annotating, and analyzing vascular pressure myography trace data.  
It provides synchronized display of vessel diameter traces alongside snapshot frames, automatic event-based diameter extraction, and seamless export of results.

Originally built to support research in the Tykocki Lab, this version modernizes the previous MATLAB-based pipeline into a clean, standalone Python workflow.

---

## Key Features

- **Load and visualize** pressure myography traces (`.csv` format)
- **Load event annotation** files (`.csv` or `.txt`) and display event markers
- **Load snapshot files** (`_Result.tiff`) associated with the experiment
- **Interactive trace plot** with zoom, pan, axis scaling, and event label auto-positioning
- **Linked snapshot viewer** controlled by a synchronized slider
- **Auto-export**:
  - Event diameter tables (`eventDiameters_output.csv`)
  - Editable trace plots (`tracePlot_output.fig.pickle`)
- **Modern, responsive UI** built with PyQt5 and Matplotlib
- **Light theme** with framed panels for a clean, publication-ready look
- **Fast loading** even with large TIFF stacks and long traces

---

## Installation

### Requirements

- Python 3.10+
- PyQt5
- Matplotlib
- Pandas
- Tifffile
- OpenCV-python (optional, for enhanced TIFF compatibility)

### Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/vr-oj/VasoAnalyzer_2.0.git
cd VasoAnalyzer_2.0
pip install -r requirements.txt
```

---

## Usage

Launch the application:

```bash
python main.py
```

Upon opening:

1. **Load Trace File**: Select your `.csv` trace file containing diameter measurements.
2. **Load Event File**: Select your `.csv` or `.txt` file with event labels and timings.
3. **Load Snapshot File** (optional): Select a multi-frame `.tiff` file containing experiment snapshots.
4. **Explore the Data**:
   - Use the interactive trace plot to inspect vessel behavior over time.
   - Scroll through snapshots using the slider, synchronized to the trace timeline.
   - Click on events in the table to jump directly to their corresponding location on the trace.
5. **Export Results**:
   - Save an event-based diameter table (`eventDiameters_output.csv`) ready for statistical analysis.
   - Save the interactive trace figure as a `.fig.pickle` for future editing.

---

## File Structure

```
VasoAnalyzer_2.0/
│
├── main.py                 # Main launcher for the app
├── vasotracker_ui.py       # App logic and UI layout
├── trace_loader.py         # Trace data loader
├── event_loader.py         # Event file handler
├── snapshot_loader.py      # TIFF snapshot handler
├── plot_handler.py         # Interactive plotting functions
├── utils.py                # Helper functions
├── requirements.txt        # Python dependencies
└── README.md               # You are here!
```

---

## License

This project is licensed for **non-commercial academic research use**.  
For other uses, please contact the Tykocki Lab.

---
