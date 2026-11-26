"""Estados e validação das entradas do modelo meteorológico."""

from math import fsum, isfinite
from numbers import Real
from typing import Sequence

ESTADOS = ("E", "N", "C")
NOMES = ("Ensolarado", "Nublado", "Chuvoso")
TOLERANCIA = 1e-9
Distribuicao = tuple[float, float, float]
Matriz = tuple[Distribuicao, Distribuicao, Distribuicao]

def validar_distribuicao(
    valores: Sequence[float], nome: str = "Distribuição inicial"
) -> Distribuicao:
    """Valida sem normalizar ou corrigir silenciosamente as probabilidades."""
    if isinstance(valores, (str, bytes)) or not isinstance(valores, Sequence):
        raise ValueError(f"{nome}: informe três probabilidades na ordem E, N, C.")
    if len(valores) != 3:
        raise ValueError(f"{nome}: são necessárias três probabilidades (E, N, C).")
    for valor in valores:
        if isinstance(valor, bool) or not isinstance(valor, Real):
            raise ValueError(f"{nome}: as probabilidades devem ser números.")
        if not isfinite(valor) or not 0 <= valor <= 1:
            raise ValueError(f"{nome}: cada probabilidade deve ser finita e estar entre 0 e 1.")
    resultado = tuple(float(valor) for valor in valores)
    if abs(fsum(resultado) - 1.0) > TOLERANCIA:
        raise ValueError(f"{nome}: a soma das probabilidades deve ser 1.")
    return resultado


def validar_matriz(matriz: Sequence[Sequence[float]]) -> Matriz:
    if isinstance(matriz, (str, bytes)) or not isinstance(matriz, Sequence):
        raise ValueError("A matriz deve ter três linhas e três colunas.")
    if len(matriz) != 3:
        raise ValueError("A matriz deve ter três linhas e três colunas.")
    return tuple(
        validar_distribuicao(linha, f"Linha {ESTADOS[i]} da matriz")
        for i, linha in enumerate(matriz)
    )


def validar_inteiro(valor: int, nome: str, minimo: int = 0) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < minimo:
        raise ValueError(f"{nome} deve ser um inteiro maior ou igual a {minimo}.")
    return valor


def inicial_por_estado(estado: str) -> Distribuicao:
    if not isinstance(estado, str) or estado.upper() not in ESTADOS:
        raise ValueError("Estado inicial inválido. Escolha E, N ou C.")
    return tuple(1.0 if item == estado.upper() else 0.0 for item in ESTADOS)
