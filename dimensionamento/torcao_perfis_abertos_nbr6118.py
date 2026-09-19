"""Flexo-torção de perfis abertos de parede fina (NBR 6118:2026, 17.5.2).

Quando o elemento estrutural sob torção puder ser assimilado a um perfil
aberto de parede fina (I, C, Z, U e análogos — típico de pré-moldados), o
projeto deve considerar, além da torção uniforme de Saint-Venant (já coberta
por torcao_nbr6118.py, com a seção vazada equivalente de 17.5.1.4.1), também
os efeitos da flexo-torção (17.5.2.1/17.5.2.2, PDF p. 162; 17.5.2.3/17.5.2.4,
PDF p. 163).

A norma permite compatibilizar os dois mecanismos dividindo entre si o
carregamento externo de forma variável ao longo do elemento, e permite
desprezar um deles desde que o mecanismo considerado não tenha rigidez menor
que o desprezado (17.5.2.2).

Este módulo não recalcula flechas de viga nem seções: recebe as flechas ou
as forças/resistências das paredes isoladas (já calculadas pelo projetista,
com metade da rigidez elástica de cada parede e a largura colaborante bf de
cada parede — 14.6.2.2, largura_colaborante_cm em analise_linear_nbr6118.py,
pacote P14) e aplica as expressões de 17.5.2.2 a 17.5.2.4.

Convenções: ver dimensionamento/nucleo_nbr6118.py. Comprimentos em cm,
forças em kN, momentos em kN·cm, ângulos em rad. Texto para o usuário em
português com acento.
"""

from __future__ import annotations

from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError


# ---------------------------------------------------------------------------
# 17.5.2.1/17.5.2.2 — generalidades e rigidezes reduzidas (PDF p. 162)
# ---------------------------------------------------------------------------
FATOR_RIGIDEZ_TORCAO_UNIFORME = 0.15
"""17.5.2.2: fração da rigidez elástica à torção uniforme considerada com a
fissuração (PDF p. 162)."""

FATOR_RIGIDEZ_FLEXO_TORCAO = 0.50
"""17.5.2.2: fração da rigidez elástica à flexo-torção considerada com a
fissuração (PDF p. 162)."""


@dataclass(frozen=True)
class RigidezesReduzidas:
    """Rigidezes à torção uniforme e à flexo-torção, reduzidas pela
    fissuração (17.5.2.2)."""

    rigidez_torcao_uniforme_reduzida_kncm2: float
    rigidez_flexo_torcao_reduzida_kncm_por_rad: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def rigidezes_reduzidas(
    rigidez_elastica_torcao_uniforme_kncm2: float,
    rigidez_elastica_flexo_torcao_kncm_por_rad: float,
) -> RigidezesReduzidas:
    """Rigidezes reduzidas por fissuração de um perfil aberto de parede fina
    sob torção uniforme + flexo-torção (17.5.2.1/17.5.2.2, PDF p. 162).

    No caso geral, a torção uniforme e a flexo-torção manifestam-se de forma
    compatibilizada, dividindo entre si o carregamento externo. Os valores
    de rigidez devem ser calculados considerando os efeitos da fissuração:

        rigidez_torcao_uniforme_reduzida = 0,15 * rigidez_elástica_torção_uniforme
        rigidez_flexo_torcao_reduzida    = 0,50 * rigidez_elástica_flexo_torção

    A norma permite desprezar um dos dois mecanismos, desde que o mecanismo
    considerado (mantido) não tenha rigidez menor que o desprezado; por isso
    `governante` aqui informa qual dos dois valores reduzidos é o maior — é
    esse o que pode ficar sozinho se o projetista optar por desprezar o
    outro. A função não decide sozinha desprezar nada: apenas calcula os
    dois valores para o projetista comparar.

    rigidez_elastica_torcao_uniforme_kncm2: rigidez elástica à torção
    uniforme (GJ, sem fissuração), kN.cm2.
    rigidez_elastica_flexo_torcao_kncm_por_rad: rigidez elástica à
    flexo-torção (r = T/theta, 17.5.2.3, sem fissuração), kN.cm/rad.

    Faixa: as duas rigidezes elásticas de entrada devem ser >= 0.
    """
    if rigidez_elastica_torcao_uniforme_kncm2 < 0.0:
        raise FaixaNormativaError(
            "rigidez_elastica_torcao_uniforme_kncm2 = "
            f"{rigidez_elastica_torcao_uniforme_kncm2:g} não pode ser "
            "negativa (17.5.2.2)."
        )
    if rigidez_elastica_flexo_torcao_kncm_por_rad < 0.0:
        raise FaixaNormativaError(
            "rigidez_elastica_flexo_torcao_kncm_por_rad = "
            f"{rigidez_elastica_flexo_torcao_kncm_por_rad:g} não pode ser "
            "negativa (17.5.2.2)."
        )
    ru = FATOR_RIGIDEZ_TORCAO_UNIFORME * rigidez_elastica_torcao_uniforme_kncm2
    rf = FATOR_RIGIDEZ_FLEXO_TORCAO * rigidez_elastica_flexo_torcao_kncm_por_rad
    governante = "torcao_uniforme" if ru >= rf else "flexo_torcao"
    memoria = (
        "17.5.2.2: rigidez à torção uniforme reduzida = 0,15 x "
        f"{rigidez_elastica_torcao_uniforme_kncm2:g} = {ru:g} kN.cm2",
        "17.5.2.2: rigidez à flexo-torção reduzida = 0,50 x "
        f"{rigidez_elastica_flexo_torcao_kncm_por_rad:g} = {rf:g} kN.cm/rad",
        f"17.5.2.2: mecanismo de maior rigidez reduzida = {governante}",
    )
    return RigidezesReduzidas(ru, rf, True, governante, memoria)


