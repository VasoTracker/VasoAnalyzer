import os
import re
from PyQt5.QtWidgets import QFileDialog, QMessageBox
# [A] ========================= IMPORTS AND GLOBAL CONFIG ============================
import sys, os, pickle
import numpy as np
import pandas as pd
import tifffile
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib import rcParams
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

from PyQt5.QtWidgets import (
	QMainWindow, QWidget, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout,
	QSlider, QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView,
	QHeaderView, QMessageBox, QInputDialog, QMenu, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt, QTimer

from vasoanalyzer.trace_loader import load_trace
from vasoanalyzer.tiff_loader import load_tiff
from vasoanalyzer.event_loader import load_events

# [B] ========================= MAIN CLASS DEFINITION ================================
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
		self.setWindowTitle("VasoAnalyzer 2.1 - Python Edition")
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
		self.last_replaced_event = None	 # Stores (index, old_value)

		# ===== Axis + Slider State =====
		self.axis_dragging = False
		self.axis_drag_start = None
		self.drag_direction = None
		self.scroll_slider = None
		self.window_width = None

		# ===== Build UI =====
		self.initUI()

# [C] ========================= UI SETUP (initUI) ======================================
	def initUI(self):
		from PyQt5.QtWidgets import QSizePolicy
	
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
		self.loadTraceBtn = QPushButton("Load Trace + Events")
		self.loadTraceBtn.clicked.connect(self.load_trace_and_events)
	
		self.load_snapshot_button = QPushButton("Load _Result.tiff")
		self.load_snapshot_button.clicked.connect(self.load_snapshot)
		self.save_hr_button = QPushButton("Export High-Res Plot")
		self.save_hr_button.clicked.connect(self.export_high_res_plot)

		# ===== Plot + Toolbar =====
		self.fig = Figure(figsize=(8, 4), facecolor='white')
		self.canvas = FigureCanvas(self.fig)
		self.ax = self.fig.add_subplot(111)
	
		self.toolbar = NavigationToolbar(self.canvas, self)
		self.toolbar.setStyleSheet("""
			QToolBar {
				background-color: #F0F0F0;
				border: 1px solid #DDD;
				padding: 4px;
			}
			QToolButton {
				background-color: #FFFFFF;
				border: 1px solid #CCC;
				border-radius: 6px;
				padding: 6px;
				margin: 2px;
			}
			QToolButton:hover {
				background-color: #E0F0FF;
				border: 1px solid #3399FF;
			}
			QToolButton:checked {
				background-color: #CCE5FF;
				border: 1px solid #3399FF;
			}
		""")
		
		# File label in toolbar
		self.trace_file_label = QLabel("No trace loaded")
		self.trace_file_label.setStyleSheet("color: gray; font-size: 12px; padding-left: 10px;")
		self.trace_file_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
		
		# Add file label to toolbar with spacing
		self.toolbar.addSeparator()
		spacer = QWidget()
		spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
		self.toolbar.addWidget(spacer)
		self.toolbar.addWidget(self.trace_file_label)
		self.toolbar.addSeparator()
		style_button = QPushButton("Plot Style Editor…")
		style_button.setStyleSheet("background-color: white; padding: 4px;")
		style_button.clicked.connect(self.open_plot_style_editor)
		self.toolbar.addWidget(style_button)
	
		# Fix toolbar tooltips
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
	
		# ===== TIFF Frame Slider =====
		self.slider = QSlider(Qt.Horizontal)
		self.slider.setMinimum(0)
		self.slider.setValue(0)
		self.slider.valueChanged.connect(self.change_frame)
		self.slider.hide()
		self.slider.setToolTip("Navigate TIFF frames")
	
		# ===== X-Axis Scroll Slider =====
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
		self.event_table.setEditTriggers(QAbstractItemView.DoubleClicked)
		self.event_table.setSelectionBehavior(QAbstractItemView.SelectRows)
		self.event_table.setStyleSheet("background-color: white; color: black;")
		self.event_table.horizontalHeader().setStretchLastSection(True)
		self.event_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		self.event_table.cellClicked.connect(self.table_row_clicked)
		self.event_table.itemChanged.connect(self.handle_table_edit)
	
		# ===== Hover Label =====
		self.hover_label = QLabel("", self)
		self.hover_label.setStyleSheet("""
			background-color: rgba(255, 255, 255, 220);
			border: 1px solid #888;
			border-radius: 5px;
			padding: 2px 6px;
			font-size: 12px;
		""")
		self.hover_label.hide()
	
		# ===== Layout Assembly =====
		plot_with_slider_layout = QVBoxLayout()
		plot_with_slider_layout.addWidget(self.canvas)
		plot_with_slider_layout.addWidget(self.scroll_slider)
	
		left_layout = QVBoxLayout()
		left_layout.addWidget(self.toolbar)
		left_layout.addLayout(plot_with_slider_layout)
	
		# Create a vertical layout to group TIFF snapshot + its slider
		snapshot_with_slider_layout = QVBoxLayout()
		snapshot_with_slider_layout.addWidget(self.snapshot_label)
		snapshot_with_slider_layout.addWidget(self.slider)
		
		right_layout.addLayout(snapshot_with_slider_layout)
		right_layout.addWidget(self.event_table)
	
		top_layout.addLayout(left_layout, 4)
		top_layout.addLayout(right_layout, 1)
	
		bottom_layout.addWidget(self.loadTraceBtn)
		bottom_layout.addWidget(self.load_snapshot_button)
		bottom_layout.addWidget(self.save_hr_button)
	
		main_layout.addLayout(top_layout)
		main_layout.addLayout(bottom_layout)
	
		main_layout.setContentsMargins(10, 10, 10, 10)
		top_layout.setSpacing(10)
		bottom_layout.setContentsMargins(0, 5, 0, 0)
	
		central_widget.setLayout(main_layout)
	
		# ===== Canvas Interactions =====
		self.canvas.mpl_connect("draw_event", self.update_event_label_positions)
		self.canvas.mpl_connect("motion_notify_event", self.update_event_label_positions)
		self.canvas.mpl_connect("motion_notify_event", self.update_hover_label)
		self.canvas.mpl_connect("button_press_event", self.handle_click_on_plot)
		self.canvas.mpl_connect("button_release_event", lambda event: QTimer.singleShot(100, lambda: self.on_mouse_release(event)))

# [D] ========================= FILE LOADERS: TRACE / EVENTS / TIFF =====================
	def load_trace(self, file_path):
		if file_path:
			try:
				self.trace_data = load_trace(file_path)
				filename = os.path.basename(file_path)
				self.trace_file_path = os.path.dirname(file_path)
				self.trace_file_label.setText(f"🧪 {filename}")
				self.update_plot()
			except Exception as e:
				QMessageBox.critical(self, "Error", f"Failed to load trace file:\n{e}")
	

	def load_events(self, file_path):
		if file_path:
			try:
				self.event_labels, self.event_times = load_events(file_path)
				self.update_plot()
			except Exception as e:
				QMessageBox.critical(self, "Error", f"Failed to load event file:\n{e}")
	def load_trace_and_events(self):
		file_path, _ = QFileDialog.getOpenFileName(
			self, "Select Trace CSV", "", "CSV Files (*.csv)"
		)
		if not file_path:
			return

		self.load_trace(file_path)
		self.update_plot()

		trace_base = os.path.basename(file_path)
		match = re.match(r"(.*_Exp\d+)\.csv", trace_base)
		if match:
			event_filename = match.group(1) + "_table.csv"
			event_path = os.path.join(os.path.dirname(file_path), event_filename)

			if os.path.exists(event_path):
				self.load_events(event_path)
				self.populate_table()
				self.update_event_label_positions()
			else:
				QMessageBox.warning(
					self, "Event File Missing",
					f"Could not find expected event file:\n{event_filename}"
				)
	
	def load_snapshot(self):
		file_path, _ = QFileDialog.getOpenFileName(self, "Open Result TIFF", "", "TIFF Files (*.tif *.tiff)")
		if file_path:
			try:
				frames = load_tiff(file_path)
				valid_frames = [f for f in frames if f is not None and f.size > 0]
	
				if len(valid_frames) < len(frames):
					QMessageBox.warning(self, "TIFF Warning", "Some TIFF frames were empty or corrupted and were skipped.")
	
				self.snapshot_frames = valid_frames
				if self.snapshot_frames:
					self.display_frame(0)
					self.slider.setMaximum(len(self.snapshot_frames) - 1)
					self.slider.setValue(0)
					self.snapshot_label.show()
					self.slider.show()
					self.slider_marker = None
			except Exception as e:
				QMessageBox.critical(self, "Error", f"Failed to load TIFF file:\n{e}")

	def display_frame(self, index):
		if not self.snapshot_frames:
			return
	
		# Clamp index to valid range
		if index < 0 or index >= len(self.snapshot_frames):
			print(f"⚠️ Frame index {index} out of bounds.")
			return
	
		frame = self.snapshot_frames[index]
	
		# Skip if frame is empty or corrupted
		if frame is None or frame.size == 0:
			print(f"⚠️ Skipping empty or corrupted frame at index {index}")
			return
	
		try:
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
	
		except Exception as e:
			print(f"⚠️ Error displaying frame {index}: {e}")


	def change_frame(self):
		if not self.snapshot_frames:
			return
	
		idx = self.slider.value()
		self.current_frame = idx
		self.display_frame(idx)
		self.update_slider_marker()

	def update_slider_marker(self):
		if self.trace_data is None or not self.snapshot_frames:
			return
	
		t_current = self.slider.value() * self.recording_interval
	
		if self.slider_marker is None:
			self.slider_marker = self.ax.axvline(x=t_current, color='red', linestyle='--', linewidth=1.5, label="TIFF Frame")
		else:
			self.slider_marker.set_xdata([t_current, t_current])
	
		self.canvas.draw_idle()
		self.canvas.flush_events()

# [E] ========================= PLOT RENDERING AND UPDATES ==============================
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
					clip_on=True  # keeps text within plot limits
				)
				self.event_text_objects.append((txt, self.event_times[i]))
				self.event_table_data.append((self.event_labels[i], round(self.event_times[i], 2), round(diam_pre, 2)))
	
			self.populate_table()
			self.auto_export_table()
			self.auto_export_editable_plot()
	
		self.canvas.draw()
		QTimer.singleShot(50, self.update_event_label_positions)
		self.update_scroll_slider()
	
	def update_event_label_positions(self, event=None):
		if not self.event_text_objects:
			return
		y_min, y_max = self.ax.get_ylim()
		y_top = min(y_max - 5, y_max * 0.95)
		for txt, x in self.event_text_objects:
			txt.set_position((x, y_top))

