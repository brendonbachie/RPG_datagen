"""
Testes para as regras determinísticas do Sistema das Relíquias.
NÃO dependem do Ollama — usam seeds fixos para reprodutibilidade.
Alinhados ao repositório RPG_scheema (grau de ressonância 1-30, novas fórmulas).
"""
import random

import pytest

from engine.regras import (
    ATRIBUTOS,
    ESCOLAS_PERICIAS,
    GRAU_MAX,
    PERICIAS,
    ajustar_pericias,
    calcular_conexao,
    calcular_vida,
    clampar_grau,
    contar_pericias,
    corrigir_atributos,
    matriz_no_conceito,
    rolar,
    soma_atributos,
    total_ecos,
    total_pericias,
    validar_atributos,
)


@pytest.mark.parametrize("conceito,esperado", [
    ("uma raposa da matriz guardião, deve ser um bicho raro", "GUARDIÃO"),
    ("guardiao sem acento também", "GUARDIÃO"),
    ("um espadachim de matriz incêndio", "INCÊNDIO"),
    ("criatura mental e enigmática", "MENTAL"),
    ("uma serpente feita de sombras", None),   # 'sombras' não é nome de matriz
])
def test_matriz_no_conceito(conceito, esperado):
    assert matriz_no_conceito(conceito) == esperado


# ─── Progressão de grau ──────────────────────────────────────────────────────

class TestClamparGrau:
    def test_limites(self):
        assert clampar_grau(0) == 1
        assert clampar_grau(1) == 1
        assert clampar_grau(30) == 30
        assert clampar_grau(99) == GRAU_MAX
        assert clampar_grau("abc") == 1  # entrada inválida → mínimo


class TestSomaAtributos:
    @pytest.mark.parametrize("grau,esperado", [
        (1, 10), (5, 10), (6, 11), (11, 11), (12, 12),
        (18, 13), (24, 14), (30, 15),
    ])
    def test_marcos(self, grau, esperado):
        assert soma_atributos(grau) == esperado


class TestTotalPericias:
    @pytest.mark.parametrize("grau,esperado", [
        (1, 3), (4, 3), (5, 4), (9, 4), (10, 5),
        (15, 6), (20, 7), (25, 8), (30, 9),
    ])
    def test_marcos(self, grau, esperado):
        assert total_pericias(grau) == esperado


class TestTotalEcos:
    @pytest.mark.parametrize("grau,esperado", [
        (1, 1), (4, 1), (5, 2), (10, 3), (15, 4), (20, 5), (25, 6), (30, 7),
    ])
    def test_marcos(self, grau, esperado):
        assert total_ecos(grau) == esperado

    def test_nunca_passa_de_sete(self):
        for g in range(1, 31):
            assert total_ecos(g) <= 7


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

    def test_seed_determinista(self):
        r1 = rolar(5, 10, random.Random(99))
        r2 = rolar(5, 10, random.Random(99))
        assert r1 == r2

    def test_seeds_diferentes_produzem_resultados_diferentes(self):
        r1 = rolar(10, 6, random.Random(1))
        r2 = rolar(10, 6, random.Random(2))
        assert r1 != r2


# ─── calcular_vida ─────────────────────────────────────────────────────────────
# VIDA MÁXIMA = 8 + (GRAU × VITALIDADE) + soma de GRAU rolagens de 1d6.

class TestCalcularVida:
    def _dado_esperado(self, seed: int, n: int) -> int:
        return sum(rolar(n, 6, random.Random(seed)))

    def test_formula_grau1_vit2(self):
        seed = 100
        dado = self._dado_esperado(seed, 1)
        vida = calcular_vida(1, 2, random.Random(seed))
        assert vida == 8 + (1 * 2) + dado

    def test_formula_grau3_vit3(self):
        seed = 7
        dado = self._dado_esperado(seed, 3)
        vida = calcular_vida(3, 3, random.Random(seed))
        assert vida == 8 + (3 * 3) + dado

    def test_grau1_vit0_intervalo(self):
        """VIDA com vitalidade 0 e grau 1: 8 + 0 + 1d6 ∈ [9, 14]."""
        for seed in range(20):
            vida = calcular_vida(1, 0, random.Random(seed))
            assert 9 <= vida <= 14, f"seed={seed}: vida={vida}"

    def test_minimo_teorico(self):
        """Mínimo teórico (grau 1, vit 0, 1d6=1) = 9; range do repo começa em 12+
        a partir de vit típica, mas a fórmula nunca cai abaixo de 9."""
        for seed in range(20):
            assert calcular_vida(1, 0, random.Random(seed)) >= 9


