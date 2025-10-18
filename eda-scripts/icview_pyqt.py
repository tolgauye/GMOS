import sys
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QDockWidget, QTabWidget, QLabel,
    QLineEdit, QTextEdit, QComboBox, QColorDialog, QSpinBox,
    QMessageBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg

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
        self.setWindowTitle("Advanced Waveform Viewer")
        self.resize(1600, 900)

        # ---------- Central Plot ----------
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True)
        self.main_layout.addWidget(self.plot_widget)

        # Toolbar buttons
        toolbar_layout = QHBoxLayout()
        self.main_layout.addLayout(toolbar_layout)

        self.load_btn = QPushButton("Load CSV/RAW")
        self.load_btn.clicked.connect(self.load_file)
        toolbar_layout.addWidget(self.load_btn)

        self.reset_btn = QPushButton("Reset View")
        self.reset_btn.clicked.connect(self.reset_view)
        toolbar_layout.addWidget(self.reset_btn)

        self.add_v_cursor_btn = QPushButton("Add Vertical Cursor")
        self.add_v_cursor_btn.clicked.connect(self.add_vertical_cursor)
        toolbar_layout.addWidget(self.add_v_cursor_btn)

        self.add_h_cursor_btn = QPushButton("Add Horizontal Cursor")
        self.add_h_cursor_btn.clicked.connect(self.add_horizontal_cursor)
        toolbar_layout.addWidget(self.add_h_cursor_btn)

        self.delete_cursor_btn = QPushButton("Delete Cursor")
        self.delete_cursor_btn.clicked.connect(self.delete_selected_cursor)
        toolbar_layout.addWidget(self.delete_cursor_btn)

        # ---------- Data ----------
        self.loaded_waveforms = []  # All loaded waveforms
        self.plot_data_items = []   # Currently plotted waveforms
        self.v_cursors = []
        self.h_cursors = []

        self.line_colors = {}
        self.selected_color = 'r'

        # ---------- Cursor text ----------
        self.dx_text = pg.TextItem(anchor=(0.5, 1.5), color='r')
        self.dy_text = pg.TextItem(anchor=(0,0), color='g')
        self.cursor_text = pg.TextItem(anchor=(0,1), color='b')
        self.plot_widget.addItem(self.dx_text)
        self.plot_widget.addItem(self.dy_text)
        self.plot_widget.addItem(self.cursor_text)
        self.dx_text.hide()
        self.dy_text.hide()
        self.cursor_text.hide()

        # ---------- Waveform Manager Dock ----------
        self.waveform_manager_dock = QDockWidget("Waveform Manager", self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.waveform_manager_dock)

        self.waveform_list = QListWidget()
        self.waveform_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.waveform_manager_dock.setWidget(self.waveform_list)

        # Plot & Delete buttons in manager dock
        self.plot_selected_btn = QPushButton("Plot Selected")
        self.plot_selected_btn.clicked.connect(self.plot_selected_waveforms)
        self.delete_selected_btn = QPushButton("Delete Selected")
        self.delete_selected_btn.clicked.connect(self.delete_selected_waveforms)
        manager_layout = QVBoxLayout()
        manager_layout.addWidget(self.plot_selected_btn)
        manager_layout.addWidget(self.delete_selected_btn)
        manager_layout.addStretch()
        manager_btn_widget = QWidget()
        manager_btn_widget.setLayout(manager_layout)
        self.waveform_manager_dock.setTitleBarWidget(manager_btn_widget)

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
        add_as_waveform_btn = QPushButton("Add Expression as Waveform")
        add_as_waveform_btn.clicked.connect(self.add_expression_waveform)
        expr_layout.addWidget(add_as_waveform_btn)

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

        # Keyboard shortcuts
        self.plot_widget.keyPressEvent = self.keyPressEvent
        self.plot_widget.scene().sigMouseMoved.connect(self.mouse_moved)

    # ---------- File Loading ----------
    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV/RAW", "", "CSV Files (*.csv);;RAW Files (*.raw)")
        if not file_path:
            return
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            time = df.iloc[:,0].values
            data = df.iloc[:,1:].values
            labels = list(df.columns[1:])
        elif file_path.endswith('.raw'):
            time, data, labels = self.parse_raw(file_path)
        else:
            return
        self.loaded_waveforms.append((time, data, labels))
        # Add items to waveform list
        for label in labels:
            self.waveform_list.addItem(QListWidgetItem(label))
        QMessageBox.information(self, "Loaded", f"File loaded: {file_path}\nWaveforms: {', '.join(labels)}")

    def parse_raw(self, filepath):
        time, values = [], []
        with open(filepath, 'r') as f:
            for line in f:
                if line.startswith('*') or line.startswith('Title') or line.startswith('Variables'):
                    continue
                parts = line.strip().split()
                if len(parts) > 1:
                    time.append(float(parts[0]))
                    values.append([float(x) for x in parts[1:]])
        data = np.array(values)
        labels = [f'V{i}' for i in range(data.shape[1])]
        return np.array(time), data, labels

    # ---------- Plot Selected Waveforms ----------
    def plot_selected_waveforms(self):
        selected_items = self.waveform_list.selectedItems()
        if not selected_items:
            return
        selected_labels = [item.text() for item in selected_items]

        # Clear previous plot but keep cursors
        for _, item, _, _ in self.plot_data_items:
            self.plot_widget.removeItem(item)
        self.plot_data_items.clear()
        self.waveform_select.clear()
        self.analysis_combo.clear()

        legend = pg.LegendItem((100,60), offset=(70,30))
        legend.setParentItem(self.plot_widget.graphicsItem())

        # Plot only selected waveforms
        for time, data, labels in self.loaded_waveforms:
            for i, label in enumerate(labels):
                if label in selected_labels:
                    color = self.line_colors.get(label, 'r')
                    pen = pg.mkPen(color=color, width=self.thickness_spin.value())
                    item = self.plot_widget.plot(time, data[:,i], pen=pen, name=label)
                    self.plot_data_items.append((label, item, time, data[:,i]))
                    legend.addItem(item, label)
                    self.waveform_select.addItem(label)
                    self.analysis_combo.addItem(label)
        self.update_cursor_measurements()

    # ---------- Delete Selected Waveforms ----------
    def delete_selected_waveforms(self):
        selected_items = self.waveform_list.selectedItems()
        if not selected_items:
            return
        selected_labels = [item.text() for item in selected_items]

        # Remove from plot
        self.plot_data_items = [(l,item,t,d) for l,item,t,d in self.plot_data_items if l not in selected_labels]
        for l, item, _, _ in self.plot_data_items:
            if l in selected_labels:
                self.plot_widget.removeItem(item)

        # Remove from loaded_waveforms
        new_loaded = []
        for time, data, labels in self.loaded_waveforms:
            keep_indices = [i for i,l in enumerate(labels) if l not in selected_labels]
            if keep_indices:
                new_data = data[:, keep_indices]
                new_labels = [labels[i] for i in keep_indices]
                new_loaded.append((time, new_data, new_labels))
        self.loaded_waveforms = new_loaded

        # Remove from list widget
        for item in selected_items:
            self.waveform_list.takeItem(self.waveform_list.row(item))

    # ---------- Reset View ----------
    def reset_view(self):
        self.plot_widget.enableAutoRange()

    # ---------- Cursor Management ----------
    def add_vertical_cursor(self):
        vline = pg.InfiniteLine(pos=0, angle=90, movable=True, pen=pg.mkPen('r', width=1))
        vline.sigPositionChanged.connect(self.update_cursor_measurements)
        self.plot_widget.addItem(vline)
        self.v_cursors.append(vline)
        self.update_cursor_measurements()

    def add_horizontal_cursor(self):
        hline = pg.InfiniteLine(pos=0, angle=0, movable=True, pen=pg.mkPen('g', width=1))
        hline.sigPositionChanged.connect(self.update_cursor_measurements)
        self.plot_widget.addItem(hline)
        self.h_cursors.append(hline)
        self.update_cursor_measurements()

    def delete_selected_cursor(self):
        if self.v_cursors:
            line = self.v_cursors.pop()
            self.plot_widget.removeItem(line)
        elif self.h_cursors:
            line = self.h_cursors.pop()
            self.plot_widget.removeItem(line)
        self.update_cursor_measurements()

    def update_cursor_measurements(self):
        if self.v_cursors or self.h_cursors:
            if len(self.v_cursors) >= 2:
                x1 = self.v_cursors[0].value()
                x2 = self.v_cursors[1].value()
                dx = abs(x2 - x1)
                self.dx_text.setText(f'ΔX = {dx:.6f} s')
                self.dx_text.setPos((x1+x2)/2, self.plot_widget.viewRange()[1][1]*0.95)
                self.dx_text.show()
            else:
                self.dx_text.hide()
            if len(self.h_cursors) >= 2:
                y1 = self.h_cursors[0].value()
                y2 = self.h_cursors[1].value()
                dy = abs(y2 - y1)
                self.dy_text.setText(f'ΔY = {dy:.6f} V')
                self.dy_text.setPos(self.plot_widget.viewRange()[0][0], (y1+y2)/2)
                self.dy_text.show()
            else:
                self.dy_text.hide()
        else:
            self.dx_text.hide()
            self.dy_text.hide()

    # ---------- Mouse Move ----------
    def mouse_moved(self, pos):
        if self.v_cursors or self.h_cursors:
            vb = self.plot_widget.getViewBox()
            if self.plot_widget.sceneBoundingRect().contains(pos):
                mouse_point = vb.mapSceneToView(pos)
                self.cursor_text.setText(f'X={mouse_point.x():.6f}, Y={mouse_point.y():.6f}')
                self.cursor_text.setPos(mouse_point.x(), mouse_point.y())
                self.cursor_text.show()
        else:
            self.cursor_text.hide()

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
                    local_dict[l] = data[:,i]
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
                    local_dict[l] = data[:,i]
            result = eval(expr, {}, local_dict)
            time = self.loaded_waveforms[0][0]
            new_label = f'Expr_{expr}'
            self.loaded_waveforms.append((time, result.reshape(-1,1), [new_label]))
            self.waveform_list.addItem(QListWidgetItem(new_label))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ---------- Analysis ----------
    def calculate_frequency(self):
        label = self.analysis_combo.currentText()
        for l, _, time, data in self.plot_data_items:
            if l == label:
                zero_crossings = np.where(np.diff(np.sign(data)))[0]
                if len(zero_crossings) > 1:
                    period = np.mean(np.diff(time[zero_crossings]))
                    freq = 1/period
                    QMessageBox.information(self, "Frequency", f"{freq:.3f} Hz")
                else:
                    QMessageBox.information(self, "Frequency", "Cannot calculate frequency (no zero crossings).")
                break

    def calculate_rms(self):
        label = self.analysis_combo.currentText()
        for l, _, _, data in self.plot_data_items:
            if l == label:
                rms = np.sqrt(np.mean(data**2))
                QMessageBox.information(self, "RMS", f"RMS = {rms:.6f}")
                break

    def calculate_peak_to_peak(self):
        label = self.analysis_combo.currentText()
        for l, _, _, data in self.plot_data_items:
            if l == label:
                ptp = np.ptp(data)
                QMessageBox.information(self, "Peak-to-Peak", f"Peak-to-Peak = {ptp:.6f}")
                break

# ---------- Run ----------
if __name__ == "__main__":
    generate_sample_csv()
    app = QApplication(sys.argv)
    viewer = WaveformViewer()
    viewer.show()
    sys.exit(app.exec())
