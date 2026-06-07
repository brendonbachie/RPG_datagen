# JSON Schemas para saída estruturada via Ollama.
# Cada schema é passado no campo "format" da chamada à API.

# PERÍCIAS, RARIDADES, MATRIZES e EFEITOS vêm de regras.py (fonte única).
from engine.regras import EFEITOS, MATRIZES, PERICIAS, RARIDADES

SUBMATRIZES = ["ONDA", "FÚRIA", "ESPORO", "TEMPERATURA", "ESPIRAL", "NENHUMA"]

ESCOLAS = ["DESTEMIDO", "CANALIZADOR", "INABALAVEL", "OPORTUNISTA", "CALCULISTA", "FACILITADOR"]

NUCLEOS = ["IMPACTO", "CANALIZAÇÃO", "DEFERIMENTO"]

VETORES = ["BRUTALIDADE", "RAPIDEZ", "VITALIDADE", "INFLUÊNCIA", "SINTONIA", "ASTÚCIA"]

ALCANCES = ["CURTO", "MÉDIO", "LONGO", "EXTREMO"]

AREAS = ["INDIVIDUAL", "LINHA", "CONE", "CÍRCULO", "ZONA"]

TIPOS_DANO = ["PERFURAÇÃO", "CORTE", "IMPACTO", "MATRIZ"]

NIVEIS_RELIQUIA = ["USUAL", "CERIMONIAL", "CATACLISMA"]

_DADO_DANO_SCHEMA = {
    "type": "object",
    "required": ["x", "y"],
    "properties": {
        "x": {"type": "integer", "minimum": 1, "maximum": 6},
        "y": {"type": "integer", "enum": [4, 6, 8, 10, 12, 20]},
    },
}

SCHEMA_CONJURADOR = {
    "type": "object",
    "required": ["nome", "nivel", "idade", "escola", "atributos", "pericias", "historia", "aparencia"],
    "properties": {
        "nome":     {"type": "string"},
        "nivel":    {"type": "integer", "minimum": 1, "maximum": 10},
        "idade":    {"type": "string"},
        "escola":   {"type": "string", "enum": ESCOLAS},
        "atributos": {
            "type": "object",
            "required": ["brutalidade", "rapidez", "vitalidade", "influencia", "sintonia", "astucia"],
            "properties": {
                "brutalidade": {"type": "integer", "minimum": 0, "maximum": 3},
                "rapidez":     {"type": "integer", "minimum": 0, "maximum": 3},
                "vitalidade":  {"type": "integer", "minimum": 0, "maximum": 3},
                "influencia":  {"type": "integer", "minimum": 0, "maximum": 3},
                "sintonia":    {"type": "integer", "minimum": 0, "maximum": 3},
                "astucia":     {"type": "integer", "minimum": 0, "maximum": 3},
            },
        },
        "pericias":  {
            "type": "array",
            "items": {"type": "string", "enum": PERICIAS},
            "minItems": 1,
        },
        "historia":  {"type": "string"},
        "aparencia": {"type": "string"},
    },
}

SCHEMA_RELIQUIA = {
    "type": "object",
    "required": [
        "nome", "descricao",
        "familiar_nome", "familiar_descricao", "familiar_comportamento",
        "matriz", "submatriz", "forma", "nucleo", "vetor",
        "nivel", "alcance", "area", "tipos_dano", "dado_dano", "mult_critico",
        "conjuracoes",
    ],
    "properties": {
        "nome":                   {"type": "string"},
        "descricao":              {"type": "string"},
        "familiar_nome":          {"type": "string"},
        "familiar_descricao":     {"type": "string"},
        "familiar_comportamento": {"type": "string"},
        "matriz":                 {"type": "string", "enum": MATRIZES},
        "submatriz":              {"type": "string", "enum": SUBMATRIZES},
        "forma":                  {"type": "string"},
        "nucleo":                 {"type": "string", "enum": NUCLEOS},
        "vetor":                  {"type": "string", "enum": VETORES},
        "nivel":                  {"type": "string", "enum": NIVEIS_RELIQUIA},
        "alcance":                {"type": "string", "enum": ALCANCES},
        "area":                   {"type": "string", "enum": AREAS},
        "tipos_dano":             {
            "type": "array",
            "items": {"type": "string", "enum": TIPOS_DANO},
            "minItems": 1,
        },
        "dado_dano":              _DADO_DANO_SCHEMA,
        "mult_critico":           {"type": "integer", "minimum": 2, "maximum": 4},
        "conjuracoes":            {"type": "array", "items": {"type": "string"}},
    },
}

SCHEMA_CONJURACAO = {
    "type": "object",
    "required": [
        "nome", "descricao", "matriz", "submatriz", "nivel",
        "alcance", "area", "conexao_custo", "conexao_ganho",
        "tem_dano", "dado_dano", "efeitos",
    ],
    "properties": {
        "nome":           {"type": "string"},
        # minLength evita descrição vazia ou eco do conceito.
        "descricao":      {"type": "string", "minLength": 80},
        "matriz":         {"type": "string", "enum": MATRIZES},
        "submatriz":      {"type": "string", "enum": SUBMATRIZES},
        "nivel":          {"type": "integer", "minimum": 0, "maximum": 3},
        "alcance":        {"type": "string", "enum": ALCANCES},
        "area":           {"type": "string", "enum": AREAS},
        "conexao_custo":  {"type": "integer", "minimum": 0},
        "conexao_ganho":  {"type": "integer", "minimum": 0},
        # tem_dano=false → dado_dano pode ser ignorado (conjuração utilitária)
        "tem_dano":       {"type": "boolean"},
        "dado_dano":      _DADO_DANO_SCHEMA,
        # efeitos: SOMENTE condições (IMOBILIZADO, CAÍDO…) e/ou manobras
        # (EMPURRAR, DERRUBAR…) — restrito por enum para não vazar texto livre.
        "efeitos":        {"type": "array", "items": {"type": "string", "enum": EFEITOS}},
    },
}

SCHEMA_FAMILIAR = {
    "type": "object",
    "required": ["nome", "descricao", "comportamento", "matriz", "submatriz", "habilidades", "raridade"],
    "properties": {
        "nome":          {"type": "string"},
        # minLength incentiva descrições substanciais (evita 'O Lobo da Noite').
        "descricao":     {"type": "string", "minLength": 120},
        "comportamento": {"type": "string", "minLength": 120},
        "matriz":        {"type": "string", "enum": MATRIZES},
        "submatriz":     {"type": "string", "enum": SUBMATRIZES},
        "habilidades":   {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "raridade":      {"type": "string", "enum": RARIDADES},
    },
}

SCHEMAS: dict[str, dict] = {
    "conjurador": SCHEMA_CONJURADOR,
    "reliquia":   SCHEMA_RELIQUIA,
    "conjuracao": SCHEMA_CONJURACAO,
    "familiar":   SCHEMA_FAMILIAR,
}
