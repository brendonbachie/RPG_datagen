# JSON Schemas para saída estruturada via Ollama.
# Cada schema é passado no campo "format" da chamada à API.
# Espelham os schemas oficiais de regras/Schemas/ (RPG_scheema).

# Enums e ranges vêm de regras.py (fonte única).
from engine.regras import (
    COBERTURAS,
    ESCOLAS,
    GASTOS_ACAO,
    GRAU_MAX,
    GRAU_MIN,
    HABITOS,
    MATRIZES,
    PERICIAS,
    PORTES,
    SOCIALIZACOES,
    SUBMATRIZES,
    TEMPERAMENTOS,
)

NUCLEOS = ["IMPACTO", "CANALIZAÇÃO", "DEFERIMENTO"]

# Alcance: o schema oficial usa apenas estas quatro faixas.
ALCANCES = ["CURTO", "MÉDIO", "LONGO", "EXTREMO"]

# Área de ação da CONJURAÇÃO (Schema_Conjuracao.md): ALVO em vez de INDIVIDUAL.
AREAS = ["ALVO", "LINHA", "CONE", "CÍRCULO", "ZONA"]

# Nível da relíquia (Schema_Reliquia.md): CATACLISMO (não "CATACLISMA").
NIVEIS_RELIQUIA = ["USUAL", "CERIMONIAL", "CATACLISMO"]

_DADO_DANO_SCHEMA = {
    "type": "object",
    "required": ["x", "y"],
    "properties": {
        "x": {"type": "integer", "minimum": 1, "maximum": 6},
        "y": {"type": "integer", "enum": [4, 6, 8, 10, 12, 20]},
    },
}

# ─── Conjurador ───────────────────────────────────────────────────────────────
# VIDA e CONEXÃO (atual/máxima) são calculadas em código e injetadas depois —
# não entram no schema para o LLM não "chutar" os valores.
SCHEMA_CONJURADOR = {
    "type": "object",
    "required": [
        "nome", "idade", "grau_ressonancia", "escola",
        "atributos", "pericias", "ecos", "reliquias",
        "historia", "aparencia",
    ],
    "properties": {
        "nome":             {"type": "string"},
        "idade":            {"type": "integer", "minimum": 0},
        "grau_ressonancia": {"type": "integer", "minimum": GRAU_MIN, "maximum": GRAU_MAX},
        "escola":           {"type": "string", "enum": ESCOLAS},
        "atributos": {
            "type": "object",
            "required": ["brutalidade", "rapidez", "vitalidade", "influencia", "sintonia", "astucia"],
            "properties": {
                "brutalidade": {"type": "integer", "minimum": 0, "maximum": 6},
                "rapidez":     {"type": "integer", "minimum": 0, "maximum": 6},
                "vitalidade":  {"type": "integer", "minimum": 0, "maximum": 6},
                "influencia":  {"type": "integer", "minimum": 0, "maximum": 6},
                "sintonia":    {"type": "integer", "minimum": 0, "maximum": 6},
                "astucia":     {"type": "integer", "minimum": 0, "maximum": 6},
            },
        },
        "pericias": {
            "type": "array",
            "items": {"type": "string", "enum": PERICIAS},
            "minItems": 1,
        },
        # ECOS: nomes próprios das habilidades passivas (a quantidade exata é
        # ajustada pelo sistema conforme o grau).
        "ecos": {"type": "array", "items": {"type": "string"}},
        # RELÍQUIAS vinculadas ao conjurador (nomes próprios; ao menos uma).
        "reliquias": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "historia":  {"type": "string"},
        "aparencia": {"type": "string"},
    },
}

