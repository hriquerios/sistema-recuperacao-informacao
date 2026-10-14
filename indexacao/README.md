# Módulo 1 — Extração e Indexação

Lê os 20 artigos em PDF da pasta [`artigos/`](artigos/) (área: Engenharia de
Dados, SOL/SBC), extrai título, autores e resumo, faz o pré-processamento do
resumo e grava os índices usados pelo módulo de
[recuperação](../recuperacao/README.md).

> Visão geral do projeto e instruções completas: [README principal](../README.md).

## Como executar

Na raiz do repositório, com o ambiente virtual ativo
(veja [Como executar](../README.md#como-executar)):

```bash
python -m pip install -r indexacao/requirements.txt   # só na primeira vez
python indexacao/main.py
```

O script pode ser executado de qualquer pasta. Ao final aparece
`Concluído: 20/20 documentos indexados...` e os arquivos são gravados em
[`saida/`](saida/).

> **PowerShell:** se aparecer um erro dizendo que a execução de scripts foi
> desabilitada ao ativar o ambiente virtual, rode uma vez o comando abaixo:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

## O que é gerado (pasta `saida/`)

| Arquivo | Conteúdo |
|---|---|
| `vocabulario/doc_XX.txt` | Vocabulário controlado de cada documento, uma linha `<Termo, Freq>` por termo |
| `dicionario_termos.txt` | Dicionário de termos da coleção com a quantidade total de ocorrências `<Termo, Freq>` |
| `tabela_documentos.csv` | `<DocId, Título, Autor, Total de termos significativos>` (separador `;`, abre direto no Excel) |
| `registro_totpal.txt` | Registro `<DocId, TotPal>` com o último identificador e o total de palavras, seguido do detalhamento por documento |
| `resumos/doc_XX.txt` | Resumo extraído de cada PDF, para conferência |
| `relatorio_extracao.txt` | Gerado só quando algum PDF apresenta problema na extração |

Definições usadas:
- **DocId**: número sequencial atribuído pela ordem alfabética do nome do PDF
  (1 a 20). Por isso os arquivos de `artigos/` começam com `01-` a `20-`: o
  prefixo garante que o PDF `NN-...pdf` receba o DocId `NN`.
- **TotPal**: total de palavras do resumo, antes da remoção das stopwords.
- **Total de termos significativos**: total de ocorrências de termos que sobraram depois da remoção das stopwords.

## Estrutura do código

| Arquivo | Responsabilidade |
|---|---|
| `extrator.py` | Lê o PDF (PyMuPDF): título, autor(es) e resumo, com correção dos acentos |
| `preprocessador.py` | Transforma o resumo em vetor de palavras, normaliza e remove stopwords |
| `indexador.py` | Elimina repetições contabilizando frequências e grava os `.txt <Termo, Freq>` |
| `catalogador.py` | Tabela de documentos e registro `<DocId, TotPal>` |
| `main.py` | Orquestra o pipeline para todos os PDFs de `artigos/` |

## Como a extração funciona

- **Título**: linhas com a maior fonte da primeira página.
- **Autor(es)**: linhas logo abaixo do título, até a primeira linha de afiliação
  (números sobrescritos de afiliação são descartados).
- **Resumo**: trecho entre `Resumo.` e o primeiro marcador de fim (`Abstract.`,
  `Palavras-chave`, `1. Introdução` ou o rodapé `Proceedings of...`).

### Correção de acentos

Os PDFs gerados em LaTeX guardam os acentos separados da letra: o texto sai como
`n˜ao`, `an´alise`, `informac¸˜ao`. O `extrator.corrigir_acentos()` recompõe esses
pares (`não`, `análise`, `informação`) e também desfaz ligaduras tipográficas
(`ﬁ` → `fi`). Palavras hifenizadas na quebra de linha (`en-` / `contrar`) são
unidas. Se sobrar algum acento solto, o documento aparece em `relatorio_extracao.txt`.

## Tokenização

- Palavra = sequência de letras e dígitos; hífen interno faz parte da palavra
  (`espaço-temporais`, `sistemas-de-sistemas`).
- Tokens só com números (`2025`, `80`) e palavras de uma letra são descartados.
- Tudo em minúsculas, mantendo a acentuação.

## Stopwords

O `stopwords.txt` está em **ISO-8859-1 (Latin-1)**, não em UTF-8;
`preprocessador.carregar_stopwords()` trata isso automaticamente.

Além dessa lista, `preprocessador.STOPWORDS_EXPANSAO_AREA` remove termos
genéricos que aparecem na maioria dos resumos desta área e por isso não
diferenciam um documento do outro: *dados, sistema(s), informação(ões), artigo,
trabalho(s), resultado(s), proposta, estudo(s)*, entre outros. Para usar apenas a
lista do arquivo, basta esvaziar esse conjunto.
