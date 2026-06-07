# Biblioteca persistente de CONJURAÇÕES geradas.
#
# Toda conjuração gerada entra aqui (a "lista de habilidades disponíveis").
# Criações que possuem habilidades (familiar, relíquia) selecionam suas
# habilidades a partir desta lista — e, quando ela é insuficiente, geram o
# que faltar (o novo também é adicionado aqui).
#
# Usa apenas a stdlib (json, pathlib, os). O caminho do arquivo pode ser
# sobrescrito pela variável de ambiente RPG_BIBLIOTECA (útil em testes).
import json
import os
import pathlib

_RAIZ = pathlib.Path(__file__).parent.parent.resolve()


def caminho() -> pathlib.Path:
    """Caminho do arquivo JSON da biblioteca (configurável via RPG_BIBLIOTECA)."""
    env = os.environ.get("RPG_BIBLIOTECA")
    return pathlib.Path(env) if env else _RAIZ / "biblioteca" / "conjuracoes.json"


def normalizar(nome: str) -> str:
    """Normaliza um nome para comparação (espaços colapsados, minúsculo)."""
    return " ".join(str(nome).split()).strip().lower()


def carregar() -> list[dict]:
    """Lê todas as conjurações da biblioteca. Retorna [] se não existir/inválida."""
    arq = caminho()
    if not arq.exists():
        return []
    try:
        dados = json.loads(arq.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return dados if isinstance(dados, list) else []


def _salvar(conjuracoes: list[dict]) -> None:
    arq = caminho()
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(
        json.dumps(conjuracoes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def adicionar(conjuracao: dict) -> bool:
    """
    Adiciona uma conjuração à biblioteca se ainda não existir (comparando o
    nome normalizado). Retorna True se adicionou, False se já existia ou se
    não tem nome.
    """
    if not isinstance(conjuracao, dict):
        return False
    nome = conjuracao.get("nome", "")
    if not nome:
        return False

    conjuracoes = carregar()
    existentes = {normalizar(c.get("nome", "")) for c in conjuracoes}
    if normalizar(nome) in existentes:
        return False

    conjuracoes.append(conjuracao)
    _salvar(conjuracoes)
    return True


def salvar_lista(conjuracoes: list[dict]) -> None:
    """Persiste a lista completa (usado pela edição/exclusão manual na GUI)."""
    _salvar(list(conjuracoes))


def nomes() -> list[str]:
    """Nomes de todas as conjurações disponíveis na biblioteca."""
    return [c.get("nome", "") for c in carregar() if c.get("nome")]


def selecionar(quantidade: int, matriz: str | None = None, estrito: bool = False) -> list[dict]:
    """
    Seleciona até `quantidade` conjurações da biblioteca.

    Com `matriz` informada, prioriza as da mesma matriz. Se `estrito=True`,
    retorna SOMENTE as da mesma matriz (modo híbrido — quem chama gera o
    restante temático). Retorna lista de dicts (pode ter menos que pedido).
    """
    if quantidade <= 0:
        return []
    conjuracoes = carregar()
    matriz_u = (matriz or "").strip().upper()
    if matriz_u:
        preferidas = [c for c in conjuracoes if str(c.get("matriz", "")).upper() == matriz_u]
        if estrito:
            ordenadas = preferidas
        else:
            outras = [c for c in conjuracoes if str(c.get("matriz", "")).upper() != matriz_u]
            ordenadas = preferidas + outras
    else:
        ordenadas = list(conjuracoes)
    return ordenadas[:quantidade]
