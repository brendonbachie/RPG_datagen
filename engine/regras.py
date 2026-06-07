# Regras determinísticas do Sistema das Relíquias.
# Nenhuma lógica aqui depende do LLM.
import random
import re
import unicodedata

# MATRIZES canônicas (fonte da verdade — o schema importa daqui).
MATRIZES = [
    "INCÊNDIO", "INUNDAÇÃO", "TEMPESTADE", "CICLONE", "TERREMOTO",
    "NEUTRO", "MARCIAL", "FAUNA", "FLORA", "GUARDIÃO", "FÁBULA",
    "SÓLIDO", "MALEÁVEL", "ESCURO", "ESPIRITUAL", "MENTAL",
]


# Efeitos válidos de uma CONJURAÇÃO = CONDIÇÕES (fonte: Condições.txt) +
# MANOBRAS (fonte: Manobras.txt). O schema restringe 'efeitos' a esta lista,
# o que impede o LLM de "vazar" texto livre (nome/conceito) no campo.
CONDICOES = [
    "CAÍDO", "AGARRADO", "IMOBILIZADO", "ABALADO", "PROVOCADO", "ATORDOADO",
    "DESMORALIZADO", "EXPOSTO", "SANGRANDO", "ENVENENADO", "INCENDIADO",
    "CONGELADO", "ELETROCUTADO", "CEGO", "SURDO", "SILENCIADO", "INCONSCIENTE",
    "MORRENDO", "INVISÍVEL", "OCULTO", "AMEDRONTADO", "FORTIFICADO",
    "ACELERADO", "ENFRAQUECIDO", "EXAUSTO",
]
MANOBRAS = ["DERRUBAR", "EMPURRAR", "AGARRAR", "MOVER", "ARREMESSAR", "IMOBILIZAR", "PROVOCAR"]
EFEITOS = CONDICOES + MANOBRAS


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

ATRIBUTOS = ["brutalidade", "rapidez", "vitalidade", "influencia", "sintonia", "astucia"]

# Raridades possíveis de um FAMILIAR (fonte da verdade — o schema importa daqui).
RARIDADES = ["COMUM", "INCOMUM", "RARO", "LENDÁRIO"]

# Pesos do sorteio de RARIDADE (mesma ordem de RARIDADES): raridades altas são
# mais raras. COMUM 50% · INCOMUM 30% · RARO 15% · LENDÁRIO 5%.
RARIDADE_PESOS = [50, 30, 15, 5]


def raridade_aleatoria(_rng: random.Random | None = None) -> str:
    """Sorteia uma RARIDADE (ponderada) quando o usuário não a informa.

    Raridades mais altas são proporcionalmente mais raras (ver RARIDADE_PESOS).
    `_rng` permite testes determinísticos.
    """
    rng: random.Random = _rng or random.SystemRandom()  # type: ignore[assignment]
    return rng.choices(RARIDADES, weights=RARIDADE_PESOS, k=1)[0]


# Padrões para detectar uma RARIDADE mencionada no texto do conceito.
# Ordem importa: termos mais específicos primeiro (INCOMUM antes de COMUM).
_RARIDADE_PADROES = [
    (re.compile(r"lend[áa]ri", re.IGNORECASE), "LENDÁRIO"),
    (re.compile(r"incomum|incomuns", re.IGNORECASE), "INCOMUM"),
    (re.compile(r"\brar[oíi]ssim|\brar[oa]s?\b", re.IGNORECASE), "RARO"),
    (re.compile(r"\bcomum\b|\bcomuns\b", re.IGNORECASE), "COMUM"),
]


def raridade_no_conceito(conceito: str) -> str | None:
    """Detecta uma RARIDADE citada no conceito (ex.: 'bicho raro' → 'RARO').

    Retorna a raridade encontrada ou None se o conceito não mencionar nenhuma.
    """
    texto = conceito or ""
    for padrao, raridade in _RARIDADE_PADROES:
        if padrao.search(texto):
            return raridade
    return None

# Lista canônica de PERÍCIAS (fonte: Perícias.txt + as citadas em Escolas.txt).
# É a fonte da verdade — o schema do conjurador importa daqui.
PERICIAS = [
    # 19 perícias oficiais de Perícias.txt
    "EQUILÍBRIO", "POTÊNCIA", "OFÍCIOS", "DOMESTICAÇÃO", "ERUDIÇÃO",
    "MALANDRAGEM", "PERSUASÃO", "ENGANAÇÃO", "RESILIÊNCIA", "INICIATIVA",
    "AMEAÇA", "COMBATE", "MEDICINA", "CONJURAÇÃO", "SENTIDOS",
    "ESQUIVA", "CRENÇA", "SOBREVIVÊNCIA", "VONTADE",
    # Citadas como perícias nos pools das escolas (Escolas.txt)
    "CRIME", "TECNOLOGIA", "DIPLOMACIA", "ASTÚCIA", "INFLUÊNCIA",
]

