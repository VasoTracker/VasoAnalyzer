# ===== GUI Layout and Core App =====
import sys
import os
import numpy as np
import pandas as pd
import tifffile
import matplotlib.pyplot as plt
import pickle

from PyQt5.QtWidgets import (QMainWindow, QWidget, QPushButton, QFileDialog,
                             QVBoxLayout, QHBoxLayout, QSlider, QLabel,
                             QTableWidget, QTableWidgetItem, QAbstractItemView,
                             QHeaderView)
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt, QTimer

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from vasoanalyzer.trace_loader import load_trace
from vasoanalyzer.tiff_loader import load_tiff
from vasoanalyzer.event_loader import load_events

class VasoAnalyzerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        icon_path = os.path.join(os.path.dirname(__file__), 'vasoanalyzer_icon.png')
        self.setWindowIcon(QIcon(icon_path))

        # ===== Setup App Window =====
        self.setWindowTitle("VasoAnalyzer 2.0 - Python Edition")
        self.setGeometry(100, 100, 1280, 720)

        # ===== Initialize State =====
        self.trace_data = None
        self.trace_file_path = None
        self.snapshot_frames = []
        self.current_frame = 0
        self.event_labels = []
        self.event_times = []
        self.event_text_objects = []
        self.event_table_data = []
        self.selected_event_marker = None
        self.slider_marker = None
        self.recording_interval = 0.14  # 140 ms per frame (Vasotracker acquisition)

        # ===== Build UI =====
        self.initUI()

    def initUI(self):
        # ===== Apply Styles =====
        self.setStyleSheet("""
            QWidget { background-color: #F5F5F5; font-family: 'Arial'; font-size: 13px; }
            QPushButton { background-color: #FFFFFF; border: 1px solid #CCCCCC; border-radius: 8px; padding: 6px 12px; }
            QPushButton:hover { background-color: #E6F0FF; }
            QToolButton { background-color: #FFFFFF; border: 1px solid #CCCCCC; border-radius: 6px; padding: 6px; }
            QToolButton:hover { background-color: #D6E9FF; }
            QHeaderView::section { background-color: #E0E0E0; font-weight: bold; padding: 6px; }
            QTableWidget { gridline-color: #DDDDDD; }
            QTableWidget::item { padding: 6px; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        right_layout = QVBoxLayout()
        bottom_layout = QHBoxLayout()

        # ===== Buttons =====
        self.load_trace_button = QPushButton("Load Trace")
        self.load_trace_button.clicked.connect(self.load_trace)

        self.load_events_button = QPushButton("Load Events")
        self.load_events_button.clicked.connect(self.load_events)

        self.load_snapshot_button = QPushButton("Load _Result.tiff")
        self.load_snapshot_button.clicked.connect(self.load_snapshot)

        # ===== Plot (Matplotlib) =====
        self.fig = Figure(figsize=(8, 4), facecolor='white')
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background-color: #F5F5F5; border: none;")

        # ===== Snapshot Viewer =====
        self.snapshot_label = QLabel("Snapshot will appear here")
        self.snapshot_label.setAlignment(Qt.AlignCenter)
        self.snapshot_label.setFixedSize(400, 300)
        self.snapshot_label.setStyleSheet("background-color: white; border: 1px solid #999;")
        self.snapshot_label.hide()

        # ===== Slider =====
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self.change_frame)
        self.slider.hide()

        # ===== Event Table =====
        self.event_table = QTableWidget()
        self.event_table.setColumnCount(3)
        self.event_table.setHorizontalHeaderLabels(["Event", "Time (s)", "ID (µm)"])
        self.event_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.event_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.event_table.setStyleSheet("background-color: white; color: black;")
        self.event_table.horizontalHeader().setStretchLastSection(True)
        self.event_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.event_table.cellClicked.connect(self.table_row_clicked)

        # ===== Layout Assembly =====
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.toolbar)
        left_layout.addWidget(self.canvas)

        right_layout.addWidget(self.snapshot_label)
        right_layout.addWidget(self.event_table)

        top_layout.addLayout(left_layout, 4)
        top_layout.addLayout(right_layout, 1)

        bottom_layout.addWidget(self.load_trace_button)
        bottom_layout.addWidget(self.load_events_button)
        bottom_layout.addWidget(self.load_snapshot_button)
        bottom_layout.addWidget(self.slider)

        main_layout.addLayout(top_layout)
        main_layout.addLayout(bottom_layout)

        main_layout.setContentsMargins(10, 10, 10, 10)
        top_layout.setSpacing(10)
        bottom_layout.setContentsMargins(0, 5, 0, 0)

        central_widget.setLayout(main_layout)

        self.canvas.mpl_connect("draw_event", self.update_event_label_positions)
        self.canvas.mpl_connect("button_release_event", self.update_event_label_positions)
        self.canvas.mpl_connect("motion_notify_event", self.update_event_label_positions)

    # ===== All Other Functions =====
    # (Your load_trace, load_events, update_plot, etc. remain unchanged.)


    # ===== Trace File Loading =====
    def load_trace(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Trace File", "", "CSV Files (*.csv)")
        if file_path:
            self.trace_data = load_trace(file_path)
            self.trace_file_path = os.path.dirname(file_path)
            self.update_plot()

    # ===== Event File Loading =====
    def load_events(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Events File", "", "CSV Files (*.csv *.txt)")
        if file_path:
            self.event_labels, self.event_times = load_events(file_path)
            self.update_plot()

    # ===== Update Trace Plot =====
    def update_plot(self):
        self.ax.clear()
        self.ax.set_facecolor("white")
        self.ax.tick_params(colors='black')
        self.ax.xaxis.label.set_color('black')
        self.ax.yaxis.label.set_color('black')
        self.ax.title.set_color('black')
        self.event_text_objects = []

        if self.trace_data is not None:
            t = self.trace_data['Time (s)']
            d = self.trace_data['Inner Diameter']
            self.ax.plot(t, d, 'k-', linewidth=1.5)
            self.ax.set_xlabel("Time (s)")
            self.ax.set_ylabel("Inner Diameter (µm)")
            self.ax.set_title("Trace Plot")
            self.ax.grid(True, color='#CCC')

        if self.event_times and self.event_labels:
            self.event_table_data = []
            offset_sec = 2
            nEv = len(self.event_times)
            diam_trace = self.trace_data['Inner Diameter']
            time_trace = self.trace_data['Time (s)']
            for i in range(nEv):
                idx_ev = np.argmin(np.abs(time_trace - self.event_times[i]))
                diam_at_ev = diam_trace.iloc[idx_ev]

                if i < nEv - 1:
                    t_sample = self.event_times[i+1] - offset_sec
                    idx_pre = np.argmin(np.abs(time_trace - t_sample))
                else:
                    idx_pre = -1
                diam_pre = diam_trace.iloc[idx_pre]

                self.ax.axvline(x=self.event_times[i], color='black', linestyle='--', linewidth=0.8)
                txt = self.ax.text(self.event_times[i], 0, self.event_labels[i], rotation=90,
                                   verticalalignment='top', horizontalalignment='right',
                                   fontsize=8, color='black')
                self.event_text_objects.append((txt, self.event_times[i]))
                self.event_table_data.append((self.event_labels[i], round(self.event_times[i],2), round(diam_pre,2)))

            self.populate_table()
            self.auto_export_table()
            self.auto_export_editable_plot()

        self.canvas.draw()
        QTimer.singleShot(50, self.update_event_label_positions)

    # ===== Populate Event Table =====
    def populate_table(self):
        self.event_table.setRowCount(len(self.event_table_data))
        for row, (label, t, d) in enumerate(self.event_table_data):
            self.event_table.setItem(row, 0, QTableWidgetItem(str(label)))
            self.event_table.setItem(row, 1, QTableWidgetItem(str(t)))
            self.event_table.setItem(row, 2, QTableWidgetItem(str(d)))

    # ===== Table Row Click Event =====
    def table_row_clicked(self, row, col):
        if not self.event_table_data:
            return
        t = self.event_table_data[row][1]
        if self.selected_event_marker:
            self.selected_event_marker.remove()
        self.selected_event_marker = self.ax.axvline(x=t, color='blue', linestyle='--', linewidth=1.2)
        self.canvas.draw()

    # ===== Update Event Label Positions on Zoom =====
    def update_event_label_positions(self, event=None):
        if not self.event_text_objects:
            return
        y_top = self.ax.get_ylim()[1] * 0.95
        for txt, x in self.event_text_objects:
            txt.set_position((x, y_top))

    # ===== Load TIFF Snapshot (Result.tiff) =====
    def load_snapshot(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Result TIFF", "", "TIFF Files (*.tif *.tiff)")
        if file_path:
            self.snapshot_frames = load_tiff(file_path)
            if self.snapshot_frames:
                self.display_frame(0)
                self.slider.setMaximum(len(self.snapshot_frames) - 1)
                self.slider.setValue(0)
                self.snapshot_label.show()  # Show snapshot viewer
                self.slider.show()           # Show slider
                self.slider_marker = None    # <--- Reset red marker so it's clean for new TIFF

    # ===== Display Frame (Supports Grayscale and RGB) =====
    def display_frame(self, index):
        if self.snapshot_frames:
            frame = self.snapshot_frames[index]

            if frame.ndim == 2:
                height, width = frame.shape
                q_img = QImage(frame.data, width, height, QImage.Format_Grayscale8)
            elif frame.ndim == 3:
                height, width, channels = frame.shape
                if channels == 3:
                    q_img = QImage(frame.data, width, height, 3 * width, QImage.Format_RGB888)
                else:
                    raise ValueError(f"Unsupported TIFF frame format: {frame.shape}")
            else:
                raise ValueError(f"Unknown TIFF frame dimensions: {frame.shape}")

            self.snapshot_label.setPixmap(QPixmap.fromImage(q_img).scaled(
                self.snapshot_label.width(), self.snapshot_label.height(), Qt.KeepAspectRatio))

    # ===== Slider Change Frame =====
    def change_frame(self):
        idx = self.slider.value()
        self.current_frame = idx
        self.display_frame(idx)
        self.update_slider_marker()

    # ===== Update Red Slider Marker on Trace =====
    def update_slider_marker(self):
        if self.trace_data is None or not self.snapshot_frames:
            return

        frame_idx = self.slider.value()
        t_current = frame_idx * self.recording_interval

        print(f"Slider moved to frame {frame_idx}, time {t_current:.2f} sec")

        if self.slider_marker is None:
            # Create red line once
            self.slider_marker = self.ax.axvline(x=t_current, color='red', linestyle='--', linewidth=1.5, label="TIFF Frame")
        else:
            # Move the existing red line to new position
            self.slider_marker.set_xdata([t_current, t_current])

        self.canvas.draw_idle()
        self.canvas.flush_events()

    # ===== Auto-Export Event Table as CSV =====
    def auto_export_table(self):
        if not self.trace_file_path:
            return
        csv_path = os.path.join(self.trace_file_path, "eventDiameters_output.csv")
        df = pd.DataFrame(self.event_table_data, columns=["Event", "Time (s)", "ID (µm)"])
        df.to_csv(csv_path, index=False)
        print(f"✔ Event table saved to:\n{csv_path}")

    # ===== Auto-Export Editable Trace Plot =====
    def auto_export_editable_plot(self):
        if not self.trace_file_path:
            return
        pickle_path = os.path.join(self.trace_file_path, "tracePlot_output.fig.pickle")
        with open(pickle_path, 'wb') as f:
            pickle.dump(self.fig, f)
        print(f"✔ Editable trace figure saved to:\n{pickle_path}")


