# Testes da biblioteca persistente de conjurações (sem Ollama).
from engine import biblioteca


def _isolar(tmp_path, monkeypatch):
    """Aponta a biblioteca para um arquivo temporário isolado."""
    monkeypatch.setenv("RPG_BIBLIOTECA", str(tmp_path / "conjuracoes.json"))


def test_carregar_vazia_quando_nao_existe(tmp_path, monkeypatch):
    _isolar(tmp_path, monkeypatch)
    assert biblioteca.carregar() == []
    assert biblioteca.nomes() == []


def test_adicionar_persiste_e_evita_duplicatas(tmp_path, monkeypatch):
    _isolar(tmp_path, monkeypatch)

    assert biblioteca.adicionar({"nome": "Garras de Granito", "matriz": "SÓLIDO"}) is True
    # Mesmo nome com espaços/maiúsculas diferentes → considerado duplicata
    assert biblioteca.adicionar({"nome": "  garras   de  granito ", "matriz": "SÓLIDO"}) is False
    assert biblioteca.adicionar({"nome": "Brasas Espirais", "matriz": "INCÊNDIO"}) is True

    assert biblioteca.nomes() == ["Garras de Granito", "Brasas Espirais"]


def test_adicionar_ignora_sem_nome(tmp_path, monkeypatch):
    _isolar(tmp_path, monkeypatch)
    assert biblioteca.adicionar({"matriz": "MENTAL"}) is False
    assert biblioteca.adicionar({"nome": ""}) is False
    assert biblioteca.adicionar("não é dict") is False
    assert biblioteca.carregar() == []


def test_selecionar_prioriza_matriz(tmp_path, monkeypatch):
    _isolar(tmp_path, monkeypatch)
    biblioteca.adicionar({"nome": "A", "matriz": "INCÊNDIO"})
    biblioteca.adicionar({"nome": "B", "matriz": "SÓLIDO"})
    biblioteca.adicionar({"nome": "C", "matriz": "SÓLIDO"})

    sel = biblioteca.selecionar(2, matriz="SÓLIDO")
    assert [c["nome"] for c in sel] == ["B", "C"]


def test_selecionar_completa_com_outras_matrizes(tmp_path, monkeypatch):
    _isolar(tmp_path, monkeypatch)
    biblioteca.adicionar({"nome": "A", "matriz": "INCÊNDIO"})
    biblioteca.adicionar({"nome": "B", "matriz": "SÓLIDO"})

    sel = biblioteca.selecionar(2, matriz="SÓLIDO")
    nomes = [c["nome"] for c in sel]
    assert nomes[0] == "B"          # preferida primeiro
    assert set(nomes) == {"A", "B"} # completa com a outra matriz


def test_selecionar_limita_ao_disponivel(tmp_path, monkeypatch):
    _isolar(tmp_path, monkeypatch)
    biblioteca.adicionar({"nome": "A", "matriz": "INCÊNDIO"})
    assert len(biblioteca.selecionar(5, matriz="INCÊNDIO")) == 1
    assert biblioteca.selecionar(0) == []


def test_lote_grava_uma_vez_no_fim(tmp_path, monkeypatch):
    _isolar(tmp_path, monkeypatch)
    arq = tmp_path / "conjuracoes.json"

    with biblioteca.lote():
        biblioteca.adicionar({"nome": "A", "matriz": "SÓLIDO"})
        biblioteca.adicionar({"nome": "B", "matriz": "SÓLIDO"})
        # Dentro do lote, leituras já enxergam o acumulado…
        assert biblioteca.nomes() == ["A", "B"]
        # …mas nada foi gravado em disco ainda.
        assert not arq.exists()

    # Ao sair, o arquivo é gravado de uma só vez com tudo.
    assert arq.exists()
    assert biblioteca.nomes() == ["A", "B"]


