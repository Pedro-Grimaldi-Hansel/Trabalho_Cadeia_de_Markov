# Cadeia de Markov — tempo em Juiz de Fora

Projeto de Linguagens Formais e Autômatos que estima as probabilidades de transição entre dias ensolarados (E), nublados (N) e chuvosos (C) para Juiz de Fora, MG. Calcula a evolução das probabilidades, simula trajetórias e avalia previsões de um dia em um período separado do treino.

A base inclui **2.192 dias de 2020 a 2025**, obtidos do Open-Meteo/ERA5. É uma **reanálise meteorológica**, que combina observações e modelagem para uma célula regional próxima da cidade, sem corresponder a medições diretas de uma estação local.

## Requisitos

- Python **3.10 ou superior**.
- Apenas a biblioteca padrão do Python; não é necessário instalar pacotes.
- A execução e os testes funcionam sem internet. A rede só é necessária para baixar novamente os dados.

## Executar

Abra o terminal na pasta que contém este README.

### Prompt de Comando do Windows (cmd)

```bat
executar.bat
start "" "resultados\juiz_de_fora\relatorio.html"
```

### PowerShell

```powershell
.\executar.ps1
Start-Process .\resultados\juiz_de_fora\relatorio.html
```

### Python no Windows, Linux ou macOS

```text
python -m src.main
```

No Windows, se necessário, substitua `python` por `py -3`; no Linux e macOS, por `python3`. Abra `resultados/juiz_de_fora/relatorio.html` no navegador. Não é necessário iniciar um servidor.

A execução estima a matriz com o treino, avalia os dias de teste e gera **13 arquivos**. Por padrão, o cenário parte de E e calcula 30 transições com 10.000 trajetórias e semente 42. Ele não consulta o tempo atual da cidade.

## Configurar o Python no Windows

Os executores procuram, nesta ordem:

1. `.venv\Scripts\python.exe`.
2. O executável indicado em `python-local.txt`.
3. `py -3`.
4. `python` no PATH, desconsiderando o atalho da Microsoft Store.

Para uma instalação fora do PATH, copie `python-local.example.txt` para `python-local.txt` e substitua seu conteúdo pelo caminho completo do seu `python.exe`, em uma única linha e sem aspas. Esse arquivo é uma configuração local ignorada pelo Git.

Um ambiente virtual é opcional e não precisa ser ativado para usar os executores:

```text
python -m venv .venv
```

