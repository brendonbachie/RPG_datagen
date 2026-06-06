"""
Testes para as regras determinísticas do Sistema das Relíquias.
NÃO dependem do Ollama — usam seeds fixos para reprodutibilidade.
"""
import random

import pytest

from engine.regras import (
    ATRIBUTOS,
    ESCOLAS_PERICIAS,
    PERICIAS,
    ajustar_pericias,
    calcular_conexao,
    calcular_vida,
    contar_pericias,
    corrigir_atributos,
    rolar,
    validar_atributos,
)


# ─── rolar ────────────────────────────────────────────────────────────────────

class TestRolar:
    def test_quantidade_correta(self):
        assert len(rolar(3, 6)) == 3
        assert len(rolar(1, 20)) == 1
        assert len(rolar(10, 4)) == 10

    def test_valores_no_intervalo_d6(self):
        rng = random.Random(42)
        for _ in range(200):
            for v in rolar(4, 6, rng):
                assert 1 <= v <= 6

    def test_valores_no_intervalo_d20(self):
        rng = random.Random(0)
        for v in rolar(500, 20, rng):
            assert 1 <= v <= 20

    def test_seed_determinista(self):
        """Mesma seed deve produzir exatamente a mesma sequência."""
        r1 = rolar(5, 10, random.Random(99))
        r2 = rolar(5, 10, random.Random(99))
        assert r1 == r2

    def test_seeds_diferentes_produzem_resultados_diferentes(self):
        r1 = rolar(10, 6, random.Random(1))
        r2 = rolar(10, 6, random.Random(2))
        assert r1 != r2


# ─── calcular_vida ─────────────────────────────────────────────────────────────

class TestCalcularVida:
    def _dado_esperado(self, seed: int, n: int) -> int:
        """Reproduz a rolagem de n d6 com a mesma seed."""
        return sum(rolar(n, 6, random.Random(seed)))

    def test_formula_nivel1_vit2(self):
        seed = 100
        dado = self._dado_esperado(seed, 1)
        vida = calcular_vida(1, 2, random.Random(seed))
        assert vida == 8 + (1 * 2) + dado

    def test_formula_nivel3_vit3(self):
        """Verifica o mesmo cálculo do exemplo na ficha de conjurador do repo."""
        seed = 7
        dado = self._dado_esperado(seed, 3)
        vida = calcular_vida(3, 3, random.Random(seed))
        assert vida == 8 + (3 * 3) + dado

    def test_nivel1_vit0_intervalo(self):
        """VIDA mínima com vitalidade 0 e nível 1: 8 + 0 + 1d6 ∈ [9, 14]."""
        for seed in range(20):
            vida = calcular_vida(1, 0, random.Random(seed))
            assert 9 <= vida <= 14, f"seed={seed}: vida={vida}"

    def test_nivel1_vit3_intervalo(self):
        """VIDA máx por nível com vit=3, nível=1: 8 + 3 + 1d6 ∈ [12, 17]."""
        for seed in range(20):
            vida = calcular_vida(1, 3, random.Random(seed))
            assert 12 <= vida <= 17, f"seed={seed}: vida={vida}"

    def test_nivel_zero_invalido_nao_acontece_em_producao(self):
        """Nível mínimo é 1; testamos que funciona sem crash."""
        vida = calcular_vida(1, 1, random.Random(42))
        assert isinstance(vida, int)
        assert vida >= 10  # 8 + 1 + 1


# ─── calcular_conexao ──────────────────────────────────────────────────────────

