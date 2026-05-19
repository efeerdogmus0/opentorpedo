"""
ui_components.py — PyQt6 user interface for OpenTorpedo.
"""

from __future__ import annotations

import copy
import math
import os
from typing import Optional

from PyQt6.QtCore import Qt, QRectF, QThread, pyqtSignal
from PyQt6.QtGui import (
    QAction, QBrush, QColor, QFont, QKeySequence, QPainterPath, QPen,
)
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGraphicsScene, QGraphicsView, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QListWidget, QMainWindow, QMenu, QMenuBar, QMessageBox,
    QProgressBar, QPushButton, QSpinBox, QSplitter, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import pyqtgraph as pg

import physics_engine as pe
from config_manager import load_config, save_config, save_last_session
from optimizer import (
    METRIC_FUNCTIONS,
    Constraint,
    ConstraintOp,
    DesignVariable,
    ObjectiveGoal,
    OptimizationResult,
    run_optimization,
)
from simulator import SimulationResult, run_simulation
from torpedo_model import (
    BallastMass,
    BodyTube,
    CadHull,
    Fin,
    LaunchSpring,
    Motor,
    NoseCone,
    Torpedo,
    component_from_dict,
    create_default_torpedo,
)
from ui_theme import (
    BODY_FILL,
    BODY_STROKE,
    CAD_FILL,
    CAD_STROKE,
    COB_COLOR,
    COG_COLOR,
    CP_COLOR,
    FIN_FILL,
    NOSE_FILL,
    PLOT_BACKGROUND,
    PLOT_START_MARKER,
    PLOT_TRAJECTORY,
    PLOT_VELOCITY,
    STYLESHEET,
    panel_title,
)

_COG_COL = QColor(COG_COLOR)
_COB_COL = QColor(COB_COLOR)
_CP_COL = QColor(CP_COLOR)


