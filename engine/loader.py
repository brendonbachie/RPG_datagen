# Carrega todos os arquivos .txt de regras do repositório e retorna como texto único.
import pathlib

_RAIZ = pathlib.Path(__file__).parent.parent.resolve()

# Pastas que não contêm regras do sistema
_EXCLUIR_DIRS = {"engine", "tests", "repo_clone", ".git", "__pycache__"}

_cache: str | None = None


def carregar_regras() -> str:
    """Lê todos os .txt de regras e retorna texto concatenado (com cache)."""
    global _cache
    if _cache is not None:
        return _cache

    partes: list[str] = []
    for caminho in sorted(_RAIZ.rglob("*.txt")):
        partes_rel = caminho.relative_to(_RAIZ).parts
        # Ignora se algum componente do caminho é uma pasta excluída ou oculta
        if any(p in _EXCLUIR_DIRS or p.startswith(".") for p in partes_rel[:-1]):
            continue
        try:
            texto = caminho.read_text(encoding="utf-8", errors="replace").strip()
            partes.append(f"=== {'/'.join(partes_rel)} ===\n{texto}")
        except Exception:
            pass

    _cache = "\n\n".join(partes)
    return _cache
