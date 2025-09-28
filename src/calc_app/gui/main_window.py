"""
Main window: Welcome page → Tabbed app.

• Zero IO in pages: all persistence/proxies via AppState.
• Tabs are created following TAB_NAMES keys.
• Real pages:
    - 'farmacologia_avancada' (PharmacySpecialPage)
    - 'price_base'           (BasePrecosPage)
    - 'production_cost'      (CustoProducaoPage)
• Remaining keys get a small "under construction" placeholder.
"""

from contextlib import contextmanager
from typing import Optional

from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QDesktopServices, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QStackedWidget,
    QTabWidget, QGridLayout, QSizePolicy, QGroupBox, QStyle, QHBoxLayout,
    QMessageBox, QToolButton, QFormLayout, QSpinBox, QFileDialog, QMenu, QFrame
)

from calc_app.app_state import AppState
from .pages.farmacologia_avancada import PharmacySpecialPage
from .pages.base_precos import BasePrecosPage
from .pages.custo_producao import CustoProducaoPage

from .icons import icon_for_skill, icon_for_social
from ..config import (
    SOCIAL_LINKS, TAB_NAMES, BUTTON_SPECS,
    DEFAULT_FIXED_SIZE, TAB_FIXED_SIZES, SKILL_META
)


WELCOME_TEXT = (
    "<h2>Calculadora Ragnarok</h2>"
    "<p>Bem-vindo! Este programa reúne calculadoras e ferramentas para quem produz itens no "
    "Ragnarok Online. Aqui você encontra módulos de <b>Farmacologia Avançada</b>, base de preços, "
    "custo de produção e utilidades — tudo em uma interface única.</p>"
)

# ──────────────────────────────────────────────────────────────
# Small helpers
# ──────────────────────────────────────────────────────────────

@contextmanager
def _block_signals(*widgets):
    prev = [w.blockSignals(True) for w in widgets]
    try:
        yield
    finally:
        for w in widgets:
            w.blockSignals(False)

def _hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line


