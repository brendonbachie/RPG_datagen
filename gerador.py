#!/usr/bin/env python3
"""
Gerador de conteúdo para o Sistema das Relíquias (RPG de mesa).

Uso:
    python gerador.py conjurador "um espadachim de matriz incêndio" --grau 3
    python gerador.py reliquia   "machado de gelo de um urso glacial"
    python gerador.py conjuracao "raio espiral da tempestade"
    python gerador.py familiar   "serpente feita de sombras"
"""
import argparse
import json
import re
import sys

from engine import biblioteca
from engine.loader import carregar_regras
from engine.ollama import ErroOllama, MODELO_PADRAO, chamar_ollama
from engine.regras import (
    ajustar_pericias,
    calcular_conexao,
    calcular_vida,
    clampar_grau,
    corrigir_atributos,
    matriz_no_conceito,
    total_ecos,
    validar_atributos,
)
from engine.schemas import SCHEMAS

# Cache das regras — carregado uma vez por execução
_REGRAS_CACHE: str | None = None


def _regras() -> str:
    global _REGRAS_CACHE
    if _REGRAS_CACHE is None:
        _REGRAS_CACHE = carregar_regras()
    return _REGRAS_CACHE


def _system_prompt(tipo: str) -> str:
    return (
        "Você é um gerador criativo de conteúdo para o RPG de mesa 'Sistema das Relíquias', "
        f"com a função exclusiva de criar {tipo.upper()} válidos segundo as regras do sistema.\n"
        "Responda APENAS com o JSON solicitado — sem explicações, sem texto fora do JSON.\n"
        "Escreva descrições e histórias em português do Brasil.\n"
        "/no_think\n\n"
        "REGRAS COMPLETAS DO SISTEMA (fonte da verdade):\n\n"
        + _regras()
    )


def _custo_conjuracao(c: dict) -> int:
    """Custo de conexão de uma conjuração (aceita o nome novo e o legado)."""
    valor = c.get("custo", c.get("conexao_custo", 0))
    try:
        return int(valor or 0)
    except (TypeError, ValueError):
        return 0


def _resolver_habilidades(
    quantidade: int,
    matriz: str,
    conceito: str,
    modelo: str | None,
    url: str | None,
    custo: int | None = None,
) -> list[dict]:
    """
    Resolve habilidades (conjurações) a partir da biblioteca, modo HÍBRIDO:
    reaproveita conjurações da MESMA matriz (e, se `custo` for dado, do mesmo
    custo) e gera novas conjurações temáticas para o que faltar — cada uma
    também é adicionada à biblioteca por `gerar_conjuracao`.
    """
    quantidade = max(0, quantidade)
    if quantidade == 0:
        return []

    # Todas as conjurações da mesma matriz; filtra por custo quando exigido.
    candidatas = biblioteca.selecionar(10_000, matriz, estrito=True)
    if custo is not None:
        candidatas = [c for c in candidatas if _custo_conjuracao(c) == custo]
    selecionadas = candidatas[:quantidade]
    usados = {biblioteca.normalizar(c.get("nome", "")) for c in selecionadas}

    # Lote: as conjurações geradas abaixo são acumuladas e gravadas de uma só vez.
    with biblioteca.lote():
        tentativas = 0
        while len(selecionadas) < quantidade and tentativas < quantidade + 3:
            tentativas += 1
            tema = re.sub(
                r"^\s*(crie|gere|fa[çc]a)\s+(um|uma)\s+\w+\s*,?\s*(basead[oa]\s+em\s+|com\s+base\s+em\s+|sobre\s+)?",
                "", conceito, flags=re.IGNORECASE,
            )
            tema = re.sub(r",?\s*(deve ser|sendo|que (é|seja))\b.*$", "", tema, flags=re.IGNORECASE).strip()
            conceito_conj = f"conjuração temática inspirada em {tema or conceito}"
            nova = gerar_conjuracao(conceito_conj, modelo, url, matriz=matriz or None, custo=custo)
            chave = biblioteca.normalizar(nova.get("nome", ""))
            if not chave or chave in usados:
                continue
            usados.add(chave)
            selecionadas.append(nova)

    return selecionadas[:quantidade]


def _forcar_matriz(resultado: dict, conceito: str) -> None:
    """Se o conceito citar uma MATRIZ, força-a (não deixa o LLM divergir)."""
    mat = matriz_no_conceito(conceito)
    if mat:
        resultado["matriz"] = mat


