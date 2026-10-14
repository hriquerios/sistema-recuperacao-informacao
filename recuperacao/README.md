# Módulo 2 — Recuperação de Informações

Interface gráfica de busca (Tkinter) sobre os 20 artigos indexados pelo módulo
de [indexação](../indexacao/README.md), com **Modelo Booleano** e **Modelo de
Espaço Vetorial** implementados à mão (sem bibliotecas de RI). Só usa a
biblioteca padrão do Python.

> Visão geral do projeto e instruções completas: [README principal](../README.md).

## Como executar

Este módulo lê os índices de [`../indexacao/saida/`](../indexacao/saida/), que
já vêm gerados no repositório. Se a indexação for refeita, a interface passa a
usar os novos índices. Na raiz do repositório:

```bash
python recuperacao/main.py
```

Não é preciso instalar nada além do Python: o Tkinter já vem com ele no Windows
e o PyMuPDF só é usado na indexação. Os scripts podem ser executados de
qualquer pasta.

Para gerar só o relatório das 5 consultas de teste, sem abrir a janela:

```bash
python recuperacao/consultas_teste.py
```

O relatório é gravado em
[`saida/avaliacao_consultas_teste.txt`](saida/avaliacao_consultas_teste.txt).

## Usando a interface

**Aba Busca**
1. Digite a consulta e escolha o modelo (Espaço Vetorial ou Booleano).
2. Abaixo da caixa aparecem os termos que sobraram após o pré-processamento e as
   stopwords descartadas (a consulta passa pelo mesmo processo da indexação).
3. Os resultados aparecem ordenados por relevância, com Título e Autor(es).
4. Clique num resultado para ver os detalhes: DocId, autores, resumo com os
   termos da consulta destacados e o motivo de ter sido recuperado (no vetorial,
   a tabela com tf, idf, pesos e similaridade; no booleano, os termos presentes
   e ausentes).
5. **Abrir documento (PDF)** ou duplo clique abre o artigo original.
6. O menu "Carregar consulta de teste..." preenche uma das 5 consultas fixas.

**Aba Consultas de teste**: precisão e revocação dos dois modelos nas 5
consultas fixas. Selecione uma linha para ver o gabarito, o que cada modelo
devolveu (✔ relevante / ✘ não relevante) e o que a consulta demonstra.

## Estrutura do código

| Arquivo | Responsabilidade |
|---|---|
| `colecao.py` | Carrega a tabela de documentos, os vocabulários `<Termo, Freq>`, os resumos e os PDFs de `indexacao/` e monta o índice invertido. Processa a consulta reutilizando o `preprocessador.py` de `indexacao/` |
| `modelo_booleano.py` | Analisador léxico e sintático (descendente recursivo) para AND/OR/NOT com parênteses e avaliação por operações de conjuntos |
| `modelo_vetorial.py` | Pesos TF-IDF e similaridade do cosseno |
| `consultas_teste.py` | 5 consultas fixas, julgamento de relevância a priori, precisão e revocação |
| `interface.py` | Janela Tkinter |
| `main.py` | Ponto de entrada |

## Processamento da consulta

`colecao.processar_texto()` chama as **mesmas funções** usadas na indexação
(`tokenizar` e `remover_stopwords` do `preprocessador.py` de `indexacao/`, com a
mesma lista de stopwords + expansão da área):
separação de palavras com hífen interno, minúsculas mantendo acentos, remoção de
stopwords e de palavras de uma letra. Assim, "Governança de Dados em Data Lakes"
vira `governança, data, lakes`.

## Modelo Booleano

- Operadores: `AND`, `OR` e `NOT` (em qualquer caixa) ou `E`, `OU` e `NÃO`
  (só em maiúsculas, porque "e", "ou" e "não" minúsculos são palavras comuns).
- Parênteses permitem aninhar: `(nosql OR newsql) AND (desempenho OR benchmarks) AND NOT levantamento`.
- Precedência: parênteses > NOT > AND > OR. Termos lado a lado são ligados por AND implícito.
- `"data lake"` entre aspas vira `data AND lake`. Não há índice posicional, então
  não é uma busca por frase exata.
- Avaliação: AND = interseção, OR = união, NOT = complemento em relação aos 20 documentos.
- Um termo que é stopword é ignorado, e `x AND de` vale apenas `x`. A expressão
  interpretada, com os parênteses explícitos, é mostrada na interface.
- **Não existe ranking.** Um documento satisfaz ou não a expressão, então todos
  os recuperados têm a mesma relevância e são listados por DocId.

## Modelo de Espaço Vetorial

