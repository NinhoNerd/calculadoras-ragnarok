# src/calc_app/gui/pages/farmacologia_avancada.py
"""
Special Pharmacy (Farmacologia Avançada) — live-updating tab
(Uses AppState as the single source of truth.)

New in this version
-------------------
• Buffs box (checkboxes) in the Inputs column.
• Inline badges next to INT/DES/SOR spins showing "base + buff = total".
• Calculations use effective stats (base + buffs) from AppState.
"""

from typing import Optional, Dict
from contextlib import contextmanager
import logging, traceback, time

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QSplitter, QGroupBox, QSpinBox,
    QStyle, QTableWidget, QTableWidgetItem, QLabel, QHeaderView, QSizePolicy,
    QHBoxLayout, QCheckBox, QMessageBox
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import MaxNLocator
from matplotlib.figure import Figure

from calc_app.config import (
    LEFT_PANE_WIDTH, DEBOUNCE_MS, TABLE_ICON_PX, HIDE_HISTOGRAM_Y_TICKS
)
from calc_app.app_state import AppState, PharmacySpecialSnapshot, ItemRow

# Stats / probabilities core
from ...core.stats import (
    enumerate_special_pharmacy_results,
    pharmacy_special_probability_by_ranges,
    PHARMACY_SPECIAL_TOTAL_COMBOS,
)

# Buff catalog (declarative)
from calc_app.core import buffs as buffs_core

from ..icons import icon_for_item_id

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")

# ──────────────────────────────────────────────────────────────
# Matplotlib canvas
# ──────────────────────────────────────────────────────────────

class _MplCanvas(FigureCanvas):
    def __init__(self):
        self.fig = Figure(figsize=(5, 3))
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)

    def plot_hist(self, results, *, guide_x: Optional[int] = None):
        self.ax.clear()
        if not results:
            self.draw()
            return
        lo, hi = min(results), max(results)
        bins = range(lo, hi + 2)
        self.ax.hist(results, bins=bins, align="left")
        self.ax.set_xlabel("Resultado")
        self.ax.set_ylabel("Contagem")
        self.ax.set_title("Distribuição de Resultados (Histograma)")
        self.ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        if guide_x is not None:
            self.ax.axvline(guide_x, linestyle="--")
        if HIDE_HISTOGRAM_Y_TICKS:
            self.ax.tick_params(axis="y", left=False, labelleft=False)
        self.fig.tight_layout()
        self.draw()


@contextmanager
def _block_signals(*widgets):
    prev = [w.blockSignals(True) for w in widgets]
    try:
        yield
    finally:
        for w in widgets:
            w.blockSignals(False)


# ──────────────────────────────────────────────────────────────
# Page
# ──────────────────────────────────────────────────────────────

