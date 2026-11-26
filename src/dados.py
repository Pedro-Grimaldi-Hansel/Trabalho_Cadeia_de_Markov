"""Classificação diária, estimação por contagens e avaliação temporal."""

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import date, timedelta
from math import isfinite
from pathlib import Path

from .modelo import ESTADOS, validar_matriz

PASTA_DADOS = Path(__file__).resolve().parent.parent / "dados" / "juiz_de_fora"
CORTE_TREINO = date(2024, 12, 31)
LIMIAR_CHUVA_MM = 1.0
LIMIAR_NUVENS_PCT = 50.0
REGRA = (
    "C: precipitação diária >= 1 mm; nos demais dias, E: nebulosidade média <= 50%; "
    "N: nebulosidade média > 50%. São critérios operacionais deste trabalho, "
    "não uma classificação oficial. E pode incluir dias parcialmente nublados."
)


def classificar_dia(chuva: float | None, nuvens: float | None) -> str | None:
    for valor, nome, limite in ((chuva, "Precipitação", None), (nuvens, "Nebulosidade", 100)):
        if valor is not None and (not isfinite(valor) or valor < 0 or (limite is not None and valor > limite)):
            raise ValueError(f"{nome} inválida: {valor}.")
    if chuva is None or nuvens is None:
        return None
    if chuva >= LIMIAR_CHUVA_MM:
        return "C"
    return "E" if nuvens <= LIMIAR_NUVENS_PCT else "N"


@dataclass(frozen=True)
class Dia:
    data: date
    chuva: float | None
    nuvens: float | None

    @property
    def estado(self) -> str | None:
        return classificar_dia(self.chuva, self.nuvens)


def carregar_diario(caminho: Path) -> list[Dia]:
    dias = []
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        obrigatorias = {"data", "precipitacao_mm", "nebulosidade_pct", "estado"}
        if not obrigatorias.issubset(leitor.fieldnames or []):
            raise ValueError("CSV diário sem as colunas obrigatórias.")
        for linha in leitor:
            dia = Dia(date.fromisoformat(linha["data"]),
                      float(linha["precipitacao_mm"]) if linha["precipitacao_mm"] else None,
                      float(linha["nebulosidade_pct"]) if linha["nebulosidade_pct"] else None)
            if dias and dia.data <= dias[-1].data:
                raise ValueError("As datas do CSV devem ser únicas e estar em ordem crescente.")
            if (dia.estado or "") != linha["estado"]:
                raise ValueError(f"Estado incompatível com as medições em {dia.data}.")
            dias.append(dia)
    if not dias:
        raise ValueError("CSV diário vazio.")
    return dias


def carregar_base(pasta: Path = PASTA_DADOS) -> tuple[list[Dia], dict]:
    """Confere a integridade e a correspondência entre a fonte e o CSV diário."""
    try:
        fonte = json.loads((pasta / "fonte.json").read_text(encoding="utf-8"))
        bruto = (pasta / "open_meteo_era5_2020_2025.json").read_bytes()
        if hashlib.sha256(bruto).hexdigest() != fonte["sha256_bruto"]:
            raise ValueError("O histórico bruto não corresponde ao hash registrado em fonte.json.")
        diario = carregar_diario(pasta / "diario.csv")
        dados = json.loads(bruto)
        valores = dados["daily"]
        if dados["daily_units"]["precipitation_sum"] != "mm" or dados["daily_units"]["cloud_cover_mean"] != "%":
            raise ValueError("Unidades incompatíveis com a classificação diária.")
        colunas = [valores[chave] for chave in ("time", "precipitation_sum", "cloud_cover_mean")]
        if len({len(coluna) for coluna in colunas}) != 1:
            raise ValueError("O histórico bruto contém colunas com comprimentos diferentes.")
        esperado = list(zip(*colunas))
        obtido = [(dia.data.isoformat(), dia.chuva, dia.nuvens) for dia in diario]
        if esperado != obtido:
            raise ValueError("O CSV diário não corresponde ao histórico bruto; execute python -m src.preparar_dados.")
        if (fonte["dias"], fonte["inicio"], fonte["fim"]) != (len(diario), diario[0].data.isoformat(), diario[-1].data.isoformat()):
            raise ValueError("O período informado em fonte.json não corresponde aos registros diários.")
        return diario, fonte
    except KeyError as erro:
        raise ValueError(f"Campo obrigatório ausente na base: {erro}.") from erro
    except FileNotFoundError as erro:
        raise ValueError("Base de Juiz de Fora incompleta. Confira a pasta dados/juiz_de_fora ou execute python -m src.preparar_dados.") from erro


