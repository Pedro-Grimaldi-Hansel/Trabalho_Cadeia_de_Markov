"""Evolução por vetores-linha, classificação e solução estacionária."""

from collections import deque
from dataclasses import dataclass
from math import fsum, gcd

from .modelo import (
    ESTADOS, TOLERANCIA, Distribuicao, Matriz,
    validar_distribuicao, validar_inteiro, validar_matriz,
)


def _multiplicar(vetor: Distribuicao, matriz: Matriz) -> Distribuicao:
    return tuple(fsum(vetor[i] * matriz[i][j] for i in range(3)) for j in range(3))


def evolucao(
    inicial: Distribuicao, dias: int, matriz: Matriz
) -> list[Distribuicao]:
    """Retorna π(0), ..., π(dias); cada passo calcula π(n + 1) = π(n)P."""
    atual = validar_distribuicao(inicial)
    validar_inteiro(dias, "Número de dias")
    matriz = validar_matriz(matriz)
    historico = [atual]
    for _ in range(dias):
        atual = _multiplicar(atual, matriz)
        historico.append(atual)
    return historico


def distribuicao_estacionaria(matriz: Matriz) -> Distribuicao:
    """Resolve πP = π e soma(π) = 1 por eliminação com pivoteamento.

    Uma equação de πP = π é redundante e é substituída pela soma.
    Matrizes sem solução estacionária única são rejeitadas.
    """
    matriz = validar_matriz(matriz)
    sistema = [
        [matriz[coluna][linha] - float(linha == coluna) for coluna in range(3)]
        + [0.0]
        for linha in range(2)
    ]
    sistema.append([1.0, 1.0, 1.0, 1.0])
    for coluna in range(3):
        pivo = max(range(coluna, 3), key=lambda i: abs(sistema[i][coluna]))
        if abs(sistema[pivo][coluna]) < 1e-14:
            raise ValueError("Não foi possível obter uma distribuição estacionária única.")
        sistema[coluna], sistema[pivo] = sistema[pivo], sistema[coluna]
        divisor = sistema[coluna][coluna]
        sistema[coluna] = [valor / divisor for valor in sistema[coluna]]
        for linha in range(3):
            if linha != coluna:
                fator = sistema[linha][coluna]
                sistema[linha] = [
                    sistema[linha][j] - fator * sistema[coluna][j] for j in range(4)
                ]
    solucao = tuple(linha[3] for linha in sistema)
    # Remove apenas resíduos numéricos negativos de magnitude desprezível.
    solucao = tuple(0.0 if -1e-14 < valor < 0.0 else valor for valor in solucao)
    solucao = validar_distribuicao(solucao, "Distribuição estacionária")
    if max(abs(a - b) for a, b in zip(solucao, _multiplicar(solucao, matriz))) > TOLERANCIA:
        raise ValueError("A solução estacionária não satisfez πP = π na tolerância definida.")
    return solucao


@dataclass(frozen=True)
class Classificacao:
    irredutivel: bool
    periodos: tuple[int | None, ...]
    absorventes: tuple[str, ...]

    @property
    def aperiodica(self) -> bool:
        return all(periodo == 1 for periodo in self.periodos)


def classificar_cadeia(matriz: Matriz) -> Classificacao:
    """Usa alcançabilidade e MDC dos ciclos nas classes de comunicação."""
    matriz = validar_matriz(matriz)
    arestas = [[j for j in range(3) if matriz[i][j] > 0] for i in range(3)]
    alcanca = [[i == j or matriz[i][j] > 0 for j in range(3)] for i in range(3)]
    for k in range(3):
        for i in range(3):
            for j in range(3):
                alcanca[i][j] = alcanca[i][j] or (alcanca[i][k] and alcanca[k][j])
    periodos: list[int | None] = [None] * 3
    visitados: set[int] = set()
    for raiz in range(3):
        if raiz in visitados:
            continue
        classe = {j for j in range(3) if alcanca[raiz][j] and alcanca[j][raiz]}
        visitados.update(classe)
        distancias = {raiz: 0}
        fila = deque([raiz])
        while fila:
            atual = fila.popleft()
            for proximo in arestas[atual]:
                if proximo in classe and proximo not in distancias:
                    distancias[proximo] = distancias[atual] + 1
                    fila.append(proximo)
        periodo = 0
        for origem in classe:
            for destino in arestas[origem]:
                if destino in classe:
                    periodo = gcd(periodo, abs(distancias[origem] + 1 - distancias[destino]))
        for estado in classe:
            periodos[estado] = periodo or None  # None indica ausência de retorno possível.
    absorventes = tuple(
        ESTADOS[i] for i in range(3)
        if all(matriz[i][j] == 0.0 for j in range(3) if j != i)
    )
    return Classificacao(all(all(linha) for linha in alcanca), tuple(periodos), absorventes)
