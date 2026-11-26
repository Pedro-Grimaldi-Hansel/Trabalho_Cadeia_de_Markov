"""Análise de uma cadeia de Markov para o tempo em Juiz de Fora."""

import argparse
from pathlib import Path

from .analise import distribuicao_estacionaria, evolucao
from .dados import ajustar_e_avaliar, carregar_base
from .modelo import ESTADOS, inicial_por_estado, validar_distribuicao
from .relatorio import exportar, percentual
from .simulacao import comparar, simular_trajetoria

RAIZ = Path(__file__).resolve().parent.parent


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cadeia de Markov para o tempo em Juiz de Fora, com histórico Open-Meteo / ERA5.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dias", type=int, default=30, help="Número de transições diárias; zero é permitido.")
    inicio = parser.add_mutually_exclusive_group()
    inicio.add_argument("--estado", type=str.upper, choices=ESTADOS, default="E", help="Estado inicial: E (ensolarado), N (nublado) ou C (chuvoso).")
    inicio.add_argument("--inicial", nargs=3, type=float, metavar=("E", "N", "C"), help="Probabilidades iniciais na ordem E, N, C, com soma 1. Use ponto decimal.")
    parser.add_argument("--repeticoes", type=int, default=10000, help="Quantidade de trajetórias independentes.")
    parser.add_argument("--semente", type=int, default=42, help="Semente inteira não negativa para reproduzir os sorteios.")
    parser.add_argument("--saida", type=Path, help="Pasta de saída; padrão: resultados/juiz_de_fora na raiz do projeto.")
    parser.add_argument("--demo", action="store_true", help="Inclui 12 cenários: 1, 2, 7 e 30 dias com 100, 1.000 e 10.000 trajetórias.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = criar_parser()
    args = parser.parse_args(argv)
    try:
        inicial = validar_distribuicao(args.inicial) if args.inicial is not None else inicial_por_estado(args.estado)
        diario, fonte = carregar_base()
        ajuste = ajustar_e_avaliar(diario)
        matriz = ajuste["matriz"]
        historico = evolucao(inicial, args.dias, matriz)
        caminho = simular_trajetoria(inicial, args.dias, semente=args.semente, matriz=matriz)
        selecionado = comparar(inicial, args.dias, args.repeticoes, semente=args.semente, matriz=matriz)
        experimentos = []
        if args.demo:
            for dias in (1, 2, 7, 30):
                for repeticoes in (100, 1000, 10000):
                    experimento = selecionado if (dias, repeticoes) == (args.dias, args.repeticoes) else comparar(
                        inicial, dias, repeticoes, semente=args.semente, matriz=matriz
                    )
                    experimentos.append(experimento)
        if selecionado not in experimentos:
            experimentos.append(selecionado)
        pasta = args.saida if args.saida is not None else RAIZ / "resultados" / "juiz_de_fora"
        arquivos = exportar(pasta, inicial, historico, caminho, experimentos, selecionado,
                            matriz=matriz, contexto={"fonte": fonte, "ajuste": ajuste}, demonstracao=args.demo)
    except (ValueError, OSError) as erro:
        parser.error(str(erro))

    print("CADEIA DE MARKOV | JUIZ DE FORA\n")
    print(f"Fonte: Open-Meteo / ERA5 (reanálise) | {fonte['dias']} dias na base")
    print(f"Treino: {ajuste['treino']['inicio']} a {ajuste['treino']['fim']}")
    print(f"Teste: {ajuste['teste']['inicio']} a {ajuste['teste']['fim']}")
    print("Cenário iniciado na distribuição escolhida; não representa o tempo atual.\n")
    print("Dia        Ensolarado      Nublado      Chuvoso")
    dias_exibidos = range(args.dias + 1) if args.dias <= 10 else sorted({0, 1, 2, 3, 7, args.dias})
    for dia in dias_exibidos:
        print(f"{dia:>3}     " + "  ".join(f"{percentual(p):>11}" for p in historico[dia]))
    print(f"\nSimulação no dia {args.dias} | {args.repeticoes} trajetórias | semente {args.semente}")
    for i, estado in enumerate(ESTADOS):
        print(f"{estado}: teoria {percentual(selecionado.teorica[i])}; simulação {percentual(selecionado.frequencias[i])}; erro {selecionado.erros[i] * 100:.3f} p.p.")
    print("\nDistribuição estacionária: " + "; ".join(
        f"{estado} = {percentual(p)}" for estado, p in zip(ESTADOS, distribuicao_estacionaria(matriz))
    ))
    print("\nAvaliação histórica de um dia em 2025 (menor Brier é melhor):")
    for nome, valores in ajuste["metricas"].items():
        print(f"{nome}: acurácia {percentual(valores['acuracia'])}; Brier {valores['brier']:.4f}")
    print("O erro da simulação e a avaliação histórica são medidas diferentes.")
    print(f"\n{len(experimentos)} cenário(s), {len(arquivos)} arquivos. Relatório: {(pasta / 'relatorio.html').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