# ─── Preferências do usuário ────────────────────────────────────────────────
# Campos opcionais vindos da GUI: preenchidos guiam o LLM e (quando forçáveis)
# são gravados exatamente no resultado; ausentes deixam o LLM decidir.

# Rótulos amigáveis para o bloco de instrução enviado ao LLM.
_PREF_ROTULOS = {
    "matriz": "matriz", "submatriz": "submatriz",
    "alcance": "alcance", "area": "área", "efeitos": "efeitos",
    "custo": "custo de conexão", "ganho_conexao": "ganho de conexão",
    "gasto_acao": "gasto de ação", "tem_dano": "causa dano",
    "escola": "escola", "idade": "idade", "grau_ressonancia": "grau de ressonância",
    "atributos": "atributos", "pericias": "perícias", "nucleo": "núcleo",
    "nivel": "nível da relíquia", "porte": "porte", "cobertura": "cobertura",
    "coloracao": "coloração", "temperamento": "temperamento", "habito": "hábito",
    "socializacao": "socialização", "bioma": "bioma", "regiao": "região",
    "especie_base": "espécie base",
}

# Campos que, quando informados, são gravados exatamente no resultado (por tipo).
# Os demais (ex.: atributos/perícias do conjurador) entram só como guia no prompt,
# pois são pós-processados pelo motor de regras.
_PREF_FORCAR = {
    "conjuracao": {"matriz", "submatriz", "alcance", "area", "tem_dano",
                   "dado_dano", "custo", "ganho_conexao", "gasto_acao", "efeitos"},
    "conjurador": {"escola", "idade"},
    "reliquia": {"matriz", "submatriz", "nucleo", "nivel", "alcance", "dado_dano"},
    "familiar": {"matriz", "submatriz", "porte", "cobertura", "temperamento",
                 "habito", "socializacao", "especie_base"},
}


def _fmt_pref(chave: str, valor) -> str:
    """Formata um par preferência→texto para o bloco de instrução."""
    if isinstance(valor, (list, tuple)):
        valor = ", ".join(str(v) for v in valor)
    elif isinstance(valor, bool):
        valor = "sim" if valor else "não"
    return f"• {_PREF_ROTULOS.get(chave, chave)}: {valor}"


def _bloco_preferencias(prefs: dict | None) -> str:
    """Bloco de instrução com as preferências preenchidas (vazio se não houver)."""
    if not prefs:
        return ""
    linhas = []
    dx, dy = prefs.get("dado_x"), prefs.get("dado_y")
    if dx is not None or dy is not None:
        linhas.append(f"• dado de dano: {dx if dx is not None else '?'}d{dy if dy is not None else '?'}")
    for chave, valor in prefs.items():
        if chave in ("dado_x", "dado_y"):
            continue
        linhas.append(_fmt_pref(chave, valor))
    return (
        "\n\nPREFERÊNCIAS DO USUÁRIO — use EXATAMENTE estes valores; para os campos "
        "não citados, decida livremente:\n" + "\n".join(linhas) + "\n"
    )


def _forcar_preferencias(resultado: dict, prefs: dict | None, permitidos: set[str]) -> None:
    """Grava no resultado as preferências cujas chaves estão em `permitidos`.

    `dado_x`/`dado_y` montam `dado_dano` (quando 'dado_dano' é permitido). Chaves
    fora de `permitidos` são ignoradas aqui (servem só como guia no prompt).
    """
    if not prefs:
        return
    for chave, valor in prefs.items():
        if chave in ("dado_x", "dado_y"):
            continue
        if chave in permitidos:
            resultado[chave] = valor
    if "dado_dano" in permitidos and ("dado_x" in prefs or "dado_y" in prefs):
        dd = dict(resultado.get("dado_dano") or {})
        if prefs.get("dado_x") is not None:
            dd["x"] = prefs["dado_x"]
        if prefs.get("dado_y") is not None:
            dd["y"] = prefs["dado_y"]
        resultado["dado_dano"] = dd


# ─── Geradores ────────────────────────────────────────────────────────────────

