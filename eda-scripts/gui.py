from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QComboBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QTextEdit, QFormLayout, QGroupBox,
    QFileDialog, QListWidget, QMessageBox, QScrollArea
)
import sys
import os

class SpiceGenerator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SPICE Netlist Generator")
        self.setMinimumSize(1000, 600)
        self.imported_netlist = ""
        self.stimuli_list = []
        self.initUI()

    # ===== Helper to clear layout =====
    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # ===== Dynamic Stimuli Parameters =====
    def update_stimuli_params(self):
        self.clear_layout(self.stimuli_form)
        source = self.source_type_combo.currentText()
        params = []
        if source == "PULSE":
            params = ["V_initial", "V_on", "delay", "rise_time", "fall_time", "pulse_width", "period"]
        elif source == "PWL":
            params = ["Time-Voltage Pairs (t1 v1 t2 v2 ...)"]
        elif source == "VDC":
            params = ["Voltage"]
        elif source == "VAC":
            params = ["Amplitude", "Frequency", "Phase"]
        elif source == "IDC":
            params = ["Current"]

        self.param_widgets = {}
        for p in params:
            le = QLineEdit()
            self.stimuli_form.addRow(f"{p}:", le)
            self.param_widgets[p] = le

    # ===== Dynamic Analysis Parameters =====
    def update_analysis_params(self):
        self.clear_layout(self.analysis_form)
        analysis = self.analysis_type_combo.currentText()
        self.analysis_widgets = {}
        if analysis == "Transient":
            for p in ["Stop Time", "Time Step", "Max Step", "Min Step"]:
                le = QLineEdit()
                self.analysis_form.addRow(f"{p}:", le)
                self.analysis_widgets[p] = le
        elif analysis == "DC":
            for p in ["Start Value", "Stop Value", "Step"]:
                le = QLineEdit()
                self.analysis_form.addRow(f"{p}:", le)
                self.analysis_widgets[p] = le

    # ===== UI Setup =====
    def initUI(self):
        main_layout = QHBoxLayout()

        # ===== Analysis Section =====
        analysis_group = QGroupBox("Analysis")
        analysis_layout = QVBoxLayout()
        self.analysis_type_combo = QComboBox()
        self.analysis_type_combo.addItems(["Transient", "DC"])
        self.analysis_type_combo.currentTextChanged.connect(self.update_analysis_params)
        analysis_layout.addWidget(QLabel("Analysis Type:"))
        analysis_layout.addWidget(self.analysis_type_combo)
        self.analysis_form = QFormLayout()
        analysis_layout.addLayout(self.analysis_form)
        analysis_group.setLayout(analysis_layout)
        main_layout.addWidget(analysis_group, 1)

        # ===== Stimuli Section =====
        stimuli_group = QGroupBox("Stimuli")
        stimuli_layout = QVBoxLayout()
        self.source_type_combo = QComboBox()
        self.source_type_combo.addItems(["PULSE", "PWL", "VDC", "VAC", "IDC"])
        self.source_type_combo.currentTextChanged.connect(self.update_stimuli_params)
        stimuli_layout.addWidget(QLabel("Stimuli Type:"))
        stimuli_layout.addWidget(self.source_type_combo)

        self.source_name_input = QLineEdit()
        stimuli_layout.addWidget(QLabel("Source Name:"))
        stimuli_layout.addWidget(self.source_name_input)

        self.node_input = QLineEdit()
        stimuli_layout.addWidget(QLabel("Node:"))
        stimuli_layout.addWidget(self.node_input)

        # Scrollable parameters
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.stimuli_form = QFormLayout(scroll_content)
        scroll_content.setLayout(self.stimuli_form)
        self.scroll_area.setWidget(scroll_content)
        stimuli_layout.addWidget(self.scroll_area, stretch=1)

        # Add/remove buttons
        self.add_stimuli_btn = QPushButton("Add Stimuli")
        self.add_stimuli_btn.clicked.connect(self.add_stimuli)
        stimuli_layout.addWidget(self.add_stimuli_btn)

        self.remove_stimuli_btn = QPushButton("Remove Selected Stimuli")
        self.remove_stimuli_btn.clicked.connect(self.remove_selected_stimuli)
        stimuli_layout.addWidget(self.remove_stimuli_btn)

        # Stimuli list
        self.stimuli_list_widget = QListWidget()
        stimuli_layout.addWidget(self.stimuli_list_widget, stretch=1)
        stimuli_group.setLayout(stimuli_layout)
        main_layout.addWidget(stimuli_group, 2)

        # ===== Bottom: Netlist Display & Buttons =====
        bottom_layout = QVBoxLayout()
        self.import_btn = QPushButton("Import Netlist")
        self.import_btn.clicked.connect(self.import_netlist)
        bottom_layout.addWidget(self.import_btn)

        self.generate_btn = QPushButton("Generate/Append Netlist")
        self.generate_btn.clicked.connect(self.generate_netlist)
        bottom_layout.addWidget(self.generate_btn)

        self.netlist_text = QTextEdit()
        bottom_layout.addWidget(self.netlist_text, stretch=1)

        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.clicked.connect(self.copy_netlist)
        bottom_layout.addWidget(self.copy_btn)

        overall_layout = QVBoxLayout()
        overall_layout.addLayout(main_layout, stretch=3)
        overall_layout.addLayout(bottom_layout, stretch=2)
        self.setLayout(overall_layout)

        # Initialize forms
        self.update_stimuli_params()
        self.update_analysis_params()

    # ===== Add Stimuli =====
    def add_stimuli(self):
        source_type = self.source_type_combo.currentText()
        source_name = self.source_name_input.text().strip()
        node = self.node_input.text().strip()

        if not source_name or not node:
            QMessageBox.warning(self, "Input Error", "Please enter source name and node.")
            return

        stim = {"type": source_type, "name": source_name, "node": node, "params": {}}
        for key, widget in self.param_widgets.items():
            stim["params"][key] = widget.text().strip()

        self.stimuli_list.append(stim)
        self.stimuli_list_widget.addItem(f"{source_name} ({source_type}) -> {node}")

        # Clear inputs for next stimuli
        self.source_name_input.clear()
        self.node_input.clear()
        for w in self.param_widgets.values():
            w.clear()

    # ===== Remove Selected Stimuli =====
    def remove_selected_stimuli(self):
        selected_items = self.stimuli_list_widget.selectedIndexes()
        for index in reversed(selected_items):
            self.stimuli_list.pop(index.row())
            self.stimuli_list_widget.takeItem(index.row())

    # ===== Import Netlist =====
    def import_netlist(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Netlist", "", "SPICE Files (*.cir *.sp *.net)")
        if file_name and os.path.isfile(file_name):
            with open(file_name, "r") as f:
                self.imported_netlist = f.read()
            self.netlist_text.setPlainText(self.imported_netlist)

    # ===== Generate/Append Netlist =====
    def generate_netlist(self):
        netlist = self.imported_netlist if self.imported_netlist else "* SPICE Netlist\n"

        for stim in self.stimuli_list:
            s_type = stim["type"]
            s_name = stim["name"]
            node = stim["node"]
            p = stim["params"]
            if s_type == "PULSE":
                netlist += f"{s_name} {node} 0 PULSE({p['V_initial']} {p['V_on']} {p['delay']} {p['rise_time']} {p['fall_time']} {p['pulse_width']} {p['period']})\n"
            elif s_type == "PWL":
                netlist += f"{s_name} {node} 0 PWL({p['Time-Voltage Pairs (t1 v1 t2 v2 ...)']})\n"
            elif s_type == "VDC":
                netlist += f"{s_name} {node} 0 DC {p['Voltage']}\n"
            elif s_type == "VAC":
                netlist += f"{s_name} {node} 0 AC {p['Amplitude']} SIN(0 {p['Amplitude']} {p['Frequency']} {p['Phase']})\n"
            elif s_type == "IDC":
                netlist += f"{s_name} {node} 0 DC {p['Current']}\n"

        analysis_type = self.analysis_type_combo.currentText()
        if analysis_type == "Transient":
            stop = self.analysis_widgets["Stop Time"].text()
            step = self.analysis_widgets["Time Step"].text()
            max_step = self.analysis_widgets["Max Step"].text()
            min_step = self.analysis_widgets["Min Step"].text()
            if stop and step:
                netlist += f".TRAN {step} {stop}"
                if max_step: netlist += f" {max_step}"
                if min_step: netlist += f" {min_step}"
                netlist += "\n"
        elif analysis_type == "DC" and self.stimuli_list:
            start = self.analysis_widgets["Start Value"].text()
            stop = self.analysis_widgets["Stop Value"].text()
            step = self.analysis_widgets["Step"].text()
            if start and stop and step:
                netlist += f".DC {self.stimuli_list[0]['name']} {start} {stop} {step}\n"

        netlist += ".END"
        self.netlist_text.setPlainText(netlist)

    # ===== Copy Netlist =====
    def copy_netlist(self):
        self.netlist_text.selectAll()
        self.netlist_text.copy()

# ===== Run Application =====
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpiceGenerator()
    window.show()
    sys.exit(app.exec())
