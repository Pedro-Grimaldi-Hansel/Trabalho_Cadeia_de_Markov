import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from src.analise import evolucao

RAIZ = Path(__file__).resolve().parent.parent


class IntegracaoTest(unittest.TestCase):
    def executar(self, *argumentos):
        return subprocess.run(
            [sys.executable, "-m", "src.main", *map(str, argumentos)], cwd=RAIZ,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def test_cli_exporta_dados_e_relatorios_coerentes(self):
        with tempfile.TemporaryDirectory() as temporario:
            pasta = Path(temporario) / "resultado com espaços"
            resultado = self.executar("--dias", 3, "--inicial", 0.2, 0.3, 0.5,
                                     "--repeticoes", 20, "--semente", 9, "--saida", pasta)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            self.assertEqual(len(list(pasta.iterdir())), 13)
            config = json.loads((pasta / "configuracao.json").read_text(encoding="utf-8"))
            self.assertEqual(config["distribuicao_inicial"], [0.2, 0.3, 0.5])
            self.assertEqual(config["semente"], 9)
            self.assertEqual(sum(config["experimentos"][0]["contagens"]), 20)
            esperado = evolucao((0.2, 0.3, 0.5), 3, config["matriz"])
            with (pasta / "evolucao.csv").open(encoding="utf-8-sig", newline="") as arquivo:
                linhas = list(csv.DictReader(arquivo))
            self.assertEqual(len(linhas), 4)
            for linha, vetor in zip(linhas, esperado):
                for estado, p in zip(("E", "N", "C"), vetor):
                    self.assertAlmostEqual(float(linha[estado]), p)
            with (pasta / "comparacao.csv").open(encoding="utf-8-sig", newline="") as arquivo:
                self.assertEqual(len(list(csv.DictReader(arquivo))), 3)
            for nome in ("evolucao.svg", "comparacao.svg", "diagrama.svg"):
                svg = ET.parse(pasta / nome).getroot()
                self.assertEqual(svg.tag, "{http://www.w3.org/2000/svg}svg")
            html = (pasta / "relatorio.html").read_text(encoding="utf-8")
            self.assertIn('lang="pt-BR"', html)
            self.assertEqual(html.count("<svg "), 3)
            self.assertNotIn("<script", html)

    def test_cli_dia_zero(self):
        with tempfile.TemporaryDirectory() as temporario:
            pasta = Path(temporario)
            resultado = self.executar("--dias", 0, "--estado", "c", "--repeticoes", 3, "--saida", pasta)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            config = json.loads((pasta / "configuracao.json").read_text(encoding="utf-8"))
            self.assertEqual(config["experimentos"][0]["contagens"], [0, 0, 3])
            ET.parse(pasta / "evolucao.svg")

    def test_cli_usa_matriz_estimada_em_todos_os_resultados(self):
        with tempfile.TemporaryDirectory() as temporario:
            pasta = Path(temporario) / "historico com espaços"
            resultado = self.executar("--dias", 1, "--repeticoes", 20, "--saida", pasta)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            config = json.loads((pasta / "configuracao.json").read_text(encoding="utf-8"))
            self.assertAlmostEqual(config["matriz"][0][2], 77 / 544)
            self.assertEqual(config["experimentos"][0]["teorica"], config["matriz"][0])
            estacionaria = config["distribuicao_estacionaria"]
            for j in range(3):
                self.assertAlmostEqual(sum(estacionaria[i] * config["matriz"][i][j] for i in range(3)), estacionaria[j])
            with (pasta / "previsoes_2025.csv").open(encoding="utf-8-sig", newline="") as arquivo:
                previsoes = list(csv.DictReader(arquivo))
            self.assertEqual(len(previsoes), 365)
            self.assertEqual(previsoes[0]["data"], "2025-01-01")
            avaliacao = json.loads((pasta / "avaliacao_historica.json").read_text(encoding="utf-8"))
            self.assertEqual(avaliacao["treino"]["fim"], "2024-12-31")
            acertos = sum(p["previsto"] == p["observado"] for p in previsoes)
            self.assertAlmostEqual(avaliacao["metricas"]["markov"]["acuracia"], acertos / len(previsoes))
            brier = sum(sum((float(p[f"prob_{estado}"]) - float(p["observado"] == estado)) ** 2
                            for estado in ("E", "N", "C")) for p in previsoes) / len(previsoes)
            self.assertAlmostEqual(avaliacao["metricas"]["markov"]["brier"], brier)
            for nome in ("relatorio.html", "relatorio.md"):
                conteudo = (pasta / nome).read_text(encoding="utf-8")
                for texto in ("Juiz de Fora", "56,16%", "43,04%", "Classificação dos dias",
                              "Estimação da matriz", "Avaliação em 2025", "Limitações", "Conclusão",
                              "não garante boa previsão"):
                    self.assertIn(texto, conteudo)
            self.assertIn("14,15%", (pasta / "diagrama.svg").read_text(encoding="utf-8"))

    def test_demo_exporta_os_doze_cenarios(self):
        with tempfile.TemporaryDirectory() as temporario:
            pasta = Path(temporario)
            resultado = self.executar("--demo", "--saida", pasta)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            config = json.loads((pasta / "configuracao.json").read_text(encoding="utf-8"))
            cenarios = {(e["dias"], e["repeticoes"]) for e in config["experimentos"]}
            self.assertEqual(cenarios, {(d, r) for d in (1, 2, 7, 30) for r in (100, 1000, 10000)})
            self.assertEqual(len(list(pasta.iterdir())), 13)

    def test_entradas_invalidas_nao_geram_saida(self):
        casos = (
            ("--dias", "-1"), ("--repeticoes", "0"), ("--semente", "-3"),
            ("--inicial", "0.2", "0.2", "0.2"), ("--inicial", "nan", "0", "1"),
            ("--estado", "X"), ("--estado", "E", "--inicial", "1", "0", "0"),
        )
        with tempfile.TemporaryDirectory() as temporario:
            pasta = Path(temporario) / "nao_criar"
            for caso in casos:
                with self.subTest(caso=caso):
                    resultado = self.executar(*caso, "--saida", pasta)
                    self.assertEqual(resultado.returncode, 2)
                    self.assertFalse(pasta.exists())
                    self.assertNotIn("Traceback", resultado.stderr)


if __name__ == "__main__":
    unittest.main()
