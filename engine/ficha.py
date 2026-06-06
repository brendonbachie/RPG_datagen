# Renderiza fichas formatadas em texto para cada tipo de entidade.
from typing import Any

_LARGURA = 52


def _linha(char: str = "─") -> str:
    return char * _LARGURA


def _caixa_titulo(texto: str, char_borda: str = "═") -> str:
    interno = f"  {texto}  "
    pad = _LARGURA - len(interno)
    esq = pad // 2
    dir_ = pad - esq
    return (
        "╔" + char_borda * _LARGURA + "╗\n"
        + "║" + " " * esq + interno + " " * dir_ + "║\n"
        + "╚" + char_borda * _LARGURA + "╝"
    )


def _barra_attr(valor: int, maximo: int = 3) -> str:
    preenchido = "█" * max(0, valor)
    vazio = "░" * max(0, maximo - valor)
    return preenchido + vazio


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


# ─── Conjurador ───────────────────────────────────────────────────────────────

def ficha_conjurador(d: dict[str, Any]) -> str:
    nome   = d.get("nome", "?")
    nivel  = d.get("nivel", 1)
    idade  = d.get("idade") or "?"
    escola = d.get("escola", "?")
    vida   = d.get("vida", "?")
    con    = d.get("conexao", "?")
    attrs  = d.get("atributos", {})
    pericias = d.get("pericias", [])
    historia = d.get("historia", "")
    aparencia = d.get("aparencia", "")
    aviso  = d.get("_aviso", "")

    linhas: list[str] = []
    linhas.append("╔" + "═" * _LARGURA + "╗")
    titulo = f"CONJURADOR  ·  {nome.upper()}"
    pad = _LARGURA - len(titulo) - 2
    linhas.append(f"║  {titulo}" + " " * pad + "║")
    sub = f"Nível {nivel}  ·  {idade}  ·  {escola}"
    pad2 = _LARGURA - len(sub) - 2
    linhas.append(f"║  {sub}" + " " * pad2 + "║")
    linhas.append("╠" + "═" * _LARGURA + "╣")

    # Stats
    vida_str = f"VIDA: {vida}"
    con_str  = f"CONEXÃO: {con}"
    gap = _LARGURA - len(vida_str) - len(con_str) - 2
    linhas.append(f"║  {vida_str}" + " " * gap + f"{con_str}  ║")
    linhas.append("╠" + "═" * _LARGURA + "╣")

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
        per_col = f"• {pericias[i][:20]}" if i < len(pericias) else ""
        a_pad = 22 - len(attr_col)
        p_pad = 24 - len(per_col)
        linhas.append(f"║  {attr_col}{' ' * a_pad}│  {per_col}{' ' * p_pad}║")

    if aparencia:
        linhas.append("╠" + "═" * _LARGURA + "╣")
        linhas.append("║  " + _secao("aparência") + " " * (_LARGURA - len(_secao("aparência")) - 4) + "  ║")
        for ln in _wrap(aparencia).split("\n"):
            pad = _LARGURA - len(ln) - 2
            linhas.append(f"║{ln}" + " " * pad + "  ║")

    if historia:
        linhas.append("╠" + "═" * _LARGURA + "╣")
        linhas.append("║  " + _secao("história") + " " * (_LARGURA - len(_secao("história")) - 4) + "  ║")
        for ln in _wrap(historia).split("\n"):
            pad = _LARGURA - len(ln) - 2
            linhas.append(f"║{ln}" + " " * pad + "  ║")

    if aviso:
        linhas.append("╠" + "─" * _LARGURA + "╣")
        av = f"⚠  {aviso}"
        pad = _LARGURA - len(av) - 2
        linhas.append(f"║  {av}" + " " * pad + "║")

    linhas.append("╚" + "═" * _LARGURA + "╝")
    return "\n".join(linhas)


# ─── Relíquia ─────────────────────────────────────────────────────────────────

