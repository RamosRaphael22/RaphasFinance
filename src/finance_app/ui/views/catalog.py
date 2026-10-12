"""Cadastro, edição, listagem e desativação de contas e categorias."""

import tkinter.messagebox as messagebox
from dataclasses import replace

import customtkinter as ctk

from finance_app.domain.models import Account, Category
from finance_app.services import BalanceService, CatalogService
from finance_app.ui.formatting import format_brl_amount, parse_brl_amount

ACCOUNT_KINDS = {
    "Dinheiro": "cash",
    "Conta corrente": "bank",
    "Poupança": "savings",
    "Cartão de crédito": "credit_card",
}
CATEGORY_KINDS = {"Receita": "income", "Despesa": "expense"}


class CatalogView(ctk.CTkFrame):
    """Formulário e lista de um dos cadastros pessoais."""

    def __init__(self, master, service: CatalogService, model: type[Account] | type[Category],
                 balances: BalanceService | None = None) -> None:
        super().__init__(master, fg_color="transparent")
        self.service = service
        self.balances = balances
        self.model = model
        self.title_text = "Contas" if model is Account else "Categorias"
        self.kinds = ACCOUNT_KINDS if model is Account else CATEGORY_KINDS
        self.reverse_kinds = {value: label for label, value in self.kinds.items()}
        self.editing: Account | Category | None = None
        self.name_input: ctk.CTkEntry
        self.kind_input: ctk.CTkOptionMenu
        self.opening_balance_input: ctk.CTkEntry | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self, text=self.title_text, font=ctk.CTkFont(size=28, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(8, 5))
        ctk.CTkLabel(
            self,
            text="Cadastre e organize seus registros pessoais. Cadastros em uso podem ser desativados para preservar o histórico.",
            anchor="w", wraplength=740, justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 20))

        form = ctk.CTkFrame(self)
        form.grid(row=2, column=0, sticky="new", pady=(0, 18))
        for column in range(3 if self.model is Account else 2):
            form.grid_columnconfigure(column, weight=1)
        ctk.CTkLabel(form, text="Nome").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        ctk.CTkLabel(form, text="Tipo").grid(row=0, column=1, sticky="w", padx=12, pady=(12, 4))
        self.name_input = ctk.CTkEntry(form, placeholder_text="Ex.: Conta principal")
        self.name_input.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.kind_input = ctk.CTkOptionMenu(form, values=list(self.kinds))
        self.kind_input.grid(row=1, column=1, sticky="ew", padx=12, pady=(0, 12))
        if self.model is Account:
            ctk.CTkLabel(form, text="Saldo inicial (R$)").grid(
                row=0, column=2, sticky="w", padx=12, pady=(12, 4),
            )
            self.opening_balance_input = ctk.CTkEntry(form, placeholder_text="0,00")
            self.opening_balance_input.insert(0, "0,00")
            self.opening_balance_input.grid(
                row=1, column=2, sticky="ew", padx=12, pady=(0, 12),
            )
            ctk.CTkLabel(
                form, text="Em cartões, informe a dívida que já está em aberto.", anchor="w",
            ).grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 8))
        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(
            row=3 if self.model is Account else 2, column=0,
            columnspan=3 if self.model is Account else 2,
            sticky="e", padx=12, pady=(0, 14),
        )
        self.cancel_button = ctk.CTkButton(
            actions, text="Cancelar edição", width=130, fg_color="transparent",
            border_width=1, command=self._cancel_edit,
        )
        self.save_button = ctk.CTkButton(actions, text="Adicionar", width=130, command=self._save)
        self.cancel_button.pack(side="left", padx=(0, 8))
        self.save_button.pack(side="left")
        self.cancel_button.pack_forget()

        list_header = ctk.CTkFrame(self, fg_color="transparent")
        list_header.grid(row=3, column=0, sticky="ew")
        list_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            list_header, text="Cadastrados", font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        self.count_label = ctk.CTkLabel(list_header, text="")
        self.count_label.grid(row=0, column=1, sticky="e")
        self.rows = ctk.CTkScrollableFrame(self, label_text="")
        self.rows.grid(row=4, column=0, sticky="nsew", pady=(8, 0))
        self.grid_rowconfigure(4, weight=1)

    def refresh(self) -> None:
        for child in self.rows.winfo_children():
            child.destroy()
        try:
            records = self.service.list(self.model)
            balances = {
                item.account.id: item.amount for item in self.balances.list()
            } if self.model is Account and self.balances else {}
        except (ValueError, OSError) as exc:
            ctk.CTkLabel(
                self.rows, text=f"Não foi possível carregar {self.title_text.lower()}:\n{exc}",
                anchor="w", justify="left", wraplength=680,
            ).pack(fill="x", padx=12, pady=12)
            self.count_label.configure(text="Erro ao carregar")
            return

        active_count = sum(record.active for record in records)
        self.count_label.configure(
            text=f"{active_count} ativo(s) · {len(records)} no total"
        )
        if not records:
            ctk.CTkLabel(
                self.rows, text="Nenhum cadastro ainda. Use o formulário acima para adicionar.",
                anchor="w",
            ).pack(fill="x", padx=12, pady=14)
            return

        for record in records:
            self._add_row(record, balances.get(record.id))

    def _add_row(self, record: Account | Category, balance=None) -> None:
        row = ctk.CTkFrame(self.rows)
        row.pack(fill="x", padx=4, pady=4)
        row.grid_columnconfigure(0, weight=1)
        kind_label = self.reverse_kinds.get(record.kind, record.kind)
        status = "Ativo" if record.active else "Inativo"
        ctk.CTkLabel(
            row, text=record.name, font=ctk.CTkFont(size=15, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(14, 8), pady=(10, 0))
        ctk.CTkLabel(
            row, text=f"{kind_label} · {status}", anchor="w",
            text_color=("gray35", "gray70"),
        ).grid(row=1, column=0, sticky="w", padx=(14, 8), pady=(0, 10))
        button_rows = 2
        if isinstance(record, Account) and balance is not None:
            if record.kind == "credit_card":
                label = "Fatura em aberto" if balance >= 0 else "Crédito disponível"
                amount = balance if balance >= 0 else -balance
            else:
                label, amount = "Saldo calculado", balance
            ctk.CTkLabel(
                row, text=f"{label}: {format_brl_amount(amount)}", anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
            ).grid(row=2, column=0, sticky="w", padx=(14, 8), pady=(0, 10))
            button_rows = 3
        ctk.CTkButton(
            row, text="Editar", width=72, command=lambda item=record: self._edit(item),
        ).grid(row=0, column=1, rowspan=button_rows, padx=(4, 6), pady=10)
        ctk.CTkButton(
            row, text="Desativar" if record.active else "Ativar", width=90,
            fg_color="transparent", border_width=1,
            command=lambda item=record: self._toggle_active(item),
        ).grid(row=0, column=2, rowspan=button_rows,
               padx=(0, 6 if isinstance(record, Category) else 12), pady=10)
        if isinstance(record, Category):
            ctk.CTkButton(
                row, text="Excluir", width=76, fg_color="transparent",
                border_width=1, command=lambda item=record: self._delete(item),
            ).grid(row=0, column=3, rowspan=button_rows, padx=(0, 12), pady=10)

    def _edit(self, record: Account | Category) -> None:
        self.editing = record
        self.name_input.delete(0, "end")
        self.name_input.insert(0, record.name)
        self.kind_input.set(self.reverse_kinds[record.kind])
        if isinstance(record, Account) and self.opening_balance_input:
            self.opening_balance_input.delete(0, "end")
            self.opening_balance_input.insert(
                0, format_brl_amount(record.opening_balance).replace("R$ ", ""),
            )
        self.save_button.configure(text="Salvar alterações")
        self.cancel_button.pack(side="left", padx=(0, 8))
        self.name_input.focus_set()

    def _cancel_edit(self) -> None:
        self.editing = None
        self.name_input.delete(0, "end")
        self.kind_input.set(next(iter(self.kinds)))
        if self.opening_balance_input:
            self.opening_balance_input.delete(0, "end")
            self.opening_balance_input.insert(0, "0,00")
        self.save_button.configure(text="Adicionar")
        self.cancel_button.pack_forget()

    def _save(self) -> None:
        name = self.name_input.get().strip()
        kind = self.kinds[self.kind_input.get()]
        try:
            if self.editing is None:
                if self.model is Account:
                    opening_balance = parse_brl_amount(self.opening_balance_input.get())
                    record = Account(name=name, kind=kind, opening_balance=opening_balance)
                else:
                    record = Category(name=name, kind=kind)
            else:
                if isinstance(self.editing, Account) and self.opening_balance_input:
                    opening_balance = parse_brl_amount(self.opening_balance_input.get())
                    record = replace(
                        self.editing, name=name, kind=kind, opening_balance=opening_balance,
                    )
                else:
                    record = replace(self.editing, name=name, kind=kind)
            self.service.save(record)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Não foi possível salvar", str(exc), parent=self.winfo_toplevel())
            return
        self._cancel_edit()
        self.refresh()

    def _toggle_active(self, record: Account | Category) -> None:
        try:
            self.service.set_active(record, not record.active)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Não foi possível atualizar", str(exc), parent=self.winfo_toplevel())
            return
        self.refresh()

    def _delete(self, record: Category) -> None:
        if not messagebox.askyesno(
            "Excluir categoria",
            f'Deseja excluir a categoria "{record.name}"? Esta ação não pode ser desfeita.',
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            self.service.delete(record)
        except (ValueError, OSError) as exc:
            messagebox.showerror(
                "Não foi possível excluir",
                f"{exc}\n\nCategorias usadas em lançamentos, orçamentos ou recorrências precisam ser desativadas.",
                parent=self.winfo_toplevel(),
            )
            return
        if self.editing and self.editing.id == record.id:
            self._cancel_edit()
        self.refresh()