# [F] ========================= EVENT TABLE MANAGEMENT ================================
	def populate_table(self):
		self.event_table.blockSignals(True)
		self.event_table.setRowCount(len(self.event_table_data))
		for row, (label, t, d) in enumerate(self.event_table_data):
			self.event_table.setItem(row, 0, QTableWidgetItem(str(label)))
			self.event_table.setItem(row, 1, QTableWidgetItem(str(t)))
			self.event_table.setItem(row, 2, QTableWidgetItem(str(d)))
		self.event_table.blockSignals(False)
	
	def handle_table_edit(self, item):
		row = item.row()
		col = item.column()
	
		if col != 2:
			self.populate_table()  # Reject edits to non-ID columns
			return
	
		try:
			new_val = float(item.text())
		except ValueError:
			QMessageBox.warning(self, "Invalid Input", "Please enter a valid number.")
			self.populate_table()
			return
	
		label = self.event_table_data[row][0]
		time = self.event_table_data[row][1]
		old_val = self.event_table_data[row][2]
	
		self.last_replaced_event = (row, old_val)
		self.event_table_data[row] = (label, time, round(new_val, 2))
	
		self.auto_export_table()
		print(f"✏️ ID updated at {time:.2f}s → {new_val:.2f} µm")
	
	def table_row_clicked(self, row, col):
		if not self.event_table_data:
			return
		t = self.event_table_data[row][1]
		if self.selected_event_marker:
			self.selected_event_marker.remove()
		self.selected_event_marker = self.ax.axvline(x=t, color='blue', linestyle='--', linewidth=1.2)
		self.canvas.draw()

