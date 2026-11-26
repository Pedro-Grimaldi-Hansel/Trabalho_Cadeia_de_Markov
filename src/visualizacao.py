"""Gráficos vetoriais em SVG, sem bibliotecas externas."""

from html import escape

from .modelo import ESTADOS, NOMES, Distribuicao, Matriz
from .simulacao import Experimento

CORES = ("#ad6800", "#526c89", "#087d81")


def _texto(x: float, y: float, texto: str, **atributos: str) -> str:
    extras = " ".join(f'{chave.replace("_", "-")}="{escape(valor)}"' for chave, valor in atributos.items())
    return f'<text x="{x:.2f}" y="{y:.2f}" {extras}>{escape(texto)}</text>'


def _svg(identificador: str, titulo: str, descricao: str, corpo: str, altura: int = 410) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {altura}" '
        f'role="img" aria-labelledby="{identificador}-titulo {identificador}-descricao">'
        f'<title id="{identificador}-titulo">{escape(titulo)}</title>'
        f'<desc id="{identificador}-descricao">{escape(descricao)}</desc>'
        f'<rect width="960" height="{altura}" fill="white"/>'
        '<g font-family="Segoe UI, Arial, sans-serif" font-size="15" fill="#243238">'
        f'{corpo}</g></svg>'
    )


def grafico_evolucao(historico: list[Distribuicao]) -> str:
    dias = len(historico) - 1
    esquerda, topo, largura, altura = 84, 60, 830, 260
    partes = [_texto(84, 28, "Probabilidades ao longo dos dias", font_size="21", font_weight="600")]
    for percentual in range(0, 101, 20):
        y = topo + altura * (1 - percentual / 100)
        partes.append(f'<path d="M {esquerda} {y} h {largura}" stroke="#dce2e3" fill="none"/>')
        partes.append(_texto(70, y + 5, f"{percentual}%", text_anchor="end"))
    marcas = sorted({round(dias * i / 6) for i in range(7)})
    for dia in marcas:
        x = esquerda + largura * dia / max(1, dias)
        partes.append(_texto(x, 347, str(dia), text_anchor="middle"))
    partes.append(_texto(500, 374, "Dia", text_anchor="middle"))
    # Limita o tamanho da figura, preservando a tabela CSV completa.
    indices = sorted({round(dias * i / min(dias, 500)) for i in range(min(dias, 500) + 1)}) if dias else [0]
    for estado, cor in enumerate(CORES):
        pontos = " ".join(
            f'{esquerda + largura * dia / max(1, dias):.3f},{topo + altura * (1 - historico[dia][estado]):.3f}'
            for dia in indices
        )
        partes.append(f'<polyline points="{pontos}" fill="none" stroke="{cor}" stroke-width="3"/>')
        if dias == 0:
            partes.append(f'<circle cx="{esquerda}" cy="{topo + altura * (1 - historico[0][estado])}" r="4" fill="{cor}"/>')
        x = 190 + estado * 240
        partes.append(f'<path d="M {x} 397 h 26" stroke="{cor}" stroke-width="4"/>')
        partes.append(_texto(x + 35, 402, NOMES[estado]))
    return _svg("evolucao", "Evolução das probabilidades", "Eixo horizontal: dia. Eixo vertical: probabilidade de cada estado, entre zero e cem por cento.", "".join(partes), 425)


def grafico_comparacao(experimento: Experimento) -> str:
    partes = [_texto(84, 28, f"Teoria e simulação no dia {experimento.dias}", font_size="21", font_weight="600")]
    for percentual in range(0, 101, 20):
        y = 60 + 260 * (1 - percentual / 100)
        partes.append(f'<path d="M 84 {y} h 830" stroke="#dce2e3" fill="none"/>')
        partes.append(_texto(70, y + 5, f"{percentual}%", text_anchor="end"))
    for i in range(3):
        centro = 240 + i * 265
        for deslocamento, valor, cor in (
            (-64, experimento.teorica[i], "#087d81"),
            (5, experimento.frequencias[i], "#c47c34"),
        ):
            x, y = centro + deslocamento, 320 - 260 * valor
            partes.append(f'<rect x="{x}" y="{y:.3f}" width="58" height="{260 * valor:.3f}" fill="{cor}" rx="3"/>')
            partes.append(_texto(x + 29, y - 10, f"{100 * valor:.2f}%".replace(".", ","), text_anchor="middle", font_size="14"))
        partes.append(_texto(centro, 347, f"{ESTADOS[i]} · {NOMES[i]}", text_anchor="middle"))
    for x, cor, titulo in ((285, "#087d81", "Teoria"), (480, "#c47c34", "Simulação")):
        partes.append(f'<rect x="{x}" y="377" width="20" height="14" fill="{cor}" rx="2"/>')
        partes.append(_texto(x + 30, 390, titulo))
    return _svg("comparacao", "Comparação entre teoria e simulação", f"Frequências dos estados finais de {experimento.repeticoes} trajetórias independentes. Semente {experimento.semente}.", "".join(partes))


def diagrama_estados(matriz: Matriz) -> str:
    partes = [
        '<defs><marker id="seta-markov" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#52616b"/></marker></defs>'
    ]
    # Cada rótulo identifica origem e destino; as curvas opostas ficam separadas.
    ligacoes = (
        ("M 280 165 Q 480 45 680 165", 480, 100, 0, 1),
        ("M 680 215 Q 480 330 280 215", 480, 278, 1, 0),
        ("M 200 270 Q 190 450 400 520", 205, 420, 0, 2),
        ("M 430 455 Q 350 310 260 250", 345, 340, 2, 0),
        ("M 760 270 Q 770 450 560 520", 755, 420, 1, 2),
        ("M 530 455 Q 610 310 700 250", 615, 340, 2, 1),
        ("M 155 125 C 80 15 320 15 245 125", 200, 40, 0, 0),
        ("M 715 125 C 640 15 880 15 805 125", 760, 40, 1, 1),
        ("M 435 585 C 360 710 600 710 525 585", 480, 680, 2, 2),
    )
    for caminho, _, _, _, _ in ligacoes:
        partes.append(f'<path d="{caminho}" fill="none" stroke="#52616b" stroke-width="2.5" marker-end="url(#seta-markov)"/>')
    for i, (x, y) in enumerate(((200, 190), (760, 190), (480, 520))):
        partes.append(f'<circle cx="{x}" cy="{y}" r="75" fill="#f3f7f7" stroke="{CORES[i]}" stroke-width="3"/>')
        partes.append(_texto(x, y - 4, ESTADOS[i], text_anchor="middle", font_size="30", font_weight="700"))
        partes.append(_texto(x, y + 25, NOMES[i], text_anchor="middle", font_size="19"))
    for _, x, y, origem, destino in ligacoes:
        probabilidade = f"{100 * matriz[origem][destino]:.2f}%".replace(".", ",")
        rotulo = f"{ESTADOS[origem]} → {ESTADOS[destino]}  {probabilidade}"
        partes.append(_texto(x, y, rotulo, text_anchor="middle", font_size="18", stroke="white", stroke_width="7", paint_order="stroke", stroke_linejoin="round"))
    return _svg("diagrama", "Diagrama das transições", "Nove transições da matriz, com probabilidades e identificação de origem e destino em cada seta.", "".join(partes), 720)
