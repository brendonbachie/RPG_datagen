#!/usr/bin/env python3
"""
Interface gráfica (tkinter) para o Gerador do Sistema das Relíquias.
Tema escuro (Catppuccin Mocha). Saída em duas abas: JSON bruto e Ficha formatada.
"""
import json
import queue
import sys
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, scrolledtext, ttk

import engine.ollama as _ollama_mod
from engine import biblioteca
from engine.ficha import formatar
from engine.ollama import ErroOllama
from engine.schemas import ALCANCES, AREAS, MATRIZES, SUBMATRIZES
from gerador import gerar_conjurador, gerar_conjuracao, gerar_familiar, gerar_reliquia

_DADO_Y = ["4", "6", "8", "10", "12", "20"]

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

# Fontes preferidas (resolvidas em runtime conforme o que existe no sistema —
# ver _resolver_fontes). "Consolas"/"Segoe UI" existem no Windows; em Linux/WSL
# caímos para DejaVu/Noto, que têm os glifos de box-drawing usados nas fichas.
FONTE_UI   = "Segoe UI"
FONTE_MONO = "Consolas"

# Ordem de preferência. A MONO precisa ter box-drawing (─│╔█░▌) — Consolas,
# Cascadia e DejaVu/Noto Sans Mono têm; muitas fontes "Courier" não têm blocos.
_PREF_MONO = ["Consolas", "Cascadia Mono", "Cascadia Code", "DejaVu Sans Mono",
              "Noto Sans Mono", "Liberation Mono", "Ubuntu Mono", "Courier New"]
_PREF_UI   = ["Segoe UI", "DejaVu Sans", "Noto Sans", "Ubuntu",
              "Liberation Sans", "Arial"]


