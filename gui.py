#!/usr/bin/env python3
"""
Interface gráfica (tkinter) para o Gerador do Sistema das Relíquias.
Tema escuro (Catppuccin Mocha). Saída em duas abas: JSON bruto e Ficha formatada.
"""
import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import engine.ollama as _ollama_mod
from engine.ficha import formatar
from engine.ollama import ErroOllama
from gerador import gerar_conjurador, gerar_conjuracao, gerar_familiar, gerar_reliquia

# ── Paleta de cores (Catppuccin Mocha) ─────────────────────────────────────────
CRUST    = "#11111b"
MANTLE   = "#181825"
BASE     = "#1e1e2e"
SURFACE0 = "#313244"
SURFACE1 = "#45475a"
SURFACE2 = "#585b70"
TEXT     = "#cdd6f4"
SUBTEXT  = "#a6adc8"
MAUVE    = "#cba6f7"
PINK     = "#f5c2e7"
GREEN    = "#a6e3a1"
RED      = "#f38ba8"
YELLOW   = "#f9e2af"

FONTE_UI   = "Segoe UI"
FONTE_MONO = "Consolas"

_TIPOS: list[tuple[str, str, str, bool]] = [
    ("conjurador", "Conjurador", "⚔", True),
    ("reliquia",   "Relíquia",   "◆", False),
    ("conjuracao", "Conjuração", "✦", False),
    ("familiar",   "Familiar",   "⊚", False),
]

_GERADORES = {
    "conjurador": gerar_conjurador,
    "reliquia":   gerar_reliquia,
    "conjuracao": gerar_conjuracao,
    "familiar":   gerar_familiar,
}


class GeradorGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Gerador de Conteúdo — ")
        self.root.minsize(820, 760)
        self.root.configure(bg=BASE)
        self._aplicar_tema()
        self._construir_ui()

    # ── Tema ────────────────────────────────────────────────────────────────────

    def _aplicar_tema(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", background=BASE, foreground=TEXT,
                         fieldbackground=SURFACE0, font=(FONTE_UI, 10))
        style.configure("TFrame", background=BASE)
        style.configure("Card.TFrame", background=MANTLE)
        style.configure("TLabel", background=BASE, foreground=TEXT, font=(FONTE_UI, 10))
        style.configure("Header.TLabel", background=BASE, foreground=MAUVE,
                        font=(FONTE_UI, 18, "bold"))
        style.configure("Sub.TLabel", background=BASE, foreground=SUBTEXT, font=(FONTE_UI, 9))
        style.configure("Field.TLabel", background=BASE, foreground=SUBTEXT,
                        font=(FONTE_UI, 9, "bold"))
        style.configure("Status.TLabel", background=MANTLE, foreground=SUBTEXT,
                        font=(FONTE_UI, 9))

        # LabelFrame
        style.configure("TLabelframe", background=BASE, bordercolor=SURFACE1,
                        borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", background=BASE, foreground=MAUVE,
                        font=(FONTE_UI, 9, "bold"))

        # Notebook
        style.configure("TNotebook", background=BASE, borderwidth=0, tabmargins=(2, 6, 2, 0))
        style.configure("TNotebook.Tab", background=SURFACE0, foreground=SUBTEXT,
                        padding=(20, 9), borderwidth=0, font=(FONTE_UI, 10))
        style.map("TNotebook.Tab",
                  background=[("selected", BASE)],
                  foreground=[("selected", MAUVE)],
                  expand=[("selected", (1, 1, 1, 0))])

        # Sub-notebook (saída JSON/Ficha)
        style.configure("Out.TNotebook", background=BASE, borderwidth=0)
        style.configure("Out.TNotebook.Tab", background=MANTLE, foreground=SUBTEXT,
                        padding=(16, 6), font=(FONTE_UI, 9, "bold"))
        style.map("Out.TNotebook.Tab",
                  background=[("selected", SURFACE0)],
                  foreground=[("selected", TEXT)])

        # Botões
        style.configure("TButton", background=SURFACE1, foreground=TEXT, borderwidth=0,
                        padding=(12, 6), font=(FONTE_UI, 9), focuscolor=BASE)
        style.map("TButton",
                  background=[("active", SURFACE2), ("pressed", SURFACE2),
                              ("disabled", SURFACE0)],
                  foreground=[("disabled", SUBTEXT)])

        style.configure("Accent.TButton", background=MAUVE, foreground=CRUST,
                        font=(FONTE_UI, 11, "bold"), padding=(20, 9), borderwidth=0)
        style.map("Accent.TButton",
                  background=[("active", PINK), ("pressed", PINK),
                              ("disabled", SURFACE1)],
                  foreground=[("disabled", SUBTEXT)])

        # Campos
        style.configure("TEntry", fieldbackground=SURFACE0, foreground=TEXT,
                        bordercolor=SURFACE1, insertcolor=TEXT, padding=5, borderwidth=1)
        style.map("TEntry", bordercolor=[("focus", MAUVE)])
        style.configure("TSpinbox", fieldbackground=SURFACE0, foreground=TEXT,
                        bordercolor=SURFACE1, arrowcolor=MAUVE, insertcolor=TEXT,
                        padding=4, borderwidth=1)
        style.map("TSpinbox", bordercolor=[("focus", MAUVE)])

        # Scrollbar
        style.configure("Vertical.TScrollbar", background=SURFACE1, troughcolor=BASE,
                        bordercolor=BASE, arrowcolor=SUBTEXT, borderwidth=0)
        style.map("Vertical.TScrollbar", background=[("active", SURFACE2)])

    # ── Construção da UI ──────────────────────────────────────────────────────

    def _construir_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
        self._construir_cabecalho()
        self._construir_barra_config()
        self._construir_notebook()
        self._construir_status()

    def _construir_cabecalho(self) -> None:
        frame = ttk.Frame(self.root)
        frame.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 2))
        ttk.Label(frame, text="✦  Sistema das Relíquias", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Gerador local de conteúdo · Ollama",
                  style="Sub.TLabel").pack(anchor="w")

    def _construir_barra_config(self) -> None:
        frame = ttk.LabelFrame(self.root, text=" Ollama ", padding=(12, 8))
        frame.grid(row=1, column=0, sticky="ew", padx=18, pady=(8, 4))
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=2)

        ttk.Label(frame, text="Modelo", style="Field.TLabel").grid(row=0, column=0, sticky="w")
        self.var_modelo = tk.StringVar(value=_ollama_mod.MODELO_PADRAO)
        ttk.Entry(frame, textvariable=self.var_modelo, width=18).grid(
            row=0, column=1, padx=(8, 18), sticky="ew"
        )

        ttk.Label(frame, text="URL", style="Field.TLabel").grid(row=0, column=2, sticky="w")
        self.var_url = tk.StringVar(value=_ollama_mod.OLLAMA_URL)
        ttk.Entry(frame, textvariable=self.var_url, width=34).grid(
            row=0, column=3, padx=8, sticky="ew"
        )

        ttk.Label(frame, text="num_ctx", style="Field.TLabel").grid(
            row=0, column=4, padx=(18, 0), sticky="w")
        self.var_ctx = tk.IntVar(value=_ollama_mod.NUM_CTX)
        ttk.Spinbox(frame, from_=4096, to=65536, increment=4096,
                    textvariable=self.var_ctx, width=8).grid(row=0, column=5, padx=8)

    def _construir_notebook(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=2, column=0, sticky="nsew", padx=18, pady=6)

        for tipo, label, icone, precisa_nivel in _TIPOS:
            frame = ttk.Frame(self.notebook, padding=16)
            self.notebook.add(frame, text=f"{icone}  {label}")
            self._construir_aba(frame, tipo, precisa_nivel)

    def _construir_aba(self, frame: ttk.Frame, tipo: str, precisa_nivel: bool) -> None:
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        # ── Linha superior: label + nível + botão Gerar ──
        topo = ttk.Frame(frame)
        topo.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        topo.columnconfigure(0, weight=1)

        ttk.Label(topo, text="Conceito / Descrição", style="Field.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        var_nivel: tk.IntVar | None = None
        if precisa_nivel:
            ttk.Label(topo, text="Nível", style="Field.TLabel").grid(
                row=0, column=1, padx=(0, 6), sticky="e")
            var_nivel = tk.IntVar(value=1)
            ttk.Spinbox(topo, from_=1, to=10, textvariable=var_nivel, width=4).grid(
                row=0, column=2, padx=(0, 12))

        btn_gerar = ttk.Button(topo, text="▶  GERAR", style="Accent.TButton")
        btn_gerar.grid(row=0, column=3, sticky="e")

        # ── Campo de texto ──
        entrada = tk.Text(
            frame, height=4, wrap=tk.WORD, font=(FONTE_UI, 11),
            background=SURFACE0, foreground=TEXT, insertbackground=MAUVE,
            relief="flat", borderwidth=0, highlightthickness=1,
            highlightbackground=SURFACE1, highlightcolor=MAUVE, padx=10, pady=8,
        )
        entrada.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # ── Sub-notebook de saída: JSON | Ficha ──
        nb_saida = ttk.Notebook(frame, style="Out.TNotebook")
        nb_saida.grid(row=2, column=0, sticky="nsew")

        frame_json  = ttk.Frame(nb_saida)
        frame_ficha = ttk.Frame(nb_saida)
        nb_saida.add(frame_json,  text="  { } JSON  ")
        nb_saida.add(frame_ficha, text="  ▦ Ficha  ")

        for f in (frame_json, frame_ficha):
            f.columnconfigure(0, weight=1)
            f.rowconfigure(0, weight=1)

        saida_json = scrolledtext.ScrolledText(
            frame_json, state=tk.DISABLED, wrap=tk.NONE,
            font=(FONTE_MONO, 10), background=CRUST, foreground=TEXT,
            relief="flat", borderwidth=0, insertbackground=TEXT,
            padx=12, pady=10, highlightthickness=0,
        )
        saida_json.grid(row=0, column=0, sticky="nsew")

        saida_ficha = scrolledtext.ScrolledText(
            frame_ficha, state=tk.DISABLED, wrap=tk.NONE,
            font=(FONTE_MONO, 10), background=CRUST, foreground=GREEN,
            relief="flat", borderwidth=0, insertbackground=TEXT,
            padx=12, pady=10, highlightthickness=0,
        )
        saida_ficha.grid(row=0, column=0, sticky="nsew")

        # ── Botões inferiores ──
        acoes = ttk.Frame(frame)
        acoes.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(acoes, text="⧉ Copiar JSON",
                   command=lambda: self._copiar(saida_json, "JSON")).pack(side=tk.LEFT)
        ttk.Button(acoes, text="⧉ Copiar Ficha",
                   command=lambda: self._copiar(saida_ficha, "Ficha")).pack(side=tk.LEFT, padx=6)
        ttk.Button(acoes, text="⭳ Salvar…",
                   command=lambda: self._salvar(saida_json, tipo)).pack(side=tk.LEFT, padx=6)
        ttk.Button(acoes, text="✕ Limpar",
                   command=lambda: self._limpar(saida_json, saida_ficha)).pack(side=tk.RIGHT)

        # Conecta o botão GERAR
        acao = lambda *_: self._iniciar_geracao(
            tipo, entrada, var_nivel, saida_json, saida_ficha, btn_gerar, nb_saida
        )
        btn_gerar.configure(command=acao)
        entrada.bind("<Control-Return>", acao)

    def _construir_status(self) -> None:
        self.var_status = tk.StringVar(value="Pronto — insira um conceito e clique em GERAR.")
        ttk.Label(
            self.root, textvariable=self.var_status, style="Status.TLabel",
            anchor=tk.W, padding=(12, 6),
        ).grid(row=3, column=0, sticky="ew")

    # ── Ações ─────────────────────────────────────────────────────────────────

    def _iniciar_geracao(
        self,
        tipo: str,
        entrada: tk.Text,
        var_nivel: tk.IntVar | None,
        saida_json: scrolledtext.ScrolledText,
        saida_ficha: scrolledtext.ScrolledText,
        btn: ttk.Button,
        nb_saida: ttk.Notebook,
    ) -> None:
        conceito = entrada.get("1.0", tk.END).strip()
        if not conceito:
            messagebox.showwarning("Aviso", "Digite um conceito antes de gerar.")
            return

        modelo  = self.var_modelo.get().strip() or None
        url     = self.var_url.get().strip() or None
        num_ctx = self.var_ctx.get()
        nivel   = var_nivel.get() if var_nivel else 1

        btn.configure(state=tk.DISABLED, text="⏳ Gerando…")
        self.var_status.set(f"Gerando {tipo}… isso pode levar alguns segundos.")
        self._mostrar_texto(saida_json,  "⏳ Aguardando resposta do Ollama…")
        self._mostrar_texto(saida_ficha, "⏳ Aguardando resposta do Ollama…")

        def tarefa() -> None:
            try:
                _ollama_mod.NUM_CTX = num_ctx

                if tipo == "conjurador":
                    resultado = gerar_conjurador(conceito, nivel, modelo, url)
                else:
                    resultado = _GERADORES[tipo](conceito, modelo, url)

                texto_json  = json.dumps(resultado, ensure_ascii=False, indent=2)
                texto_ficha = formatar(tipo, resultado)

                self.root.after(0, lambda: self._mostrar_texto(saida_json,  texto_json))
                self.root.after(0, lambda: self._mostrar_texto(saida_ficha, texto_ficha))
                # Muda para a aba Ficha automaticamente ao concluir
                self.root.after(0, lambda: nb_saida.select(1))
                self.root.after(0, lambda: self.var_status.set("✓ Geração concluída!"))

            except ErroOllama as e:
                msg = str(e)
                self.root.after(0, lambda: messagebox.showerror("Erro — Ollama", msg))
                self.root.after(0, lambda: self.var_status.set("✗ Erro de conexão com o Ollama."))
                self.root.after(0, lambda: self._mostrar_texto(saida_json, f"ERRO:\n{msg}"))
            except Exception as e:
                msg = str(e)
                self.root.after(0, lambda: messagebox.showerror("Erro inesperado", msg))
                self.root.after(0, lambda: self.var_status.set("✗ Erro inesperado."))
            finally:
                self.root.after(0, lambda: btn.configure(state=tk.NORMAL, text="▶  GERAR"))

        threading.Thread(target=tarefa, daemon=True).start()

    def _mostrar_texto(self, widget: scrolledtext.ScrolledText, texto: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", texto)
        widget.configure(state=tk.DISABLED)

    def _copiar(self, widget: scrolledtext.ScrolledText, label: str) -> None:
        texto = widget.get("1.0", tk.END).strip()
        if not texto or texto.startswith("⏳"):
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(texto)
        self.var_status.set(f"✓ {label} copiado para a área de transferência.")

    def _salvar(self, widget: scrolledtext.ScrolledText, tipo: str) -> None:
        texto = widget.get("1.0", tk.END).strip()
        if not texto or texto.startswith("⏳") or texto.startswith("ERRO"):
            messagebox.showwarning("Aviso", "Nada para salvar.")
            return
        caminho = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=f"{tipo}.json",
            filetypes=[("JSON", "*.json"), ("Texto", "*.txt"), ("Todos", "*.*")],
        )
        if caminho:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(texto)
            self.var_status.set(f"✓ Salvo em: {caminho}")

    def _limpar(
        self,
        json_w: scrolledtext.ScrolledText,
        ficha_w: scrolledtext.ScrolledText,
    ) -> None:
        self._mostrar_texto(json_w, "")
        self._mostrar_texto(ficha_w, "")
        self.var_status.set("Pronto.")


# ── Entrada ───────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--auto-tipo",     default=None)
    parser.add_argument("--auto-conceito", default=None)
    parser.add_argument("--auto-nivel",    type=int, default=1)
    opts, _ = parser.parse_known_args()

    root = tk.Tk()
    app = GeradorGUI(root)

    if opts.auto_tipo and opts.auto_conceito:
        idx = [t for t, _, _, _ in _TIPOS].index(opts.auto_tipo)
        app.notebook.select(idx)

        def _auto() -> None:
            aba = app.notebook.nametowidget(app.notebook.tabs()[idx])

            entradas: list[tk.Text] = []
            fichas:   list[scrolledtext.ScrolledText] = []
            jsons:    list[scrolledtext.ScrolledText] = []
            btns:     list[ttk.Button] = []
            nbs:      list[ttk.Notebook] = []
            spins:    list[ttk.Spinbox] = []

            def _coletar(w: tk.Widget) -> None:
                if isinstance(w, tk.Text) and not isinstance(w, scrolledtext.ScrolledText):
                    entradas.append(w)
                elif isinstance(w, scrolledtext.ScrolledText):
                    # primeiro ScrolledText é JSON, segundo é Ficha
                    if len(jsons) <= len(fichas):
                        jsons.append(w)
                    else:
                        fichas.append(w)
                elif isinstance(w, ttk.Button) and "GERAR" in (w.cget("text") or ""):
                    btns.append(w)
                elif isinstance(w, ttk.Spinbox):
                    spins.append(w)
                elif isinstance(w, ttk.Notebook) and w is not app.notebook:
                    nbs.append(w)
                for c in w.winfo_children():
                    _coletar(c)

            _coletar(aba)

            if entradas:
                entradas[0].delete("1.0", tk.END)
                entradas[0].insert("1.0", opts.auto_conceito)

            # Nível: ajusta o spinbox da aba (se houver) e passa um IntVar
            var_nivel = None
            if spins:
                spins[0].set(opts.auto_nivel)
                var_nivel = tk.IntVar(value=opts.auto_nivel)

            if entradas and jsons and fichas and btns and nbs:
                app._iniciar_geracao(
                    opts.auto_tipo, entradas[0],
                    var_nivel, jsons[0], fichas[0], btns[0], nbs[0],
                )

        root.after(800, _auto)

    root.mainloop()


if __name__ == "__main__":
    main()
