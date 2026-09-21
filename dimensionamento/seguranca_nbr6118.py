"""Verificação de segurança — ABNT NBR 6118:2026, 10.3, 11.8.2.1 e 12.5.2.

Lugar único para:
    - o checklist dos estados-limites últimos a verificar (10.3, a a h,
      PDF p. 74-75);
    - a condição analítica geral de segurança Rd >= Sd (12.5.2, PDF p. 92),
      que todo módulo de verificação e dimensionamento reaproveita;
    - a verificação de perda de equilíbrio como corpo rígido (11.8.2.1,
      Tabela 11.3, PDF p. 87-88), caso particular de Rd >= Sd com as ações
      estabilizante (Fsd) e não estabilizante (Fnd) da própria tabela.

Norma: ABNT NBR 6118:2026. As páginas citadas são as do PDF (a página
impressa é 18 a menos). Os coeficientes γg, γq da Tabela 11.1 são
reaproveitados de ``acoes_nbr6118`` (P4); este módulo não reimplementa a
tabela.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

try:
    import nucleo_nbr6118 as nbr
    import acoes_nbr6118 as ac
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr
    from dimensionamento import acoes_nbr6118 as ac

FaixaNormativaError = nbr.FaixaNormativaError

_TOL = 1e-9


def _fmt(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


# ---------------------------------------------------------------------------
# 10.3 — Estados-limites últimos a verificar (PDF p. 74-75)
# ---------------------------------------------------------------------------
ESTADOS_LIMITES_ULTIMOS = {
    "a": "Perda do equilíbrio da estrutura, admitida como corpo rígido.",
    "b": ("Esgotamento da capacidade resistente da estrutura, no seu todo ou "
          "em parte, devido às solicitações normais e tangenciais."),
    "c": ("Esgotamento da capacidade resistente da estrutura, no seu todo ou "
          "em parte, considerando os efeitos de 2ª ordem."),
    "d": "Estado-limite último provocado por solicitações dinâmicas (Seção 23).",
    "e": "Estado-limite último de colapso progressivo.",
    "f": ("Esgotamento da capacidade resistente da estrutura, no seu todo ou "
          "em parte, considerando exposição ao fogo, conforme a ABNT NBR 15200."),
    "g": ("Esgotamento da capacidade resistente da estrutura, considerando "
          "ações sísmicas, de acordo com a ABNT NBR 15421."),
    "h": "Outros estados-limites últimos que eventualmente possam ocorrer em casos especiais.",
}


def checklist_elu(verificados: Iterable[str]) -> list[str]:
    """Linhas de memória de cálculo com os 8 ELU de 10.3 (a a h, PDF p. 74-75).

    ``verificados`` é o conjunto de letras ('a' a 'h') já checadas pelo
    chamador, por outro módulo ou por decisão de projeto (ex.: 2ª ordem
    verificada por P26/P46, esgotamento por flexão pelos módulos de
    dimensionamento). Letra fora de {'a', ..., 'h'} levanta ``ValueError``.
    Devolve uma linha de título e uma por estado-limite, com '[x]' ou '[ ]'.
    """
    verificados = {str(v).strip().lower() for v in verificados}
    desconhecidas = verificados - set(ESTADOS_LIMITES_ULTIMOS)
    if desconhecidas:
        raise ValueError(
            f"Estado-limite último desconhecido: {sorted(desconhecidas)}. "
            "Use letras de 'a' a 'h' (10.3)."
        )
    linhas = ["Estados-limites últimos a verificar (10.3, PDF p. 74-75):"]
    for letra, texto in ESTADOS_LIMITES_ULTIMOS.items():
        marca = "[x]" if letra in verificados else "[ ]"
        linhas.append(f"  {marca} {letra}) {texto}")
    return linhas


# ---------------------------------------------------------------------------
# 12.5.2 — Condição analítica geral de segurança, Rd >= Sd (PDF p. 92)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoSeguranca:
    """Resultado da condição Rd >= Sd (12.5.2)."""

    Rd: float
    Sd: float
    rotulo: str
    item: str
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_seguranca(Rd: float, Sd: float, rotulo: str = "",
                        item: str = "12.5.2") -> ResultadoSeguranca:
    """Condição analítica geral de segurança Rd >= Sd, tolerância 1e-9 (12.5.2, PDF p. 92).

    "As condições analíticas de segurança estabelecem que as resistências não
    podem ser menores que as solicitações [...] deve ser respeitada a
    condição: Rd >= Sd." Rd e Sd têm de estar na mesma unidade e se referir ao
    mesmo efeito (o mesmo esforço, na mesma seção). Rd == Sd passa (a
    igualdade é o limite, não a falha, com tolerância numérica de 1e-9); Rd
    menor que Sd, mesmo por 1e-6, não passa.

    ``rotulo`` identifica a verificação na memória de cálculo (ex.:
    'Md x MRd', 'Vsd x VRd2'); ``item`` é o item da norma que a chama — o
    padrão é 12.5.2 (a condição geral), e outros módulos de verificação ou
    dimensionamento podem passar o item deles (ex. '17.4.2.2' para VRd2 da
    força cortante), porque a condição Rd >= Sd é sempre a mesma daqui.
    """
    rd, sd = float(Rd), float(Sd)
    ok = rd >= sd - _TOL
    rot = f"{rotulo}: " if rotulo else ""
    governante = f"{rot}Rd >= Sd" if ok else f"{rot}Rd < Sd — não passa"
    memoria = (
        f"{item} (Rd >= Sd): Rd = {_fmt(rd)}, Sd = {_fmt(sd)}"
        f"{f', {rotulo}' if rotulo else ''}.",
        f"Rd >= Sd: {_fmt(rd)} >= {_fmt(sd)} -> {'ok' if ok else 'não ok'}.",
    )
    return ResultadoSeguranca(rd, sd, rotulo, item, ok, governante, memoria)


# ---------------------------------------------------------------------------
# 11.8.2.1, Tabela 11.3 — Perda de equilíbrio como corpo rígido (PDF p. 87-88)
# ---------------------------------------------------------------------------
def fsd_equilibrio(Gsk: float, Rd: float = 0.0, combinacao: str = "normal",
                   gama_gs: float | None = None) -> float:
    """Fsd = γgs·Gsk + Rd, ação estabilizante de cálculo (Tabela 11.3, PDF p. 87-88).

    Gsk é o valor característico da ação permanente estabilizante; Rd é o
    esforço resistente considerado estabilizante, quando houver (ex.: atrito
    de base, ancoragem), já de cálculo — a Tabela 11.3 não dá coeficiente
    próprio para ele. γgs é o γg **favorável** de 11.7.1 (Tabela 11.1, coluna
    g, F): a nota de rodapé da Tabela 11.3 remete γg, γq à Tabela 11.1, e
    para a parcela estabilizante da ação permanente o valor cabível é o
    favorável. Sem ``gama_gs``, usa ``acoes_nbr6118.gama_f_tabela_11_1``
    com a ``combinacao`` pedida ('normal', 'especial'/'construcao' ou
    'excepcional'); nas três, γg,F = 1,0.
    """
    g_gs = (ac.gama_f_tabela_11_1(combinacao, "permanente", "F") if gama_gs is None
            else float(gama_gs))
    return g_gs * float(Gsk) + float(Rd)


def fnd_equilibrio(Gnk: float, Qnk: float, Qs_min: float = 0.0,
                   combinacao: str = "normal", gama_gn: float | None = None,
                   gama_q: float | None = None, gama_qs: float = 1.0) -> float:
    """Fnd = γgn·Gnk + γq·Qnk − γqs·Qs,mín, ação não estabilizante de cálculo (Tabela 11.3, PDF p. 87-88).

    Gnk é o valor característico da ação permanente instabilizante; Qnk é o
    valor característico das ações variáveis instabilizantes
    (Qnk = Q1k + Σψ0j·Qjk, com Q1k a variável instabilizante principal e ψ0j
    da Tabela 11.2 — monte Qnk com ``acoes_nbr6118`` antes de chamar esta
    função); Qs,mín é o valor característico mínimo da ação variável
    estabilizante que acompanha obrigatoriamente a instabilizante.

    γgn é o γg **desfavorável** de 11.7.1 (Tabela 11.1, coluna g, D: 1,4 na
    combinação normal, reduzido a 1,3 pela nota a — ``nucleo_nbr6118.GAMA_G``
    — ou 1,3/1,2 nas combinações especial/construção/excepcional); γq é o γq
    da Tabela 11.1 (coluna q, G: 1,4/1,2/1,0 conforme a combinação). Sem
    ``gama_gn``/``gama_q``, os dois vêm de
    ``acoes_nbr6118.gama_f_tabela_11_1`` com a ``combinacao`` pedida.

    γqs pondera Qs,mín: nem a Tabela 11.3 nem a Tabela 11.1 dão um valor
    próprio para ele (a nota de rodapé da Tabela 11.3 só remete γg, γq à
    Tabela 11.1; γqs não é um deles). O padrão adotado aqui é 1,0 — Qs,mín
    entra inteiro, sem redução, subtraindo o máximo possível de Fnd. Atenção:
    isso é o lado **menos** conservador (Fnd menor, mais folga contra a perda
    de equilíbrio), porque Qs,mín é a ação variável estabilizante que
    acompanha a instabilizante, e reduzi-la a favor da segurança significaria
    usar um γqs **menor** que 1,0 (subtrai menos, Fnd fica maior). O valor
    1,0 foi mantido como padrão por não haver, na norma, um γqs próprio nem
    indicação de reduzi-lo; quem quiser o lado mais conservador informa
    ``gama_qs`` explícito, menor que 1,0.
    """
    g_gn = (ac.gama_f_tabela_11_1(combinacao, "permanente", "D") if gama_gn is None
            else float(gama_gn))
    g_q = (ac.gama_f_tabela_11_1(combinacao, "variavel", "G") if gama_q is None
           else float(gama_q))
    return g_gn * float(Gnk) + g_q * float(Qnk) - float(gama_qs) * float(Qs_min)


def verificar_equilibrio_corpo_rigido(F_estabilizante: float,
                                      F_desestabilizante: float) -> ResultadoSeguranca:
    """Verifica S(Fsd) >= S(Fnd), perda de equilíbrio como corpo rígido (11.8.2.1, Tabela 11.3, PDF p. 87-88).

    Reaproveita ``verificar_seguranca`` (12.5.2): a norma trata a perda de
    equilíbrio como corpo rígido como caso particular da condição geral
    Rd >= Sd (12.5.2, "Para a verificação do estado-limite último de perda de
    equilíbrio como corpo rígido, Rd e Sd devem assumir os valores de cálculo
    das ações estabilizantes e desestabilizantes respectivamente."); aqui
    Rd = Fsd (``fsd_equilibrio``) e Sd = Fnd (``fnd_equilibrio``), já
    calculados pelo chamador.
    """
    return verificar_seguranca(
        F_estabilizante, F_desestabilizante,
        rotulo="Fsd x Fnd (perda de equilíbrio como corpo rígido)",
        item="11.8.2.1",
    )
