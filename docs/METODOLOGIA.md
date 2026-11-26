# Metodologia — cadeia de Markov para Juiz de Fora

## Objetivo e unidade de análise

O projeto representa o tempo diário em três estados: ensolarado (E), nublado (N) e chuvoso (C). Um passo da cadeia corresponde à passagem de um dia para o seguinte. O objetivo é estimar as probabilidades dessas transições, calcular sua evolução e avaliar previsões retrospectivas de um dia.

## Fonte e recorte temporal

A entrada contém 2.192 registros diários, de 1º de janeiro de 2020 a 31 de dezembro de 2025. Os campos são precipitação acumulada, em milímetros, e nebulosidade média, em porcentagem, obtidos da [Historical Weather API do Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api), com o modelo ERA5.

As coordenadas consultadas são latitude −21,76417 e longitude −43,35028, com fuso `America/Sao_Paulo`. A célula retornada pelo provedor tem latitude −21,75 e longitude −43,25. Ela representa uma área regional próxima da cidade. ERA5 é uma reanálise que combina observações e modelagem; os valores não são medições diretas de uma estação local.

O arquivo `dados/juiz_de_fora/fonte.json` registra a consulta, as coordenadas, a data de obtenção, a licença e o hash SHA-256 da resposta JSON. O programa confere o hash, as unidades, as datas e a correspondência entre os valores brutos e o CSV classificado antes de realizar a análise.

| Uso | Período | Dias | Transições ou previsões |
| --- | --- | ---: | ---: |
| Estimação | 2020–2024 | 1.827 | 1.826 transições |
| Avaliação | 2025 | 365 | 365 previsões de um dia |

Os cinco anos de treino cobrem vários ciclos anuais e fornecem centenas de saídas por estado. Esse tamanho é uma escolha prática para o trabalho; não há uma quantidade universal ideal. O ano de teste cobre um ciclo anual completo e não participa da estimação da matriz.

## Classificação dos dias

As regras são aplicadas nesta ordem:

1. Precipitação de pelo menos 1 mm: **C**.
2. Precipitação menor que 1 mm e nebulosidade média de até 50%: **E**.
3. Precipitação menor que 1 mm e nebulosidade média acima de 50%: **N**.

São critérios operacionais escolhidos para o trabalho, sem equivaler a categorias oficiais do provedor. E pode incluir dias parcialmente nublados. Uma categoria diária também simplifica mudanças que acontecem dentro do mesmo dia.

Um dia com informação necessária ausente não recebe estado. Pares separados por lacunas não são contados, e dados ausentes não viram dias secos. Valores negativos, não finitos ou nebulosidade acima de 100% são rejeitados. A base fornecida não possui datas ausentes nem dias sem classificação.

## Estimação por contagens

A matriz segue a ordem E, N, C. A linha indica o estado do dia atual e a coluna o do próximo dia. Para cada par de dias consecutivos do treino, incrementa-se uma contagem de origem e destino:

`P(i,j) = contagem(i → j) / total de saídas de i`

| Origem / destino | E | N | C | Total de saídas |
| --- | ---: | ---: | ---: | ---: |
| E | 344 | 123 | 77 | 544 |
| N | 141 | 217 | 138 | 496 |
| C | 59 | 156 | 571 | 786 |

Por exemplo, `P(E → C) = 77/544 ≈ 14,15%`. O último dia do treino não possui sucessor dentro do treino; por isso 1.827 dias consecutivos fornecem 1.826 pares. Cada linha é dividida por seu próprio total, sem suavização. Se um estado não tiver nenhuma saída no treino, a estimação é rejeitada, pois não há informação para essa linha.

| Atual / próximo | E | N | C |
| --- | ---: | ---: | ---: |
| E | 63,24% | 22,61% | 14,15% |
| N | 28,43% | 43,75% | 27,82% |
| C | 7,51% | 19,85% | 72,65% |

Os valores exibidos estão arredondados; os cálculos usam as razões completas entre contagens. Cada linha soma 1 dentro da tolerância numérica de `1e-9`.

## Cálculo analítico

O modelo usa vetores-linha. A distribuição inicial `π(0)` contém as probabilidades dos estados antes de qualquer transição:

`π(n + 1) = π(n)P`, portanto `π(n) = π(0)Pⁿ`.

Partindo de E, `π(0) = [1, 0, 0]`. No primeiro dia, o vetor é a linha E da matriz. No segundo, as probabilidades são aproximadamente `[47,48%, 27,00%, 25,52%]`. Um componente pode ser conferido manualmente, com coeficientes arredondados:

```text
P(E no dia 2) ≈ 0,632353 × 0,632353
              + 0,226103 × 0,284274
              + 0,141544 × 0,075064
              ≈ 0,474770
```

Cada termo representa um caminho de dois passos até E, passando por E, N ou C no primeiro dia.

