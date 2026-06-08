# Testes das preferências do usuário (puros — sem Ollama).
from gerador import _PREF_FORCAR, _bloco_preferencias, _forcar_preferencias


def test_bloco_vazio():
    assert _bloco_preferencias(None) == ""
    assert _bloco_preferencias({}) == ""


def test_bloco_lista_valores_e_dado():
    bloco = _bloco_preferencias({
        "matriz": "INCÊNDIO", "custo": 2,
        "dado_x": 2, "dado_y": 8, "tem_dano": True,
        "efeitos": ["IMOBILIZADO", "EMPURRAR"],
    })
    assert "matriz: INCÊNDIO" in bloco
    assert "custo de conexão: 2" in bloco
    assert "2d8" in bloco
    assert "causa dano: sim" in bloco
    assert "IMOBILIZADO, EMPURRAR" in bloco


def test_forcar_grava_so_permitidos():
    res = {"matriz": "ONDA", "custo": 0, "alcance": "CURTO"}
    _forcar_preferencias(res, {"matriz": "INCÊNDIO", "custo": 3},
                         _PREF_FORCAR["conjuracao"])
    assert res["matriz"] == "INCÊNDIO"
    assert res["custo"] == 3
    assert res["alcance"] == "CURTO"  # não foi pedido, mantém


def test_forcar_monta_dado_dano():
    res = {"dado_dano": {"x": 1, "y": 6}}
    _forcar_preferencias(res, {"dado_x": 2, "dado_y": 8}, _PREF_FORCAR["conjuracao"])
    assert res["dado_dano"] == {"x": 2, "y": 8}


def test_forcar_dado_parcial_preserva_outro_eixo():
    res = {"dado_dano": {"x": 3, "y": 12}}
    _forcar_preferencias(res, {"dado_y": 20}, _PREF_FORCAR["reliquia"])
    assert res["dado_dano"] == {"x": 3, "y": 20}


def test_forcar_ignora_fora_da_allowlist():
    # atributos/perícias NÃO são travados no conjurador (só guia no prompt).
    res = {"escola": "DESTEMIDO"}
    _forcar_preferencias(res, {"atributos": "brutalidade 3", "pericias": ["atletismo"],
                              "escola": "CALCULISTA"},
                         _PREF_FORCAR["conjurador"])
    assert res["escola"] == "CALCULISTA"
    assert "atributos" not in res
    assert "pericias" not in res


def test_forcar_none_nao_quebra():
    res = {"nome": "x"}
    _forcar_preferencias(res, None, _PREF_FORCAR["familiar"])
    assert res == {"nome": "x"}
