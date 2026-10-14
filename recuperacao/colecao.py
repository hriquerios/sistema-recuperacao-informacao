# -*- coding: utf-8 -*-
"""
Módulo 2a — Carga da coleção indexada.

Lê as estruturas gravadas pelo módulo de indexação (pasta "indexacao/saida") e monta, em
memória, o que os modelos de recuperação precisam:

    - tabela de documentos   <DocId, Título, Autor, Total de termos significativos>
    - vocabulário de cada documento  <Termo, Freq>  (vocabulario/doc_XX.txt)
    - índice invertido       termo -> {DocId: freq}  (montado a partir do vocabulário)
    - dicionário de termos   <Termo, Freq total na coleção>
    - resumo e caminho do PDF original de cada documento

O processamento da consulta reutiliza EXATAMENTE as funções do pré-processador
do módulo de indexação (tokenizar + remover_stopwords), garantindo que a consulta passe
pelas mesmas etapas que os resumos passaram na indexação.
"""

import csv
import glob
import os
import re
import sys
from collections import Counter

# ---------------------------------------------------------------------------
# Caminhos (recuperacao/ fica ao lado de indexacao/, na raiz do projeto)
# ---------------------------------------------------------------------------
PASTA_RECUPERACAO = os.path.dirname(os.path.abspath(__file__))
PASTA_INDEXACAO = os.path.join(os.path.dirname(PASTA_RECUPERACAO), "indexacao")
PASTA_SAIDA_INDEXACAO = os.path.join(PASTA_INDEXACAO, "saida")
PASTA_ARTIGOS = os.path.join(PASTA_INDEXACAO, "artigos")
ARQUIVO_STOPWORDS = os.path.join(PASTA_INDEXACAO, "stopwords.txt")

# Permite importar o preprocessador.py de indexacao/ (mesmo código da indexação)
if PASTA_INDEXACAO not in sys.path:
    sys.path.insert(0, PASTA_INDEXACAO)
from preprocessador import carregar_stopwords, tokenizar, remover_stopwords  # noqa: E402

# Linha dos arquivos de vocabulário/dicionário: "<termo, freq>"
_PADRAO_LINHA_TF = re.compile(r"^<(.+),\s*(\d+)>$")


def _ler_arquivo_tf(caminho: str) -> dict:
    """Lê um arquivo no formato <Termo, Freq> e devolve {termo: freq}."""
    frequencias = {}
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            m = _PADRAO_LINHA_TF.match(linha.strip())
            if m:
                frequencias[m.group(1)] = int(m.group(2))
    return frequencias


class Colecao:
    """Coleção de documentos já indexada, carregada a partir da saída de indexacao/."""

    def __init__(self):
        # Mesma lista de stopwords usada na indexação (fornecida + expansão da área)
        self.stopwords = carregar_stopwords(ARQUIVO_STOPWORDS)

        self.documentos = {}         # DocId -> dict com título, autores, resumo, pdf...
        self.vocabulario = {}        # DocId -> {termo: freq}
        self.indice_invertido = {}   # termo -> {DocId: freq}
        self.dicionario = _ler_arquivo_tf(os.path.join(PASTA_SAIDA_INDEXACAO, "dicionario_termos.txt"))

        self._carregar_tabela_documentos()
        self._carregar_vocabularios()
        self._montar_indice_invertido()

    # ------------------------------------------------------------------
    # Carga das estruturas gravadas pela indexação
    # ------------------------------------------------------------------

    def _carregar_tabela_documentos(self):
        """Lê a tabela <DocId, Título, Autor, Total de termos> e associa o PDF original."""
        # O DocId foi atribuído na indexação pela ordem alfabética do nome do PDF,
        # então o i-ésimo PDF em ordem alfabética corresponde ao DocId i.
        pdfs = sorted(glob.glob(os.path.join(PASTA_ARTIGOS, "*.pdf")))

        caminho = os.path.join(PASTA_SAIDA_INDEXACAO, "tabela_documentos.csv")
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            leitor = csv.reader(f, delimiter=";")
            next(leitor)  # pula o cabeçalho
            for linha in leitor:
                doc_id = int(linha[0])
                caminho_resumo = os.path.join(PASTA_SAIDA_INDEXACAO, "resumos", f"doc_{doc_id:02d}.txt")
                resumo = ""
                if os.path.exists(caminho_resumo):
                    with open(caminho_resumo, encoding="utf-8") as fr:
                        resumo = fr.read().strip()
                self.documentos[doc_id] = {
                    "doc_id": doc_id,
                    "titulo": linha[1],
                    "autores": linha[2],
                    "total_termos": int(linha[3]),
                    "resumo": resumo,
                    "pdf": pdfs[doc_id - 1] if doc_id <= len(pdfs) else None,
                }

    def _carregar_vocabularios(self):
        """Lê o vocabulário controlado <Termo, Freq> de cada documento."""
        for doc_id in self.documentos:
            caminho = os.path.join(PASTA_SAIDA_INDEXACAO, "vocabulario", f"doc_{doc_id:02d}.txt")
            self.vocabulario[doc_id] = _ler_arquivo_tf(caminho)

    def _montar_indice_invertido(self):
        """Inverte o vocabulário: para cada termo, em quais documentos aparece e quantas vezes."""
        for doc_id, termos in self.vocabulario.items():
            for termo, freq in termos.items():
                self.indice_invertido.setdefault(termo, {})[doc_id] = freq

    # ------------------------------------------------------------------
    # Utilidades usadas pelos modelos
    # ------------------------------------------------------------------

    @property
    def total_documentos(self) -> int:
        """N = número de documentos da coleção."""
        return len(self.documentos)

    def todos_doc_ids(self) -> set:
        """Conjunto universo, usado pelo operador NOT do modelo booleano."""
        return set(self.documentos)

    def documentos_com_termo(self, termo: str) -> set:
        """Lista de postings: conjunto de DocIds em que o termo aparece."""
        return set(self.indice_invertido.get(termo, {}))

    def processar_texto(self, texto: str) -> dict:
        """
        Processa um texto de consulta exatamente como a indexação processou os resumos:
          1) separa as palavras (hífen interno faz parte da palavra);
          2) normaliza (minúsculas, mantendo acentos);
          3) elimina stopwords e palavras de uma letra.
        Devolve os termos significativos e as palavras descartadas (para exibir ao usuário).
        """
        palavras = tokenizar(texto)
        termos = remover_stopwords(palavras, self.stopwords)
        descartadas = [p for p in palavras if p not in termos]
        return {"termos": termos, "frequencias": Counter(termos), "descartadas": descartadas}