# ─── calcular_conexao ──────────────────────────────────────────────────────────
# CONEXÃO MÁXIMA = GRAU + (SINTONIA × 2) + 1d4 (um único d4).

class TestCalcularConexao:
    def _d4(self, seed: int) -> int:
        return rolar(1, 4, random.Random(seed))[0]

    def test_formula_grau1_sint3(self):
        seed = 10
        d4 = self._d4(seed)
        conexao = calcular_conexao(1, 3, random.Random(seed))
        assert conexao == 1 + (3 * 2) + d4

    def test_formula_grau3_sint2(self):
        seed = 5
        d4 = self._d4(seed)
        conexao = calcular_conexao(3, 2, random.Random(seed))
        assert conexao == 3 + (2 * 2) + d4

    def test_minimo_grau1_sint0(self):
        """Mínimo absoluto: 1 + 0 + 1 = 2 (1d4 mínimo é 1) — Conexao.md."""
        for seed in range(20):
            c = calcular_conexao(1, 0, random.Random(seed))
            assert c >= 2, f"seed={seed}: conexao={c}"

    def test_maximo_grau30_sint6(self):
        """Máximo aproximado (Conexao.md): 30 + 12 + 4 = 46."""
        for seed in range(20):
            c = calcular_conexao(30, 6, random.Random(seed))
            assert 30 + 12 + 1 <= c <= 46


# ─── validar_atributos ─────────────────────────────────────────────────────────

class TestValidarAtributos:
    def _attrs(self, **kw):
        base = {a: 1 for a in ATRIBUTOS}
        base.update(kw)
        return base

    def test_valido_exemplo_ficha(self):
        """bru=2,rap=1,vit=3,inf=1,sin=2,ast=1 → soma=10 (grau 1)."""
        ok, msg = validar_atributos(
            {"brutalidade": 2, "rapidez": 1, "vitalidade": 3,
             "influencia": 1, "sintonia": 2, "astucia": 1}
        )
        assert ok, msg

    def test_soma_errada_falha(self):
        # 3+3+3+1+1+1 = 12 ≠ 10 (no grau 1)
        ok, msg = validar_atributos(
            {"brutalidade": 3, "rapidez": 3, "vitalidade": 3,
             "influencia": 1, "sintonia": 1, "astucia": 1}
        )
        assert not ok
        assert "12" in msg

    def test_soma_12_valida_no_grau_12(self):
        """A mesma soma 12 é VÁLIDA quando o grau exige soma 12."""
        ok, msg = validar_atributos(
            {"brutalidade": 3, "rapidez": 3, "vitalidade": 3,
             "influencia": 1, "sintonia": 1, "astucia": 1},
            grau=12,
        )
        assert ok, msg

    def test_valor_acima_do_maximo_absoluto_falha(self):
        ok, msg = validar_atributos(self._attrs(brutalidade=7))
        assert not ok
        assert "brutalidade" in msg

    def test_valor_seis_dentro_do_range(self):
        """6 é o teto absoluto — não falha por range (falha só na soma, se houver)."""
        ok, msg = validar_atributos(
            {"brutalidade": 6, "rapidez": 6, "vitalidade": 1,
             "influencia": 1, "sintonia": 1, "astucia": 0},
            grau=30,  # soma alvo 15
        )
        assert ok, msg

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
        ok, msg = validar_atributos(
            {"brutalidade": 0, "rapidez": 2, "vitalidade": 3,
             "influencia": 2, "sintonia": 2, "astucia": 1}
        )
        assert ok, msg

    def test_todos_um_invalido_no_grau1(self):
        """Distribuição padrão sem ponto extra: soma = 6 ≠ 10."""
        ok, _ = validar_atributos({a: 1 for a in ATRIBUTOS})
        assert not ok