class PharmacySpecialPage(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state

        # debounce
        self._recalc_timer = QTimer(self)
        self._recalc_timer.setSingleShot(True)
        self._recalc_timer.setInterval(DEBOUNCE_MS)
        self._recalc_timer.timeout.connect(self.calculate)

        # keep small references
        self._eff_labels: dict[str, QLabel] = {}          # stat_key -> QLabel with "base + buff = total"
        self._buff_checks: dict[str, QCheckBox] = {}      # buff_key -> checkbox

        # ------------- Left column (inputs + buffs) -------------
        left_col = QWidget()
        left_v = QVBoxLayout(left_col)
        left_v.setContentsMargins(0, 0, 0, 0)
        left_v.setSpacing(10)

        # Inputs box
        inputs_box = QGroupBox("Inputs")
        form = QFormLayout(inputs_box)

        # stats / levels / skills spins
        self.spin_int  = self._spin(1, 500, 1)
        self.spin_des  = self._spin(1, 500, 1)
        self.spin_sor  = self._spin(1, 500, 1)
        self.spin_base = self._spin(101, 175, 101)
        self.spin_job  = self._spin(1, 70, 1)
        self.spin_pr   = self._spin(0, 10, 0)  # Pesquisa de Poções
        self.spin_cpf  = self._spin(0, 5, 0)   # Proteção Química Total (Full)
        self.spin_adv  = self._spin(1, 10, 1)  # Farmacologia Avançada

        # For INT/DES/SOR we wrap the spin with a small label that shows "base + buff = total".
        form.addRow("INT", self._row_with_effect("int_stat", self.spin_int))
        form.addRow("DES", self._row_with_effect("des_stat", self.spin_des))
        form.addRow("SOR", self._row_with_effect("sor_stat", self.spin_sor))
        # Levels / Skills (no badges needed)
        form.addRow("Lv Base", self.spin_base)
        form.addRow("Lv Classe", self.spin_job)
        form.addRow("Lv Pesquisa de Poções", self.spin_pr)
        form.addRow("Lv Proteção Química Total", self.spin_cpf)
        form.addRow("Lv Farmacologia Avançada", self.spin_adv)

        # Buffs box (appears under Inputs)
        buffs_box = self._build_buffs_box()

        left_v.addWidget(inputs_box)
        left_v.addWidget(buffs_box)
        left_v.addStretch(1)

        left_col.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        left_col.setFixedWidth(LEFT_PANE_WIDTH)

        # ------------- Right column (chart + table) -------------
        self.canvas = _MplCanvas()
        self.lbl_summary = QLabel("")
        self.lbl_summary.setWordWrap(True)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["ITEM", "Dificuldade", "MAX", "MAX-3", "MAX-4", "MAX-5", "MAX-6", "Média"]
        )
        self.table.setIconSize(QSize(TABLE_ICON_PX, TABLE_ICON_PX))
        self.table.verticalHeader().setDefaultSectionSize(max(24, TABLE_ICON_PX + 4))

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 8):
            header.setSectionResizeMode(col, QHeaderView.Fixed)
            self.table.setColumnWidth(col, 80)

        right = QWidget()
        v = QVBoxLayout(right)
        v.addWidget(self.canvas)
        v.addWidget(self.lbl_summary)
        v.addWidget(self.table)

        # ------------- Splitter / root -------------
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(left_col)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root = QVBoxLayout(self)
        root.addWidget(splitter)

        # Bind to AppState
        self._apply_state_to_spins()
        self._connect_spins_to_state()
        self._connect_state_signals()

        # Initial UI refresh and compute
        self._refresh_effect_labels()
        self.calculate()

    # ──────────────────────────────────────────────────────────
    # UI helpers
    # ──────────────────────────────────────────────────────────

    def _spin(self, minimum: int, maximum: int, value: int) -> QSpinBox:
        sb = QSpinBox()
        sb.setRange(minimum, maximum)
        sb.setValue(value)
        return sb

    def _row_with_effect(self, stat_key: str, spin_widget: QSpinBox) -> QWidget:
        """
        Composite widget used in the FormLayout:
        [ spin ] [  base + buff = total  ]
        Where 'base' is the spin value (user-edited), and 'buff' is derived from AppState buffs.
        """
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(spin_widget)

        lbl = QLabel("")  # will be filled by _refresh_effect_labels
        lbl.setStyleSheet("color: grey")
        lbl.setMinimumWidth(120)
        h.addWidget(lbl, 1, Qt.AlignLeft)

        self._eff_labels[stat_key] = lbl
        return row

    def _build_buffs_box(self) -> QGroupBox:
        """Create a checkbox list for all known buffs."""
        gb = QGroupBox("Buffs")
        v = QVBoxLayout(gb)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(4)

        current = self.state.get_buffs()
        for b in buffs_core.BUFFS:
            cb = QCheckBox(b.label)
            cb.setChecked(bool(current.get(b.key, False)))
            cb.stateChanged.connect(lambda _state, key=b.key: self.state.set_buffs({key: bool(_state)}))
            v.addWidget(cb)
            self._buff_checks[b.key] = cb

        v.addStretch(1)
        return gb

    def _dbg(self, msg: str) -> None:
        """Lightweight checkpoint logger with a timestamp."""
        logging.info("[Farmacologia] %s", msg)

    def _report_exception(self, where: str, exc: Exception) -> None:
        """Show and log a full traceback so you know the exact file/line."""
        tb = traceback.format_exc()
        logging.error("[Farmacologia] ERROR in %s: %s\n%s", where, exc, tb)
        # Optional: surface it in the UI while debugging
        QMessageBox.critical(self, "Erro interno",
                             f"Falha em {where}:\n{exc}\n\n{tb}")


    # ──────────────────────────────────────────────────────────
    # State <-> UI wiring
    # ──────────────────────────────────────────────────────────

    def _schedule_recalc(self):
        self._recalc_timer.start()

    def _apply_state_to_spins(self):
        stats  = self.state.get_stats()
        levels = self.state.get_levels()
        skills = self.state.get_skills()
        with _block_signals(
            self.spin_int, self.spin_des, self.spin_sor,
            self.spin_job, self.spin_base, self.spin_pr, self.spin_cpf, self.spin_adv
        ):
            self.spin_int.setValue(stats["int_stat"])
            self.spin_des.setValue(stats["des_stat"])
            self.spin_sor.setValue(stats["sor_stat"])
            self.spin_job.setValue(levels["job_level"])
            self.spin_base.setValue(levels["base_level"])
            self.spin_pr.setValue(skills["potion_research"])
            self.spin_cpf.setValue(skills["chemical_protection_full"])
            self.spin_adv.setValue(skills["advanced_pharmacy"])

    def _connect_spins_to_state(self):
        # base stats
        self.spin_int.valueChanged.connect(lambda v: self.state.set_stats({"int_stat": v}))
        self.spin_des.valueChanged.connect(lambda v: self.state.set_stats({"des_stat": v}))
        self.spin_sor.valueChanged.connect(lambda v: self.state.set_stats({"sor_stat": v}))
        # levels
        self.spin_job.valueChanged.connect(lambda v: self.state.set_levels({"job_level": v}))
        self.spin_base.valueChanged.connect(lambda v: self.state.set_levels({"base_level": v}))
        # skills
        self.spin_pr.valueChanged.connect(lambda v: self.state.set_skills({"potion_research": v}))
        self.spin_cpf.valueChanged.connect(lambda v: self.state.set_skills({"chemical_protection_full": v}))
        self.spin_adv.valueChanged.connect(lambda v: self.state.set_skills({"advanced_pharmacy": v}))

    def _connect_state_signals(self):
        # reflect state -> UI for base values
        self.state.stats_changed.connect(self._on_stats_changed)
        self.state.levels_changed.connect(self._on_levels_changed)
        self.state.skills_changed.connect(self._on_skills_changed)
        self.state.buffs_changed.connect(self._on_buffs_changed)

        # any change should update badges + recompute
        self.state.stats_changed.connect(self._refresh_effect_labels)
        self.state.buffs_changed.connect(self._refresh_effect_labels)

        self.state.stats_changed.connect(self._schedule_recalc)
        self.state.levels_changed.connect(self._schedule_recalc)
        self.state.skills_changed.connect(self._schedule_recalc)
        self.state.buffs_changed.connect(self._schedule_recalc)

    def _on_stats_changed(self, stats: dict[str, int]):
        with _block_signals(self.spin_int, self.spin_des, self.spin_sor):
            self.spin_int.setValue(stats["int_stat"])
            self.spin_des.setValue(stats["des_stat"])
            self.spin_sor.setValue(stats["sor_stat"])

    def _on_levels_changed(self, levels: dict[str, int]):
        with _block_signals(self.spin_job, self.spin_base):
            self.spin_job.setValue(levels["job_level"])
            self.spin_base.setValue(levels["base_level"])

    def _on_skills_changed(self, skills: dict[str, int]):
        with _block_signals(self.spin_pr, self.spin_cpf, self.spin_adv):
            self.spin_pr.setValue(skills["potion_research"])
            self.spin_cpf.setValue(skills["chemical_protection_full"])
            self.spin_adv.setValue(skills["advanced_pharmacy"])

    def _on_buffs_changed(self, buffs: dict[str, bool]):
        # keep checkboxes in sync (in case we load/reset profile)
        for key, cb in self._buff_checks.items():
            want = bool(buffs.get(key, False))
            if cb.isChecked() != want:
                with _block_signals(cb):
                    cb.setChecked(want)

    # Inline badges: "base + buff = total"
    def _refresh_effect_labels(self):
        base = self.state.get_stats()
        eff = self.state.get_effective_stats()
        for key, lbl in self._eff_labels.items():
            b = int(base.get(key, 0))
            e = int(eff.get(key, b))
            delta = e - b
            sign = "+" if delta >= 0 else "-"
            lbl.setText(f"{b} {sign} {abs(delta)} = {e}")

    # ──────────────────────────────────────────────────────────
    # Compute & publish snapshot
    # ──────────────────────────────────────────────────────────
    def calculate(self):
        """
        Recompute everything. Robust against exceptions (never leaves the table
        frozen black) and logs precise failure points.
        """
        self._dbg("calculate: start")
        t0 = time.time()
        try:
            # ---- Step 1: gather inputs (can’t fail silently now)
            eff_stats = self.state.get_effective_stats()
            self._dbg(f"calculate: got effective stats {eff_stats}")

            int_stat = eff_stats.get("int_stat", self.spin_int.value())
            des_stat = eff_stats.get("des_stat", self.spin_des.value())
            sor_stat = eff_stats.get("sor_stat", self.spin_sor.value())

            job_level = self.spin_job.value()
            base_level = self.spin_base.value()
            pr_level = self.spin_pr.value()
            cpf_level = self.spin_cpf.value()
            adv_level = self.spin_adv.value()

            self._dbg(f"calculate: inputs int={int_stat} des={des_stat} sor={sor_stat} "
                      f"base={base_level} job={job_level} pr={pr_level} cpf={cpf_level} adv={adv_level}")

            # ---- Step 2: enumerate results
            results = enumerate_special_pharmacy_results(
                int_stat, des_stat, sor_stat, job_level, base_level, pr_level, cpf_level
            )
            self._dbg(f"calculate: results len={len(results)}")
            if not results:
                self.canvas.plot_hist([])
                self.table.setRowCount(0)
                self.lbl_summary.setText("Sem resultados.")
                return

            global_min = min(results)
            global_max = max(results)
            max_cap = self.state.pharmacy_special_level_cap(adv_level, fallback=global_max)
            item_ids = self.state.pharmacy_special_item_ids()
            self._dbg(f"calculate: min={global_min} max={global_max} cap={max_cap} items={len(item_ids)}")

            # ---- Step 3: fill table (guard repaints)
            self.table.setUpdatesEnabled(False)
            try:
                self.table.setRowCount(len(item_ids))
                per_item: Dict[str, ItemRow] = {}

                for row, item_id in enumerate(item_ids):
                    # Per-row guard to keep rendering even if one item fails
                    try:
                        name = self.state.catalog_id_to_name(item_id) or f"<id:{item_id}>"
                        difficulty = self.state.pharmacy_special_item_difficulty(item_id, adv_level)
                        distro = pharmacy_special_probability_by_ranges(results, difficulty)
                        p_max = distro["MAX"][1]
                        p_m3 = distro["MAX-3"][1]
                        p_m4 = distro["MAX-4"][1]
                        p_m5 = distro["MAX-5"][1]
                        p_m6 = distro["MAX-6"][1]
                    except Exception as e:
                        self._report_exception(f"table row {row} (item {item_id})", e)
                        name = self.state.catalog_id_to_name(item_id) or f"<id:{item_id}>"
                        difficulty = 0
                        p_max = p_m3 = p_m4 = p_m5 = p_m6 = 0.0

                    weighted_avg = (
                            max_cap * p_max
                            + (max_cap - 3) * p_m3
                            + (max_cap - 4) * p_m4
                            + (max_cap - 5) * p_m5
                            + (max_cap - 6) * p_m6
                    )

                    def _cell(text: str, center: bool = True) -> QTableWidgetItem:
                        it = QTableWidgetItem(text)
                        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                        it.setTextAlignment(Qt.AlignCenter if center else (Qt.AlignVCenter | Qt.AlignLeft))
                        return it

                    it0 = _cell(name, center=False)
                    ico = icon_for_item_id(item_id) or self.style().standardIcon(QStyle.SP_FileIcon)
                    it0.setIcon(ico)
                    self.table.setItem(row, 0, it0)

                    self.table.setItem(row, 1, _cell(str(difficulty)))
                    self.table.setItem(row, 2, _cell(f"{p_max:.2%}"))
                    self.table.setItem(row, 3, _cell(f"{p_m3:.2%}"))
                    self.table.setItem(row, 4, _cell(f"{p_m4:.2%}"))
                    self.table.setItem(row, 5, _cell(f"{p_m5:.2%}"))
                    self.table.setItem(row, 6, _cell(f"{p_m6:.2%}"))
                    self.table.setItem(row, 7, _cell(f"{weighted_avg:.1f}"))

                    per_item[name] = ItemRow(
                        difficulty=difficulty, p_max=p_max, p_m3=p_m3, p_m4=p_m4, p_m5=p_m5, p_m6=p_m6,
                        mean_weighted=weighted_avg,
                    )

            finally:
                # Always re-enable painting (prevents the 'black table' effect)
                self.table.setUpdatesEnabled(True)

            # ---- Step 4: summary + plot + publish snapshot
            self.lbl_summary.setText(
                f"Número Máximo de Poções: {max_cap} | Min: {global_min} | Max: {global_max} "
                f"(Combos: {PHARMACY_SPECIAL_TOTAL_COMBOS})"
            )
            self.canvas.plot_hist(results)

            self.state.set_pharmacy_special_snapshot(PharmacySpecialSnapshot(
                results=results,
                max_cap=max_cap,
                per_item=per_item,
                global_min=global_min,
                global_max=global_max,
            ))

        except Exception as e:
            self._report_exception("calculate()", e)
        finally:
            self._dbg(f"calculate: end (dt={time.time() - t0:.3f}s)")

