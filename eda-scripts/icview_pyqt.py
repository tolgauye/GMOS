# ...existing code...
import sys
import os
import math
import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QDockWidget, QTabWidget, QLabel,
    QLineEdit, QTextEdit, QComboBox, QColorDialog, QSpinBox,
    QMessageBox, QCheckBox, QListWidget, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
# ...existing code...

# SI-prefix AxisItem and formatter
class SIPrefixAxis(pg.AxisItem):
    """
    Axis that formats tick labels using SI prefixes (p, n, u, m, k, M, G).
    """
    PREFIX_MAP = {
        -12: 'p',
        -9:  'n',
        -6:  'u',
        -3:  'm',
         0:  '',
         3:  'k',
         6:  'M',
         9:  'G',
    }

    def __init__(self, orientation='bottom', **kwargs):
        super().__init__(orientation=orientation, **kwargs)

    def tickStrings(self, values, scale, spacing):
        strs = []
        for val in values:
            try:
                if val == 0 or not math.isfinite(val):
                    strs.append("0")
                    continue
                exp = int(math.floor(math.log10(abs(val))))
                exp3 = int(math.floor(exp / 3.0) * 3)
                if exp3 not in self.PREFIX_MAP:
                    strs.append(f"{val:.3e}")
                    continue
                factor = 10.0 ** exp3
                scaled = val / factor
                prefix = self.PREFIX_MAP[exp3]
                s = f"{scaled:.3g}"
                strs.append(f"{s}{prefix}")
            except Exception:
                strs.append(str(val))
        return strs

def format_si(val):
    """Format a single float with SI prefix (p, n, u, m, k, M, G) or scientific if outside range."""
    try:
        if val == 0 or not math.isfinite(val):
            return "0"
        exp = int(math.floor(math.log10(abs(val))))
        exp3 = int(math.floor(exp / 3.0) * 3)
        mapping = SIPrefixAxis.PREFIX_MAP
        if exp3 not in mapping:
            return f"{val:.3e}"
        factor = 10.0 ** exp3
        scaled = val / factor
        s = f"{scaled:.3g}"
        return f"{s}{mapping[exp3]}"
    except Exception:
        return str(val)

# ---------- Sample CSV Generator ----------
def generate_sample_csv(filename="sample_waveform.csv", points=1000):
    t = np.linspace(0, 1, points)
    v1 = np.sin(2 * np.pi * 5 * t)
    v2 = 0.5 * np.sin(2 * np.pi * 10 * t)
    df = pd.DataFrame({'Time': t, 'V1': v1, 'V2': v2})
    df.to_csv(filename, index=False)

