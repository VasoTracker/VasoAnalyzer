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
	QHeaderView, QMessageBox, QInputDialog, QMenu, QSizePolicy, QAction,
	QToolBar, QToolButton, QSpacerItem
)

from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt, QTimer, QSize, QSettings
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QStatusBar


from vasoanalyzer.trace_loader import load_trace
from vasoanalyzer.tiff_loader import load_tiff
from vasoanalyzer.event_loader import load_events
from vasoanalyzer.excel_mapper import ExcelMappingDialog, update_excel_file

# [B] ========================= MAIN CLASS DEFINITION ================================
PREVIOUS_PLOT_PATH = os.path.join(os.path.expanduser("~"), ".vasoanalyzer_last_plot.pickle")

class VasoAnalyzerApp(QMainWindow):
    ...

    def update_plot(self):
        if self.trace_data is None:
            return

        self.ax.clear()
        self.ax.set_facecolor("white")
        self.ax.tick_params(colors='black')
        self.ax.xaxis.label.set_color('black')
        self.ax.yaxis.label.set_color('black')
        self.ax.title.set_color('black')
        self.event_text_objects = []

        # Plot trace
        t = self.trace_data['Time (s)']
        d = self.trace_data['Inner Diameter']
        self.ax.plot(t, d, 'k-', linewidth=1.5)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Inner Diameter (µm)")
        self.ax.grid(True, color='#CCC')

        # Plot events if available
        if self.event_labels and self.event_times:
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

                # Vertical line
                self.ax.axvline(x=self.event_times[i], color='black', linestyle='--', linewidth=0.8)

                # Label on plot
                txt = self.ax.text(
                    self.event_times[i], 0, self.event_labels[i],
                    rotation=90,
                    verticalalignment='top',
                    horizontalalignment='right',
                    fontsize=8,
                    color='black',
                    clip_on=True
                )
                self.event_text_objects.append((txt, self.event_times[i]))

                # Table entry
                self.event_table_data.append((
                    self.event_labels[i],
                    round(self.event_times[i], 2),
                    round(diam_pre, 2)
                ))

            self.populate_table()
            self.auto_export_table()

        self.canvas.draw()
        self.canvas.flush_events()

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

		# Only allow editing the third column (ID)
		if col != 2:
			self.populate_table()
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
					replace_action = menu.addAction("Replace Event Value…")
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
	
		text = f"Time: {x_val:.2f} s\nID: {y_val:.2f} µm"
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

