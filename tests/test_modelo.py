import math
import unittest

from src.analise import classificar_cadeia, distribuicao_estacionaria, evolucao
from src.modelo import (
    inicial_por_estado, validar_distribuicao, validar_inteiro,
    validar_matriz,
)
from src.simulacao import comparar, simular_trajetoria

MATRIZ_EXEMPLO = ((0.6, 0.3, 0.1), (0.3, 0.4, 0.3), (0.2, 0.4, 0.4))
IDENTIDADE = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
CICLO = ((0, 1, 0), (0, 0, 1), (1, 0, 0))


class EntradasTest(unittest.TestCase):
    def test_matriz_estocastica(self):
        self.assertEqual(validar_matriz(MATRIZ_EXEMPLO), MATRIZ_EXEMPLO)
        self.assertEqual([sum(linha) for linha in MATRIZ_EXEMPLO], [1, 1, 1])

    def test_probabilidades_invalidas(self):
        for valores in ([0, 0, 0], [1, 0], [1, 0, 0, 0], [-0.1, 0.6, 0.5],
                        [math.nan, 0, 1], [math.inf, 0, 0], [True, 0, 0],
                        ["1", 0, 0], [1.1, -0.1, 0], "100", None):
            with self.subTest(valores=valores), self.assertRaises(ValueError):
                validar_distribuicao(valores)

    def test_tolerancia_nao_normaliza(self):
        vetor = (0.6, 0.3, 0.1000000001)
        self.assertEqual(validar_distribuicao(vetor), vetor)
        with self.assertRaises(ValueError):
            validar_distribuicao((0.6, 0.3, 0.10001))

    def test_matriz_invalida(self):
        for matriz in ([], [[1, 0, 0]], [[1, 0]] * 3, [[1, 1, 1]] * 3, None):
            with self.subTest(matriz=matriz), self.assertRaises(ValueError):
                validar_matriz(matriz)

    def test_contagens_inteiras(self):
        for valor in (-1, 1.5, True, "3"):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                validar_inteiro(valor, "Dias")
        with self.assertRaises(ValueError):
            validar_inteiro(0, "Repetições", 1)

    def test_estados_iniciais(self):
        self.assertEqual(inicial_por_estado("e"), (1, 0, 0))
        self.assertEqual(inicial_por_estado("N"), (0, 1, 0))
        self.assertEqual(inicial_por_estado("C"), (0, 0, 1))
        with self.assertRaises(ValueError):
            inicial_por_estado("X")


class AnaliseTest(unittest.TestCase):
    def assertVetor(self, resultado, esperado, casas=12):
        for obtido, referencia in zip(resultado, esperado):
            self.assertAlmostEqual(obtido, referencia, places=casas)

    def test_multiplicacao_com_valores_conhecidos(self):
        esperado = [(1, 0, 0), (0.6, 0.3, 0.1), (0.47, 0.34, 0.19), (0.422, 0.353, 0.225)]
        for resultado, referencia in zip(evolucao((1, 0, 0), 3, MATRIZ_EXEMPLO), esperado):
            self.assertVetor(resultado, referencia)

    def test_dia_zero_sem_transicao(self):
        self.assertEqual(evolucao((0.2, 0.3, 0.5), 0, MATRIZ_EXEMPLO), [(0.2, 0.3, 0.5)])

    def test_linha_representa_origem(self):
        for i, inicial in enumerate(((1, 0, 0), (0, 1, 0), (0, 0, 1))):
            self.assertVetor(evolucao(inicial, 1, MATRIZ_EXEMPLO)[1], MATRIZ_EXEMPLO[i])

    def test_inicial_mista(self):
        self.assertVetor(evolucao((0.2, 0.3, 0.5), 1, MATRIZ_EXEMPLO)[1], (0.31, 0.38, 0.31))

    def test_conserva_probabilidades_em_muitos_dias(self):
        for vetor in evolucao((0.2, 0.3, 0.5), 1000, MATRIZ_EXEMPLO):
            self.assertAlmostEqual(sum(vetor), 1, places=12)
            self.assertTrue(all(0 <= p <= 1 for p in vetor))

    def test_estacionaria_e_convergencia(self):
        estacionaria = distribuicao_estacionaria(MATRIZ_EXEMPLO)
        self.assertVetor(estacionaria, (24 / 61, 22 / 61, 15 / 61))
        self.assertVetor(evolucao(estacionaria, 1, MATRIZ_EXEMPLO)[1], estacionaria)
        for inicial in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            self.assertVetor(evolucao(inicial, 50, MATRIZ_EXEMPLO)[-1], estacionaria)

    def test_sistema_sem_estacionaria_unica(self):
        with self.assertRaisesRegex(ValueError, "única"):
            distribuicao_estacionaria(IDENTIDADE)

    def test_cadeia_periodica_tem_estacionaria_mas_nao_converge(self):
        self.assertVetor(distribuicao_estacionaria(CICLO), (1 / 3, 1 / 3, 1 / 3))
        self.assertEqual(evolucao((1, 0, 0), 3, CICLO)[-1], (1, 0, 0))
        resultado = classificar_cadeia(CICLO)
        self.assertTrue(resultado.irredutivel)
        self.assertFalse(resultado.aperiodica)
        self.assertEqual(resultado.periodos, (3, 3, 3))

    def test_classificacao_irredutivel_e_aperiodica(self):
        resultado = classificar_cadeia(MATRIZ_EXEMPLO)
        self.assertTrue(resultado.irredutivel)
        self.assertTrue(resultado.aperiodica)
        self.assertEqual(resultado.periodos, (1, 1, 1))
        self.assertEqual(resultado.absorventes, ())

    def test_aperiodicidade_sem_lacos(self):
        # Há ciclos de comprimentos 2 e 3: MDC = 1, embora a diagonal seja zero.
        matriz = ((0, 1, 0), (0, 0, 1), (0.5, 0.5, 0))
        self.assertEqual(classificar_cadeia(matriz).periodos, (1, 1, 1))

    def test_estado_transiente_e_absorvente(self):
        matriz = ((0, 1, 0), (0, 0, 1), (0, 0, 1))
        resultado = classificar_cadeia(matriz)
        self.assertFalse(resultado.irredutivel)
        self.assertEqual(resultado.periodos, (None, None, 1))
        self.assertEqual(resultado.absorventes, ("C",))
        self.assertVetor(distribuicao_estacionaria(matriz), (0, 0, 1))


