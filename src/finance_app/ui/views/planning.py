"""Telas de desejos, metas pessoais e orçamentos mensais."""

import tkinter.messagebox as messagebox
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

import customtkinter as ctk

from finance_app.domain.models import Budget, Category, Goal, Wish
from finance_app.services import CatalogService, PlanningService
from finance_app.ui.formatting import format_brl_amount, parse_brl_amount


class PlanningView(ctk.CTkFrame):
    def __init__(self, master, service: PlanningService, catalogs: CatalogService,
                 initial_tab: str = "Planejamento") -> None:
        super().__init__(master, fg_color="transparent")
        self.service, self.catalogs = service, catalogs
        self.editing: dict[str, object | None] = {"Desejos": None, "Metas": None, "Orçamentos": None}
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True)
        for name in ("Desejos", "Metas", "Orçamentos"):
            self.tabs.add(name)
        self._build_personal_tab("Desejos", Wish)
        self._build_personal_tab("Metas", Goal)
        self._build_budget_tab()
        self.tabs.set("Orçamentos" if initial_tab == "Orçamentos" else "Metas" if initial_tab == "Metas" else "Desejos")

    def _build_personal_tab(self, tab: str, model: type) -> None:
        panel = self.tabs.tab(tab)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(panel, text="Registre valores reservados e acompanhe o progresso.", anchor="w").grid(row=0, column=0, sticky="ew", pady=(4, 10))
        form = ctk.CTkFrame(panel)
        form.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        for col in range(4): form.grid_columnconfigure(col, weight=1)
        self._label(form, "Nome", 0, 0)
        name = ctk.CTkEntry(form, placeholder_text="Ex.: viagem, reserva de emergência")
        name.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 7))
        amount_title = "Valor estimado (R$)" if model is Wish else "Valor desejado (R$)"
        self._label(form, amount_title, 0, 1)
        target = ctk.CTkEntry(form, placeholder_text="0,00")
        target.grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 7))
        self._label(form, "Já reservado (R$)", 0, 2)
        saved = ctk.CTkEntry(form, placeholder_text="0,00")
        saved.grid(row=1, column=2, sticky="ew", padx=8, pady=(0, 7))
        self._label(form, "Prioridade", 0, 3)
        priority = ctk.CTkOptionMenu(form, values=["Baixa", "Média", "Alta"])
        priority.grid(row=1, column=3, sticky="ew", padx=8, pady=(0, 7))
        self._label(form, "Prazo opcional (DD/MM/AAAA)", 2, 0)
        due = ctk.CTkEntry(form, placeholder_text="DD/MM/AAAA")
        due.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 7))
        self._label(form, "Situação", 2, 1)
        choices = ["Planejado", "Realizado", "Cancelado"] if model is Wish else ["Em andamento", "Concluída", "Pausada"]
        status = ctk.CTkOptionMenu(form, values=choices)
        status.grid(row=3, column=1, sticky="ew", padx=8, pady=(0, 7))
        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(row=3, column=2, columnspan=2, sticky="e", padx=8, pady=(0, 7))
        cancel = ctk.CTkButton(actions, text="Cancelar edição", width=120, command=lambda: self._clear(tab))
        save = ctk.CTkButton(actions, text="Salvar", width=100)
        save.pack(side="right")
        cancel.pack(side="right", padx=(0, 6)); cancel.pack_forget()
        msg = ctk.CTkLabel(form, text="", anchor="w", wraplength=740)
        msg.grid(row=4, column=0, columnspan=4, sticky="ew", padx=8, pady=(0, 7))
        rows = ctk.CTkScrollableFrame(panel, label_text="Acompanhamento")
        rows.grid(row=2, column=0, sticky="nsew")
        refs = {"name": name, "target": target, "saved": saved, "priority": priority,
                "due": due, "status": status, "cancel": cancel, "save": save, "msg": msg,
                "rows": rows, "model": model}
        setattr(self, f"_{tab.lower()}_refs", refs)
        save.configure(command=lambda: self._save_personal(tab, refs))
        self._refresh_personal(tab, refs)

    def _build_budget_tab(self) -> None:
        panel = self.tabs.tab("Orçamentos")
        panel.grid_columnconfigure(0, weight=1); panel.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(panel, text="Defina um limite por categoria e mês; ultrapassar o limite não bloqueia lançamentos.", anchor="w", wraplength=760).grid(row=0, column=0, sticky="ew", pady=(4, 10))
        form = ctk.CTkFrame(panel); form.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        for col in range(4): form.grid_columnconfigure(col, weight=1)
        self._label(form, "Categoria de despesa", 0, 0)
        category = ctk.CTkOptionMenu(form, values=["Cadastre uma categoria"])
        category.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 7))
        self._label(form, "Mês (AAAA-MM)", 0, 1)
        period = ctk.CTkEntry(form, placeholder_text=date.today().strftime("%Y-%m")); period.insert(0, date.today().strftime("%Y-%m"))
        period.grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 7))
        self._label(form, "Limite (R$)", 0, 2)
        amount = ctk.CTkEntry(form, placeholder_text="0,00")
        amount.grid(row=1, column=2, sticky="ew", padx=8, pady=(0, 7))
        actions = ctk.CTkFrame(form, fg_color="transparent"); actions.grid(row=1, column=3, sticky="e", padx=8)
        cancel = ctk.CTkButton(actions, text="Cancelar", width=84, command=lambda: self._clear("Orçamentos"))
        save = ctk.CTkButton(actions, text="Salvar", width=95, command=self._save_budget)
        save.pack(side="right"); cancel.pack(side="right", padx=(0, 5)); cancel.pack_forget()
        msg = ctk.CTkLabel(form, text="", anchor="w", wraplength=740); msg.grid(row=2, column=0, columnspan=4, sticky="ew", padx=8, pady=(0, 7))
        rows = ctk.CTkScrollableFrame(panel, label_text="Gasto realizado e saldo do limite")
        rows.grid(row=2, column=0, sticky="nsew")
        self.budget_refs = {"category": category, "period": period, "amount": amount, "cancel": cancel, "save": save, "msg": msg, "rows": rows}
        self._refresh_categories(); self._refresh_budgets()

    @staticmethod
    def _label(parent, text, row, column):
        ctk.CTkLabel(parent, text=text).grid(row=row, column=column, sticky="w", padx=8, pady=(8, 2))

    def _save_personal(self, tab, refs):
        model = refs["model"]
        try:
            priority = {"Baixa": "low", "Média": "medium", "Alta": "high"}[refs["priority"].get()]
            status_map = ({"Planejado": "planned", "Realizado": "purchased", "Cancelado": "cancelled"}
                          if model is Wish else {"Em andamento": "active", "Concluída": "completed", "Pausada": "paused"})
            due_text = refs["due"].get().strip()
            due = datetime.strptime(due_text, "%d/%m/%Y").date() if due_text else None
            target_amount = parse_brl_amount(refs["target"].get())
            saved_amount = parse_brl_amount(refs["saved"].get() or "0")
            if model is Wish:
                record = Wish(refs["name"].get().strip(), target_amount, saved_amount, priority, status_map[refs["status"].get()], due)
            else:
                record = Goal(refs["name"].get().strip(), target_amount, saved_amount, due, priority, status_map[refs["status"].get()])
            if self.editing[tab]: record = replace(record, id=self.editing[tab].id)
            self.service.save(record)
        except (KeyError, ValueError) as exc:
            refs["msg"].configure(text=str(exc) or "Confira os valores informados."); return
        self._clear(tab); refs["msg"].configure(text="Registro salvo."); self._refresh_personal(tab, refs)

    def _save_budget(self):
        refs = self.budget_refs
        try:
            categories = self._budget_categories
            category_id = categories[refs["category"].get()]
            record = Budget(category_id, refs["period"].get().strip(), parse_brl_amount(refs["amount"].get()))
            if self.editing["Orçamentos"]: record = replace(record, id=self.editing["Orçamentos"].id)
            self.service.save(record)
        except (KeyError, ValueError) as exc:
            refs["msg"].configure(text=str(exc) or "Confira os dados do orçamento."); return
        self._clear("Orçamentos"); refs["msg"].configure(text="Orçamento salvo."); self._refresh_budgets()

    def _refresh_personal(self, tab, refs):
        rows = refs["rows"]
        for child in rows.winfo_children(): child.destroy()
        try: records = self.service.list(refs["model"])
        except (ValueError, OSError) as exc:
            ctk.CTkLabel(rows, text=f"Não foi possível carregar os registros: {exc}").pack(padx=10, pady=10); return
        if not records:
            ctk.CTkLabel(rows, text="Nenhum registro ainda.", anchor="w").pack(fill="x", padx=10, pady=12); return
        for record in records:
            target_amount = record.estimated_amount if isinstance(record, Wish) else record.target_amount
            progress = record.saved_amount / target_amount * 100
            due = record.target_date if isinstance(record, Wish) else record.deadline
            due_text = due.strftime("%d/%m/%Y") if due else "Sem prazo"
            status = {"planned": "Planejado", "purchased": "Realizado", "cancelled": "Cancelado", "active": "Em andamento", "completed": "Concluída", "paused": "Pausada"}[record.status]
            row = ctk.CTkFrame(rows); row.pack(fill="x", padx=4, pady=4); row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=f"{record.name} · {status}", font=ctk.CTkFont(weight="bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))
            ctk.CTkLabel(row, text=f"Reservado {format_brl_amount(record.saved_amount)} de {format_brl_amount(target_amount)} ({progress:.0f}%) · {due_text} · Prioridade {record.priority}", anchor="w").grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))
            ctk.CTkButton(row, text="Editar", width=62, command=lambda item=record: self._edit_personal(tab, refs, item)).grid(row=0, column=1, rowspan=2, padx=4)
            ctk.CTkButton(row, text="Excluir", width=62, fg_color="transparent", border_width=1, command=lambda item=record, t=tab, r=refs: self._delete(t, r["model"], item)).grid(row=0, column=2, rowspan=2, padx=(0, 10))

    def _edit_personal(self, tab, refs, record):
        self.editing[tab] = record
        refs["name"].delete(0, "end"); refs["name"].insert(0, record.name)
        target_amount = record.estimated_amount if isinstance(record, Wish) else record.target_amount
        refs["target"].delete(0, "end"); refs["target"].insert(0, format_brl_amount(target_amount).replace("R$ ", ""))
        refs["saved"].delete(0, "end"); refs["saved"].insert(0, format_brl_amount(record.saved_amount).replace("R$ ", ""))
        refs["priority"].set({"low": "Baixa", "medium": "Média", "high": "Alta"}[record.priority])
        due = record.target_date if isinstance(record, Wish) else record.deadline
        refs["due"].delete(0, "end"); refs["due"].insert(0, due.strftime("%d/%m/%Y") if due else "")
        status = {"planned": "Planejado", "purchased": "Realizado", "cancelled": "Cancelado", "active": "Em andamento", "completed": "Concluída", "paused": "Pausada"}[record.status]
        refs["status"].set(status); refs["save"].configure(text="Salvar alterações"); refs["cancel"].pack(side="right", padx=(0, 6))

    def _refresh_categories(self):
        try: cats = [c for c in self.catalogs.list(Category) if c.kind == "expense"]
        except (ValueError, OSError): cats = []
        self._budget_categories = {c.name: c.id for c in cats}
        self.budget_refs["category"].configure(values=list(self._budget_categories) or ["Cadastre uma categoria"])
        if self._budget_categories: self.budget_refs["category"].set(next(iter(self._budget_categories)))

    def _refresh_budgets(self):
        rows = self.budget_refs["rows"]
        for child in rows.winfo_children(): child.destroy()
        try:
            budgets = self.service.list(Budget); cats = {c.id: c.name for c in self.catalogs.list(Category)}
            data = [(b, self.service.budget_spending(b)) for b in budgets]
        except (ValueError, OSError) as exc:
            ctk.CTkLabel(rows, text=f"Não foi possível carregar os orçamentos: {exc}").pack(padx=10, pady=10); return
        if not data:
            ctk.CTkLabel(rows, text="Nenhum orçamento registrado.", anchor="w").pack(fill="x", padx=10, pady=12); return
        for budget, spent in sorted(data, key=lambda pair: (pair[0].period, cats.get(pair[0].category_id, "")), reverse=True):
            remaining = budget.limit_amount - spent
            row = ctk.CTkFrame(rows); row.pack(fill="x", padx=4, pady=4); row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=f"{cats.get(budget.category_id, 'Categoria indisponível')} · {budget.period}", font=ctk.CTkFont(weight="bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))
            ctk.CTkLabel(row, text=f"Gasto {format_brl_amount(spent)} de {format_brl_amount(budget.limit_amount)} · {'Disponível' if remaining >= 0 else 'Acima do limite'} {format_brl_amount(abs(remaining))}", anchor="w").grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))
            ctk.CTkButton(row, text="Editar", width=62, command=lambda item=budget: self._edit_budget(item)).grid(row=0, column=1, rowspan=2, padx=4)
            ctk.CTkButton(row, text="Excluir", width=62, fg_color="transparent", border_width=1, command=lambda item=budget: self._delete("Orçamentos", Budget, item)).grid(row=0, column=2, rowspan=2, padx=(0, 10))

    def _edit_budget(self, budget):
        self.editing["Orçamentos"] = budget; refs = self.budget_refs
        self._refresh_categories()
        label = next((name for name, cid in self._budget_categories.items() if cid == budget.category_id), None)
        if label: refs["category"].set(label)
        refs["period"].delete(0, "end"); refs["period"].insert(0, budget.period)
        refs["amount"].delete(0, "end"); refs["amount"].insert(0, format_brl_amount(budget.limit_amount).replace("R$ ", ""))
        refs["save"].configure(text="Salvar alterações"); refs["cancel"].pack(side="right", padx=(0, 5))

    def _delete(self, tab, model, record):
        if not messagebox.askyesno("Excluir registro", "Deseja excluir este registro?", parent=self.winfo_toplevel()): return
        try: self.service.delete(model, record.id)
        except (ValueError, OSError) as exc: messagebox.showerror("Não foi possível excluir", str(exc), parent=self.winfo_toplevel()); return
        if tab == "Orçamentos": self._refresh_budgets()
        else: self._refresh_personal(tab, getattr(self, f"_{tab.lower()}_refs"))

    def _clear(self, tab):
        self.editing[tab] = None
        if tab == "Orçamentos":
            refs = self.budget_refs
            refs["period"].delete(0, "end"); refs["period"].insert(0, date.today().strftime("%Y-%m")); refs["amount"].delete(0, "end")
        else:
            refs = getattr(self, f"_{tab.lower()}_refs")
            for key in ("name", "target", "saved", "due"): refs[key].delete(0, "end")
            refs["priority"].set("Média"); refs["status"].set("Planejado" if tab == "Desejos" else "Em andamento")
        refs["save"].configure(text="Salvar"); refs["cancel"].pack_forget()
