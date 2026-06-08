# Regras determinísticas do Sistema das Relíquias.
# Fonte da verdade: regras/ (espelho de github.com/Tody0224/RPG_scheema).
# Nenhuma lógica aqui depende do LLM.
import random
import unicodedata

# GRAU DE RESSONÂNCIA — substitui o antigo "nível". Vai de 1 a 30
# (Progressao_de_nivel.md). É a entrada que dimensiona VIDA, CONEXÃO,
# atributos, perícias e ecos.
GRAU_MIN, GRAU_MAX = 1, 30

# MATRIZES canônicas (Matrizes.md — o schema importa daqui).
MATRIZES = [
    "INCÊNDIO", "INUNDAÇÃO", "TEMPESTADE", "CICLONE", "TERREMOTO",
    "NEUTRO", "MARCIAL", "FAUNA", "FLORA", "GUARDIÃO", "FÁBULA",
    "SÓLIDO", "MALEÁVEL", "ESCURO", "ESPIRITUAL", "MENTAL",
]

# SUBMATRIZES (Matrizes.md). "NENHUMA" é o sentinela de "sem submatriz"
# (o campo é opcional nos schemas).
SUBMATRIZES = ["ONDA", "FÚRIA", "ESPORO", "TEMPERATURA", "ESPIRAL", "NENHUMA"]

# ESCOLAS (Escolas.md). INABALÁVEL acentuado conforme o repositório.
ESCOLAS = ["DESTEMIDO", "CANALIZADOR", "INABALÁVEL", "OPORTUNISTA", "CALCULISTA", "FACILITADOR"]

# Gasto de ação de uma CONJURAÇÃO (Acoes.md / Schema_Conjuracao.md).
GASTOS_ACAO = ["AÇÃO DE LOCOMOÇÃO", "AÇÃO COMPLEXA", "AÇÃO EXTRA"]

# Enums descritivos de FAMILIAR (Schema_Familiar.md).
PORTES = ["MINÚSCULO", "PEQUENO", "MÉDIO", "GRANDE", "GIGANTE"]
COBERTURAS = ["PELOS", "PENAS", "ESCAMAS", "CARAPAÇA", "PELE", "OUTRO"]
TEMPERAMENTOS = ["PASSIVO", "TERRITORIAL", "AGRESSIVO", "CURIOSO", "PREDADOR"]
HABITOS = ["DIURNO", "NOTURNO", "CREPUSCULAR"]
SOCIALIZACOES = ["SOLITÁRIO", "CASAL", "BANDO", "COLÔNIA"]

# Efeitos canônicos de uma CONJURAÇÃO = CONDIÇÕES (Condicoes.md) + MANOBRAS
# (Manobras.md). O schema novo também aceita EFEITOS PERSONALIZADOS (texto
# livre), então estas listas servem como vocabulário sugerido, não como trava.
CONDICOES = [
    "CAÍDO", "AGARRADO", "IMOBILIZADO", "ABALADO", "PROVOCADO", "ATORDOADO",
    "DESMORALIZADO", "EXPOSTO", "SANGRANDO", "ENVENENADO", "INCENDIADO",
    "CONGELADO", "ELETROCUTADO", "CEGO", "SURDO", "SILENCIADO", "INCONSCIENTE",
    "MORRENDO", "INVISÍVEL", "OCULTO", "AMEDRONTADO", "FORTIFICADO",
    "ACELERADO", "ENFRAQUECIDO", "EXAUSTO",
]
MANOBRAS = ["DERRUBAR", "EMPURRAR", "AGARRAR", "MOVER", "ARREMESSAR", "IMOBILIZAR", "PROVOCAR"]
EFEITOS = CONDICOES + MANOBRAS

ATRIBUTOS = ["brutalidade", "rapidez", "vitalidade", "influencia", "sintonia", "astucia"]

# Range absoluto de um atributo (Atributos.md): 0 a 6.
ATR_MIN, ATR_MAX = 0, 6


def _sem_acentos(texto: str) -> str:
    """Minúsculo e sem acentos, para comparação tolerante (guardião≈guardiao)."""
    nfd = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def matriz_no_conceito(conceito: str) -> str | None:
    """Detecta uma MATRIZ citada no conceito (ex.: 'matriz guardião' → 'GUARDIÃO').

    Comparação tolerante a acentos. Retorna a matriz ou None se nenhuma aparecer.
    """
    alvo = _sem_acentos(conceito)
    for matriz in MATRIZES:
        if _sem_acentos(matriz) in alvo:
            return matriz
    return None