def gerar_conjurador(
    conceito: str,
    grau: int = 1,
    modelo: str | None = None,
    url: str | None = None,
    prefs: dict | None = None,
) -> dict:
    """Gera um conjurador e calcula VIDA e CONEXÃO deterministicamente."""
    grau = clampar_grau(grau)
    system = _system_prompt("conjurador")
    user = (
        f"Crie um CONJURADOR com o seguinte conceito: '{conceito}'\n"
        f"Grau de ressonância: {grau}\n\n"
        "Regras obrigatórias para os atributos (criação + progressão):\n"
        "• Os 6 atributos (brutalidade, rapidez, vitalidade, influencia, sintonia, astucia) "
        "começam em 1 e você distribui pontos extras; o total exato é ajustado pelo sistema "
        "conforme o grau. Cada atributo fica entre 0 e 6.\n"
        "• Opcionalmente pode zerar UM atributo. No máximo um atributo pode ser 0.\n"
        "• NÃO inclua VIDA nem CONEXÃO — são calculados pelo sistema.\n"
        "• Escolha a escola coerente com o conceito. As perícias devem fazer sentido com a "
        "escola e com o conceito — a quantidade exata é ajustada pelo sistema.\n"
        "• 'ecos' = nomes próprios curtos das habilidades passivas adquiridas (a quantidade é "
        "ajustada pelo sistema).\n"
        "• 'reliquias' = ao menos um nome próprio de relíquia vinculada ao conjurador.\n"
    ) + _bloco_preferencias(prefs)

    resultado = chamar_ollama(system, user, SCHEMAS["conjurador"], modelo, url)

    # Grau é entrada do usuário — força o valor pedido (não depende do LLM)
    resultado["grau_ressonancia"] = grau

    # Validação e correção determinística dos atributos (soma alvo pelo grau)
    attrs = resultado.get("atributos", {})
    valido, motivo = validar_atributos(attrs, grau)
    if not valido:
        resultado["atributos"] = corrigir_atributos(attrs, grau)
        resultado["_aviso"] = f"Atributos corrigidos automaticamente: {motivo}"

    # Ajuste determinístico da quantidade de perícias (progressão de grau)
    escola = resultado.get("escola", "")
    resultado["pericias"] = ajustar_pericias(escola, grau, resultado.get("pericias", []))

    # Ecos: quantidade segue a progressão (graus 1/5/10/15/20/25/30, máx 7)
    ecos = [str(e).strip() for e in (resultado.get("ecos") or []) if str(e).strip()]
    resultado["ecos"] = ecos[: total_ecos(grau)]

    # Condições começam vazias (Schema_Conjurador.md)
    resultado["condicoes"] = []

    # Cálculo determinístico (rola dados em código, não pelo LLM)
    vit = resultado["atributos"].get("vitalidade", 1)
    sint = resultado["atributos"].get("sintonia", 1)
    vida_max = calcular_vida(grau, vit)
    con_max = calcular_conexao(grau, sint)
    resultado["vida_maxima"] = vida_max
    resultado["vida_atual"] = vida_max
    resultado["conexao_maxima"] = con_max
    resultado["conexao_atual"] = con_max

    _forcar_preferencias(resultado, prefs, _PREF_FORCAR["conjurador"])
    biblioteca.CONJURADORES.adicionar(resultado)
    return resultado


def gerar_reliquia(
    conceito: str,
    modelo: str | None = None,
    url: str | None = None,
    prefs: dict | None = None,
) -> dict:
    """Gera uma relíquia com suas 6 conjurações iniciais (3 de custo 0, 3 de custo 1)."""
    system = _system_prompt("relíquia")
    user = (
        f"Crie uma RELÍQUIA com o seguinte conceito: '{conceito}'\n\n"
        "Escolha todos os parâmetros mecânicos de acordo com as regras do sistema.\n\n"
        "Sobre o campo 'conjuracoes': liste NOMES PRÓPRIOS de conjurações (técnicas/golpes) "
        "inventados, coerentes com a matriz e o conceito — por exemplo 'Garras de Granito' ou "
        "'Investida do Tigre'. O sistema completará as 6 conjurações iniciais (3 de custo 0 e "
        "3 de custo 1).\n"
        "NUNCA use termos de sistema como nomes de conjuração (ex.: IMPACTO, CANALIZAÇÃO, "
        "DEFERIMENTO, INCÊNDIO, ONDA) — esses são tipos de núcleo, matriz ou submatriz.\n"
    ) + _bloco_preferencias(prefs)
    resultado = chamar_ollama(system, user, SCHEMAS["reliquia"], modelo, url)

    # Matriz citada no conceito tem prioridade sobre a escolha do LLM.
    _forcar_matriz(resultado, conceito)
    # Preferência explícita do usuário vence a matriz do conceito.
    _forcar_preferencias(resultado, prefs, _PREF_FORCAR["reliquia"])

    # 6 conjurações iniciais (modo híbrido): 3 de custo 0 + 3 de custo 1.
    matriz = resultado.get("matriz", "")
    c0 = _resolver_habilidades(3, matriz, conceito, modelo, url, custo=0)
    c1 = _resolver_habilidades(3, matriz, conceito, modelo, url, custo=1)
    resultado["conjuracoes"] = c0 + c1

    biblioteca.RELIQUIAS.adicionar(resultado)
    return resultado


