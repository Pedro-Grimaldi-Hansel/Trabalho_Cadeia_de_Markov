"""Exportação dos resultados e de um relatório HTML que funciona sem internet."""

import csv
from dataclasses import asdict
from html import escape
import json
from pathlib import Path
import platform

from .analise import classificar_cadeia, distribuicao_estacionaria
from .modelo import ESTADOS, NOMES, Distribuicao, Matriz, validar_matriz
from .simulacao import Experimento
from .visualizacao import diagrama_estados, grafico_comparacao, grafico_evolucao

ARQUIVOS = (
    "configuracao.json", "evolucao.csv", "trajetoria.csv", "comparacao.csv",
    "evolucao.svg", "comparacao.svg", "diagrama.svg", "relatorio.md", "relatorio.html",
    "transicoes_treino.csv", "previsoes_2025.csv", "avaliacao_historica.csv", "avaliacao_historica.json",
)
ROTULOS_METRICAS = {
    "markov": "Cadeia de Markov",
    "persistencia": "Repetir o estado de ontem",
    "frequencia_treino": "Frequências gerais do treino",
}
CSS = """
* { box-sizing: border-box; }
body { margin: 0; background: #f5f6f3; color: #243238; font: 16px/1.65 "Segoe UI", Arial, sans-serif; }
main { max-width: 1100px; margin: 40px auto; padding: 48px 64px; background: white; }
h1 { font-size: clamp(30px, 4vw, 44px); line-height: 1.15; margin: 12px 0 22px; }
h2 { font-size: 25px; margin: 42px 0 16px; }
p { max-width: 86ch; overflow-wrap: anywhere; }
.rotulo { color: #087d81; font-weight: 700; letter-spacing: 2px; font-size: 13px; }
figure { margin: 28px 0; } svg { width: 100%; height: auto; }
figcaption { color: #58676e; font-size: 14px; }
.tabela { overflow-x: auto; margin: 20px 0; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 11px 14px; text-align: right; border-bottom: 1px solid #dce2e3; white-space: nowrap; }
th { background: #edf3f3; } th:first-child, td:first-child { text-align: left; white-space: normal; min-width: 110px; }
tbody tr:nth-child(even) { background: #f8faf9; }
a { color: #076e76; } code { font-family: Consolas, monospace; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f0f3f2; padding: 20px; font-size: 14px; }
@media(max-width: 700px) { main { margin: 0; padding: 28px 20px; } th, td { padding: 8px; } }
@media print { body { background: white; } main { margin: 0; padding: 0; }
h2 { break-after: avoid; } figure, tr { break-inside: avoid; } thead { display: table-header-group; } }
"""


def numero(valor: float, casas: int = 2) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def percentual(valor: float) -> str:
    return numero(valor * 100) + "%"


def _csv(caminho: Path, cabecalho, linhas) -> None:
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)


class _Documento:
    """Mantém HTML e Markdown com o mesmo conteúdo."""

    def __init__(self):
        self.md = []
        self.html = []

    def titulo(self, texto: str, nivel: int = 2) -> None:
        self.md.extend(("#" * nivel + " " + texto, ""))
        self.html.append(f"<h{nivel}>{escape(texto)}</h{nivel}>")

    def paragrafo(self, texto: str) -> None:
        self.md.extend((texto, ""))
        self.html.append(f"<p>{escape(texto)}</p>")

    def tabela(self, cabecalho, linhas) -> None:
        self.md.extend(("| " + " | ".join(cabecalho) + " |",
                        "| " + " | ".join("---" for _ in cabecalho) + " |"))
        self.md.extend("| " + " | ".join(linha) + " |" for linha in linhas)
        self.md.append("")
        self.html.append('<div class="tabela"><table><thead><tr>'
                         + "".join(f'<th scope="col">{escape(x)}</th>' for x in cabecalho)
                         + "</tr></thead><tbody>"
                         + "".join("<tr>" + "".join(f"<td>{escape(x)}</td>" for x in linha) + "</tr>" for linha in linhas)
                         + "</tbody></table></div>")

    def figura(self, legenda: str, nome: str, svg: str) -> None:
        self.md.extend((f"![{legenda}]({nome})", ""))
        self.html.append(f"<figure>{svg}<figcaption>{escape(legenda)}</figcaption></figure>")

    def codigo(self, texto: str) -> None:
        cerca = chr(96) * 3
        self.md.extend((cerca + "text", texto, cerca, ""))
        self.html.append(f"<pre><code>{escape(texto)}</code></pre>")

    def links(self, itens) -> None:
        self.md.extend(("- " + f"[{rotulo}]({url})" for rotulo, url in itens))
        self.md.append("")
        self.html.append("<ul>" + "".join(f'<li><a href="{escape(url, quote=True)}">{escape(rotulo)}</a></li>'
                                         for rotulo, url in itens) + "</ul>")