# Lista canônica de PERÍCIAS (Pericias.md: 19 oficiais). ASTÚCIA e INFLUÊNCIA
# aparecem como opções nos pools de algumas escolas (Escolas.md), então também
# são aceitas como perícias treináveis.
PERICIAS = [
    "EQUILÍBRIO", "POTÊNCIA", "OFÍCIOS", "DOMESTICAÇÃO", "ERUDIÇÃO",
    "MALANDRAGEM", "PERSUASÃO", "ENGANAÇÃO", "RESILIÊNCIA", "INICIATIVA",
    "AMEAÇA", "COMBATE", "MEDICINA", "CONJURAÇÃO", "SENTIDOS",
    "ESQUIVA", "CRENÇA", "SOBREVIVÊNCIA", "VONTADE",
    # Citadas nos pools das escolas (Escolas.md), embora sejam atributos.
    "ASTÚCIA", "INFLUÊNCIA",
]

# Pool de perícias de cada ESCOLA e quantas o personagem escolhe dele no grau 1
# (Escolas.md). A quantidade TOTAL de perícias treinadas, porém, segue a
# progressão de grau (ver total_pericias) — o pool define a preferência de
# preenchimento, não o total.
ESCOLAS_PERICIAS: dict[str, tuple[list[str], int]] = {
    "DESTEMIDO":   (["POTÊNCIA", "INICIATIVA", "COMBATE", "RESILIÊNCIA", "EQUILÍBRIO", "AMEAÇA"], 2),
    "CANALIZADOR": (["CONJURAÇÃO", "SENTIDOS", "CRENÇA", "ASTÚCIA", "VONTADE", "PERSUASÃO"], 2),
    "INABALÁVEL":  (["POTÊNCIA", "RESILIÊNCIA", "COMBATE", "CRENÇA", "VONTADE", "AMEAÇA"], 2),
    "OPORTUNISTA": (["MALANDRAGEM", "EQUILÍBRIO", "INICIATIVA", "SENTIDOS", "ENGANAÇÃO", "ESQUIVA"], 2),
    "CALCULISTA":  (["ASTÚCIA", "OFÍCIOS", "SENTIDOS", "INICIATIVA", "COMBATE", "ERUDIÇÃO"], 3),
    "FACILITADOR": (["PERSUASÃO", "CONJURAÇÃO", "ENGANAÇÃO", "CRENÇA", "INFLUÊNCIA", "VONTADE"], 3),
}

# Marcos da progressão de GRAU DE RESSONÂNCIA (Progressao_de_nivel.md).
_MARCOS_ATRIBUTO = (6, 12, 18, 24, 30)            # +1 ponto de atributo em cada
_MARCOS_PERICIA = (5, 10, 15, 20, 25, 30)         # +1 perícia treinada em cada
_GRAUS_ECO = (1, 5, 10, 15, 20, 25, 30)           # +1 eco em cada (máx 7)


def clampar_grau(grau: int) -> int:
    """Restringe o GRAU DE RESSONÂNCIA ao intervalo válido [1, 30]."""
    try:
        return max(GRAU_MIN, min(GRAU_MAX, int(grau)))
    except (TypeError, ValueError):
        return GRAU_MIN


def soma_atributos(grau: int) -> int:
    """Soma alvo dos atributos no GRAU: 10 na criação + 1 por marco de atributo.

    Marcos em 6/12/18/24/30 concedem +1 ponto cada (Progressao_de_nivel.md).
    """
    g = clampar_grau(grau)
    return 10 + sum(1 for marco in _MARCOS_ATRIBUTO if g >= marco)


def total_pericias(grau: int) -> int:
    """Nº de PERÍCIAS treinadas no GRAU: 3 no grau 1 + 1 por marco de perícia.

    Marcos em 5/10/15/20/25/30 (Progressao_de_nivel.md).
    """
    g = clampar_grau(grau)
    return 3 + sum(1 for marco in _MARCOS_PERICIA if g >= marco)


def total_ecos(grau: int) -> int:
    """Nº de ECOS adquiridos no GRAU (graus 1/5/10/15/20/25/30, máx 7)."""
    g = clampar_grau(grau)
    return sum(1 for marco in _GRAUS_ECO if g >= marco)


def rolar(quantidade: int, lados: int, _rng: random.Random | None = None) -> list[int]:
    """Rola `quantidade` dados de `lados` lados. Aceita `_rng` para testes determinísticos."""
    rng: random.Random = _rng or random.SystemRandom()  # type: ignore[assignment]
    return [rng.randint(1, lados) for _ in range(max(0, quantidade))]


