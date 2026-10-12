"""Tela de backup, restauração e exportação dos dados locais."""

from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from finance_app.services import PortabilityService


class DataToolsView(ctk.CTkFrame):
    def __init__(self, master, service: PortabilityService) -> None:
        super().__init__(master, fg_color="transparent")
        self.service = service
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Dados, backup e exportação", font=ctk.CTkFont(size=28, weight="bold")).grid(row=0, column=0, sticky="w", pady=(4, 5))
        ctk.CTkLabel(
            self,
            text="Crie uma cópia de segurança, restaure um backup do aplicativo ou exporte os arquivos CSV para abrir em uma planilha.",
            anchor="w", justify="left", wraplength=760,
        ).grid(row=1, column=0, sticky="ew", pady=(0, 16))

        self._action(
            2, "Criar backup", "Pacote ZIP com manifesto e verificação de integridade, pronto para restauração.",
            "Salvar backup", self._backup,
        )
        self._action(
            3, "Restaurar backup", "Valida o pacote e todos os dados antes de substituir os arquivos atuais.",
            "Escolher backup", self._restore,
        )
        self._action(
            4, "Exportar dados CSV", "Exporta cada tabela como CSV UTF-8, com valores e acentos preservados, em um ZIP.",
            "Exportar CSVs", self._export,
        )
        self.message = ctk.CTkLabel(self, text="", anchor="w", justify="left", wraplength=760)
        self.message.grid(row=5, column=0, sticky="ew", pady=(12, 0))

    def _action(self, row, title, description, button_text, command):
        panel = ctk.CTkFrame(self)
        panel.grid(row=row, column=0, sticky="ew", pady=5)
        panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(panel, text=title, font=ctk.CTkFont(size=17, weight="bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(11, 2))
        ctk.CTkLabel(panel, text=description, anchor="w", justify="left", wraplength=620).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 11))
        ctk.CTkButton(panel, text=button_text, command=command, width=150).grid(row=0, column=1, rowspan=2, padx=14, pady=12)

    @staticmethod
    def _save_path(title: str, default_name: str) -> str:
        return filedialog.asksaveasfilename(
            title=title, initialfile=default_name, defaultextension=".zip",
            filetypes=[("Pacote ZIP", "*.zip")],
        )

    def _backup(self):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = self._save_path("Salvar backup", f"backup_financeiro_{stamp}.zip")
        if not destination: return
        try:
            path = self.service.backup(destination)
        except (ValueError, OSError) as exc:
            self.message.configure(text=f"Não foi possível criar o backup: {exc}"); return
        self.message.configure(text=f"Backup criado e verificado: {path}")

    def _restore(self):
        source = filedialog.askopenfilename(
            title="Escolher backup para restaurar",
            filetypes=[("Backup do Minhas Finanças", "*.zip")],
        )
        if not source: return
        confirmed = messagebox.askyesno(
            "Confirmar restauração",
            "A restauração substituirá os dados atuais do aplicativo pelos dados do backup. "
            "O arquivo será validado antes da substituição. Deseja continuar?",
            parent=self.winfo_toplevel(),
        )
        if not confirmed: return
        try:
            self.service.restore(source)
        except (ValueError, OSError) as exc:
            self.message.configure(text=f"Restauração não concluída: {exc}"); return
        self.message.configure(text="Backup restaurado. Abra novamente as outras telas para atualizar as listas exibidas.")

    def _export(self):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = self._save_path("Exportar arquivos CSV", f"exportacao_financeira_{stamp}.zip")
        if not destination: return
        try:
            path = self.service.export(destination)
        except (ValueError, OSError) as exc:
            self.message.configure(text=f"Não foi possível exportar os dados: {exc}"); return
        self.message.configure(text=f"Arquivos CSV exportados em UTF-8: {path}")