class SimulacaoTest(unittest.TestCase):
    def test_trajetoria_deterministica_e_tamanho(self):
        self.assertEqual(
            simular_trajetoria((1, 0, 0), 6, matriz=CICLO),
            ["E", "N", "C", "E", "N", "C", "E"],
        )
        self.assertEqual(simular_trajetoria((0, 1, 0), 0, matriz=MATRIZ_EXEMPLO), ["N"])

    def test_mesma_semente_reproduz_sorteios(self):
        self.assertEqual(simular_trajetoria((0.2, 0.3, 0.5), 50, semente=9, matriz=MATRIZ_EXEMPLO),
                         simular_trajetoria((0.2, 0.3, 0.5), 50, semente=9, matriz=MATRIZ_EXEMPLO))
        self.assertEqual(comparar((1, 0, 0), 7, 100, semente=15, matriz=MATRIZ_EXEMPLO),
                         comparar((1, 0, 0), 7, 100, semente=15, matriz=MATRIZ_EXEMPLO))

    def test_cada_trajetoria_reinicia_na_distribuicao_inicial(self):
        matriz = ((0, 1, 0), (0, 0, 1), (0, 0, 1))
        exp = comparar((1, 0, 0), 1, 50, matriz=matriz)
        self.assertEqual(exp.contagens, (0, 50, 0))
        self.assertEqual(exp.frequencias, (0, 1, 0))
        self.assertEqual(exp.erros, (0, 0, 0))

    def test_comparacao_dia_zero(self):
        exp = comparar((0, 0, 1), 0, 20, matriz=MATRIZ_EXEMPLO)
        self.assertEqual(exp.contagens, (0, 0, 20))
        self.assertEqual(exp.erros_padrao, (0, 0, 0))

    def test_conserva_contagens_sem_afirmacao_estatistica(self):
        exp = comparar((0.2, 0.3, 0.5), 7, 101, matriz=MATRIZ_EXEMPLO)
        self.assertEqual(sum(exp.contagens), 101)
        self.assertAlmostEqual(sum(exp.frequencias), 1)
        self.assertEqual(exp.erros, tuple(abs(a - b) for a, b in zip(exp.teorica, exp.frequencias)))
        for i, p in enumerate(exp.teorica):
            self.assertAlmostEqual(exp.erros_padrao[i], math.sqrt(p * (1 - p) / 101))

    def test_parametros_invalidos_na_simulacao(self):
        for argumentos in ((-1, 10, 42), (1, 0, 42), (1, 2, -1)):
            with self.subTest(argumentos=argumentos), self.assertRaises(ValueError):
                comparar((1, 0, 0), argumentos[0], argumentos[1], semente=argumentos[2], matriz=MATRIZ_EXEMPLO)


if __name__ == "__main__":
    unittest.main()
