# SRI — Sistema de Recuperação de Informação

Sistema de Recuperação de Informação (SRI) feito em Python para uma coleção de
20 artigos científicos em português sobre **Engenharia de Dados**, publicados na
SOL/SBC. Ele cobre o ciclo completo de um buscador:

1. **Indexação**: lê os PDFs, extrai título, autores e resumo, faz o
   pré-processamento (tokenização e remoção de stopwords) e grava o vocabulário
   de cada documento e o dicionário da coleção.
2. **Recuperação**: interface gráfica de busca com **Modelo Booleano** e
   **Modelo de Espaço Vetorial (TF-IDF + cosseno)**, implementados à mão, sem
   bibliotecas de RI, e avaliados com precisão e revocação em 5 consultas de
   teste.

## Estrutura do repositório

```
SRI/
├── indexacao/              # Módulo 1: extração dos PDFs e indexação
│   ├── artigos/            # Os 20 PDFs da coleção (01-...pdf a 20-...pdf)
│   ├── saida/              # Índices gerados (vocabulários, dicionário, tabela de documentos)
│   ├── extrator.py         # Leitura do PDF: título, autores e resumo
│   ├── preprocessador.py   # Tokenização, normalização e remoção de stopwords
│   ├── indexador.py        # Frequências <Termo, Freq> e gravação dos vocabulários
│   ├── catalogador.py      # Tabela de documentos e registro <DocId, TotPal>
│   ├── main.py             # Executa o pipeline de indexação
│   ├── stopwords.txt
│   └── requirements.txt
└── recuperacao/            # Módulo 2: busca e avaliação
    ├── saida/              # Relatório das consultas de teste
    ├── colecao.py          # Carrega os índices e monta o índice invertido
    ├── modelo_booleano.py  # AND / OR / NOT com parênteses
    ├── modelo_vetorial.py  # TF-IDF e similaridade do cosseno
    ├── consultas_teste.py  # 5 consultas fixas, precisão e revocação
    ├── interface.py        # Interface gráfica (Tkinter)
    └── main.py             # Abre a interface
```

Cada módulo tem um README com os detalhes de implementação:
- [indexacao/README.md](indexacao/README.md)
- [recuperacao/README.md](recuperacao/README.md)

## Como executar

Requisitos: Python 3 (testado com 3.14) e Tkinter, que já vem com o Python no
Windows. Os comandos abaixo devem ser executados na raiz do repositório.

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows (PowerShell)
source .venv/bin/activate         # Linux / macOS

# 2. Instalar as dependências (PyMuPDF, usado na leitura dos PDFs)
python -m pip install -r indexacao/requirements.txt

# 3. (Opcional) Refazer a indexação. A pasta indexacao/saida/ já vem gerada.
python indexacao/main.py

# 4. Abrir a interface de busca
python recuperacao/main.py

# 5. (Opcional) Gerar só o relatório das consultas de teste
python recuperacao/consultas_teste.py
```

> No Linux, o Tkinter pode precisar ser instalado à parte
> (por exemplo, `sudo apt install python3-tk`).

## Como funciona

```
 PDFs (indexacao/artigos)
        │  extrator.py         título, autores, resumo (com correção de acentos do LaTeX)
        ▼
 preprocessador.py             tokenização, minúsculas, remoção de stopwords
        │
        ▼
 indexador.py / catalogador.py vocabulário <Termo, Freq> por documento,
        │                      dicionário da coleção, tabela de documentos
        ▼
 indexacao/saida/  ───────────► recuperacao/colecao.py   índice invertido
                                       │
                         ┌─────────────┴─────────────┐
                         ▼                           ▼
                 Modelo Booleano            Modelo de Espaço Vetorial
              (AND/OR/NOT, conjuntos)      (TF-IDF, cosseno, ranking)
                         └─────────────┬─────────────┘
                                       ▼
                             interface.py (Tkinter)
```

- O **DocId** de cada artigo é atribuído pela ordem alfabética do nome do PDF.
  Por isso os arquivos têm o prefixo `01-` a `20-`.
- A consulta passa pelo **mesmo pré-processamento** dos resumos: o módulo de
  recuperação reaproveita o `preprocessador.py` da indexação.
- **Booleano:** analisador sintático descendente recursivo, com precedência
  `()` > `NOT` > `AND` > `OR` e AND implícito entre termos. Não gera ranking.
- **Vetorial:** `tf = 1 + log2(f)`, `idf = log2(N / n_t)`, peso `tf × idf` e
  similaridade do cosseno. O resultado é ordenado por relevância.

## Resultados da avaliação

O julgamento de relevância foi feito **a priori**, antes de rodar os modelos.
Cada consulta foi escolhida para mostrar um comportamento diferente:

| Teste | Necessidade de informação | Booleano (P / R) | Vetorial (P@5 / R@5) | O que demonstra |
|---|---|---|---|---|
| T1 | Governança de dados em data lakes | 0,67 / 1,00 | 0,40 / 1,00 | caso de sucesso |
| T2 | Desempenho de SGBDs NoSQL/NewSQL | 1,00 / 0,50 | 0,20 / 0,50 | operadores aninhados |
| T3 | Blockchain / criptografia | n/d | n/d | resultado vazio |
| T4 | Proveniência e linhagem de dados | n/d / 0,00 | 1,00 / 1,00 | limitação do booleano (AND é tudo ou nada) |
| T5 | Bancos de dados relacionais | 1,00 / 1,00 | 0,25 / 0,33 | limitação do vetorial (sem *stemming*) |

n/d = indefinida (0/0). A análise completa está em
[recuperacao/README.md](recuperacao/README.md#conjunto-de-testes-obrigatório) e
em [recuperacao/saida/avaliacao_consultas_teste.txt](recuperacao/saida/avaliacao_consultas_teste.txt).

## Tecnologias

- Python 3, só com a biblioteca padrão, exceto a leitura de PDF
- [PyMuPDF](https://pymupdf.readthedocs.io/) para extrair o texto dos PDFs
- Tkinter para a interface gráfica
