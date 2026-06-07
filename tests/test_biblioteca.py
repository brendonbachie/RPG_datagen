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