def gerar_conjuracao(
    conceito: str,
    modelo: str | None = None,
    url: str | None = None,
    matriz: str | None = None,
    custo: int | None = None,
    nome_forcado: str | None = None,
    prefs: dict | None = None,
) -> dict:
    """Gera uma conjuração conforme as regras.

    Se `matriz` for informada, força-a; se `custo` for informado, força o custo
    de conexão; se `nome_forcado` for informado, mantém esse nome próprio (usado
    para materializar habilidades nomeadas de familiares).
    """
    system = _system_prompt("conjuração")
    instr_custo = (
        f"O custo de conexão DEVE ser exatamente {custo}.\n" if custo is not None else ""
    )
    user = (
        f"Crie uma CONJURAÇÃO com o seguinte conceito: '{conceito}'\n\n"
        + instr_custo +
        "Se a conjuração não causar dano (utilitária), defina tem_dano=false "
        "e dado_dano com valores quaisquer (serão ignorados).\n"
        "O campo 'nome' deve ser um NOME PRÓPRIO curto e evocativo da técnica "
        "(ex.: 'Garras de Granito', 'Vigília da Raposa', 'Manto Espiral') — "
        "NUNCA comece com a palavra 'Conjuração' e NUNCA use termos de sistema "
        "(matriz, núcleo, submatriz) no nome.\n"
        "O campo 'gasto_acao' deve ser um de: AÇÃO DE LOCOMOÇÃO, AÇÃO COMPLEXA, AÇÃO EXTRA.\n"
        "O campo 'efeitos' aceita condições, manobras das regras (ex.: IMOBILIZADO, CAÍDO, "
        "EMPURRAR) ou efeitos personalizados curtos. Se a técnica não tem efeito mecânico, "
        "deixe 'efeitos' como lista vazia [].\n"
        "O campo 'descricao' deve narrar COMO a conjuração se manifesta no mundo "
        "(cores, formas, som, movimento), em 1 a 2 frases vívidas. NUNCA repita o "
        "conceito recebido nem o nome da conjuração; descreva a cena, não a instrução.\n"
    ) + _bloco_preferencias(prefs)
    resultado = chamar_ollama(system, user, SCHEMAS["conjuracao"], modelo, url)

    # Matriz: parâmetro explícito tem prioridade; senão, a citada no conceito.
    if matriz:
        resultado["matriz"] = matriz
    else:
        _forcar_matriz(resultado, conceito)

    # Custo forçado (modo híbrido) tem prioridade sobre a escolha do LLM.
    if custo is not None:
        resultado["custo"] = int(custo)

    # Nome próprio preservado (ex.: habilidade nomeada de um familiar).
    if nome_forcado:
        resultado["nome"] = nome_forcado

    # Preferências do usuário vencem (matriz, custo, dano, efeitos…).
    _forcar_preferencias(resultado, prefs, _PREF_FORCAR["conjuracao"])

    # Toda conjuração gerada entra na lista de habilidades disponíveis.
    biblioteca.adicionar(resultado)

    return resultado


