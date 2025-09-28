# src/calc_app/gui/pages/base_precos.py
from typing import Dict, List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QLineEdit, QSizePolicy, QMessageBox, QGridLayout, QSpacerItem
)

from ..icons import icon_for_item_id
from calc_app.app_state import AppState, BasePricesSnapshot
from ...core import catalog


class BasePrecosPage(QWidget):
    """
    Base de Preços (grade 3-col):
      • Cada 'célula' = [ícone] Nome ............ [input preço]
      • Fonte: snapshot de preços publicado pelo AppState (user→default→live)
      • Ao editar: publica um snapshot "live" (sem gravar disco)
      • Ao salvar: persiste e publica snapshot "user"
    """

    COLUMNS = 3
    CELL_PRICE_WIDTH = 120

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state

        # ── Layout raiz ──
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        title = QLabel("<h3>Base de Preços</h3><p>Edite os preços e clique em salvar.</p>")
        title.setTextFormat(Qt.RichText)
        root.addWidget(title)

        # ── Área rolável ──
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(self.scroll, 1)

        self._content = QWidget()
        self._grid: QGridLayout = QGridLayout(self._content)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(18)
        self._grid.setVerticalSpacing(10)
        self.scroll.setWidget(self._content)

        # ── Barra de ações ──
        actions = QHBoxLayout()
        self.btn_save = QPushButton("Salvar preços")
        self.btn_save.setToolTip("Salvar os preços no arquivo do usuário.")
        self.btn_save.clicked.connect(self._save)
        actions.addWidget(self.btn_save)
        actions.addStretch(1)
        root.addLayout(actions)

        # Mapa id -> QLineEdit (somente widgets atuais)
        self._price_edits: Dict[int, QLineEdit] = {}

        # Re-render when a new snapshot is published (reset/save/live edits)
        self.state.base_prices_changed.connect(self._render_from_snapshot)

        # Initial render
        snap = self.state.base_prices()
        if snap is not None:
            self._render_from_snapshot(snap)

    # ──────────────────────────────────────────────────────────────────────
    # Render
    # ──────────────────────────────────────────────────────────────────────
    def _render_from_snapshot(self, snap: BasePricesSnapshot) -> None:
        """
        Rebuild the grid from a BasePricesSnapshot.
        """
        self._clear_grid()
        self._price_edits.clear()

        if not snap.rows:
            self._grid.setRowStretch(0, 1)
            return

        for idx, row in enumerate(snap.rows):
            iid = int(row["item_id"]); name = row["name"]; price = int(row["price"])
            r = idx // self.COLUMNS
            c = idx % self.COLUMNS
            self._grid.addWidget(self._make_cell(iid, name, price), r, c)

        # fill remaining cells with spacers for alignment
        last_row = (len(snap.rows) - 1) // self.COLUMNS
        remainder = len(snap.rows) % self.COLUMNS
        if remainder != 0:
            for c in range(remainder, self.COLUMNS):
                self._grid.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum), last_row, c)

        self._grid.setRowStretch(self._grid.rowCount(), 1)

    def _make_cell(self, iid: int, name: str, price: int) -> QWidget:
        """
        One cell: [icon] name ... [QLineEdit price]
        """
        cell = QFrame()
        cell.setFrameShape(QFrame.StyledPanel)
        cell.setObjectName("priceCell")
        cell.setStyleSheet("#priceCell { border: 1px solid rgba(0,0,0,20); border-radius: 6px; }")

        h = QHBoxLayout(cell)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(10)

        icon_label = QLabel()
        icon = icon_for_item_id(iid)
        if icon:
            icon_label.setPixmap(icon.pixmap(20, 20))
        icon_label.setFixedWidth(24)
        h.addWidget(icon_label, 0, Qt.AlignVCenter)

        name_label = QLabel(name)
        name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        h.addWidget(name_label, 1)

        edit = QLineEdit(str(price))
        edit.setAlignment(Qt.AlignRight)
        edit.setValidator(QIntValidator(0, 2_000_000_000, edit))
        edit.setFixedWidth(self.CELL_PRICE_WIDTH)
        edit.setPlaceholderText("0")
        self._price_edits[iid] = edit
        h.addWidget(edit, 0, Qt.AlignRight)

        # Publish live snapshot when the user finishes editing this field
        edit.editingFinished.connect(self._on_any_edit_finished)

        return cell

    def _clear_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    # ──────────────────────────────────────────────────────────────────────
    # Collect → Publish (live) / Save (persist + publish)
    # ──────────────────────────────────────────────────────────────────────
    def _collect_current_blob(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for iid, edit in self._price_edits.items():
            txt = (edit.text() or "").strip()
            if not txt:
                continue
            try:
                v = int(txt)
                if v < 0: v = 0
                out[str(iid)] = v
            except Exception:
                pass
        return out

    def _on_any_edit_finished(self) -> None:
        """
        Push a *live* snapshot so consumers (e.g., Custo de Produção) update immediately.
        """
        self.state.set_prices_live(self._collect_current_blob())

    def _save(self) -> None:
        """
        Persist prices, then publish a snapshot sourced as 'user'.
        """
        out = self._collect_current_blob()
        written_path = self.state.save_prices_blob(out)

        self.btn_save.setText("Salvo!")
        self.btn_save.setEnabled(False); self.btn_save.setEnabled(True)
        self.btn_save.setText("Salvar preços")
        QMessageBox.information(self, "Saved", f"Preços salvos em:\n{written_path}")
