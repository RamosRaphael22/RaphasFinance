"""Apresenta projeções claramente separadas dos valores realizados."""

import customtkinter as ctk

from finance_app.analytics.forecasts import ForecastResult
from finance_app.services import ForecastService
from finance_app.ui.formatting import format_brl_amount


class ForecastView(ctk.CTkFrame):
    def __init__(self, master, service: ForecastService) -> None:
        super().__init__(master, fg_color="transparent")
        self.service = service
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(self, text="Previsões básicas", font=ctk.CTkFont(size=28, weight="bold")).grid(row=0, column=0, sticky="w", pady=(4, 3))
        ctk.CTkLabel(self, text="Estimativa baseada somente no seu histórico recente de receitas e despesas.", anchor="w").grid(row=1, column=0, sticky="w", pady=(0, 12))
        controls = ctk.CTkFrame(self); controls.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(controls, text="Horizonte").pack(side="left", padx=(10, 6), pady=9)
        self.horizon = ctk.CTkOptionMenu(controls, values=["3 meses", "6 meses", "12 meses"], command=lambda _: self.refresh())
        self.horizon.pack(side="left", padx=5, pady=8)
        self.message = ctk.CTkLabel(controls, text="", anchor="w", wraplength=680)
        self.message.pack(side="left", fill="x", expand=True, padx=10)
        self.content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content.grid(row=3, column=0, sticky="nsew")
        self.refresh()

    def refresh(self):
        try:
            months = int(self.horizon.get().split()[0])
            result = self.service.forecast(months_ahead=months)
        except (ValueError, OSError) as exc:
            self.message.configure(text=f"Não foi possível calcular a previsão: {exc}"); return
        for child in self.content.winfo_children(): child.destroy()
        if not result.available:
            self.message.configure(text="Previsão indisponível")
            card = ctk.CTkFrame(self.content)
            card.pack(fill="x", padx=2, pady=4)
            ctk.CTkLabel(card, text=result.reason, anchor="w", justify="left", wraplength=700).pack(fill="x", padx=14, pady=14)
            ctk.CTkLabel(self.content, text="São necessários seis meses completos de histórico e atividade registrada em pelo menos quatro desses meses.", anchor="w", wraplength=700, justify="left", text_color=("gray35", "gray70")).pack(fill="x", padx=4, pady=(8, 4))
            return
        self.message.configure(text="Estimativa, não valor realizado")
        start = _month_label(result.history_start.strftime("%Y-%m"))
        end = _month_label(result.history_end.strftime("%Y-%m"))
        ctk.CTkLabel(self.content, text=f"Histórico usado: {start} a {end} · seis meses completos · atividade em {result.months_with_activity} meses", anchor="w").pack(fill="x", padx=4, pady=(0, 8))
        notice = ctk.CTkFrame(self.content, fg_color=("#fff0cc", "#183A25"))
        notice.pack(fill="x", padx=2, pady=(0, 10))
        ctk.CTkLabel(notice, text="PROJEÇÃO · NÃO REALIZADO", font=ctk.CTkFont(weight="bold"), text_color=("#805500", "#86EFAC"), anchor="w").pack(fill="x", padx=12, pady=(9, 2))
        ctk.CTkLabel(notice, text="Média simples dos seis meses completos anteriores. Meses sem lançamentos contam como zero; não considera sazonalidade, inflação, mudanças futuras ou eventos atípicos. Não é aconselhamento financeiro.", anchor="w", justify="left", wraplength=720).pack(fill="x", padx=12, pady=(0, 10))
        header = ctk.CTkFrame(self.content, fg_color="transparent"); header.pack(fill="x", padx=3, pady=(0, 3))
        for column in range(4): header.grid_columnconfigure(column, weight=1)
        for col, label in enumerate(("Mês", "Receitas estimadas", "Despesas estimadas", "Resultado estimado")):
            ctk.CTkLabel(header, text=label, font=ctk.CTkFont(weight="bold"), anchor="w" if col == 0 else "e").grid(row=0, column=col, sticky="ew", padx=8)
        for item in result.forecasts:
            row = ctk.CTkFrame(self.content, fg_color=("#fff8e8", "#141F18")); row.pack(fill="x", padx=2, pady=3)
            for column in range(4): row.grid_columnconfigure(column, weight=1)
            values = (_month_label(item.month), format_brl_amount(item.income), format_brl_amount(item.expenses), format_brl_amount(item.result))
            for col, value in enumerate(values):
                ctk.CTkLabel(row, text=value, anchor="w" if col == 0 else "e").grid(row=0, column=col, sticky="ew", padx=8, pady=9)


def _month_label(value: str) -> str:
    year, month = value.split("-")
    names = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
    return f"{names[int(month) - 1]}/{year}"