# [G] ========================= PIN INTERACTION LOGIC ================================
	def handle_click_on_plot(self, event):
		if event.inaxes != self.ax:
			return
	
		x = event.xdata
		if x is None:
			return
	
		# 🔴 Right-click = open pin context menu
		if event.button == 3:
			click_x, click_y = event.x, event.y
	
			for marker, label in self.pinned_points:
				data_x = marker.get_xdata()[0]
				data_y = marker.get_ydata()[0]
				pixel_x, pixel_y = self.ax.transData.transform((data_x, data_y))
				pixel_distance = np.hypot(pixel_x - click_x, pixel_y - click_y)
	
				if pixel_distance < 10:
					menu = QMenu(self)
					replace_action = menu.addAction("Replace Event Value...")
					delete_action = menu.addAction("Delete Pin")
					undo_action = menu.addAction("Undo Last Replacement")
					add_new_action = menu.addAction("➕ Add as New Event")
	
					action = menu.exec_(self.canvas.mapToGlobal(event.guiEvent.pos()))
					if action == delete_action:
						marker.remove()
						label.remove()
						self.pinned_points.remove((marker, label))
						self.canvas.draw_idle()
						return
					elif action == replace_action:
						self.handle_event_replacement(data_x, data_y)
						return
					elif action == undo_action:
						self.undo_last_replacement()
						return
					elif action == add_new_action:
						self.prompt_add_event(data_x, data_y)
						return
			return
	
		# 🟢 Left-click = add pin (unless toolbar zoom/pan is active)
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
	
	def handle_event_replacement(self, x, y):
		if not self.event_labels or not self.event_times:
			print("No events available to replace.")
			return
	
		options = [f"{label} at {time:.2f}s" for label, time in zip(self.event_labels, self.event_times)]
		selected, ok = QInputDialog.getItem(
			self,
			"Select Event to Replace",
			"Choose the event whose value you want to replace:",
			options,
			0,
			False
		)
	
		if ok and selected:
			index = options.index(selected)
			event_label = self.event_labels[index]
			event_time = self.event_times[index]
	
			confirm = QMessageBox.question(
				self,
				"Confirm Replacement",
				f"Replace ID for '{event_label}' at {event_time:.2f}s with {y:.1f} µm?",
				QMessageBox.Yes | QMessageBox.No
			)
	
			if confirm == QMessageBox.Yes:
				old_value = self.event_table_data[index][2]
				self.last_replaced_event = (index, old_value)
	
				self.event_table_data[index] = (event_label, round(event_time, 2), round(y, 2))
				self.populate_table()
				self.auto_export_table()
				print(f"✅ Replaced value at {event_time:.2f}s with {y:.1f} µm.")
	
	def prompt_add_event(self, x, y):
		if not self.event_table_data:
			QMessageBox.warning(self, "No Events", "You must load events before adding new ones.")
			return
	
		# Build label options and insertion points
		insert_labels = [f"{label} at {t:.2f}s" for label, t, _ in self.event_table_data]
		insert_labels.append("↘️ Add to end")  # final option
	
		selected, ok = QInputDialog.getItem(
			self,
			"Insert Event",
			"Insert new event before which existing event?",
			insert_labels,
			0,
			False
		)
	
		if not ok or not selected:
			return
	
		# Choose label for new event
		new_label, label_ok = QInputDialog.getText(
			self,
			"New Event Label",
			"Enter label for the new event:"
		)
	
		if not label_ok or not new_label.strip():
			return
	
		insert_idx = insert_labels.index(selected)
		new_entry = (new_label.strip(), round(x, 2), round(y, 2))
	
		# Insert into data
		if insert_idx == len(self.event_table_data):  # Add to end
			self.event_labels.append(new_label.strip())
			self.event_times.append(x)
			self.event_table_data.append(new_entry)
		else:
			self.event_labels.insert(insert_idx, new_label.strip())
			self.event_times.insert(insert_idx, x)
			self.event_table_data.insert(insert_idx, new_entry)
	
		self.populate_table()
		self.auto_export_table()
		print(f"➕ Inserted new event: {new_entry}")
		
	def undo_last_replacement(self):
		if self.last_replaced_event is None:
			QMessageBox.information(self, "Undo", "No replacement to undo.")
			return
	
		index, old_val = self.last_replaced_event
		label, time, _ = self.event_table_data[index]
	
		self.event_table_data[index] = (label, time, old_val)
		self.populate_table()
		self.auto_export_table()
	
		QMessageBox.information(self, "Undo", f"Restored value for '{label}' at {time:.2f}s.")
		self.last_replaced_event = None