# ---------------------------------------------------------------------------
# 17.5.2.3 — rigidez à flexo-torção de perfil com paredes opostas (PDF p. 163)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RigidezFlexoTorcao:
    """Rigidez estrutural r = T/theta à flexo-torção de um perfil com
    paredes opostas paralelas (17.5.2.3, Figura 17.5)."""

    theta_rad: float
    r_kncm_por_rad: float
    T_kncm: float
    z_cm: float
    a1_cm: float
    a2_cm: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def rigidez_flexo_torcao(
    a1_cm: float, a2_cm: float, z_cm: float, T_kncm: float
) -> RigidezFlexoTorcao:
    """Rigidez à flexo-torção r = T/theta de perfil com paredes opostas
    paralelas ou aproximadamente paralelas — casos I, C, Z, U e análogos
    (17.5.2.3, Figura 17.5, PDF p. 163).

        theta = (a1 + a2) / z
        r = T / theta

    T_kncm: momento externo que provoca torção, considerado aplicado no
    meio do vão, kN.cm.
    z_cm: distância entre os eixos das paredes 1 e 2, cm.
    a1_cm: flecha provocada pela flexão da parede 1 sob a força F = T/z.
    a2_cm: flecha provocada pela flexão da parede 2, sob a mesma força F =
    T/z de sentido oposto ao que se aplica à parede 1.

    No cálculo de a1_cm e a2_cm (fora deste módulo — depende da rigidez à
    flexão isolada de cada parede, cada uma com sua largura colaborante bf,
    14.6.2.2, pacote P14), deve ser considerada metade da rigidez elástica
    de cada parede.

    Faixa: z_cm > 0; a1_cm >= 0; a2_cm >= 0; a1_cm + a2_cm > 0 (theta = 0
    torna r indefinido).
    """
    if z_cm <= 0.0:
        raise FaixaNormativaError(
            f"z_cm = {z_cm:g} cm não é uma distância válida entre eixos de "
            "paredes opostas (17.5.2.3): deve ser positiva."
        )
    if a1_cm < 0.0 or a2_cm < 0.0:
        raise FaixaNormativaError(
            f"a1_cm = {a1_cm:g} cm, a2_cm = {a2_cm:g} cm: flecha não pode "
            "ser negativa (17.5.2.3)."
        )
    theta = (a1_cm + a2_cm) / z_cm
    if theta <= 0.0:
        raise FaixaNormativaError(
            f"theta = {theta:g} rad (a1 + a2 = 0): rigidez à flexo-torção "
            "indefinida (17.5.2.3) — as flechas não podem ser ambas nulas."
        )
    r = T_kncm / theta
    governante = "parede_1" if a1_cm >= a2_cm else "parede_2"
    memoria = (
        f"17.5.2.3: theta = (a1 + a2) / z = ({a1_cm:g} + {a2_cm:g}) / "
        f"{z_cm:g} = {theta:g} rad",
        f"17.5.2.3: r = T / theta = {T_kncm:g} / {theta:g} = {r:g} kN.cm/rad",
        f"17.5.2.3: parede mais flexível (governa a rotação) = {governante}",
    )
    return RigidezFlexoTorcao(theta, r, T_kncm, z_cm, a1_cm, a2_cm, True,
                               governante, memoria)


