"""Painel de totais, saldos e gráficos realizados por período."""

import tkinter as tk
from datetime import date, datetime
from decimal import Decimal

import customtkinter as ctk

from finance_app.config import DATA_DIR
from finance_app.analytics.summaries import FinancialSummary
from finance_app.services import SummaryService
from finance_app.storage.csv_store import StorageError
from finance_app.storage.dashboard_preferences import DashboardPeriodPreferences
from finance_app.ui.formatting import format_brl_amount


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, service: SummaryService) -> None:
        super().__init__(master, fg_color="transparent")
        self.service = service
        self.period_preferences = DashboardPeriodPreferences(DATA_DIR / "dashboard_period.json")
        self.summary: FinancialSummary | None = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        ctk.CTkLabel(self, text="Visão geral", font=ctk.CTkFont(size=28, weight="bold")).grid(row=0, column=0, sticky="w", pady=(4, 2))
        ctk.CTkLabel(self, text="Receitas e despesas no período; o saldo considera movimentações em dinheiro e pagamentos de fatura.", anchor="w").grid(row=1, column=0, sticky="w", pady=(0, 8))

        filters = ctk.CTkFrame(self)
        filters.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self._label(filters, "De (DD/MM/AAAA)", 0, 0)
        self.start_input = ctk.CTkEntry(filters, width=145)
        self.start_input.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="w")
        self._label(filters, "Até (DD/MM/AAAA)", 0, 1)
        self.end_input = ctk.CTkEntry(filters, width=145)
        self.end_input.grid(row=1, column=1, padx=8, pady=(0, 8), sticky="w")
        ctk.CTkButton(filters, text="Atualizar painel", command=self.refresh).grid(row=1, column=2, padx=8, pady=(0, 8), sticky="w")
        self.message = ctk.CTkLabel(filters, text="", anchor="w")
        self.message.grid(row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 6))

        today = date.today()
        first_month = today.month - 11
        year = today.year
        while first_month <= 0:
            first_month += 12; year -= 1
        start_date, end_date = date(year, first_month, 1), today
        try:
            saved_period = self.period_preferences.load()
            if saved_period:
                start_date, end_date = saved_period
        except (OSError, ValueError, KeyError, TypeError):
            pass
        self.start_input.insert(0, start_date.strftime("%d/%m/%Y"))
        self.end_input.insert(0, end_date.strftime("%d/%m/%Y"))
        self.start_input.bind("<KeyRelease>", self._persist_period_inputs)
        self.end_input.bind("<KeyRelease>", self._persist_period_inputs)

        self.metrics = ctk.CTkFrame(self, fg_color="transparent")
        self.metrics.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        self.metric_values = {}
        for column, (key, label) in enumerate((
            ("income", "Receitas"), ("expenses", "Despesas"), ("result", "Saldo"),
        )):
            self.metrics.grid_columnconfigure(column, weight=1)
            card = ctk.CTkFrame(self.metrics)
            card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 5, 0))
            ctk.CTkLabel(card, text=label, anchor="w", text_color=("gray35", "gray70")).pack(anchor="w", padx=12, pady=(8, 0))
            value = ctk.CTkLabel(card, text="R$ 0,00", anchor="w", font=ctk.CTkFont(size=19, weight="bold"))
            value.pack(anchor="w", padx=12, pady=(0, 8)); self.metric_values[key] = value

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=4, column=0, sticky="nsew")
        self.refresh()

    @staticmethod
    def _label(parent, text, row, column):
        ctk.CTkLabel(parent, text=text).grid(row=row, column=column, sticky="w", padx=8, pady=(7, 2))

    def _persist_period_inputs(self, _event=None) -> None:
        try:
            start = datetime.strptime(self.start_input.get().strip(), "%d/%m/%Y").date()
            end = datetime.strptime(self.end_input.get().strip(), "%d/%m/%Y").date()
            self.period_preferences.save(start, end)
        except ValueError:
            return
        except OSError as exc:
            self.message.configure(text=f"Não foi possível salvar as datas: {exc}")

    def refresh(self):
        try:
            start = datetime.strptime(self.start_input.get().strip(), "%d/%m/%Y").date()
            end = datetime.strptime(self.end_input.get().strip(), "%d/%m/%Y").date()
            summary = self.service.summarize(start, end)
        except StorageError as exc:
            self.message.configure(text=f"Não foi possível ler os dados: {exc}"); return
        except ValueError:
            self.message.configure(text="Informe as datas como DD/MM/AAAA e confira o intervalo."); return
        except OSError as exc:
            self.message.configure(text=f"Não foi possível ler os dados: {exc}"); return
        try:
            self.period_preferences.save(start, end)
        except OSError as exc:
            self.message.configure(
                text=f"Período atualizado, mas não foi possível salvar as datas: {exc}"
            )
        else:
            self.message.configure(
                text=f"Período: {start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}. "
                "Transferências não entram nos totais de receitas e despesas."
            )
        self.summary = summary
        for key, amount in (("income", summary.income), ("expenses", summary.expenses), ("result", summary.cash_flow)):
            self.metric_values[key].configure(text=format_brl_amount(amount))
        for child in self.body.winfo_children(): child.destroy()
        self._render_balances(summary)
        self._render_categories(summary)
        self._render_monthly(summary)

    def _section(self, title: str) -> ctk.CTkFrame:
        block = ctk.CTkFrame(self.body)
        block.pack(fill="x", padx=2, pady=(0, 10))
        ctk.CTkLabel(block, text=title, font=ctk.CTkFont(size=17, weight="bold"), anchor="w").pack(fill="x", padx=12, pady=(9, 4))
        return block

    def _render_balances(self, summary: FinancialSummary):
        block = self._section("Saldos por conta no fim do período")
        if not summary.balances:
            ctk.CTkLabel(block, text="Cadastre contas para acompanhar saldos.", anchor="w").pack(fill="x", padx=12, pady=(0, 10)); return
        for item in summary.balances:
            kind = "Fatura em aberto" if item.account.kind == "credit_card" else "Saldo"
            ctk.CTkLabel(block, text=f"{item.account.name} · {kind}: {format_brl_amount(item.amount)}", anchor="w").pack(fill="x", padx=12, pady=(0, 6))
        ctk.CTkLabel(block, text="Inclui o saldo inicial e todo o histórico registrado até a data final.", anchor="w", text_color=("gray35", "gray70")).pack(fill="x", padx=12, pady=(0, 10))

    def _create_chart_canvas(self, parent, height: int):
        dark = ctk.get_appearance_mode() == "Dark"
        canvas = tk.Canvas(parent, height=height, bg="#141F18" if dark else "#f2f2f2",
                          highlightthickness=0, bd=0)
        canvas.pack(fill="x", padx=8, pady=(0, 10))
        return canvas, ("#E8F3EB" if dark else "#202020")

    def _render_categories(self, summary: FinancialSummary):
        block = self._section("Despesas por categoria")
        if not summary.category_expenses:
            ctk.CTkLabel(block, text="Sem despesas no período selecionado.", anchor="w").pack(fill="x", padx=12, pady=(0, 10)); return
        canvas, foreground = self._create_chart_canvas(block, max(76, len(summary.category_expenses) * 34 + 18))
        values = summary.category_expenses
        maximum = max(item.amount for item in values)
        def draw(event=None):
            width = max(canvas.winfo_width(), 420); canvas.delete("all")
            bar_left = min(245, max(145, width // 3)); available = max(width - bar_left - 125, 40)
            for index, item in enumerate(values):
                y = 17 + index * 34
                canvas.create_text(8, y + 8, text=item.name, anchor="w", fill=foreground)
                bar_width = int(item.amount / maximum * Decimal(available)) if maximum else 0
                canvas.create_rectangle(bar_left, y, bar_left + bar_width, y + 17, fill="#F87171", outline="")
                canvas.create_text(width - 8, y + 8, text=format_brl_amount(item.amount), anchor="e", fill=foreground)
        canvas.bind("<Configure>", draw); draw()

    def _render_monthly(self, summary: FinancialSummary):
        block = self._section("Evolução mensal")
        if not summary.monthly_totals:
            ctk.CTkLabel(block, text="Sem meses no período selecionado.", anchor="w").pack(fill="x", padx=12, pady=(0, 10)); return
        legend = ctk.CTkLabel(block, text="Receitas em verde  ·  Despesas em vermelho-claro", anchor="w", text_color=("gray35", "gray70"))
        legend.pack(fill="x", padx=12, pady=(0, 4))
        canvas, foreground = self._create_chart_canvas(block, max(88, len(summary.monthly_totals) * 42 + 20))
        values = summary.monthly_totals
        maximum = max((max(item.income, item.expenses) for item in values), default=0)
        def draw(event=None):
            width = max(canvas.winfo_width(), 420); canvas.delete("all")
            bar_left = 95; available = max(width - bar_left - 135, 40)
            for index, item in enumerate(values):
                y = 8 + index * 42
                year, month = map(int, item.month.split("-"))
                label = f"{calendar_month(month)}/{str(year)[-2:]}"
                canvas.create_text(8, y + 13, text=label, anchor="w", fill=foreground)
                income_width = int(item.income / maximum * Decimal(available)) if maximum else 0
                expense_width = int(item.expenses / maximum * Decimal(available)) if maximum else 0
                canvas.create_rectangle(bar_left, y + 2, bar_left + income_width, y + 12, fill="#22C55E", outline="")
                canvas.create_rectangle(bar_left, y + 16, bar_left + expense_width, y + 26, fill="#F87171", outline="")
                right = max(item.income, item.expenses)
                canvas.create_text(width - 8, y + 13, text=format_brl_amount(right), anchor="e", fill=foreground)
        canvas.bind("<Configure>", draw); draw()


def calendar_month(month: int) -> str:
    return ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")[month - 1]