# [H] ========================= HOVER LABEL AND CURSOR SYNC ===========================
	def update_hover_label(self, event):
		if event.inaxes != self.ax or self.trace_data is None:
			self.hover_label.hide()
			return
	
		x_val = event.xdata
		if x_val is None:
			self.hover_label.hide()
			return
	
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

# [I] ========================= ZOOM + SLIDER LOGIC ================================
	def on_mouse_release(self, event):
		self.update_event_label_positions(event)
	
		# Deselect zoom after box zoom
		if self.toolbar.mode == 'zoom':
			self.toolbar.zoom()	 # toggles off
			self.toolbar.mode = ''
			self.toolbar._active = None
			self.canvas.setCursor(Qt.ArrowCursor)
	
		self.update_scroll_slider()
	
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
	
		# Sync slider to match zoomed view
		fraction = (xlim[0] - full_t_min) / (full_t_max - full_t_min - self.window_width)
		slider_val = int(fraction * self.scroll_slider.maximum())
		self.scroll_slider.blockSignals(True)
		self.scroll_slider.setValue(slider_val)
		self.scroll_slider.blockSignals(False)
	
	def scroll_plot(self):
		if self.trace_data is None:
			return
	
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

# [J] ========================= PLOT STYLE EDITOR ================================
	def open_plot_style_editor(self):
		from PyQt5.QtWidgets import QDialog
	
		dialog = PlotStyleDialog(self)
		if dialog.exec_() == QDialog.Accepted:
			style = dialog.get_style()
	
			if style['apply_x']:
				self.ax.tick_params(axis='x', labelsize=style['font_size'])
				self.ax.xaxis.label.set_fontsize(style['font_size'])
				self.ax.xaxis.label.set_fontname(style['font_family'])
				self.ax.xaxis.label.set_fontstyle('italic' if style['italic'] else 'normal')
				self.ax.xaxis.label.set_fontweight('bold' if style['bold'] else 'normal')
	
			if style['apply_y']:
				self.ax.tick_params(axis='y', labelsize=style['font_size'])
				self.ax.yaxis.label.set_fontsize(style['font_size'])
				self.ax.yaxis.label.set_fontname(style['font_family'])
				self.ax.yaxis.label.set_fontstyle('italic' if style['italic'] else 'normal')
				self.ax.yaxis.label.set_fontweight('bold' if style['bold'] else 'normal')
	
			if style['apply_events']:
				for txt, _ in self.event_text_objects:
					txt.set_fontsize(style['font_size'])
					txt.set_fontname(style['font_family'])
					txt.set_fontstyle('italic' if style['italic'] else 'normal')
					txt.set_fontweight('bold' if style['bold'] else 'normal')
	
			if style['apply_pins']:
				for marker, label in self.pinned_points:
					marker.set_markersize(style['pin_size'])
					label.set_fontsize(style['font_size'])
					label.set_fontname(style['font_family'])
					label.set_fontstyle('italic' if style['italic'] else 'normal')
					label.set_fontweight('bold' if style['bold'] else 'normal')
	
			# Update trace line width
			for line in self.ax.get_lines():
				line.set_linewidth(style['line_width'])
	
			self.canvas.draw_idle()
			
