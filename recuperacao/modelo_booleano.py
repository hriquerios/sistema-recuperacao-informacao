# -*- coding: utf-8 -*-
"""
Módulo 2b — Modelo Booleano (implementado "à mão", sem bibliotecas de RI).

A consulta é uma expressão lógica sobre termos, com os operadores:
    AND (ou E)    -> interseção dos conjuntos de documentos
    OR  (ou OU)   -> união
    NOT (ou NÃO)  -> complemento em relação à coleção inteira
    ( )           -> agrupamento, permitindo operadores aninhados
AND, OR e NOT são aceitos em maiúsculas ou minúsculas (são palavras em inglês,
não aparecem nos resumos). Já E, OU e NÃO só valem em MAIÚSCULAS, para não
serem confundidos com as palavras comuns "e", "ou", "não" (que são stopwords).
Dois termos lado a lado sem operador são ligados por AND implícito.
Um trecho entre aspas ("data lake") vira o AND de seus termos.

Precedência (da maior para a menor): parênteses > NOT > AND > OR.
Gramática (análise sintática descendente recursiva):
    expr_or   := expr_and ( OR expr_and )*
    expr_and  := expr_not ( [AND] expr_not )*
    expr_not  := NOT expr_not | primario
    primario  := "(" expr_or ")" | TERMO

Cada TERMO passa pelo MESMO processamento da indexação (minúsculas, remoção de
stopwords). Se um termo for uma stopword, ele é ignorado: "x AND <stopword>"
vale apenas "x". No modelo booleano todo documento recuperado tem a mesma
relevância (satisfaz ou não a expressão), por isso não existe ranking:
os resultados são exibidos em ordem de DocId.
"""

import re

# Sinônimos aceitos para cada operador (sempre em maiúsculas)
OPERADORES = {
    "AND": "AND", "E": "AND",
    "OR": "OR", "OU": "OR",
    "NOT": "NOT", "NÃO": "NOT", "NAO": "NOT",
}

# Tokens da consulta: parênteses, trechos entre aspas ou palavras soltas
_PADRAO_TOKEN = re.compile(r'\(|\)|"[^"]*"|[^\s()"]+')


class ErroConsulta(Exception):
    """Erro de sintaxe na consulta booleana (mensagem exibida ao usuário)."""


# ---------------------------------------------------------------------------
# 1) Análise léxica: texto -> lista de tokens
# ---------------------------------------------------------------------------

def _tokenizar_consulta(consulta: str) -> list:
    """Separa a consulta em tokens do tipo ("OP", "AND"), ("ABRE",), ("FECHA",) ou ("TERMO", texto)."""
    tokens = []
    for bruto in _PADRAO_TOKEN.findall(consulta):
        if bruto == "(":
            tokens.append(("ABRE",))
        elif bruto == ")":
            tokens.append(("FECHA",))
        elif bruto.upper() in ("AND", "OR", "NOT"):  # inglês: qualquer caixa
            tokens.append(("OP", bruto.upper()))
        elif bruto in OPERADORES:  # português: só em maiúsculas
            tokens.append(("OP", OPERADORES[bruto]))
        else:
            tokens.append(("TERMO", bruto.strip('"')))
    return tokens


# ---------------------------------------------------------------------------
# 2) Análise sintática: tokens -> árvore da expressão
#    Nós da árvore: ("TERMO", [termos], texto_original) | ("NOT", filho)
#                   ("AND", esq, dir) | ("OR", esq, dir)
# ---------------------------------------------------------------------------