# ─── corrigir_atributos ────────────────────────────────────────────────────────

class TestCorrigirAtributos:
    def _valido_apos_correcao(self, attrs: dict, grau: int = 1) -> None:
        corrigido = corrigir_atributos(attrs, grau)
        ok, msg = validar_atributos(corrigido, grau)
        assert ok, f"Ainda inválido após correção: {msg}\nOriginal: {attrs}\nCorrigido: {corrigido}"

    def test_todos_max(self):
        self._valido_apos_correcao({a: 6 for a in ATRIBUTOS})

    def test_todos_um(self):
        self._valido_apos_correcao({a: 1 for a in ATRIBUTOS})

    def test_valor_negativo(self):
        attrs = {"brutalidade": -1, "rapidez": 3, "vitalidade": 3,
                 "influencia": 2, "sintonia": 2, "astucia": 1}
        self._valido_apos_correcao(attrs)

    def test_dois_zeros_corrigidos(self):
        attrs = {"brutalidade": 0, "rapidez": 0, "vitalidade": 3,
                 "influencia": 3, "sintonia": 3, "astucia": 3}
        corrigido = corrigir_atributos(attrs)
        zeros = sum(1 for v in corrigido.values() if v == 0)
        assert zeros <= 1

    def test_resultado_sempre_valido_grau1(self):
        casos = [
            {a: i for a, i in zip(ATRIBUTOS, [0, 0, 3, 3, 3, 3])},
            {a: i for a, i in zip(ATRIBUTOS, [3, 2, 1, 2, 1, 3])},
            {a: i for a, i in zip(ATRIBUTOS, [1, 1, 1, 1, 1, 4])},
            {a: 0 for a in ATRIBUTOS},
        ]
        for caso in casos:
            self._valido_apos_correcao(caso)

    def test_resultado_valido_em_varios_graus(self):
        attrs = {a: 1 for a in ATRIBUTOS}
        for grau in (1, 6, 12, 18, 24, 30):
            self._valido_apos_correcao(attrs, grau)


# ─── contar_pericias / ajustar_pericias ─────────────────────────────────────────

class TestContarPericias:
    def test_grau1(self):
        assert contar_pericias(1) == 3

    def test_marco_grau5(self):
        assert contar_pericias(5) == 4

    def test_grau_maximo(self):
        assert contar_pericias(30) == 9


class TestAjustarPericias:
    def test_quantidade_exata_grau1(self):
        out = ajustar_pericias("INABALÁVEL", 1, ["COMBATE", "RESILIÊNCIA"])
        assert len(out) == 3

    def test_apara_excesso_mantendo_validas(self):
        muitas = ["COMBATE", "POTÊNCIA", "AMEAÇA", "CRENÇA", "VONTADE", "SENTIDOS"]
        out = ajustar_pericias("INABALÁVEL", 1, muitas)
        assert len(out) == 3
        assert out == muitas[:3]

    def test_preenche_faltantes_com_pool(self):
        out = ajustar_pericias("DESTEMIDO", 1, ["COMBATE"])
        assert len(out) == 3
        assert "COMBATE" in out
        pool = ESCOLAS_PERICIAS["DESTEMIDO"][0]
        assert all(p in pool for p in out)

    def test_ignora_invalidas(self):
        out = ajustar_pericias("INABALÁVEL", 1, ["INVENTADA", "XPTO", "COMBATE"])
        assert len(out) == 3
        assert "INVENTADA" not in out
        assert all(p in PERICIAS for p in out)

    def test_sem_duplicatas(self):
        out = ajustar_pericias("INABALÁVEL", 5, ["COMBATE", "COMBATE", "combate"])
        assert len(out) == len(set(out))

    def test_lista_vazia_preenche_tudo(self):
        out = ajustar_pericias("CALCULISTA", 10, [])
        assert len(out) == 5  # total_pericias(10)
        assert all(p in PERICIAS for p in out)

    def test_todos_os_pools_sao_pericias_validas(self):
        for escola, (pool, _) in ESCOLAS_PERICIAS.items():
            for p in pool:
                assert p in PERICIAS, f"{p} (pool de {escola}) não está em PERICIAS"