# [J] ========================= PLOT STYLE EDITOR ================================
	def open_plot_style_editor(self, tab_name=None):
		from PyQt5.QtWidgets import QDialog

		dialog = PlotStyleDialog(self)

		if tab_name:
			index = dialog.tabs.indexOf(dialog.tabs.findChild(QWidget, tab_name))
			if index != -1:
				dialog.tabs.setCurrentIndex(index)

		prev_style = dialog.get_style()

		if dialog.exec_() == QDialog.Accepted:
			style = dialog.get_style()
			self.apply_plot_style(style)
		else:
			self.apply_plot_style(prev_style)
	
	def apply_plot_style(self, style):
		# Axis Titles
		self.ax.xaxis.label.set_fontsize(style['axis_font_size'])
		self.ax.xaxis.label.set_fontname(style['axis_font_family'])
		self.ax.xaxis.label.set_fontstyle('italic' if style['axis_italic'] else 'normal')
		self.ax.xaxis.label.set_fontweight('bold' if style['axis_bold'] else 'normal')
	
		self.ax.yaxis.label.set_fontsize(style['axis_font_size'])
		self.ax.yaxis.label.set_fontname(style['axis_font_family'])
		self.ax.yaxis.label.set_fontstyle('italic' if style['axis_italic'] else 'normal')
		self.ax.yaxis.label.set_fontweight('bold' if style['axis_bold'] else 'normal')
	
		# Tick Labels
		self.ax.tick_params(axis='x', labelsize=style['tick_font_size'])
		self.ax.tick_params(axis='y', labelsize=style['tick_font_size'])
	
		# Event Labels
		for txt, _ in self.event_text_objects:
			txt.set_fontsize(style['event_font_size'])
			txt.set_fontname(style['event_font_family'])
			txt.set_fontstyle('italic' if style['event_italic'] else 'normal')
			txt.set_fontweight('bold' if style['event_bold'] else 'normal')
	
		# Pinned Labels
		for marker, label in self.pinned_points:
			marker.set_markersize(style['pin_size'])
			label.set_fontsize(style['pin_font_size'])
			label.set_fontname(style['pin_font_family'])
			label.set_fontstyle('italic' if style['pin_italic'] else 'normal')
			label.set_fontweight('bold' if style['pin_bold'] else 'normal')
	
		# Line Width — ONLY change the main trace line
		main_line = self.ax.lines[0] if self.ax.lines else None
		if main_line:
			main_line.set_linewidth(style['line_width'])
	
		self.canvas.draw_idle()
		
	
	def open_customize_dialog(self):
		# Check visibility of any existing grid line
		is_grid_visible = any(line.get_visible() for line in self.ax.get_xgridlines())
		self.ax.grid(not is_grid_visible)
		self.toolbar.edit_parameters()
		self.canvas.draw_idle()

	def start_new_analysis(self):
		confirm = QMessageBox.question(
			self, "Start New Analysis",
			"Clear current session and start fresh?",
			QMessageBox.Yes | QMessageBox.No
		)
		if confirm == QMessageBox.Yes:
			self.clear_current_session()

	def clear_current_session(self):
		self.trace_data = None
		self.trace_file_path = None
		self.snapshot_frames = []
		self.current_frame = 0
		self.event_labels = []
		self.event_times = []
		self.event_text_objects = []
		self.event_table_data = []
		self.pinned_points = []
		self.selected_event_marker = None
		self.slider_marker = None
		self.ax.clear()
		self.canvas.draw()
		self.event_table.setRowCount(0)
		self.snapshot_label.clear()
		self.trace_file_label.setText("No trace loaded")
		self.slider.hide()
		self.snapshot_label.hide()
		self.excel_btn.setEnabled(False)
		print("🧼 Cleared session.")
		self.statusBar().showMessage("Started new analysis.")

	def show_event_table_context_menu(self, position):
		index = self.event_table.indexAt(position)
		if not index.isValid():
			return
	
		row = index.row()
		menu = QMenu()
	
		# Group 1: Edit & Delete
		edit_action = menu.addAction("✏️ Edit ID (µm)…")
		delete_action = menu.addAction("🗑️ Delete Event")
		menu.addSeparator()
	
		# Group 2: Plot Navigation
		jump_action = menu.addAction("🔍 Jump to Event on Plot")
		pin_action = menu.addAction("📌 Pin to Plot")
		menu.addSeparator()
	
		# Group 3: Pin Utilities
		replace_with_pin_action = menu.addAction("🔄 Replace ID with Pinned Value")
		clear_pins_action = menu.addAction("❌ Clear All Pins")
	
		# Show menu
		action = menu.exec_(self.event_table.viewport().mapToGlobal(position))
	
		# Group 1 actions
		if action == edit_action:
			old_val = self.event_table.item(row, 2).text()
			new_val, ok = QInputDialog.getDouble(self, "Edit ID", "Enter new ID (µm):", float(old_val), 0, 10000, 2)
			if ok:
				self.event_table_data[row] = (
					self.event_table_data[row][0],
					self.event_table_data[row][1],
					round(new_val, 2)
				)
				self.populate_table()
				self.auto_export_table()
	
		elif action == delete_action:
			confirm = QMessageBox.question(
				self, "Delete Event", f"Delete event: {self.event_table_data[row][0]}?",
				QMessageBox.Yes | QMessageBox.No
			)
			if confirm == QMessageBox.Yes:
				del self.event_labels[row]
				del self.event_times[row]
				del self.event_table_data[row]
				self.populate_table()
				self.update_plot()
	
		# Group 2 actions
		elif action == jump_action:
			t = self.event_table_data[row][1]
			if self.selected_event_marker:
				self.selected_event_marker.remove()
			self.selected_event_marker = self.ax.axvline(x=t, color='blue', linestyle='--', linewidth=1.2)
			self.canvas.draw()
	
		elif action == pin_action:
			t = self.event_table_data[row][1]
			id_val = self.event_table_data[row][2]
			marker = self.ax.plot(t, id_val, 'ro', markersize=6)[0]
			label = self.ax.annotate(
				f"{t:.2f} s\n{round(id_val,1)} µm",
				xy=(t, id_val),
				xytext=(6, 6),
				textcoords='offset points',
				bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=1),
				fontsize=8
			)
			self.pinned_points.append((marker, label))
			self.canvas.draw_idle()
	
		# Group 3 actions
		elif action == replace_with_pin_action:
			t_event = self.event_table_data[row][1]
			if not self.pinned_points:
				QMessageBox.information(self, "No Pins", "There are no pinned points to use.")
				return
			closest_pin = min(self.pinned_points, key=lambda p: abs(p[0].get_xdata()[0] - t_event))
			pin_time = closest_pin[0].get_xdata()[0]
			pin_id = closest_pin[0].get_ydata()[0]
			confirm = QMessageBox.question(
				self, "Confirm Replacement",
				f"Replace ID at {t_event:.2f}s with pinned value: {pin_id:.2f} µm?",
				QMessageBox.Yes | QMessageBox.No
			)
			if confirm == QMessageBox.Yes:
				self.last_replaced_event = (row, self.event_table_data[row][2])
				self.event_table_data[row] = (
					self.event_table_data[row][0],
					t_event,
					round(pin_id, 2)
				)
				self.populate_table()
				self.auto_export_table()
				print(f"🔄 Replaced ID at {t_event:.2f}s with pinned value {pin_id:.2f} µm.")
	
		elif action == clear_pins_action:
			if not self.pinned_points:
				QMessageBox.information(self, "No Pins", "There are no pins to clear.")
				return
			for marker, label in self.pinned_points:
				marker.remove()
				label.remove()
			self.pinned_points.clear()
			self.canvas.draw_idle()
			print("🧹 Cleared all pins.")
	
	def save_recent_files(self):
		self.settings.setValue("recentFiles", self.recent_files)
	
	def clear_recent_files(self):
		self.recent_files = []
		self.save_recent_files()
		self.build_recent_files_menu()
		
	def dragEnterEvent(self, event):
		if event.mimeData().hasUrls():
			event.acceptProposedAction()
	
	def dropEvent(self, event):
		for url in event.mimeData().urls():
			file_path = url.toLocalFile()
			if file_path.lower().endswith(".csv"):
				self.load_trace_and_events(file_path)
			elif file_path.lower().endswith(".pickle"):
				self.load_custom_pickle_plot(file_path)
			else:
				QMessageBox.warning(self, "Unsupported File",
					f"Unsupported file type:\n{file_path}")
		
