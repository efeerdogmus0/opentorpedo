"""
Teknofest mode UI — fixed CAD geometry, tunable ballast and launch parameters.
"""

from __future__ import annotations

import copy
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel, QMessageBox, QTableWidgetItem,
    QHBoxLayout, QVBoxLayout, QPushButton, QFileDialog,
    QGroupBox, QFormLayout, QWidget,
)

from torpedo_model import BallastMass, CadHull
from ui_components import MainWindow
from optimizer import DesignVariable, ObjectiveGoal
from teknofest.materials import DEFAULT_INFILL, PLA_DENSITY, PLA_NAME
from teknofest.preset import (
    create_teknofest_torpedo,
    default_design_variables,
    default_sim_params,
)


class TeknofestMainWindow(MainWindow):
    """OpenTorpedo Teknofest: fixed STEP hull, tunable mass / CoG / launch."""

    def __init__(self, cad_path: str | None = None) -> None:
        self._cad_geom = None
        torpedo, geom = create_teknofest_torpedo(cad_path)
        self._cad_geom = geom
        super().__init__(torpedo)
        self.setWindowTitle("OpenTorpedo / Teknofest")
        self._apply_teknofest_restrictions()
        self._set_sim_params(default_sim_params())
        self._setup_cad_panel()
        self._preset_design_variables()
        self._localize_labels()

    def _localize_labels(self) -> None:
        self.prop_group.setTitle("Parameters")
        self.spin_spring.setSuffix(" N")
        # Launch tab — Turkish technical labels
        launch = self.right_tabs.widget(0)
        if launch is not None:
            for gb in launch.findChildren(QGroupBox):
                if gb.title() == "Launch Parameters":
                    gb.setTitle("Atış")
                elif gb.title() == "Environment":
                    gb.setTitle("Ortam")

    def _apply_teknofest_restrictions(self) -> None:
        self.btn_add.hide()
        self.btn_remove.hide()
        self.btn_dup.hide()
        self.btn_up.hide()
        self.btn_down.hide()
        self.combo_add_type.hide()

        for w in (
            self.spin_length, self.spin_diameter, self.spin_density,
            self.spin_fin_count, self.spin_fin_span,
            self.spin_fin_root, self.spin_fin_tip, self.spin_fin_thick,
            self.spin_fin_sweep, self.spin_thrust, self.spin_burn_time,
            self.spin_dry_mass,
        ):
            w.setEnabled(False)

        self.btn_add_dv.hide()
        self.btn_rm_dv.hide()
        self.tbl_dvars.setEditTriggers(self.tbl_dvars.EditTrigger.NoEditTriggers)

        self.btn_run.setText("Simülasyonu çalıştır")
        self.btn_optimize.setText("Optimizasyonu çalıştır")

    def _setup_cad_panel(self) -> None:
        g = self._cad_geom
        if g is None:
            return

        hull = self.torpedo.cad_hull
        hull_g = hull.hull_mass * 1000 if hull else 0.0

        model_box = QGroupBox("Model (CAD)")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setContentsMargins(8, 12, 8, 8)
        form.setSpacing(4)

        def row(label: str, value: str) -> None:
            lbl = QLabel(value)
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            form.addRow(label + ":", lbl)

        row("Dosya", os.path.basename(g.source_file))
        row("Boy", f"{g.length * 100:.1f} cm")
        row("Çap", f"{g.max_diameter * 100:.1f} cm")
        row("Hacim", f"{g.volume * 1e6:.0f} cm³")
        row("Malzeme", f"{PLA_NAME}, {PLA_DENSITY:.0f} kg/m³")
        row("Doluluk", f"{DEFAULT_INFILL * 100:.0f} %")
        row("Gövde kütlesi", f"{hull_g:.0f} g")

        note = QLabel("Geometri kilitli. Balast: kütle + konum (CoG). Atış: kuvvet.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #9ca3af; font-size: 11px;")
        form.addRow(note)

        model_box.setLayout(form)

        reload_row = QHBoxLayout()
        btn_reload = QPushButton("CAD yükle…")
        btn_reload.setObjectName("btnSecondary")
        btn_reload.clicked.connect(self._on_reload_cad)
        reload_row.addWidget(btn_reload)

        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(model_box)
        lay.addLayout(reload_row)

        left = self.comp_list.parentWidget().layout()
        if left is not None:
            left.insertWidget(1, wrap)

    def _preset_design_variables(self) -> None:
        self.tbl_dvars.setRowCount(0)
        for spec in default_design_variables(self.torpedo):
            row = self.tbl_dvars.rowCount()
            self.tbl_dvars.insertRow(row)
            self.tbl_dvars.setItem(row, 0, QTableWidgetItem(spec["label"]))
            self.tbl_dvars.setItem(row, 1, QTableWidgetItem(spec["attribute"]))
            self.tbl_dvars.setItem(row, 2, QTableWidgetItem(str(spec["lower"])))
            self.tbl_dvars.setItem(row, 3, QTableWidgetItem(str(spec["upper"])))
            self.tbl_dvars.item(row, 0).setData(Qt.ItemDataRole.UserRole, spec)

    def _on_reload_cad(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "CAD dosyası",
            os.path.dirname(self._cad_geom.source_file) if self._cad_geom else "",
            "CAD (*.stp *.step *.igs *.iges);;All Files (*)",
        )
        if not path:
            return
        try:
            torpedo, geom = create_teknofest_torpedo(path)
        except Exception as exc:
            QMessageBox.critical(self, "CAD", str(exc))
            return
        self.torpedo = torpedo
        self._cad_geom = geom
        self._populate_list()
        self._update_visualizer()
        self._preset_design_variables()

    def _ballast_position_limits(self) -> tuple[float, float]:
        hull = self.torpedo.cad_hull
        return (0.0, hull.length if hull else self.torpedo.total_length)

    def _on_select_component(self, index: int) -> None:
        super()._on_select_component(index)
        if index < 0 or index >= len(self.torpedo.components):
            return
        comp = self.torpedo.components[index]
        if isinstance(comp, CadHull):
            self.spin_length.setValue(comp.length)
            self.spin_diameter.setValue(comp.diameter)
            self.spin_mass.setValue(comp.hull_mass)
            self.spin_density.setValue(comp.density)
            self.spin_mass.setEnabled(False)
            self.spin_position.setEnabled(False)
            self.spin_density.setEnabled(False)
        elif isinstance(comp, BallastMass):
            lo, hi = self._ballast_position_limits()
            self.spin_mass.setEnabled(True)
            self.spin_position.setEnabled(True)
            self.spin_position.setRange(lo, hi)
            self.spin_position.setValue(comp.position)
            self.spin_position.setToolTip("Burundan balast konumu (m) — ağırlık merkezi")

    def _on_property_changed(self) -> None:
        if self._selected_index < 0:
            return
        comp = self.torpedo.components[self._selected_index]
        if isinstance(comp, CadHull):
            return
        if isinstance(comp, BallastMass):
            comp.mass = self.spin_mass.value()
            comp.position = self.spin_position.value()
            self._update_visualizer()
            return
        super()._on_property_changed()

    def _on_new(self) -> None:
        reply = QMessageBox.question(
            self,
            "Sıfırla",
            "Varsayılan CAD modeline dönülsün mü?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.torpedo, self._cad_geom = create_teknofest_torpedo()
            self._populate_list()
            self._update_visualizer()
            self._preset_design_variables()

    def _on_run_optimization(self) -> None:
        dvars = []
        for r in range(self.tbl_dvars.rowCount()):
            item = self.tbl_dvars.item(r, 0)
            if item is None:
                continue
            spec = item.data(Qt.ItemDataRole.UserRole)
            if not spec:
                continue
            try:
                lo = float(self.tbl_dvars.item(r, 2).text())
                hi = float(self.tbl_dvars.item(r, 3).text())
            except (ValueError, AttributeError):
                QMessageBox.warning(self, "Sınır", f"Satır {r + 1}: geçersiz min/max")
                return
            dvars.append(
                DesignVariable(
                    component_index=spec.get("component_index", 0),
                    attribute=spec["attribute"],
                    lower=lo,
                    upper=hi,
                    label=spec.get("label", spec["attribute"]),
                    scope=spec.get("scope", "component"),
                )
            )

        if len(dvars) < 2:
            QMessageBox.warning(self, "Değişkenler", "En az iki tasarım değişkeni gerekli.")
            return

        from ui_components import OptimizerWorker
        from optimizer import Constraint, ConstraintOp

        cons = []
        for r in range(self.tbl_cons.rowCount()):
            combo_m = self.tbl_cons.cellWidget(r, 0)
            combo_op = self.tbl_cons.cellWidget(r, 1)
            if combo_m is None or combo_op is None:
                continue
            metric = combo_m.currentText()
            op = ConstraintOp.GEQ if combo_op.currentText() == ">=" else ConstraintOp.LEQ
            val = float(self.tbl_cons.item(r, 2).text())
            cons.append(Constraint(metric=metric, op=op, limit=val))

        obj_metric = self.combo_obj_metric.currentText()
        goal = ObjectiveGoal.MINIMIZE if self.combo_obj_goal.currentIndex() == 0 else ObjectiveGoal.MAXIMIZE

        sim = self._get_sim_params()
        sim.update(self._get_env_params())

        self.btn_optimize.setEnabled(False)
        self.opt_progress.show()
        self._optimizer_worker = OptimizerWorker(
            copy.deepcopy(self.torpedo), sim, obj_metric, goal, dvars, cons
        )
        self._optimizer_worker.finished.connect(self._on_teknofest_optimization_done)
        self._optimizer_worker.start()

    def _on_teknofest_optimization_done(self, result) -> None:
        if isinstance(result, str):
            self.btn_optimize.setEnabled(True)
            self.opt_progress.hide()
            QMessageBox.critical(self, "Optimizasyon", result)
            return

        from optimizer import OptimizationResult

        r: OptimizationResult = result
        self.btn_optimize.setEnabled(True)
        self.opt_progress.hide()

        status = "Tamam" if r.success else r.message
        lines = [
            f"Durum: {status}",
            f"Hedef: {r.initial_value:.4f} -> {r.final_value:.4f}",
            "",
        ]
        for key, old in r.initial_params.items():
            new = r.final_params[key]
            lines.append(f"  {key}: {old:.4f} -> {new:.4f}")
        self.lbl_opt_result.setText("\n".join(lines))

        if r.success:
            reply = QMessageBox.question(
                self,
                "Uygula",
                "Sonuçlar modele uygulansın mı?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                for spec in default_design_variables(self.torpedo):
                    label = spec.get("label", spec["attribute"])
                    if label not in r.final_params:
                        continue
                    val = r.final_params[label]
                    if spec.get("scope") == "sim_params":
                        if spec["attribute"] == "spring_force":
                            self.spin_spring.setValue(val)
                    else:
                        idx = spec["component_index"]
                        setattr(self.torpedo.components[idx], spec["attribute"], val)
                self._populate_list()
                self._update_visualizer()
