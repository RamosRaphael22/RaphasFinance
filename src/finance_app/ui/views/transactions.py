"""Formulário, filtros e lista de receitas e despesas."""

import tkinter.messagebox as messagebox
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

import customtkinter as ctk

from finance_app.domain.models import Account, Category, Transaction
from finance_app.services import CatalogService, TransactionService
from finance_app.ui.formatting import format_brl_amount, parse_brl_amount

KIND_LABELS = {"Receita": "income", "Despesa": "expense"}
KIND_NAMES = {value: key for key, value in KIND_LABELS.items()}
ALL = "Todos"


class TransactionView(ctk.CTkFrame):
    """Tela para registrar e consultar lançamentos pessoais."""

    def __init__(self, master, service: TransactionService, catalogs: CatalogService) -> None:
        super().__init__(master, fg_color="transparent")
        self.service = service
        self.catalogs = catalogs
        self.editing: Transaction | None = None
        self.accounts: list[Account] = []
        self.categories: list[Category] = []
        self.account_options: dict[str, str] = {}
        self.category_options: dict[str, str] = {}
        self.filter_category_options: dict[str, str] = {}
        self.filter_account_options: dict[str, str] = {}
        self._build()
        self._load_catalogs()
        self.refresh()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        ctk.CTkLabel(
            self, text="Lançamentos", font=ctk.CTkFont(size=28, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(4, 3))
        ctk.CTkLabel(
            self,
            text="Registre receitas e despesas com valores positivos. O tipo define como cada lançamento será interpretado.",
            anchor="w", justify="left", wraplength=760,
        ).grid(row=1, column=0, sticky="ew", pady=(0, 12))

        self._build_form()
        self._build_filters()
        self.rows = ctk.CTkScrollableFrame(self, label_text="")
        self.rows.grid(row=4, column=0, sticky="nsew", pady=(8, 0))

    def _build_form(self) -> None:
        form = ctk.CTkFrame(self)
        form.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        for column in range(3):
            form.grid_columnconfigure(column, weight=1)
        fields = (
            ("Tipo", 0, 0), ("Descrição", 0, 1), ("Valor (R$)", 0, 2),
            ("Data (DD/MM/AAAA)", 2, 0), ("Categoria", 2, 1), ("Conta", 2, 2),
        )
        for text, row, column in fields:
            ctk.CTkLabel(form, text=text).grid(
                row=row, column=column, sticky="w", padx=10, pady=(8, 3),
            )
        self.kind_input = ctk.CTkOptionMenu(
            form, values=list(KIND_LABELS), command=self._kind_changed,
        )
        self.kind_input.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.description_input = ctk.CTkEntry(form, placeholder_text="Ex.: Mercado")
        self.description_input.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 5))
        self.amount_input = ctk.CTkEntry(form, placeholder_text="0,00")
        self.amount_input.grid(row=1, column=2, sticky="ew", padx=10, pady=(0, 5))
        self.date_input = ctk.CTkEntry(form, placeholder_text="DD/MM/AAAA")
        self.date_input.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.category_input = ctk.CTkOptionMenu(form, values=["Cadastre uma categoria"])
        self.category_input.grid(row=3, column=1, sticky="ew", padx=10, pady=(0, 5))
        self.account_input = ctk.CTkOptionMenu(form, values=["Cadastre uma conta"])
        self.account_input.grid(row=3, column=2, sticky="ew", padx=10, pady=(0, 5))
        ctk.CTkLabel(form, text="Observação (opcional)").grid(
            row=4, column=0, sticky="w", padx=10, pady=(4, 3),
        )
        self.notes_input = ctk.CTkEntry(form, placeholder_text="Detalhes adicionais")
        self.notes_input.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))
        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(row=5, column=2, sticky="e", padx=10, pady=(0, 8))
        self.cancel_button = ctk.CTkButton(
            actions, text="Cancelar", width=86, fg_color="transparent",
            border_width=1, command=self._cancel_edit,
        )
        self.cancel_button.pack(side="left", padx=(0, 6))
        self.save_button = ctk.CTkButton(actions, text="Adicionar", width=112, command=self._save)
        self.save_button.pack(side="left")
        self.cancel_button.pack_forget()
        self.form_message = ctk.CTkLabel(form, text="", anchor="w", wraplength=740)
        self.form_message.grid(row=6, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 6))

    def _build_filters(self) -> None:
        panel = ctk.CTkFrame(self)
        panel.grid(row=3, column=0, sticky="ew")
        for column, weight in enumerate((2, 1, 1, 1, 1, 1)):
            panel.grid_columnconfigure(column, weight=weight)
        self.query_input = ctk.CTkEntry(panel, placeholder_text="Buscar descrição ou observação")
        self.query_input.grid(row=0, column=0, columnspan=2, sticky="ew", padx=(10, 5), pady=(9, 5))
        self.start_input = ctk.CTkEntry(panel, placeholder_text="De · DD/MM/AAAA")
        self.start_input.grid(row=0, column=2, sticky="ew", padx=5, pady=(9, 5))
        self.end_input = ctk.CTkEntry(panel, placeholder_text="Até · DD/MM/AAAA")
        self.end_input.grid(row=0, column=3, sticky="ew", padx=5, pady=(9, 5))
        self.filter_kind = ctk.CTkOptionMenu(
            panel, values=[ALL, *KIND_LABELS], width=105,
        )
        self.filter_kind.grid(row=0, column=4, sticky="ew", padx=5, pady=(9, 5))
        ctk.CTkButton(
            panel, text="Filtrar", width=82, command=self.refresh,
        ).grid(row=0, column=5, sticky="ew", padx=(5, 10), pady=(9, 5))
        ctk.CTkLabel(panel, text="Categoria", anchor="e").grid(
            row=1, column=0, sticky="ew", padx=(10, 5), pady=(4, 9),
        )
        self.filter_category = ctk.CTkOptionMenu(panel, values=[ALL], width=130)
        self.filter_category.grid(row=1, column=1, sticky="ew", padx=5, pady=(4, 9))
        ctk.CTkLabel(panel, text="Conta", anchor="e").grid(
            row=1, column=2, sticky="ew", padx=5, pady=(4, 9),
        )
        self.filter_account = ctk.CTkOptionMenu(panel, values=[ALL], width=130)
        self.filter_account.grid(row=1, column=3, sticky="ew", padx=5, pady=(4, 9))
        ctk.CTkButton(
            panel, text="Limpar filtros", width=112, fg_color="transparent",
            border_width=1, command=self._clear_filters,
        ).grid(row=1, column=4, columnspan=2, sticky="e", padx=10, pady=(4, 9))

    def _load_catalogs(self) -> None:
        try:
            self.accounts = self.catalogs.list(Account)
            self.categories = self.catalogs.list(Category)
        except (ValueError, OSError) as exc:
            self.form_message.configure(text=f"Não foi possível carregar contas e categorias: {exc}")
            return
        self._refresh_entry_options()
        self._refresh_filter_options()

    def _refresh_entry_options(self, selected_category: str | None = None,
                               selected_account: str | None = None) -> None:
        kind = KIND_LABELS[self.kind_input.get()]
        account_choices = [item for item in self.accounts if item.active]
        category_choices = [item for item in self.categories if item.active and item.kind == kind]
        if self.editing:
            if all(item.id != self.editing.account_id for item in account_choices):
                account_choices.append(next(
                    item for item in self.accounts if item.id == self.editing.account_id
                ))
            if all(item.id != self.editing.category_id for item in category_choices):
                current = next(item for item in self.categories if item.id == self.editing.category_id)
                if current.kind == kind:
                    category_choices.append(current)
        account_labels = self._labels(account_choices, lambda item: item.name)
        category_labels = self._labels(category_choices, lambda item: item.name)
        self.account_options = {label: item.id for label, item in account_labels}
        self.category_options = {label: item.id for label, item in category_labels}
        self.account_input.configure(values=list(self.account_options) or ["Cadastre uma conta"])
        self.category_input.configure(values=list(self.category_options) or ["Cadastre uma categoria"])
        if selected_account in self.account_options.values():
            self.account_input.set(next(label for label, record_id in self.account_options.items()
                                        if record_id == selected_account))
        elif self.account_options:
            self.account_input.set(next(iter(self.account_options)))
        else:
            self.account_input.set("Cadastre uma conta")
        if selected_category in self.category_options.values():
            self.category_input.set(next(label for label, record_id in self.category_options.items()
                                          if record_id == selected_category))
        elif self.category_options:
            self.category_input.set(next(iter(self.category_options)))
        else:
            self.category_input.set("Cadastre uma categoria")

    def _refresh_filter_options(self) -> None:
        category_labels = self._labels(self.categories, lambda item: item.name)
        account_labels = self._labels(self.accounts, lambda item: item.name)
        self.filter_category_options = {label: item.id for label, item in category_labels}
        self.filter_account_options = {label: item.id for label, item in account_labels}
        self.filter_category.configure(values=[ALL, *self.filter_category_options])
        self.filter_account.configure(values=[ALL, *self.filter_account_options])
        self.filter_category.set(ALL)
        self.filter_account.set(ALL)

    @staticmethod
    def _labels(records, get_name) -> list[tuple[str, Account | Category]]:
        counts: dict[str, int] = {}
        for record in records:
            counts[get_name(record)] = counts.get(get_name(record), 0) + 1
        labels = []
        for record in records:
            name = get_name(record)
            label = f"{name} · {record.id[:6]}" if counts[name] > 1 else name
            labels.append((label, record))
        return labels

    def _kind_changed(self, _label: str) -> None:
        selected = self.category_options.get(self.category_input.get())
        self._refresh_entry_options(selected_category=selected)

    def _save(self) -> None:
        try:
            kind = KIND_LABELS[self.kind_input.get()]
            if not self.category_options:
                raise ValueError("Cadastre uma categoria ativa para este tipo de lançamento.")
            if not self.account_options:
                raise ValueError("Cadastre uma conta ativa antes de criar lançamentos.")
            category_id = self.category_options[self.category_input.get()]
            account_id = self.account_options[self.account_input.get()]
            amount = self._parse_amount(self.amount_input.get())
            entry_date = self._parse_date(self.date_input.get(), required=True)
            record = Transaction(
                kind=kind,
                description=self.description_input.get().strip(),
                amount=amount,
                date=entry_date,
                category_id=category_id,
                account_id=account_id,
                notes=self.notes_input.get().strip(),
            )
            if self.editing:
                record = replace(
                    record, id=self.editing.id,
                    recurrence_id=self.editing.recurrence_id,
                    recurrence_date=self.editing.recurrence_date,
                )
            self.service.save(record)
        except (KeyError, ValueError) as exc:
            self.form_message.configure(text=str(exc) or "Escolha uma conta e categoria ativas.")
            return
        except OSError as exc:
            self.form_message.configure(text=f"Não foi possível salvar o lançamento: {exc}")
            return
        self._cancel_edit()
        self.form_message.configure(text="Lançamento salvo.")
        self.refresh()

    def _edit(self, record: Transaction) -> None:
        self.editing = record
        self.kind_input.set(KIND_NAMES[record.kind])
        self._refresh_entry_options(record.category_id, record.account_id)
        self.description_input.delete(0, "end")
        self.description_input.insert(0, record.description)
        self.amount_input.delete(0, "end")
        self.amount_input.insert(0, format(record.amount, "f").replace(".", ","))
        self.date_input.delete(0, "end")
        self.date_input.insert(0, record.date.strftime("%d/%m/%Y"))
        self.notes_input.delete(0, "end")
        self.notes_input.insert(0, record.notes)
        self.save_button.configure(text="Salvar alterações")
        self.cancel_button.pack(side="left", padx=(0, 6))

    def _cancel_edit(self) -> None:
        self.editing = None
        for entry in (self.description_input, self.amount_input, self.date_input, self.notes_input):
            entry.delete(0, "end")
        self.kind_input.set("Receita")
        self._refresh_entry_options()
        self.save_button.configure(text="Adicionar")
        self.cancel_button.pack_forget()

    def _delete(self, record: Transaction) -> None:
        confirmed = messagebox.askyesno(
            "Excluir lançamento",
            f"Deseja excluir o lançamento “{record.description}”? Esta ação não pode ser desfeita.",
            parent=self.winfo_toplevel(),
        )
        if not confirmed:
            return
        try:
            self.service.delete(record.id)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Não foi possível excluir", str(exc), parent=self.winfo_toplevel())
            return
        if self.editing and self.editing.id == record.id:
            self._cancel_edit()
        self.refresh()

    def refresh(self) -> None:
        for child in self.rows.winfo_children():
            child.destroy()
        try:
            start = self._parse_date(self.start_input.get(), required=False)
            end = self._parse_date(self.end_input.get(), required=False)
            selected_kind = self.filter_kind.get()
            records = self.service.list(
                query=self.query_input.get(), start=start, end=end,
                kind=KIND_LABELS.get(selected_kind),
                category_id=self.filter_category_options.get(self.filter_category.get()),
                account_id=self.filter_account_options.get(self.filter_account.get()),
            )
            categories = {item.id: item.name for item in self.catalogs.list(Category)}
            accounts = {item.id: item.name for item in self.catalogs.list(Account)}
        except (KeyError, ValueError, OSError) as exc:
            ctk.CTkLabel(
                self.rows, text=f"Não foi possível carregar os lançamentos: {exc}",
                anchor="w", wraplength=720,
            ).pack(fill="x", padx=12, pady=12)
            return
        if not records:
            ctk.CTkLabel(
                self.rows, text="Nenhum lançamento encontrado para os filtros selecionados.",
                anchor="w",
            ).pack(fill="x", padx=12, pady=14)
            return
        for record in records:
            self._add_row(record, categories.get(record.category_id, "Categoria indisponível"),
                          accounts.get(record.account_id, "Conta indisponível"))

    def _add_row(self, record: Transaction, category_name: str, account_name: str) -> None:
        row = ctk.CTkFrame(self.rows)
        row.pack(fill="x", padx=4, pady=4)
        row.grid_columnconfigure(0, weight=1)
        kind_label = KIND_NAMES[record.kind]
        color = ("#18794e", "#4ADE80") if record.kind == "income" else ("#527a16", "#A3E635")
        ctk.CTkLabel(
            row, text=record.description, font=ctk.CTkFont(size=15, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(14, 8), pady=(9, 0))
        ctk.CTkLabel(
            row, text=f"{kind_label} · {record.date.strftime('%d/%m/%Y')} · {category_name} · {account_name}",
            anchor="w", text_color=("gray35", "gray70"),
        ).grid(row=1, column=0, sticky="w", padx=(14, 8), pady=(0, 9))
        ctk.CTkLabel(
            row, text=self._format_amount(record.amount), text_color=color,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=1, rowspan=2, padx=10)
        ctk.CTkButton(
            row, text="Editar", width=66, command=lambda item=record: self._edit(item),
        ).grid(row=0, column=2, rowspan=2, padx=(4, 5), pady=9)
        ctk.CTkButton(
            row, text="Excluir", width=68, fg_color="transparent", border_width=1,
            command=lambda item=record: self._delete(item),
        ).grid(row=0, column=3, rowspan=2, padx=(0, 12), pady=9)
        if record.notes:
            ctk.CTkLabel(
                row, text=f"Observação: {record.notes}", anchor="w", wraplength=580,
            ).grid(row=2, column=0, columnspan=4, sticky="w", padx=14, pady=(0, 9))

    def _clear_filters(self) -> None:
        for entry in (self.query_input, self.start_input, self.end_input):
            entry.delete(0, "end")
        self.filter_kind.set(ALL)
        self.filter_category.set(ALL)
        self.filter_account.set(ALL)
        self.refresh()

    @staticmethod
    def _parse_date(value: str, *, required: bool) -> date | None:
        value = value.strip()
        if not value:
            if required:
                raise ValueError("Informe a data no formato DD/MM/AAAA.")
            return None
        try:
            return datetime.strptime(value, "%d/%m/%Y").date()
        except ValueError as exc:
            raise ValueError(f"Data inválida {value!r}; use o formato DD/MM/AAAA.") from exc

    @staticmethod
    def _parse_amount(value: str) -> Decimal:
        return parse_brl_amount(value)

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        return format_brl_amount(amount)