def exportar(
    pasta: Path,
    inicial: Distribuicao,
    historico: list[Distribuicao],
    caminho: list[str],
    experimentos: list[Experimento],
    selecionado: Experimento,
    *,
    matriz: Matriz,
    contexto: dict,
    demonstracao: bool = False,
) -> list[Path]:
    matriz = validar_matriz(matriz)
    fonte, ajuste = contexto["fonte"], contexto["ajuste"]
    if matriz != ajuste["matriz"]:
        raise ValueError("A matriz do cenário deve corresponder à matriz estimada do histórico.")
    estacionaria = distribuicao_estacionaria(matriz)
    classificacao = classificar_cadeia(matriz)
    dias = len(historico) - 1
    resumo_ajuste = {chave: valor for chave, valor in ajuste.items() if chave != "previsoes"}
    pasta.mkdir(parents=True, exist_ok=True)
    configuracao = {
        "local": fonte["local"], "estados": ESTADOS, "nomes": NOMES, "matriz": matriz,
        "distribuicao_inicial": inicial, "dias": dias, "repeticoes": selecionado.repeticoes,
        "semente": selecionado.semente, "demonstracao": demonstracao,
        "python": platform.python_version(), "implementacao_python": platform.python_implementation(),
        "gerador_aleatorio": "random.Random; choices; um gerador local por experimento",
        "classificacao": asdict(classificacao), "distribuicao_estacionaria": estacionaria,
        "fonte": fonte, "ajuste": resumo_ajuste, "experimentos": [asdict(e) for e in experimentos],
    }
    for nome, conteudo in (("configuracao.json", configuracao),
                           ("avaliacao_historica.json", {**resumo_ajuste, "fonte": fonte})):
        (pasta / nome).write_text(json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _csv(pasta / "evolucao.csv", ("dia", *ESTADOS), ((dia, *vetor) for dia, vetor in enumerate(historico)))
    _csv(pasta / "trajetoria.csv", ("dia", "estado", "descricao"),
         ((dia, estado, NOMES[ESTADOS.index(estado)]) for dia, estado in enumerate(caminho)))
    _csv(pasta / "comparacao.csv",
         ("dias", "repeticoes", "semente", "estado", "probabilidade_teorica", "contagem",
          "frequencia_simulada", "erro_absoluto", "erro_pontos_percentuais", "erro_padrao_teorico"),
         ((e.dias, e.repeticoes, e.semente, estado, e.teorica[i], e.contagens[i], e.frequencias[i],
           e.erros[i], 100 * e.erros[i], e.erros_padrao[i]) for e in experimentos for i, estado in enumerate(ESTADOS)))
    _csv(pasta / "transicoes_treino.csv", ("origem", "destino", "contagem", "total_saidas_origem", "probabilidade"),
         ((origem, destino, ajuste["contagens_transicoes"][i][j], sum(ajuste["contagens_transicoes"][i]), matriz[i][j])
          for i, origem in enumerate(ESTADOS) for j, destino in enumerate(ESTADOS)))
    _csv(pasta / "previsoes_2025.csv", ("data", "estado_anterior", "observado", "prob_E", "prob_N", "prob_C", "previsto"),
         ((p["data"], p["estado_anterior"], p["observado"], *p["probabilidades"], p["previsto"]) for p in ajuste["previsoes"]))
    _csv(pasta / "avaliacao_historica.csv", ("modelo", "dias_avaliados", "acuracia", "brier"),
         ((nome, ajuste["teste"]["previsoes_avaliadas"], valores["acuracia"], valores["brier"])
          for nome, valores in ajuste["metricas"].items()))
    figuras = {"evolucao.svg": grafico_evolucao(historico), "comparacao.svg": grafico_comparacao(selecionado),
               "diagrama.svg": diagrama_estados(matriz)}
    for nome, conteudo in figuras.items():
        (pasta / nome).write_text(conteudo + "\n", encoding="utf-8")

    doc = _Documento()
    doc.titulo("Cadeia de Markov para o tempo em Juiz de Fora", 1)
    doc.titulo("Objetivo")
    doc.paragrafo("Estimar uma cadeia de Markov de três estados a partir do histórico meteorológico de Juiz de Fora, "
                  "calcular a evolução das probabilidades e comparar trajetórias simuladas com a teoria. "
                  "A capacidade de previsão é avaliada separadamente em dias posteriores ao treino.")
    treino, teste = ajuste["treino"], ajuste["teste"]
    doc.titulo("Fonte e período dos dados")
    doc.paragrafo(f"Fonte: Open-Meteo / ERA5. Local: {fonte['local']}. {fonte['natureza']} "
                  "A célula regional representa uma área próxima da cidade, sem corresponder a uma estação local.")
    doc.paragrafo(f"Base: {fonte['inicio']} a {fonte['fim']}, com {fonte['dias']} dias. "
                  f"Treino: {treino['inicio']} a {treino['fim']}, com {treino['dias_validos']} dias válidos e "
                  f"{ajuste['transicoes_treino']} transições. Teste: {teste['inicio']} a {teste['fim']}, "
                  f"com {teste['previsoes_avaliadas']} previsões de um dia.")
    doc.paragrafo("Seis anos são uma escolha prática para este trabalho: cinco ciclos anuais no treino e um ciclo inteiro "
                  "no teste. Não existe um número universal ideal. É necessário considerar as contagens por estado, "
                  "a sazonalidade e as lacunas, além do número total de registros.")
    doc.paragrafo(f"Qualidade da base: {ajuste['dias_ausentes']} datas ausentes e "
                  f"{ajuste['dias_sem_classificacao']} dias sem classificação. Dados ausentes não são tratados como "
                  "dias secos, e pares separados por lacunas não são contados.")
    doc.titulo("Classificação dos dias")
    doc.paragrafo(ajuste["regra_classificacao"])
    doc.paragrafo("Cada registro fornece precipitação acumulada do dia, em milímetros, e nebulosidade média, em porcentagem. "
                  "Primeiro se verifica a chuva; depois, nos dias com menos de 1 mm, a nebulosidade separa E e N. "
                  "Os estados são categorias operacionais e simplificam a variação do tempo ao longo de um mesmo dia.")
    doc.titulo("Estimação da matriz")
    doc.paragrafo("A sequência de uso dos dados é: registro diário → classificação E/N/C → contagem das mudanças "
                  "entre dias consecutivos do treino → divisão pelo total de saídas de cada origem. "
                  "P(i,j) = contagem(i → j) / soma das saídas de i. "
                  "Um treino de 1.827 dias consecutivos tem 1.826 pares, pois o último dia não tem sucessor dentro do treino. "
                  "Nenhum dia de 2025 entra nessas contagens e não é aplicada suavização.")
    doc.tabela(["Origem / próximo", "E", "N", "C", "Total de saídas"],
               [[ESTADOS[i], *map(str, linha), str(sum(linha))] for i, linha in enumerate(ajuste["contagens_transicoes"])])
    total_e = sum(ajuste["contagens_transicoes"][0])
    n_ec = ajuste["contagens_transicoes"][0][2]
    doc.paragrafo(f"Exemplo: das {total_e} saídas de dias E, {n_ec} foram seguidas por C. "
                  f"Assim, P(E → C) = {n_ec}/{total_e} = {percentual(matriz[0][2])}. "
                  "A mesma divisão fornece as nove probabilidades. Linhas representam o estado atual e colunas o próximo dia.")
    doc.tabela(["Atual / próximo", "E", "N", "C"],
               [[ESTADOS[i], *[percentual(p) for p in linha]] for i, linha in enumerate(matriz)])
    doc.figura("Transições entre os três estados e suas probabilidades.", "diagrama.svg", figuras["diagrama.svg"])
    doc.paragrafo("Cada linha soma 1, pois o próximo estado deve ser uma das três categorias. "
                  f"Cadeia irredutível: {'sim' if classificacao.irredutivel else 'não'}; "
                  f"aperiódica: {'sim' if classificacao.aperiodica else 'não'}; "
                  f"estados absorventes: {', '.join(classificacao.absorventes) or 'nenhum'}. "
                  "Irredutibilidade significa que é possível chegar de qualquer estado a qualquer outro. "
                  "Nesta matriz, as probabilidades de permanência positivas tornam os períodos iguais a 1.")

    inicial_texto = "; ".join(f"{e}: {percentual(p)}" for e, p in zip(ESTADOS, inicial))
    final_texto = "; ".join(f"{e}: {percentual(p)}" for e, p in zip(ESTADOS, historico[-1]))
    doc.titulo("Cálculo analítico e parâmetros")
    doc.paragrafo(f"Distribuição inicial: {inicial_texto}. Horizonte: {dias} transições diárias. "
                  f"Trajetórias no cenário principal: {selecionado.repeticoes}. Semente: {selecionado.semente}. "
                  "O cenário começa na distribuição escolhida e não representa o tempo atual da cidade.")
    doc.paragrafo("O cálculo usa vetores-linha: π(n + 1) = π(n)P, ou π(n) = π(0)Pⁿ. "
                  "O dia zero antecede qualquer transição. A hipótese de Markov considera que, dado o estado atual, "
                  "a distribuição do próximo estado não depende dos dias anteriores. A mesma matriz é usada em todos os dias.")
    doc.figura("Evolução calculada das probabilidades a partir da distribuição inicial.", "evolucao.svg", figuras["evolucao.svg"])
    doc.paragrafo(f"Distribuição calculada no dia {dias}: {final_texto}.")
    doc.titulo("Simulação e comparação com a teoria")
    doc.paragrafo("Cada trajetória sorteia o estado inicial e depois segue a linha da matriz referente ao estado atual. "
                  "Uma trajetória com n transições contém n + 1 estados, incluindo o dia zero. "
                  "As frequências são obtidas contando somente o estado final de cada trajetória independente.")
    trajeto = " → ".join(caminho[:41]) + (" → … (continua no CSV)" if len(caminho) > 41 else "")
    doc.paragrafo(f"Trajetória de exemplo: {trajeto}.")
    doc.figura("Probabilidades calculadas e frequências simuladas no cenário principal.", "comparacao.svg", figuras["comparacao.svg"])
    doc.tabela(["Dias", "Trajetórias", "Estado", "Teoria", "Simulação", "Erro em p.p."],
               [[str(e.dias), str(e.repeticoes), estado, percentual(e.teorica[i]), percentual(e.frequencias[i]),
                 numero(100 * e.erros[i], 3)] for e in experimentos for i, estado in enumerate(ESTADOS)])
    doc.paragrafo(f"Foram exportados {len(experimentos)} cenários. O maior erro absoluto no cenário principal é "
                  f"{numero(100 * max(selecionado.erros), 3)} pontos percentuais. Esse erro compara sorteios com a teoria "
                  "da mesma matriz e não mede a capacidade de prever o tempo observado.")
    doc.paragrafo("As trajetórias são sintéticas. Usar 10.000 trajetórias não acrescenta 10.000 registros meteorológicos "
                  "ao histórico. Mais trajetórias reduzem a variabilidade esperada, mas não garantem menor erro em cada execução. "
                  "O erro padrão de uma frequência é √(p(1−p)/M), onde M é a quantidade de trajetórias. "
                  "Cada cenário reinicia seu gerador com a mesma semente; o conjunto de cenários não é tratado como ensaios independentes. "
                  "A mesma configuração no mesmo ambiente reproduz os sorteios.")

    doc.titulo("Comportamento de longo prazo")
    doc.paragrafo("A distribuição estacionária π* satisfaz π*P = π* e soma 1. "
                  "Como a cadeia é finita, irredutível e aperiódica, a distribuição converge para esse equilíbrio "
                  "a partir de qualquer condição inicial. A tabela separa o equilíbrio do modelo das proporções observadas no teste.")
    n_teste = len(ajuste["previsoes"])
    observadas = [sum(p["observado"] == estado for p in ajuste["previsoes"]) / n_teste for estado in ESTADOS]
    doc.tabela(["Estado", "Equilíbrio do modelo", "Observado em 2025"],
               [[NOMES[i], percentual(estacionaria[i]), percentual(observadas[i])] for i in range(3)])
    doc.paragrafo(f"A probabilidade de um dia C ser seguido por C é {percentual(matriz[2][2])}, "
                  f"e a participação de C no equilíbrio é {percentual(estacionaria[2])}. "
                  "São medidas diferentes: a primeira condiciona a previsão a hoje estar chuvoso; a segunda descreve "
                  "o limite de muitas transições. O equilíbrio não é a porcentagem de dias chuvosos observada em um ano específico "
                  "nem uma previsão para amanhã. As frequências de visitas numa trajetória e os estados finais de várias trajetórias também são medidas diferentes.")

    doc.titulo("Avaliação em 2025")
    doc.paragrafo(ajuste["metodo_avaliacao"])
    doc.paragrafo("A matriz permanece fixa durante o teste. Para prever cada dia, usa-se o estado observado no dia anterior. "
                  "Isso é uma avaliação retrospectiva de um passo, e não uma previsão única de todo o ano. "
                  "A persistência aposta com probabilidade 1 na categoria de ontem. A referência de frequências "
                  "usa a proporção de cada estado no treino, sem considerar ontem.")
    doc.tabela(["Método", "Acurácia", "Brier — menor é melhor"],
               [[ROTULOS_METRICAS[nome], percentual(valores["acuracia"]), numero(valores["brier"], 4)]
                for nome, valores in ajuste["metricas"].items()])
    doc.paragrafo("Acurácia é a fração dos dias em que a categoria de maior probabilidade coincide com a observada. "
                  "Em caso de empate, a escolha segue a ordem E, N, C. Brier avalia o vetor inteiro de probabilidades: "
                  "para cada dia, soma-se (probabilidade − indicador observado)² nos três estados e depois calcula-se "
                  "a média dos dias. O indicador vale 1 para o estado observado e 0 para os outros; a escala usada vai de 0 a 2.")
    if all(max(range(3), key=lambda j: matriz[i][j]) == i for i in range(3)):
        doc.paragrafo("A categoria mais provável nesta matriz é sempre a de ontem: "
                      + "; ".join(f"{e} → {e}: {percentual(matriz[i][i])}" for i, e in enumerate(ESTADOS))
                      + ". Por isso Markov e persistência produzem as mesmas categorias e empatam na acurácia. "
                      "Na linha de N, a maior probabilidade pode ser menor que 50% e ainda superar as outras duas. "
                      "O empate não indica um erro de cálculo. As probabilidades são diferentes, pois Markov admite outros estados "
                      "e a persistência atribui certeza à permanência.")
    doc.paragrafo("O Brier permite distinguir essas probabilidades mesmo quando as categorias previstas coincidem. "
                  "Os resultados descrevem este período e esta classificação; não foi realizado um teste de significância "
                  "e não se garante desempenho igual em outros anos.")

    doc.titulo("Validação matemática e interpretação")
    doc.paragrafo("A validação verifica probabilidades entre 0 e 1, soma das linhas, orientação da multiplicação, "
                  "conservação da massa de probabilidade e a identidade π*P = π*. Os testes incluem exemplos calculados "
                  "à mão, trajetórias determinísticas, reprodutibilidade, separação temporal e coerência das exportações. "
                  "Eles fornecem evidências de correção da implementação, sem provar ausência de todo defeito.")
    doc.paragrafo("Correção matemática, proximidade entre teoria e simulação e desempenho preditivo são questões distintas. "
                  "Um programa pode executar corretamente uma cadeia de Markov e ainda ter capacidade limitada para prever o tempo. "
                  "A avaliação histórica mede esse desempenho; aumentar o número de sorteios não corrige hipóteses inadequadas do modelo.")
    doc.titulo("Relação com Linguagens Formais e Autômatos")
    doc.paragrafo("Os estados e suas transições formam um grafo finito; cada trajetória é um caminho nesse grafo. "
                  "As arestas possuem probabilidades, formando uma cadeia de Markov. Um reconhecedor de linguagem exigiria "
                  "definir adicionalmente um alfabeto de entrada e condições de aceitação, que não fazem parte deste modelo meteorológico.")
    doc.titulo("Limitações")
    doc.paragrafo("A base é uma reanálise regional, não uma validação independente contra medições de uma estação local. "
                  "Os três estados e os limites de chuva e nebulosidade são escolhas deste trabalho. "
                  "A matriz anual constante mistura períodos do ano e considera apenas o estado do dia anterior, "
                  "sem modelar diretamente temperatura, pressão, umidade ou vento. "
                  "Os resultados têm finalidade acadêmica e não constituem uma previsão meteorológica operacional.")
    doc.titulo("Conclusão")
    doc.paragrafo("A cadeia estimada relaciona registros diários, probabilidades de transição, evolução analítica e simulação. "
                  f"No teste de 2025, a acurácia de Markov foi {percentual(ajuste['metricas']['markov']['acuracia'])}, "
                  f"com Brier {numero(ajuste['metricas']['markov']['brier'], 4)}. "
                  "O empate de acurácia com persistência limita a evidência de ganho ao escolher uma única categoria. "
                  "A avaliação das probabilidades deve considerar o Brier e as duas referências apresentadas.")
    doc.paragrafo("Seguir a teoria não garante boa previsão. O resultado é útil para demonstrar tanto o funcionamento "
                  "quanto o alcance de uma cadeia de Markov de primeira ordem com três estados. "
                  "Modelos por estação do ano ou com memória maior exigiriam avaliação própria: as escolhas devem ser feitas "
                  "com validação dentro do treino e um teste final reservado. Uma comparação com uma estação local "
                  "também ajudaria a avaliar a representação meteorológica dos dados.")

    doc.titulo("Como reproduzir")
    comando = (f"python -m src.main --dias {dias} --inicial {' '.join(str(p) for p in inicial)} "
               f"--repeticoes {selecionado.repeticoes} --semente {selecionado.semente}" + (" --demo" if demonstracao else ""))
    doc.paragrafo(f"Execute na raiz do projeto com Python 3.10 ou superior. Ambiente desta execução: Python {platform.python_version()}. "
                  "A execução usa a base local e funciona sem internet. O JSON bruto, o CSV diário e os metadados da fonte "
                  "ficam em dados/juiz_de_fora; o hash SHA-256 confere a integridade do arquivo obtido do provedor.")
    doc.codigo(comando)
    doc.paragrafo("Para verificar os cálculos e a integração, execute: python -m unittest discover -s tests -v. "
                  "Os CSVs usam UTF-8 com BOM, vírgula como separador e ponto decimal. Probabilidades variam entre 0 e 1; "
                  "o erro em pontos percentuais é o erro absoluto multiplicado por 100. "
                  "Implementações ou versões diferentes do Python podem produzir sorteios diferentes.")
    doc.links([(nome, nome) for nome in ARQUIVOS if nome not in ("relatorio.html", "relatorio.md")])
    doc.titulo("Fontes")
    doc.links([
        ("Open-Meteo — documentação do histórico meteorológico", fonte["documentacao"]),
        ("ERA5 — Copernicus/ECMWF, DOI 10.24381/cds.adbb2d47", "https://doi.org/10.24381/cds.adbb2d47"),
        ("Licença dos dados: CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
    ])
    doc.paragrafo("Dados disponibilizados por Open-Meteo, com atribuição a Copernicus/ECMWF ERA5. "
                  "Os campos diários foram selecionados e classificados pelos critérios descritos neste relatório. "
                  "Consulta, coordenadas, data de obtenção e hash estão registrados nos metadados.")

    (pasta / "relatorio.md").write_text("\n".join(doc.md), encoding="utf-8")
    html = ('<!doctype html>\n<html lang="pt-BR"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Cadeia de Markov — Juiz de Fora</title><style>' + CSS + '</style></head><body><main>'
            '<div class="rotulo">LFA · JUIZ DE FORA</div>' + "\n".join(doc.html) + '</main></body></html>\n')
    (pasta / "relatorio.html").write_text(html, encoding="utf-8")
    return [pasta / nome for nome in ARQUIVOS]