# ---------- Waveform Viewer ----------
class WaveformViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Professional Waveform Viewer")
        self.resize(1600, 900)

        # Data
        self.loaded_waveforms = []  # list of tuples: (time, data, labels)
        self.plot_data_items = []   # list of tuples: (label, item, time, data)
        self.v_cursors = []
        self.h_cursors = []
        self.line_colors = {}
        # default waveform color -> black for visibility on white background
        self.selected_color = '#000000'
        self.subplots = {}  # label -> (dock, plotwidget, time, data, pen)

        # cursor defaults
        self.cursor_default_thickness = 2

        # Central plot
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        pg.setConfigOptions(antialias=True)
        # Use SI-prefixed axes so tick labels display with p, n, u, m, k, M, ...
        xaxis = SIPrefixAxis(orientation='bottom')
        yaxis = SIPrefixAxis(orientation='left')
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': xaxis, 'left': yaxis}, background='w')
        self.plot_widget.showGrid(x=True, y=True)
        self.main_layout.addWidget(self.plot_widget)

        # Top toolbar
        toolbar_layout = QHBoxLayout()
        self.main_layout.addLayout(toolbar_layout)
        reset_btn = QPushButton("Reset View")
        reset_btn.clicked.connect(self.reset_view)
        toolbar_layout.addWidget(reset_btn)
        add_v_cursor_btn = QPushButton("Add Vertical Cursor (V)")
        add_v_cursor_btn.clicked.connect(self.add_vertical_cursor)
        toolbar_layout.addWidget(add_v_cursor_btn)
        add_h_cursor_btn = QPushButton("Add Horizontal Cursor (H)")
        add_h_cursor_btn.clicked.connect(self.add_horizontal_cursor)
        toolbar_layout.addWidget(add_h_cursor_btn)
        delete_cursor_btn = QPushButton("Delete Cursor (Backspace)")
        delete_cursor_btn.clicked.connect(self.delete_selected_cursor)
        toolbar_layout.addWidget(delete_cursor_btn)
        split_btn = QPushButton("Split Selected")
        split_btn.clicked.connect(self.split_selected_waveforms)
        toolbar_layout.addWidget(split_btn)
        restore_btn = QPushButton("Restore All Splits")
        restore_btn.clicked.connect(self.restore_all_splits)
        toolbar_layout.addWidget(restore_btn)

        # Cursor text items (use black text for white bg)
        self.dx_text = pg.TextItem(anchor=(0.5, 1.5), color='#000000')
        self.dy_text = pg.TextItem(anchor=(0, 0), color='#000000')
        self.cursor_text = pg.TextItem(anchor=(0, 1), color='#000000')
        qfont = QFont("Arial", 9)
        self.dx_text.setFont(qfont)
        self.dy_text.setFont(qfont)
        self.cursor_text.setFont(qfont)
        self.dx_text.setZValue(100)
        self.dy_text.setZValue(100)
        self.cursor_text.setZValue(100)
        self.plot_widget.addItem(self.dx_text)
        self.plot_widget.addItem(self.dy_text)
        self.plot_widget.addItem(self.cursor_text)
        self.dx_text.hide()
        self.dy_text.hide()
        self.cursor_text.hide()

        # ---------- Waveform Manager Top Dock (compact) ----------
        self.waveform_manager_dock = QDockWidget("Waveform Manager", self)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.waveform_manager_dock)

        manager_widget = QWidget()
        manager_layout = QVBoxLayout()
        manager_layout.setContentsMargins(6, 6, 6, 6)
        manager_widget.setLayout(manager_layout)

        top_row = QHBoxLayout()
        self.load_btn = QPushButton("Load CSV/RAW")
        self.load_btn.clicked.connect(self.load_file)
        top_row.addWidget(self.load_btn)

        self.append_checkbox = QCheckBox("Append")
        self.append_checkbox.setToolTip("If unchecked, a new load replaces existing data")
        top_row.addWidget(self.append_checkbox)

        self.loaded_file_combo = QComboBox()
        self.loaded_file_combo.setMinimumWidth(220)
        top_row.addWidget(self.loaded_file_combo)

        self.loaded_waveform_combo = QComboBox()
        self.loaded_waveform_combo.setMinimumWidth(200)
        top_row.addWidget(self.loaded_waveform_combo)

        self.plot_btn = QPushButton("Plot Selected")
        self.plot_btn.clicked.connect(self.plot_selected_waveform)
        top_row.addWidget(self.plot_btn)

        manager_layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        self.plotted_list = QListWidget()
        self.plotted_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.plotted_list.setMinimumWidth(320)
        bottom_row.addWidget(self.plotted_list)

        btns = QVBoxLayout()
        self.remove_plot_btn = QPushButton("Remove Selected")
        self.remove_plot_btn.clicked.connect(self.delete_selected_plotted_from_list)
        btns.addWidget(self.remove_plot_btn)
        self.split_btn = QPushButton("Split Selected")
        self.split_btn.clicked.connect(self.split_selected_waveforms)
        btns.addWidget(self.split_btn)

        self.split_list = QListWidget()
        self.split_list.setMaximumHeight(100)
        btns.addWidget(QLabel("Split windows:"))
        btns.addWidget(self.split_list)

        self.restore_selected_btn = QPushButton("Restore Selected")
        self.restore_selected_btn.clicked.connect(self.restore_selected_splits)
        btns.addWidget(self.restore_selected_btn)

        bottom_row.addLayout(btns)
        manager_layout.addLayout(bottom_row)

        self.waveform_manager_dock.setWidget(manager_widget)

        # ---------- Control Dock (Expressions, Analysis, Settings) ----------
        self.dock = QDockWidget("Controls", self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.tabs = QTabWidget()
        self.dock.setWidget(self.tabs)

        # Expressions Tab
        self.expr_tab = QWidget()
        self.tabs.addTab(self.expr_tab, "Expressions")
        expr_layout = QVBoxLayout()
        self.expr_tab.setLayout(expr_layout)
        self.expr_input = QLineEdit()
        self.expr_input.setPlaceholderText("Enter expression e.g., V1+V2")
        expr_layout.addWidget(self.expr_input)
        self.expr_output = QTextEdit()
        self.expr_output.setReadOnly(True)
        expr_layout.addWidget(self.expr_output)
        eval_btn = QPushButton("Evaluate Expression")
        eval_btn.clicked.connect(self.evaluate_expression)
        expr_layout.addWidget(eval_btn)
        add_expr_btn = QPushButton("Add Expression as Waveform")
        add_expr_btn.clicked.connect(self.add_expression_waveform)
        expr_layout.addWidget(add_expr_btn)

        # Analysis Tab
        self.analysis_tab = QWidget()
        self.tabs.addTab(self.analysis_tab, "Analysis")
        analysis_layout = QVBoxLayout()
        self.analysis_tab.setLayout(analysis_layout)
        self.analysis_combo = QComboBox()
        analysis_layout.addWidget(QLabel("Select waveform for analysis:"))
        analysis_layout.addWidget(self.analysis_combo)
        freq_btn = QPushButton("Frequency (Hz)")
        freq_btn.clicked.connect(self.calculate_frequency)
        analysis_layout.addWidget(freq_btn)
        rms_btn = QPushButton("RMS")
        rms_btn.clicked.connect(self.calculate_rms)
        analysis_layout.addWidget(rms_btn)
        ptp_btn = QPushButton("Peak-to-Peak")
        ptp_btn.clicked.connect(self.calculate_peak_to_peak)
        analysis_layout.addWidget(ptp_btn)

        # Plot Settings Tab
        self.settings_tab = QWidget()
        self.tabs.addTab(self.settings_tab, "Plot Settings")
        settings_layout = QVBoxLayout()
        self.settings_tab.setLayout(settings_layout)
        self.waveform_select = QComboBox()
        settings_layout.addWidget(QLabel("Select waveform to modify:"))
        settings_layout.addWidget(self.waveform_select)
        self.color_btn = QPushButton("Select Line Color")
        self.color_btn.clicked.connect(self.select_color)
        settings_layout.addWidget(self.color_btn)
        self.thickness_spin = QSpinBox()
        self.thickness_spin.setRange(1, 10)
        self.thickness_spin.setValue(1)
        self.thickness_spin.setPrefix("Thickness: ")
        settings_layout.addWidget(self.thickness_spin)

        # Cursor thickness control (visibility improvement)
        self.cursor_thickness_spin = QSpinBox()
        self.cursor_thickness_spin.setRange(1, 10)
        self.cursor_thickness_spin.setValue(self.cursor_default_thickness)
        settings_layout.addWidget(QLabel("Cursor thickness:"))
        settings_layout.addWidget(self.cursor_thickness_spin)

        apply_style_btn = QPushButton("Apply Style")
        apply_style_btn.clicked.connect(self.apply_style)
        settings_layout.addWidget(apply_style_btn)
        self.xaxis_input = QLineEdit()
        self.xaxis_input.setPlaceholderText("Enter X-axis label")
        settings_layout.addWidget(QLabel("X-axis label:"))
        settings_layout.addWidget(self.xaxis_input)
        self.yaxis_input = QLineEdit()
        self.yaxis_input.setPlaceholderText("Enter Y-axis label")
        settings_layout.addWidget(QLabel("Y-axis label:"))
        settings_layout.addWidget(self.yaxis_input)
        axis_apply_btn = QPushButton("Apply Axis Labels")
        axis_apply_btn.clicked.connect(self.apply_axis_labels)
        settings_layout.addWidget(axis_apply_btn)

        # Keyboard and mouse
        self.plot_widget.keyPressEvent = self.keyPressEvent
        self.plot_widget.scene().sigMouseMoved.connect(self.mouse_moved)

    # ---------- Clear all loaded waveforms ----------
    def clear_loaded_waveforms(self):
        self.loaded_waveforms.clear()
        self.plot_data_items.clear()
        self.loaded_waveform_combo.clear()
        self.plotted_list.clear()
        # Keep plotted_waveform_combo for backward compatibility if present
        try:
            self.plotted_waveform_combo.clear()
        except Exception:
            pass
        self.waveform_select.clear()
        self.analysis_combo.clear()
        self.plot_widget.clear()
        # remove cursor lines
        for v in list(self.v_cursors):
            try:
                self.plot_widget.removeItem(v)
            except Exception:
                pass
        for h in list(self.h_cursors):
            try:
                self.plot_widget.removeItem(h)
            except Exception:
                pass
        self.v_cursors = []
        self.h_cursors = []
        self.dx_text.hide()
        self.dy_text.hide()
        self.cursor_text.hide()
        # remove any split docks
        for key, entry in list(self.subplots.items()):
            dock = entry[0]
            try:
                self.removeDockWidget(dock)
            except Exception:
                try:
                    dock.setParent(None)
                except Exception:
                    pass
        self.subplots = {}
        self.split_list.clear()
        self.loaded_file_combo.clear()

    # ---------- File Loading ----------
    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV/RAW", "", "CSV Files (*.csv);;RAW Files (*.raw);;All Files (*)")
        if not file_path:
            return
        # If not append, clear previous
        if not getattr(self, 'append_checkbox', None) or not self.append_checkbox.isChecked():
            self.clear_loaded_waveforms()

        file_base = os.path.splitext(os.path.basename(file_path))[0]
        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
            time = df.iloc[:, 0].values
            data = df.iloc[:, 1:].values
            labels = list(df.columns[1:])
        elif file_path.lower().endswith('.raw'):
            time, data, labels = self.parse_raw(file_path)
        else:
            QMessageBox.information(self, "Load", "Unsupported file type")
            return

        # if append, prefix labels with filename to avoid collisions
        if getattr(self, 'append_checkbox', None) and self.append_checkbox.isChecked():
            labels = [f"{file_base}_{lab}" for lab in labels]

        self.loaded_waveforms.append((time, data, labels))
        self.loaded_file_combo.addItem(os.path.basename(file_path))
        for label in labels:
            self.loaded_waveform_combo.addItem(label)
        QMessageBox.information(self, "Loaded", f"File loaded: {file_path}\nWaveforms: {', '.join(labels)}")

    def parse_raw(self, filepath):
        time = []
        values = []
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('*') or line.lower().startswith('title') or line.lower().startswith('variables'):
                    continue
                parts = line.split()
                try:
                    t = float(parts[0])
                    nums = [float(x) for x in parts[1:]]
                except Exception:
                    continue
                time.append(t)
                values.append(nums)
        if len(values) == 0:
            return np.array([]), np.array([[]]), []
        data = np.array(values)
        labels = [f'V{i+1}' for i in range(data.shape[1])]
        return np.array(time), data, labels

    # ---------- Plot Selected ----------
    def plot_selected_waveform(self):
        label = self.loaded_waveform_combo.currentText()
        if not label:
            return
        for time, data, labels in self.loaded_waveforms:
            if label in labels:
                idx = labels.index(label)
                y = data[:, idx]
                color = self.line_colors.get(label, self.selected_color)
                pen = pg.mkPen(color=color, width=self.thickness_spin.value())
                item = self.plot_widget.plot(time, y, pen=pen, name=label)
                self.plot_data_items.append((label, item, time, y))
                self.plotted_list.addItem(label)
                # keep combos consistent
                try:
                    self.plotted_waveform_combo.addItem(label)
                except Exception:
                    pass
                self.waveform_select.addItem(label)
                self.analysis_combo.addItem(label)
                return

    # ---------- Remove plotted selections ----------
    def delete_selected_plotted_from_list(self):
        items = self.plotted_list.selectedItems()
        if not items:
            QMessageBox.information(self, "Remove", "No plotted waveform selected")
            return
        for it in items:
            label = it.text()
            new_plot_items = []
            for l, item, t, d in self.plot_data_items:
                if l == label:
                    try:
                        self.plot_widget.removeItem(item)
                    except Exception:
                        pass
                    # remove from combos
                    try:
                        i = self.plotted_waveform_combo.findText(label)
                        if i >= 0:
                            self.plotted_waveform_combo.removeItem(i)
                    except Exception:
                        pass
                    idx_ws = self.waveform_select.findText(label)
                    if idx_ws >= 0:
                        self.waveform_select.removeItem(idx_ws)
                    idx_a = self.analysis_combo.findText(label)
                    if idx_a >= 0:
                        self.analysis_combo.removeItem(idx_a)
                else:
                    new_plot_items.append((l, item, t, d))
            self.plot_data_items = new_plot_items
            row = self.plotted_list.row(it)
            self.plotted_list.takeItem(row)

    # ---------- Reset View ----------
    def reset_view(self):
        self.plot_widget.enableAutoRange()

    # ---------- Cursor Management ----------
    def add_vertical_cursor(self):
        # vertical cursor default color -> black
        pen = pg.mkPen('#000000', width=getattr(self, 'cursor_thickness_spin', None) and self.cursor_thickness_spin.value() or self.cursor_default_thickness)
        vline = pg.InfiniteLine(pos=0, angle=90, movable=True, pen=pen)
        vline.sigPositionChanged.connect(self.update_cursor_measurements)
        self.plot_widget.addItem(vline)
        self.v_cursors.append(vline)
        self.update_cursor_measurements()

    def add_horizontal_cursor(self):
        # horizontal cursor default color -> black
        pen = pg.mkPen('#000000', width=getattr(self, 'cursor_thickness_spin', None) and self.cursor_thickness_spin.value() or self.cursor_default_thickness)
        hline = pg.InfiniteLine(pos=0, angle=0, movable=True, pen=pen)
        hline.sigPositionChanged.connect(self.update_cursor_measurements)
        self.plot_widget.addItem(hline)
        self.h_cursors.append(hline)
        self.update_cursor_measurements()

    def delete_selected_cursor(self):
        # prefer deleting last vertical first (stack behavior)
        if self.v_cursors:
            line = self.v_cursors.pop()
            try:
                self.plot_widget.removeItem(line)
            except Exception:
                pass
        elif self.h_cursors:
            line = self.h_cursors.pop()
            try:
                self.plot_widget.removeItem(line)
            except Exception:
                pass
        self.update_cursor_measurements()

    def update_cursor_measurements(self):
        # hide defaults
        self.dx_text.hide()
        self.dy_text.hide()
        # helper to compute y for each plotted waveform at x (interpolate)
        def y_values_at_x(x):
            vals = []
            for l, item, t, d in self.plot_data_items:
                try:
                    if len(t) > 1:
                        yv = np.interp(float(x), np.asarray(t).astype(float), np.asarray(d).astype(float))
                        vals.append((l, yv))
                except Exception:
                    # skip any invalid series
                    continue
            return vals

        # Vertical cursors
        if len(self.v_cursors) >= 1:
            x0 = float(self.v_cursors[0].value())
            vals = y_values_at_x(x0)
            if vals:
                text = f"X={format_si(x0)}\n" + "\n".join([f"{l}: {format_si(y)}" for l, y in vals])
            else:
                text = f"X={format_si(x0)}"
            vr = self.plot_widget.viewRange()
            y_top = vr[1][1] if vr and len(vr) > 1 else 0
            self.cursor_text.setText(text)
            self.cursor_text.setPos(x0, y_top)
            self.cursor_text.show()
        if len(self.v_cursors) >= 2:
            x1 = float(self.v_cursors[0].value())
            x2 = float(self.v_cursors[1].value())
            dx = abs(x2 - x1)
            vr = self.plot_widget.viewRange()
            y_top = vr[1][1] if vr and len(vr) > 1 else 0
            self.dx_text.setText(f'ΔX = {format_si(dx)}')
            self.dx_text.setPos((x1 + x2) / 2, y_top * 0.95)
            self.dx_text.show()

        # Horizontal cursors
        if len(self.h_cursors) >= 1:
            y0 = float(self.h_cursors[0].value())
            vr = self.plot_widget.viewRange()
            x_left = vr[0][0] if vr and len(vr) > 0 else 0
            self.dy_text.setText(f"Y={format_si(y0)}")
            # Position label slightly to the right so it does not overlap the axis
            self.dy_text.setPos(x_left + (vr[0][1] - vr[0][0]) * 0.005 if vr else x_left, y0)
            self.dy_text.show()
        if len(self.h_cursors) >= 2:
            y1 = float(self.h_cursors[0].value())
            y2 = float(self.h_cursors[1].value())
            dy = abs(y2 - y1)
            vr = self.plot_widget.viewRange()
            x_left = vr[0][0] if vr and len(vr) > 0 else 0
            self.dy_text.setText(f'ΔY = {format_si(dy)}')
            self.dy_text.setPos(x_left + (vr[0][1] - vr[0][0]) * 0.005 if vr else x_left, (y1 + y2) / 2)
            self.dy_text.show()

        # If both vertical and horizontal exist, show intersection comparisons
        if (self.v_cursors and self.h_cursors):
            x = float(self.v_cursors[0].value())
            y = float(self.h_cursors[0].value())
            vals = y_values_at_x(x)
            inter_text = f"X={format_si(x)}, Y={format_si(y)}\n"
            if vals:
                inter_text += "\n".join([f"{l}: Y_at_X={format_si(yval)}, Δ={format_si(yval - y)}" for l, yval in vals])
            self.cursor_text.setText(inter_text)
            vr = self.plot_widget.viewRange()
            self.cursor_text.setPos(x, vr[1][1] if vr and len(vr) > 1 else y)
            self.cursor_text.show()

    # ---------- Mouse Move ----------
    def mouse_moved(self, pos):
        vb = self.plot_widget.getViewBox()
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            return
        mouse_point = vb.mapSceneToView(pos)
        x = mouse_point.x()
        y = mouse_point.y()
        # show mouse coordinates and nearest values for a few plotted waveforms
        info = [f"x={format_si(x)}, y={format_si(y)}"]
        for l, item, t, d in self.plot_data_items[:6]:
            try:
                if len(t) > 1:
                    yv = np.interp(float(x), np.asarray(t).astype(float), np.asarray(d).astype(float))
                    info.append(f"{l}: {format_si(yv)}")
            except Exception:
                continue
        self.cursor_text.setText("\n".join(info))
        # ensure cursor text visible above plot and slightly offset for readability
        self.cursor_text.setPos(x, y)
        self.cursor_text.show()
        # also refresh cursor-derived measurements (if any cursor lines present)
        self.update_cursor_measurements()

    # ---------- Keyboard Shortcuts ----------
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_V:
            self.add_vertical_cursor()
        elif event.key() == Qt.Key.Key_H:
            self.add_horizontal_cursor()
        elif event.key() == Qt.Key.Key_Backspace:
            self.delete_selected_cursor()
        elif event.key() == Qt.Key.Key_R:
            self.reset_view()
        else:
            super().keyPressEvent(event)

    # ---------- Plot Style ----------
    def select_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color.name()

    def apply_style(self):
        label = self.waveform_select.currentText()
        for l, item, _, _ in self.plot_data_items:
            if l == label:
                item.setPen(pg.mkPen(self.selected_color, width=self.thickness_spin.value()))
                self.line_colors[label] = self.selected_color
                break

    # ---------- Axis Labels ----------
    def apply_axis_labels(self):
        x_label = self.xaxis_input.text()
        y_label = self.yaxis_input.text()
        if x_label:
            self.plot_widget.setLabel('bottom', x_label)
        if y_label:
            self.plot_widget.setLabel('left', y_label)

    # ---------- Expression Evaluation ----------
    def evaluate_expression(self):
        expr = self.expr_input.text()
        if not expr:
            return
        try:
            local_dict = {}
            for _, data, labels in self.loaded_waveforms:
                for i, l in enumerate(labels):
                    local_dict[l] = data[:, i]
            result = eval(expr, {}, local_dict)
            self.expr_output.setPlainText(str(result))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def add_expression_waveform(self):
        expr = self.expr_input.text()
        if not expr:
            return
        try:
            local_dict = {}
            for _, data, labels in self.loaded_waveforms:
                for i, l in enumerate(labels):
                    local_dict[l] = data[:, i]
            result = eval(expr, {}, local_dict)
            time = self.loaded_waveforms[0][0]
            new_label = f'Expr_{expr}'
            arr = np.asarray(result).reshape(-1, 1)
            self.loaded_waveforms.append((time, arr, [new_label]))
            self.loaded_waveform_combo.addItem(new_label)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ---------- Analysis ----------
    def calculate_frequency(self):
        label = self.analysis_combo.currentText()
        for l, _, time, data in self.plot_data_items:
            if l == label:
                zero_crossings = np.where(np.diff(np.sign(data)))[0]
                if len(zero_crossings) > 1:
                    periods = np.diff(time[zero_crossings])
                    if len(periods) > 0 and np.mean(periods) != 0:
                        freq = 1.0 / np.mean(periods)
                        QMessageBox.information(self, "Frequency", f"{freq:.3f} Hz")
                        return
                QMessageBox.information(self, "Frequency", "Cannot calculate frequency (no zero crossings).")
                return

    def calculate_rms(self):
        label = self.analysis_combo.currentText()
        for l, _, _, data in self.plot_data_items:
            if l == label:
                rms = np.sqrt(np.mean(data**2))
                QMessageBox.information(self, "RMS", f"RMS = {rms:.6f}")
                return

    def calculate_peak_to_peak(self):
        label = self.analysis_combo.currentText()
        for l, _, _, data in self.plot_data_items:
            if l == label:
                ptp = np.ptp(data)
                QMessageBox.information(self, "Peak-to-Peak", f"Peak-to-Peak = {ptp:.6f}")
                return

    # ---------- Split / Restore ----------
    def split_selected_waveforms(self):
        items = self.plotted_list.selectedItems()
        if not items:
            QMessageBox.information(self, "Split", "No plotted waveform selected")
            return
        for it in list(items):
            label = it.text()
            for idx, (l, item, t, d) in enumerate(list(self.plot_data_items)):
                if l == label:
                    # remove from main plot
                    try:
                        self.plot_widget.removeItem(item)
                    except Exception:
                        pass
                    # preserve pen if available
                    try:
                        pen = item.opts.get('pen', pg.mkPen(self.selected_color))
                    except Exception:
                        pen = pg.mkPen(self.selected_color)
                    dock = QDockWidget(f"Wave: {label}", self)
                    # use SI prefixed axes for split window too
                    xaxis = SIPrefixAxis(orientation='bottom')
                    yaxis = SIPrefixAxis(orientation='left')
                    pw = pg.PlotWidget(axisItems={'bottom': xaxis, 'left': yaxis}, background='w')
                    pw.plot(t, d, pen=pen, name=label)
                    dock.setWidget(pw)
                    self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
                    self.subplots[label] = (dock, pw, t, d, pen)
                    # remove from internal structures and UI lists
                    self.plot_data_items = [pd for pd in self.plot_data_items if pd[0] != label]
                    # remove combos
                    try:
                        i = self.plotted_waveform_combo.findText(label)
                        if i >= 0:
                            self.plotted_waveform_combo.removeItem(i)
                    except Exception:
                        pass
                    idx_ws = self.waveform_select.findText(label)
                    if idx_ws >= 0:
                        self.waveform_select.removeItem(idx_ws)
                    idx_a = self.analysis_combo.findText(label)
                    if idx_a >= 0:
                        self.analysis_combo.removeItem(idx_a)
                    # update lists
                    row = self.plotted_list.row(it)
                    self.plotted_list.takeItem(row)
                    self.split_list.addItem(label)
                    break
        QMessageBox.information(self, "Split", "Selected waveform(s) moved to their own window(s)")

    def restore_selected_splits(self):
        items = self.split_list.selectedItems()
        if not items:
            QMessageBox.information(self, "Restore", "No split waveform selected")
            return
        for it in list(items):
            label = it.text()
            entry = self.subplots.get(label)
            if not entry:
                continue
            dock, pw, t, d, pen = entry
            try:
                self.removeDockWidget(dock)
            except Exception:
                try:
                    dock.setParent(None)
                except Exception:
                    pass
            item = self.plot_widget.plot(t, d, pen=pen, name=label)
            self.plot_data_items.append((label, item, t, d))
            self.plotted_list.addItem(label)
            try:
                self.plotted_waveform_combo.addItem(label)
            except Exception:
                pass
            self.waveform_select.addItem(label)
            self.analysis_combo.addItem(label)
            del self.subplots[label]
            row = self.split_list.row(it)
            self.split_list.takeItem(row)
        QMessageBox.information(self, "Restore", "Selected split waveform(s) restored to main plot")

    def restore_all_splits(self):
        labels = list(self.subplots.keys())
        for label in labels:
            entry = self.subplots.get(label)
            if not entry:
                continue
            dock, pw, t, d, pen = entry
            try:
                self.removeDockWidget(dock)
            except Exception:
                try:
                    dock.setParent(None)
                except Exception:
                    pass
            item = self.plot_widget.plot(t, d, pen=pen, name=label)
            self.plot_data_items.append((label, item, t, d))
            self.plotted_list.addItem(label)
            try:
                self.plotted_waveform_combo.addItem(label)
            except Exception:
                pass
            self.waveform_select.addItem(label)
            self.analysis_combo.addItem(label)
            # remove from split_list if present
            matches = self.split_list.findItems(label, Qt.MatchFlag.MatchExactly)
            for m in matches:
                self.split_list.takeItem(self.split_list.row(m))
            del self.subplots[label]
        QMessageBox.information(self, "Restore", "All split waveform(s) restored to main plot")


# ---------- Run ----------
if __name__ == "__main__":
    generate_sample_csv()
    app = QApplication(sys.argv)
    viewer = WaveformViewer()
    viewer.show()
    sys.exit(app.exec())