# [K] ========================= EXPORT LOGIC (CSV, FIG) ==============================
	def auto_export_table(self):
		if not self.trace_file_path:
			return
		csv_path = os.path.join(self.trace_file_path, "eventDiameters_output.csv")
		df = pd.DataFrame(self.event_table_data, columns=["Event", "Time (s)", "ID (µm)"])
		df.to_csv(csv_path, index=False)
		print(f"✔ Event table saved to:\n{csv_path}")
	
	def auto_export_editable_plot(self):
		if not self.trace_file_path:
			return
		pickle_path = os.path.join(self.trace_file_path, "tracePlot_output.fig.pickle")
		with open(pickle_path, 'wb') as f:
			pickle.dump(self.fig, f)
		print(f"✔ Editable trace figure saved to:\n{pickle_path}")
		
	def export_high_res_plot(self):
		if not self.trace_file_path:
			QMessageBox.warning(self, "Export Error", "No trace file loaded.")
			return
	
		save_path, _ = QFileDialog.getSaveFileName(
			self,
			"Save High-Resolution Plot",
			os.path.join(self.trace_file_path, "tracePlot_highres.tiff"),
			"TIFF Image (*.tiff);;SVG Vector (*.svg)"
		)
	
		if save_path:
			try:
				ext = os.path.splitext(save_path)[1].lower()
				if ext == ".svg":
					self.fig.savefig(save_path, format='svg', bbox_inches='tight')
				else:
					self.fig.savefig(save_path, format='tiff', dpi=600, bbox_inches='tight')
	
				QMessageBox.information(self, "Export Complete", f"Plot exported:\n{save_path}")
			except Exception as e:
				QMessageBox.critical(self, "Export Failed", str(e))



