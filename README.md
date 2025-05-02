# VasoAnalyzer 2.1.1

🧪 *Bladder Vasculature Analysis Toolkit — Python Edition*  
Built by **Osvaldo J. Vega Rodríguez** | Tykocki Lab | Michigan State University

[![Download macOS App](https://img.shields.io/badge/Download-macOS-blue?logo=apple&style=for-the-badge)](https://github.com/vr-oj/VasoAnalyzer/releases/download/v2.1.1/VasoAnalyzer_v2.1.1_macOS.zip)
[![Download Windows App](https://img.shields.io/badge/Download-Windows-blue?logo=windows&style=for-the-badge)](https://github.com/vr-oj/VasoAnalyzer_2.0/releases/download/v2.1.1/VasoAnalyzer_2.1.1.for.Windows.zip)

---

## 🌟 What is VasoAnalyzer?

**VasoAnalyzer** is a standalone desktop app built to make pressure myography data analysis clean, fast, and intuitive. It visualizes diameter traces, and auto-extracts event-based inner diameter data.

Designed for researchers. Powered by Python. Zero coding required.

---

## 🧰 Key Features in v2.1.1

- **📊 Load and visualize trace data** from `.csv` files
- **📍 Import and display events** from `.csv` or `.txt` files
- **🖼️ View synchronized TIFF snapshots** with red trace markers
- **🧠 Interactive plotting**: zoom, pan, hover, and pin points
- **📏 Auto-populated event table** with editable inner diameter values
- **🎨 Plot Style Editor** (new!)
  - Customize fonts, colors, and line widths
  - Edit axis titles and tick labels separately
  - Adjust event and pin label styles in real time
  - Tabbed layout with per-section Apply + Reset buttons
- **🔄 One-click export**:
  - `eventDiameters_output.csv` (for analysis)
  - `tracePlot_output.fig.pickle` (editable in Python)
  - `tracePlot_output_pubready.tiff` or `.svg` (high-res export)
- **📌 Undo Support + Pinning**:
  - Visually pin measurement points
  - Replace event values via right-click menu
  - Undo accidental changes anytime
- **⚡ Optimizations and UI polish**
  - New app icon and splash branding
  - Updated toolbar with hover tooltips
  - Faster TIFF loading and error handling

---

## 🚀 Download & Install

### ✅ Option 1: No Python Needed — Use the App!

- [⬇️ Download for macOS (.app)](https://github.com/vr-oj/VasoAnalyzer_2.0/releases/download/v2.1.1/VasoAnalyzer_2.1.1.for.macOS.zip)
- [⬇️ Download for Windows (.exe)](https://github.com/vr-oj/VasoAnalyzer_2.0/releases/download/v2.1.1/VasoAnalyzer_2.1.1.for.Windows.zip)

After downloading:
- **macOS**: Unzip → Right-click → Open (to bypass Gatekeeper)
- **Windows**: Unzip → Double-click `.exe`

**macOS** users  
If you see a warning like:  
**“VasoAnalyzer is damaged and can’t be opened...”**  
this is caused by macOS Gatekeeper blocking unsigned apps by default.

Don't worry — your download is safe and complete. Here's how to fix it:

#### Quick Fix (One-Time Step)

```bash
xattr -rd com.apple.quarantine ~/Downloads/VasoAnalyzer_2.1.1.app
```

> You only need to do this once — unless the app is re-downloaded or moved to another computer.

---

### 🧪 Option 2: Run From Source (Python 3.10+)

```bash
git clone https://github.com/vr-oj/VasoAnalyzer_2.0.git
cd VasoAnalyzer_2.0/src
pip install -r requirements.txt
python main.py
```

---

## 👟 How to Use

1. **Load Trace File** (.csv from VasoTracker)
2. **Load Event File** (.csv or .txt with time labels)
3. *(Optional)* Load TIFF file (`_Result.tif`) to view snapshots
4. **Zoom** into regions and drag timeline using slider
5. **Pin points** on trace to annotate or edit events
6. **Export** results with one click:
   - `eventDiameters_output.csv`
   - `tracePlot_output.fig.pickle`
   - `tracePlot_output_pubready.tiff`

---

## 🛠️ Folder Structure

```
VasoAnalyzer_2.0/
├── src/
│   ├── main.py                 # App launcher
│   └── vasoanalyzer/           # App modules and logic
│       ├── gui.py              # UI logic (PyQt5)
│       ├── trace_loader.py     # Load trace CSV
│       ├── event_loader.py     # Load event files
│       ├── tiff_loader.py      # Load TIFFs
│       └── VasoAnalyzerIcon.icns
└── requirements.txt
```

---

## 🧪 Requirements for Developers

- Python 3.10+
- PyQt5, matplotlib, pandas, tifffile
- Compatible with macOS and Windows

---

## 🛡️ License

Non-commercial academic use only.  
To collaborate, adapt, or extend, please contact the **Tykocki Lab**.

---

## 👨‍🔬 Credits

Crafted by **Osvaldo J. Vega Rodríguez**  
Developed at the **Tykocki Lab**, Michigan State University

---

### Legacy Version

Want the original 2.0 version?  
Head to [Releases](https://github.com/vr-oj/VasoAnalyzer_2.0/releases/tag/v2.0.0) for prior downloads.