| Componente | Fórmula | Justificativa |
|---|---|---|
| TF | `1 + log2(f)` | Amortece a frequência bruta: um termo que aparece 4× pesa mais que 1×, mas não 4× mais |
| IDF | `log2(N / n_t)` | Termos presentes em muitos resumos (ex.: `data`, em 11 de 20) discriminam pouco |
| Peso | `w = tf × idf` | Usado tanto nos documentos quanto na consulta |
| Similaridade | cosseno: `Σ w_d·w_q / (‖d‖·‖q‖)` | Normaliza o tamanho do resumo, para que resumos longos não sejam favorecidos |

São devolvidos todos os documentos com similaridade > 0, do maior para o menor
valor. Para economizar cálculos, só são comparados os documentos que aparecem
no índice invertido de algum termo da consulta, já que os demais teriam produto
escalar 0.

## Conjunto de testes obrigatório

O julgamento de relevância foi feito **a priori**, a partir do título e do
resumo de cada artigo e da necessidade de informação descrita, antes de rodar
os modelos. Ele está registrado em `consultas_teste.py`, junto com a
justificativa de cada documento considerado relevante ou não relevante.

| Teste | Necessidade | Consulta booleana | Consulta vetorial | Relevantes | Cobre |
|---|---|---|---|---|---|
| T1 | Governança de dados em data lakes | `governança AND (lake OR lakes)` | `governança de dados em data lakes` | 3, 9 | caso de sucesso |
| T2 | Avaliação de desempenho de SGBDs NoSQL/NewSQL (sem surveys) | `(nosql OR newsql) AND (desempenho OR benchmarks) AND NOT levantamento` | `desempenho de bancos NoSQL e NewSQL` | 5, 18 | **operadores aninhados** |
| T3 | Blockchain / criptografia | `blockchain OR criptografia` | `blockchain e criptografia de dados` | nenhum | **resultado vazio** |
| T4 | Proveniência e linhagem de dados | `proveniência AND linhagem AND rastreabilidade` | `proveniência, linhagem e rastreabilidade de dados` | 3, 7, 17 | **limitação do booleano** |
| T5 | Bancos de dados relacionais | `(relacional OR relacionais) AND (banco OR bancos)` | `banco de dados relacional` | 10, 16, 18 | **limitação do vetorial** |

### Resultados obtidos

| Teste | Booleano: recup. | P | R | Vetorial: recup. | P | R | P@5 | R@5 |
|---|---|---|---|---|---|---|---|---|
| T1 | 3 | 0,67 | 1,00 | 13 | 0,15 | 1,00 | 0,40 | 1,00 |
| T2 | 1 | 1,00 | 0,50 | 9 | 0,22 | 1,00 | 0,20 | 0,50 |
| T3 | 0 | n/d | n/d | 0 | n/d | n/d | n/d | n/d |
| T4 | 0 | n/d | 0,00 | 3 | 1,00 | 1,00 | 1,00 | 1,00 |
| T5 | 3 | 1,00 | 1,00 | 4 | 0,25 | 0,33 | 0,25 | 0,33 |

n/d = indefinida (0/0). No vetorial, P e R usam a lista completa (sim > 0) e
P@5/R@5 usam só os 5 primeiros do ranking. O detalhamento completo está em
`saida/avaliacao_consultas_teste.txt`.

### Pontos para a discussão

- **T1:** o vetorial coloca os 2 relevantes nas posições 1 e 2. A precisão da
  lista completa é baixa (0,15) porque qualquer documento com `data` entra com
  similaridade pequena. Por isso P@5 mostra melhor a qualidade do ranking.
  O doc 5 aparece porque usa "data" no sentido de *dia* ("consultas espaciais
  em uma data específica"). É um exemplo de **polissemia**: os modelos comparam
  palavras, não significados.
- **T2:** a consulta aninhada acerta o doc 18, mas perde o doc 5. O resumo do
  doc 5 cita "MongoDB" e "InfluxDB" e não usa a palavra "NoSQL", que só aparece
  no título. Como a indexação considera apenas o resumo, o artigo não é
  encontrado (**problema de vocabulário**).
- **T3:** os termos não existem no dicionário da coleção, então os dois modelos
  devolvem vazio, como esperado.
- **T4 (limitação do booleano):** o AND é tudo ou nada. Cada artigo relevante usa
  só parte dos termos, então a interseção é vazia (revocação 0). O vetorial
  aceita casamento parcial e ranqueia os três relevantes.
- **T5 (limitação do vetorial):** sem radicalização (*stemming*), `relacional` e
  `relacionais` (e também `banco` e `bancos`) são dimensões diferentes do vetor.
  A frase em linguagem natural casa só com `banco` e traz artigos de NoSQL. No
  booleano, o usuário pode listar as variações com OR aninhado e recuperar tudo.
  O modelo vetorial é mais tolerante, mas não é necessariamente melhor.