# ---------------------------------------------------------------------------
# 17.5.2.4 — resistência à flexo-torção (PDF p. 163)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResistenciaFlexoTorcao:
    """Resistência TRd à flexo-torção de todo o elemento estrutural, a
    partir da resistência à flexão das duas paredes opostas (17.5.2.4)."""

    delta_FRd_parede1_kn: float
    delta_FRd_parede2_kn: float
    delta_FRd_min_kn: float
    TRd_kncm: float
    z_cm: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def TRd_flexo_torcao(
    FRd_parede1_kn: float,
    FSd_parede1_kn: float,
    FRd_parede2_kn: float,
    FSd_parede2_kn: float,
    z_cm: float,
) -> ResistenciaFlexoTorcao:
    """Resistência à flexo-torção de todo o elemento estrutural, calculada
    a partir da resistência à flexão das paredes opostas (17.5.2.4, PDF
    p. 163).

        delta_FRd,i   = FRd,i - FSd,i    (parede i isolada, sem o efeito da
                                           torção)
        delta_FRd,min = min(delta_FRd,1, delta_FRd,2)
        TRd           = delta_FRd,min * z

    FRd_parede{1,2}_kn: força transversal que esgota a resistência da
    parede isolada, sem o efeito da torção, kN.
    FSd_parede{1,2}_kn: parcela da força transversal total aplicada ao
    elemento estrutural que cabe à parede isolada, sem o efeito da torção,
    kN.
    z_cm: distância entre os eixos das paredes 1 e 2, cm (mesma definição
    de rigidez_flexo_torcao).

    `governante` informa qual das duas paredes tem o menor excedente de
    resistência à flexão (a que comanda delta_FRd,min).

    Faixa: z_cm > 0. delta_FRd,min pode dar negativo (a parede isolada já
    estaria esgotada por flexão simples antes mesmo de somar a torção);
    nesse caso TRd <= 0 e `ok` vem False — a seção não tem folga alguma
    para resistir a flexo-torção adicional.
    """
    if z_cm <= 0.0:
        raise FaixaNormativaError(
            f"z_cm = {z_cm:g} cm não é uma distância válida entre eixos de "
            "paredes opostas (17.5.2.4): deve ser positiva."
        )
    delta1 = FRd_parede1_kn - FSd_parede1_kn
    delta2 = FRd_parede2_kn - FSd_parede2_kn
    delta_min = min(delta1, delta2)
    governante = "parede_1" if delta1 <= delta2 else "parede_2"
    TRd = delta_min * z_cm
    ok = TRd > 0.0
    memoria = (
        f"17.5.2.4: delta_FRd,1 = {FRd_parede1_kn:g} - {FSd_parede1_kn:g} "
        f"= {delta1:g} kN",
        f"17.5.2.4: delta_FRd,2 = {FRd_parede2_kn:g} - {FSd_parede2_kn:g} "
        f"= {delta2:g} kN",
        f"17.5.2.4: delta_FRd,min = {delta_min:g} kN (parede governante: "
        f"{governante})",
        f"17.5.2.4: TRd = delta_FRd,min x z = {delta_min:g} x {z_cm:g} = "
        f"{TRd:g} kN.cm",
    )
    return ResistenciaFlexoTorcao(delta1, delta2, delta_min, TRd, z_cm, ok,
                                   governante, memoria)