# [K] ========================= EXPORT LOGIC (CSV, FIG) ==============================
	def auto_export_table(self):
		if not self.trace_file_path:
			print("⚠️ No trace path set. Cannot export event table.")
			return

		try:
			output_dir = os.path.abspath(self.trace_file_path)
			csv_path = os.path.join(output_dir, "eventDiameters_output.csv")
			df = pd.DataFrame(self.event_table_data, columns=["Event", "Time (s)", "ID (µm)"])
			df.to_csv(csv_path, index=False)
			print(f"✔ Event table auto-exported to:\n{csv_path}")
		except Exception as e:
			print(f"❌ Failed to auto-export event table:\n{e}")

		if self.excel_auto_path and self.excel_auto_column:
			update_excel_file(
				self.excel_auto_path,
				self.event_table_data,
				start_row=3,
				column_letter=self.excel_auto_column
			)

	def auto_export_editable_plot(self):
		if not self.trace_file_path:
			return
		try:
			pickle_path = os.path.join(os.path.abspath(self.trace_file_path), "tracePlot_output.fig.pickle")
			state = {
				"trace_data": self.trace_data,
				"event_labels": self.event_labels,
				"event_times": self.event_times,
				"event_table_data": self.event_table_data
			}
			with open(pickle_path, 'wb') as f:
				pickle.dump(state, f)
			print(f"✔ Editable trace figure state saved to:\n{pickle_path}")
		except Exception as e:
			print(f"❌ Failed to save .pickle figure:\n{e}")

	def export_high_res_plot(self):
		if not self.trace_file_path:
			QMessageBox.warning(self, "Export Error", "No trace file loaded.")
			return

		save_path, _ = QFileDialog.getSaveFileName(
			self,
			"Save High-Resolution Plot",
			os.path.join(os.path.abspath(self.trace_file_path), "tracePlot_highres.tiff"),
			"TIFF Image (*.tiff);;SVG Vector (*.svg)"
		)

		if save_path:
			try:
				ext = os.path.splitext(save_path)[1].lower()
				if ext == ".svg":
					self.fig.savefig(save_path, format='svg', bbox_inches='tight')
				else:
					self.fig.savefig(save_path, format='tiff', dpi=600, bbox_inches='tight')
					self.auto_export_editable_plot()

				QMessageBox.information(self, "Export Complete", f"Plot exported:\n{save_path}")
			except Exception as e:
				QMessageBox.critical(self, "Export Failed", str(e))


	def open_excel_mapping_dialog(self):
		if not self.event_table_data:
			QMessageBox.warning(self, "No Data", "No event data available to export.")
			return
	
		dialog = ExcelMappingDialog(self, [
			{"EventLabel": label, "Time (s)": time, "ID (µm)": idval}
			for label, time, idval in self.event_table_data
		])
		if dialog.exec_():
			# Only remember file path and column – don't trigger auto-write!
			self.excel_auto_path = dialog.excel_path
			self.excel_auto_column = dialog.column_selector.currentText()

	def toggle_grid(self):
		self.grid_visible = not self.grid_visible
		if self.grid_visible:
			self.ax.grid(True, color='#CCC')
		else:
			self.ax.grid(False)
		self.canvas.draw_idle()


