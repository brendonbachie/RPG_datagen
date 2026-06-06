# Cliente HTTP para a API local do Ollama.
# Usa apenas urllib da stdlib — sem dependências externas.
import json
import os
import urllib.error
import urllib.request

OLLAMA_URL: str = os.environ.get("RPG_OLLAMA_URL", "http://localhost:11434/api/chat")
MODELO_PADRAO: str = os.environ.get("RPG_MODEL", "llama3:latest")

# Contexto mínimo para caber as regras (~13k tokens) + prompt do usuário
NUM_CTX: int = int(os.environ.get("RPG_NUM_CTX", "16384"))

# Timeout (s) de cada chamada. Modelos grandes sem GPU completa (ex: qwen3:8b
# parcialmente na CPU) podem levar vários minutos em schemas grandes (relíquia).
TIMEOUT: int = int(os.environ.get("RPG_TIMEOUT", "600"))


class ErroOllama(Exception):
    """Erro de comunicação ou resposta inválida do Ollama."""


def chamar_ollama(
    system: str,
    user: str,
    schema: dict,
    modelo: str | None = None,
    url: str | None = None,
    num_ctx: int | None = None,
    timeout: int | None = None,
) -> dict:
    """
    Envia uma chamada ao Ollama com saída estruturada (JSON Schema no campo 'format').
    Retorna o objeto Python já desserializado.
    Lança ErroOllama em caso de falha de conexão ou resposta inválida.
    """
    modelo = modelo or MODELO_PADRAO
    url = url or OLLAMA_URL
    num_ctx = num_ctx or NUM_CTX
    timeout = timeout or TIMEOUT

    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "format": schema,
        "stream": False,
        "options": {"num_ctx": num_ctx},
    }

    dados = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=dados,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            corpo = resp.read().decode("utf-8")
    except urllib.error.URLError as e:
        raise ErroOllama(
            f"Não foi possível conectar ao Ollama em '{url}'.\n"
            f"Certifique-se de que o Ollama está rodando: ollama serve\n"
            f"Detalhe: {e}"
        ) from e

    try:
        resposta = json.loads(corpo)
    except json.JSONDecodeError as e:
        raise ErroOllama(f"Corpo da resposta não é JSON válido: {e}\n{corpo[:500]}") from e

    try:
        conteudo = resposta["message"]["content"]
        return json.loads(conteudo)
    except KeyError as e:
        raise ErroOllama(f"Campo ausente na resposta do Ollama: {e}\n{resposta}") from e
    except json.JSONDecodeError as e:
        raise ErroOllama(
            f"Conteúdo retornado não é JSON válido: {e}\n"
            f"Conteúdo: {resposta.get('message', {}).get('content', '')[:500]}"
        ) from e
