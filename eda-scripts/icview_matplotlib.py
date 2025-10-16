#!/usr/bin/env python3
import sys
import numpy as np
import pandas as pd
import csv
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QPushButton, QFileDialog, QLineEdit, QMessageBox,
    QDockWidget, QTextEdit, QComboBox, QLabel, QInputDialog
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# ---------- Draggable Cursor ----------
class DraggableCursor:
    def __init__(self, line, orientation='v', ax=None, delta_annotation=None):
        self.line = line
        self.orientation = orientation
        self.ax = ax or line.axes
        self.press = None
        self.delta_annotation = delta_annotation
        # annotation showing value next to cursor
        self.txt = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(5, 5),
            textcoords='offset points',
            color='red' if orientation == 'v' else 'blue',
            fontsize=8,
        )
        self.connect()

    def connect(self):
        self.cid_press = self.line.figure.canvas.mpl_connect('button_press_event', self.on_press)
        self.cid_release = self.line.figure.canvas.mpl_connect('button_release_event', self.on_release)
        self.cid_motion = self.line.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)

    def on_press(self, event):
        if event.inaxes != self.ax:
            return
        contains, _ = self.line.contains(event)
        if contains:
            self.press = (
                self.line.get_xdata() if self.orientation == 'v' else self.line.get_ydata(),
                event.xdata,
                event.ydata,
            )

    def on_motion(self, event):
        if self.press is None or event.inaxes != self.ax:
            return
        if self.orientation == 'v':
            # update vertical line position and its text
            self.line.set_xdata([event.xdata, event.xdata])
            self.txt.set_position((event.xdata, 0))
            self.txt.set_text(f"X={event.xdata:.6f}")
        else:
            self.line.set_ydata([event.ydata, event.ydata])
            self.txt.set_position((0, event.ydata))
            self.txt.set_text(f"Y={event.ydata:.6f}")

        if self.delta_annotation:
            # delta_annotation is expected to have update_text() method
            try:
                self.delta_annotation.update_text()
            except Exception:
                pass

        self.line.figure.canvas.draw_idle()

    def on_release(self, event):
        self.press = None

    def remove(self):
        # remove line and text from axes
        try:
            self.line.remove()
        except Exception:
            pass
        try:
            self.txt.remove()
        except Exception:
            pass
        self.line.figure.canvas.draw_idle()

# ---------- Delta Annotation ----------
class DeltaAnnotation:
    def __init__(self, ax, v_cursors, h_cursors):
        self.ax = ax
        self.v_cursors = v_cursors
        self.h_cursors = h_cursors
        self.annotation = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(15, 15),
            textcoords='offset points',
            color='green',
            bbox=dict(boxstyle="round", fc="w"),
            fontsize=9,
        )
        self.annotation.set_visible(False)

    def update_text(self):
        if len(self.v_cursors) >= 2 and len(self.h_cursors) >= 2:
            dx = abs(self.v_cursors[0].line.get_xdata()[0] - self.v_cursors[1].line.get_xdata()[0])
            dy = abs(self.h_cursors[0].line.get_ydata()[0] - self.h_cursors[1].line.get_ydata()[0])
            self.annotation.set_text(f"ΔX={dx:.6f}\nΔY={dy:.6f}")
            self.annotation.set_visible(True)
        else:
            self.annotation.set_visible(False)
        self.ax.figure.canvas.draw_idle()