def _resolver_fontes(root: tk.Tk) -> None:
    """Reatribui FONTE_UI/FONTE_MONO para a 1ª fonte preferida realmente
    instalada. Sem isso, fontes ausentes (ex.: Consolas no Linux) caem num
    fallback sem glifos de box-drawing e a ficha vira '@'/quadrados."""
    global FONTE_UI, FONTE_MONO
    disponiveis = {f.lower() for f in tkfont.families(root)}
    FONTE_MONO = next((f for f in _PREF_MONO if f.lower() in disponiveis), FONTE_MONO)
    FONTE_UI   = next((f for f in _PREF_UI   if f.lower() in disponiveis), FONTE_UI)

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
        # Se a fonte mono não tiver os glifos de box-drawing (largura 0), a
        # ficha é renderizada em ASCII para não virar '@'/quadrados.
        self.ascii_ficha = self._fonte_sem_boxdrawing()
        self._aplicar_tema()
        self._construir_ui()

    def _fonte_sem_boxdrawing(self) -> bool:
        """True se a FONTE_MONO atual não consegue desenhar '─'/'█'."""
        try:
            f = tkfont.Font(root=self.root, family=FONTE_MONO, size=10)
            return f.measure("─") == 0 or f.measure("█") == 0
        except Exception:
            return False

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

        # Combobox (dropdowns da aba Biblioteca). No estado 'readonly' o ttk
        # pinta o texto com as cores de seleção — sem mapear isso, o texto fica
        # ilegível (escuro sobre escuro). Fixamos cores legíveis em todos estados.
        style.configure("TCombobox", fieldbackground=SURFACE0, background=SURFACE1,
                        foreground=TEXT, arrowcolor=MAUVE, bordercolor=SURFACE1,
                        insertcolor=TEXT, padding=4, borderwidth=1)
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", SURFACE0), ("focus", SURFACE0)],
            foreground=[("readonly", TEXT), ("disabled", SUBTEXT)],
            selectbackground=[("readonly", SURFACE0), ("focus", SURFACE0)],
            selectforeground=[("readonly", TEXT), ("focus", TEXT)],
            bordercolor=[("focus", MAUVE)],
            arrowcolor=[("readonly", MAUVE)],
        )
        # Lista suspensa do Combobox (Listbox clássico, estilizado via option_add).
        self.root.option_add("*TCombobox*Listbox.background", SURFACE0)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", MAUVE)
        self.root.option_add("*TCombobox*Listbox.selectForeground", CRUST)

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

        # Aba Biblioteca: lista todas as conjurações já criadas.
        frame_bib = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(frame_bib, text="≡  Biblioteca")
        self._idx_biblioteca = self.notebook.index("end") - 1
        self._construir_aba_biblioteca(frame_bib)
        self.notebook.bind("<<NotebookTabChanged>>", self._ao_trocar_aba)

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

    # ── Aba Biblioteca ────────────────────────────────────────────────────────

    def _construir_aba_biblioteca(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)
        self._conjuracoes_cache: list[dict] = []
        self._idx_editando: int | None = None

        topo = ttk.Frame(frame)
        topo.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        topo.columnconfigure(0, weight=1)
        self.var_bib_info = tk.StringVar(value="Conjurações criadas")
        ttk.Label(topo, textvariable=self.var_bib_info,
                  style="Field.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(topo, text="↻ Atualizar",
                   command=self._recarregar_biblioteca).grid(row=0, column=1, sticky="e")

        self.lista_biblioteca = tk.Listbox(
            frame, width=30, activestyle="none", font=(FONTE_UI, 11),
            background=SURFACE0, foreground=TEXT, borderwidth=0,
            highlightthickness=1, highlightbackground=SURFACE1, highlightcolor=MAUVE,
            selectbackground=MAUVE, selectforeground=CRUST,
        )
        self.lista_biblioteca.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        self.lista_biblioteca.bind("<<ListboxSelect>>", self._ao_selecionar_conjuracao)

        self._construir_form_conjuracao(frame)
        self._recarregar_biblioteca()

    def _construir_form_conjuracao(self, parent: ttk.Frame) -> None:
        """Formulário de edição da conjuração selecionada (4 colunas)."""
        form = ttk.Frame(parent)
        form.grid(row=1, column=1, sticky="nsew")
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        form.rowconfigure(8, weight=1)

        def lbl(r: int, c: int, txt: str) -> None:
            ttk.Label(form, text=txt, style="Field.TLabel").grid(
                row=r, column=c, sticky="w", padx=(0, 6), pady=3)

        self.f_nome = tk.StringVar()
        self.f_matriz = tk.StringVar()
        self.f_submatriz = tk.StringVar()
        self.f_nivel = tk.IntVar(value=0)
        self.f_alcance = tk.StringVar()
        self.f_area = tk.StringVar()
        self.f_tem_dano = tk.BooleanVar()
        self.f_dado_x = tk.IntVar(value=1)
        self.f_dado_y = tk.StringVar(value="6")
        self.f_custo = tk.IntVar(value=0)
        self.f_ganho = tk.IntVar(value=0)
        self.f_efeitos = tk.StringVar()

        def combo(var, valores, w=14):
            return ttk.Combobox(form, textvariable=var, values=valores,
                                state="readonly", width=w)

        lbl(0, 0, "Nome")
        ttk.Entry(form, textvariable=self.f_nome).grid(
            row=0, column=1, columnspan=3, sticky="ew", pady=3)

        lbl(1, 0, "Matriz");    combo(self.f_matriz, MATRIZES).grid(row=1, column=1, sticky="ew", pady=3)
        lbl(1, 2, "Submatriz"); combo(self.f_submatriz, SUBMATRIZES).grid(row=1, column=3, sticky="ew", pady=3)

        lbl(2, 0, "Nível")
        ttk.Spinbox(form, from_=0, to=3, textvariable=self.f_nivel, width=6).grid(row=2, column=1, sticky="w", pady=3)
        lbl(2, 2, "Alcance");   combo(self.f_alcance, ALCANCES).grid(row=2, column=3, sticky="ew", pady=3)

        lbl(3, 0, "Área");      combo(self.f_area, AREAS).grid(row=3, column=1, sticky="ew", pady=3)
        ttk.Checkbutton(form, text="Causa dano", variable=self.f_tem_dano).grid(
            row=3, column=3, sticky="w", pady=3)

        lbl(4, 0, "Dado X")
        ttk.Spinbox(form, from_=1, to=6, textvariable=self.f_dado_x, width=6).grid(row=4, column=1, sticky="w", pady=3)
        lbl(4, 2, "Dado Y");    combo(self.f_dado_y, _DADO_Y, w=6).grid(row=4, column=3, sticky="w", pady=3)

        lbl(5, 0, "Custo Conexão")
        ttk.Spinbox(form, from_=0, to=999, textvariable=self.f_custo, width=6).grid(row=5, column=1, sticky="w", pady=3)
        lbl(5, 2, "Ganho Conexão")
        ttk.Spinbox(form, from_=0, to=999, textvariable=self.f_ganho, width=6).grid(row=5, column=3, sticky="w", pady=3)

        lbl(6, 0, "Efeitos")
        ttk.Entry(form, textvariable=self.f_efeitos).grid(
            row=6, column=1, columnspan=3, sticky="ew", pady=3)
        ttk.Label(form, text="(separados por vírgula — ex.: IMOBILIZADO, EMPURRAR)",
                  style="Sub.TLabel").grid(row=7, column=1, columnspan=3, sticky="w")

        self.f_descricao = tk.Text(
            form, height=6, wrap=tk.WORD, font=(FONTE_UI, 10),
            background=SURFACE0, foreground=TEXT, insertbackground=MAUVE,
            relief="flat", borderwidth=0, highlightthickness=1,
            highlightbackground=SURFACE1, highlightcolor=MAUVE, padx=8, pady=6,
        )
        self.f_descricao.grid(row=8, column=0, columnspan=4, sticky="nsew", pady=(6, 4))

        botoes = ttk.Frame(form)
        botoes.grid(row=9, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        ttk.Button(botoes, text="✔ Salvar alterações", style="Accent.TButton",
                   command=self._salvar_conjuracao_editada).pack(side=tk.LEFT)
        ttk.Button(botoes, text="🗑 Excluir",
                   command=self._excluir_conjuracao).pack(side=tk.LEFT, padx=6)

    def _recarregar_biblioteca(self) -> None:
        self._conjuracoes_cache = biblioteca.carregar()
        self.lista_biblioteca.delete(0, tk.END)
        for c in self._conjuracoes_cache:
            self.lista_biblioteca.insert(
                tk.END, f"  {c.get('nome', '(sem nome)')}  ·  {c.get('matriz', '?')}")
        n = len(self._conjuracoes_cache)
        self.var_bib_info.set(
            f"{n} conjuração(ões) — clique para editar" if n
            else "Nenhuma conjuração ainda — gere uma na outra aba")

    def _ao_selecionar_conjuracao(self, _event: object = None) -> None:
        sel = self.lista_biblioteca.curselection()
        if not sel:
            return
        self._idx_editando = sel[0]
        c = self._conjuracoes_cache[sel[0]]
        dd = c.get("dado_dano") or {}
        self.f_nome.set(c.get("nome", ""))
        self.f_matriz.set(c.get("matriz", ""))
        self.f_submatriz.set(c.get("submatriz", "NENHUMA"))
        self.f_nivel.set(int(c.get("nivel", 0) or 0))
        self.f_alcance.set(c.get("alcance", ""))
        self.f_area.set(c.get("area", ""))
        self.f_tem_dano.set(bool(c.get("tem_dano")))
        self.f_dado_x.set(int(dd.get("x", 1) or 1))
        self.f_dado_y.set(str(dd.get("y", 6)))
        self.f_custo.set(int(c.get("conexao_custo", 0) or 0))
        self.f_ganho.set(int(c.get("conexao_ganho", 0) or 0))
        self.f_efeitos.set(", ".join(c.get("efeitos") or []))
        self.f_descricao.delete("1.0", tk.END)
        self.f_descricao.insert("1.0", c.get("descricao", ""))

    def _salvar_conjuracao_editada(self) -> None:
        if self._idx_editando is None or not (0 <= self._idx_editando < len(self._conjuracoes_cache)):
            self.var_status.set("Selecione uma conjuração na lista para editar.")
            return
        c = self._conjuracoes_cache[self._idx_editando]
        c["nome"] = self.f_nome.get().strip() or c.get("nome", "")
        c["matriz"] = self.f_matriz.get()
        c["submatriz"] = self.f_submatriz.get()
        c["alcance"] = self.f_alcance.get()
        c["area"] = self.f_area.get()
        c["tem_dano"] = bool(self.f_tem_dano.get())
        c["efeitos"] = [e.strip().upper() for e in self.f_efeitos.get().split(",") if e.strip()]
        c["descricao"] = self.f_descricao.get("1.0", tk.END).strip()
        try:
            c["nivel"] = int(self.f_nivel.get())
            c["dado_dano"] = {"x": int(self.f_dado_x.get()), "y": int(self.f_dado_y.get())}
            c["conexao_custo"] = int(self.f_custo.get())
            c["conexao_ganho"] = int(self.f_ganho.get())
        except (tk.TclError, ValueError):
            self.var_status.set("✗ Valores numéricos inválidos — verifique nível/dado/conexão.")
            return
        biblioteca.salvar_lista(self._conjuracoes_cache)
        idx = self._idx_editando
        self._recarregar_biblioteca()
        self.lista_biblioteca.selection_set(idx)
        self.var_status.set(f"✓ Conjuração salva: {c['nome']}")

    def _excluir_conjuracao(self) -> None:
        if self._idx_editando is None or not (0 <= self._idx_editando < len(self._conjuracoes_cache)):
            self.var_status.set("Selecione uma conjuração para excluir.")
            return
        removida = self._conjuracoes_cache.pop(self._idx_editando)
        biblioteca.salvar_lista(self._conjuracoes_cache)
        self._idx_editando = None
        self._recarregar_biblioteca()
        self.var_status.set(f"✓ Conjuração excluída: {removida.get('nome', '?')}")

    def _ao_trocar_aba(self, _event: object = None) -> None:
        # Ao abrir a aba Biblioteca, recarrega para refletir o que foi gerado.
        try:
            if self.notebook.index(self.notebook.select()) == self._idx_biblioteca:
                self._recarregar_biblioteca()
        except tk.TclError:
            pass

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

        # tkinter NÃO é thread-safe: a thread de trabalho NUNCA toca em widgets.
        # Ela apenas deposita o resultado numa fila; a thread PRINCIPAL consome
        # essa fila por um poller (root.after) e faz toda a atualização da UI.
        fila: "queue.Queue[tuple[str, object]]" = queue.Queue()

        def tarefa() -> None:
            print(f"[gui] geração iniciada: tipo={tipo!r} modelo={modelo!r}", file=sys.stderr, flush=True)
            try:
                _ollama_mod.NUM_CTX = num_ctx
                if tipo == "conjurador":
                    resultado = gerar_conjurador(conceito, nivel, modelo, url)
                else:
                    resultado = _GERADORES[tipo](conceito, modelo, url)
                fila.put(("ok", resultado))
                print("[gui] geração concluída OK", file=sys.stderr, flush=True)
            except ErroOllama as e:
                fila.put(("erro", f"✗ ERRO DE COMUNICAÇÃO COM O OLLAMA\n\n{e}"))
                print(f"[gui] ErroOllama: {e}", file=sys.stderr, flush=True)
            except Exception:
                tb = traceback.format_exc()
                fila.put(("erro", f"✗ ERRO INESPERADO\n\n{tb}"))
                print(f"[gui] exceção inesperada:\n{tb}", file=sys.stderr, flush=True)

        def consumir() -> None:
            try:
                status, payload = fila.get_nowait()
            except queue.Empty:
                self.root.after(120, consumir)   # ainda processando — repõe o poller
                return

            if status == "ok":
                texto_json  = json.dumps(payload, ensure_ascii=False, indent=2)
                texto_ficha = formatar(tipo, payload, ascii_mode=self.ascii_ficha)  # type: ignore[arg-type]
                self._mostrar_texto(saida_json,  texto_json)
                self._mostrar_texto(saida_ficha, texto_ficha)
                nb_saida.select(1)                 # vai para a aba Ficha
                self.var_status.set("✓ Geração concluída!")
            else:
                self._mostrar_texto(saida_json,  str(payload))
                self._mostrar_texto(saida_ficha, str(payload))
                self.var_status.set("✗ Falha na geração (ver painel JSON).")

            btn.configure(state=tk.NORMAL, text="▶  GERAR")
            print(f"[gui] UI atualizada (status={status})", file=sys.stderr, flush=True)

        threading.Thread(target=tarefa, daemon=True).start()
        self.root.after(120, consumir)   # poller roda na thread PRINCIPAL

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
    _resolver_fontes(root)        # escolhe fontes existentes ANTES de montar a UI
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