class TestCalcularConexao:
    def _dado_esperado(self, seed: int, n: int) -> int:
        return sum(rolar(n, 4, random.Random(seed)))

    def test_formula_nivel1_sint3(self):
        seed = 10
        dado = self._dado_esperado(seed, 1)
        conexao = calcular_conexao(1, 3, random.Random(seed))
        assert conexao == 4 + (1 * 3) + dado

    def test_formula_nivel3_sint2(self):
        seed = 5
        dado = self._dado_esperado(seed, 3)
        conexao = calcular_conexao(3, 2, random.Random(seed))
        assert conexao == 4 + (3 * 2) + dado

    def test_conexao_minima_nivel1_sint0(self):
        """Mínimo absoluto: 4 + 0 + 1 = 5 (1d4 mínimo é 1)."""
        for seed in range(20):
            c = calcular_conexao(1, 0, random.Random(seed))
            assert c >= 5, f"seed={seed}: conexao={c}"


# ─── validar_atributos ─────────────────────────────────────────────────────────

class TestValidarAtributos:
    def _attrs(self, **kw):
        base = {a: 1 for a in ATRIBUTOS}
        base.update(kw)
        return base

    def test_valido_exemplo_ficha(self):
        """Ficha de exemplo: bru=2,rap=1,vit=3,inf=1,sin=2,ast=1 → soma=10."""
        ok, msg = validar_atributos(
            {"brutalidade": 2, "rapidez": 1, "vitalidade": 3,
             "influencia": 1, "sintonia": 2, "astucia": 1}
        )
        assert ok, msg

    def test_soma_errada_falha(self):
        # 3+3+3+1+1+1 = 12 ≠ 10
        ok, msg = validar_atributos(
            {"brutalidade": 3, "rapidez": 3, "vitalidade": 3,
             "influencia": 1, "sintonia": 1, "astucia": 1}
        )
        assert not ok
        assert "12" in msg

    def test_valor_acima_max_falha(self):
        ok, msg = validar_atributos(self._attrs(brutalidade=4))
        assert not ok
        assert "brutalidade" in msg

    def test_valor_negativo_falha(self):
        ok, msg = validar_atributos(self._attrs(rapidez=-1))
        assert not ok

    def test_dois_zeros_falha(self):
        ok, msg = validar_atributos(
            {"brutalidade": 0, "rapidez": 0, "vitalidade": 3,
             "influencia": 3, "sintonia": 2, "astucia": 2}
        )
        assert not ok
        assert "zerado" in msg.lower()

    def test_um_zero_valido(self):
        """Zerando um atributo e distribuindo ponto extra: soma ainda = 10."""
        ok, msg = validar_atributos(
            {"brutalidade": 0, "rapidez": 2, "vitalidade": 3,
             "influencia": 2, "sintonia": 2, "astucia": 1}
        )
        assert ok, msg

    def test_todos_um_invalido(self):
        """Distribuição padrão sem nenhum ponto extra: soma = 6 ≠ 10."""
        ok, _ = validar_atributos({a: 1 for a in ATRIBUTOS})
        assert not ok


# ─── corrigir_atributos ────────────────────────────────────────────────────────

class TestCorrigirAtributos:
    def _valido_apos_correcao(self, attrs: dict) -> None:
        corrigido = corrigir_atributos(attrs)
        ok, msg = validar_atributos(corrigido)
        assert ok, f"Ainda inválido após correção: {msg}\nOriginal: {attrs}\nCorrigido: {corrigido}"

    def test_todos_max(self):
        """Todos em 3 → soma = 18; corrigir deve baixar para 10."""
        self._valido_apos_correcao({a: 3 for a in ATRIBUTOS})

    def test_todos_um(self):
        """Todos em 1 → soma = 6; corrigir deve subir para 10."""
        self._valido_apos_correcao({a: 1 for a in ATRIBUTOS})

    def test_valor_negativo(self):
        """Valor negativo deve ser tratado como 0."""
        attrs = {"brutalidade": -1, "rapidez": 3, "vitalidade": 3,
                 "influencia": 2, "sintonia": 2, "astucia": 1}
        self._valido_apos_correcao(attrs)

    def test_dois_zeros_corrigidos(self):
        attrs = {"brutalidade": 0, "rapidez": 0, "vitalidade": 3,
                 "influencia": 3, "sintonia": 3, "astucia": 3}
        corrigido = corrigir_atributos(attrs)
        zeros = sum(1 for v in corrigido.values() if v == 0)
        assert zeros <= 1

    def test_resultado_sempre_valido(self):
        """Testa combinações variadas — resultado deve sempre ser válido."""
        casos = [
            {a: i for a, i in zip(ATRIBUTOS, [0, 0, 3, 3, 3, 3])},
            {a: i for a, i in zip(ATRIBUTOS, [3, 2, 1, 2, 1, 3])},
            {a: i for a, i in zip(ATRIBUTOS, [1, 1, 1, 1, 1, 4])},
            {a: 0 for a in ATRIBUTOS},
        ]
        for caso in casos:
            self._valido_apos_correcao(caso)