def calcular_vida(grau: int, vitalidade: int, _rng: random.Random | None = None) -> int:
    """VIDA MÁXIMA = 8 + (GRAU × VITALIDADE) + soma de GRAU rolagens de 1d6.

    (Vida.md: a cada grau adquirido rola-se 1d6 e soma-se à VIDA MÁXIMA.)
    """
    g = clampar_grau(grau)
    dados = rolar(g, 6, _rng)
    return 8 + (g * vitalidade) + sum(dados)


def calcular_conexao(grau: int, sintonia: int, _rng: random.Random | None = None) -> int:
    """CONEXÃO MÁXIMA = GRAU + (SINTONIA × 2) + 1d4 (Conexao.md)."""
    g = clampar_grau(grau)
    d4 = rolar(1, 4, _rng)[0]
    return g + (sintonia * 2) + d4


def validar_atributos(atributos: dict[str, int], grau: int = 1) -> tuple[bool, str]:
    """
    Valida os atributos do conjurador conforme as regras (Atributos.md):
    - Valores de 0 a 6 cada
    - No máximo um atributo zerado
    - Soma igual a soma_atributos(GRAU) — 10 na criação + 1 por marco de atributo
    Retorna (True, "") se válido, ou (False, mensagem_de_erro).
    """
    valores = [atributos.get(a, 0) for a in ATRIBUTOS]

    for nome, val in zip(ATRIBUTOS, valores):
        if not isinstance(val, int) or not (ATR_MIN <= val <= ATR_MAX):
            return False, f"Atributo '{nome}' = {val!r} fora do intervalo [{ATR_MIN}, {ATR_MAX}]"

    zeros = sum(1 for v in valores if v == 0)
    if zeros > 1:
        return False, f"{zeros} atributos zerados; no máximo um é permitido"

    alvo = soma_atributos(grau)
    total = sum(valores)
    if total != alvo:
        return False, f"Soma dos atributos = {total}; deve ser exatamente {alvo} (grau {clampar_grau(grau)})"

    return True, ""


def corrigir_atributos(atributos: dict[str, int], grau: int = 1) -> dict[str, int]:
    """
    Corrige atributos inválidos retornados pelo LLM para satisfazer as regras.
    Trunca valores fora de [0, 6], elimina zeros extras e ajusta a soma para
    soma_atributos(GRAU). Preserva, quando possível, o único atributo zerado.
    """
    alvo = soma_atributos(grau)
    corrigido = {a: max(ATR_MIN, min(ATR_MAX, int(atributos.get(a, 1)))) for a in ATRIBUTOS}

    # Garante no máximo um zero (mantém o primeiro encontrado)
    zeros = [a for a in ATRIBUTOS if corrigido[a] == 0]
    for a in zeros[1:]:
        corrigido[a] = 1

    zero_attr = next((a for a in ATRIBUTOS if corrigido[a] == 0), None)

    # Aumenta atributos não-máximos até a soma alvo
    for a in ATRIBUTOS:
        if sum(corrigido.values()) >= alvo:
            break
        espaco = ATR_MAX - corrigido[a]
        add = min(espaco, alvo - sum(corrigido.values()))
        corrigido[a] += add

    # Diminui atributos não-mínimos até a soma alvo
    for a in reversed(ATRIBUTOS):
        if sum(corrigido.values()) <= alvo:
            break
        if a == zero_attr:
            continue  # Não toca no atributo intencionalmente zerado
        remove = min(corrigido[a] - 1, sum(corrigido.values()) - alvo)
        corrigido[a] -= remove

    return corrigido


def contar_pericias(grau: int) -> int:
    """Número de PERÍCIAS treinadas de um conjurador no GRAU (= total_pericias)."""
    return total_pericias(grau)


def ajustar_pericias(escola: str, grau: int, pericias) -> list[str]:
    """
    Ajusta a lista de perícias para conter exatamente total_pericias(GRAU) itens.
    Mantém as perícias válidas fornecidas (sem duplicar) e, se faltarem, preenche
    primeiro com o pool da ESCOLA e depois com as demais perícias.
    """
    escola_u = escola.upper() if isinstance(escola, str) else ""
    pool, _ = ESCOLAS_PERICIAS.get(escola_u, ([], 2))
    alvo = total_pericias(grau)

    final: list[str] = []
    for p in pericias or []:
        if not isinstance(p, str):
            continue
        nome = p.strip().upper()
        if nome in PERICIAS and nome not in final:
            final.append(nome)

    # Preenche o que faltar: primeiro do pool da escola, depois das demais perícias
    if len(final) < alvo:
        for fonte in (pool, PERICIAS):
            for nome in fonte:
                if len(final) >= alvo:
                    break
                if nome not in final:
                    final.append(nome)
            if len(final) >= alvo:
                break

    return final[:alvo]
