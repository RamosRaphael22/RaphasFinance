"""Janela principal e navegação inicial."""

import customtkinter as ctk


COLORS = {
    "background": "#080D0A",
    "sidebar": "#0D1510",
    "surface": "#141F18",
    "surface_hover": "#1B2B20",
    "accent": "#22C55E",
    "accent_hover": "#16A34A",
    "active": "#183A25",
    "text": "#E8F3EB",
    "muted": "#9BB1A1",
    "border": "#2A4533",
}

from finance_app.config import APP_TITLE, DATA_DIR, MIN_WINDOW_SIZE, WINDOW_SIZE
from finance_app.domain.models import Account, Category
from finance_app.services import (
    BalanceService,
    CatalogService,
    TransactionService,
    TransferService,
    PlanningService,
    RecurrenceService,
    SummaryService,
    ForecastService,
    PortabilityService,
)
from finance_app.storage.csv_store import CsvStore
from finance_app.ui.views.catalog import CatalogView
from finance_app.ui.views.transactions import TransactionView
from finance_app.ui.views.transfers import TransferView
from finance_app.ui.views.planning import PlanningView
from finance_app.ui.views.recurrences import RecurrenceView
from finance_app.ui.views.dashboard import DashboardView
from finance_app.ui.views.forecasts import ForecastView
from finance_app.ui.views.data_tools import DataToolsView


class FinanceApp(ctk.CTk):
    """Janela inicial com navegação para as áreas pessoais do app."""

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(*MIN_WINDOW_SIZE)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        self.configure(fg_color=COLORS["background"])
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        store = CsvStore(DATA_DIR)
        self.catalogs = CatalogService(store)
        self.transactions = TransactionService(store)
        self.transfers = TransferService(store)
        self.balances = BalanceService(store)
        self.planning = PlanningService(store)
        self.recurrences = RecurrenceService(store)
        self.summaries = SummaryService(store)
        self.forecasts = ForecastService(store)
        self.portability = PortabilityService(store)
        self._build_layout()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(
            self, width=220, corner_radius=0, fg_color=COLORS["sidebar"],
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="Minhas Finanças",
            font=ctk.CTkFont(size=21, weight="bold"),
            text_color=COLORS["text"],
        ).pack(padx=20, pady=(30, 28), anchor="w")

        for label in (
            "Visão geral", "Lançamentos", "Transferências", "Contas",
            "Categorias", "Planejamento", "Recorrências", "Previsões",
            "Dados e backup",
        ):
            button = ctk.CTkButton(
                sidebar,
                text=label,
                anchor="w",
                fg_color="transparent",
                text_color=COLORS["muted"],
                hover_color=COLORS["surface_hover"],
                height=40,
                corner_radius=9,
                command=lambda item=label: self._show_section(item),
            )
            button.pack(fill="x", padx=12, pady=3)
            self._nav_buttons[label] = button

        self.content = ctk.CTkFrame(self, fg_color=COLORS["background"])
        self.content.grid(row=0, column=1, sticky="nsew", padx=32, pady=28)
        self._show_section("Visão geral")

    def _show_section(self, section: str) -> None:
        for label, button in self._nav_buttons.items():
            selected = label == section
            button.configure(
                fg_color=COLORS["active"] if selected else "transparent",
                text_color=COLORS["accent"] if selected else COLORS["muted"],
                hover_color=COLORS["surface_hover"],
            )
        for child in self.content.winfo_children():
            child.destroy()

        if section == "Contas":
            CatalogView(
                self.content, self.catalogs, Account, self.balances,
            ).pack(fill="both", expand=True)
            return
        if section == "Categorias":
            CatalogView(self.content, self.catalogs, Category).pack(fill="both", expand=True)
            return
        if section == "Lançamentos":
            TransactionView(self.content, self.transactions, self.catalogs).pack(
                fill="both", expand=True,
            )
            return
        if section == "Transferências":
            TransferView(self.content, self.transfers, self.catalogs).pack(
                fill="both", expand=True,
            )
            return
        if section == "Planejamento":
            PlanningView(self.content, self.planning, self.catalogs, section).pack(
                fill="both", expand=True,
            )
            return
        if section == "Recorrências":
            RecurrenceView(self.content, self.recurrences, self.catalogs).pack(
                fill="both", expand=True,
            )
            return
        if section == "Visão geral":
            DashboardView(self.content, self.summaries).pack(fill="both", expand=True)
            return
        if section == "Previsões":
            ForecastView(self.content, self.forecasts).pack(fill="both", expand=True)
            return
        if section == "Dados e backup":
            DataToolsView(self.content, self.portability).pack(fill="both", expand=True)
            return

        ctk.CTkLabel(
            self.content,
            text="Área não encontrada",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(anchor="w", pady=(8, 12))
        ctk.CTkLabel(
            self.content,
            text="Selecione uma das áreas disponíveis no menu.",
            justify="left",
            anchor="w",
            wraplength=680,
            font=ctk.CTkFont(size=15),
        ).pack(anchor="w", pady=8)