Se Python não estiver instalado, obtenha-o na [página oficial](https://www.python.org/downloads/windows/) e reabra o terminal.

## Escolher um cenário

No cmd, partindo de um dia chuvoso:

```bat
executar.bat --dias 7 --estado C --repeticoes 5000 --semente 42
```

Partindo de uma distribuição de probabilidades, na ordem E, N, C:

```bat
executar.bat --dias 10 --inicial 0.2 0.3 0.5 --saida resultados/cenario
```

Para incluir os 12 cenários com 1, 2, 7 e 30 dias e 100, 1.000 e 10.000 trajetórias:

```bat
executar.bat --demo
```

No PowerShell, use `.\executar.ps1` no lugar de `executar.bat`. Com Python direto, use `python -m src.main` seguido dos mesmos parâmetros.

| Opção | Significado | Padrão |
| --- | --- | --- |
| `--dias` | Número de transições; inclui o dia zero nos resultados. | 30 |
| `--estado` | Estado inicial conhecido: E, N ou C. | E |
| `--inicial E N C` | Três probabilidades com soma 1; alternativa a `--estado`. | Não informado |
| `--repeticoes` | Número de trajetórias independentes. | 10000 |
| `--semente` | Inteiro não negativo para reproduzir os sorteios. | 42 |
| `--saida` | Pasta de saída; caminhos relativos usam a pasta de execução. | `resultados/juiz_de_fora/` na raiz do projeto |
| `--demo` | Acrescenta a grade de 12 cenários. | Desativado |
| `--help` | Mostra a ajuda do programa. | — |

Use ponto decimal. `--estado` e `--inicial` não podem ser usados juntos. Os executores Windows usam a raiz do projeto como pasta de execução, mesmo quando chamados de outra pasta. Executar novamente na mesma saída substitui os arquivos com os mesmos nomes.

## Dados e metodologia

| Etapa | Período | Quantidade |
| --- | --- | ---: |
| Estimação da matriz | 2020–2024 | 1.827 dias, 1.826 transições |
| Avaliação retrospectiva de um dia | 2025 | 365 previsões |

Os dias são classificados por precipitação acumulada e nebulosidade média:

- **C:** precipitação de pelo menos 1 mm.
- **E:** precipitação menor que 1 mm e nebulosidade de até 50%.
- **N:** precipitação menor que 1 mm e nebulosidade acima de 50%.

Esses limites são escolhas do trabalho. E pode incluir dias parcialmente nublados. Dados ausentes são excluídos, sem ligar registros separados por lacunas. A base incluída não contém lacunas nem dias sem classificação.

A matriz é estimada por `P(i,j) = contagem(i → j) / total de saídas de i`. Linhas representam o estado atual e colunas o próximo dia, na ordem E, N, C:

| Atual / próximo | E | N | C |
| --- | ---: | ---: | ---: |
| E | 63,24% | 22,61% | 14,15% |
| N | 28,43% | 43,75% | 27,82% |
| C | 7,51% | 19,85% | 72,65% |

A evolução usa vetores-linha: `π(n + 1) = π(n)P`. O equilíbrio do modelo é aproximadamente **29,79% E, 27,16% N e 43,04% C**. Ele descreve o limite sob uma matriz constante, não a proporção observada de cada ano nem uma previsão para amanhã.

Na avaliação de 2025:

| Método | Acerto da categoria | Brier — menor é melhor |
| --- | ---: | ---: |
| Cadeia de Markov | 56,16% | 0,5778 |
| Repetir o estado de ontem | 56,16% | 0,8767 |
| Frequências gerais do treino | 34,52% | 0,6783 |

Markov e persistência escolhem as mesmas categorias nesta matriz, mas atribuem probabilidades diferentes. Brier avalia o vetor inteiro de probabilidades, na escala de 0 a 2. O erro entre simulação e teoria é uma medida separada: trajetórias sorteadas não são registros meteorológicos adicionais.

A matriz anual mistura períodos do ano e considera apenas o estado do dia anterior. O teste é retrospectivo na mesma reanálise; o projeto tem finalidade acadêmica e não constitui uma previsão meteorológica operacional.

Consulte a [metodologia](docs/METODOLOGIA.md) e o [roteiro de apresentação](docs/ROTEIRO_APRESENTACAO.md). O relatório gerado apresenta os cálculos, tabelas, gráficos, avaliação e interpretação completa.

## Arquivos de saída

| Arquivo | Conteúdo |
| --- | --- |
| `relatorio.html` | Relatório com gráficos incorporados, para abrir no navegador. |
| `relatorio.md` | Relatório em texto com referências às figuras locais. |
| `configuracao.json` | Parâmetros, matriz, fonte, ambiente e experimentos. |
| `evolucao.csv` | Distribuição de probabilidades de cada dia. |
| `trajetoria.csv` | Uma trajetória sintética, incluindo o dia zero. |
| `comparacao.csv` | Frequências simuladas, teoria e erros de cada cenário. |
| `evolucao.svg` | Evolução das probabilidades. |
| `comparacao.svg` | Teoria e simulação do cenário principal. |
| `diagrama.svg` | Transições entre os três estados. |
| `transicoes_treino.csv` | Contagens e probabilidades usadas para estimar a matriz. |
| `previsoes_2025.csv` | Previsão e categoria observada de cada dia avaliado. |
| `avaliacao_historica.csv` | Acurácia e Brier dos três métodos. |
| `avaliacao_historica.json` | Avaliação, qualidade da base e metadados da fonte. |

CSVs usam UTF-8 com BOM, vírgula como separador e ponto decimal. As probabilidades vão de 0 a 1; erros em pontos percentuais são multiplicados por 100. Ao importar no Excel, escolha esses separadores.

## Verificar o funcionamento

No cmd:

```bat
executar.bat -Testes
```

No PowerShell:

```powershell
.\executar.ps1 -Testes
```

Com Python direto:

```text
python -m unittest discover -s tests -v
```

A suíte verifica cálculos conhecidos, conservação de probabilidades, distribuição estacionária, classificação da cadeia, integridade dos dados, separação temporal, reprodutibilidade e exportação. O resultado esperado termina em `OK`. Testes matemáticos aprovados não garantem boa capacidade de previsão: essa é medida pela avaliação histórica.

## Preparar a base de dados

Os três arquivos em `dados/juiz_de_fora/` fazem parte da entrada do programa e devem acompanhar o código: resposta JSON do provedor, CSV diário classificado e `fonte.json`, com consulta, coordenadas, data de obtenção e hash SHA-256.

Para reconstruir o CSV a partir da resposta JSON local:

```text
python -m src.preparar_dados
```

Para baixar novamente o mesmo período, com internet:

```text
python -m src.preparar_dados --atualizar
```

Se Python não estiver no PATH, no PowerShell use o executável configurado:

```powershell
$pythonProjeto = (Get-Content .\python-local.txt -Raw).Trim()
& $pythonProjeto -m src.preparar_dados
```

## Organização

| Caminho | Finalidade |
| --- | --- |
| `src/modelo.py` | Estados e validação das entradas. |
| `src/dados.py` | Integridade, classificação, estimação e avaliação temporal. |
| `src/analise.py` | Evolução, classificação da cadeia e distribuição estacionária. |
| `src/simulacao.py` | Sorteio de trajetórias e comparação com a teoria. |
| `src/visualizacao.py` | Gráficos e diagrama em SVG. |
| `src/relatorio.py` | Exportação e montagem do relatório. |
| `src/main.py` | Interface pelo terminal. |
| `src/preparar_dados.py` | Obtenção e preparação da base meteorológica. |
| `dados/juiz_de_fora/` | Base de entrada e seus metadados. |
| `tests/` | Testes automatizados. |
| `docs/` | Metodologia e roteiro de apresentação. |
| `resultados/` | Saídas regeneráveis, ignoradas pelo Git. |

Configurações locais, ambientes virtuais, caches e resultados são ignorados pelo `.gitignore`. O código, os testes, os documentos e a base de entrada são versionáveis.

## Solução de problemas

| Problema | Solução |
| --- | --- |
| `python` abre a Microsoft Store | Tente `py -3` ou configure `python-local.txt` com um executável instalado. |
| Um arquivo `.ps1` abre no editor | No cmd, execute `executar.bat`; no PowerShell, use `.\executar.ps1`. |
| Python não encontrado ou versão insuficiente | Instale Python 3.10 ou superior e confira a ordem de procura descrita acima. |
| `No module named src` | Execute na raiz do projeto e use `python -m src.main`. |
| Base ausente ou incompatível com o hash | Confira os três arquivos em `dados/juiz_de_fora/`. Uma nova obtenção pode ser feita com `python -m src.preparar_dados --atualizar`. |
| Nenhuma janela aparece ao executar | Abra o relatório no navegador com o comando indicado na seção de execução. |

Se a política do PowerShell bloquear a execução direta, use `executar.bat` ou execute `powershell -NoProfile -ExecutionPolicy Bypass -File .\executar.ps1`. A opção vale somente para esse processo.

## Fontes e licença dos dados

- [Open-Meteo — Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api).
- [ERA5 — Copernicus/ECMWF, DOI 10.24381/cds.adbb2d47](https://doi.org/10.24381/cds.adbb2d47).
- [Dados disponibilizados por Open-Meteo sob CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Os campos diários são selecionados e classificados pelos critérios descritos neste projeto, com atribuição ao Open-Meteo e ao Copernicus/ECMWF ERA5.