from PyQt5.QtWidgets import (
	QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
	QCheckBox, QSpinBox, QFontComboBox, QGroupBox
)

class PlotStyleDialog(QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Plot Style Editor")

		layout = QVBoxLayout()

		# Font group
		font_group = QGroupBox("Font Styling")
		font_layout = QVBoxLayout()
		self.font_size = QSpinBox(); self.font_size.setRange(6, 40); self.font_size.setValue(12)
		self.font_family = QFontComboBox()
		self.bold = QCheckBox("Bold")
		self.italic = QCheckBox("Italic")
		font_layout.addWidget(QLabel("Font Size:")); font_layout.addWidget(self.font_size)
		font_layout.addWidget(QLabel("Font Family:")); font_layout.addWidget(self.font_family)
		font_layout.addWidget(self.bold); font_layout.addWidget(self.italic)
		font_group.setLayout(font_layout)

		# Line/Marker group
		line_group = QGroupBox("Trace & Marker Styling")
		line_layout = QVBoxLayout()
		self.line_width = QSpinBox(); self.line_width.setRange(1, 10); self.line_width.setValue(2)
		self.pin_size = QSpinBox(); self.pin_size.setRange(1, 20); self.pin_size.setValue(6)
		line_layout.addWidget(QLabel("Trace Line Width:")); line_layout.addWidget(self.line_width)
		line_layout.addWidget(QLabel("Pin Marker Size:")); line_layout.addWidget(self.pin_size)
		line_group.setLayout(line_layout)

		# Apply To section
		target_group = QGroupBox("Apply Style To...")
		target_layout = QVBoxLayout()
		self.apply_x = QCheckBox("X-Axis Labels and Ticks"); self.apply_x.setChecked(True)
		self.apply_y = QCheckBox("Y-Axis Labels and Ticks"); self.apply_y.setChecked(True)
		self.apply_events = QCheckBox("Event Labels"); self.apply_events.setChecked(True)
		self.apply_pins = QCheckBox("Pinned Points"); self.apply_pins.setChecked(True)
		target_layout.addWidget(self.apply_x)
		target_layout.addWidget(self.apply_y)
		target_layout.addWidget(self.apply_events)
		target_layout.addWidget(self.apply_pins)
		target_group.setLayout(target_layout)

		# Confirm buttons
		button_layout = QHBoxLayout()
		apply_btn = QPushButton("Apply")
		cancel_btn = QPushButton("Cancel")
		apply_btn.clicked.connect(self.accept)
		cancel_btn.clicked.connect(self.reject)
		button_layout.addWidget(apply_btn)
		button_layout.addWidget(cancel_btn)

		# Assemble layout
		layout.addWidget(font_group)
		layout.addWidget(line_group)
		layout.addWidget(target_group)
		layout.addLayout(button_layout)
		self.setLayout(layout)

	def get_style(self):
		return {
			'font_size': self.font_size.value(),
			'font_family': self.font_family.currentFont().family(),
			'bold': self.bold.isChecked(),
			'italic': self.italic.isChecked(),
			'line_width': self.line_width.value(),
			'pin_size': self.pin_size.value(),
			'apply_x': self.apply_x.isChecked(),
			'apply_y': self.apply_y.isChecked(),
			'apply_events': self.apply_events.isChecked(),
			'apply_pins': self.apply_pins.isChecked(),
		}