# -*- coding: utf-8 -*-
"""
Módulo 2d — Conjunto de testes obrigatório (5 consultas fixas) e avaliação.

JULGAMENTO DE RELEVÂNCIA "A PRIORI":
    Para cada consulta, o grupo definiu ANTES de rodar os modelos quais
    documentos da base são relevantes para a NECESSIDADE DE INFORMAÇÃO
    descrita, lendo título e resumo de cada artigo (e não olhando o que os
    modelos devolvem). Só depois os modelos são executados e comparados com
    esse gabarito, usando:

        Precisão  = |relevantes ∩ recuperados| / |recuperados|
        Revocação = |relevantes ∩ recuperados| / |relevantes|

    Para o modelo vetorial, que devolve TODO documento com similaridade > 0,
    também calculamos P@5 e R@5 (considerando só os 5 primeiros do ranking),
    pois a qualidade dele está na ORDEM dos resultados.

Cobertura exigida pelo enunciado:
    - consulta com resultado vazio ............................ T3
    - consulta booleana com operadores aninhados ................ T2 (e T5)
    - consulta que expõe limitação de um dos modelos ............ T4 (booleano)
                                                                  T5 (vetorial)

Uso (gera o relatório em ./saida/avaliacao_consultas_teste.txt):
    python consultas_teste.py
"""

import os

import modelo_booleano

# Corte usado nas métricas P@k e R@k do modelo vetorial
K_CORTE = 5

CONSULTAS_TESTE = [
    {
        "id": "T1",
        "nome": "Governança em data lakes",
        "necessidade": "Artigos cujo foco é a governança de dados aplicada a data lakes.",
        "booleana": "governança AND (lake OR lakes)",
        "vetorial": "governança de dados em data lakes",
        "relevantes": {3, 9},
        "justificativa": {
            3: "governança de metadados e proveniência em data lakes (tema central)",
            9: "revisão sistemática de governança aplicada ao gerenciamento de data lakes",
        },
        "nao_relevantes_notaveis": {
            2: "arquitetura de data lake governamental; governança só citada como característica",
            7: "governança de dados, mas em sistemas-de-sistemas (não data lake)",
            17: "governança via linhagem de dados, sem data lake",
        },
        "demonstra": "Caso de sucesso: necessidade bem descrita pelos termos do vocabulário.",
    },
    {
        "id": "T2",
        "nome": "Desempenho de SGBDs NoSQL/NewSQL (aninhada)",
        "necessidade": "Avaliações experimentais de desempenho de SGBDs NoSQL ou NewSQL "
                       "(levantamentos/surveys não interessam).",
        "booleana": "(nosql OR newsql) AND (desempenho OR benchmarks) AND NOT levantamento",
        "vetorial": "desempenho de bancos NoSQL e NewSQL",
        "relevantes": {5, 18},
        "justificativa": {
            5: "compara o desempenho do MongoDB e do InfluxDB (NoSQL) com séries espaço-temporais",
            18: "compara produtos NewSQL usando benchmarks",
        },
        "nao_relevantes_notaveis": {
            1: "levantamento sobre adoção de NoSQL, sem avaliação de desempenho",
            14: "levantamento de SGBDs NoSQL multimodelo (survey)",
            16: "avaliação de desempenho, mas do PostgreSQL (relacional)",
        },
        "demonstra": "Consulta booleana com operadores ANINHADOS (OR dentro de AND, mais NOT). "
                     "Também expõe o problema de vocabulário: o resumo do doc 5 cita "
                     "'MongoDB' e 'InfluxDB', mas não a palavra 'NoSQL' (que só está no título).",
    },
    {
        "id": "T3",
        "nome": "Blockchain e criptografia (vazia)",
        "necessidade": "Uso de blockchain ou criptografia para proteger dados.",
        "booleana": "blockchain OR criptografia",
        "vetorial": "blockchain e criptografia de dados",
        "relevantes": set(),
        "justificativa": {},
        "nao_relevantes_notaveis": {},
        "demonstra": "Consulta com resultado VAZIO: nenhum artigo da base trata do tema; "
                     "o correto é nenhum dos dois modelos devolver documentos.",
    },
    {
        "id": "T4",
        "nome": "Proveniência / linhagem (limitação do booleano)",
        "necessidade": "Rastreabilidade do ciclo de vida dos dados: proveniência e linhagem de dados.",
        "booleana": "proveniência AND linhagem AND rastreabilidade",
        "vetorial": "proveniência, linhagem e rastreabilidade de dados",
        "relevantes": {3, 7, 17},
        "justificativa": {
            3: "governança de metadados com proveniência em data lakes",
            7: "governança baseada em dados de proveniência e rastreabilidade em SoS",
            17: "gestão da linhagem de dados com rastreabilidade",
        },
        "nao_relevantes_notaveis": {},
        "demonstra": "LIMITAÇÃO DO MODELO BOOLEANO: o AND é tudo-ou-nada. Cada artigo relevante "
                     "usa só parte dos termos, então a interseção é vazia (revocação 0), "
                     "enquanto o vetorial aceita casamento parcial e ranqueia os três.",
    },
    {
        "id": "T5",
        "nome": "Bancos relacionais (limitação do vetorial)",
        "necessidade": "Artigos que tratam de bancos de dados relacionais.",
        "booleana": "(relacional OR relacionais) AND (banco OR bancos)",
        "vetorial": "banco de dados relacional",
        "relevantes": {10, 16, 18},
        "justificativa": {
            10: "migração de bancos relacionais para grafos",
            16: "avaliação de desempenho do PostgreSQL (SGBD relacional)",
            18: "NewSQL como alternativa aos bancos relacionais (BDRs) em transações OLTP",
        },
        "nao_relevantes_notaveis": {
            1: "SGBDs NoSQL (cita 'banco de dados', mas não relacional)",
            11: "Data Mart / banco multidimensional",
            14: "SGBDs NoSQL multimodelo",
        },
        "demonstra": "LIMITAÇÃO DO MODELO VETORIAL (sem radicalização/stemming e sem semântica): "
                     "'relacional' e 'relacionais', 'banco' e 'bancos' são termos diferentes "
                     "no vetor. A consulta em linguagem natural casa apenas com 'banco', e "
                     "devolve artigos de NoSQL, perdendo os docs 10 e 18. No booleano o usuário "
                     "pode listar as variações com OR aninhado e acertar tudo.",
    },
]


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------

