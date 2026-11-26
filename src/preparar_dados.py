"""Baixa um histórico fixo de Juiz de Fora e prepara a entrada versionável."""

import argparse
import csv
from datetime import datetime, timezone, date, timedelta
import hashlib
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError

from .dados import PASTA_DADOS, REGRA, classificar_dia

PARAMETROS = {
    "latitude": -21.76417, "longitude": -43.35028,
    "start_date": "2020-01-01", "end_date": "2025-12-31",
    "daily": "precipitation_sum,cloud_cover_mean",
    "models": "era5", "timezone": "America/Sao_Paulo",
}
URL = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(PARAMETROS)


def preparar(atualizar: bool = False) -> None:
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    bruto = PASTA_DADOS / "open_meteo_era5_2020_2025.json"
    manifesto = PASTA_DADOS / "fonte.json"
    anterior = json.loads(manifesto.read_text(encoding="utf-8")) if manifesto.exists() else {}
    baixado = atualizar or not bruto.exists()
    if baixado:
        pedido = Request(URL, headers={"User-Agent": "Trabalho-LFA-Markov/1.0"})
        with urlopen(pedido, timeout=120) as resposta:
            conteudo = resposta.read()
    else:
        conteudo = bruto.read_bytes()
    dados = json.loads(conteudo)
    diario = dados["daily"]
    datas, chuva, nuvens = (diario[chave] for chave in ("time", "precipitation_sum", "cloud_cover_mean"))
    inicio, fim = date.fromisoformat(PARAMETROS["start_date"]), date.fromisoformat(PARAMETROS["end_date"])
    esperadas = [(inicio + timedelta(days=i)).isoformat() for i in range((fim - inicio).days + 1)]
    if datas != esperadas or len(chuva) != len(datas) or len(nuvens) != len(datas):
        raise ValueError("Resposta com datas ou comprimentos incompatíveis com o período solicitado.")
    if dados["daily_units"]["precipitation_sum"] != "mm" or dados["daily_units"]["cloud_cover_mean"] != "%":
        raise ValueError("Unidades inesperadas na resposta da fonte.")
    linhas = [(data, p, c, classificar_dia(p, c) or "") for data, p, c in zip(datas, chuva, nuvens)]
    # Só grava após validar toda a resposta; uma falha de rede não substitui o snapshot existente.
    if baixado:
        bruto.write_bytes(conteudo)
    with (PASTA_DADOS / "diario.csv").open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(("data", "precipitacao_mm", "nebulosidade_pct", "estado"))
        escritor.writerows(linhas)
    metadados = {
        "local": "Juiz de Fora, Minas Gerais, Brasil", "provedor": "Open-Meteo",
        "modelo": "ERA5", "natureza": "Reanálise: observações combinadas com modelagem; não é medição direta de uma estação local.",
        "documentacao": "https://open-meteo.com/en/docs/historical-weather-api",
        "licenca": "CC BY 4.0; atribuição a Open-Meteo e Copernicus/ECMWF ERA5.",
        "licenca_url": "https://creativecommons.org/licenses/by/4.0/",
        "transformacoes": "O JSON bruto é preservado. O CSV seleciona os campos diários e acrescenta a classificação E/N/C pelos critérios do trabalho.",
        "url_consulta": URL, "parametros": PARAMETROS,
        "coordenadas_celula": {"latitude": dados["latitude"], "longitude": dados["longitude"]},
        "observacao_espacial": "A célula ERA5 representa uma área próxima às coordenadas pedidas, não uma estação dentro da cidade.",
        "baixado_em_utc": datetime.now(timezone.utc).isoformat() if baixado else anterior.get("baixado_em_utc"),
        "sha256_bruto": hashlib.sha256(conteudo).hexdigest(),
        "dias": len(datas), "inicio": datas[0], "fim": datas[-1],
        "regra_classificacao": REGRA,
    }
    manifesto.write_text(json.dumps(metadados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(linhas)} dias preparados em {PASTA_DADOS}. Fonte: Open-Meteo / ERA5.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atualizar", action="store_true", help="Baixa novamente; sem esta opção reutiliza o snapshot local.")
    args = parser.parse_args()
    try:
        preparar(args.atualizar)
    except (OSError, URLError, ValueError, KeyError) as erro:
        parser.error(f"Não foi possível preparar o histórico: {erro}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