def pares_consecutivos(dias: list[Dia]):
    for anterior, atual in zip(dias, dias[1:]):
        if atual.data - anterior.data == timedelta(days=1) and anterior.estado and atual.estado:
            yield anterior, atual


def ajustar_e_avaliar(dias: list[Dia], corte: date = CORTE_TREINO) -> dict:
    treino = [dia for dia in dias if dia.data <= corte]
    teste = [dia for dia in dias if dia.data > corte]
    if not treino or not teste:
        raise ValueError("É necessário ter dias anteriores e posteriores ao corte temporal.")
    contagens = [[0] * 3 for _ in ESTADOS]
    for anterior, atual in pares_consecutivos(treino):
        contagens[ESTADOS.index(anterior.estado)][ESTADOS.index(atual.estado)] += 1
    for i, linha in enumerate(contagens):
        if not sum(linha):
            raise ValueError(f"Nenhuma transição de saída de {ESTADOS[i]} no treino; amplie o histórico.")
    matriz = validar_matriz(tuple(tuple(n / sum(linha) for n in linha) for linha in contagens))
    frequencias = [sum(dia.estado == estado for dia in treino) for estado in ESTADOS]
    total_validos = sum(frequencias)
    climatologia = tuple(n / total_validos for n in frequencias)
    acumulados = {nome: {"acertos": 0, "brier": 0.0} for nome in ("markov", "persistencia", "frequencia_treino")}
    previsoes = []
    for anterior, atual in pares_consecutivos(dias):
        if atual.data <= corte:
            continue
        origem = ESTADOS.index(anterior.estado)
        observado = ESTADOS.index(atual.estado)
        probabilidades = {"markov": matriz[origem],
                          "persistencia": tuple(float(i == origem) for i in range(3)),
                          "frequencia_treino": climatologia}
        for nome, vetor in probabilidades.items():
            # Empates usam a ordem E, N, C, de forma determinística.
            acumulados[nome]["acertos"] += max(range(3), key=lambda i: vetor[i]) == observado
            acumulados[nome]["brier"] += sum((p - float(i == observado)) ** 2 for i, p in enumerate(vetor))
        previsoes.append({"data": atual.data.isoformat(), "estado_anterior": anterior.estado,
                          "observado": atual.estado, "probabilidades": matriz[origem],
                          "previsto": ESTADOS[max(range(3), key=lambda i: matriz[origem][i])]})
    n = len(previsoes)
    if not n:
        raise ValueError("Não há pares consecutivos válidos para avaliar após o corte.")
    metricas = {nome: {"acuracia": valores["acertos"] / n, "brier": valores["brier"] / n}
                for nome, valores in acumulados.items()}
    return {"matriz": matriz, "contagens_transicoes": contagens,
            "transicoes_treino": sum(map(sum, contagens)),
            "treino": {"inicio": treino[0].data.isoformat(), "fim": treino[-1].data.isoformat(),
                       "dias": len(treino), "dias_validos": total_validos,
                       "contagens_estados": dict(zip(ESTADOS, frequencias))},
            "teste": {"inicio": teste[0].data.isoformat(), "fim": teste[-1].data.isoformat(),
                      "dias": len(teste), "previsoes_avaliadas": n},
            "dias_sem_classificacao": sum(dia.estado is None for dia in dias),
            "dias_ausentes": (dias[-1].data - dias[0].data).days + 1 - len(dias),
            "regra_classificacao": REGRA,
            "metodo_estimacao": "P(i,j) = contagem(i -> j) / soma das saídas de i; sem suavização.",
            "metodo_avaliacao": (
                "Previsão de um dia com matriz fixa do treino e estado observado do dia anterior. "
                "O primeiro alvo do teste pode usar o último dia do treino como contexto. "
                "Sem embaralhar datas nem ajustar a matriz com o teste. Pares com lacunas são excluídos. "
                "Brier multiclasse = média da soma dos três erros quadráticos, escala 0 a 2; menor é melhor."
            ), "metricas": metricas, "previsoes": previsoes}