# [L] ========================= PlotStyleDialog =========================
from PyQt5.QtWidgets import (
	QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox,
	QCheckBox, QPushButton, QFormLayout
)

class PlotStyleDialog(QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Plot Style Editor")
		self.setMinimumWidth(400)

		self.tabs = QTabWidget()
		main_layout = QVBoxLayout()
		main_layout.addWidget(self.tabs)
		self.setLayout(main_layout)

		# ===== Bottom OK / Apply / Cancel =====
		btn_row = QHBoxLayout()
		btn_row.setContentsMargins(10, 4, 10, 10)
		
		self.ok_btn = QPushButton("OK")
		self.cancel_btn = QPushButton("Cancel")
		self.apply_btn = QPushButton("Apply")
		
		self.ok_btn.clicked.connect(self.accept)
		self.cancel_btn.clicked.connect(self.reject)
		self.apply_btn.clicked.connect(self.handle_apply_all)
		
		btn_row.addStretch()
		btn_row.addWidget(self.apply_btn)
		btn_row.addWidget(self.cancel_btn)
		btn_row.addWidget(self.ok_btn)
		
		main_layout.addLayout(btn_row)

		# Track settings per tab
		self.init_axis_tab()
		self.init_tick_tab()
		self.init_event_tab()
		self.init_pin_tab()
		self.init_line_tab()

	def init_axis_tab(self):
		tab = QWidget()
		layout = QVBoxLayout(tab)
		form = QFormLayout()

		self.axis_font_size = QSpinBox()
		self.axis_font_size.setRange(6, 32)
		self.axis_font_size.setValue(14)

		self.axis_font_family = QComboBox()
		self.axis_font_family.addItems(["Arial", "Helvetica", "Times New Roman", "Courier", "Verdana"])

		self.axis_bold = QCheckBox("Bold")
		self.axis_italic = QCheckBox("Italic")

		form.addRow("Font Size:", self.axis_font_size)
		form.addRow("Font Family:", self.axis_font_family)
		form.addRow("", self.axis_bold)
		form.addRow("", self.axis_italic)

		layout.addLayout(form)
		layout.addLayout(self.button_row('axis'))
		self.tabs.addTab(tab, "Axis Titles")
		tab.setObjectName("Axis Titles")

	def init_tick_tab(self):
		tab = QWidget()
		layout = QVBoxLayout(tab)
		form = QFormLayout()

		self.tick_font_size = QSpinBox()
		self.tick_font_size.setRange(6, 32)
		self.tick_font_size.setValue(12)

		form.addRow("Tick Label Font Size:", self.tick_font_size)

		layout.addLayout(form)
		layout.addLayout(self.button_row('tick'))
		self.tabs.addTab(tab, "Tick Labels")
		tab.setObjectName("Tick Labels")

	def init_event_tab(self):
		tab = QWidget()
		layout = QVBoxLayout(tab)
		form = QFormLayout()

		self.event_font_size = QSpinBox()
		self.event_font_size.setRange(6, 32)
		self.event_font_size.setValue(10)

		self.event_font_family = QComboBox()
		self.event_font_family.addItems(["Arial", "Helvetica", "Times New Roman", "Courier", "Verdana"])

		self.event_bold = QCheckBox("Bold")
		self.event_italic = QCheckBox("Italic")

		form.addRow("Font Size:", self.event_font_size)
		form.addRow("Font Family:", self.event_font_family)
		form.addRow("", self.event_bold)
		form.addRow("", self.event_italic)

		layout.addLayout(form)
		layout.addLayout(self.button_row('event'))
		self.tabs.addTab(tab, "Event Labels")
		tab.setObjectName("Event Labels")

	def init_pin_tab(self):
		tab = QWidget()
		layout = QVBoxLayout(tab)
		form = QFormLayout()

		self.pin_font_size = QSpinBox()
		self.pin_font_size.setRange(6, 32)
		self.pin_font_size.setValue(10)

		self.pin_font_family = QComboBox()
		self.pin_font_family.addItems(["Arial", "Helvetica", "Times New Roman", "Courier", "Verdana"])

		self.pin_bold = QCheckBox("Bold")
		self.pin_italic = QCheckBox("Italic")

		self.pin_size = QSpinBox()
		self.pin_size.setRange(2, 20)
		self.pin_size.setValue(6)

		form.addRow("Font Size:", self.pin_font_size)
		form.addRow("Font Family:", self.pin_font_family)
		form.addRow("", self.pin_bold)
		form.addRow("", self.pin_italic)
		form.addRow("Marker Size:", self.pin_size)

		layout.addLayout(form)
		layout.addLayout(self.button_row('pin'))
		self.tabs.addTab(tab, "Pinned Labels")
		tab.setObjectName("Pinned Labels")

	def init_line_tab(self):
		tab = QWidget()
		layout = QVBoxLayout(tab)
		form = QFormLayout()

		self.line_width = QSpinBox()
		self.line_width.setRange(1, 10)
		self.line_width.setValue(2)

		form.addRow("Trace Line Width:", self.line_width)
		layout.addLayout(form)
		layout.addLayout(self.button_row('line'))
		self.tabs.addTab(tab, "Trace Style")
		tab.setObjectName("Trace Style")

	def button_row(self, section):
		layout = QHBoxLayout()
		apply_btn = QPushButton("Apply")
		default_btn = QPushButton("Default")
	
		apply_btn.clicked.connect(lambda: self.handle_apply_tab(section))
		default_btn.clicked.connect(lambda: self.reset_defaults(section))
	
		layout.addStretch()
		layout.addWidget(apply_btn)
		layout.addWidget(default_btn)
		return layout
	
	def handle_apply_tab(self, section):
		if hasattr(self.parent(), "apply_plot_style"):
			self.parent().apply_plot_style(self.get_style())

	def handle_apply_all(self):
		if hasattr(self.parent(), "apply_plot_style"):
			self.parent().apply_plot_style(self.get_style())

	def reset_defaults(self, section):
		if section == 'axis':
			self.axis_font_size.setValue(14)
			self.axis_font_family.setCurrentText("Arial")
			self.axis_bold.setChecked(False)
			self.axis_italic.setChecked(False)
		elif section == 'tick':
			self.tick_font_size.setValue(12)
		elif section == 'event':
			self.event_font_size.setValue(10)
			self.event_font_family.setCurrentText("Arial")
			self.event_bold.setChecked(False)
			self.event_italic.setChecked(False)
		elif section == 'pin':
			self.pin_font_size.setValue(10)
			self.pin_font_family.setCurrentText("Arial")
			self.pin_bold.setChecked(False)
			self.pin_italic.setChecked(False)
			self.pin_size.setValue(6)
		elif section == 'line':
			self.line_width.setValue(2)

	def get_style(self):
		return {
			"axis_font_size": self.axis_font_size.value(),
			"axis_font_family": self.axis_font_family.currentText(),
			"axis_bold": self.axis_bold.isChecked(),
			"axis_italic": self.axis_italic.isChecked(),

			"tick_font_size": self.tick_font_size.value(),

			"event_font_size": self.event_font_size.value(),
			"event_font_family": self.event_font_family.currentText(),
			"event_bold": self.event_bold.isChecked(),
			"event_italic": self.event_italic.isChecked(),

			"pin_font_size": self.pin_font_size.value(),
			"pin_font_family": self.pin_font_family.currentText(),
			"pin_bold": self.pin_bold.isChecked(),
			"pin_italic": self.pin_italic.isChecked(),
			"pin_size": self.pin_size.value(),

			"line_width": self.line_width.value()
		}
