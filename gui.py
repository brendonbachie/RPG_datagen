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
from engine.schemas import (
    ALCANCES, AREAS, ESCOLAS, MATRIZES, NIVEIS_RELIQUIA, NUCLEOS,
    SUBMATRIZES, TIPOS_DANO, VETORES,
)
from engine.regras import PERICIAS, RARIDADES
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

        # Aba Biblioteca: itens criados de todos os tipos (seletor de tipo).
        frame_bib = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(frame_bib, text="≡  Biblioteca")
        self._idx_biblioteca = self.notebook.index("end") - 1
        self._construir_aba_biblioteca(frame_bib)
        self.notebook.bind("<<NotebookTabChanged>>", self._ao_trocar_aba)

    def _construir_aba(self, frame: ttk.Frame, tipo: str, precisa_nivel: bool) -> None:
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(4, weight=1)

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

        # ── Painel recolhível de preferências (opcional) ──
        prefs_frame, coletar_prefs = self._construir_prefs(frame, tipo)
        aberto = tk.BooleanVar(value=False)
        btn_pref = ttk.Button(frame, text="▸ Preferências (opcional)")

        def alternar_prefs() -> None:
            if aberto.get():
                prefs_frame.grid_remove()
                btn_pref.configure(text="▸ Preferências (opcional)")
                aberto.set(False)
            else:
                prefs_frame.grid()
                btn_pref.configure(text="▾ Preferências (opcional)")
                aberto.set(True)

        btn_pref.configure(command=alternar_prefs)
        btn_pref.grid(row=2, column=0, sticky="w", pady=(0, 4))
        prefs_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        prefs_frame.grid_remove()

        # ── Sub-notebook de saída: JSON | Ficha ──
        nb_saida = ttk.Notebook(frame, style="Out.TNotebook")
        nb_saida.grid(row=4, column=0, sticky="nsew")

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
        acoes.grid(row=5, column=0, sticky="ew", pady=(10, 0))
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
            tipo, entrada, var_nivel, saida_json, saida_ficha, btn_gerar, nb_saida,
            coletar_prefs,
        )
        btn_gerar.configure(command=acao)
        entrada.bind("<Control-Return>", acao)

    # ── Preferências por aba de geração ─────────────────────────────────────────
    def _construir_prefs(self, parent: ttk.Frame, tipo: str):
        """Cria o painel de preferências do tipo e retorna (frame, coletar_prefs).

        coletar_prefs() devolve só os campos preenchidos (vazio ⇒ aleatório).
        Comboboxes têm 1ª opção vazia = '(aleatório)'.
        """
        frame = ttk.Frame(parent)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

        def lbl(r, c, txt):
            ttk.Label(frame, text=txt, style="Field.TLabel").grid(
                row=r, column=c, sticky="w", padx=(0, 6), pady=2)

        def combo(var, valores, w=14):
            return ttk.Combobox(frame, textvariable=var, values=[""] + list(valores),
                                state="readonly", width=w)

        nums = lambda a, b: [str(i) for i in range(a, b + 1)]

        if tipo == "conjuracao":
            v_matriz = tk.StringVar(); v_sub = tk.StringVar(); v_nivel = tk.StringVar()
            v_alc = tk.StringVar(); v_area = tk.StringVar(); v_dano = tk.StringVar()
            v_dx = tk.StringVar(); v_dy = tk.StringVar()
            v_custo = tk.StringVar(); v_ganho = tk.StringVar(); v_efe = tk.StringVar()
            lbl(0, 0, "Matriz");    combo(v_matriz, MATRIZES).grid(row=0, column=1, sticky="ew", pady=2)
            lbl(0, 2, "Submatriz"); combo(v_sub, SUBMATRIZES).grid(row=0, column=3, sticky="ew", pady=2)
            lbl(1, 0, "Nível");     combo(v_nivel, nums(0, 3), w=6).grid(row=1, column=1, sticky="w", pady=2)
            lbl(1, 2, "Alcance");   combo(v_alc, ALCANCES).grid(row=1, column=3, sticky="ew", pady=2)
            lbl(2, 0, "Área");      combo(v_area, AREAS).grid(row=2, column=1, sticky="ew", pady=2)
            lbl(2, 2, "Causa dano"); combo(v_dano, ["Sim", "Não"], w=6).grid(row=2, column=3, sticky="w", pady=2)
            lbl(3, 0, "Dado X");    combo(v_dx, nums(1, 6), w=6).grid(row=3, column=1, sticky="w", pady=2)
            lbl(3, 2, "Dado Y");    combo(v_dy, _DADO_Y, w=6).grid(row=3, column=3, sticky="w", pady=2)
            lbl(4, 0, "Custo conexão"); combo(v_custo, nums(0, 10), w=6).grid(row=4, column=1, sticky="w", pady=2)
            lbl(4, 2, "Ganho conexão"); combo(v_ganho, nums(0, 10), w=6).grid(row=4, column=3, sticky="w", pady=2)
            lbl(5, 0, "Efeitos")
            ttk.Entry(frame, textvariable=v_efe).grid(row=5, column=1, columnspan=3, sticky="ew", pady=2)
            ttk.Label(frame, text="(vírgula; deixe vazio para aleatório)",
                      style="Sub.TLabel").grid(row=6, column=1, columnspan=3, sticky="w")

            def coletar():
                p = {}
                if v_matriz.get(): p["matriz"] = v_matriz.get()
                if v_sub.get():    p["submatriz"] = v_sub.get()
                if v_nivel.get():  p["nivel"] = int(v_nivel.get())
                if v_alc.get():    p["alcance"] = v_alc.get()
                if v_area.get():   p["area"] = v_area.get()
                if v_dano.get():   p["tem_dano"] = (v_dano.get() == "Sim")
                if v_dx.get():     p["dado_x"] = int(v_dx.get())
                if v_dy.get():     p["dado_y"] = int(v_dy.get())
                if v_custo.get():  p["conexao_custo"] = int(v_custo.get())
                if v_ganho.get():  p["conexao_ganho"] = int(v_ganho.get())
                ef = self._csv(v_efe.get())
                if ef:             p["efeitos"] = [e.upper() for e in ef]
                return p

        elif tipo == "conjurador":
            v_escola = tk.StringVar(); v_idade = tk.StringVar(); v_per = tk.StringVar()
            atr_chaves = [
                ("brutalidade", "BRU"), ("rapidez", "RAP"), ("vitalidade", "VIT"),
                ("influencia", "INF"), ("sintonia", "SIN"), ("astucia", "AST"),
            ]
            v_atr = {k: tk.StringVar() for k, _ in atr_chaves}
            lbl(0, 0, "Escola"); combo(v_escola, ESCOLAS).grid(row=0, column=1, sticky="ew", pady=2)
            lbl(0, 2, "Idade")
            ttk.Entry(frame, textvariable=v_idade).grid(row=0, column=3, sticky="ew", pady=2)
            lbl(1, 0, "Atributos")
            attrs = ttk.Frame(frame); attrs.grid(row=1, column=1, columnspan=3, sticky="w", pady=2)
            for i, (chave, rot) in enumerate(atr_chaves):
                ttk.Label(attrs, text=rot, style="Sub.TLabel").grid(row=0, column=i * 2, padx=(0, 2))
                ttk.Combobox(attrs, textvariable=v_atr[chave], values=["", "0", "1", "2", "3"],
                             state="readonly", width=3).grid(row=0, column=i * 2 + 1, padx=(0, 8))
            lbl(2, 0, "Perícias")
            ttk.Entry(frame, textvariable=v_per).grid(row=2, column=1, columnspan=3, sticky="ew", pady=2)
            ttk.Label(frame, text="Atributos/perícias são guia — o sistema ajusta pelas regras.",
                      style="Sub.TLabel").grid(row=3, column=1, columnspan=3, sticky="w")

            def coletar():
                p = {}
                if v_escola.get(): p["escola"] = v_escola.get()
                if v_idade.get().strip(): p["idade"] = v_idade.get().strip()
                atr = {k: v_atr[k].get() for k, _ in atr_chaves if v_atr[k].get()}
                if atr:
                    p["atributos"] = ", ".join(f"{k} {v}" for k, v in atr.items())  # guia (não travado)
                per = self._csv(v_per.get())
                if per: p["pericias"] = per                                          # guia (não travado)
                return p

        elif tipo == "reliquia":
            v_matriz = tk.StringVar(); v_sub = tk.StringVar(); v_nuc = tk.StringVar()
            v_vet = tk.StringVar(); v_nivel = tk.StringVar(); v_forma = tk.StringVar()
            v_alc = tk.StringVar(); v_area = tk.StringVar(); v_tipos = tk.StringVar()
            v_dx = tk.StringVar(); v_dy = tk.StringVar(); v_mult = tk.StringVar()
            lbl(0, 0, "Matriz");    combo(v_matriz, MATRIZES).grid(row=0, column=1, sticky="ew", pady=2)
            lbl(0, 2, "Submatriz"); combo(v_sub, SUBMATRIZES).grid(row=0, column=3, sticky="ew", pady=2)
            lbl(1, 0, "Núcleo");    combo(v_nuc, NUCLEOS).grid(row=1, column=1, sticky="ew", pady=2)
            lbl(1, 2, "Vetor");     combo(v_vet, VETORES).grid(row=1, column=3, sticky="ew", pady=2)
            lbl(2, 0, "Nível");     combo(v_nivel, NIVEIS_RELIQUIA).grid(row=2, column=1, sticky="ew", pady=2)
            lbl(2, 2, "Forma")
            ttk.Entry(frame, textvariable=v_forma).grid(row=2, column=3, sticky="ew", pady=2)
            lbl(3, 0, "Alcance");   combo(v_alc, ALCANCES).grid(row=3, column=1, sticky="ew", pady=2)
            lbl(3, 2, "Área");      combo(v_area, AREAS).grid(row=3, column=3, sticky="ew", pady=2)
            lbl(4, 0, "Tipos de dano")
            ttk.Entry(frame, textvariable=v_tipos).grid(row=4, column=1, columnspan=3, sticky="ew", pady=2)
            lbl(5, 0, "Dado X");    combo(v_dx, nums(1, 6), w=6).grid(row=5, column=1, sticky="w", pady=2)
            lbl(5, 2, "Dado Y");    combo(v_dy, _DADO_Y, w=6).grid(row=5, column=3, sticky="w", pady=2)
            lbl(6, 0, "Mult. crítico"); combo(v_mult, nums(2, 4), w=6).grid(row=6, column=1, sticky="w", pady=2)
            ttk.Label(frame, text="(tipos de dano separados por vírgula)",
                      style="Sub.TLabel").grid(row=7, column=1, columnspan=3, sticky="w")

            def coletar():
                p = {}
                if v_matriz.get(): p["matriz"] = v_matriz.get()
                if v_sub.get():    p["submatriz"] = v_sub.get()
                if v_nuc.get():    p["nucleo"] = v_nuc.get()
                if v_vet.get():    p["vetor"] = v_vet.get()
                if v_nivel.get():  p["nivel"] = v_nivel.get()
                if v_forma.get().strip(): p["forma"] = v_forma.get().strip()
                if v_alc.get():    p["alcance"] = v_alc.get()
                if v_area.get():   p["area"] = v_area.get()
                td = self._csv(v_tipos.get())
                if td:             p["tipos_dano"] = [t.upper() for t in td]
                if v_dx.get():     p["dado_x"] = int(v_dx.get())
                if v_dy.get():     p["dado_y"] = int(v_dy.get())
                if v_mult.get():   p["mult_critico"] = int(v_mult.get())
                return p

        else:  # familiar
            v_matriz = tk.StringVar(); v_sub = tk.StringVar(); v_rar = tk.StringVar()
            lbl(0, 0, "Matriz");    combo(v_matriz, MATRIZES).grid(row=0, column=1, sticky="ew", pady=2)
            lbl(0, 2, "Submatriz"); combo(v_sub, SUBMATRIZES).grid(row=0, column=3, sticky="ew", pady=2)
            lbl(1, 0, "Raridade");  combo(v_rar, RARIDADES).grid(row=1, column=1, sticky="ew", pady=2)

            def coletar():
                p = {}
                if v_matriz.get(): p["matriz"] = v_matriz.get()
                if v_sub.get():    p["submatriz"] = v_sub.get()
                if v_rar.get():    p["raridade"] = v_rar.get()
                return p

        return frame, coletar

    # ── Aba Biblioteca ────────────────────────────────────────────────────────

    # Coleções e rótulos de lista por tipo (definidos em _construir_aba_biblioteca).
    def _construir_aba_biblioteca(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)
        self._bib_cache: list[dict] = []
        self._bib_idx: int | None = None
        self._forms: dict[str, dict] = {}
        self._bib_label_para_tipo: dict[str, str] = {}

        # (tipo, rótulo, coleção, builder do form, rótulo do item na lista)
        tipos = [
            ("conjurador", "Conjuradores", biblioteca.CONJURADORES,
             self._construir_form_conjurador,
             lambda c: f"{c.get('nome', '(sem nome)')}  ·  {c.get('escola', '?')}"),
            ("reliquia", "Relíquias", biblioteca.RELIQUIAS,
             self._construir_form_reliquia,
             lambda c: f"{c.get('nome', '(sem nome)')}  ·  {c.get('matriz', '?')}"),
            ("conjuracao", "Conjurações", biblioteca.CONJURACOES,
             self._construir_form_conjuracao,
             lambda c: f"{c.get('nome', '(sem nome)')}  ·  {c.get('matriz', '?')}"),
            ("familiar", "Familiares", biblioteca.FAMILIARES,
             self._construir_form_familiar,
             lambda c: f"{c.get('nome', '(sem nome)')}  ·  {c.get('raridade', '?')}"),
        ]

        # ── Barra superior: seletor de tipo + info + atualizar ──
        topo = ttk.Frame(frame)
        topo.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        topo.columnconfigure(2, weight=1)
        ttk.Label(topo, text="Tipo", style="Field.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.var_bib_tipo = tk.StringVar()
        combo_tipo = ttk.Combobox(
            topo, textvariable=self.var_bib_tipo, state="readonly", width=16,
            values=[label for _, label, _, _, _ in tipos])
        combo_tipo.grid(row=0, column=1, sticky="w")
        combo_tipo.bind("<<ComboboxSelected>>", self._trocar_tipo_biblioteca)
        self.var_bib_info = tk.StringVar(value="")
        ttk.Label(topo, textvariable=self.var_bib_info,
                  style="Field.TLabel").grid(row=0, column=2, sticky="w", padx=12)
        ttk.Button(topo, text="↻ Atualizar",
                   command=self._recarregar_biblioteca).grid(row=0, column=3, sticky="e")

        # ── Lista de itens ──
        self.lista_biblioteca = tk.Listbox(
            frame, width=30, activestyle="none", font=(FONTE_UI, 11),
            background=SURFACE0, foreground=TEXT, borderwidth=0,
            highlightthickness=1, highlightbackground=SURFACE1, highlightcolor=MAUVE,
            selectbackground=MAUVE, selectforeground=CRUST,
        )
        self.lista_biblioteca.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        self.lista_biblioteca.bind("<<ListboxSelect>>", self._ao_selecionar_item)

        # ── Container que empilha os forms (um visível por vez) ──
        cont = ttk.Frame(frame)
        cont.grid(row=1, column=1, sticky="nsew")
        cont.columnconfigure(0, weight=1)
        cont.rowconfigure(0, weight=1)

        for tipo, label, colecao, builder, rotulo in tipos:
            form_frame, popular, coletar = builder(cont)
            form_frame.grid(row=0, column=0, sticky="nsew")
            form_frame.grid_remove()
            self._forms[tipo] = {
                "frame": form_frame, "popular": popular, "coletar": coletar,
                "colecao": colecao, "rotulo": rotulo, "label": label,
            }
            self._bib_label_para_tipo[label] = tipo

        # Tipo inicial: Conjurações (preserva o comportamento anterior).
        self._bib_tipo = "conjuracao"
        self.var_bib_tipo.set("Conjurações")
        self._forms["conjuracao"]["frame"].grid()
        self._recarregar_biblioteca()

    def _mk_text(self, parent: ttk.Frame, height: int = 4) -> tk.Text:
        """Cria um Text de prosa no padrão visual dos forms."""
        return tk.Text(
            parent, height=height, wrap=tk.WORD, font=(FONTE_UI, 10),
            background=SURFACE0, foreground=TEXT, insertbackground=MAUVE,
            relief="flat", borderwidth=0, highlightthickness=1,
            highlightbackground=SURFACE1, highlightcolor=MAUVE, padx=8, pady=6,
        )

    def _botoes_form(self, form: ttk.Frame, row: int) -> None:
        """Linha de botões Salvar/Excluir (operam sobre o tipo ativo)."""
        botoes = ttk.Frame(form)
        botoes.grid(row=row, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        ttk.Button(botoes, text="✔ Salvar alterações", style="Accent.TButton",
                   command=self._salvar_item_editado).pack(side=tk.LEFT)
        ttk.Button(botoes, text="🗑 Excluir",
                   command=self._excluir_item).pack(side=tk.LEFT, padx=6)

    @staticmethod
    def _csv(valor: str) -> list[str]:
        return [x.strip() for x in valor.split(",") if x.strip()]

    # ── Form: Conjuração ────────────────────────────────────────────────────
    def _construir_form_conjuracao(self, parent: ttk.Frame):
        form = ttk.Frame(parent)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        form.rowconfigure(8, weight=1)

        def lbl(r, c, txt):
            ttk.Label(form, text=txt, style="Field.TLabel").grid(
                row=r, column=c, sticky="w", padx=(0, 6), pady=3)

        def combo(var, valores, w=14):
            return ttk.Combobox(form, textvariable=var, values=valores, state="readonly", width=w)

        v_nome = tk.StringVar(); v_matriz = tk.StringVar(); v_submatriz = tk.StringVar()
        v_nivel = tk.IntVar(value=0); v_alcance = tk.StringVar(); v_area = tk.StringVar()
        v_tem_dano = tk.BooleanVar(); v_dado_x = tk.IntVar(value=1); v_dado_y = tk.StringVar(value="6")
        v_custo = tk.IntVar(value=0); v_ganho = tk.IntVar(value=0); v_efeitos = tk.StringVar()

        lbl(0, 0, "Nome")
        ttk.Entry(form, textvariable=v_nome).grid(row=0, column=1, columnspan=3, sticky="ew", pady=3)
        lbl(1, 0, "Matriz");    combo(v_matriz, MATRIZES).grid(row=1, column=1, sticky="ew", pady=3)
        lbl(1, 2, "Submatriz"); combo(v_submatriz, SUBMATRIZES).grid(row=1, column=3, sticky="ew", pady=3)
        lbl(2, 0, "Nível")
        ttk.Spinbox(form, from_=0, to=3, textvariable=v_nivel, width=6).grid(row=2, column=1, sticky="w", pady=3)
        lbl(2, 2, "Alcance");   combo(v_alcance, ALCANCES).grid(row=2, column=3, sticky="ew", pady=3)
        lbl(3, 0, "Área");      combo(v_area, AREAS).grid(row=3, column=1, sticky="ew", pady=3)
        ttk.Checkbutton(form, text="Causa dano", variable=v_tem_dano).grid(row=3, column=3, sticky="w", pady=3)
        lbl(4, 0, "Dado X")
        ttk.Spinbox(form, from_=1, to=6, textvariable=v_dado_x, width=6).grid(row=4, column=1, sticky="w", pady=3)
        lbl(4, 2, "Dado Y");    combo(v_dado_y, _DADO_Y, w=6).grid(row=4, column=3, sticky="w", pady=3)
        lbl(5, 0, "Custo Conexão")
        ttk.Spinbox(form, from_=0, to=999, textvariable=v_custo, width=6).grid(row=5, column=1, sticky="w", pady=3)
        lbl(5, 2, "Ganho Conexão")
        ttk.Spinbox(form, from_=0, to=999, textvariable=v_ganho, width=6).grid(row=5, column=3, sticky="w", pady=3)
        lbl(6, 0, "Efeitos")
        ttk.Entry(form, textvariable=v_efeitos).grid(row=6, column=1, columnspan=3, sticky="ew", pady=3)
        ttk.Label(form, text="(separados por vírgula — ex.: IMOBILIZADO, EMPURRAR)",
                  style="Sub.TLabel").grid(row=7, column=1, columnspan=3, sticky="w")
        t_descricao = self._mk_text(form, height=6)
        t_descricao.grid(row=8, column=0, columnspan=4, sticky="nsew", pady=(6, 4))
        self._botoes_form(form, 9)

        def popular(c):
            dd = c.get("dado_dano") or {}
            v_nome.set(c.get("nome", "")); v_matriz.set(c.get("matriz", ""))
            v_submatriz.set(c.get("submatriz", "NENHUMA"))
            v_nivel.set(int(c.get("nivel", 0) or 0))
            v_alcance.set(c.get("alcance", "")); v_area.set(c.get("area", ""))
            v_tem_dano.set(bool(c.get("tem_dano")))
            v_dado_x.set(int(dd.get("x", 1) or 1)); v_dado_y.set(str(dd.get("y", 6)))
            v_custo.set(int(c.get("conexao_custo", 0) or 0))
            v_ganho.set(int(c.get("conexao_ganho", 0) or 0))
            v_efeitos.set(", ".join(c.get("efeitos") or []))
            t_descricao.delete("1.0", tk.END); t_descricao.insert("1.0", c.get("descricao", ""))

        def coletar(c):
            c["nome"] = v_nome.get().strip() or c.get("nome", "")
            c["matriz"] = v_matriz.get(); c["submatriz"] = v_submatriz.get()
            c["alcance"] = v_alcance.get(); c["area"] = v_area.get()
            c["tem_dano"] = bool(v_tem_dano.get())
            c["efeitos"] = [e.upper() for e in self._csv(v_efeitos.get())]
            c["descricao"] = t_descricao.get("1.0", tk.END).strip()
            try:
                c["nivel"] = int(v_nivel.get())
                c["dado_dano"] = {"x": int(v_dado_x.get()), "y": int(v_dado_y.get())}
                c["conexao_custo"] = int(v_custo.get())
                c["conexao_ganho"] = int(v_ganho.get())
            except (tk.TclError, ValueError):
                self.var_status.set("✗ Valores numéricos inválidos — verifique nível/dado/conexão.")
                return False
            return True

        return form, popular, coletar

    # ── Form: Conjurador ──────────────────────────────────────────────────────
    def _construir_form_conjurador(self, parent: ttk.Frame):
        form = ttk.Frame(parent)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        form.rowconfigure(6, weight=1)
        form.rowconfigure(8, weight=1)

        def lbl(r, c, txt):
            ttk.Label(form, text=txt, style="Field.TLabel").grid(
                row=r, column=c, sticky="w", padx=(0, 6), pady=3)

        v_nome = tk.StringVar(); v_nivel = tk.IntVar(value=1); v_idade = tk.StringVar()
        v_escola = tk.StringVar(); v_pericias = tk.StringVar()
        v_vida = tk.IntVar(value=0); v_conexao = tk.IntVar(value=0)
        atr_chaves = [
            ("brutalidade", "BRU"), ("rapidez", "RAP"), ("vitalidade", "VIT"),
            ("influencia", "INF"), ("sintonia", "SIN"), ("astucia", "AST"),
        ]
        v_atr = {chave: tk.IntVar(value=1) for chave, _ in atr_chaves}

        lbl(0, 0, "Nome")
        ttk.Entry(form, textvariable=v_nome).grid(row=0, column=1, columnspan=3, sticky="ew", pady=3)
        lbl(1, 0, "Escola")
        ttk.Combobox(form, textvariable=v_escola, values=ESCOLAS, state="readonly", width=14).grid(
            row=1, column=1, sticky="ew", pady=3)
        lbl(1, 2, "Nível")
        ttk.Spinbox(form, from_=1, to=10, textvariable=v_nivel, width=6).grid(row=1, column=3, sticky="w", pady=3)
        lbl(2, 0, "Idade")
        ttk.Entry(form, textvariable=v_idade).grid(row=2, column=1, columnspan=3, sticky="ew", pady=3)

        lbl(3, 0, "Atributos")
        attrs = ttk.Frame(form)
        attrs.grid(row=3, column=1, columnspan=3, sticky="w", pady=3)
        for i, (chave, rotulo) in enumerate(atr_chaves):
            ttk.Label(attrs, text=rotulo, style="Sub.TLabel").grid(row=0, column=i * 2, padx=(0, 2))
            ttk.Spinbox(attrs, from_=0, to=3, textvariable=v_atr[chave], width=3).grid(
                row=0, column=i * 2 + 1, padx=(0, 8))

        lbl(4, 0, "Perícias")
        ttk.Entry(form, textvariable=v_pericias).grid(row=4, column=1, columnspan=3, sticky="ew", pady=3)
        ttk.Label(form, text="(separadas por vírgula)", style="Sub.TLabel").grid(
            row=5, column=1, columnspan=3, sticky="w")
        # Vida e Conexão (calculados ao gerar; editáveis aqui)
        vc = ttk.Frame(form); vc.grid(row=5, column=2, columnspan=2, sticky="e")
        ttk.Label(vc, text="Vida", style="Sub.TLabel").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Spinbox(vc, from_=0, to=999, textvariable=v_vida, width=5).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(vc, text="Conexão", style="Sub.TLabel").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Spinbox(vc, from_=0, to=999, textvariable=v_conexao, width=5).pack(side=tk.LEFT)

        lbl(6, 0, "História")
        t_historia = self._mk_text(form, height=4)
        t_historia.grid(row=6, column=1, columnspan=3, sticky="nsew", pady=3)
        lbl(8, 0, "Aparência")
        t_aparencia = self._mk_text(form, height=4)
        t_aparencia.grid(row=8, column=1, columnspan=3, sticky="nsew", pady=3)
        self._botoes_form(form, 9)

        def popular(c):
            atr = c.get("atributos") or {}
            v_nome.set(c.get("nome", "")); v_idade.set(c.get("idade", ""))
            v_escola.set(c.get("escola", ""))
            v_nivel.set(int(c.get("nivel", 1) or 1))
            for chave, _ in atr_chaves:
                v_atr[chave].set(int(atr.get(chave, 1) or 0))
            v_pericias.set(", ".join(c.get("pericias") or []))
            v_vida.set(int(c.get("vida", 0) or 0)); v_conexao.set(int(c.get("conexao", 0) or 0))
            t_historia.delete("1.0", tk.END); t_historia.insert("1.0", c.get("historia", ""))
            t_aparencia.delete("1.0", tk.END); t_aparencia.insert("1.0", c.get("aparencia", ""))

        def coletar(c):
            c["nome"] = v_nome.get().strip() or c.get("nome", "")
            c["idade"] = v_idade.get(); c["escola"] = v_escola.get()
            c["pericias"] = self._csv(v_pericias.get())
            c["historia"] = t_historia.get("1.0", tk.END).strip()
            c["aparencia"] = t_aparencia.get("1.0", tk.END).strip()
            try:
                c["nivel"] = int(v_nivel.get())
                c["atributos"] = {chave: int(v_atr[chave].get()) for chave, _ in atr_chaves}
                c["vida"] = int(v_vida.get()); c["conexao"] = int(v_conexao.get())
            except (tk.TclError, ValueError):
                self.var_status.set("✗ Valores numéricos inválidos — verifique nível/atributos/vida.")
                return False
            return True

        return form, popular, coletar

    # ── Form: Relíquia ────────────────────────────────────────────────────────
    def _construir_form_reliquia(self, parent: ttk.Frame):
        form = ttk.Frame(parent)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        form.rowconfigure(10, weight=1)

        def lbl(r, c, txt):
            ttk.Label(form, text=txt, style="Field.TLabel").grid(
                row=r, column=c, sticky="w", padx=(0, 6), pady=3)

        def combo(var, valores, w=14):
            return ttk.Combobox(form, textvariable=var, values=valores, state="readonly", width=w)

        v_nome = tk.StringVar(); v_matriz = tk.StringVar(); v_submatriz = tk.StringVar()
        v_nucleo = tk.StringVar(); v_vetor = tk.StringVar(); v_nivel = tk.StringVar()
        v_forma = tk.StringVar(); v_alcance = tk.StringVar(); v_area = tk.StringVar()
        v_tipos = tk.StringVar(); v_dado_x = tk.IntVar(value=1); v_dado_y = tk.StringVar(value="6")
        v_mult = tk.IntVar(value=2); v_conjs = tk.StringVar()
        v_fam_nome = tk.StringVar()

        lbl(0, 0, "Nome")
        ttk.Entry(form, textvariable=v_nome).grid(row=0, column=1, columnspan=3, sticky="ew", pady=3)
        lbl(1, 0, "Matriz");    combo(v_matriz, MATRIZES).grid(row=1, column=1, sticky="ew", pady=3)
        lbl(1, 2, "Submatriz"); combo(v_submatriz, SUBMATRIZES).grid(row=1, column=3, sticky="ew", pady=3)
        lbl(2, 0, "Núcleo");    combo(v_nucleo, NUCLEOS).grid(row=2, column=1, sticky="ew", pady=3)
        lbl(2, 2, "Vetor");     combo(v_vetor, VETORES).grid(row=2, column=3, sticky="ew", pady=3)
        lbl(3, 0, "Nível");     combo(v_nivel, NIVEIS_RELIQUIA).grid(row=3, column=1, sticky="ew", pady=3)
        lbl(3, 2, "Forma")
        ttk.Entry(form, textvariable=v_forma).grid(row=3, column=3, sticky="ew", pady=3)
        lbl(4, 0, "Alcance");   combo(v_alcance, ALCANCES).grid(row=4, column=1, sticky="ew", pady=3)
        lbl(4, 2, "Área");      combo(v_area, AREAS).grid(row=4, column=3, sticky="ew", pady=3)
        lbl(5, 0, "Tipos de dano")
        ttk.Entry(form, textvariable=v_tipos).grid(row=5, column=1, columnspan=3, sticky="ew", pady=3)
        ttk.Label(form, text="(vírgula — ex.: CORTE, IMPACTO)", style="Sub.TLabel").grid(
            row=6, column=1, columnspan=3, sticky="w")
        lbl(7, 0, "Dado X")
        ttk.Spinbox(form, from_=1, to=6, textvariable=v_dado_x, width=6).grid(row=7, column=1, sticky="w", pady=3)
        lbl(7, 2, "Dado Y");    combo(v_dado_y, _DADO_Y, w=6).grid(row=7, column=3, sticky="w", pady=3)
        lbl(8, 0, "Mult. crítico")
        ttk.Spinbox(form, from_=2, to=4, textvariable=v_mult, width=6).grid(row=8, column=1, sticky="w", pady=3)
        lbl(9, 0, "Conjurações")
        ttk.Entry(form, textvariable=v_conjs, state="readonly").grid(
            row=9, column=1, columnspan=3, sticky="ew", pady=3)
        lbl(10, 0, "Descrição")
        t_descricao = self._mk_text(form, height=4)
        t_descricao.grid(row=10, column=1, columnspan=3, sticky="nsew", pady=3)
        lbl(11, 0, "Familiar")
        ttk.Entry(form, textvariable=v_fam_nome).grid(row=11, column=1, columnspan=3, sticky="ew", pady=3)
        lbl(12, 0, "Fam. descrição")
        t_fam_desc = self._mk_text(form, height=3)
        t_fam_desc.grid(row=12, column=1, columnspan=3, sticky="ew", pady=3)
        lbl(13, 0, "Fam. comport.")
        t_fam_comp = self._mk_text(form, height=3)
        t_fam_comp.grid(row=13, column=1, columnspan=3, sticky="ew", pady=3)
        self._botoes_form(form, 14)

        def popular(r):
            dd = r.get("dado_dano") or {}
            v_nome.set(r.get("nome", "")); v_matriz.set(r.get("matriz", ""))
            v_submatriz.set(r.get("submatriz", "NENHUMA")); v_nucleo.set(r.get("nucleo", ""))
            v_vetor.set(r.get("vetor", "")); v_nivel.set(r.get("nivel", ""))
            v_forma.set(r.get("forma", "")); v_alcance.set(r.get("alcance", ""))
            v_area.set(r.get("area", "")); v_tipos.set(", ".join(r.get("tipos_dano") or []))
            v_dado_x.set(int(dd.get("x", 1) or 1)); v_dado_y.set(str(dd.get("y", 6)))
            v_mult.set(int(r.get("mult_critico", 2) or 2))
            nomes_conj = ", ".join(
                (x.get("nome", "") if isinstance(x, dict) else str(x))
                for x in (r.get("conjuracoes") or []))
            v_conjs.set(nomes_conj)
            v_fam_nome.set(r.get("familiar_nome", ""))
            t_descricao.delete("1.0", tk.END); t_descricao.insert("1.0", r.get("descricao", ""))
            t_fam_desc.delete("1.0", tk.END); t_fam_desc.insert("1.0", r.get("familiar_descricao", ""))
            t_fam_comp.delete("1.0", tk.END); t_fam_comp.insert("1.0", r.get("familiar_comportamento", ""))

        def coletar(r):
            r["nome"] = v_nome.get().strip() or r.get("nome", "")
            r["matriz"] = v_matriz.get(); r["submatriz"] = v_submatriz.get()
            r["nucleo"] = v_nucleo.get(); r["vetor"] = v_vetor.get()
            r["nivel"] = v_nivel.get(); r["forma"] = v_forma.get()
            r["alcance"] = v_alcance.get(); r["area"] = v_area.get()
            r["tipos_dano"] = [t.upper() for t in self._csv(v_tipos.get())]
            r["familiar_nome"] = v_fam_nome.get()
            r["descricao"] = t_descricao.get("1.0", tk.END).strip()
            r["familiar_descricao"] = t_fam_desc.get("1.0", tk.END).strip()
            r["familiar_comportamento"] = t_fam_comp.get("1.0", tk.END).strip()
            # 'conjuracoes' guarda dicts completos — não é editado aqui.
            try:
                r["dado_dano"] = {"x": int(v_dado_x.get()), "y": int(v_dado_y.get())}
                r["mult_critico"] = int(v_mult.get())
            except (tk.TclError, ValueError):
                self.var_status.set("✗ Valores numéricos inválidos — verifique dado/mult. crítico.")
                return False
            return True

        return form, popular, coletar

    # ── Form: Familiar ────────────────────────────────────────────────────────
    def _construir_form_familiar(self, parent: ttk.Frame):
        form = ttk.Frame(parent)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        form.rowconfigure(4, weight=1)
        form.rowconfigure(6, weight=1)

        def lbl(r, c, txt):
            ttk.Label(form, text=txt, style="Field.TLabel").grid(
                row=r, column=c, sticky="w", padx=(0, 6), pady=3)

        def combo(var, valores, w=14):
            return ttk.Combobox(form, textvariable=var, values=valores, state="readonly", width=w)

        v_nome = tk.StringVar(); v_matriz = tk.StringVar(); v_submatriz = tk.StringVar()
        v_raridade = tk.StringVar(); v_habilidades = tk.StringVar()

        lbl(0, 0, "Nome")
        ttk.Entry(form, textvariable=v_nome).grid(row=0, column=1, columnspan=3, sticky="ew", pady=3)
        lbl(1, 0, "Matriz");    combo(v_matriz, MATRIZES).grid(row=1, column=1, sticky="ew", pady=3)
        lbl(1, 2, "Submatriz"); combo(v_submatriz, SUBMATRIZES).grid(row=1, column=3, sticky="ew", pady=3)
        lbl(2, 0, "Raridade");  combo(v_raridade, RARIDADES).grid(row=2, column=1, sticky="ew", pady=3)
        lbl(3, 0, "Habilidades")
        ttk.Entry(form, textvariable=v_habilidades).grid(row=3, column=1, columnspan=3, sticky="ew", pady=3)
        lbl(4, 0, "Descrição")
        t_descricao = self._mk_text(form, height=5)
        t_descricao.grid(row=4, column=1, columnspan=3, sticky="nsew", pady=3)
        lbl(6, 0, "Comportamento")
        t_comport = self._mk_text(form, height=5)
        t_comport.grid(row=6, column=1, columnspan=3, sticky="nsew", pady=3)
        self._botoes_form(form, 7)

        def popular(c):
            v_nome.set(c.get("nome", "")); v_matriz.set(c.get("matriz", ""))
            v_submatriz.set(c.get("submatriz", "NENHUMA")); v_raridade.set(c.get("raridade", ""))
            v_habilidades.set(", ".join(c.get("habilidades") or []))
            t_descricao.delete("1.0", tk.END); t_descricao.insert("1.0", c.get("descricao", ""))
            t_comport.delete("1.0", tk.END); t_comport.insert("1.0", c.get("comportamento", ""))

        def coletar(c):
            c["nome"] = v_nome.get().strip() or c.get("nome", "")
            c["matriz"] = v_matriz.get(); c["submatriz"] = v_submatriz.get()
            c["raridade"] = v_raridade.get()
            c["habilidades"] = self._csv(v_habilidades.get())
            c["descricao"] = t_descricao.get("1.0", tk.END).strip()
            c["comportamento"] = t_comport.get("1.0", tk.END).strip()
            return True

        return form, popular, coletar

    # ── Lista / edição genéricas (operam sobre o tipo ativo) ──────────────────
    def _trocar_tipo_biblioteca(self, _event: object = None) -> None:
        tipo = self._bib_label_para_tipo.get(self.var_bib_tipo.get(), "conjuracao")
        for info in self._forms.values():
            info["frame"].grid_remove()
        self._bib_tipo = tipo
        self._forms[tipo]["frame"].grid()
        self._bib_idx = None
        self._recarregar_biblioteca()

    def _recarregar_biblioteca(self) -> None:
        info = self._forms[self._bib_tipo]
        self._bib_cache = info["colecao"].carregar()
        self.lista_biblioteca.delete(0, tk.END)
        for item in self._bib_cache:
            self.lista_biblioteca.insert(tk.END, "  " + info["rotulo"](item))
        n = len(self._bib_cache)
        rotulo = info["label"].lower()
        self.var_bib_info.set(
            f"{n} {rotulo} — clique para editar" if n
            else f"Nenhum item em {rotulo} — gere na aba correspondente")

    def _ao_selecionar_item(self, _event: object = None) -> None:
        sel = self.lista_biblioteca.curselection()
        if not sel:
            return
        self._bib_idx = sel[0]
        self._forms[self._bib_tipo]["popular"](self._bib_cache[sel[0]])

    def _salvar_item_editado(self) -> None:
        if self._bib_idx is None or not (0 <= self._bib_idx < len(self._bib_cache)):
            self.var_status.set("Selecione um item na lista para editar.")
            return
        info = self._forms[self._bib_tipo]
        item = self._bib_cache[self._bib_idx]
        if info["coletar"](item) is False:
            return  # erro numérico já reportado no status
        info["colecao"].salvar_lista(self._bib_cache)
        idx = self._bib_idx
        self._recarregar_biblioteca()
        self.lista_biblioteca.selection_set(idx)
        self.var_status.set(f"✓ Salvo: {item.get('nome', '?')}")

    def _excluir_item(self) -> None:
        if self._bib_idx is None or not (0 <= self._bib_idx < len(self._bib_cache)):
            self.var_status.set("Selecione um item para excluir.")
            return
        info = self._forms[self._bib_tipo]
        removido = self._bib_cache.pop(self._bib_idx)
        info["colecao"].salvar_lista(self._bib_cache)
        self._bib_idx = None
        self._recarregar_biblioteca()
        self.var_status.set(f"✓ Excluído: {removido.get('nome', '?')}")

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
        coletar_prefs=None,
    ) -> None:
        conceito = entrada.get("1.0", tk.END).strip()
        if not conceito:
            messagebox.showwarning("Aviso", "Digite um conceito antes de gerar.")
            return

        modelo  = self.var_modelo.get().strip() or None
        url     = self.var_url.get().strip() or None
        num_ctx = self.var_ctx.get()
        nivel   = var_nivel.get() if var_nivel else 1
        # Preferências lidas AQUI (thread principal); a thread só recebe o dict.
        prefs   = coletar_prefs() if coletar_prefs else None

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
                    resultado = gerar_conjurador(conceito, nivel, modelo, url, prefs=prefs)
                else:
                    resultado = _GERADORES[tipo](conceito, modelo, url, prefs=prefs)
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