## Simulação

Cada trajetória sorteia um estado inicial conforme `π(0)` e depois sorteia o próximo estado conforme a linha da matriz correspondente ao atual. O gerador é `random.Random`, com semente configurável. Uma trajetória de n transições contém n + 1 estados.

Para comparar com `π(n)`, o programa reinicia o estado inicial a cada trajetória independente e conta somente o estado final. A frequência de visitas durante uma trajetória inteira é outra medida.

O erro absoluto é `|frequência simulada − probabilidade teórica|`. Em pontos percentuais, multiplica-se por 100. O erro padrão teórico de uma frequência é `sqrt(p(1−p)/M)`, onde M é a quantidade de trajetórias. Mais trajetórias reduzem a variabilidade esperada, sem garantir uma redução do erro em toda execução. A grade de cenários reutiliza a mesma semente por cenário e não é tratada como múltiplos ensaios independentes para medir erro médio.

Trajetórias simuladas são sintéticas. Aumentar M não aumenta a quantidade de registros meteorológicos nem melhora, por si só, as hipóteses do modelo.

## Distribuição estacionária

O programa resolve `π*P = π*`, com soma dos componentes igual a 1, por eliminação com pivoteamento. A solução aproximada é `[29,79%, 27,16%, 43,04%]`.

A cadeia estimada é finita, irredutível e aperiódica: todos os estados se comunicam e as permanências positivas tornam os períodos iguais a 1. Assim, a distribuição converge para esse equilíbrio a partir de qualquer condição inicial.

O equilíbrio é uma propriedade da matriz mantida constante indefinidamente. Ele não é a proporção observada em cada ano, nem a previsão de amanhã. A probabilidade de amanhã depende da distribuição inicial ou do estado observado hoje.

## Avaliação temporal

A matriz é estimada somente com 2020–2024 e permanece fixa ao avaliar 2025. Para cada alvo de teste, o contexto é o estado observado no dia anterior. O dia 1º de janeiro pode usar 31 de dezembro do treino como contexto, sem usar o alvo para ajustar a matriz. As datas não são embaralhadas.

É uma avaliação retrospectiva de um passo: o modelo recebe o estado de ontem em cada previsão. Não é uma projeção única de 365 dias a partir do começo do ano.

As referências são persistência, que atribui probabilidade 1 à categoria de ontem, e frequências gerais dos estados no treino, que não consideram ontem.

| Método | Acurácia | Brier |
| --- | ---: | ---: |
| Cadeia de Markov | 56,16% | 0,5778 |
| Persistência | 56,16% | 0,8767 |
| Frequências gerais do treino | 34,52% | 0,6783 |

A acurácia conta o acerto da categoria de maior probabilidade. Empates são resolvidos na ordem E, N, C. Na matriz estimada, o maior valor de cada linha é sua diagonal: Markov e persistência escolhem a mesma categoria e, por isso, têm a mesma acurácia.

O Brier usa o vetor inteiro: calcula-se a soma de `(p − indicador observado)²` para E, N e C em cada dia, depois a média entre os dias. O indicador é 1 para o estado observado e 0 para os demais. A escala adotada vai de 0 a 2; menor é melhor. O Brier diferencia métodos que escolhem a mesma categoria, mas atribuem probabilidades diferentes.

## Validação e limites de interpretação

Os testes verificam exemplos numéricos conhecidos, orientação da multiplicação, conservação das probabilidades, solução estacionária, classificação da cadeia, entradas inválidas, trajetórias determinísticas, reprodução dos sorteios, integridade da base e exportação. Também verificam que alterar os dados de teste não altera a matriz estimada.

Essas verificações fornecem evidências de correção da implementação, sem provar ausência de todo defeito. A proximidade entre teoria e simulação também não demonstra boa capacidade de previsão: ambas seguem a mesma matriz. O desempenho preditivo é medido separadamente no teste de 2025.

O modelo tem três estados, usa memória de um dia e uma matriz constante ao longo do ano. Os limites de classificação são escolhas do trabalho, e a reanálise representa uma célula regional. Um ano de teste não demonstra superioridade em todos os períodos; não foi realizado teste de significância. Não há validação independente contra uma estação local. A finalidade é acadêmica.

## Relação com LFA

Os estados e as transições formam um grafo finito, e cada trajetória corresponde a um caminho nesse grafo. As transições carregam probabilidades. Um reconhecedor de linguagem precisaria também de alfabeto de entrada e condições de aceitação, que não estão definidos neste modelo meteorológico.

## Atribuição

Dados por [Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api) e [ERA5 — Copernicus/ECMWF](https://doi.org/10.24381/cds.adbb2d47), disponibilizados pelo Open-Meteo sob [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Os campos diários foram selecionados e classificados pelos critérios descritos acima.