def calcular_metricas(recuperados: list, relevantes: set) -> dict:
    """
    Precisão e revocação de uma lista de DocIds recuperados.
    Quando o denominador é 0 a métrica fica indefinida (None), por exemplo:
    nada recuperado (precisão 0/0) ou nenhum relevante (revocação 0/0).
    """
    acertos = len(set(recuperados) & relevantes)
    precisao = acertos / len(recuperados) if recuperados else None
    revocacao = acertos / len(relevantes) if relevantes else None
    if precisao is not None and revocacao is not None and (precisao + revocacao) > 0:
        f1 = 2 * precisao * revocacao / (precisao + revocacao)
    else:
        f1 = None
    return {"acertos": acertos, "recuperados": len(recuperados),
            "precisao": precisao, "revocacao": revocacao, "f1": f1}


def formatar_metrica(valor) -> str:
    """Formata uma métrica (None = indefinida, exibida como 'n/d')."""
    return "n/d" if valor is None else f"{valor:.2f}"


def executar_teste(teste: dict, colecao, modelo_vetorial) -> dict:
    """Roda uma consulta de teste nos dois modelos e calcula as métricas contra o gabarito."""
    res_bool = modelo_booleano.buscar(teste["booleana"], colecao)
    res_vet = modelo_vetorial.buscar(teste["vetorial"])

    docs_bool = [d for d, _ in res_bool["resultados"]]
    docs_vet = [d for d, _ in res_vet["resultados"]]

    return {
        "teste": teste,
        "booleano": res_bool,
        "vetorial": res_vet,
        "metricas_booleano": calcular_metricas(docs_bool, teste["relevantes"]),
        "metricas_vetorial": calcular_metricas(docs_vet, teste["relevantes"]),
        "metricas_vetorial_k": calcular_metricas(docs_vet[:K_CORTE], teste["relevantes"]),
    }


def executar_todos(colecao, modelo_vetorial) -> list:
    """Roda as 5 consultas de teste."""
    return [executar_teste(t, colecao, modelo_vetorial) for t in CONSULTAS_TESTE]


# ---------------------------------------------------------------------------
# Relatório em texto (mesmo conteúdo exibido na aba "Consultas de teste")
# ---------------------------------------------------------------------------

