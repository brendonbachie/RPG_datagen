# Biblioteca persistente das entidades geradas.
#
# Cada TIPO gerado (conjurador, relíquia, conjuração, familiar) tem sua própria
# coleção — um arquivo JSON em `biblioteca/<tipo>.json`. Toda entidade gerada
# entra na coleção do seu tipo (a "lista de itens criados").
#
# As CONJURAÇÕES têm um papel extra: são a "lista de habilidades disponíveis".
# Criações com habilidades (familiar, relíquia) selecionam suas habilidades a
# partir dessa coleção (ver `selecionar`) e geram o que faltar.
#
# Usa apenas a stdlib (json, pathlib, os, threading, contextlib).
# Caminhos configuráveis em testes:
#   • RPG_BIBLIOTECA      → caminho completo do arquivo de CONJURAÇÕES (legado).
#   • RPG_BIBLIOTECA_DIR  → diretório base de TODAS as coleções.
import contextlib
import json
import os
import pathlib
import threading

_RAIZ = pathlib.Path(__file__).parent.parent.resolve()


def normalizar(nome: str) -> str:
    """Normaliza um nome para comparação (espaços colapsados, minúsculo)."""
    return " ".join(str(nome).split()).strip().lower()


class Colecao:
    """Coleção persistente de entidades (um arquivo JSON, dedup por nome).

    Cada instância tem seu próprio estado de LOTE (por thread): dentro de um
    `with col.lote():`, `adicionar` acumula em memória e o arquivo é gravado
    UMA única vez ao sair — troca a geração em massa de O(n²) (read+rewrite por
    item) por um único O(n) no fim.
    """

    def __init__(self, arquivo: str, env: str | None = None) -> None:
        self._arquivo = arquivo          # nome do arquivo (ex.: "familiares.json")
        self._env = env                  # var de ambiente p/ caminho completo (legado)
        self._lote = threading.local()   # estado de lote isolado por thread
        self._mutex = threading.Lock()   # serializa read-modify-write entre threads

    # ── Caminho ─────────────────────────────────────────────────────────────
    def caminho(self) -> pathlib.Path:
        """Caminho do arquivo JSON desta coleção.

        Prioridade: env de caminho completo (se houver) → RPG_BIBLIOTECA_DIR →
        diretório padrão `biblioteca/` na raiz do projeto.
        """
        if self._env:
            valor = os.environ.get(self._env)
            if valor:
                return pathlib.Path(valor)
        base = os.environ.get("RPG_BIBLIOTECA_DIR")
        raiz = pathlib.Path(base) if base else _RAIZ / "biblioteca"
        return raiz / self._arquivo

    # ── Lote ────────────────────────────────────────────────────────────────
    def _lote_ativo(self) -> bool:
        return getattr(self._lote, "ativo", False)

    @contextlib.contextmanager
    def lote(self):
        """Acumula adições em memória e grava o arquivo UMA vez ao sair.

            with col.lote():
                for ...:
                    col.adicionar(item)

        Reentrante: um `lote()` aninhado delega ao externo (flush só no mais
        externo). Em caso de exceção, o que já foi acumulado ainda é gravado.
        """
        if self._lote_ativo():          # já dentro de um lote — apenas delega
            yield
            return

        self._lote.lista = self.carregar()
        self._lote.existentes = {normalizar(c.get("nome", "")) for c in self._lote.lista}
        self._lote.sujo = False
        self._lote.ativo = True
        try:
            yield
        finally:
            sujo, lista = self._lote.sujo, self._lote.lista
            self._lote.ativo = False
            self._lote.lista = []
            self._lote.existentes = set()
            if sujo:
                with self._mutex:
                    self._salvar(lista)

    # ── Leitura ─────────────────────────────────────────────────────────────
    def carregar(self) -> list[dict]:
        """Lê todas as entidades da coleção. Retorna [] se não existir/inválida.

        Durante um `with lote()`, devolve uma cópia do estado acumulado em
        memória (inclui o que ainda não foi gravado), para que leituras e
        deduplicação fiquem consistentes dentro do lote.
        """
        if self._lote_ativo():
            return list(self._lote.lista)
        arq = self.caminho()
        if not arq.exists():
            return []
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return dados if isinstance(dados, list) else []

    def nomes(self) -> list[str]:
        """Nomes de todas as entidades da coleção."""
        return [c.get("nome", "") for c in self.carregar() if c.get("nome")]

    # ── Escrita ─────────────────────────────────────────────────────────────
    def _salvar(self, itens: list[dict]) -> None:
        arq = self.caminho()
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(
            json.dumps(itens, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def adicionar(self, entidade: dict) -> bool:
        """Adiciona à coleção se ainda não existir (compara o nome normalizado).

        Retorna True se adicionou, False se já existia ou se não tem nome.
        """
        if not isinstance(entidade, dict):
            return False
        nome = entidade.get("nome", "")
        if not nome:
            return False
        chave = normalizar(nome)

        # Modo LOTE: dedup via set em memória e append sem gravar (flush no fim).
        if self._lote_ativo():
            if chave in self._lote.existentes:
                return False
            self._lote.lista.append(entidade)
            self._lote.existentes.add(chave)
            self._lote.sujo = True
            return True

        with self._mutex:
            itens = self.carregar()
            existentes = {normalizar(c.get("nome", "")) for c in itens}
            if chave in existentes:
                return False

            itens.append(entidade)
            self._salvar(itens)
            return True

    def salvar_lista(self, itens: list[dict]) -> None:
        """Persiste a lista completa (usado pela edição/exclusão manual na GUI)."""
        with self._mutex:
            self._salvar(list(itens))

    # ── Específico de conjurações (habilidades) ──────────────────────────────
    def selecionar(self, quantidade: int, matriz: str | None = None, estrito: bool = False) -> list[dict]:
        """Seleciona até `quantidade` entidades, priorizando a mesma `matriz`.

        Se `estrito=True`, retorna SOMENTE as da mesma matriz (modo híbrido —
        quem chama gera o restante temático). Pode retornar menos que o pedido.
        """
        if quantidade <= 0:
            return []
        itens = self.carregar()
        matriz_u = (matriz or "").strip().upper()
        if matriz_u:
            preferidas = [c for c in itens if str(c.get("matriz", "")).upper() == matriz_u]
            if estrito:
                ordenadas = preferidas
            else:
                outras = [c for c in itens if str(c.get("matriz", "")).upper() != matriz_u]
                ordenadas = preferidas + outras
        else:
            ordenadas = list(itens)
        return ordenadas[:quantidade]


# ── Coleções por tipo ───────────────────────────────────────────────────────
# CONJURACOES honra RPG_BIBLIOTECA (caminho completo) para compatibilidade com
# os testes/instalações existentes.
CONJURACOES  = Colecao("conjuracoes.json", env="RPG_BIBLIOTECA")
CONJURADORES = Colecao("conjuradores.json")
RELIQUIAS    = Colecao("reliquias.json")
FAMILIARES   = Colecao("familiares.json")


# ── API de módulo (compatibilidade) ──────────────────────────────────────────
# Mantida para os call sites existentes (gerador.py, GUI, testes), que operam
# sobre as CONJURAÇÕES — a coleção com papel de "lista de habilidades".
def caminho() -> pathlib.Path:
    return CONJURACOES.caminho()


def carregar() -> list[dict]:
    return CONJURACOES.carregar()


def adicionar(conjuracao: dict) -> bool:
    return CONJURACOES.adicionar(conjuracao)


def salvar_lista(conjuracoes: list[dict]) -> None:
    CONJURACOES.salvar_lista(conjuracoes)


def nomes() -> list[str]:
    return CONJURACOES.nomes()


def lote():
    return CONJURACOES.lote()


def selecionar(quantidade: int, matriz: str | None = None, estrito: bool = False) -> list[dict]:
    return CONJURACOES.selecionar(quantidade, matriz, estrito)
