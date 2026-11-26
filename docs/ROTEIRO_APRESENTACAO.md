# Roteiro de apresentação — tempo em Juiz de Fora

Demonstração de aproximadamente oito minutos, usando o relatório gerado pelo programa.

## 1. Objetivo e estados

“O trabalho estima uma cadeia de Markov para o tempo em Juiz de Fora. Os estados são ensolarado, nublado e chuvoso. Cada passo representa um dia, e a hipótese é que a distribuição do dia seguinte depende apenas do estado atual.”

Explique que os dados são uma reanálise Open-Meteo/ERA5, que combina observações e modelos para uma área próxima da cidade. Não são medições diretas de uma estação local.

## 2. Dados e classificação

“A base contém 2.192 dias. Usamos 2020–2024 para estimar a matriz e reservamos 2025 para avaliação. O teste não participa da estimação.”

Apresente as regras: precipitação de pelo menos 1 mm define C; nos demais dias, nebulosidade média de até 50% define E, e acima disso define N. Declare que são critérios do trabalho e que E pode incluir dias parcialmente nublados.

## 3. Das contagens à matriz

Mostre a tabela de contagens no relatório:

- Saídas de E: 344 para E, 123 para N e 77 para C; total 544.
- Saídas de N: 141 para E, 217 para N e 138 para C; total 496.
- Saídas de C: 59 para E, 156 para N e 571 para C; total 786.

“Para calcular cada probabilidade, dividimos a contagem da transição pelo total de saídas da origem. Assim, P(E → C) = 77/544, aproximadamente 14,15%.”

Mostre que cada linha soma 1 e que linhas são origens, enquanto colunas são destinos. Explique que 1.827 dias consecutivos de treino fornecem 1.826 transições.

## 4. Evolução e simulação

“O cálculo usa π(n + 1) = π(n)P. Começando em E, o primeiro dia tem aproximadamente 63,24% E, 22,61% N e 14,15% C. No segundo dia, são 47,48%, 27,00% e 25,52%.”

Mostre o gráfico de evolução e uma trajetória sorteada. Diferencie o vetor de probabilidades de uma sequência particular de estados.

“Na simulação, reiniciamos a condição inicial para cada trajetória e contamos seu último estado. As trajetórias são sintéticas; 10.000 trajetórias não representam 10.000 registros meteorológicos.”

Explique que o erro entre teoria e simulação oscila com os sorteios e não mede a qualidade da previsão meteorológica.

## 5. Longo prazo

Mostre o equilíbrio aproximado: 29,79% E, 27,16% N e 43,04% C.

“A distribuição estacionária satisfaz π*P = π*. Como a cadeia é finita, irredutível e aperiódica, a distribuição converge para esse equilíbrio. Isso vale se a mesma matriz continuar sendo aplicada.”

Destaque que 43,04% no equilíbrio não significa que essa foi a proporção de dias chuvosos observada em 2025, nem que amanhã terá essa probabilidade de chuva.

## 6. Avaliação e conclusão

Mostre a tabela de avaliação:

| Método | Acerto da categoria | Brier |
| --- | ---: | ---: |
| Markov | 56,16% | 0,5778 |
| Persistência | 56,16% | 0,8767 |
| Frequências do treino | 34,52% | 0,6783 |

“A maior probabilidade de cada linha está na permanência no mesmo estado. Por isso Markov e repetir ontem escolhem as mesmas categorias e empatam no acerto. O Brier considera todas as probabilidades, na escala de 0 a 2; menor é melhor.”

“Os testes sustentam os cálculos, mas não garantem boa previsão do tempo. O modelo simplifica os dias em três categorias, considera apenas um dia anterior e mistura períodos do ano com uma matriz constante. A avaliação é retrospectiva na mesma reanálise.”

Encerre relacionando os estados a um grafo finito e as trajetórias a caminhos nesse grafo. Um reconhecedor de linguagem exigiria definir também entradas e condições de aceitação.

## Demonstração no cmd

Na raiz do projeto:

```bat
executar.bat
start "" "resultados\juiz_de_fora\relatorio.html"
```

Para mostrar uma condição inicial chuvosa, em uma pasta de saída própria:

```bat
executar.bat --dias 7 --estado C --saida resultados/apresentacao
start "" "resultados\apresentacao\relatorio.html"
```

Antes de apresentar, execute os testes:

```bat
executar.bat -Testes
```

## Perguntas frequentes

| Pergunta | Resposta |
| --- | --- |
| Os dados são medições locais diretas? | São uma reanálise regional Open-Meteo/ERA5; não uma estação local. |
| Por que seis anos? | É um recorte prático com cinco ciclos anuais no treino e um no teste; a suficiência depende também das contagens e da qualidade. |
| Por que Markov empata com persistência? | A categoria mais provável é sempre o estado de ontem nesta matriz. |
| Por que os valores de Brier são diferentes? | Os métodos atribuem probabilidades diferentes às mesmas categorias. |
| Os 43,04% descrevem 2025? | Descrevem o equilíbrio do modelo constante; as proporções observadas do teste são calculadas separadamente. |
| Tudo funcionar garante boa previsão? | O funcionamento e os cálculos são verificados por testes; o desempenho preditivo é medido no período de teste. |
