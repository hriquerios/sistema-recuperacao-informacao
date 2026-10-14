# -*- coding: utf-8 -*-
"""
Módulo 2c — Modelo de Espaço Vetorial (implementado "à mão", sem bibliotecas de RI).

Cada documento e a consulta viram vetores no espaço dos termos do vocabulário.
O peso de um termo t em um vetor é TF-IDF:

    TF  (normalização logarítmica):  tf(t, d) = 1 + log2(f(t, d))   se f > 0, senão 0
    IDF (raridade na coleção):       idf(t)   = log2(N / n_t)
    peso:                            w(t, d)  = tf(t, d) * idf(t)

    f(t, d) = frequência do termo no documento (arquivo vocabulario/doc_XX.txt)
    N       = total de documentos da coleção
    n_t     = número de documentos em que o termo aparece

Por que essas escolhas:
  - TF logarítmico: um termo que aparece 4 vezes é mais importante que um que
    aparece 1 vez, mas não 4 vezes mais importante. O log amortece a frequência
    bruta e evita que um termo repetido domine o vetor.
  - IDF: termos presentes em quase todos os resumos (ex.: "data") discriminam
    pouco e recebem peso baixo; termos raros (ex.: "newsql") recebem peso alto.
    Um termo presente em TODOS os documentos teria idf = log2(1) = 0.

A consulta recebe a mesma fórmula, usando a frequência do termo na consulta.

Similaridade do cosseno entre o documento d e a consulta q:

                  Σ_t  w(t, d) * w(t, q)
    sim(d, q) = --------------------------
                     |d|  *  |q|

onde |d| e |q| são as normas euclidianas dos vetores. O cosseno normaliza o
tamanho dos documentos (resumos longos não são favorecidos só por terem mais
termos). Resultado entre 0 (nenhum termo em comum) e 1 (vetores proporcionais).
São devolvidos apenas documentos com similaridade > 0, ordenados da maior para
a menor similaridade.
"""

import math


def peso_tf(frequencia: int) -> float:
    """TF com normalização logarítmica: 1 + log2(f), ou 0 se o termo não ocorre."""
    return 1 + math.log2(frequencia) if frequencia > 0 else 0.0


class ModeloVetorial:
    """Pré-calcula os pesos TF-IDF dos documentos e responde consultas por similaridade do cosseno."""

    def __init__(self, colecao):
        self.colecao = colecao
        n = colecao.total_documentos

        # idf(t) = log2(N / n_t), calculado uma vez para cada termo do vocabulário
        self.idf = {termo: math.log2(n / len(postings))
                    for termo, postings in colecao.indice_invertido.items()}

        # Vetor de pesos de cada documento (esparso: só os termos que ele contém)
        self.pesos_documentos = {}
        self.normas = {}
        for doc_id, termos in colecao.vocabulario.items():
            vetor = {t: peso_tf(f) * self.idf[t] for t, f in termos.items()}
            self.pesos_documentos[doc_id] = vetor
            self.normas[doc_id] = math.sqrt(sum(w * w for w in vetor.values()))

    def vetor_consulta(self, frequencias: dict) -> dict:
        """Pesos TF-IDF da consulta. Termos fora do vocabulário da coleção têm peso 0."""
        return {t: peso_tf(f) * self.idf[t] for t, f in frequencias.items() if t in self.idf}

    def buscar(self, consulta: str) -> dict:
        """
        Executa a consulta. Devolve:
            resultados : lista de (DocId, similaridade), da maior para a menor
            termos     : termos da consulta após o pré-processamento
            ignorados  : palavras descartadas (stopwords)
            fora_vocab : termos que não existem em nenhum documento
            vetor_q    : pesos da consulta {termo: w(t, q)}
        """
        processada = self.colecao.processar_texto(consulta)
        vetor_q = self.vetor_consulta(processada["frequencias"])
        norma_q = math.sqrt(sum(w * w for w in vetor_q.values()))

        resultados = []
        if norma_q > 0:
            # Só precisa olhar os documentos que têm pelo menos um termo da consulta
            # (os demais têm produto escalar 0) -> percorre as listas do índice invertido
            candidatos = set()
            for termo in vetor_q:
                candidatos |= self.colecao.documentos_com_termo(termo)

            for doc_id in candidatos:
                vetor_d = self.pesos_documentos[doc_id]
                produto_escalar = sum(w_q * vetor_d.get(t, 0.0) for t, w_q in vetor_q.items())
                if produto_escalar > 0 and self.normas[doc_id] > 0:
                    resultados.append((doc_id, produto_escalar / (self.normas[doc_id] * norma_q)))

        # Maior similaridade primeiro; empate desempata pelo DocId
        resultados.sort(key=lambda x: (-x[1], x[0]))
        return {
            "resultados": resultados,
            "termos": list(processada["frequencias"]),
            "ignorados": processada["descartadas"],
            "fora_vocab": [t for t in processada["frequencias"] if t not in self.idf],
            "vetor_q": vetor_q,
            "norma_q": norma_q,
        }

    def explicar(self, doc_id: int, vetor_q: dict) -> list:
        """
        Detalha a contribuição de cada termo da consulta para a similaridade de
        um documento (exibido no painel de detalhes da interface):
        (termo, f no doc, tf, idf, w doc, w consulta, produto).
        """
        linhas = []
        frequencias_doc = self.colecao.vocabulario[doc_id]
        for termo, w_q in vetor_q.items():
            f = frequencias_doc.get(termo, 0)
            w_d = self.pesos_documentos[doc_id].get(termo, 0.0)
            linhas.append((termo, f, peso_tf(f), self.idf[termo], w_d, w_q, w_d * w_q))
        return linhas