# Pool de perícias de cada ESCOLA e quantas são escolhidas dele (o "x/6").
# Fonte: Escolas.txt. A quantidade total de perícias do conjurador é
#   ESCOLA(escolhas) + ASTÚCIA + 2   (ver Stats.txt e Conjurador_Exemplo.txt).
ESCOLAS_PERICIAS: dict[str, tuple[list[str], int]] = {
    "DESTEMIDO":   (["POTÊNCIA", "INICIATIVA", "COMBATE", "RESILIÊNCIA", "EQUILÍBRIO", "AMEAÇA"], 2),
    "CANALIZADOR": (["CONJURAÇÃO", "SENTIDOS", "CRENÇA", "ASTÚCIA", "VONTADE", "DIPLOMACIA"], 2),
    "INABALAVEL":  (["POTÊNCIA", "RESILIÊNCIA", "COMBATE", "CRENÇA", "VONTADE", "AMEAÇA"], 2),
    "OPORTUNISTA": (["CRIME", "EQUILÍBRIO", "INICIATIVA", "SENTIDOS", "ENGANAÇÃO", "ESQUIVA"], 2),
    "CALCULISTA":  (["TECNOLOGIA", "ASTÚCIA", "OFÍCIOS", "SENTIDOS", "INICIATIVA", "COMBATE"], 3),
    "FACILITADOR": (["DIPLOMACIA", "CONJURAÇÃO", "ENGANAÇÃO", "CRENÇA", "INFLUÊNCIA", "VONTADE"], 3),
}


def rolar(quantidade: int, lados: int, _rng: random.Random | None = None) -> list[int]:
    """Rola `quantidade` dados de `lados` lados. Aceita `_rng` para testes determinísticos."""
    rng: random.Random = _rng or random.SystemRandom()  # type: ignore[assignment]
    return [rng.randint(1, lados) for _ in range(quantidade)]


def calcular_vida(nivel: int, vitalidade: int, _rng: random.Random | None = None) -> int:
    """VIDA = 8 + (NÍVEL × VITALIDADE) + soma de NÍVEL rolagens de 1d6."""
    dados = rolar(nivel, 6, _rng)
    return 8 + (nivel * vitalidade) + sum(dados)


def calcular_conexao(nivel: int, sintonia: int, _rng: random.Random | None = None) -> int:
    """CONEXÃO = 4 + (NÍVEL × SINTONIA) + soma de NÍVEL rolagens de 1d4."""
    dados = rolar(nivel, 4, _rng)
    return 4 + (nivel * sintonia) + sum(dados)


def validar_atributos(atributos: dict[str, int]) -> tuple[bool, str]:
    """
    Valida os atributos do conjurador conforme as regras:
    - Valores de 0 a 3 cada
    - No máximo um atributo zerado
    - Soma obrigatoriamente igual a 10
    Retorna (True, "") se válido, ou (False, mensagem_de_erro).
    """
    valores = [atributos.get(a, 0) for a in ATRIBUTOS]

    for nome, val in zip(ATRIBUTOS, valores):
        if not isinstance(val, int) or not (0 <= val <= 3):
            return False, f"Atributo '{nome}' = {val!r} fora do intervalo [0, 3]"

    zeros = sum(1 for v in valores if v == 0)
    if zeros > 1:
        return False, f"{zeros} atributos zerados; no máximo um é permitido"

    total = sum(valores)
    if total != 10:
        return False, f"Soma dos atributos = {total}; deve ser exatamente 10"

    return True, ""


def corrigir_atributos(atributos: dict[str, int]) -> dict[str, int]:
    """
    Corrige atributos inválidos retornados pelo LLM para satisfazer as regras.
    Trunça valores fora do intervalo, elimina zeros extras e ajusta a soma para 10.
    """
    corrigido = {a: max(0, min(3, int(atributos.get(a, 1)))) for a in ATRIBUTOS}

    # Garante no máximo um zero (mantém o primeiro encontrado)
    zeros = [a for a in ATRIBUTOS if corrigido[a] == 0]
    for a in zeros[1:]:
        corrigido[a] = 1

    zero_attr = next((a for a in ATRIBUTOS if corrigido[a] == 0), None)

    # Aumenta atributos não-máximos até soma = 10
    for a in ATRIBUTOS:
        if sum(corrigido.values()) >= 10:
            break
        espaco = 3 - corrigido[a]
        add = min(espaco, 10 - sum(corrigido.values()))
        corrigido[a] += add

    # Diminui atributos não-mínimos até soma = 10
    for a in reversed(ATRIBUTOS):
        if sum(corrigido.values()) <= 10:
            break
        if a == zero_attr:
            continue  # Não toca no atributo intencionalmente zerado
        remove = min(corrigido[a] - 1, sum(corrigido.values()) - 10)
        corrigido[a] -= remove

    return corrigido


def contar_pericias(escola: str, astucia: int) -> int:
    """Número de perícias de um conjurador = ESCOLA(escolhas) + ASTÚCIA + 2."""
    escola_u = escola.upper() if isinstance(escola, str) else ""
    _, escolhas = ESCOLAS_PERICIAS.get(escola_u, ([], 2))
    return escolhas + max(0, int(astucia)) + 2


def ajustar_pericias(escola: str, astucia: int, pericias) -> list[str]:
    """
    Ajusta a lista de perícias para conter exatamente o número correto pela regra
    ESCOLA + ASTÚCIA + 2. Mantém as perícias válidas fornecidas (sem duplicar) e,
    se faltarem, preenche primeiro com o pool da ESCOLA e depois com as demais.
    """
    escola_u = escola.upper() if isinstance(escola, str) else ""
    pool, _ = ESCOLAS_PERICIAS.get(escola_u, ([], 2))
    alvo = contar_pericias(escola_u, astucia)

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