def ficha_reliquia(d: dict[str, Any]) -> str:
    nome     = d.get("nome", "?")
    desc     = d.get("descricao", "")
    matriz   = d.get("matriz", "?")
    sub      = d.get("submatriz", "NENHUMA")
    forma    = d.get("forma", "?")
    nucleo   = d.get("nucleo", "?")
    vetor    = d.get("vetor", "?")
    nivel    = d.get("nivel", "?")
    alcance  = d.get("alcance", "?")
    area     = d.get("area", "?")
    dano_d   = d.get("dado_dano", {})
    tipos    = d.get("tipos_dano", [])
    critico  = d.get("mult_critico", "?")
    conjs    = d.get("conjuracoes", [])
    fam_nome = d.get("familiar_nome", "?")
    fam_desc = d.get("familiar_descricao", "")
    fam_comp = d.get("familiar_comportamento", "")

    dano_str = f"{dano_d.get('x','?')}d{dano_d.get('y','?')}"
    tipos_str = " · ".join(tipos) if tipos else "—"
    subm_str = "" if sub in ("NENHUMA", None) else f" · {sub}"

    linhas: list[str] = []
    linhas.append("╔" + "═" * _LARGURA + "╗")

    def _row(txt: str) -> str:
        pad = _LARGURA - len(txt) - 2
        return f"║  {txt}" + " " * pad + "║"

    linhas.append(_row(f"RELÍQUIA  ·  {nome.upper()}"))
    linhas.append(_row(f"{forma}  ·  Nível {nivel}"))
    linhas.append("╠" + "═" * _LARGURA + "╣")

    # Propriedades mecânicas
    linhas.append(_row(f"Matriz:    {matriz}{subm_str}"))
    linhas.append(_row(f"Núcleo:    {nucleo}"))
    linhas.append(_row(f"Vetor:     {vetor}"))
    linhas.append(_row(f"Alcance:   {alcance:<10}  Área: {area}"))
    linhas.append(_row(f"Dano:      {dano_str:<10}  Crit: ×{critico}"))
    linhas.append(_row(f"Tipo:      {tipos_str}"))

    if desc:
        linhas.append("╠" + "═" * _LARGURA + "╣")
        linhas.append(_row(_secao("descrição")))
        for ln in _wrap(desc).split("\n"):
            pad = _LARGURA - len(ln) - 2
            linhas.append(f"║{ln}" + " " * pad + "  ║")

    if conjs:
        linhas.append("╠" + "═" * _LARGURA + "╣")
        linhas.append(_row(_secao("conjurações")))
        for c in conjs:
            linhas.append(_row(f"  • {c}"))

    # Familiar de origem
    linhas.append("╠" + "═" * _LARGURA + "╣")
    linhas.append(_row(f"FAMILIAR DE ORIGEM:  {fam_nome}"))
    if fam_desc:
        for ln in _wrap(fam_desc).split("\n"):
            pad = _LARGURA - len(ln) - 2
            linhas.append(f"║{ln}" + " " * pad + "  ║")
    if fam_comp:
        linhas.append(_row("Comportamento:"))
        for ln in _wrap(fam_comp).split("\n"):
            pad = _LARGURA - len(ln) - 2
            linhas.append(f"║{ln}" + " " * pad + "  ║")

    linhas.append("╚" + "═" * _LARGURA + "╝")
    return "\n".join(linhas)


# ─── Conjuração ───────────────────────────────────────────────────────────────

