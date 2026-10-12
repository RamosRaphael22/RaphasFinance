"""Cadastro de regras recorrentes e confirmação de ocorrências vencidas."""

from dataclasses import replace
from datetime import datetime
import tkinter.messagebox as messagebox

import customtkinter as ctk

from finance_app.domain.models import Account, Category, RecurrenceRule
from finance_app.services import CatalogService, RecurrenceService
from finance_app.ui.formatting import format_brl_amount, parse_brl_amount


class RecurrenceView(ctk.CTkFrame):
    def __init__(self, master, service: RecurrenceService, catalogs: CatalogService) -> None:
        super().__init__(master, fg_color="transparent")
        self.service, self.catalogs = service, catalogs
        self.editing: RecurrenceRule | None = None
        self.categories: dict[str, Category] = {}
        self.accounts: dict[str, Account] = {}
        self._build()
        self.refresh()

    def _build(self):
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(self, text="Recorrências", font=ctk.CTkFont(size=28, weight="bold")).grid(row=0, column=0, sticky="w", pady=(4, 3))
        ctk.CTkLabel(self, text="Cada ocorrência vencida aparece para confirmação. Fins de semana mantêm a data prevista; meses curtos usam o último dia do mês.", anchor="w", wraplength=800, justify="left").grid(row=1, column=0, sticky="ew", pady=(0, 12))
        form = ctk.CTkFrame(self); form.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        for col in range(4): form.grid_columnconfigure(col, weight=1)
        self._label(form, "Nome da regra", 0, 0); self.name = ctk.CTkEntry(form, placeholder_text="Ex.: salário, aluguel"); self.name.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        self._label(form, "Tipo", 0, 1); self.kind = ctk.CTkOptionMenu(form, values=["Despesa", "Receita"], command=lambda _: self._refresh_choices()); self.kind.grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 6))
        self._label(form, "Descrição do lançamento", 0, 2); self.description = ctk.CTkEntry(form); self.description.grid(row=1, column=2, sticky="ew", padx=8, pady=(0, 6))
        self._label(form, "Valor (R$)", 0, 3); self.amount = ctk.CTkEntry(form, placeholder_text="0,00"); self.amount.grid(row=1, column=3, sticky="ew", padx=8, pady=(0, 6))
        self._label(form, "Categoria", 2, 0); self.category = ctk.CTkOptionMenu(form, values=["Cadastre uma categoria"]); self.category.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 6))
        self._label(form, "Conta", 2, 1); self.account = ctk.CTkOptionMenu(form, values=["Cadastre uma conta"]); self.account.grid(row=3, column=1, sticky="ew", padx=8, pady=(0, 6))
        self._label(form, "Periodicidade", 2, 2); self.frequency = ctk.CTkOptionMenu(form, values=["Semanal", "Mensal", "Anual"]); self.frequency.grid(row=3, column=2, sticky="ew", padx=8, pady=(0, 6))
        self._label(form, "A cada", 2, 3); self.interval = ctk.CTkEntry(form, placeholder_text="1"); self.interval.insert(0, "1"); self.interval.grid(row=3, column=3, sticky="ew", padx=8, pady=(0, 6))
        self._label(form, "Data inicial (DD/MM/AAAA)", 4, 0); self.start = ctk.CTkEntry(form, placeholder_text="DD/MM/AAAA"); self.start.grid(row=5, column=0, sticky="ew", padx=8, pady=(0, 6))
        self._label(form, "Data final opcional", 4, 1); self.end = ctk.CTkEntry(form, placeholder_text="DD/MM/AAAA"); self.end.grid(row=5, column=1, sticky="ew", padx=8, pady=(0, 6))
        actions = ctk.CTkFrame(form, fg_color="transparent"); actions.grid(row=5, column=2, columnspan=2, sticky="e", padx=8)
        self.cancel = ctk.CTkButton(actions, text="Cancelar edição", width=125, command=self._clear); self.cancel.pack(side="right", padx=(0, 6)); self.cancel.pack_forget()
        self.save = ctk.CTkButton(actions, text="Salvar regra", width=105, command=self._save); self.save.pack(side="right")
        self.message = ctk.CTkLabel(form, text="", anchor="w", wraplength=800); self.message.grid(row=6, column=0, columnspan=4, sticky="ew", padx=8, pady=(0, 6))
        self.rules = ctk.CTkScrollableFrame(self, label_text="Regras cadastradas")
        self.rules.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        self.pending = ctk.CTkScrollableFrame(self, label_text="Ocorrências vencidas para revisar")
        self.pending.grid(row=4, column=0, sticky="ew")

    @staticmethod
    def _label(parent, text, row, column):
        ctk.CTkLabel(parent, text=text).grid(row=row, column=column, sticky="w", padx=8, pady=(7, 2))

    def _refresh_choices(self):
        kind = {"Despesa": "expense", "Receita": "income"}.get(self.kind.get(), "expense")
        try:
            categories = [item for item in self.catalogs.list(Category) if item.kind == kind and item.active]
            accounts = [item for item in self.catalogs.list(Account) if item.active]
        except (ValueError, OSError) as exc:
            self.message.configure(text=f"Não foi possível carregar contas e categorias: {exc}"); return
        if self.editing:
            categories += [item for item in self.catalogs.list(Category) if item.id == self.editing.category_id and item not in categories]
            accounts += [item for item in self.catalogs.list(Account) if item.id == self.editing.account_id and item not in accounts]
        self.categories = self._make_options(categories)
        self.accounts = self._make_options(accounts)
        self.category.configure(values=list(self.categories) or ["Cadastre uma categoria compatível"])
        self.account.configure(values=list(self.accounts) or ["Cadastre uma conta"])
        if self.categories and self.category.get() not in self.categories: self.category.set(next(iter(self.categories)))
        if self.accounts and self.account.get() not in self.accounts: self.account.set(next(iter(self.accounts)))

    @staticmethod
    def _make_options(records):
        counts = {}
        for item in records: counts[item.name] = counts.get(item.name, 0) + 1
        return {(f"{item.name} · {item.id[:6]}" if counts[item.name] > 1 else item.name): item for item in records}

    def _save(self):
        try:
            category = self.categories[self.category.get()]
            account = self.accounts[self.account.get()]
            rule = RecurrenceRule(
                name=self.name.get().strip(), kind={"Despesa": "expense", "Receita": "income"}[self.kind.get()],
                description=self.description.get().strip(), amount=parse_brl_amount(self.amount.get()),
                category_id=category.id, account_id=account.id,
                frequency={"Semanal": "weekly", "Mensal": "monthly", "Anual": "yearly"}[self.frequency.get()],
                interval=int(self.interval.get().strip()), start_date=self._parse_date(self.start.get(), required=True),
                end_date=self._parse_date(self.end.get()), active=True if self.editing is None else self.editing.active,
            )
            if self.editing: rule = replace(rule, id=self.editing.id)
            self.service.save(rule)
        except (KeyError, ValueError) as exc:
            self.message.configure(text=str(exc) or "Confira os dados da recorrência."); return
        self._clear(); self.message.configure(text="Regra salva. As ocorrências vencidas aguardam confirmação."); self.refresh()

    @staticmethod
    def _parse_date(value: str, required: bool = False):
        value = value.strip()
        if not value and not required: return None
        try: return datetime.strptime(value, "%d/%m/%Y").date()
        except ValueError as exc: raise ValueError("Informe as datas no formato DD/MM/AAAA.") from exc

    def _edit(self, rule):
        self.editing = rule; self._refresh_choices()
        self.name.delete(0, "end"); self.name.insert(0, rule.name)
        self.kind.set("Despesa" if rule.kind == "expense" else "Receita"); self._refresh_choices()
        self.description.delete(0, "end"); self.description.insert(0, rule.description)
        self.amount.delete(0, "end"); self.amount.insert(0, format_brl_amount(rule.amount).replace("R$ ", ""))
        self.category.set(next((label for label, item in self.categories.items() if item.id == rule.category_id), ""))
        self.account.set(next((label for label, item in self.accounts.items() if item.id == rule.account_id), ""))
        self.frequency.set({"weekly": "Semanal", "monthly": "Mensal", "yearly": "Anual"}[rule.frequency])
        self.interval.delete(0, "end"); self.interval.insert(0, str(rule.interval))
        self.start.delete(0, "end"); self.start.insert(0, rule.start_date.strftime("%d/%m/%Y"))
        self.end.delete(0, "end"); self.end.insert(0, rule.end_date.strftime("%d/%m/%Y") if rule.end_date else "")
        self.save.configure(text="Salvar alterações"); self.cancel.pack(side="right", padx=(0, 6))

    def _toggle(self, rule):
        try: self.service.set_active(rule, not rule.active)
        except (ValueError, OSError) as exc: self.message.configure(text=str(exc)); return
        self.refresh()

    def _delete(self, rule):
        if not messagebox.askyesno(
            "Excluir recorrência",
            "Deseja excluir esta regra? Lançamentos já confirmados serão mantidos no histórico.",
            parent=self.winfo_toplevel(),
        ):
            return
        try: self.service.delete(rule.id)
        except (ValueError, OSError) as exc: self.message.configure(text=str(exc)); return
        if self.editing and self.editing.id == rule.id:
            self._clear()
        self.refresh()

    def _confirm(self, rule, occurrence_date):
        try: self.service.confirm(rule.id, occurrence_date)
        except (ValueError, OSError) as exc: self.message.configure(text=str(exc)); return
        self.refresh()

    def _skip(self, rule, occurrence_date):
        try: self.service.skip(rule.id, occurrence_date)
        except (ValueError, OSError) as exc: self.message.configure(text=str(exc)); return
        self.refresh()

    def _clear(self):
        self.editing = None
        for entry in (self.name, self.description, self.amount, self.interval, self.start, self.end): entry.delete(0, "end")
        self.interval.insert(0, "1"); self.kind.set("Despesa"); self.frequency.set("Semanal")
        self.save.configure(text="Salvar regra"); self.cancel.pack_forget(); self._refresh_choices()

    def refresh(self):
        self._refresh_choices()
        for area in (self.rules, self.pending):
            for child in area.winfo_children(): child.destroy()
        try:
            rules = self.service.list()
            pending = self.service.pending()
            cats = {item.id: item.name for item in self.catalogs.list(Category)}
            accounts = {item.id: item.name for item in self.catalogs.list(Account)}
        except (ValueError, OSError) as exc:
            ctk.CTkLabel(self.rules, text=f"Não foi possível carregar recorrências: {exc}").pack(padx=10, pady=10); return
        if not rules: ctk.CTkLabel(self.rules, text="Nenhuma regra cadastrada.", anchor="w").pack(fill="x", padx=10, pady=10)
        for rule in rules:
            row = ctk.CTkFrame(self.rules); row.pack(fill="x", padx=4, pady=3); row.grid_columnconfigure(0, weight=1)
            frequency = {"weekly": "semanal", "monthly": "mensal", "yearly": "anual"}[rule.frequency]
            text = f"{rule.name} · {format_brl_amount(rule.amount)} · {frequency} a cada {rule.interval} · {'Ativa' if rule.active else 'Pausada'}"
            ctk.CTkLabel(row, text=text, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(6, 0))
            ctk.CTkLabel(row, text=f"{rule.description} · {cats.get(rule.category_id, 'Categoria indisponível')} · {accounts.get(rule.account_id, 'Conta indisponível')}", anchor="w").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))
            ctk.CTkButton(row, text="Editar", width=58, command=lambda item=rule: self._edit(item)).grid(row=0, column=1, rowspan=2, padx=3)
            ctk.CTkButton(row, text="Pausar" if rule.active else "Ativar", width=66, command=lambda item=rule: self._toggle(item)).grid(row=0, column=2, rowspan=2, padx=3)
            ctk.CTkButton(row, text="Excluir", width=60, fg_color="transparent", border_width=1, command=lambda item=rule: self._delete(item)).grid(row=0, column=3, rowspan=2, padx=(3, 8))
        if not pending: ctk.CTkLabel(self.pending, text="Nenhuma ocorrência vencida aguardando confirmação.", anchor="w").pack(fill="x", padx=10, pady=10)
        for rule, due in pending:
            row = ctk.CTkFrame(self.pending); row.pack(fill="x", padx=4, pady=3); row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=f"{due.strftime('%d/%m/%Y')} · {rule.name} · {format_brl_amount(rule.amount)}", anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=7)
            ctk.CTkButton(row, text="Confirmar", width=82, command=lambda r=rule, d=due: self._confirm(r, d)).grid(row=0, column=1, padx=4, pady=4)
            ctk.CTkButton(row, text="Ignorar", width=72, fg_color="transparent", border_width=1, command=lambda r=rule, d=due: self._skip(r, d)).grid(row=0, column=2, padx=(0, 8), pady=4)
