# Gerador do Sistema das Relíquias

Gerador **local e offline** de conteúdo para o RPG de mesa *Sistema das Relíquias*, usando um modelo de linguagem rodando localmente via [Ollama](https://ollama.com).

---

## Pré-requisitos

| Ferramenta | Versão mínima |
|---|---|
| Python | 3.10+ |
| Ollama | 0.5+ (saída estruturada / JSON Schema) |
| pytest | qualquer (apenas para testes) |

Sem dependências de terceiros além do Python padrão (`urllib`, `tkinter`, `json`).

---

## 0 — Ambiente virtual (venv)

O projeto **não** tem dependências de runtime além da stdlib, mas uma venv deixa
os testes (`pytest`) isolados e o setup reproduzível em qualquer máquina.

### Opção A — com `uv` (recomendado, **sem sudo**, GUI inclusa)

O `tkinter` (usado pela GUI) **não** é instalável via pip. A forma mais simples
de tê-lo sem privilégios de administrador é usar um Python "standalone" do
[`uv`](https://docs.astral.sh/uv/), que **já vem com tkinter embutido**:

```bash
uv python install 3.12               # baixa um CPython com tkinter (Tk 9), sem sudo
uv venv --python 3.12 .venv          # cria a venv a partir desse Python
source .venv/bin/activate            # Windows: .venv\Scripts\activate
uv pip install -r requirements-dev.txt
```

Pronto — `python gerador.py ...`, `python gui.py` e `pytest tests/` rodam todos
pela venv, **incluindo a GUI**, sem instalar nada no sistema.

### Opção B — venv padrão + tkinter do sistema (requer sudo)

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
sudo apt-get install -y python3-tk   # tkinter do sistema (precisa de sudo)
```

> **WSL2:** a janela da GUI requer WSLg (Windows 11) ou um servidor X (ex.:
> VcXsrv no Windows 10).

---

## 1 — Instalar o Ollama

**Windows / WSL2:**
```bash
# No PowerShell (Windows)
winget install Ollama.Ollama

# Ou via script (Linux/WSL)
curl -fsSL https://ollama.com/install.sh | sh
```

Inicie o servidor:
```bash
ollama serve
```

---

## 2 — Baixar o modelo

```bash
ollama pull qwen3:8b
```

> O modelo `qwen3:8b` pesa ~5 GB. Qualquer modelo compatível com Ollama funciona
> (ex: `llama3.1:8b`, `mistral:7b`). Use a variável `RPG_MODEL` para trocar.

---

## 3 — Ampliar o contexto (IMPORTANTE)

As regras do sistema têm ~13 000 tokens. O `num_ctx` padrão do Ollama é 2 048,
o que **corta as regras** e produz resultados incorretos.

### Opção A — Modelfile (recomendado, persistente)

```bash
# Na raiz do projeto
ollama create rpg-reliquia -f Modelfile
export RPG_MODEL=rpg-reliquia
```

### Opção B — Variável de ambiente (por sessão)

```bash
export RPG_NUM_CTX=16384
```

A variável `RPG_NUM_CTX` é lida pelo `engine/ollama.py` e enviada em cada
chamada via `options.num_ctx`. A GUI também possui um campo ajustável.

---

## 4 — Usar a CLI

```bash
# Formato
python gerador.py <tipo> "<conceito>" [opções]

# Exemplos
python gerador.py conjurador "um espadachim de matriz incêndio"
python gerador.py conjurador "ladra sombria e astuta" --nivel 3
python gerador.py reliquia   "machado de gelo de um urso glacial"
python gerador.py conjuracao "raio espiral da tempestade"
python gerador.py familiar   "serpente feita de sombras"

# Usar outro modelo
python gerador.py familiar "lobo de pedra" --modelo llama3.1:8b

# Redirecionar a saída para arquivo
python gerador.py conjurador "arqueiro flora" > personagem.json
```

### Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `RPG_MODEL` | `qwen3:8b` | Modelo Ollama a usar |
| `RPG_OLLAMA_URL` | `http://localhost:11434/api/chat` | Endpoint da API |
| `RPG_NUM_CTX` | `16384` | Tamanho do contexto em tokens |
| `RPG_TIMEOUT` | `600` | Timeout (s) por chamada — aumente em máquinas lentas |

---

## 5 — Usar a interface gráfica

```bash
python gui.py
```

A GUI abre com quatro abas (Conjurador, Relíquia, Conjuração, Familiar).
Na barra superior é possível ajustar modelo, URL e `num_ctx` sem reiniciar.

> **WSL2:** a GUI requer WSLg (Windows 11) ou um servidor X (ex: VcXsrv no Windows 10).

---

## 6 — Rodar os testes

```bash
# Instalar pytest (se necessário)
pip install pytest

# Rodar os testes (não requerem Ollama)
pytest tests/ -v
```

Os testes cobrem:
- **`rolar`** — quantidade, intervalo, determinismo por seed
- **`calcular_vida`** — fórmula `8 + (N×VIT) + N×1d6`
- **`calcular_conexao`** — fórmula `4 + (N×SINT) + N×1d4`
- **`validar_atributos`** — soma = 10, valores 0–3, no máximo um zero
- **`corrigir_atributos`** — correção de saídas inválidas do LLM

---

## Arquitetura

```
RPG/
├── gerador.py          # CLI — subcomandos conjurador/reliquia/conjuracao/familiar
├── gui.py              # Interface gráfica (tkinter)
├── engine/
│   ├── loader.py       # Carrega todos os .txt de regras no system prompt
│   ├── regras.py       # Regras hard-coded: validação, VIDA, CONEXÃO, dados
│   ├── schemas.py      # JSON Schemas para saída estruturada do Ollama
│   ├── biblioteca.py   # Lista persistente de conjurações (habilidades disponíveis)
│   └── ollama.py       # Cliente HTTP (urllib) para a API do Ollama
├── biblioteca/
│   └── conjuracoes.json # Banco acumulado de conjurações geradas (criado em runtime)
├── tests/
│   └── test_regras.py  # Testes pytest (sem Ollama)
├── Modelfile           # Configuração do modelo com num_ctx=16384
└── README.md
```

### Fluxo de geração

```
Usuário digita conceito
      │
      ▼
gerador.py
      │  carrega todas as regras (.txt)
      │  monta system prompt (regras) + user prompt (conceito)
      │  envia JSON Schema no campo "format"
      ▼
Ollama (qwen3:8b local)
      │  retorna JSON válido conforme schema
      ▼
Pós-processamento (apenas conjurador)
      │  validar_atributos() → corrigir_atributos() se necessário
      │  calcular_vida()    → determinístico, rola dados em Python
      │  calcular_conexao() → determinístico, rola dados em Python
      ▼
Resultado JSON final
```

### Regras duras implementadas em código

| Regra | Implementação |
|---|---|
| Atributos somam 10 | `validar_atributos` + `corrigir_atributos` |
| Valores 0–3, máx 1 zero | idem |
| VIDA = 8 + N×VIT + N×1d6 | `calcular_vida` |
| CONEXÃO = 4 + N×SINT + N×1d4 | `calcular_conexao` |
| Nº de perícias = ESCOLA + ASTÚCIA + 2 | `contar_pericias` + `ajustar_pericias` |
| Pool de perícias por escola | `ESCOLAS_PERICIAS` |
| Nível do conjurador = valor pedido | forçado em `gerar_conjurador` |
| Matrizes, núcleos, vetores… | enums nos JSON Schemas |

O LLM **nunca** calcula VIDA, CONEXÃO, a quantidade de perícias, nem valida a
distribuição de atributos — tudo isso é feito deterministicamente em Python.

### Habilidades = conjurações (biblioteca compartilhada)

As **habilidades** de uma criação são sempre **conjurações**. O sistema mantém
uma lista persistente em `biblioteca/conjuracoes.json`:

- Toda vez que uma **conjuração** é gerada (CLI, GUI ou indiretamente), ela é
  **adicionada à biblioteca**.
- Criações que possuem habilidades — **familiar** (`habilidades`) e **relíquia**
  (`conjuracoes`) — **selecionam** suas habilidades da biblioteca, preferindo a
  mesma matriz. Se a biblioteca for **insuficiente**, novas conjurações são
  geradas para preencher (e também entram na lista).

O caminho do arquivo pode ser trocado com a variável `RPG_BIBLIOTECA`.