def gerar_familiar(
    conceito: str,
    modelo: str | None = None,
    url: str | None = None,
    prefs: dict | None = None,
) -> dict:
    """Gera um familiar selvagem (também serve como base para monstros).

    As habilidades têm duas origens (Schema_Familiar.md): habilidades FÍSICAS são
    conjurações da matriz NEUTRA; habilidades de MATRIZ são conjurações da matriz
    do familiar. Aqui geramos apenas os NOMES, virando esqueletos na biblioteca.
    """
    system = _system_prompt("familiar")
    user = (
        f"Crie um FAMILIAR com o seguinte conceito: '{conceito}'\n\n"
        "Um FAMILIAR é uma criatura cuja existência foi transformada pela influência de uma "
        "MATRIZ. Se o conceito indicar uma matriz específica, USE EXATAMENTE essa matriz.\n"
        "Preencha todos os campos com coerência (porte, cobertura, temperamento, hábito, "
        "socialização, bioma, região, coloração e características visíveis da matriz).\n"
        "• 'descricao' = APARÊNCIA e comportamento vívidos: como a matriz alterou a criatura, "
        "como ela age e como se apresenta visualmente (pelo menos 3 ou 4 frases).\n"
        "• 'habilidades_fisicas' = 1+ NOMES de capacidades naturais da espécie "
        "(ex.: 'Mordida', 'Garras', 'Investida').\n"
        "• 'habilidades_matriz' = 1+ NOMES de manifestações sobrenaturais da matriz "
        "(ex.: 'Sopro Glacial', 'Véu de Sombras').\n"
        "Mantenha o nome e as descrições coerentes com o conceito (ex.: se é uma raposa, "
        "descreva uma raposa).\n"
    ) + _bloco_preferencias(prefs)
    resultado = chamar_ollama(system, user, SCHEMAS["familiar"], modelo, url)

    # Matriz citada no conceito tem prioridade sobre a escolha do LLM.
    _forcar_matriz(resultado, conceito)

    # Preferências do usuário vencem (matriz/submatriz/enums descritivos).
    _forcar_preferencias(resultado, prefs, _PREF_FORCAR["familiar"])

    matriz = resultado.get("matriz", "")
    especie = resultado.get("especie_base", "") or "uma criatura"

    def _nomes(campo: str) -> list[str]:
        out: list[str] = []
        for h in (resultado.get(campo) or []):
            nome = str(h).strip()
            if nome and nome not in out:
                out.append(nome)
        return out[:5]

    fisicas = _nomes("habilidades_fisicas")
    de_matriz = _nomes("habilidades_matriz")

    # Cada nome vira uma CONJURAÇÃO COMPLETA na biblioteca (com dano, custo e
    # efeitos coerentes), preservando o nome inventado pelo LLM. Físicas usam a
    # matriz NEUTRA; habilidades de matriz usam a matriz do familiar.
    with biblioteca.lote():
        for nome in fisicas:
            gerar_conjuracao(
                f"{nome}: habilidade física natural de {especie}",
                modelo, url, matriz="NEUTRO", nome_forcado=nome,
            )
        for nome in de_matriz:
            gerar_conjuracao(
                f"{nome}: manifestação sobrenatural da matriz {matriz}",
                modelo, url, matriz=matriz or None, nome_forcado=nome,
            )

    resultado["habilidades_fisicas"] = fisicas
    resultado["habilidades_matriz"] = de_matriz

    biblioteca.FAMILIARES.adicionar(resultado)
    return resultado


# ─── CLI ──────────────────────────────────────────────────────────────────────

_GERADORES = {
    "conjurador": gerar_conjurador,
    "reliquia":   gerar_reliquia,
    "conjuracao": gerar_conjuracao,
    "familiar":   gerar_familiar,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gerador.py",
        description="Gerador de conteúdo para o Sistema das Relíquias",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python gerador.py conjurador "um espadachim de matriz incêndio"
  python gerador.py conjurador "ladra sombria" --grau 3
  python gerador.py reliquia   "machado de gelo de um urso glacial"
  python gerador.py conjuracao "raio espiral da tempestade"
  python gerador.py familiar   "serpente feita de sombras"
        """,
    )
    parser.add_argument(
        "tipo",
        choices=list(_GERADORES.keys()),
        help="Tipo de entidade a gerar",
    )
    parser.add_argument("conceito", help="Descrição ou conceito da entidade")
    parser.add_argument(
        "--grau", "--nivel", type=int, default=1, metavar="N", dest="grau",
        help="Grau de ressonância do conjurador (1-30) — apenas para 'conjurador' (padrão: 1)",
    )
    parser.add_argument(
        "--modelo", default=None, metavar="NOME",
        help=f"Modelo Ollama (padrão: {MODELO_PADRAO} ou $RPG_MODEL)",
    )
    parser.add_argument(
        "--url", default=None, metavar="URL",
        help="URL da API do Ollama (padrão: http://localhost:11434/api/chat ou $RPG_OLLAMA_URL)",
    )
    parser.add_argument(
        "--indent", type=int, default=2,
        help="Indentação do JSON de saída (padrão: 2)",
    )
    args = parser.parse_args()

    try:
        if args.tipo == "conjurador":
            resultado = gerar_conjurador(args.conceito, args.grau, args.modelo, args.url)
        else:
            resultado = _GERADORES[args.tipo](args.conceito, args.modelo, args.url)

        print(json.dumps(resultado, ensure_ascii=False, indent=args.indent))

    except ErroOllama as e:
        print(f"\nERRO DE CONEXÃO COM O OLLAMA:\n{e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrompido.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
