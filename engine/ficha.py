# Renderiza fichas formatadas em texto para cada tipo de entidade.
from typing import Any

_LARGURA = 52

# Mapa Unicode → ASCII (1:1, preserva alinhamento) para ambientes cujo
# tkinter/fonte não possui glifos de box-drawing (ex.: Tk standalone no WSL,
# onde '─'/'█' têm largura 0). Cada caractere vira exatamente 1 ASCII.
_ASCII_MAP = str.maketrans({
    "—": "-", "•": "*",
    "─": "-", "═": "-", "│": "|", "║": "|",
    "┼": "+", "╔": "+", "╗": "+", "╚": "+", "╝": "+", "╠": "+", "╣": "+",
    "█": "#", "░": ".", "▌": "|",
    "▲": "^", "▼": "v", "⚠": "!",
})


def _to_ascii(texto: str) -> str:
    """Converte os caracteres de desenho para ASCII (mesma largura)."""
    return texto.translate(_ASCII_MAP)


def _barra_attr(valor: int, maximo: int = 6) -> str:
    valor = max(0, min(maximo, valor))
    return "█" * valor + "░" * (maximo - valor)


def _wrap(texto: str, largura: int = 48, prefixo: str = "  ") -> str:
    palavras = texto.split()
    linhas: list[str] = []
    linha_atual = prefixo
    for p in palavras:
        if len(linha_atual) + len(p) + 1 > largura:
            linhas.append(linha_atual.rstrip())
            linha_atual = prefixo + p + " "
        else:
            linha_atual += p + " "
    if linha_atual.strip():
        linhas.append(linha_atual.rstrip())
    return "\n".join(linhas)


def _secao(titulo: str) -> str:
    return f"▌ {titulo.upper()}"


def _custo_ganho(c: dict) -> tuple[int, int]:
    """Custo e ganho de conexão de uma conjuração (nomes novos + legado)."""
    custo = c.get("custo", c.get("conexao_custo", 0))
    ganho = c.get("ganho_conexao", c.get("conexao_ganho", 0))
    return custo, ganho


def _conjuracao_resumo(c: dict) -> list[str]:
    """Linhas de texto (≤ largura) com a mecânica de uma conjuração/habilidade."""
    nome  = str(c.get("nome", "?"))
    alc   = c.get("alcance", "?") or "?"
    area  = c.get("area", "?") or "?"
    if c.get("tem_dano"):
        dd = c.get("dado_dano") or {}
        dano = f"{dd.get('x', '?')}d{dd.get('y', '?')}"
    else:
        dano = "utilitária"
    custo, ganho = _custo_ganho(c)

    linhas = [
        f"  • {nome}"[: _LARGURA - 2],
        f"      {dano} · {alc}/{area}"[: _LARGURA - 2],
        f"      Conexão -{custo} / +{ganho}"[: _LARGURA - 2],
    ]
    efeitos = [str(e) for e in (c.get("efeitos") or [])]
    if efeitos:
        linhas.append(f"      Efeitos: {', '.join(efeitos)}"[: _LARGURA - 2])
    return linhas


def _abrir(linhas: list[str]) -> None:
    linhas.append("╔" + "═" * _LARGURA + "╗")


def _row(txt: str) -> str:
    pad = _LARGURA - len(txt) - 2
    return f"║  {txt}" + " " * max(0, pad) + "║"


def _div(linhas: list[str]) -> None:
    linhas.append("╠" + "═" * _LARGURA + "╣")


def _bloco_texto(linhas: list[str], texto: str) -> None:
    for ln in _wrap(texto).split("\n"):
        pad = _LARGURA - len(ln) - 2
        linhas.append(f"║{ln}" + " " * max(0, pad) + "  ║")


# ─── Conjurador ───────────────────────────────────────────────────────────────

