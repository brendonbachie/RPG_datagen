# CRIAÇÃO DE CONJURAÇÕES

Toda CONJURAÇÃO deve possuir os seguintes campos.

## ESTRUTURA

- NOME (TEXTO)
- MATRIZ (MATRIZ)
- SUB-MATRIZ (SUB-MATRIZ | OPCIONAL)
- CUSTO (0+)
- GANHO DE CONEXÃO (0+)
- GASTO DE AÇÃO (AÇÃO DE LOCOMOÇÃO | AÇÃO COMPLEXA | AÇÃO EXTRA)
- ALCANCE (CURTO | MÉDIO | LONGO | EXTREMO)
- ÁREA (ALVO | LINHA | CONE | CÍRCULO | ZONA)
- DANO (XdY | 0)
- EFEITOS (LISTA)
- DESCRIÇÃO (TEXTO)

---

# MATRIZ

Define a natureza fundamental da CONJURAÇÃO.

## VALORES VÁLIDOS

- INCÊNDIO
- INUNDAÇÃO
- TEMPESTADE
- CICLONE
- TERREMOTO
- NEUTRO
- MARCIAL
- FAUNA
- FLORA
- GUARDIÃO
- FÁBULA
- SÓLIDO
- MALEÁVEL
- ESCURO
- ESPIRITUAL
- MENTAL

---

# SUB-MATRIZ

Define a forma de manifestação da CONJURAÇÃO.

## VALORES VÁLIDOS

- ESPIRAL
- ONDA
- FÚRIA
- ESPORO
- TEMPERATURA

---

# CUSTO

Quantidade de CONEXÃO consumida ao utilizar a CONJURAÇÃO.

## RANGE

- 0+

---

# GANHO DE CONEXÃO

Quantidade de CONEXÃO gerada ao utilizar a CONJURAÇÃO.

## RANGE

- 0+

---

# GASTO DE AÇÃO

Determina qual tipo de AÇÃO deve ser gasto para utilizar a CONJURAÇÃO.

## VALORES VÁLIDOS

- AÇÃO DE LOCOMOÇÃO
- AÇÃO COMPLEXA
- AÇÃO EXTRA

---

# ALCANCE

Determina a distância máxima da CONJURAÇÃO.

## VALORES VÁLIDOS

- CURTO
- MÉDIO
- LONGO
- EXTREMO

---

# ÁREA

Determina como a CONJURAÇÃO afeta seus alvos.

## VALORES VÁLIDOS

- ALVO
- LINHA
- CONE
- CÍRCULO
- ZONA

---

# DANO

Quantidade de DADOS utilizados para determinar o DANO causado.

## FORMATO

- XdY
- 0

---

# EFEITOS

Lista de efeitos mecânicos produzidos pela CONJURAÇÃO.

## VALORES POSSÍVEIS

- CONDIÇÕES
- MANOBRAS
- EFEITOS PERSONALIZADOS

---

# DESCRIÇÃO

Representação narrativa e visual da CONJURAÇÃO.

## FORMATO

- TEXTO