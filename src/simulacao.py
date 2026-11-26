"""Sorteio de trajetórias e comparação dos estados finais com a teoria."""

from dataclasses import dataclass
from math import sqrt
from random import Random

from .analise import evolucao
from .modelo import (
    ESTADOS, Distribuicao, Matriz,
    validar_distribuicao, validar_inteiro, validar_matriz,
)


def _sortear(pesos: Distribuicao, gerador: Random) -> int:
    return gerador.choices(range(3), weights=pesos, k=1)[0]


def simular_trajetoria(
    inicial: Distribuicao,
    dias: int,
    *,
    semente: int = 42,
    matriz: Matriz,
) -> list[str]:
    inicial = validar_distribuicao(inicial)
    matriz = validar_matriz(matriz)
    validar_inteiro(dias, "Número de dias")
    validar_inteiro(semente, "Semente")
    gerador = Random(semente)
    atual = _sortear(inicial, gerador)
    caminho = [ESTADOS[atual]]
    for _ in range(dias):
        atual = _sortear(matriz[atual], gerador)
        caminho.append(ESTADOS[atual])
    return caminho


@dataclass(frozen=True)
class Experimento:
    dias: int
    repeticoes: int
    semente: int
    teorica: Distribuicao
    contagens: tuple[int, int, int]
    frequencias: Distribuicao
    erros: Distribuicao
    erros_padrao: Distribuicao


def comparar(
    inicial: Distribuicao,
    dias: int,
    repeticoes: int,
    *,
    semente: int = 42,
    matriz: Matriz,
) -> Experimento:
    """Simula trajetórias independentes e conta somente o último dia de cada uma."""
    inicial = validar_distribuicao(inicial)
    matriz = validar_matriz(matriz)
    validar_inteiro(dias, "Número de dias")
    validar_inteiro(repeticoes, "Quantidade de trajetórias", minimo=1)
    validar_inteiro(semente, "Semente")
    teorica = evolucao(inicial, dias, matriz)[-1]
    gerador = Random(semente)
    contagens = [0, 0, 0]
    for _ in range(repeticoes):
        atual = _sortear(inicial, gerador)
        for _ in range(dias):
            atual = _sortear(matriz[atual], gerador)
        contagens[atual] += 1
    frequencias = tuple(contagem / repeticoes for contagem in contagens)
    erros = tuple(abs(observada - prevista) for observada, prevista in zip(frequencias, teorica))
    erros_padrao = tuple(sqrt(max(0.0, p * (1 - p)) / repeticoes) for p in teorica)
    return Experimento(
        dias, repeticoes, semente, teorica, tuple(contagens), frequencias, erros, erros_padrao
    )
