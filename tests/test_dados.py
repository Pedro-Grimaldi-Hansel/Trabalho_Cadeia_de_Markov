import csv
from datetime import date, timedelta
import hashlib
import json
import math
import shutil
from pathlib import Path
import tempfile
import unittest

from src.dados import (
    Dia, PASTA_DADOS, ajustar_e_avaliar, carregar_base, carregar_diario, classificar_dia, pares_consecutivos,
)


def dias_de_estados(estados):
    valores = {"E": (0.0, 20.0), "N": (0.0, 80.0), "C": (5.0, 80.0)}
    return [Dia(date(2020, 1, 1) + timedelta(days=i), *valores[e]) for i, e in enumerate(estados)]


class HistoricoTest(unittest.TestCase):
    def test_classificacao_limites_prioridade_e_ausencias(self):
        self.assertEqual(classificar_dia(1.0, 0), "C")
        self.assertEqual(classificar_dia(0.999, 50), "E")
        self.assertEqual(classificar_dia(0, 50.001), "N")
        self.assertEqual(classificar_dia(0, 100), "N")
        self.assertIsNone(classificar_dia(None, 0))
        self.assertIsNone(classificar_dia(0, None))
        for chuva, nuvens in ((-1, 0), (0, 101), (math.nan, 0), (0, math.inf)):
            with self.subTest(chuva=chuva, nuvens=nuvens), self.assertRaises(ValueError):
                classificar_dia(chuva, nuvens)

    def test_lacunas_nao_viram_transicoes(self):
        dias = [Dia(date(2020, 1, 1), 0, 0), Dia(date(2020, 1, 2), 0, 90),
                Dia(date(2020, 1, 3), None, None), Dia(date(2020, 1, 4), 5, 90),
                Dia(date(2020, 1, 6), 0, 0), Dia(date(2020, 1, 7), 0, 0)]
        pares = [(a.estado, b.estado) for a, b in pares_consecutivos(dias)]
        self.assertEqual(pares, [("E", "N"), ("E", "E")])

    def test_contagens_estimacao_e_metricas_calculadas_a_mao(self):
        # Treino E,E,N,N,C,C,E: cada origem tem duas saídas.
        dias = dias_de_estados("EENNCCEENC")
        resultado = ajustar_e_avaliar(dias, date(2020, 1, 7))
        self.assertEqual(resultado["contagens_transicoes"], [[1, 1, 0], [0, 1, 1], [1, 0, 1]])
        self.assertEqual(resultado["matriz"], ((0.5, 0.5, 0), (0, 0.5, 0.5), (0.5, 0, 0.5)))
        self.assertEqual(resultado["transicoes_treino"], 6)
        self.assertEqual(resultado["teste"]["previsoes_avaliadas"], 3)
        self.assertEqual(resultado["previsoes"][0]["data"], "2020-01-08")
        metricas = resultado["metricas"]
        self.assertAlmostEqual(metricas["markov"]["acuracia"], 1 / 3)
        self.assertAlmostEqual(metricas["markov"]["brier"], 0.5)
        self.assertAlmostEqual(metricas["persistencia"]["acuracia"], 1 / 3)
        self.assertAlmostEqual(metricas["persistencia"]["brier"], 4 / 3)
        self.assertAlmostEqual(metricas["frequencia_treino"]["brier"], 100 / 147)

    def test_alterar_teste_nao_muda_matriz_do_treino(self):
        primeiro = ajustar_e_avaliar(dias_de_estados("EENNCCEENC"), date(2020, 1, 7))
        segundo = ajustar_e_avaliar(dias_de_estados("EENNCCECCC"), date(2020, 1, 7))
        self.assertEqual(primeiro["matriz"], segundo["matriz"])
        self.assertEqual(primeiro["contagens_transicoes"], segundo["contagens_transicoes"])
        self.assertNotEqual(primeiro["metricas"], segundo["metricas"])

    def test_base_rejeita_fonte_com_hash_incompativel(self):
        with tempfile.TemporaryDirectory() as temporario:
            pasta = Path(temporario)
            for arquivo in PASTA_DADOS.iterdir():
                shutil.copyfile(arquivo, pasta / arquivo.name)
            bruto = pasta / "open_meteo_era5_2020_2025.json"
            bruto.write_bytes(bruto.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "hash"):
                carregar_base(pasta)

    def test_base_rejeita_csv_divergente_e_metadados_incorretos(self):
        with tempfile.TemporaryDirectory() as temporario:
            pasta = Path(temporario)
            for arquivo in PASTA_DADOS.iterdir():
                shutil.copyfile(arquivo, pasta / arquivo.name)
            csv_diario = pasta / "diario.csv"
            texto = csv_diario.read_text(encoding="utf-8-sig")
            linhas = texto.splitlines()
            campos = linhas[1].split(",")
            campos[2] = str((float(campos[2]) + 10) % 100)
            linhas[1] = ",".join(campos)
            csv_diario.write_text("\n".join(linhas) + "\n", encoding="utf-8-sig")
            with self.assertRaises(ValueError):
                carregar_base(pasta)
            csv_diario.write_text(texto, encoding="utf-8-sig")
            manifesto = pasta / "fonte.json"
            fonte = json.loads(manifesto.read_text(encoding="utf-8"))
            fonte["dias"] += 1
            manifesto.write_text(json.dumps(fonte), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "período"):
                carregar_base(pasta)

    def test_historico_insuficiente_nao_inventa_probabilidades(self):
        with self.assertRaisesRegex(ValueError, "transição de saída"):
            ajustar_e_avaliar(dias_de_estados("EEEEEE"), date(2020, 1, 4))
        with self.assertRaisesRegex(ValueError, "anteriores e posteriores"):
            ajustar_e_avaliar(dias_de_estados("EENNCC"), date(2025, 1, 1))

    def test_csv_rejeita_estado_incompativel_e_data_duplicada(self):
        casos = [
            [("2020-01-01", 5, 90, "E")],
            [("2020-01-01", 0, 0, "E"), ("2020-01-01", 0, 90, "N")],
        ]
        with tempfile.TemporaryDirectory() as temporario:
            caminho = Path(temporario) / "diario.csv"
            for linhas in casos:
                with caminho.open("w", encoding="utf-8", newline="") as arquivo:
                    escritor = csv.writer(arquivo)
                    escritor.writerow(("data", "precipitacao_mm", "nebulosidade_pct", "estado"))
                    escritor.writerows(linhas)
                with self.assertRaises(ValueError):
                    carregar_diario(caminho)

    def test_snapshot_versionado_tem_procedencia_e_contagens_coerentes(self):
        dias_carregados, _ = carregar_base()
        fonte = json.loads((PASTA_DADOS / "fonte.json").read_text(encoding="utf-8"))
        bruto = (PASTA_DADOS / "open_meteo_era5_2020_2025.json").read_bytes()
        self.assertEqual(hashlib.sha256(bruto).hexdigest(), fonte["sha256_bruto"])
        self.assertEqual(fonte["parametros"]["models"], "era5")
        dias = carregar_diario(PASTA_DADOS / "diario.csv")
        self.assertEqual(dias, dias_carregados)
        valores = json.loads(bruto)["daily"]
        self.assertEqual([(d.data.isoformat(), d.chuva, d.nuvens) for d in dias],
                         list(zip(valores["time"], valores["precipitation_sum"], valores["cloud_cover_mean"])))
        resultado = ajustar_e_avaliar(dias)
        self.assertEqual(len(dias), 2192)
        self.assertEqual(resultado["treino"]["dias_validos"], 1827)
        self.assertEqual(resultado["transicoes_treino"], 1826)
        self.assertEqual(resultado["teste"]["previsoes_avaliadas"], 365)
        self.assertEqual(resultado["dias_sem_classificacao"], 0)
        self.assertEqual(resultado["dias_ausentes"], 0)
        for contagens, probabilidades in zip(resultado["contagens_transicoes"], resultado["matriz"]):
            self.assertAlmostEqual(sum(probabilidades), 1)
            for n, p in zip(contagens, probabilidades):
                self.assertAlmostEqual(p, n / sum(contagens))


if __name__ == "__main__":
    unittest.main()