def ficha_conjurador(d: dict[str, Any]) -> str:
    nome   = d.get("nome", "?")
    grau   = d.get("grau_ressonancia", d.get("nivel", 1))
    idade  = d.get("idade")
    escola = d.get("escola", "?")
    vida_max = d.get("vida_maxima", d.get("vida", "?"))
    vida_at  = d.get("vida_atual", vida_max)
    con_max  = d.get("conexao_maxima", d.get("conexao", "?"))
    con_at   = d.get("conexao_atual", con_max)
    attrs  = d.get("atributos", {})
    pericias = d.get("pericias", [])
    ecos = d.get("ecos", [])
    reliquias = d.get("reliquias", [])
    historia = d.get("historia", "")
    aparencia = d.get("aparencia", "")
    aviso  = d.get("_aviso", "")

    linhas: list[str] = []
    _abrir(linhas)
    titulo = f"CONJURADOR  ·  {str(nome).upper()}"
    linhas.append(_row(titulo))
    idade_str = f"{idade} anos  ·  " if idade not in (None, "", "?") else ""
    linhas.append(_row(f"Grau {grau}  ·  {idade_str}{escola}"))
    _div(linhas)

    # Stats
    vida_str = f"VIDA: {vida_at}/{vida_max}"
    con_str  = f"CONEXÃO: {con_at}/{con_max}"
    gap = _LARGURA - len(vida_str) - len(con_str) - 2
    linhas.append(f"║  {vida_str}" + " " * max(0, gap) + f"{con_str}  ║")
    _div(linhas)

    # Atributos + Perícias lado a lado
    nomes_attr = ["Brutalidade", "Rapidez", "Vitalidade", "Influência", "Sintonia", "Astúcia"]
    chaves     = ["brutalidade", "rapidez", "vitalidade", "influencia", "sintonia", "astucia"]
    linhas.append("║  ATRIBUTOS              │  PERÍCIAS               ║")
    linhas.append("║  " + "─" * 22 + "┼" + "─" * 24 + "║")

    max_linhas = max(len(nomes_attr), len(pericias))
    for i in range(max_linhas):
        if i < len(nomes_attr):
            val = attrs.get(chaves[i], 0)
            barra = _barra_attr(val)
            attr_col = f"{nomes_attr[i][:10]:<10} {barra} {val}"
        else:
            attr_col = ""
        per_col = f"• {str(pericias[i])[:20]}" if i < len(pericias) else ""
        a_pad = 22 - len(attr_col)
        p_pad = 24 - len(per_col)
        linhas.append(f"║  {attr_col}{' ' * max(0, a_pad)}│  {per_col}{' ' * max(0, p_pad)}║")

    if ecos:
        _div(linhas)
        linhas.append(_row(_secao("ecos")))
        for e in ecos:
            linhas.append(_row(f"  • {e}"))

    if reliquias:
        _div(linhas)
        linhas.append(_row(_secao("relíquias")))
        for r in reliquias:
            linhas.append(_row(f"  • {r}"))

    if aparencia:
        _div(linhas)
        linhas.append(_row(_secao("aparência")))
        _bloco_texto(linhas, aparencia)

    if historia:
        _div(linhas)
        linhas.append(_row(_secao("história")))
        _bloco_texto(linhas, historia)

    if aviso:
        linhas.append("╠" + "─" * _LARGURA + "╣")
        linhas.append(_row(f"⚠  {aviso}"))

    linhas.append("╚" + "═" * _LARGURA + "╝")
    return "\n".join(linhas)


# ─── Relíquia ─────────────────────────────────────────────────────────────────

def ficha_reliquia(d: dict[str, Any]) -> str:
    nome    = d.get("nome", "?")
    desc    = d.get("descricao", "")
    matriz  = d.get("matriz", "?")
    sub     = d.get("submatriz", "NENHUMA")
    nucleo  = d.get("nucleo", "?")
    nivel   = d.get("nivel", "?")
    alcance = d.get("alcance", "?")
    dano_d  = d.get("dado_dano", {})
    conjs   = d.get("conjuracoes", [])

    dano_str = f"{dano_d.get('x','?')}d{dano_d.get('y','?')}"
    subm_str = "" if sub in ("NENHUMA", None, "") else f" · {sub}"

    linhas: list[str] = []
    _abrir(linhas)
    linhas.append(_row(f"RELÍQUIA  ·  {str(nome).upper()}"))
    linhas.append(_row(f"Nível {nivel}"))
    _div(linhas)

    linhas.append(_row(f"Matriz:    {matriz}{subm_str}"))
    linhas.append(_row(f"Núcleo:    {nucleo}"))
    linhas.append(_row(f"Alcance:   {alcance}"))
    linhas.append(_row(f"Dano:      {dano_str}"))

    if desc:
        _div(linhas)
        linhas.append(_row(_secao("descrição")))
        _bloco_texto(linhas, desc)

    if conjs:
        _div(linhas)
        linhas.append(_row(_secao("conjurações")))
        for c in conjs:
            if isinstance(c, dict):
                for ln in _conjuracao_resumo(c):
                    linhas.append(_row(ln))
            else:
                linhas.append(_row(f"  • {c}"))

    linhas.append("╚" + "═" * _LARGURA + "╝")
    return "\n".join(linhas)


# ─── Conjuração ───────────────────────────────────────────────────────────────