def descrever_teste(r: dict, colecao) -> str:
    """Texto detalhado de uma consulta de teste: gabarito, resultados de cada modelo e métricas."""
    t = r["teste"]
    rel = t["relevantes"]

    def marca(doc_id):
        # ✔ = relevante segundo o gabarito; ✘ = não relevante
        return "✔" if doc_id in rel else "✘"

    def titulo(doc_id):
        return colecao.documentos[doc_id]["titulo"]

    linhas = [f"{t['id']} — {t['nome']}", "=" * 70,
              f"Necessidade de informação: {t['necessidade']}",
              f"O que demonstra: {t['demonstra']}", "",
              "JULGAMENTO DE RELEVÂNCIA (definido a priori, antes de rodar os modelos):"]
    if rel:
        for d in sorted(rel):
            linhas.append(f"   Doc {d:2d}  {titulo(d)}\n            -> {t['justificativa'].get(d, '')}")
    else:
        linhas.append("   (nenhum documento relevante na base)")
    if t["nao_relevantes_notaveis"]:
        linhas.append("   Considerados NÃO relevantes (apesar de terem termos parecidos):")
        for d, motivo in sorted(t["nao_relevantes_notaveis"].items()):
            linhas.append(f"   Doc {d:2d}  -> {motivo}")

    # --- Modelo booleano
    b = r["booleano"]
    mb = r["metricas_booleano"]
    linhas += ["", f"MODELO BOOLEANO — consulta: {t['booleana']}",
               f"   Expressão interpretada: {b['expressao']}"]
    for termo, docs in b["postings"].items():
        linhas.append(f"   {termo}: {docs if docs else '[]'}")
    if b["resultados"]:
        for d, _ in b["resultados"]:
            linhas.append(f"   {marca(d)} Doc {d:2d}  {titulo(d)}")
    else:
        linhas.append("   (nenhum documento recuperado)")
    linhas.append(f"   Precisão = {formatar_metrica(mb['precisao'])}   "
                  f"Revocação = {formatar_metrica(mb['revocacao'])}   "
                  f"F1 = {formatar_metrica(mb['f1'])}   "
                  f"({mb['acertos']} relevantes de {mb['recuperados']} recuperados)")

    # --- Modelo vetorial
    v = r["vetorial"]
    mv, mk = r["metricas_vetorial"], r["metricas_vetorial_k"]
    linhas += ["", f"MODELO ESPAÇO VETORIAL — consulta: {t['vetorial']}",
               f"   Termos após pré-processamento: {', '.join(v['termos']) or '(nenhum)'}"]
    if v["fora_vocab"]:
        linhas.append(f"   Fora do vocabulário da coleção: {', '.join(v['fora_vocab'])}")
    if v["resultados"]:
        for pos, (d, sim) in enumerate(v["resultados"], start=1):
            linhas.append(f"   {pos:2d}. {marca(d)} sim={sim:.4f}  Doc {d:2d}  {titulo(d)}")
    else:
        linhas.append("   (nenhum documento recuperado)")
    linhas.append(f"   Lista completa (sim > 0): Precisão = {formatar_metrica(mv['precisao'])}   "
                  f"Revocação = {formatar_metrica(mv['revocacao'])}   F1 = {formatar_metrica(mv['f1'])}")
    linhas.append(f"   Top-{K_CORTE}:                 P@{K_CORTE} = {formatar_metrica(mk['precisao'])}   "
                  f"R@{K_CORTE} = {formatar_metrica(mk['revocacao'])}")

    if not rel and not b["resultados"] and not v["resultados"]:
        linhas.append("\n   => Correto: não há relevantes e nenhum modelo devolveu documentos "
                      "(precisão e revocação ficam indefinidas, 0/0).")
    return "\n".join(linhas)


def tabela_resumo(resultados: list) -> str:
    """Tabela comparativa das métricas dos dois modelos nas 5 consultas."""
    cab = (f"{'Teste':<6}{'Relev.':>7} | {'Bool rec':>8}{'P':>6}{'R':>6} | "
           f"{'Vet rec':>8}{'P':>6}{'R':>6}{'P@' + str(K_CORTE):>7}{'R@' + str(K_CORTE):>7}")
    linhas = [cab, "-" * len(cab)]
    for r in resultados:
        mb, mv, mk = r["metricas_booleano"], r["metricas_vetorial"], r["metricas_vetorial_k"]
        linhas.append(
            f"{r['teste']['id']:<6}{len(r['teste']['relevantes']):>7} | "
            f"{mb['recuperados']:>8}{formatar_metrica(mb['precisao']):>6}{formatar_metrica(mb['revocacao']):>6} | "
            f"{mv['recuperados']:>8}{formatar_metrica(mv['precisao']):>6}{formatar_metrica(mv['revocacao']):>6}"
            f"{formatar_metrica(mk['precisao']):>7}{formatar_metrica(mk['revocacao']):>7}")
    linhas.append("n/d = indefinida (divisão 0/0: nada recuperado ou nenhum relevante)")
    return "\n".join(linhas)


def gerar_relatorio(colecao, modelo_vetorial) -> str:
    """Relatório completo: tabela resumo + detalhamento das 5 consultas."""
    resultados = executar_todos(colecao, modelo_vetorial)
    partes = ["AVALIAÇÃO DAS 5 CONSULTAS DE TESTE — Booleano × Espaço Vetorial", "",
              tabela_resumo(resultados), ""]
    partes += [descrever_teste(r, colecao) + "\n" for r in resultados]
    return "\n".join(partes)


if __name__ == "__main__":
    from colecao import Colecao, PASTA_RECUPERACAO
    from modelo_vetorial import ModeloVetorial

    colecao = Colecao()
    relatorio = gerar_relatorio(colecao, ModeloVetorial(colecao))

    pasta_saida = os.path.join(PASTA_RECUPERACAO, "saida")
    os.makedirs(pasta_saida, exist_ok=True)
    caminho = os.path.join(pasta_saida, "avaliacao_consultas_teste.txt")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(relatorio + "\n")
    print(relatorio)
    print(f"\nRelatório gravado em {caminho}")
