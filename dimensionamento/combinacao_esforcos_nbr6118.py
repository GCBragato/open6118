"""Solicitações combinadas -- Flexão, cortante e torção (NBR 6118:2026, 17.7).

Módulo novo do pacote P16. Reúne as regras de 17.7 que juntam a torção (ver
``torcao_nbr6118``) com a flexão e a força cortante de uma viga real: a soma
da armadura longitudinal de torção com a de flexão na zona tracionada
(17.7.1.2, PDF p. 164), a tensão principal de compressão no banzo comprimido
quando torção e solicitações normais atuam juntas (17.7.1.4, PDF p. 164) e a
soma das armaduras transversais calculadas separadamente para força cortante
e para torção (17.7.2.3, PDF p. 165). A combinação VSd/VRd2 + TSd/TRd2 <= 1
(17.7.2.2) já está em ``torcao_nbr6118.verifica_combinacao`` (P16 anterior;
não duplicada aqui).

Grandezas de material vêm do núcleo (``nucleo_nbr6118``); esta biblioteca não
reimplementa fcd, fctd, fywd etc.

Convenções (iguais às do núcleo):
    - fck, fyk, tensões normais em MPa; esforços em kN e kN.cm; seção em cm,
      área de aço em cm2 (ou cm2/m para armadura por unidade de comprimento).
    - Função de fórmula devolve float; verificação devolve
      ``@dataclass(frozen=True)`` com ``ok``, ``governante`` e ``memoria``.
    - Fora da faixa de validade, ``FaixaNormativaError`` (nunca um número).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
    import seguranca_nbr6118 as _seg
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr
    from dimensionamento import seguranca_nbr6118 as _seg

FaixaNormativaError = nbr.FaixaNormativaError


def _fmt(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


# ---------------------------------------------------------------------------
# 17.7.1.2 -- soma da armadura longitudinal de torção com a de flexão
# (PDF p. 164)
# ---------------------------------------------------------------------------
def As_longitudinal_total(As_flexao_cm2: float,
                          As_torcao_cm2: float) -> float:
    """As total de uma face, na zona tracionada pela flexão (17.7.1.2, PDF
    p. 164, cm2).

    "Na zona tracionada pela flexão, a armadura de torção deve ser
    acrescentada à armadura necessária para as solicitações normais,
    considerando-se em cada seção os esforços que agem concomitantemente."
    Isto é:

        As,total = As,flexão + As,torção

    onde As,flexão é a armadura de flexão já dimensionada para aquela face
    (ex.: ``rotinas.flexao_simples``) e As,torção é a parcela da armadura
    longitudinal de torção correspondente àquela face (ex.: 1/4 de
    ``torcao_nbr6118.dimensionar_torcao(...).As_long_total_cm2`` numa seção
    retangular com 4 lados, ou o valor por trecho de
    ``torcao_nbr6118.distribuir_armadura_longitudinal_torcao``). Esta função
    não reimplementa nenhum dos dois dimensionamentos: recebe os dois
    valores já calculados e soma.
    """
    if As_flexao_cm2 < 0.0 or As_torcao_cm2 < 0.0:
        raise FaixaNormativaError(
            "As_flexao_cm2 e As_torcao_cm2 têm de ser não negativos "
            "(17.7.1.2)."
        )
    return As_flexao_cm2 + As_torcao_cm2


# ---------------------------------------------------------------------------
# 17.7.2.3 -- soma das armaduras transversais calculadas separadamente para
# V e T (PDF p. 165)
# ---------------------------------------------------------------------------
def Asw_total(Asw_V_cm2_por_m: float, Asw_T_cm2_por_m: float) -> float:
    """Asw total do estribo, cm2/m (17.7.2.3, PDF p. 165).

    "A armadura transversal pode ser calculada pela soma das armaduras
    calculadas separadamente para VSd e TSd." Isto é:

        Asw,total/s = Asw,cortante/s + Asw,torção/s

    Asw_V_cm2_por_m vem de ``cortante_nbr6118`` (Asw/s da força cortante,
    modelo I ou II) e Asw_T_cm2_por_m vem de
    ``torcao_nbr6118.Asw_torcao_cm2_por_m``. 17.7.2.1 exige também que os
    dois cálculos usem o mesmo theta (17.7.2.1: "quando for utilizado o
    modelo I para a força cortante, que subentende theta = 45 graus, esse
    deve ser o valor considerado também para a torção"); a escolha de theta
    consistente é responsabilidade do chamador, que dimensiona V e T com o
    mesmo ângulo antes de chamar esta função.
    """
    if Asw_V_cm2_por_m < 0.0 or Asw_T_cm2_por_m < 0.0:
        raise FaixaNormativaError(
            "Asw_V_cm2_por_m e Asw_T_cm2_por_m têm de ser não negativos "
            "(17.7.2.3)."
        )
    return Asw_V_cm2_por_m + Asw_T_cm2_por_m


# ---------------------------------------------------------------------------
# 17.7.1.4 -- tensão principal de compressão no banzo comprimido, sob
# flexão (ou flexo-compressão) + torção (PDF p. 164)
# ---------------------------------------------------------------------------
def tau_Td_kncm2(TSd_kncm: float, Ae_cm2: float, he_cm: float) -> float:
    """Tensão tangencial de torção no banzo, kN/cm2 (17.7.1.4, PDF p. 164):

        tau_Td = Td / (2 * Ae * he)

    TSd_kncm em kN.cm; Ae_cm2 e he_cm da seção vazada (equivalente ou real)
    de 17.5.1.4, no ponto considerado.
    """
    if Ae_cm2 <= 0.0 or he_cm <= 0.0:
        raise FaixaNormativaError(
            "Ae_cm2 e he_cm têm de ser positivos (17.7.1.4)."
        )
    return TSd_kncm / (2.0 * Ae_cm2 * he_cm)


@dataclass(frozen=True)
class ResultadoTensaoPrincipalBanzo:
    """17.7.1.4: tensão principal de compressão no banzo comprimido."""

    sigma_cd_mpa: float
    TSd_kncm: float
    Ae_cm2: float
    he_cm: float
    tau_Td_mpa: float
    sigma_c_principal_mpa: float
    sigma_limite_mpa: float | None
    ok: bool | None
    governante: str
    memoria: tuple[str, ...]


def tensao_principal_banzo_comprimido(
    sigma_cd_mpa: float,
    TSd_kncm: float,
    Ae_cm2: float,
    he_cm: float,
    sigma_limite_mpa: float | None = None,
) -> ResultadoTensaoPrincipalBanzo:
    """Tensão principal de compressão no banzo comprimido, sob flexão (ou
    flexo-compressão) combinada com torção (17.7.1.4, PDF p. 164).

    "Nas seções em que a torção atua simultaneamente com solicitações
    normais intensas, que reduzem excessivamente a profundidade da linha
    neutra, particularmente em vigas de seção celular, o valor de cálculo
    da tensão principal de compressão não pode superar os valores
    estabelecidos na Seção 22. Essa tensão principal deve ser calculada
    como em um estado plano de tensões, a partir da tensão normal média que
    age no banzo comprimido de flexão e da tensão tangencial de torção
    calculada por": tau_Td = Td / (2 Ae he).

    Estado plano de tensões (Mohr), com sigma_cd_mpa a tensão normal média
    de compressão (positiva) no banzo e tau_Td a tensão tangencial de
    torção: a tensão principal de compressão (em módulo) é

        sigma_c,principal = sigma_cd/2 + sqrt((sigma_cd/2)^2 + tau_Td^2)

    Caso sem torção (TSd = 0): tau_Td = 0 -> sigma_c,principal = sigma_cd, a
    verificação recai na flexão pura (o teste do pacote confere isso).

    O limite (Seção 22) é dependência de outro pacote e não está
    implementado aqui: quando sigma_limite_mpa é informado, a função
    compara (Rd >= Sd via seguranca_nbr6118.verificar_seguranca) e devolve
    ``ok``; quando None (padrão), devolve só o valor calculado, com
    ``ok = None`` (verificação incompleta, falta o limite).
    """
    tau_kncm2 = tau_Td_kncm2(TSd_kncm, Ae_cm2, he_cm)
    tau_mpa = tau_kncm2 * 10.0
    sigma_c_principal = (sigma_cd_mpa / 2.0
                         + math.sqrt((sigma_cd_mpa / 2.0) ** 2 + tau_mpa ** 2))

    if sigma_limite_mpa is None:
        ok = None
        governante = ("17.7.1.4: sigma_c,principal calculada; falta o "
                     "limite da Seção 22 para concluir a verificação")
        seg_memoria: tuple[str, ...] = ()
    else:
        seg = _seg.verificar_seguranca(sigma_limite_mpa, sigma_c_principal,
                                       "sigma_c,principal x limite (Seção 22)",
                                       "17.7.1.4")
        ok = seg.ok
        governante = (f"17.7.1.4: sigma_c,principal <= limite (Seção 22) -> "
                     f"{'ok' if ok else 'não ok'}")
        seg_memoria = seg.memoria

    memoria = (
        f"17.7.1.4: sigma_cd = {_fmt(sigma_cd_mpa)} MPa; "
        f"TSd = {_fmt(TSd_kncm)} kN.cm; Ae = {_fmt(Ae_cm2)} cm2; "
        f"he = {_fmt(he_cm)} cm.",
        f"17.7.1.4: tau_Td = TSd/(2.Ae.he) = {_fmt(TSd_kncm)} / "
        f"(2 x {_fmt(Ae_cm2)} x {_fmt(he_cm)}) = {_fmt(tau_kncm2)} kN/cm2 "
        f"= {_fmt(tau_mpa)} MPa.",
        f"17.7.1.4: sigma_c,principal = sigma_cd/2 + "
        f"raiz((sigma_cd/2)^2 + tau_Td^2) = {_fmt(sigma_cd_mpa / 2.0)} + "
        f"raiz({_fmt((sigma_cd_mpa / 2.0) ** 2)} + {_fmt(tau_mpa ** 2)}) = "
        f"{_fmt(sigma_c_principal)} MPa.",
        governante + ".",
        *seg_memoria,
    )
    return ResultadoTensaoPrincipalBanzo(
        sigma_cd_mpa=sigma_cd_mpa, TSd_kncm=TSd_kncm, Ae_cm2=Ae_cm2,
        he_cm=he_cm, tau_Td_mpa=tau_mpa,
        sigma_c_principal_mpa=sigma_c_principal,
        sigma_limite_mpa=sigma_limite_mpa, ok=ok, governante=governante,
        memoria=memoria,
    )


def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def _demo() -> None:
    print("=== As,long total (17.7.1.2) ===")
    print(f"  As,flexao=8,0 + As,torcao=2,5 -> "
          f"{As_longitudinal_total(8.0, 2.5):.2f} cm2")
    print("=== Asw total (17.7.2.3) ===")
    print(f"  Asw,V=4,5 + Asw,T=6,12 -> "
          f"{Asw_total(4.5, 6.12):.2f} cm2/m")
    print("=== Tensão principal do banzo (17.7.1.4) ===")
    r = tensao_principal_banzo_comprimido(10.0, 6808.0, 1000.0, 10.0)
    print(f"  tau_Td = {r.tau_Td_mpa:.3f} MPa; "
          f"sigma_c,principal = {r.sigma_c_principal_mpa:.3f} MPa")


if __name__ == "__main__":
    _demo()