# ---------- Main Viewer ----------
class WaveformViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Waveform Viewer")
        self.setGeometry(100, 100, 1400, 850)

        # central widget & layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # matplotlib figure & canvas
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.layout.addWidget(self.canvas)

        # toolbar (Matplotlib's toolbar + extra widgets)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)

        # status bar
        self.status = self.statusBar()
        self.status.showMessage("Ready")

        # data storage
        self.loaded_waveforms = []
        self.time = None
        self.data = None
        self.labels = []

        # cursors
        self.v_cursors = []
        self.h_cursors = []

        # delta annotation helper
        self.delta_annotation = DeltaAnnotation(self.ax, self.v_cursors, self.h_cursors)

        # save original view
        self.original_xlim = None
        self.original_ylim = None

        # hover tooltip
        self.tooltip = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(10, 10),
            textcoords='offset points',
            bbox=dict(boxstyle="round", fc="w"),
            fontsize=8,
        )
        self.tooltip.set_visible(False)
        self.canvas.mpl_connect("motion_notify_event", self.show_hover)

        # dock panel with tabs
        self.dock = QDockWidget("Controls", self)
        self.dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)

        self.tab_widget = QTabWidget()
        self.dock.setWidget(self.tab_widget)

        # Expressions tab
        self.expr_tab = QWidget()
        self.tab_widget.addTab(self.expr_tab, "Expressions")
        self.expr_layout = QVBoxLayout(self.expr_tab)

        self.expr_input = QLineEdit()
        self.expr_input.setPlaceholderText("Enter expression (e.g., V1+V2)")
        self.expr_layout.addWidget(self.expr_input)

        self.calc_button = QPushButton("Evaluate Expression")
        self.calc_button.clicked.connect(self.calculate_expression)
        self.expr_layout.addWidget(self.calc_button)

        self.expr_output = QTextEdit()
        self.expr_output.setReadOnly(True)
        self.expr_layout.addWidget(self.expr_output)

        # Analysis tab
        self.analysis_tab = QWidget()
        self.tab_widget.addTab(self.analysis_tab, "Analysis")
        self.analysis_layout = QVBoxLayout(self.analysis_tab)

        self.analysis_options = ["Frequency", "RMS", "Peak-to-Peak", "Max", "Min", "Mean", "Integral", "Delta X/Y"]
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems(self.analysis_options)
        self.analysis_layout.addWidget(QLabel("Select Analysis:"))
        self.analysis_layout.addWidget(self.analysis_combo)

        self.run_analysis_btn = QPushButton("Run Analysis")
        self.run_analysis_btn.clicked.connect(self.run_analysis)
        self.analysis_layout.addWidget(self.run_analysis_btn)

        self.analysis_output = QTextEdit()
        self.analysis_output.setReadOnly(True)
        self.analysis_layout.addWidget(self.analysis_output)

        self.save_waveform_btn = QPushButton("Save Waveform CSV")
        self.save_waveform_btn.clicked.connect(self.save_waveform)
        self.analysis_layout.addWidget(self.save_waveform_btn)

        self.save_analysis_btn = QPushButton("Save Analysis CSV")
        self.save_analysis_btn.clicked.connect(self.save_analysis)
        self.analysis_layout.addWidget(self.save_analysis_btn)

        # extra toolbar buttons (visible symbols)
        self.load_button = QPushButton("Load Files")
        self.load_button.clicked.connect(self.load_file)
        self.toolbar.addWidget(self.load_button)

        self.reset_button = QPushButton("Reset View")
        self.reset_button.clicked.connect(self.reset_view)
        self.toolbar.addWidget(self.reset_button)

        # visible cursor buttons (text-based, always present)
        self.add_v_cursor_btn = QPushButton("│")
        self.add_v_cursor_btn.setToolTip("Add Vertical Cursor")
        self.add_v_cursor_btn.clicked.connect(self.add_vertical_cursor_button)
        self.toolbar.addWidget(self.add_v_cursor_btn)

        self.add_h_cursor_btn = QPushButton("─")
        self.add_h_cursor_btn.setToolTip("Add Horizontal Cursor")
        self.add_h_cursor_btn.clicked.connect(self.add_horizontal_cursor_button)
        self.toolbar.addWidget(self.add_h_cursor_btn)

    # keyboard: Backspace deletes last added cursor
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace:
            if self.v_cursors:
                c = self.v_cursors.pop()
                c.remove()
            elif self.h_cursors:
                c = self.h_cursors.pop()
                c.remove()
            self.delta_annotation.update_text()

    # ---------- File Loading ----------
    def load_file(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Open Waveform Files", "", "CSV Files (*.csv);;RAW Files (*.raw)")
        if not file_paths:
            return
        for file_path in file_paths:
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
                time = df.iloc[:, 0].values
                data = df.iloc[:, 1:].values
                labels = [f"{file_path.split('/')[-1]}_{col}" for col in df.columns[1:]]
            elif file_path.endswith(".raw"):
                time, data, labels = self.parse_raw_multi(file_path)
            else:
                continue
            self.loaded_waveforms.append((time, data, labels, file_path))
        self.plot_all_waveforms()

    def parse_raw_multi(self, file_path):
        time = []
        values = []
        with open(file_path, "r") as f:
            for line in f:
                # skip header/comments typical in some RAW formats
                if line.strip() == "" or line.startswith("*") or line.lower().startswith("title") or line.lower().startswith("variables"):
                    continue
                parts = line.strip().split()
                if len(parts) > 1:
                    try:
                        time.append(float(parts[0]))
                        values.append([float(x) for x in parts[1:]])
                    except Exception:
                        # ignore lines that don't parse
                        pass
        data = np.array(values)
        labels = [f"{file_path.split('/')[-1]}_V{i}" for i in range(data.shape[1])]
        return np.array(time), data, labels

    # ---------- Plot ----------
    def plot_all_waveforms(self):
        self.ax.clear()
        self.time = None
        self.data = None
        self.labels = []
        for time_arr, data_arr, labels_arr, fname in self.loaded_waveforms:
            for i in range(data_arr.shape[1]):
                self.ax.plot(time_arr, data_arr[:, i], label=labels_arr[i])
            if self.time is None:
                self.time = time_arr
                self.data = data_arr
                self.labels = labels_arr.copy()
            else:
                # stack additional channels to the right
                self.data = np.hstack((self.data, data_arr))
                self.labels.extend(labels_arr)
        self.ax.legend()
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude")
        self.canvas.draw()
        self.original_xlim = self.ax.get_xlim()
        self.original_ylim = self.ax.get_ylim()
        # clear cursors when loading new data
        self.v_cursors.clear()
        self.h_cursors.clear()
        self.delta_annotation.update_text()
        self.status.showMessage("Waveform loaded")

    # ---------- Reset ----------
    def reset_view(self):
        if self.original_xlim and self.original_ylim:
            self.ax.set_xlim(self.original_xlim)
            self.ax.set_ylim(self.original_ylim)
            self.canvas.draw()

    # ---------- Hover Tooltip ----------
    def show_hover(self, event):
        if event.inaxes != self.ax or self.data is None:
            if self.tooltip.get_visible():
                self.tooltip.set_visible(False)
                self.canvas.draw_idle()
            return
        x = event.xdata
        if x is None:
            return
        idx = np.searchsorted(self.time, x)
        if idx >= len(self.time):
            idx = -1
        # prepare tooltip text
        try:
            y_values = [self.data[idx, i] for i in range(self.data.shape[1])]
        except Exception:
            return
        lines = [f"X={self.time[idx]:.6f}"]
        for i, lbl in enumerate(self.labels):
            lines.append(f"{lbl}={y_values[i]:.6f}")
        text = "\n".join(lines)
        self.tooltip.xy = (self.time[idx], y_values[0])
        self.tooltip.set_text(text)
        self.tooltip.set_visible(True)
        self.canvas.draw_idle()

    # ---------- Cursors ----------
    def add_v_cursor(self, x):
        line = self.ax.axvline(x, color='r', linestyle='--')
        cursor = DraggableCursor(line, 'v', self.ax, self.delta_annotation)
        self.v_cursors.append(cursor)
        self.delta_annotation.update_text()
        self.canvas.draw()

    def add_h_cursor(self, y):
        line = self.ax.axhline(y, color='b', linestyle='--')
        cursor = DraggableCursor(line, 'h', self.ax, self.delta_annotation)
        self.h_cursors.append(cursor)
        self.delta_annotation.update_text()
        self.canvas.draw()

    def add_vertical_cursor_button(self):
        x, ok = QInputDialog.getDouble(self, "Vertical Cursor", "Enter X value:")
        if ok:
            self.add_v_cursor(x)

    def add_horizontal_cursor_button(self):
        y, ok = QInputDialog.getDouble(self, "Horizontal Cursor", "Enter Y value:")
        if ok:
            self.add_h_cursor(y)

    # ---------- Expressions ----------
    def calculate_expression(self):
        if self.data is None:
            self.expr_output.append("No data loaded.")
            return
        expr = self.expr_input.text().strip()
        if not expr:
            self.expr_output.append("Enter an expression first.")
            return
        try:
            # local dict maps label -> array
            local_dict = {label: self.data[:, i] for i, label in enumerate(self.labels)}
            # evaluate expression safely-ish (note: eval can run arbitrary code; only use trusted expressions)
            result = eval(expr, {"np": np}, local_dict)
            result = np.asarray(result)
            if result.shape[0] != len(self.time):
                raise ValueError("Expression length does not match time axis")
            self.ax.plot(self.time, result, label=f"Expr: {expr}", color='magenta')
            self.ax.legend()
            self.canvas.draw()
            self.expr_output.append(f"Expression '{expr}' plotted successfully.")
        except Exception as e:
            self.expr_output.append(f"Error evaluating expression: {e}")

    # ---------- Analysis ----------
    def run_analysis(self):
        if self.data is None or len(self.v_cursors) < 2:
            QMessageBox.warning(self, "Warning", "Load waveform and place 2 vertical cursors first")
            return
        x1, x2 = sorted([self.v_cursors[0].line.get_xdata()[0], self.v_cursors[1].line.get_xdata()[0]])
        idx1 = np.searchsorted(self.time, x1)
        idx2 = np.searchsorted(self.time, x2)
        # clamp indices
        idx1 = max(0, min(idx1, len(self.time)-1))
        idx2 = max(0, min(idx2, len(self.time)))
        if idx2 <= idx1:
            QMessageBox.warning(self, "Warning", "Invalid cursor positions (ordered indices).")
            return
        metric = self.analysis_combo.currentText()
        output_lines = []
        segment = self.data[idx1:idx2]

        if metric == "Frequency":
            delta_t = x2 - x1
            freq = 1.0 / delta_t if delta_t != 0 else 0
            output_lines.append(f"Frequency: {freq:.6f} Hz")
        elif metric == "RMS":
            rms_values = np.sqrt(np.mean(segment**2, axis=0))
            output_lines.extend([f"{self.labels[i]} RMS: {rms_values[i]:.6f}" for i in range(len(rms_values))])
        elif metric == "Peak-to-Peak":
            ptp_values = np.ptp(segment, axis=0)
            output_lines.extend([f"{self.labels[i]} P2P: {ptp_values[i]:.6f}" for i in range(len(ptp_values))])
        elif metric == "Max":
            max_values = np.max(segment, axis=0)
            output_lines.extend([f"{self.labels[i]} Max: {max_values[i]:.6f}" for i in range(len(max_values))])
        elif metric == "Min":
            min_values = np.min(segment, axis=0)
            output_lines.extend([f"{self.labels[i]} Min: {min_values[i]:.6f}" for i in range(len(min_values))])
        elif metric == "Mean":
            mean_values = np.mean(segment, axis=0)
            output_lines.extend([f"{self.labels[i]} Mean: {mean_values[i]:.6f}" for i in range(len(mean_values))])
        elif metric == "Integral":
            integral_values = np.trapz(segment, self.time[idx1:idx2], axis=0)
            output_lines.extend([f"{self.labels[i]} Integral: {integral_values[i]:.6f}" for i in range(len(integral_values))])
        elif metric == "Delta X/Y":
            if len(self.v_cursors) >= 2 and len(self.h_cursors) >= 2:
                dx = abs(self.v_cursors[0].line.get_xdata()[0] - self.v_cursors[1].line.get_xdata()[0])
                dy = abs(self.h_cursors[0].line.get_ydata()[0] - self.h_cursors[1].line.get_ydata()[0])
                output_lines.append(f"Delta X: {dx:.6f}, Delta Y: {dy:.6f}")
            else:
                output_lines.append("Place 2 vertical and 2 horizontal cursors for Delta X/Y")
        else:
            output_lines.append(f"Unknown metric: {metric}")

        self.analysis_output.setPlainText("\n".join(output_lines))

    # ---------- Save ----------
    def save_waveform(self):
        if self.data is None:
            QMessageBox.warning(self, "Warning", "No waveform data to save")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Waveform CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time"] + self.labels)
            for i in range(len(self.time)):
                row = [self.time[i]] + [float(self.data[i, j]) for j in range(self.data.shape[1])]
                writer.writerow(row)
        QMessageBox.information(self, "Saved", f"Waveform saved to {path}")

    def save_analysis(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Analysis Results CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, 'w', newline='') as f:
            f.write(self.analysis_output.toPlainText())
        QMessageBox.information(self, "Saved", f"Analysis saved to {path}")

# ---------- Run ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = WaveformViewer()
    viewer.show()
    sys.exit(app.exec())