class OptimizerWorker(QThread):
    finished = pyqtSignal(object)

    def __init__(
        self,
        torpedo: Torpedo,
        sim_params: dict,
        objective_metric: str,
        goal: ObjectiveGoal,
        design_vars: list[DesignVariable],
        constraints: list[Constraint],
    ) -> None:
        super().__init__()
        self.torpedo = torpedo
        self.sim_params = sim_params
        self.objective_metric = objective_metric
        self.goal = goal
        self.design_vars = design_vars
        self.constraints = constraints

    def run(self) -> None:
        try:
            result = run_optimization(
                self.torpedo,
                self.sim_params,
                self.objective_metric,
                self.goal,
                self.design_vars,
                self.constraints,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.finished.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, torpedo: Torpedo | None = None) -> None:
        super().__init__()
        self.torpedo = torpedo or create_default_torpedo()
        self._selected_index = -1
        self._optimizer_worker: OptimizerWorker | None = None
        self.setWindowTitle("OpenTorpedo")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(STYLESHEET)
        self._build_menu()
        self._build_ui()
        self._connect_signals()
        self._populate_list()
        self._update_visualizer()

    def _build_menu(self) -> None:
        bar = QMenuBar(self)
        self.setMenuBar(bar)
        file_menu = bar.addMenu("File")
        self.act_new = QAction("New", self)
        self.act_open = QAction("Open…", self)
        self.act_save = QAction("Save", self)
        self.act_save_as = QAction("Save As…", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        file_menu.addAction(self.act_new)
        file_menu.addAction(self.act_open)
        file_menu.addAction(self.act_save)
        file_menu.addAction(self.act_save_as)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # Left — components
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.addWidget(panel_title("Components"))
        self.comp_list = QListWidget()
        left_lay.addWidget(self.comp_list)

        row = QHBoxLayout()
        self.combo_add_type = QComboBox()
        self.combo_add_type.addItems([
            "NoseCone", "BodyTube", "Fin", "BallastMass", "Motor",
        ])
        self.btn_add = QPushButton("Add")
        self.btn_add.setObjectName("btnSecondary")
        self.btn_remove = QPushButton("Remove")
        self.btn_remove.setObjectName("btnDanger")
        self.btn_dup = QPushButton("Clone")
        self.btn_dup.setObjectName("btnSecondary")
        self.btn_up = QPushButton("Up")
        self.btn_down = QPushButton("Down")
        row.addWidget(self.combo_add_type)
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_remove)
        row.addWidget(self.btn_dup)
        row.addWidget(self.btn_up)
        row.addWidget(self.btn_down)
        left_lay.addLayout(row)

        self.prop_group = QGroupBox("Parameters")
        prop_form = QFormLayout(self.prop_group)
        self.spin_name = QLabel("—")
        self.spin_length = self._dbl_spin(0, 5, 4)
        self.spin_diameter = self._dbl_spin(0, 2, 4)
        self.spin_mass = self._dbl_spin(0, 50, 4)
        self.spin_density = self._dbl_spin(0, 10000, 1)
        self.spin_position = self._dbl_spin(0, 5, 4)
        self.spin_fin_count = QSpinBox()
        self.spin_fin_count.setRange(1, 8)
        self.spin_fin_span = self._dbl_spin(0, 1, 4)
        self.spin_fin_root = self._dbl_spin(0, 1, 4)
        self.spin_fin_tip = self._dbl_spin(0, 1, 4)
        self.spin_fin_thick = self._dbl_spin(0, 0.05, 4)
        self.spin_fin_sweep = self._dbl_spin(-45, 45, 1)
        self.spin_thrust = self._dbl_spin(0, 500, 2)
        self.spin_burn_time = self._dbl_spin(0, 60, 2)
        self.spin_dry_mass = self._dbl_spin(0, 50, 4)
        prop_form.addRow("Type", self.spin_name)
        prop_form.addRow("Length (m)", self.spin_length)
        prop_form.addRow("Diameter (m)", self.spin_diameter)
        prop_form.addRow("Mass (kg)", self.spin_mass)
        prop_form.addRow("Density", self.spin_density)
        prop_form.addRow("Position (m)", self.spin_position)
        prop_form.addRow("Fin count", self.spin_fin_count)
        prop_form.addRow("Fin span", self.spin_fin_span)
        prop_form.addRow("Root chord", self.spin_fin_root)
        prop_form.addRow("Tip chord", self.spin_fin_tip)
        prop_form.addRow("Thickness", self.spin_fin_thick)
        prop_form.addRow("Sweep (°)", self.spin_fin_sweep)
        prop_form.addRow("Thrust (N)", self.spin_thrust)
        prop_form.addRow("Burn (s)", self.spin_burn_time)
        prop_form.addRow("Dry mass", self.spin_dry_mass)
        left_lay.addWidget(self.prop_group)

        self.lbl_summary = QLabel()
        self.lbl_summary.setObjectName("readoutPanel")
        self.lbl_summary.setWordWrap(True)
        left_lay.addWidget(self.lbl_summary)

        # Middle — profile
        mid = QWidget()
        mid_lay = QVBoxLayout(mid)
        mid_lay.addWidget(panel_title("Side profile"))
        self.scene = QGraphicsScene()
        self.gview = QGraphicsView(self.scene)
        self.gview.setObjectName("profileView")
        self.gview.setRenderHints(
            self.gview.renderHints() | self.gview.renderHints().__class__.Antialiasing
        )
        mid_lay.addWidget(self.gview)

        # Right — tabs
        right = QWidget()
        right_lay = QVBoxLayout(right)
        self.right_tabs = QTabWidget()

        launch_tab = QWidget()
        launch_lay = QVBoxLayout(launch_tab)
        launch_grp = QGroupBox("Launch Parameters")
        launch_form = QFormLayout(launch_grp)
        self.spin_velocity = self._dbl_spin(0, 50, 2)
        self.spin_angle = self._dbl_spin(-90, 90, 1)
        self.spin_spring = self._dbl_spin(0, 5000, 1)
        self.spin_duration = self._dbl_spin(0.1, 120, 1)
        launch_form.addRow("Velocity (m/s)", self.spin_velocity)
        launch_form.addRow("Angle (deg)", self.spin_angle)
        launch_form.addRow("Spring force (N)", self.spin_spring)
        launch_form.addRow("Duration (s)", self.spin_duration)
        launch_lay.addWidget(launch_grp)

        env_grp = QGroupBox("Environment")
        env_form = QFormLayout(env_grp)
        self.chk_cd_override = QCheckBox("Constant Cd")
        self.spin_cd = self._dbl_spin(0.01, 2, 3)
        self.spin_max_depth = self._dbl_spin(1, 500, 1)
        self.spin_launch_depth = self._dbl_spin(0, 20, 2)
        env_form.addRow(self.chk_cd_override)
        env_form.addRow("Cd", self.spin_cd)
        env_form.addRow("Max depth (m)", self.spin_max_depth)
        env_form.addRow("Launch depth (m)", self.spin_launch_depth)
        launch_lay.addWidget(env_grp)

        self.btn_run = QPushButton("Run simulation")
        self.btn_run.setObjectName("btnPrimary")
        launch_lay.addWidget(self.btn_run)
        launch_lay.addStretch()

        sim_tab = QWidget()
        sim_lay = QVBoxLayout(sim_tab)
        pg.setConfigOptions(antialias=True, background=PLOT_BACKGROUND, foreground="#e5e5e5")
        self.plot_traj = pg.PlotWidget(title="Trajectory (x vs depth)")
        self.plot_traj.setLabel("bottom", "x", units="m")
        self.plot_traj.setLabel("left", "depth", units="m")
        self.plot_traj.invertY(True)
        self.plot_vel = pg.PlotWidget(title="Speed vs time")
        self.plot_vel.setLabel("bottom", "t", units="s")
        self.plot_vel.setLabel("left", "speed", units="m/s")
        sim_lay.addWidget(self.plot_traj)
        sim_lay.addWidget(self.plot_vel)

        opt_tab = QWidget()
        opt_lay = QVBoxLayout(opt_tab)
        opt_form = QFormLayout()
        self.combo_obj_metric = QComboBox()
        self.combo_obj_metric.addItems(list(METRIC_FUNCTIONS.keys()))
        self.combo_obj_metric.setCurrentText("Max Speed (m/s)")
        self.combo_obj_goal = QComboBox()
        self.combo_obj_goal.addItems(["Minimize", "Maximize"])
        self.combo_obj_goal.setCurrentIndex(1)
        opt_form.addRow("Objective", self.combo_obj_metric)
        opt_form.addRow("Goal", self.combo_obj_goal)
        opt_lay.addLayout(opt_form)

        self.tbl_dvars = QTableWidget(0, 4)
        self.tbl_dvars.setHorizontalHeaderLabels(["Label", "Attribute", "Min", "Max"])
        self.tbl_dvars.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        opt_lay.addWidget(panel_title("Design variables"))
        opt_lay.addWidget(self.tbl_dvars)
        dv_row = QHBoxLayout()
        self.btn_add_dv = QPushButton("Add variable")
        self.btn_add_dv.setObjectName("btnSecondary")
        self.btn_rm_dv = QPushButton("Remove")
        self.btn_rm_dv.setObjectName("btnDanger")
        dv_row.addWidget(self.btn_add_dv)
        dv_row.addWidget(self.btn_rm_dv)
        opt_lay.addLayout(dv_row)

        self.tbl_cons = QTableWidget(0, 3)
        self.tbl_cons.setHorizontalHeaderLabels(["Metric", "Op", "Limit"])
        opt_lay.addWidget(panel_title("Constraints"))
        opt_lay.addWidget(self.tbl_cons)
        con_row = QHBoxLayout()
        self.btn_add_con = QPushButton("Add constraint")
        self.btn_add_con.setObjectName("btnSecondary")
        self.btn_rm_con = QPushButton("Remove")
        self.btn_rm_con.setObjectName("btnDanger")
        con_row.addWidget(self.btn_add_con)
        con_row.addWidget(self.btn_rm_con)
        opt_lay.addLayout(con_row)

        self.btn_optimize = QPushButton("Run optimization")
        self.btn_optimize.setObjectName("btnPrimary")
        self.opt_progress = QProgressBar()
        self.opt_progress.setRange(0, 0)
        self.opt_progress.hide()
        self.lbl_opt_result = QLabel()
        self.lbl_opt_result.setWordWrap(True)
        opt_lay.addWidget(self.btn_optimize)
        opt_lay.addWidget(self.opt_progress)
        opt_lay.addWidget(self.lbl_opt_result)
        opt_lay.addStretch()

        self.right_tabs.addTab(launch_tab, "Launch")
        self.right_tabs.addTab(sim_tab, "Results")
        self.right_tabs.addTab(opt_tab, "Optimize")
        right_lay.addWidget(self.right_tabs)

        splitter.addWidget(left)
        splitter.addWidget(mid)
        splitter.addWidget(right)
        splitter.setSizes([280, 420, 400])

    def _dbl_spin(self, lo: float, hi: float, dec: int) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(dec)
        s.setSingleStep(10 ** -dec)
        return s

    def _connect_signals(self) -> None:
        self.act_new.triggered.connect(self._on_new)
        self.act_open.triggered.connect(self._on_open)
        self.act_save.triggered.connect(self._on_save)
        self.act_save_as.triggered.connect(self._on_save_as)
        self.comp_list.currentRowChanged.connect(self._on_select_component)
        self.btn_add.clicked.connect(self._on_add_component)
        self.btn_remove.clicked.connect(self._on_remove_component)
        self.btn_dup.clicked.connect(self._on_duplicate_component)
        self.btn_up.clicked.connect(lambda: self._on_move(-1))
        self.btn_down.clicked.connect(lambda: self._on_move(1))
        for w in (
            self.spin_length, self.spin_diameter, self.spin_mass, self.spin_density,
            self.spin_position, self.spin_fin_count, self.spin_fin_span,
            self.spin_fin_root, self.spin_fin_tip, self.spin_fin_thick,
            self.spin_fin_sweep, self.spin_thrust, self.spin_burn_time, self.spin_dry_mass,
        ):
            w.valueChanged.connect(self._on_property_changed)
        self.btn_run.clicked.connect(self._on_run_simulation)
        self.btn_add_dv.clicked.connect(self._on_add_design_var)
        self.btn_rm_dv.clicked.connect(self._on_rm_design_var)
        self.btn_add_con.clicked.connect(self._on_add_constraint)
        self.btn_rm_con.clicked.connect(self._on_rm_constraint)
        self.btn_optimize.clicked.connect(self._on_run_optimization)

    def _get_sim_params(self) -> dict:
        return {
            "velocity": self.spin_velocity.value(),
            "angle": self.spin_angle.value(),
            "spring_force": self.spin_spring.value(),
            "duration": self.spin_duration.value(),
        }

    def _get_env_params(self) -> dict:
        return {
            "cd_override": self.spin_cd.value() if self.chk_cd_override.isChecked() else None,
            "max_depth": self.spin_max_depth.value(),
            "launch_depth": self.spin_launch_depth.value(),
        }

    def _set_sim_params(self, params: dict) -> None:
        self.spin_velocity.setValue(params.get("velocity", 0.0))
        self.spin_angle.setValue(params.get("angle", 5.0))
        self.spin_spring.setValue(params.get("spring_force", 0.0))
        self.spin_duration.setValue(params.get("duration", 5.0))

    def _set_env_params(self, params: dict) -> None:
        cd = params.get("cd_override")
        self.chk_cd_override.setChecked(cd is not None)
        if cd is not None:
            self.spin_cd.setValue(cd)
        self.spin_max_depth.setValue(params.get("max_depth", 50.0))
        self.spin_launch_depth.setValue(params.get("launch_depth", 0.5))

    def _on_new(self) -> None:
        self.torpedo = create_default_torpedo()
        self._populate_list()
        self._update_visualizer()

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open config", "", "JSON (*.json)")
        if not path:
            return
        try:
            torpedo, sim, env = load_config(path)
            self.torpedo = torpedo
            self._set_sim_params(sim)
            self._set_env_params(env)
            self._populate_list()
            self._update_visualizer()
        except Exception as exc:
            QMessageBox.critical(self, "Open", str(exc))

    def _on_save(self) -> None:
        if hasattr(self, "_save_path") and self._save_path:
            self._save_to(self._save_path)
        else:
            self._on_save_as()

    def _on_save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save config", "", "JSON (*.json)")
        if path:
            self._save_to(path)

    def _save_to(self, path: str) -> None:
        try:
            save_config(path, self.torpedo, self._get_sim_params(), self._get_env_params())
            self._save_path = path
        except Exception as exc:
            QMessageBox.critical(self, "Save", str(exc))

    def _populate_list(self) -> None:
        self.comp_list.clear()
        for c in self.torpedo.components:
            self.comp_list.addItem(f"{c.name} ({type(c).__name__})")

    def _on_add_component(self) -> None:
        kind = self.combo_add_type.currentText()
        if kind == "NoseCone":
            comp = NoseCone(position=0.0)
        elif kind == "BodyTube":
            comp = BodyTube(position=self.torpedo.total_length)
        elif kind == "Fin":
            comp = Fin(position=max(0.0, self.torpedo.total_length - 0.05))
        elif kind == "BallastMass":
            comp = BallastMass()
        else:
            comp = Motor(position=self.torpedo.total_length * 0.5)
        self.torpedo.components.append(comp)
        self._populate_list()
        self.comp_list.setCurrentRow(len(self.torpedo.components) - 1)

    def _on_remove_component(self) -> None:
        i = self.comp_list.currentRow()
        if i >= 0:
            del self.torpedo.components[i]
            self._populate_list()
            self._update_visualizer()

    def _on_duplicate_component(self) -> None:
        i = self.comp_list.currentRow()
        if i < 0:
            return
        c = self.torpedo.components[i]
        d = c.to_dict()
        d["name"] = c.name + " (copy)"
        self.torpedo.components.append(component_from_dict(d))
        self._populate_list()

    def _on_move(self, delta: int) -> None:
        i = self.comp_list.currentRow()
        j = i + delta
        if 0 <= i < len(self.torpedo.components) and 0 <= j < len(self.torpedo.components):
            comps = self.torpedo.components
            comps[i], comps[j] = comps[j], comps[i]
            self._populate_list()
            self.comp_list.setCurrentRow(j)

    def _block_all_prop_signals(self, block: bool) -> None:
        for w in (
            self.spin_length, self.spin_diameter, self.spin_mass, self.spin_density,
            self.spin_position, self.spin_fin_count, self.spin_fin_span,
            self.spin_fin_root, self.spin_fin_tip, self.spin_fin_thick,
            self.spin_fin_sweep, self.spin_thrust, self.spin_burn_time, self.spin_dry_mass,
        ):
            w.blockSignals(block)

    def _on_select_component(self, index: int) -> None:
        self._selected_index = index
        self._block_all_prop_signals(True)
        if index < 0 or index >= len(self.torpedo.components):
            self.spin_name.setText("—")
            self._block_all_prop_signals(False)
            return
        comp = self.torpedo.components[index]
        self.spin_name.setText(type(comp).__name__)
        if hasattr(comp, "length"):
            self.spin_length.setValue(comp.length)
        if hasattr(comp, "diameter"):
            self.spin_diameter.setValue(comp.diameter)
        if hasattr(comp, "mass") and not isinstance(comp, CadHull):
            self.spin_mass.setValue(comp.mass)
        elif isinstance(comp, CadHull):
            self.spin_mass.setValue(comp.hull_mass)
        if hasattr(comp, "density"):
            self.spin_density.setValue(comp.density)
        if hasattr(comp, "position"):
            self.spin_position.setValue(comp.position)
        if isinstance(comp, Fin):
            self.spin_fin_count.setValue(comp.count)
            self.spin_fin_span.setValue(comp.span)
            self.spin_fin_root.setValue(comp.root_chord)
            self.spin_fin_tip.setValue(comp.tip_chord)
            self.spin_fin_thick.setValue(comp.thickness)
            self.spin_fin_sweep.setValue(comp.sweep_angle)
        if isinstance(comp, Motor):
            self.spin_thrust.setValue(comp.thrust)
            self.spin_burn_time.setValue(comp.burn_time)
            self.spin_dry_mass.setValue(comp.dry_mass)
        self._block_all_prop_signals(False)

    def _on_property_changed(self) -> None:
        if self._selected_index < 0:
            return
        comp = self.torpedo.components[self._selected_index]
        if isinstance(comp, CadHull):
            comp.infill = min(max(self.spin_density.value() / 1240.0, 0.05), 1.0)
        elif hasattr(comp, "length"):
            comp.length = self.spin_length.value()
        if hasattr(comp, "diameter"):
            comp.diameter = self.spin_diameter.value()
        if isinstance(comp, BallastMass):
            comp.mass = self.spin_mass.value()
        elif hasattr(comp, "mass") and not isinstance(comp, (CadHull, LaunchSpring)):
            if isinstance(comp, BodyTube):
                comp.mass = self.spin_mass.value()
        if hasattr(comp, "density") and not isinstance(comp, CadHull):
            comp.density = self.spin_density.value()
        if hasattr(comp, "position"):
            comp.position = self.spin_position.value()
        if isinstance(comp, Fin):
            comp.count = self.spin_fin_count.value()
            comp.span = self.spin_fin_span.value()
            comp.root_chord = self.spin_fin_root.value()
            comp.tip_chord = self.spin_fin_tip.value()
            comp.thickness = self.spin_fin_thick.value()
            comp.sweep_angle = self.spin_fin_sweep.value()
        if isinstance(comp, Motor):
            comp.thrust = self.spin_thrust.value()
            comp.burn_time = self.spin_burn_time.value()
            comp.dry_mass = self.spin_dry_mass.value()
        self._update_visualizer()

    def _update_visualizer(self) -> None:
        self.scene.clear()
        scale = 800.0
        cy = 0.0
        nose = self.torpedo.nose
        body = self.torpedo.body
        cad = self.torpedo.cad_hull
        fins = self.torpedo.fins
        max_d = self.torpedo.max_diameter or 0.04

        pen_body = QPen(QColor(BODY_STROKE), 1.0)
        brush_body = QBrush(QColor(BODY_FILL))
        pen_cad = QPen(QColor(CAD_STROKE), 1.0, Qt.PenStyle.DashLine)
        brush_cad = QBrush(QColor(CAD_FILL))

        if cad is not None:
            bx = cad.position * scale
            self.scene.addRect(
                QRectF(bx, cy - cad.diameter * scale / 2, cad.length * scale, cad.diameter * scale),
                pen_cad, brush_cad,
            )
        if body is not None:
            bx = body.position * scale
            self.scene.addRect(
                QRectF(bx, cy - body.diameter * scale / 2, body.length * scale, body.diameter * scale),
                pen_body, brush_body,
            )
        if nose is not None:
            nl = nose.length * scale
            nr = nose.radius * scale
            nx = nose.position * scale
            path = QPainterPath()
            path.moveTo(nx, 0)
            path.cubicTo(nx + nl * 0.1, -nr * 0.9, nx + nl * 0.7, -nr, nx + nl, -nr)
            path.lineTo(nx + nl, nr)
            path.cubicTo(nx + nl * 0.7, nr * 0.9, nx + nl * 0.1, nr, nx, 0)
            self.scene.addPath(path, pen_body, QBrush(QColor(NOSE_FILL)))
        if fins is not None:
            fin_x = fins.position * scale
            body_r = (max_d / 2.0) * scale
            for sign in (1, -1):
                pf = QPainterPath()
                pf.moveTo(fin_x, cy + sign * body_r)
                pf.lineTo(fin_x + fins.root_chord * scale, cy + sign * (body_r + fins.span * scale))
                pf.lineTo(fin_x + fins.tip_chord * scale, cy + sign * (body_r + fins.span * scale))
                pf.closeSubpath()
                self.scene.addPath(pf, pen_body, QBrush(QColor(FIN_FILL)))

        m = pe.total_mass(self.torpedo)
        vol = pe.total_volume(self.torpedo)
        cog = pe.center_of_gravity(self.torpedo)
        cob = pe.center_of_buoyancy(self.torpedo)
        cp = pe.center_of_pressure(self.torpedo)
        sm = pe.static_margin(self.torpedo)
        f_buoy = pe.buoyancy_force(vol)
        f_grav = pe.gravity_force(m)
        for x_pos, col, label in ((cog, _COG_COL, "CoG"), (cob, _COB_COL, "CoB"), (cp, _CP_COL, "CP")):
            self.scene.addEllipse(
                QRectF(x_pos * scale - 4, cy - 4, 8, 8), QPen(col), QBrush(col),
            )

        self.lbl_summary.setText(
            f"Mass {m*1000:.1f} g  |  Vol {vol*1e6:.0f} cm³\n"
            f"CoG {cog*100:.2f} cm  |  CoB {cob*100:.2f} cm  |  CP {cp*100:.2f} cm\n"
            f"SM {sm:.2f} cal  |  Buoy {f_buoy:.3f} N  |  Weight {f_grav:.3f} N\n"
            f"Net (up) {f_buoy - f_grav:+.3f} N"
        )
        save_last_session(self.torpedo, self._get_sim_params(), self._get_env_params())

    def _on_run_simulation(self) -> None:
        try:
            env = self._get_env_params()
            spring = self.torpedo.launch_spring
            v_boost = None
            if spring is not None:
                v_boost = spring.launch_velocity_boost(pe.total_mass(self.torpedo))
            result = run_simulation(
                self.torpedo,
                initial_velocity=self.spin_velocity.value(),
                launch_angle_deg=self.spin_angle.value(),
                spring_force=self.spin_spring.value(),
                spring_velocity_boost=v_boost,
                duration=self.spin_duration.value(),
                cd_override=env.get("cd_override"),
                max_depth=env.get("max_depth", 50.0),
                launch_depth=env.get("launch_depth", 0.5),
            )
            self._plot_results(result)
            self.right_tabs.setCurrentIndex(1)
        except Exception as exc:
            QMessageBox.critical(self, "Simulation", str(exc))

    def _plot_results(self, result: SimulationResult) -> None:
        self.plot_traj.clear()
        self.plot_traj.plot(result.x, result.z, pen=pg.mkPen(PLOT_TRAJECTORY, width=1.5))
        self.plot_traj.plot(
            [result.x[0]], [result.z[0]],
            pen=None, symbol="o", symbolBrush=PLOT_START_MARKER, symbolSize=6,
        )
        self.plot_vel.clear()
        self.plot_vel.plot(result.t, result.speed, pen=pg.mkPen(PLOT_VELOCITY, width=1.5))

    def _on_add_design_var(self) -> None:
        if self._selected_index < 0:
            QMessageBox.information(self, "Design variable", "Select a component first.")
            return
        comp = self.torpedo.components[self._selected_index]
        attr = "mass" if hasattr(comp, "mass") else "length"
        row = self.tbl_dvars.rowCount()
        self.tbl_dvars.insertRow(row)
        self.tbl_dvars.setItem(row, 0, QTableWidgetItem(f"comp[{self._selected_index}].{attr}"))
        self.tbl_dvars.setItem(row, 1, QTableWidgetItem(attr))
        self.tbl_dvars.setItem(row, 2, QTableWidgetItem("0"))
        self.tbl_dvars.setItem(row, 3, QTableWidgetItem("1"))

    def _on_rm_design_var(self) -> None:
        r = self.tbl_dvars.currentRow()
        if r >= 0:
            self.tbl_dvars.removeRow(r)

    def _on_add_constraint(self) -> None:
        row = self.tbl_cons.rowCount()
        self.tbl_cons.insertRow(row)
        combo_m = QComboBox()
        combo_m.addItems(list(METRIC_FUNCTIONS.keys()))
        combo_op = QComboBox()
        combo_op.addItems([">=", "<="])
        self.tbl_cons.setCellWidget(row, 0, combo_m)
        self.tbl_cons.setCellWidget(row, 1, combo_op)
        self.tbl_cons.setItem(row, 2, QTableWidgetItem("0.5"))

    def _on_rm_constraint(self) -> None:
        r = self.tbl_cons.currentRow()
        if r >= 0:
            self.tbl_cons.removeRow(r)

    def _on_run_optimization(self) -> None:
        dvars: list[DesignVariable] = []
        for r in range(self.tbl_dvars.rowCount()):
            try:
                dvars.append(DesignVariable(
                    component_index=self._selected_index if self._selected_index >= 0 else 0,
                    attribute=self.tbl_dvars.item(r, 1).text(),
                    lower=float(self.tbl_dvars.item(r, 2).text()),
                    upper=float(self.tbl_dvars.item(r, 3).text()),
                    label=self.tbl_dvars.item(r, 0).text(),
                ))
            except (ValueError, AttributeError):
                QMessageBox.warning(self, "Design variables", f"Invalid row {r + 1}")
                return
        if len(dvars) < 1:
            QMessageBox.warning(self, "Design variables", "Add at least one design variable.")
            return

        cons: list[Constraint] = []
        for r in range(self.tbl_cons.rowCount()):
            combo_m = self.tbl_cons.cellWidget(r, 0)
            combo_op = self.tbl_cons.cellWidget(r, 1)
            if combo_m is None or combo_op is None:
                continue
            op = ConstraintOp.GEQ if combo_op.currentText() == ">=" else ConstraintOp.LEQ
            cons.append(Constraint(
                metric=combo_m.currentText(),
                op=op,
                limit=float(self.tbl_cons.item(r, 2).text()),
            ))

        goal = ObjectiveGoal.MINIMIZE if self.combo_obj_goal.currentIndex() == 0 else ObjectiveGoal.MAXIMIZE
        sim = self._get_sim_params()
        sim.update(self._get_env_params())

        self.btn_optimize.setEnabled(False)
        self.opt_progress.show()
        self._optimizer_worker = OptimizerWorker(
            copy.deepcopy(self.torpedo), sim,
            self.combo_obj_metric.currentText(), goal, dvars, cons,
        )
        self._optimizer_worker.finished.connect(self._on_optimization_done)
        self._optimizer_worker.start()

    def _on_optimization_done(self, result: object) -> None:
        self.btn_optimize.setEnabled(True)
        self.opt_progress.hide()
        if isinstance(result, str):
            QMessageBox.critical(self, "Optimization", result)
            return
        r: OptimizationResult = result
        status = "Converged" if r.success else r.message
        lines = [
            f"Status: {status}",
            f"Iterations: {r.n_iterations}  |  Evals: {r.n_func_evals}",
            f"Objective: {r.initial_value:.6f} -> {r.final_value:.6f}",
            "",
            "Parameters:",
        ]
        for key in r.initial_params:
            lines.append(f"  {key}: {r.initial_params[key]:.6f} -> {r.final_params[key]:.6f}")
        self.lbl_opt_result.setText("\n".join(lines))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_visualizer()
