# Carrega as regras oficiais do Sistema das Relíquias e retorna como texto único.
#
# Fonte da verdade: o diretório `regras/`, espelho do repositório
# https://github.com/Tody0224/RPG_scheema (definições de termos + schemas).
# Os arquivos .txt antigos de `Mundo/` e da raiz ficaram desatualizados e NÃO
# são mais carregados — as regras vigentes vivem apenas em `regras/`.
import pathlib

_RAIZ = pathlib.Path(__file__).parent.parent.resolve()
_DIR_REGRAS = _RAIZ / "regras"

_cache: str | None = None


def carregar_regras() -> str:
    """Lê todos os .md de `regras/` e retorna o texto concatenado (com cache)."""
    global _cache
    if _cache is not None:
        return _cache

    partes: list[str] = []
    for caminho in sorted(_DIR_REGRAS.rglob("*.md")):
        try:
            texto = caminho.read_text(encoding="utf-8", errors="replace").strip()
            rel = caminho.relative_to(_DIR_REGRAS)
            partes.append(f"=== {rel.as_posix()} ===\n{texto}")
        except Exception:
            pass

    _cache = "\n\n".join(partes)
    return _cache