# ─── Relíquia ─────────────────────────────────────────────────────────────────
# Esquema enxuto (Schema_Reliquia.md): sem familiar embutido, vetor, forma,
# área, tipos de dano ou multiplicador de crítico. As conjurações iniciais
# (6: três de custo 0 e três de custo 1) são resolvidas em código.
SCHEMA_RELIQUIA = {
    "type": "object",
    "required": [
        "nome", "descricao", "matriz", "submatriz",
        "nucleo", "nivel", "alcance", "dado_dano", "conjuracoes",
    ],
    "properties": {
        "nome":        {"type": "string"},
        "descricao":   {"type": "string", "minLength": 80},
        "matriz":      {"type": "string", "enum": MATRIZES},
        "submatriz":   {"type": "string", "enum": SUBMATRIZES},
        "nucleo":      {"type": "string", "enum": NUCLEOS},
        "nivel":       {"type": "string", "enum": NIVEIS_RELIQUIA},
        "alcance":     {"type": "string", "enum": ALCANCES},
        "dado_dano":   _DADO_DANO_SCHEMA,
        "conjuracoes": {"type": "array", "items": {"type": "string"}},
    },
}

# ─── Conjuração ───────────────────────────────────────────────────────────────
SCHEMA_CONJURACAO = {
    "type": "object",
    "required": [
        "nome", "descricao", "matriz", "submatriz",
        "custo", "ganho_conexao", "gasto_acao",
        "alcance", "area", "tem_dano", "dado_dano", "efeitos",
    ],
    "properties": {
        "nome":          {"type": "string"},
        # minLength evita descrição vazia ou eco do conceito.
        "descricao":     {"type": "string", "minLength": 80},
        "matriz":        {"type": "string", "enum": MATRIZES},
        "submatriz":     {"type": "string", "enum": SUBMATRIZES},
        "custo":         {"type": "integer", "minimum": 0},
        "ganho_conexao": {"type": "integer", "minimum": 0},
        "gasto_acao":    {"type": "string", "enum": GASTOS_ACAO},
        "alcance":       {"type": "string", "enum": ALCANCES},
        "area":          {"type": "string", "enum": AREAS},
        # tem_dano=false → dado_dano é ignorado (conjuração utilitária / DANO 0).
        "tem_dano":      {"type": "boolean"},
        "dado_dano":     _DADO_DANO_SCHEMA,
        # efeitos: condições, manobras OU efeitos personalizados (texto livre).
        "efeitos":       {"type": "array", "items": {"type": "string"}},
    },
}

# ─── Familiar ─────────────────────────────────────────────────────────────────
SCHEMA_FAMILIAR = {
    "type": "object",
    "required": [
        "nome", "especie_base", "matriz", "submatriz",
        "patamar", "nivel_ameaca",
        "porte", "cobertura", "coloracao", "caracteristicas_matriz",
        "temperamento", "habito", "socializacao",
        "bioma", "regiao",
        "habilidades_fisicas", "habilidades_matriz",
        "descricao",
    ],
    "properties": {
        "nome":          {"type": "string"},
        "especie_base":  {"type": "string"},
        "matriz":        {"type": "string", "enum": MATRIZES},
        "submatriz":     {"type": "string", "enum": SUBMATRIZES},
        "patamar":       {"type": "integer", "minimum": 1},
        "nivel_ameaca":  {"type": "integer", "minimum": 1, "maximum": 10},
        "porte":         {"type": "string", "enum": PORTES},
        "cobertura":     {"type": "string", "enum": COBERTURAS},
        "coloracao":     {"type": "string"},
        "caracteristicas_matriz": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "temperamento":  {"type": "string", "enum": TEMPERAMENTOS},
        "habito":        {"type": "string", "enum": HABITOS},
        "socializacao":  {"type": "string", "enum": SOCIALIZACOES},
        "bioma":         {"type": "string"},
        "regiao":        {"type": "string"},
        # Habilidades físicas (CONJURAÇÕES da matriz NEUTRA) e habilidades de
        # MATRIZ (CONJURAÇÕES da matriz do familiar) — apenas os nomes; os
        # detalhes mecânicos são resolvidos pela biblioteca.
        "habilidades_fisicas": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "habilidades_matriz":  {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "descricao":     {"type": "string", "minLength": 120},
    },
}

SCHEMAS: dict[str, dict] = {
    "conjurador": SCHEMA_CONJURADOR,
    "reliquia":   SCHEMA_RELIQUIA,
    "conjuracao": SCHEMA_CONJURACAO,
    "familiar":   SCHEMA_FAMILIAR,
}