def test_lote_deduplica_em_memoria(tmp_path, monkeypatch):
    _isolar(tmp_path, monkeypatch)
    biblioteca.adicionar({"nome": "A", "matriz": "SÓLIDO"})  # já no disco

    with biblioteca.lote():
        assert biblioteca.adicionar({"nome": "  a ", "matriz": "SÓLIDO"}) is False  # dup do disco
        assert biblioteca.adicionar({"nome": "B", "matriz": "SÓLIDO"}) is True
        assert biblioteca.adicionar({"nome": "b", "matriz": "SÓLIDO"}) is False     # dup do lote

    assert biblioteca.nomes() == ["A", "B"]


def test_lote_grava_parcial_em_excecao(tmp_path, monkeypatch):
    _isolar(tmp_path, monkeypatch)
    try:
        with biblioteca.lote():
            biblioteca.adicionar({"nome": "A", "matriz": "SÓLIDO"})
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    # O que foi acumulado antes da exceção é preservado.
    assert biblioteca.nomes() == ["A"]


def test_lote_reentrante_so_grava_no_externo(tmp_path, monkeypatch):
    _isolar(tmp_path, monkeypatch)
    arq = tmp_path / "conjuracoes.json"

    with biblioteca.lote():
        biblioteca.adicionar({"nome": "A", "matriz": "SÓLIDO"})
        with biblioteca.lote():           # aninhado — delega ao externo
            biblioteca.adicionar({"nome": "B", "matriz": "SÓLIDO"})
        assert not arq.exists()           # lote interno NÃO grava

    assert biblioteca.nomes() == ["A", "B"]


# ── Coleções por tipo (classe Colecao) ───────────────────────────────────────

def test_colecao_isola_por_arquivo(tmp_path, monkeypatch):
    # RPG_BIBLIOTECA_DIR direciona TODAS as coleções (sem env próprio) ao tmp.
    monkeypatch.setenv("RPG_BIBLIOTECA_DIR", str(tmp_path))

    assert biblioteca.CONJURADORES.adicionar({"nome": "Lyra", "escola": "DESTEMIDO"}) is True
    assert biblioteca.FAMILIARES.adicionar({"nome": "Lobo de Pedra", "raridade": "RARO"}) is True

    # Cada coleção no seu próprio arquivo, sem interferência mútua.
    assert (tmp_path / "conjuradores.json").exists()
    assert (tmp_path / "familiares.json").exists()
    assert biblioteca.CONJURADORES.nomes() == ["Lyra"]
    assert biblioteca.FAMILIARES.nomes() == ["Lobo de Pedra"]


def test_colecao_dedup_e_salvar_lista(tmp_path, monkeypatch):
    monkeypatch.setenv("RPG_BIBLIOTECA_DIR", str(tmp_path))
    col = biblioteca.RELIQUIAS

    assert col.adicionar({"nome": "Égide", "matriz": "SÓLIDO"}) is True
    assert col.adicionar({"nome": " égide ", "matriz": "SÓLIDO"}) is False  # dup normalizada

    itens = col.carregar()
    itens[0]["matriz"] = "INCÊNDIO"
    col.salvar_lista(itens)
    assert col.carregar()[0]["matriz"] == "INCÊNDIO"


def test_colecao_lote_independente(tmp_path, monkeypatch):
    monkeypatch.setenv("RPG_BIBLIOTECA_DIR", str(tmp_path))
    arq = tmp_path / "conjuradores.json"

    with biblioteca.CONJURADORES.lote():
        biblioteca.CONJURADORES.adicionar({"nome": "A"})
        biblioteca.CONJURADORES.adicionar({"nome": "B"})
        assert not arq.exists()                       # grava só no fim
        # lote de uma coleção não afeta outra
        assert biblioteca.FAMILIARES.adicionar({"nome": "C"}) is True

    assert biblioteca.CONJURADORES.nomes() == ["A", "B"]
    assert biblioteca.FAMILIARES.nomes() == ["C"]
