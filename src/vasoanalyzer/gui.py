# ===== GUI Layout and Core App =====
import sys
import os
import numpy as np
import pandas as pd
import tifffile
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import rcParams

# ===== Matplotlib Dialog Style Patch =====
rcParams.update({
	'axes.labelcolor': 'black',
	'xtick.color': 'black',
	'ytick.color': 'black',
	'text.color': 'black',
	'figure.facecolor': 'white',
	'figure.edgecolor': 'white',
	'savefig.facecolor': 'white',
	'savefig.edgecolor': 'white',
})
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

		self.setStyleSheet("""
			QPushButton {
				color: black;
			}
		""")

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
		self.pinned_points = []
		self.slider_marker = None
		self.recording_interval = 0.14	# 140 ms per frame (Vasotracker acquisition)

		# ===== Axis + Slider State =====
		self.axis_dragging = False
		self.axis_drag_start = None
		self.drag_direction = None
		self.scroll_slider = None
		self.window_width = None

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
		
		from PyQt5.QtWidgets import QLabel, QSizePolicy

		self.trace_file_label = QLabel("No trace loaded")
		self.trace_file_label.setStyleSheet("color: gray; font-size: 12px; padding-left: 10px;")
		self.trace_file_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
		
		self.toolbar.addSeparator()
		self.toolbar.addWidget(self.trace_file_label)

		self.toolbar.setStyleSheet("""
			QToolButton {
				background-color: #FFFFFF;
				border: 1px solid #CCCCCC;
				border-radius: 4px;
				padding: 4px;
			}
			QToolButton:checked {
				background-color: #CCE5FF;
				border: 1px solid #007BFF;
			}
		""")

		# ===== Improve Toolbar Tooltips (robust version) =====
		visible_buttons = [a for a in self.toolbar.actions() if not a.icon().isNull()]
		
		if len(visible_buttons) >= 8:
			visible_buttons[0].setToolTip("Home: Reset zoom and pan")
			visible_buttons[1].setToolTip("Back: Previous view")
			visible_buttons[2].setToolTip("Forward: Next view")
			visible_buttons[3].setToolTip("Pan: Click and drag plot")
			visible_buttons[4].setToolTip("Zoom: Draw box to zoom in")
			visible_buttons[5].setToolTip("Layout: Adjust subplot spacing")
			visible_buttons[6].setToolTip("Style: Edit axes, labels, curves")
			visible_buttons[7].setToolTip("Save: Export plot to image file")

		# ===== Snapshot Viewer =====
		self.snapshot_label = QLabel("Snapshot will appear here")
		self.snapshot_label.setAlignment(Qt.AlignCenter)
		self.snapshot_label.setFixedSize(400, 300)
		self.snapshot_label.setStyleSheet("background-color: white; border: 1px solid #999;")
		self.snapshot_label.hide()

		# ===== Tiff Slider =====
		self.slider = QSlider(Qt.Horizontal)
		self.slider.setMinimum(0)
		self.slider.setValue(0)
		self.slider.valueChanged.connect(self.change_frame)
		self.slider.hide()
		self.slider.setToolTip("Navigate TIFF frames")

		# ===== X Axis Scroll Slider =====
		self.scroll_slider = QSlider(Qt.Horizontal)
		self.scroll_slider.setMinimum(0)
		self.scroll_slider.setMaximum(1000)
		self.scroll_slider.setSingleStep(1)
		self.scroll_slider.setValue(0)
		self.scroll_slider.valueChanged.connect(self.scroll_plot)
		self.scroll_slider.hide()
		self.scroll_slider.setStyleSheet("""
			QSlider::groove:horizontal {
				border: 1px solid #aaa;
				height: 10px;
				background: #e0e0e0;
				margin: 4px 0;
				border-radius: 5px;
			}
		
			QSlider::handle:horizontal {
				background: #007BFF;
				border: 1px solid #555;
				width: 16px;
				height: 16px;
				margin: -4px 0;
				border-radius: 8px;
			}
		
			QSlider::sub-page:horizontal {
				background: #cce5ff;
				border-radius: 5px;
			}
		
			QSlider::add-page:horizontal {
				background: #f5f5f5;
				border-radius: 5px;
			}
		""")
		self.scroll_slider.setToolTip("Scroll timeline (X-axis)")

		# ===== Event Table =====
		self.event_table = QTableWidget()
		self.event_table.setColumnCount(3)
		self.event_table.setHorizontalHeaderLabels(["Event", "Time (s)", "ID (µm)"])
		self.event_table.setColumnWidth(0, 180)
		self.event_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
		self.event_table.setSelectionBehavior(QAbstractItemView.SelectRows)
		self.event_table.setStyleSheet("background-color: white; color: black;")
		self.event_table.horizontalHeader().setStretchLastSection(True)
		self.event_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		self.event_table.cellClicked.connect(self.table_row_clicked)

		# ===== Create Plot Area with Scroll Slider Below =====
		plot_with_slider_layout = QVBoxLayout()
		plot_with_slider_layout.addWidget(self.canvas)
		plot_with_slider_layout.addWidget(self.scroll_slider)
		
		left_layout = QVBoxLayout()
		left_layout.addWidget(self.toolbar)
		left_layout.addLayout(plot_with_slider_layout)

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

		# ===== Hover Readout Label =====
		self.hover_label = QLabel("", self)
		self.hover_label.setStyleSheet("""
			background-color: rgba(255, 255, 255, 220);
			border: 1px solid #888;
			border-radius: 5px;
			padding: 2px 6px;
			font-size: 12px;
		""")
		self.hover_label.hide()

		self.canvas.mpl_connect("draw_event", self.update_event_label_positions)
		self.canvas.mpl_connect("button_release_event", lambda event: QTimer.singleShot(100, lambda: self.on_mouse_release(event)))
		self.canvas.mpl_connect("motion_notify_event", self.update_event_label_positions)
		self.canvas.mpl_connect("motion_notify_event", self.update_hover_label)
		self.canvas.mpl_connect("button_press_event", self.handle_click_on_plot)

	# ===== All Other Functions =====
	# (Your load_trace, load_events, update_plot, etc. remain unchanged.)

	# ===== Trace File Loading =====
	def load_trace(self):
		file_path, _ = QFileDialog.getOpenFileName(self, "Open Trace File", "", "CSV Files (*.csv)")
		if file_path:
			self.trace_data = load_trace(file_path)
			filename = os.path.basename(file_path)
			self.trace_file_label.setText(f"🧪 {filename}")

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
				txt = self.ax.text(
					self.event_times[i], 0, self.event_labels[i],
					rotation=90,
					verticalalignment='top',
					horizontalalignment='right',
					fontsize=8,
					color='black',
					clip_on=True  # ⬅ ensures text stays inside axes
				)

				self.event_text_objects.append((txt, self.event_times[i]))
				self.event_table_data.append((self.event_labels[i], round(self.event_times[i],2), round(diam_pre,2)))

			self.populate_table()
			self.auto_export_table()
			self.auto_export_editable_plot()

		self.canvas.draw()
		QTimer.singleShot(50, self.update_event_label_positions)
		self.update_scroll_slider()

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
	
		y_min, y_max = self.ax.get_ylim()
		y_top = min(y_max - 5, y_max * 0.95)
	
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
				self.snapshot_label.show()	# Show snapshot viewer
				self.slider.show()			 # Show slider
				self.slider_marker = None	 # <--- Reset red marker so it's clean for new TIFF
				self.update_scroll_slider()

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

	# ====== Axis Slider ======
	def update_scroll_slider(self):
		if self.trace_data is None:
			return
	
		full_t_min = self.trace_data['Time (s)'].min()
		full_t_max = self.trace_data['Time (s)'].max()
		xlim = self.ax.get_xlim()
		self.window_width = xlim[1] - xlim[0]
	
		if self.window_width < (full_t_max - full_t_min):
			self.scroll_slider.show()
		else:
			self.scroll_slider.hide()
	
		# Synchronize slider position to zoom window
		fraction = (xlim[0] - full_t_min) / (full_t_max - full_t_min - self.window_width)
		slider_val = int(fraction * self.scroll_slider.maximum())
		self.scroll_slider.blockSignals(True)
		self.scroll_slider.setValue(slider_val)
		self.scroll_slider.blockSignals(False)
	
	def scroll_plot(self):
		if self.trace_data is None:
			return
	
		# Get updated view window (zoom level)
		full_t_min = self.trace_data['Time (s)'].min()
		full_t_max = self.trace_data['Time (s)'].max()
		xlim = self.ax.get_xlim()
		window_width = xlim[1] - xlim[0]
	
		max_scroll = self.scroll_slider.maximum()
		slider_pos = self.scroll_slider.value()
		fraction = slider_pos / max_scroll
	
		new_left = full_t_min + (full_t_max - full_t_min - window_width) * fraction
		new_right = new_left + window_width
	
		self.ax.set_xlim(new_left, new_right)
		self.canvas.draw_idle()

	# ====== Hover Label ======
	def update_hover_label(self, event):
		if event.inaxes != self.ax or self.trace_data is None:
			self.hover_label.hide()
			return
	
		x_val = event.xdata
		if x_val is None:
			self.hover_label.hide()
			return
	
		# Get the nearest Y-value from trace
		time_array = self.trace_data['Time (s)'].values
		id_array = self.trace_data['Inner Diameter'].values
		nearest_idx = np.argmin(np.abs(time_array - x_val))
		y_val = id_array[nearest_idx]
	
		text = f"Time: {x_val:.2f} s\nID: {y_val:.1f} µm"
		self.hover_label.setText(text)
	
		cursor_offset_x = 10
		cursor_offset_y = -30
		self.hover_label.move(
			int(self.canvas.geometry().left() + event.guiEvent.pos().x() + cursor_offset_x),
			int(self.canvas.geometry().top() + event.guiEvent.pos().y() + cursor_offset_y)
		)
		self.hover_label.adjustSize()
		self.hover_label.show()


	# ====== Click on Plot ======
	def handle_click_on_plot(self, event):
		if event.inaxes != self.ax:
			return
	
		x = event.xdata
		if x is None:
			return
	
		# 🔴 Right-click = remove nearby pin
		if event.button == 3:
			click_x, click_y = event.x, event.y  # Pixel coordinates
		
			for marker, label in self.pinned_points:
				data_x = marker.get_xdata()[0]
				data_y = marker.get_ydata()[0]
		
				# Convert data coordinates to pixel space
				pixel_pos = self.ax.transData.transform((data_x, data_y))
				pixel_x, pixel_y = pixel_pos
		
				# Check pixel-distance to click
				pixel_distance = np.hypot(pixel_x - click_x, pixel_y - click_y)
		
				if pixel_distance < 10:  # 10 pixels tolerance
					marker.remove()
					label.remove()
					self.pinned_points.remove((marker, label))
					self.canvas.draw_idle()
					return
			return

		# 🟢 Left-click = add pin (unless Zoom/Pan active)
		if event.button == 1 and not self.toolbar.mode:
			time_array = self.trace_data['Time (s)'].values
			id_array = self.trace_data['Inner Diameter'].values
			nearest_idx = np.argmin(np.abs(time_array - x))
			y = id_array[nearest_idx]
	
			marker = self.ax.plot(x, y, 'ro', markersize=6)[0]
			label = self.ax.annotate(
				f"{x:.2f} s\n{y:.1f} µm",
				xy=(x, y),
				xytext=(6, 6),
				textcoords='offset points',
				bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=1),
				fontsize=8
			)
	
			self.pinned_points.append((marker, label))
			self.canvas.draw_idle()

	# ====== Deselect Zoom ======
	def on_mouse_release(self, event):
		self.update_event_label_positions(event)
	
		if self.toolbar.mode == 'zoom':
			self.toolbar.zoom()         # Toggle zoom mode OFF
			self.toolbar.mode = ''      # 🧹 Force-clear the mode string
			self.toolbar._active = None # 🔨 Also clear internal state (important!)
			self.canvas.setCursor(Qt.ArrowCursor)  # Reset cursor icon
	
		self.update_scroll_slider()