# ─── contar_pericias / ajustar_pericias ─────────────────────────────────────────

class TestContarPericias:
    def test_exemplo_oficial_inabalavel(self):
        """Cara do Capacete: INABALAVEL (2) + ASTÚCIA 1 + 2 = 5 perícias."""
        assert contar_pericias("INABALAVEL", 1) == 5

    def test_escola_tres_escolhas(self):
        """CALCULISTA escolhe 3 do pool: 3 + ASTÚCIA + 2."""
        assert contar_pericias("CALCULISTA", 0) == 5
        assert contar_pericias("CALCULISTA", 3) == 8

    def test_case_insensitive(self):
        assert contar_pericias("destemido", 2) == 6

    def test_escola_desconhecida_usa_padrao(self):
        """Escola inválida assume 2 escolhas."""
        assert contar_pericias("???", 1) == 5


class TestAjustarPericias:
    def test_quantidade_exata(self):
        """A lista final tem exatamente ESCOLA + ASTÚCIA + 2 perícias."""
        out = ajustar_pericias("INABALAVEL", 1, ["COMBATE", "RESILIÊNCIA"])
        assert len(out) == 5

    def test_apara_excesso_mantendo_validas(self):
        """LLM devolveu perícias demais — apara para o alvo, mantendo as primeiras válidas."""
        muitas = ["COMBATE", "POTÊNCIA", "AMEAÇA", "CRENÇA", "VONTADE", "SENTIDOS", "MEDICINA"]
        out = ajustar_pericias("INABALAVEL", 1, muitas)
        assert len(out) == 5
        assert out == muitas[:5]

    def test_preenche_faltantes_com_pool(self):
        """LLM devolveu poucas — completa primeiro com o pool da escola."""
        out = ajustar_pericias("DESTEMIDO", 0, ["COMBATE"])
        assert len(out) == 4  # 2 + 0 + 2
        assert "COMBATE" in out
        pool = ESCOLAS_PERICIAS["DESTEMIDO"][0]
        # As perícias adicionadas para completar vieram do pool da escola
        assert all(p in pool for p in out)

    def test_ignora_invalidas(self):
        """Perícias fora da lista canônica são descartadas e substituídas."""
        out = ajustar_pericias("INABALAVEL", 1, ["INVENTADA", "XPTO", "COMBATE"])
        assert len(out) == 5
        assert "INVENTADA" not in out
        assert all(p in PERICIAS for p in out)

    def test_sem_duplicatas(self):
        out = ajustar_pericias("INABALAVEL", 1, ["COMBATE", "COMBATE", "combate"])
        assert len(out) == len(set(out))

    def test_lista_vazia_preenche_tudo(self):
        out = ajustar_pericias("CALCULISTA", 2, [])
        assert len(out) == 7  # 3 + 2 + 2
        assert all(p in PERICIAS for p in out)

    def test_todos_os_pools_sao_pericias_validas(self):
        """Toda perícia listada nos pools das escolas existe na lista canônica."""
        for escola, (pool, _) in ESCOLAS_PERICIAS.items():
            for p in pool:
                assert p in PERICIAS, f"{p} (pool de {escola}) não está em PERICIAS"