# ──────────────────────────────────────────────────────────────
# Main Window
# ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, state: Optional[AppState] = None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Calculadora Ragnarok")
        self._lock_to_size(DEFAULT_FIXED_SIZE)

        # State (single source of truth)
        self.state = state or AppState()

        # Root stack: Welcome → Tabs
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        self.welcome = self._build_welcome()
        self.tabs    = self._build_tabs()

        self.stack.addWidget(self.welcome)
        self.stack.addWidget(self.tabs)
        self.stack.setCurrentWidget(self.welcome)

        self._build_menubar()

    # ── builders ────────────────────────────────────────────────────────────

    def _under_construction(self, title: str) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 24, 24, 24)
        lbl = QLabel(f"<h2>{title}</h2><p>🚧 Em construção…</p>")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        v.addStretch(1); v.addWidget(lbl); v.addStretch(1)
        return w

    def _build_welcome(self) -> QWidget:
        root = QWidget()
        v = QVBoxLayout(root)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(16)

        # Intro
        lbl = QLabel(WELCOME_TEXT); lbl.setWordWrap(True)
        v.addWidget(lbl)

        # Module buttons (open corresponding tab)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12); grid.setVerticalSpacing(8)
        for idx, key in enumerate(TAB_NAMES.keys()):
            label = TAB_NAMES[key]
            btn = QPushButton(label)
            ico = icon_for_skill(BUTTON_SPECS.get(label))
            if ico: btn.setIcon(ico)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _=False, k=key: self._open_tab_by_key(k))
            grid.addWidget(btn, idx // 3, idx % 3)
        v.addLayout(grid)

        # Character editor
        v.addWidget(self._build_character_editor(), 1)

        # Footer: Save Profile
        footer = QHBoxLayout()
        footer.addStretch(1)
        btn_save = QPushButton("Salvar Perfil")
        btn_save.setToolTip("Salvar o perfil (stats/níveis/skills).")
        btn_save.clicked.connect(self._save_profile_now)
        footer.addWidget(btn_save)
        v.addLayout(footer)

        # Socials
        v.addWidget(_hline())
        socials = QHBoxLayout()
        for platform, handle, url in SOCIAL_LINKS[:3]:
            text = handle or platform.title()
            btn = QPushButton(text)
            ico = icon_for_social(platform)
            if ico: btn.setIcon(ico)
            btn.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            socials.addWidget(btn)
        v.addLayout(socials)

        return root

    def _build_tabs(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.North)
        tabs.setDocumentMode(True)

        # Corner "Home" button
        home_btn = QToolButton(tabs)
        home_btn.setAutoRaise(True)
        home_btn.setToolTip("Início")
        home_btn.setIcon(self.style().standardIcon(QStyle.SP_DirHomeIcon))
        home_btn.clicked.connect(lambda: (self.stack.setCurrentWidget(self.welcome),
                                          self._lock_to_size(DEFAULT_FIXED_SIZE)))
        tabs.setCornerWidget(home_btn, Qt.TopRightCorner)

        # Build in TAB_NAMES order
        self._tab_keys: list[str] = []
        for key, label in TAB_NAMES.items():
            if key == "farmacologia_avancada":
                page = self._wrap_with_save_footer(PharmacySpecialPage(self.state))
            elif key == "price_base":
                page = BasePrecosPage(self.state)
            elif key == "production_cost":
                page = CustoProducaoPage(self.state)
            else:
                page = self._under_construction(label)

            ico = icon_for_skill(BUTTON_SPECS.get(label)) or self.style().standardIcon(QStyle.SP_FileIcon)
            tabs.addTab(page, ico, label)
            self._tab_keys.append(key)

        tabs.currentChanged.connect(self._on_tab_changed)
        return tabs

    def _wrap_with_save_footer(self, core_page: QWidget) -> QWidget:
        """Wrap a page adding a bottom-left 'Salvar Perfil' like your screenshot."""
        wrapper = QWidget()
        v = QVBoxLayout(wrapper); v.setContentsMargins(6, 6, 6, 6); v.setSpacing(4)
        v.addWidget(core_page, 1)
        v.addWidget(_hline())
        footer = QHBoxLayout()
        btn = QPushButton("Salvar Perfil")
        btn.setToolTip("Salvar o perfil (stats/níveis/skills).")
        btn.clicked.connect(self._save_profile_now)
        footer.addWidget(btn); footer.addStretch(1)
        v.addLayout(footer)
        return wrapper

    # ── character editor ─────────────────────────────────────────────────────

    def _spin(self, lo: int, hi: int, val: int) -> QSpinBox:
        w = QSpinBox(); w.setRange(lo, hi); w.setValue(val); w.setFixedWidth(120); return w

    def _build_character_editor(self) -> QWidget:
        container = QWidget()
        h = QHBoxLayout(container); h.setSpacing(24)

        # Left: Stats + Levels
        left = QGroupBox("Características (Atributos e Níveis)")
        formL = QFormLayout(left)
        st = self.state.get_stats(); lv = self.state.get_levels()

        self.spin_for  = self._spin(1, 500, st["for_stat"])
        self.spin_agi  = self._spin(1, 500, st["agi_stat"])
        self.spin_vit  = self._spin(1, 500, st["vit_stat"])
        self.spin_int  = self._spin(1, 500, st["int_stat"])
        self.spin_des  = self._spin(1, 500, st["des_stat"])
        self.spin_sor  = self._spin(1, 500, st["sor_stat"])
        self.spin_base = self._spin(101, 175, lv["base_level"])
        self.spin_job  = self._spin(1, 70,   lv["job_level"])

        formL.addRow("FOR", self.spin_for)
        formL.addRow("AGI", self.spin_agi)
        formL.addRow("VIT", self.spin_vit)
        formL.addRow("INT", self.spin_int)
        formL.addRow("DES", self.spin_des)
        formL.addRow("SOR", self.spin_sor)
        formL.addRow("Lv Base", self.spin_base)
        formL.addRow("Lv Classe", self.spin_job)

        # Right: Skills (data-driven)
        right = QGroupBox("Skills")
        self._skills_form: QFormLayout = QFormLayout(right)
        self._skill_spins: dict[str, QSpinBox] = {}

        def skill_label(k: str) -> str:
            meta = SKILL_META.get(k, {})
            return str(meta.get("label") or k.replace("_", " ").title())

        def skill_range(k: str) -> tuple[int, int]:
            meta = SKILL_META.get(k, {})
            return int(meta.get("min", 0)), int(meta.get("max", 10))

        for k, v in self.state.get_skills().items():
            lo, hi = skill_range(k)
            sb = self._spin(lo, hi, v)
            self._skills_form.addRow(skill_label(k), sb)
            self._skill_spins[k] = sb
            sb.valueChanged.connect(lambda val, key=k: self.state.set_skills({key: val}))

        # Layout
        h.addWidget(left); h.addWidget(right); h.addStretch(1)

        # Wire Stats/Levels ←→ State
        self.spin_for.valueChanged.connect(lambda v: self.state.set_stats({"for_stat": v}))
        self.spin_agi.valueChanged.connect(lambda v: self.state.set_stats({"agi_stat": v}))
        self.spin_vit.valueChanged.connect(lambda v: self.state.set_stats({"vit_stat": v}))
        self.spin_int.valueChanged.connect(lambda v: self.state.set_stats({"int_stat": v}))
        self.spin_des.valueChanged.connect(lambda v: self.state.set_stats({"des_stat": v}))
        self.spin_sor.valueChanged.connect(lambda v: self.state.set_stats({"sor_stat": v}))
        self.spin_base.valueChanged.connect(lambda v: self.state.set_levels({"base_level": v}))
        self.spin_job.valueChanged.connect(lambda v: self.state.set_levels({"job_level": v}))

        # Keep UI synced if other tabs change state
        self.state.stats_changed.connect(self._on_stats_changed)
        self.state.levels_changed.connect(self._on_levels_changed)
        self.state.skills_changed.connect(self._on_skills_changed)

        return container

    # UI ← state (no feedback loops)
    def _on_stats_changed(self, s: dict[str, int]):
        with _block_signals(self.spin_for, self.spin_agi, self.spin_vit,
                            self.spin_int, self.spin_des, self.spin_sor):
            self.spin_for.setValue(s["for_stat"]); self.spin_agi.setValue(s["agi_stat"])
            self.spin_vit.setValue(s["vit_stat"]); self.spin_int.setValue(s["int_stat"])
            self.spin_des.setValue(s["des_stat"]); self.spin_sor.setValue(s["sor_stat"])

    def _on_levels_changed(self, lv: dict[str, int]):
        with _block_signals(self.spin_base, self.spin_job):
            self.spin_base.setValue(lv["base_level"]); self.spin_job.setValue(lv["job_level"])

    def _on_skills_changed(self, skills: dict[str, int]):
        # Add any new keys
        for k, v in skills.items():
            if k not in self._skill_spins:
                lo = int(SKILL_META.get(k, {}).get("min", 0))
                hi = int(SKILL_META.get(k, {}).get("max", 10))
                sb = self._spin(lo, hi, v)
                self._skills_form.addRow(k.replace("_", " ").title(), sb)
                self._skill_spins[k] = sb
                sb.valueChanged.connect(lambda val, key=k: self.state.set_skills({key: val}))
        # Update existing
        with _block_signals(*self._skill_spins.values()):
            for k, sb in self._skill_spins.items():
                if k in skills:
                    sb.setValue(skills[k])

    # ── menus / actions ──────────────────────────────────────────────────────

    def _build_menubar(self):
        mb = self.menuBar()

        # File
        m_file = mb.addMenu("&File")

        m_load = QMenu("Load", self)
        act_load_profile = QAction("Character Profile…", self)
        act_load_profile.setShortcut("Ctrl+O")
        act_load_profile.triggered.connect(self._action_load_profile)
        m_load.addAction(act_load_profile)
        m_file.addMenu(m_load)

        m_export = QMenu("Export", self)
        act_export_profile = QAction("Character Profile…", self)
        act_export_profile.setShortcut("Ctrl+Shift+S")
        act_export_profile.triggered.connect(self._action_export_profile)
        m_export.addAction(act_export_profile)
        m_file.addMenu(m_export)

        m_file.addSeparator()
        act_exit = QAction("Exit", self); act_exit.triggered.connect(self.close)
        m_file.addAction(act_exit)

        # Edit
        m_edit = mb.addMenu("&Edit")
        m_reset = QMenu("Reset to Default", self)

        act_reset_profile = QAction("Character Profile", self)
        act_reset_profile.triggered.connect(self._action_reset_profile)
        m_reset.addAction(act_reset_profile)

        act_reset_prices = QAction("Item Prices", self)
        act_reset_prices.triggered.connect(self._action_reset_prices)
        m_reset.addAction(act_reset_prices)

        m_edit.addMenu(m_reset)

        # Help
        m_help = mb.addMenu("&Help")
        act_about = QAction("About", self)
        act_about.triggered.connect(lambda: QMessageBox.about(
            self, "About Calculadora Ragnarok",
            "<h3>Calculadora Ragnarok</h3>"
            "<p>Ferramenta em Python/PySide6 para produção e farmacologia no Ragnarok Online.</p>"
        ))
        m_help.addAction(act_about)

    def _action_load_profile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Character Profile", "", "JSON files (*.json);;All files (*)")
        if not path: return
        try:
            self.state.import_profile_from_file(path)
            QMessageBox.information(self, "Profile Loaded", "Character profile loaded.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load profile:\n{e}")

    def _action_export_profile(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Character Profile", "profile.export.json",
                                              "JSON files (*.json);;All files (*)")
        if not path: return
        try:
            written = self.state.export_profile_to_file(path)
            QMessageBox.information(self, "Profile Exported", f"Exported to:\n{written}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not export profile:\n{e}")

    def _action_reset_profile(self):
        if QMessageBox.question(
            self, "Reset Character Profile",
            "Restore default profile and overwrite your saved one?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        try:
            written = self.state.reset_profile_to_default()
            QMessageBox.information(self, "Profile Reset", f"Default restored at:\n{written}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reset profile:\n{e}")

    def _action_reset_prices(self):
        if QMessageBox.question(
            self, "Reset Item Prices",
            "Copy packaged default prices.json over your user file?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        try:
            written = self.state.reset_prices_to_default()
            QMessageBox.information(self, "Prices Reset", f"Default prices restored at:\n{written}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reset prices:\n{e}")

    def _save_profile_now(self):
        try:
            path = self.state.save_profile()
            QMessageBox.information(self, "Saved", f"Perfil salvo em:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Não foi possível salvar o perfil:\n{e}")

    # ── navigation / sizing ──────────────────────────────────────────────────

    def _open_tab_by_key(self, key: str) -> None:
        label = TAB_NAMES.get(key, "")
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == label:
                self.stack.setCurrentWidget(self.tabs)
                self.tabs.setCurrentIndex(i)
                self._lock_to_size(TAB_FIXED_SIZES.get(key, DEFAULT_FIXED_SIZE))
                return
        self.stack.setCurrentWidget(self.tabs)
        self._lock_to_size(TAB_FIXED_SIZES.get(key, DEFAULT_FIXED_SIZE))

    def _lock_to_size(self, size: QSize) -> None:
        self.setFixedSize(size)

    def _on_tab_changed(self, index: int) -> None:
        # Lock size according to TAB_NAMES key at this index
        if 0 <= index < self.tabs.count():
            key = list(TAB_NAMES.keys())[index]
            self._lock_to_size(TAB_FIXED_SIZES.get(key, DEFAULT_FIXED_SIZE))


# Factory for __main__
def create_main_window(state: Optional[AppState] = None) -> MainWindow:
    return MainWindow(state=state)