def ficha_conjuracao(d: dict[str, Any]) -> str:
    nome     = d.get("nome", "?")
    desc     = d.get("descricao", "")
    matriz   = d.get("matriz", "?")
    sub      = d.get("submatriz", "NENHUMA")
    nivel    = d.get("nivel", 0)
    alcance  = d.get("alcance", "?")
    area     = d.get("area", "?")
    custo    = d.get("conexao_custo", 0)
    ganho    = d.get("conexao_ganho", 0)
    tem_dano = d.get("tem_dano", False)
    dano_d   = d.get("dado_dano", {})
    efeitos  = d.get("efeitos", [])

    subm_str = "" if sub in ("NENHUMA", None) else f" · {sub}"
    dano_str = f"{dano_d.get('x','?')}d{dano_d.get('y','?')}" if tem_dano else "Utilitária"
    con_str  = f"▼ Custo {custo}  ·  ▲ Ganho {ganho}"

    linhas: list[str] = []
    linhas.append("╔" + "═" * _LARGURA + "╗")

    def _row(txt: str) -> str:
        pad = _LARGURA - len(txt) - 2
        return f"║  {txt}" + " " * pad + "║"

    linhas.append(_row(f"CONJURAÇÃO  ·  {nome.upper()}"))
    nivel_nome = ["Simples", "Aprimorada", "Avançada", "Extraordinária"]
    linhas.append(_row(f"Nível {nivel}  —  {nivel_nome[min(nivel, 3)]}"))
    linhas.append("╠" + "═" * _LARGURA + "╣")

    linhas.append(_row(f"Matriz:    {matriz}{subm_str}"))
    linhas.append(_row(f"Alcance:   {alcance:<12}  Área: {area}"))
    linhas.append(_row(f"Dano:      {dano_str}"))
    linhas.append(_row(f"Conexão:   {con_str}"))

    if efeitos:
        linhas.append("╠" + "═" * _LARGURA + "╣")
        linhas.append(_row(_secao("efeitos")))
        for e in efeitos:
            linhas.append(_row(f"  • {e}"))

    if desc:
        linhas.append("╠" + "═" * _LARGURA + "╣")
        linhas.append(_row(_secao("descrição")))
        for ln in _wrap(desc).split("\n"):
            pad = _LARGURA - len(ln) - 2
            linhas.append(f"║{ln}" + " " * pad + "  ║")

    linhas.append("╚" + "═" * _LARGURA + "╝")
    return "\n".join(linhas)


# ─── Familiar ─────────────────────────────────────────────────────────────────

def ficha_familiar(d: dict[str, Any]) -> str:
    nome       = d.get("nome", "?")
    desc       = d.get("descricao", "")
    comp       = d.get("comportamento", "")
    matriz     = d.get("matriz", "?")
    sub        = d.get("submatriz", "NENHUMA")
    habs       = d.get("habilidades", [])
    raridade   = d.get("raridade", "?")

    subm_str = "" if sub in ("NENHUMA", None) else f" · {sub}"

    linhas: list[str] = []
    linhas.append("╔" + "═" * _LARGURA + "╗")

    def _row(txt: str) -> str:
        pad = _LARGURA - len(txt) - 2
        return f"║  {txt}" + " " * pad + "║"

    linhas.append(_row(f"FAMILIAR  ·  {nome.upper()}"))
    linhas.append(_row(f"Raridade: {raridade}"))
    linhas.append("╠" + "═" * _LARGURA + "╣")
    linhas.append(_row(f"Matriz:   {matriz}{subm_str}"))

    if habs:
        linhas.append("╠" + "═" * _LARGURA + "╣")
        linhas.append(_row(_secao("habilidades")))
        for h in habs:
            linhas.append(_row(f"  • {h}"))

    if desc:
        linhas.append("╠" + "═" * _LARGURA + "╣")
        linhas.append(_row(_secao("aparência")))
        for ln in _wrap(desc).split("\n"):
            pad = _LARGURA - len(ln) - 2
            linhas.append(f"║{ln}" + " " * pad + "  ║")

    if comp:
        linhas.append("╠" + "═" * _LARGURA + "╣")
        linhas.append(_row(_secao("comportamento")))
        for ln in _wrap(comp).split("\n"):
            pad = _LARGURA - len(ln) - 2
            linhas.append(f"║{ln}" + " " * pad + "  ║")

    linhas.append("╚" + "═" * _LARGURA + "╝")
    return "\n".join(linhas)


# ─── Dispatcher ───────────────────────────────────────────────────────────────

_FORMATADORES = {
    "conjurador": ficha_conjurador,
    "reliquia":   ficha_reliquia,
    "conjuracao": ficha_conjuracao,
    "familiar":   ficha_familiar,
}


def formatar(tipo: str, dados: dict[str, Any]) -> str:
    """Retorna a ficha formatada em texto para o tipo e dados fornecidos."""
    fn = _FORMATADORES.get(tipo)
    if fn is None:
        return f"(sem formatador para '{tipo}')"
    try:
        return fn(dados)
    except Exception as e:
        return f"(erro ao formatar ficha: {e})"
