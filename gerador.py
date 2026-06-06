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
import sys

from engine.loader import carregar_regras
from engine.ollama import ErroOllama, MODELO_PADRAO, chamar_ollama
from engine.regras import (
    ajustar_pericias,
    calcular_conexao,
    calcular_vida,
    corrigir_atributos,
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
    return chamar_ollama(system, user, SCHEMAS["reliquia"], modelo, url)


def gerar_conjuracao(
    conceito: str,
    modelo: str | None = None,
    url: str | None = None,
) -> dict:
    """Gera uma conjuração seguindo os 9 passos das regras."""
    system = _system_prompt("conjuração")
    user = (
        f"Crie uma CONJURAÇÃO com o seguinte conceito: '{conceito}'\n\n"
        "Siga os 9 passos de criação de conjurações descritos nas regras.\n"
        "Se a conjuração não causar dano (utilitária), defina tem_dano=false "
        "e dado_dano com valores quaisquer (serão ignorados).\n"
    )
    return chamar_ollama(system, user, SCHEMAS["conjuracao"], modelo, url)


def gerar_familiar(
    conceito: str,
    modelo: str | None = None,
    url: str | None = None,
) -> dict:
    """Gera um familiar selvagem (também serve como base para monstros)."""
    system = _system_prompt("familiar")
    user = (
        f"Crie um FAMILIAR com o seguinte conceito: '{conceito}'\n\n"
        "Um FAMILIAR é uma criatura rara cuja existência foi transformada pela influência de uma "
        "MATRIZ. Descreva sua aparência, comportamento instintivo e habilidades especiais. "
        "Seja criativo e coerente com a matriz escolhida.\n"
    )
    return chamar_ollama(system, user, SCHEMAS["familiar"], modelo, url)


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
