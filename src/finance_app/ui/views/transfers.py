"""Registro de transferências e pagamentos de fatura."""

import tkinter.messagebox as messagebox
from dataclasses import replace
from datetime import datetime

import customtkinter as ctk

from finance_app.domain.models import Account, Transfer
from finance_app.services import CatalogService, TransferService
from finance_app.ui.formatting import format_brl_amount, parse_brl_amount


class TransferView(ctk.CTkFrame):
    """Movimenta valores entre contas sem registrar uma nova receita ou despesa."""

    def __init__(self, master, service: TransferService, catalogs: CatalogService) -> None:
        super().__init__(master, fg_color="transparent")
        self.service = service
        self.catalogs = catalogs
        self.accounts: list[Account] = []
        self.editing: Transfer | None = None
        self.source_options: dict[str, str] = {}
        self.destination_options: dict[str, str] = {}
        self._build()
        self._load_accounts()
        self.refresh()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(
            self, text="Transferências", font=ctk.CTkFont(size=28, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(4, 3))
        ctk.CTkLabel(
            self,
            text="Transferir entre contas não cria receita nem despesa. Para pagar um cartão, escolha a conta de origem e o cartão como destino.",
            anchor="w", justify="left", wraplength=760,
        ).grid(row=1, column=0, sticky="ew", pady=(0, 14))

        form = ctk.CTkFrame(self)
        form.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        for column in range(3):
            form.grid_columnconfigure(column, weight=1)
        labels = ("Origem", "Destino", "Valor (R$)", "Data (DD/MM/AAAA)", "Observação (opcional)")
        positions = ((0, 0), (0, 1), (0, 2), (2, 0), (2, 1))
        for label, (row, column) in zip(labels, positions):
            ctk.CTkLabel(form, text=label).grid(
                row=row, column=column, sticky="w", padx=10, pady=(9, 3),
            )
        self.source_input = ctk.CTkOptionMenu(form, values=["Cadastre uma conta"])
        self.source_input.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 7))
        self.destination_input = ctk.CTkOptionMenu(form, values=["Cadastre uma conta"])
        self.destination_input.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 7))
        self.amount_input = ctk.CTkEntry(form, placeholder_text="0,00")
        self.amount_input.grid(row=1, column=2, sticky="ew", padx=10, pady=(0, 7))
        self.date_input = ctk.CTkEntry(form, placeholder_text="DD/MM/AAAA")
        self.date_input.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 7))
        self.notes_input = ctk.CTkEntry(form, placeholder_text="Detalhes adicionais")
        self.notes_input.grid(row=3, column=1, sticky="ew", padx=10, pady=(0, 7))
        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(row=3, column=2, sticky="e", padx=10, pady=(0, 7))
        self.cancel_button = ctk.CTkButton(
            actions, text="Cancelar", width=86, fg_color="transparent",
            border_width=1, command=self._cancel_edit,
        )
        self.cancel_button.pack(side="left", padx=(0, 6))
        self.save_button = ctk.CTkButton(actions, text="Transferir", width=112, command=self._save)
        self.save_button.pack(side="left")
        self.cancel_button.pack_forget()
        self.message = ctk.CTkLabel(form, text="", anchor="w", wraplength=760)
        self.message.grid(row=4, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 7))

        self.rows = ctk.CTkScrollableFrame(self, label_text="Movimentações registradas")
        self.rows.grid(row=3, column=0, sticky="nsew")

    def _load_accounts(self) -> None:
        try:
            self.accounts = self.catalogs.list(Account)
        except (ValueError, OSError) as exc:
            self.message.configure(text=f"Não foi possível carregar as contas: {exc}")
            return
        self._refresh_options()

    @staticmethod
    def _labels(accounts: list[Account]) -> list[tuple[str, Account]]:
        counts: dict[str, int] = {}
        for account in accounts:
            counts[account.name] = counts.get(account.name, 0) + 1
        return [
            (f"{account.name} · {account.id[:6]}" if counts[account.name] > 1 else account.name, account)
            for account in accounts
        ]

    def _refresh_options(self, source_id: str | None = None,
                         destination_id: str | None = None) -> None:
        sources = [item for item in self.accounts if item.active and item.kind != "credit_card"]
        destinations = [item for item in self.accounts if item.active]
        if self.editing:
            if all(item.id != self.editing.source_account_id for item in sources):
                current = next(item for item in self.accounts if item.id == self.editing.source_account_id)
                if current.kind != "credit_card":
                    sources.append(current)
            if all(item.id != self.editing.destination_account_id for item in destinations):
                destinations.append(next(
                    item for item in self.accounts if item.id == self.editing.destination_account_id
                ))
        source_labels = self._labels(sources)
        destination_labels = self._labels(destinations)
        self.source_options = {label: item.id for label, item in source_labels}
        self.destination_options = {label: item.id for label, item in destination_labels}
        self.source_input.configure(values=list(self.source_options) or ["Cadastre uma conta"])
        self.destination_input.configure(values=list(self.destination_options) or ["Cadastre uma conta"])
        self._select(self.source_input, self.source_options, source_id)
        self._select(self.destination_input, self.destination_options, destination_id)

    @staticmethod
    def _select(menu, options: dict[str, str], selected_id: str | None) -> None:
        if selected_id in options.values():
            menu.set(next(label for label, value in options.items() if value == selected_id))
        elif options:
            menu.set(next(iter(options)))
        else:
            menu.set("Cadastre uma conta")

    def _save(self) -> None:
        try:
            if not self.source_options or not self.destination_options:
                raise ValueError("Cadastre contas antes de registrar transferências.")
            record = Transfer(
                source_account_id=self.source_options[self.source_input.get()],
                destination_account_id=self.destination_options[self.destination_input.get()],
                amount=parse_brl_amount(self.amount_input.get()),
                date=self._parse_date(self.date_input.get()),
                notes=self.notes_input.get().strip(),
            )
            if self.editing:
                record = replace(record, id=self.editing.id)
            self.service.save(record)
        except (KeyError, ValueError) as exc:
            self.message.configure(text=str(exc) or "Informe os dados da transferência.")
            return
        except OSError as exc:
            self.message.configure(text=f"Não foi possível salvar a transferência: {exc}")
            return
        self._cancel_edit()
        self.message.configure(text="Transferência registrada.")
        self.refresh()

    def _edit(self, record: Transfer) -> None:
        self.editing = record
        self._refresh_options(record.source_account_id, record.destination_account_id)
        self.amount_input.delete(0, "end")
        self.amount_input.insert(0, format_brl_amount(record.amount).replace("R$ ", ""))
        self.date_input.delete(0, "end")
        self.date_input.insert(0, record.date.strftime("%d/%m/%Y"))
        self.notes_input.delete(0, "end")
        self.notes_input.insert(0, record.notes)
        self.save_button.configure(text="Salvar alterações")
        self.cancel_button.pack(side="left", padx=(0, 6))

    def _cancel_edit(self) -> None:
        self.editing = None
        for entry in (self.amount_input, self.date_input, self.notes_input):
            entry.delete(0, "end")
        self._refresh_options()
        self.save_button.configure(text="Transferir")
        self.cancel_button.pack_forget()

    def _delete(self, record: Transfer) -> None:
        confirmed = messagebox.askyesno(
            "Excluir transferência", "Deseja excluir esta transferência?",
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
            records = self.service.list()
            accounts = {item.id: item for item in self.catalogs.list(Account)}
        except (ValueError, OSError) as exc:
            ctk.CTkLabel(self.rows, text=f"Não foi possível carregar as transferências: {exc}").pack(
                fill="x", padx=12, pady=12,
            )
            return
        if not records:
            ctk.CTkLabel(
                self.rows, text="Nenhuma transferência registrada.", anchor="w",
            ).pack(fill="x", padx=12, pady=14)
            return
        for record in records:
            source = accounts.get(record.source_account_id)
            destination = accounts.get(record.destination_account_id)
            source_name = source.name if source else "Conta indisponível"
            destination_name = destination.name if destination else "Conta indisponível"
            self._add_row(record, source_name, destination_name)

    def _add_row(self, record: Transfer, source: str, destination: str) -> None:
        row = ctk.CTkFrame(self.rows)
        row.pack(fill="x", padx=4, pady=4)
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            row, text=f"{source} → {destination}",
            font=ctk.CTkFont(size=15, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(14, 8), pady=(9, 0))
        ctk.CTkLabel(
            row, text=record.date.strftime("%d/%m/%Y"), anchor="w",
            text_color=("gray35", "gray70"),
        ).grid(row=1, column=0, sticky="w", padx=(14, 8), pady=(0, 9))
        ctk.CTkLabel(
            row, text=format_brl_amount(record.amount), font=ctk.CTkFont(weight="bold"),
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

    @staticmethod
    def _parse_date(value: str):
        try:
            return datetime.strptime(value.strip(), "%d/%m/%Y").date()
        except ValueError as exc:
            raise ValueError("Informe a data no formato DD/MM/AAAA.") from exc