class _Parser:
    """Analisador descendente recursivo: cada regra da gramática vira um método."""

    def __init__(self, tokens: list, colecao):
        self.tokens = tokens
        self.pos = 0
        self.colecao = colecao

    def _atual(self):
        """Token na posição corrente (ou None no fim da consulta)."""
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _avancar(self):
        """Consome o token corrente e o devolve."""
        token = self._atual()
        self.pos += 1
        return token

    def analisar(self):
        """Ponto de entrada: a consulta inteira tem que ser uma expressão válida."""
        if not self.tokens:
            raise ErroConsulta("Consulta vazia.")
        arvore = self._expr_or()
        if self._atual() is not None:
            raise ErroConsulta("Parêntese ')' sem o '(' correspondente.")
        return arvore

    def _expr_or(self):
        """expr_or := expr_and ( OR expr_and )*"""
        esquerda = self._expr_and()
        while self._atual() == ("OP", "OR"):
            self._avancar()
            esquerda = ("OR", esquerda, self._expr_and())
        return esquerda

    def _expr_and(self):
        """expr_and := expr_not ( [AND] expr_not )*   (AND explícito ou implícito)"""
        esquerda = self._expr_not()
        while True:
            token = self._atual()
            if token == ("OP", "AND"):
                self._avancar()
                esquerda = ("AND", esquerda, self._expr_not())
            elif token is not None and (token[0] in ("TERMO", "ABRE") or token == ("OP", "NOT")):
                # Termo logo após outro termo, sem operador: AND implícito
                esquerda = ("AND", esquerda, self._expr_not())
            else:
                return esquerda

    def _expr_not(self):
        """expr_not := NOT expr_not | primario"""
        if self._atual() == ("OP", "NOT"):
            self._avancar()
            return ("NOT", self._expr_not())
        return self._primario()

    def _primario(self):
        """primario := "(" expr_or ")" | TERMO"""
        token = self._avancar()
        if token is None:
            raise ErroConsulta("A consulta termina com um operador sem operando.")
        if token[0] == "ABRE":
            subexpressao = self._expr_or()
            if self._avancar() != ("FECHA",):
                raise ErroConsulta("Falta fechar um parêntese ')'.")
            return subexpressao
        if token[0] == "TERMO":
            # Mesmo processamento da indexação (minúsculas + remoção de stopwords)
            termos = self.colecao.processar_texto(token[1])["termos"]
            return ("TERMO", termos, token[1])
        if token[0] == "FECHA":
            raise ErroConsulta("Parêntese ')' inesperado (subexpressão vazia?).")
        raise ErroConsulta(f"Operador {token[1]} sem operando à esquerda.")


# ---------------------------------------------------------------------------
# 3) Avaliação: árvore -> conjunto de DocIds
#    None representa "subexpressão ignorada" (só tinha stopwords).
# ---------------------------------------------------------------------------

def _avaliar(no, colecao):
    """Avalia a árvore recursivamente usando operações de conjuntos."""
    tipo = no[0]
    if tipo == "TERMO":
        termos = no[1]
        if not termos:
            return None  # stopword: termo ignorado
        resultado = colecao.documentos_com_termo(termos[0])
        for termo in termos[1:]:  # trecho com várias palavras: AND entre elas
            resultado &= colecao.documentos_com_termo(termo)
        return resultado
    if tipo == "NOT":
        filho = _avaliar(no[1], colecao)
        return None if filho is None else colecao.todos_doc_ids() - filho
    esquerda = _avaliar(no[1], colecao)
    direita = _avaliar(no[2], colecao)
    if esquerda is None:
        return direita
    if direita is None:
        return esquerda
    return esquerda & direita if tipo == "AND" else esquerda | direita


def _descrever(no) -> str:
    """Reescreve a árvore como texto com parênteses explícitos (mostra a precedência aplicada)."""
    tipo = no[0]
    if tipo == "TERMO":
        if not no[1]:
            return f"[{no[2]}: ignorado]"
        return no[1][0] if len(no[1]) == 1 else "(" + " AND ".join(no[1]) + ")"
    if tipo == "NOT":
        return "NOT " + _descrever(no[1])
    return f"({_descrever(no[1])} {tipo} {_descrever(no[2])})"


def _coletar_termos(no, usados: list, ignorados: list):
    """Percorre a árvore listando os termos usados e os ignorados (stopwords)."""
    if no[0] == "TERMO":
        if no[1]:
            usados.extend(t for t in no[1] if t not in usados)
        else:
            ignorados.append(no[2])
    else:
        for filho in no[1:]:
            _coletar_termos(filho, usados, ignorados)


# ---------------------------------------------------------------------------
# Função principal do modelo
# ---------------------------------------------------------------------------

def buscar(consulta: str, colecao) -> dict:
    """
    Executa uma consulta booleana. Devolve:
        resultados : lista de (DocId, 1.0) em ordem de DocId (sem ranking)
        termos     : termos efetivamente usados após o pré-processamento
        ignorados  : palavras descartadas por serem stopwords
        expressao  : a expressão interpretada, com parênteses explícitos
        postings   : {termo: [DocIds]} para conferência
    Lança ErroConsulta se a sintaxe estiver errada.
    """
    arvore = _Parser(_tokenizar_consulta(consulta), colecao).analisar()
    conjunto = _avaliar(arvore, colecao) or set()

    usados, ignorados = [], []
    _coletar_termos(arvore, usados, ignorados)

    return {
        "resultados": [(doc_id, 1.0) for doc_id in sorted(conjunto)],
        "termos": usados,
        "ignorados": ignorados,
        "expressao": _descrever(arvore),
        "postings": {t: sorted(colecao.documentos_com_termo(t)) for t in usados},
    }
