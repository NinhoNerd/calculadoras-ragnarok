# src/calc_app/gui/pages/custo_producao.py
from typing import List, Tuple, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QStyle
)

from ..icons import icon_for_item_id
from calc_app.app_state import AppState, PharmacySpecialSnapshot
from ...core import catalog


class CustoProducaoPage(QWidget):
    """
    Cálculo:
      custo_materiais_por_uso = Σ(preço(material) * qtd)
      media_por_uso           = snapshot Farmacologia (mean_weighted) pelo NOME do item final
      custo_unitario          = custo_materiais_por_uso / media_por_uso
    Considera apenas itens do catálogo com type='final'.

    Atualiza sempre que:
      • AppState.pharmacy_special_changed (novo snapshot da Farmacologia)
      • AppState.base_prices_changed      (novo snapshot da Base de Preços)
    """

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state

        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(8)
        v.addWidget(QLabel(
            "<h3>Custo de Produção</h3>"
            "<p>Usa a <b>Base de Preços</b> e a <i>média</i> calculada em Farmacologia.</p>"
        ))

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(
            ["Item", "Custo Materiais/uso", "Média por uso", "Custo unitário", "Receita"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        v.addWidget(self.table)

        # Recompute when Farmacologia publishes OR when Base de Preços publishes
        self.state.pharmacy_special_changed.connect(self._recompute)
        self.state.base_prices_changed.connect(lambda _snap: self._recompute(self.state.pharmacy_special()))

        # Initial paint
        self._recompute(self.state.pharmacy_special())

    # Ensure it's fresh whenever the tab becomes visible
    def showEvent(self, ev):
        self._recompute(self.state.pharmacy_special())
        super().showEvent(ev)

    # ── core ────────────────────────────────────────────────────────────────

    def _materials_cost_per_use(self, recipe: List[Tuple[int, int]]) -> int:
        total = 0
        # Uses latest prices mirrored from BasePricesSnapshot (user → default → live)
        prices = self.state.load_prices_blob()
        for mid, qty in recipe:
            price = int(prices.get(str(mid), 0))
            total += price * int(qty)
        return total

    def _mean_from_snapshot(self, item_name: str, snap: Optional[PharmacySpecialSnapshot]) -> Optional[float]:
        if not snap:
            return None
        row = snap.per_item.get(item_name)
        if not row:
            return None
        return float(row.get("mean_weighted") or 0.0)

    def _recipe_str(self, recipe: List[Tuple[int, int]]) -> str:
        parts = []
        for mid, qty in recipe:
            nm = catalog.id_to_name(mid) or f"#{mid}"
            parts.append(f"{nm}×{qty}")
        return ", ".join(parts)

    def _recompute(self, snap_obj) -> None:
        """
        Rebuilds the table using:
          - current Base Preços (via state.load_prices_blob())
          - current Farmacologia snapshot (snap_obj)
          - catalog for final items and recipes
        """
        snap = snap_obj  # PharmacySpecialSnapshot | None
        finals = catalog.final_item_ids()

        rows = []  # (iid, name, mat_cost, mean, unit_cost, recipe_str)
        for iid in finals:
            name = catalog.id_to_name(iid) or f"#{iid}"
            recipe = catalog.parsed_recipe(iid)
            mat = self._materials_cost_per_use(recipe)
            mean = self._mean_from_snapshot(name, snap) or 0.0
            unit = (mat / mean) if mean > 0 else None
            rows.append((iid, name, mat, mean, unit, self._recipe_str(recipe)))

        # Deterministic order: alphabetical by name (then id)
        rows.sort(key=lambda t: (t[1].casefold(), t[0]))

        self.table.setRowCount(len(rows))
        for r, (iid, name, mat_cost, mean, unit_cost, rec_str) in enumerate(rows):
            it_name = QTableWidgetItem(name)
            ico = icon_for_item_id(iid) or self.style().standardIcon(QStyle.SP_FileIcon)
            it_name.setIcon(ico)
            it_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            it_mat = QTableWidgetItem(f"{mat_cost:,}".replace(",", "."))
            it_mean = QTableWidgetItem(f"{mean:.2f}")
            it_unit = QTableWidgetItem("-" if unit_cost is None else f"{unit_cost:.2f}")
            it_rec = QTableWidgetItem(rec_str)

            for itm in (it_mat, it_mean, it_unit):
                itm.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_rec.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            self.table.setItem(r, 0, it_name)
            self.table.setItem(r, 1, it_mat)
            self.table.setItem(r, 2, it_mean)
            self.table.setItem(r, 3, it_unit)
            self.table.setItem(r, 4, it_rec)
