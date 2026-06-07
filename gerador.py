#!/usr/bin/env python3
"""
Gerador de conteúdo para o Sistema das Relíquias (RPG de mesa).

Uso:
    python gerador.py conjurador "um espadachim de matriz incêndio"
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
    corrigir_atributos,
    matriz_no_conceito,
    raridade_aleatoria,
    raridade_no_conceito,
    validar_atributos,
)
from engine.regras import RARIDADES
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


def _resolver_habilidades(
    quantidade: int,
    matriz: str,
    conceito: str,
    modelo: str | None,
    url: str | None,
) -> list[dict]:
    """
    Resolve as habilidades de uma criação a partir da biblioteca de conjurações.

    Modo HÍBRIDO: reaproveita apenas conjurações da MESMA matriz e, para o que
    faltar, gera novas conjurações temáticas (coerentes com a matriz) — cada
    uma também é adicionada à biblioteca por `gerar_conjuracao`.
    Retorna a lista de conjurações (dicts) escolhidas.
    """
    quantidade = max(0, quantidade)
    selecionadas = biblioteca.selecionar(quantidade, matriz, estrito=True)
    usados = {biblioteca.normalizar(c.get("nome", "")) for c in selecionadas}

    tentativas = 0
    while len(selecionadas) < quantidade and tentativas < quantidade + 3:
        tentativas += 1
        # Tema enxuto: remove a instrução ('Crie um familiar, baseado em…') e
        # qualifativos ('deve ser raro'), deixando só a essência criativa.
        tema = re.sub(
            r"^\s*(crie|gere|fa[çc]a)\s+(um|uma)\s+\w+\s*,?\s*(basead[oa]\s+em\s+|com\s+base\s+em\s+|sobre\s+)?",
            "", conceito, flags=re.IGNORECASE,
        )
        tema = re.sub(r",?\s*(deve ser|sendo|que (é|seja))\b.*$", "", tema, flags=re.IGNORECASE).strip()
        conceito_conj = f"conjuração temática inspirada em {tema or conceito}"
        nova = gerar_conjuracao(conceito_conj, modelo, url, matriz=matriz or None)
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


def _esqueleto_conjuracao(nome: str, matriz: str) -> dict:
    """Conjuração com apenas o NOME (e a matriz herdada); o resto em branco,
    para o usuário preencher depois na aba Biblioteca da GUI."""
    return {
        "nome": nome,
        "descricao": "",
        "matriz": matriz or "",
        "submatriz": "NENHUMA",
        "nivel": 0,
        "alcance": "",
        "area": "",
        "tem_dano": False,
        "dado_dano": {"x": 1, "y": 6},
        "conexao_custo": 0,
        "conexao_ganho": 0,
        "efeitos": [],
    }


# ─── Geradores ────────────────────────────────────────────────────────────────

def gerar_conjurador(
    conceito: str,
    nivel: int = 1,
    modelo: str | None = None,
    url: str | None = None,
) -> dict:
    """Gera um conjurador e calcula VIDA e CONEXÃO deterministicamente."""
    system = _system_prompt("conjurador")
    user = (
        f"Crie um CONJURADOR com o seguinte conceito: '{conceito}'\n"
        f"Nível: {nivel}\n\n"
        "Regras obrigatórias para os atributos:\n"
        "• Os 6 atributos (brutalidade, rapidez, vitalidade, influencia, sintonia, astucia) "
        "começam em 1 e você distribui +4 pontos extras (total sempre = 10), máximo 3 por atributo.\n"
        "• Opcionalmente pode zerar UM atributo (reduzindo de 1 para 0) para ganhar +1 ponto extra "
        "(total 5 a distribuir, soma final ainda = 10).\n"
        "• NÃO inclua os campos 'vida' nem 'conexao' — eles são calculados pelo sistema.\n"
        "• Escolha a escola coerente com o conceito. As perícias devem fazer sentido com a escola "
        "(cada escola tem um conjunto próprio) e com o conceito — a quantidade exata é ajustada "
        "pelo sistema.\n"
    )

    resultado = chamar_ollama(system, user, SCHEMAS["conjurador"], modelo, url)

    # Nível é entrada do usuário — força o valor pedido (não depende do LLM)
    resultado["nivel"] = nivel

    # Validação e correção determinística dos atributos
    attrs = resultado.get("atributos", {})
    valido, motivo = validar_atributos(attrs)
    if not valido:
        resultado["atributos"] = corrigir_atributos(attrs)
        resultado["_aviso"] = f"Atributos corrigidos automaticamente: {motivo}"

    # Ajuste determinístico da quantidade de perícias: ESCOLA + ASTÚCIA + 2
    astucia = resultado["atributos"].get("astucia", 1)
    escola = resultado.get("escola", "")
    resultado["pericias"] = ajustar_pericias(escola, astucia, resultado.get("pericias", []))

    # Cálculo determinístico (rola dados em código, não pelo LLM)
    vit = resultado["atributos"].get("vitalidade", 1)
    sint = resultado["atributos"].get("sintonia", 1)
    resultado["vida"] = calcular_vida(nivel, vit)
    resultado["conexao"] = calcular_conexao(nivel, sint)

    return resultado


def gerar_reliquia(
    conceito: str,
    modelo: str | None = None,
    url: str | None = None,
) -> dict:
    """Gera uma relíquia com seu familiar de origem."""
    system = _system_prompt("relíquia")
    user = (
        f"Crie uma RELÍQUIA com o seguinte conceito: '{conceito}'\n\n"
        "Inclua o FAMILIAR de origem (a criatura que deu origem ao núcleo da relíquia). "
        "Escolha todos os parâmetros mecânicos de acordo com as regras do sistema.\n\n"
        "Sobre o campo 'conjuracoes': liste de 1 a 3 NOMES PRÓPRIOS de conjurações "
        "(técnicas/golpes) inventados, coerentes com a matriz e o conceito — por exemplo "
        "'Garras de Granito' ou 'Investida do Tigre'.\n"
        "NUNCA use termos de sistema como nomes de conjuração (ex.: IMPACTO, CANALIZAÇÃO, "
        "DEFERIMENTO, INCÊNDIO, ONDA) — esses são tipos de núcleo, matriz ou submatriz, "
        "não conjurações.\n"
    )
    resultado = chamar_ollama(system, user, SCHEMAS["reliquia"], modelo, url)

    # Matriz citada no conceito tem prioridade sobre a escolha do LLM.
    _forcar_matriz(resultado, conceito)

    # As conjurações da relíquia são habilidades reais (modo híbrido):
    # reusa as da mesma matriz e gera o restante coerente quando faltam.
    qtd = max(1, min(3, len(resultado.get("conjuracoes") or [])))
    conjs = _resolver_habilidades(qtd, resultado.get("matriz", ""), conceito, modelo, url)
    # Guarda as conjurações COMPLETAS (com dano, custo, efeitos) na relíquia.
    resultado["conjuracoes"] = conjs

    return resultado


def gerar_conjuracao(
    conceito: str,
    modelo: str | None = None,
    url: str | None = None,
    matriz: str | None = None,
) -> dict:
    """Gera uma conjuração seguindo os 9 passos das regras.

    Se `matriz` for informada, força-a (usado pelo modo híbrido de habilidades).
    """
    system = _system_prompt("conjuração")
    user = (
        f"Crie uma CONJURAÇÃO com o seguinte conceito: '{conceito}'\n\n"
        "Siga os 9 passos de criação de conjurações descritos nas regras.\n"
        "Se a conjuração não causar dano (utilitária), defina tem_dano=false "
        "e dado_dano com valores quaisquer (serão ignorados).\n"
        "O campo 'nome' deve ser um NOME PRÓPRIO curto e evocativo da técnica "
        "(ex.: 'Garras de Granito', 'Vigília da Raposa', 'Manto Espiral') — "
        "NUNCA comece com a palavra 'Conjuração' e NUNCA use termos de sistema "
        "(matriz, núcleo, submatriz) no nome.\n"
        "O campo 'efeitos' aceita APENAS condições e manobras das regras "
        "(ex.: IMOBILIZADO, CAÍDO, EMPURRAR, DERRUBAR). Se a técnica não impõe "
        "nenhuma condição/manobra, deixe 'efeitos' como lista vazia [].\n"
        "O campo 'descricao' deve narrar COMO a conjuração se manifesta no mundo "
        "(cores, formas, som, movimento), em 1 a 2 frases vívidas. NUNCA repita o "
        "conceito recebido nem o nome da conjuração; descreva a cena, não a instrução.\n"
    )
    resultado = chamar_ollama(system, user, SCHEMAS["conjuracao"], modelo, url)

    # Matriz: parâmetro explícito tem prioridade; senão, a citada no conceito.
    if matriz:
        resultado["matriz"] = matriz
    else:
        _forcar_matriz(resultado, conceito)

    # Toda conjuração gerada entra na lista de habilidades disponíveis.
    biblioteca.adicionar(resultado)

    return resultado


def gerar_familiar(
    conceito: str,
    modelo: str | None = None,
    url: str | None = None,
    raridade: str | None = None,
) -> dict:
    """Gera um familiar selvagem (também serve como base para monstros).

    A RARIDADE é definida pelo sistema (nunca pelo LLM), nesta ordem de
    prioridade: valor informado pelo usuário → raridade citada no conceito
    (ex.: 'bicho raro') → sorteio ponderado.
    """
    system = _system_prompt("familiar")
    user = (
        f"Crie um FAMILIAR com o seguinte conceito: '{conceito}'\n\n"
        "Um FAMILIAR é uma criatura rara cuja existência foi transformada pela influência de uma "
        "MATRIZ. Se o conceito indicar uma matriz específica, USE EXATAMENTE essa matriz.\n"
        "Escreva com riqueza de detalhes (NÃO responda com uma palavra ou um título):\n"
        "• 'descricao' = APARÊNCIA física vívida, com pelo menos 2 ou 3 frases.\n"
        "• 'comportamento' = instintos, hábitos e como age em combate, pelo menos 2 ou 3 frases.\n"
        "• 'habilidades' = de 1 a 3 NOMES PRÓPRIOS curtos de técnicas/golpes "
        "(ex.: 'Vigília da Raposa', 'Salto Sombrio') — APENAS os nomes; os detalhes "
        "mecânicos serão definidos depois.\n"
        "Mantenha o nome e as descrições coerentes com o conceito (ex.: se é uma raposa, "
        "descreva uma raposa — não a troque por outro animal).\n"
    )
    resultado = chamar_ollama(system, user, SCHEMAS["familiar"], modelo, url)

    # Matriz citada no conceito tem prioridade sobre a escolha do LLM.
    _forcar_matriz(resultado, conceito)

    # Raridade: usuário > citada no conceito ('bicho raro' → RARO) > sorteio.
    resultado["raridade"] = raridade or raridade_no_conceito(conceito) or raridade_aleatoria()

    # Habilidades: apenas os NOMES (vindos do LLM). Cada uma vira um ESQUELETO
    # de conjuração na biblioteca (matriz herdada, resto em branco) para o
    # usuário preencher na GUI. Não gera mecânica automaticamente.
    matriz = resultado.get("matriz", "")
    nomes: list[str] = []
    for h in (resultado.get("habilidades") or []):
        nome = str(h).strip()
        if nome and nome not in nomes:
            nomes.append(nome)
    nomes = nomes[:3]
    for nome in nomes:
        biblioteca.adicionar(_esqueleto_conjuracao(nome, matriz))
    resultado["habilidades"] = nomes

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
  python gerador.py conjurador "ladra sombria" --nivel 3
  python gerador.py reliquia   "machado de gelo de um urso glacial"
  python gerador.py conjuracao "raio espiral da tempestade"
  python gerador.py familiar   "serpente feita de sombras"
  python gerador.py familiar   "lobo de pedra" --modelo llama3:8b
        """,
    )
    parser.add_argument(
        "tipo",
        choices=list(_GERADORES.keys()),
        help="Tipo de entidade a gerar",
    )
    parser.add_argument("conceito", help="Descrição ou conceito da entidade")
    parser.add_argument(
        "--nivel", type=int, default=1, metavar="N",
        help="Nível do conjurador — apenas para o subcomando 'conjurador' (padrão: 1)",
    )
    parser.add_argument(
        "--raridade", default=None, choices=RARIDADES, metavar="RARIDADE",
        help="Raridade do familiar — apenas para 'familiar'. Se omitido, é sorteada.",
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
            resultado = gerar_conjurador(args.conceito, args.nivel, args.modelo, args.url)
        elif args.tipo == "familiar":
            resultado = gerar_familiar(args.conceito, args.modelo, args.url, args.raridade)
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