def ficha_conjuracao(d: dict[str, Any]) -> str:
    nome     = d.get("nome", "?")
    desc     = d.get("descricao", "")
    matriz   = d.get("matriz", "?")
    sub      = d.get("submatriz", "NENHUMA")
    alcance  = d.get("alcance", "?")
    area     = d.get("area", "?")
    gasto    = d.get("gasto_acao", "?")
    custo, ganho = _custo_ganho(d)
    tem_dano = d.get("tem_dano", False)
    dano_d   = d.get("dado_dano", {})
    efeitos  = d.get("efeitos", [])

    subm_str = "" if sub in ("NENHUMA", None, "") else f" · {sub}"
    dano_str = f"{dano_d.get('x','?')}d{dano_d.get('y','?')}" if tem_dano else "Utilitária"
    con_str  = f"▼ Custo {custo}  ·  ▲ Ganho {ganho}"

    linhas: list[str] = []
    _abrir(linhas)
    linhas.append(_row(f"CONJURAÇÃO  ·  {str(nome).upper()}"))
    linhas.append(_row(f"{gasto}"))
    _div(linhas)

    linhas.append(_row(f"Matriz:    {matriz}{subm_str}"))
    linhas.append(_row(f"Alcance:   {alcance:<12}  Área: {area}"))
    linhas.append(_row(f"Dano:      {dano_str}"))
    linhas.append(_row(f"Conexão:   {con_str}"))

    if efeitos:
        _div(linhas)
        linhas.append(_row(_secao("efeitos")))
        for e in efeitos:
            linhas.append(_row(f"  • {e}"))

    if desc:
        _div(linhas)
        linhas.append(_row(_secao("descrição")))
        _bloco_texto(linhas, desc)

    linhas.append("╚" + "═" * _LARGURA + "╝")
    return "\n".join(linhas)


# ─── Familiar ─────────────────────────────────────────────────────────────────

def ficha_familiar(d: dict[str, Any]) -> str:
    nome     = d.get("nome", "?")
    especie  = d.get("especie_base", "")
    matriz   = d.get("matriz", "?")
    sub      = d.get("submatriz", "NENHUMA")
    patamar  = d.get("patamar", "?")
    ameaca   = d.get("nivel_ameaca", "?")
    porte    = d.get("porte", "?")
    cobertura = d.get("cobertura", "?")
    coloracao = d.get("coloracao", "")
    carac    = d.get("caracteristicas_matriz", [])
    temper   = d.get("temperamento", "?")
    habito   = d.get("habito", "?")
    social   = d.get("socializacao", "?")
    bioma    = d.get("bioma", "")
    regiao   = d.get("regiao", "")
    fisicas  = d.get("habilidades_fisicas", [])
    de_matriz = d.get("habilidades_matriz", [])
    desc     = d.get("descricao", "")

    subm_str = "" if sub in ("NENHUMA", None, "") else f" · {sub}"

    linhas: list[str] = []
    _abrir(linhas)
    linhas.append(_row(f"FAMILIAR  ·  {str(nome).upper()}"))
    if especie:
        linhas.append(_row(f"Espécie: {especie}"))
    _div(linhas)
    linhas.append(_row(f"Matriz:    {matriz}{subm_str}"))
    linhas.append(_row(f"Patamar:   {patamar}      Ameaça: {ameaca}"))
    linhas.append(_row(f"Porte:     {porte:<12}  Cobertura: {cobertura}"))
    if coloracao:
        linhas.append(_row(f"Cor:       {coloracao}"[: _LARGURA - 2]))
    linhas.append(_row(f"Comport.:  {temper} · {habito} · {social}"[: _LARGURA - 2]))
    if bioma or regiao:
        hab = " · ".join(x for x in (bioma, regiao) if x)
        linhas.append(_row(f"Habitat:   {hab}"[: _LARGURA - 2]))

    if carac:
        _div(linhas)
        linhas.append(_row(_secao("características da matriz")))
        for c in carac:
            linhas.append(_row(f"  • {c}"[: _LARGURA - 2]))

    if fisicas:
        _div(linhas)
        linhas.append(_row(_secao("habilidades físicas")))
        for h in fisicas:
            linhas.append(_row(f"  • {h}"))

    if de_matriz:
        _div(linhas)
        linhas.append(_row(_secao("habilidades de matriz")))
        for h in de_matriz:
            linhas.append(_row(f"  • {h}"))

    if desc:
        _div(linhas)
        linhas.append(_row(_secao("descrição")))
        _bloco_texto(linhas, desc)

    linhas.append("╚" + "═" * _LARGURA + "╝")
    return "\n".join(linhas)


# ─── Dispatcher ───────────────────────────────────────────────────────────────

_FORMATADORES = {
    "conjurador": ficha_conjurador,
    "reliquia":   ficha_reliquia,
    "conjuracao": ficha_conjuracao,
    "familiar":   ficha_familiar,
}


def formatar(tipo: str, dados: dict[str, Any], ascii_mode: bool = False) -> str:
    """Retorna a ficha formatada em texto para o tipo e dados fornecidos.

    Com ascii_mode=True, os caracteres de box-drawing são convertidos para
    ASCII (para ambientes sem fonte com esses glifos). O padrão mantém o
    visual Unicode (terminais e arquivos).
    """
    fn = _FORMATADORES.get(tipo)
    if fn is None:
        return f"(sem formatador para '{tipo}')"
    try:
        texto = fn(dados)
    except Exception as e:
        return f"(erro ao formatar ficha: {e})"
    return _to_ascii(texto) if ascii_mode else texto
