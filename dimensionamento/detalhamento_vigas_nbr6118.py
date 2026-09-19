"""Detalhamento de vigas — ABNT NBR 6118:2026.

Parte 1, armadura longitudinal (P22 do plano de implementação).

Cobre:

- 18.2.2 — diâmetro interno mínimo de curvatura de barra longitudinal dobrada
  (para força cortante ou em nó de pórtico), PDF p. 166;
- 18.3.2.2 — espaçamento mínimo livre entre barras longitudinais de vigas,
  horizontal (ah) e vertical (av), PDF p. 168;
- 18.3.2.3.1 — cobertura do diagrama de força de tração solicitante pelo
  resistente (pontos A e B, decalagem aℓ, Figura 18.3), com o caso do ponto A
  na face do apoio, PDF p. 168-169;
- 18.3.2.3.2 — comprimento adicional das barras alojadas nas mesas, PDF p. 169;
- 18.3.2.4 b) — força de tração no apoio extremo, PDF p. 169;
- 18.3.2.4 c) — fração da armadura do vão levada ao apoio, PDF p. 170;
- 18.3.2.4.1 — comprimento de ancoragem a partir da face do apoio, PDF p. 170;
- 18.6.1.1 — força de tração da armadura em apoio intermediário, PDF p. 175.

Convenções: geometria e comprimentos em cm; diâmetro em mm; força em kN;
momento em kN·cm. Página do PDF citada em cada função (impressa = PDF − 18).
Fora da faixa de validade, as funções levantam ``FaixaNormativaError`` (do
núcleo). Os insumos que são de outros pacotes entram como parâmetro: aℓ
(17.4.2, ``viga_servico_nbr6118.decalagem_modelo_I/II`` e P15), ℓb,nec
(9.4.2.5, ``ancoragem_nbr6118.comprimento_ancoragem``), o pino da Tabela 9.1
(``ancoragem_nbr6118.diametro_pino_gancho``, P21) e φn de feixe
(``nucleo_nbr6118.phi_n_feixe``, P24).

Parte 2, estribos, torção e suspensão (P23 do plano de implementação).

Cobre:

- 18.2.4 — proteção contra flambagem das barras longitudinais junto à
  superfície (trecho de 20·φt a partir do canto do estribo poligonal);
- 18.3.3.2 — estribos para força cortante: diâmetro mínimo e máximo, barra
  de amarração ou de canto, espaçamento longitudinal máximo (degrau em
  Vd/VRd2 = 0,67), espaçamento transversal máximo entre ramos (degrau em
  Vd/VRd2 = 0,20) e emenda por traspasse;
- 18.3.3.3.2 — espaçamento longitudinal máximo entre barras dobradas;
- 18.3.4 — armadura para torção: estribo fechado com ganchos a 135°,
  espaçamento de 350 mm das barras longitudinais, relação ΔAsl/Δu e uma
  barra em cada vértice;
- 18.3.6 — armadura de suspensão de viga apoiada em viga (75 % / 25 %,
  extensões h/2, fator de redução com faces superiores coincidentes e a
  classificação de viga pendurada);
- 18.3.7 — armadura mínima de ligação mesa-alma ou talão-alma (1,5 cm²/m).

A suspensão aqui é a de **viga apoiando viga** (18.3.6). A suspensão de
bloco sobre estacas é outra coisa e está em ``blocos_nbr6118`` (plano,
seção 8, risco 3): os nomes são diferentes de propósito.

Convenções: geometria em cm; diâmetro em mm; esforço em kN; área em cm² e
taxa em cm²/m; tensão em MPa. Página do PDF citada em cada função (impressa =
PDF - 18). Fora da faixa de validade, as funções levantam
``FaixaNormativaError`` (subclasse de ``ValueError``, do núcleo). Função de
verificação devolve ``@dataclass(frozen=True)`` com ``ok``, ``governante`` e
``memoria`` (a memória de cálculo). VRd2 vem de ``cortante_nbr6118``
(``modelo_calculo_I``/``modelo_calculo_II``, P15) e é recebido como
parâmetro; As,long/ue da torção vem de
``torcao_nbr6118.As_long_torcao_cm2_por_m``.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import Sequence

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
    import ancoragem_nbr6118 as anc
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr
    from dimensionamento import ancoragem_nbr6118 as anc

FaixaNormativaError = nbr.FaixaNormativaError


def _aco_padrao(aco: str) -> str:
    """Normaliza 'CA50', 'ca-50', 'CA 50' para 'CA-50'."""
    chave = nbr._chave(aco)
    mapa = {"ca25": "CA-25", "ca50": "CA-50", "ca60": "CA-60"}
    if chave not in mapa:
        raise FaixaNormativaError(
            f"Aço {aco!r} não previsto: a norma define CA-25, CA-50 e CA-60."
        )
    return mapa[chave]


def _fmt(v: float) -> str:
    return f"{v:.4g}".replace(".", ",")


# ---------------------------------------------------------------------------
# 18.3.2.2 — Espaçamento mínimo livre entre barras longitudinais (PDF p. 168)
# ---------------------------------------------------------------------------
ESPACAMENTO_LIVRE_MIN_ABSOLUTO_MM = 20.0   # 20 mm, nas duas direções
FATOR_DMAX_AH = 1.2   # 1,2 vez a dimensão máxima característica do agregado graúdo
FATOR_DMAX_AV = 0.5   # 0,5 vez a dimensão máxima característica do agregado graúdo


def _diametro_referencia_mm(phi_mm: float, n_barras_feixe: int,
                            phi_luva_mm: float | None) -> float:
    if phi_mm <= 0.0:
        raise FaixaNormativaError("φ deve ser positivo (18.3.2.2).")
    n = int(n_barras_feixe)
    if n < 1:
        raise FaixaNormativaError("n_barras_feixe deve ser >= 1 (18.3.2.2).")
    diam = nbr.phi_n_feixe(phi_mm, n) if n >= 2 else float(phi_mm)
    if phi_luva_mm is not None:
        if phi_luva_mm <= 0.0:
            raise FaixaNormativaError("Diâmetro da luva deve ser positivo (18.3.2.2).")
        diam = max(diam, float(phi_luva_mm))
    return diam


def _espacamento_min_cm(phi_mm, dmax_agregado_mm, n_barras_feixe, phi_luva_mm,
                        fator_dmax) -> float:
    if dmax_agregado_mm <= 0.0:
        raise FaixaNormativaError(
            "Dimensão máxima característica do agregado graúdo deve ser positiva "
            "(18.3.2.2)."
        )
    diam = _diametro_referencia_mm(phi_mm, n_barras_feixe, phi_luva_mm)
    return max(ESPACAMENTO_LIVRE_MIN_ABSOLUTO_MM, diam,
               fator_dmax * float(dmax_agregado_mm)) / 10.0


def ah_min_cm(phi_mm: float, dmax_agregado_mm: float, *, n_barras_feixe: int = 1,
              phi_luva_mm: float | None = None) -> float:
    """Espaçamento livre horizontal mínimo ah entre barras longitudinais de viga (18.3.2.2 a), PDF p. 168).

    ah >= máx(20 mm; diâmetro da barra, do feixe ou da luva; 1,2·dmáx)

    ``phi_mm``: diâmetro da barra (mm). ``n_barras_feixe`` >= 2: usa o
    diâmetro do feixe φn = φ·√n (``nucleo_nbr6118.phi_n_feixe``).
    ``phi_luva_mm``: diâmetro externo da luva, se houver (entra no máximo).
    ``dmax_agregado_mm``: dimensão máxima característica do agregado graúdo —
    obrigatória, porque a norma a exige em qualquer caso. Vale também nas
    regiões de emenda por traspasse. Devolve cm (máximo em mm dividido por 10).
    """
    return _espacamento_min_cm(phi_mm, dmax_agregado_mm, n_barras_feixe,
                               phi_luva_mm, FATOR_DMAX_AH)


def av_min_cm(phi_mm: float, dmax_agregado_mm: float, *, n_barras_feixe: int = 1,
              phi_luva_mm: float | None = None) -> float:
    """Espaçamento livre vertical mínimo av entre barras longitudinais de viga (18.3.2.2 b), PDF p. 168).

    av >= máx(20 mm; diâmetro da barra, do feixe ou da luva; 0,5·dmáx)

    Parâmetros como em ``ah_min_cm``. Devolve cm.
    """
    return _espacamento_min_cm(phi_mm, dmax_agregado_mm, n_barras_feixe,
                               phi_luva_mm, FATOR_DMAX_AV)


# ---------------------------------------------------------------------------
# 18.2.2 — Diâmetro de curvatura de barra longitudinal dobrada (PDF p. 166)
# ---------------------------------------------------------------------------
TABELA_18_2_2_D_CURVATURA = {"CA-25": 10.0, "CA-50": 15.0, "CA-60": 18.0}  # D/φ


def diametro_curvatura_barra_dobrada_mm(
    phi_mm: float,
    aco: str = "CA-50",
    sigma_s_fyd: float = 1.0,
    n_barras_plano: int = 1,
    espacamento_livre_cm: float | None = None,
    espacamento_min_cm: float | None = None,
) -> float:
    """Diâmetro interno mínimo de curvatura de barra longitudinal dobrada, para força cortante ou nó de pórtico (18.2.2, PDF p. 166).

    D >= 10φ (CA-25), 15φ (CA-50), 18φ (CA-60).

    - Tensão na armadura de tração, com a solicitação de cálculo, abaixo de
      fyd: D pode ser reduzido proporcionalmente, D·(σs/fyd), nunca abaixo
      do exigido para os ganchos (Tabela 9.1, ``ancoragem_nbr6118.
      diametro_pino_gancho``). ``sigma_s_fyd`` = σs/fyd, em [0; 1].
    - Barras de tração curvadas no mesmo plano com espaçamento entre elas
      inferior ao dobro do mínimo de 18.3.2.2: o valor mínimo desta seção é
      multiplicado pelo número dessas barras (``n_barras_plano``). A
      multiplicação é aplicada ao mínimo já reduzido, que é "o valor mínimo
      estabelecido nesta seção". Se ``espacamento_livre_cm`` e
      ``espacamento_min_cm`` (ah ou av de 18.3.2.2) forem dados e o
      espaçamento for >= 2× o mínimo, não se multiplica; sem eles, a
      multiplicação é aplicada (a favor da segurança).

    Devolve D em mm. CA-60 com φ >= 20 mm e redução pedida levanta erro,
    porque a Tabela 9.1 não define o gancho nesse caso.
    """
    aco_n = _aco_padrao(aco)
    if phi_mm <= 0.0:
        raise FaixaNormativaError("φ deve ser positivo (18.2.2).")
    r = float(sigma_s_fyd)
    if not 0.0 <= r <= 1.0:
        raise FaixaNormativaError(
            f"σs/fyd = {r:g} fora de [0; 1]: a redução de 18.2.2 vale só para "
            "σs < fyd."
        )
    n = int(n_barras_plano)
    if n < 1:
        raise FaixaNormativaError("n_barras_plano deve ser >= 1 (18.2.2).")
    if espacamento_livre_cm is not None and espacamento_livre_cm < 0.0:
        raise FaixaNormativaError(
            "O espaçamento livre entre as barras não pode ser negativo (18.2.2)."
        )
    if espacamento_min_cm is not None and espacamento_min_cm <= 0.0:
        raise FaixaNormativaError(
            "O espaçamento mínimo de 18.3.2.2 deve ser positivo (18.2.2)."
        )
    D = TABELA_18_2_2_D_CURVATURA[aco_n] * phi_mm
    if r < 1.0:
        D_gancho = anc.diametro_pino_gancho(phi_mm, aco_n) * phi_mm
        D = max(D * r, D_gancho)
    if n >= 2:
        multiplica = True
        if espacamento_livre_cm is not None and espacamento_min_cm is not None:
            multiplica = espacamento_livre_cm < 2.0 * espacamento_min_cm
        if multiplica:
            D *= n
    return D


# ---------------------------------------------------------------------------
# 18.3.2.3.2 — Barras alojadas nas mesas (PDF p. 169)
# ---------------------------------------------------------------------------
def comprimento_adicional_mesa_cm(distancia_face_alma_cm: float) -> float:
    """Comprimento adicional para barras alojadas nas mesas ou lajes que fazem parte da armadura da viga (18.3.2.3.2, PDF p. 169).

    Δℓ = distância da barra à face mais próxima da alma (cm), somada ao ponto
    de interrupção obtido pelo processo de 18.3.2.3.1. Barra dentro da alma:
    0. Distância negativa levanta erro.
    """
    if distancia_face_alma_cm < 0.0:
        raise FaixaNormativaError(
            "Distância da barra à face da alma não pode ser negativa (18.3.2.3.2)."
        )
    return float(distancia_face_alma_cm)


# ---------------------------------------------------------------------------
# 18.3.2.4 b) — Força de tração no apoio extremo (PDF p. 169)
# ---------------------------------------------------------------------------
def FSd_apoio_extremo_kn(VSd_kn: float, a_l_cm: float, d_cm: float,
                         MSd_kncm: float = 0.0, z_cm: float | None = None,
                         NSd_kn: float = 0.0) -> float:
    """Força de tração a ancorar no apoio extremo (diagonal de compressão), 18.3.2.4 b), PDF p. 169.

    FSd = MSd/z + (aℓ/d)·VSd + NSd >= (aℓ/d)·VSd + NSd

    MSd, VSd e NSd na extremidade do vão efetivo e na mesma combinação. MSd
    em kN·cm, positivo quando traciona a armadura que se ancora (momento
    negativo no apoio só entra pelo piso); VSd em kN (usa-se |VSd|); aℓ, d e
    z em cm (aℓ de 17.4.2); NSd em kN, força de tração eventual (>= 0 —
    compressão não entra na expressão da norma). ``z_cm`` só é exigido
    quando MSd ≠ 0. Devolve kN. É a mesma força do caso do ponto A na face
    do apoio (18.3.2.3.1, PDF p. 169).
    """
    if d_cm <= 0.0 or a_l_cm < 0.0:
        raise FaixaNormativaError("d > 0 e aℓ >= 0 (18.3.2.4 b).")
    if NSd_kn < 0.0:
        raise FaixaNormativaError(
            "NSd é a força de tração eventualmente existente (>= 0); compressão "
            "não reduz FSd (18.3.2.4 b)."
        )
    piso = a_l_cm / d_cm * abs(VSd_kn) + NSd_kn
    if MSd_kncm == 0.0:
        return piso
    if z_cm is None or z_cm <= 0.0:
        raise FaixaNormativaError("Com MSd ≠ 0, informe z > 0 (18.3.2.4 b).")
    return max(MSd_kncm / z_cm + piso, piso)


# ---------------------------------------------------------------------------
# 18.6.1.1 — Força de tração em apoio intermediário (PDF p. 175)
# ---------------------------------------------------------------------------
FATOR_FSD_MIN_APOIO_INTERMEDIARIO = 0.2   # FSd,mín = 0,2·Vd


def FSd_apoio_intermediario_kn(delta_Vd_kn: float, Vd_kn: float, a_l_cm: float,
                               d_cm: float, Nd_kn: float = 0.0) -> float:
    """Força de tração da armadura (prolongamento dos vãos adjacentes) em apoio intermediário, por lado do apoio (18.6.1.1, PDF p. 175).

    FSd = (aℓ/d)·ΔVd + Nd >= FSd,mín = 0,2·Vd

    ΔVd: máxima diferença de força cortante de um lado para o outro do apoio
    (kN, em módulo); Vd: força cortante do lado considerado (kN, em módulo);
    aℓ e d do lado considerado (cm); Nd: força de tração eventual (kN, >= 0).
    O item está em 18.6 (cabos de protensão). A armadura a dispor é a do
    maior FSd entre os lados: ver ``FSd_apoio_intermediario_max_kn``.
    Devolve kN.
    """
    if d_cm <= 0.0 or a_l_cm < 0.0:
        raise FaixaNormativaError("d > 0 e aℓ >= 0 (18.6.1.1).")
    if Nd_kn < 0.0:
        raise FaixaNormativaError(
            "Nd é a força de tração eventualmente existente (>= 0) (18.6.1.1)."
        )
    fsd = a_l_cm / d_cm * abs(delta_Vd_kn) + Nd_kn
    return max(fsd, FATOR_FSD_MIN_APOIO_INTERMEDIARIO * abs(Vd_kn))


def FSd_apoio_intermediario_max_kn(delta_Vd_kn: float,
                                   lados: Sequence[tuple[float, float, float]],
                                   Nd_kn: float = 0.0) -> float:
    """Maior FSd entre os lados de um apoio intermediário (18.6.1.1, PDF p. 175).

    ``lados``: sequência de (Vd_kn, aℓ_cm, d_cm), um por lado do apoio. A
    armadura a dispor é a obtida para o maior dos FSd. Devolve kN.
    """
    if not lados:
        raise FaixaNormativaError("Informe ao menos um lado do apoio (18.6.1.1).")
    return max(FSd_apoio_intermediario_kn(delta_Vd_kn, Vd, al, d, Nd_kn)
               for Vd, al, d in lados)


# ---------------------------------------------------------------------------
# 18.3.2.4 c) — Fração da armadura do vão levada ao apoio (PDF p. 170)
# ---------------------------------------------------------------------------
FRACAO_AS_VAO_MOMENTO_PEQUENO = 1.0 / 3.0   # |Mapoio| <= 0,5·Mvão
FRACAO_AS_VAO_MOMENTO_GRANDE = 1.0 / 4.0    # |Mapoio| >  0,5·Mvão
LIMITE_RELACAO_MAPOIO_MVAO = 0.5


def fracao_As_vao_no_apoio(M_apoio_kncm: float, M_vao_kncm: float) -> float:
    """Fração mínima da armadura de tração do vão prolongada até o apoio (18.3.2.4 c), PDF p. 170).

    As,apoio >= 1/3·As,vão, se Mapoio for nulo ou negativo com |Mapoio| <= 0,5·Mvão;
    As,apoio >= 1/4·As,vão, se Mapoio for negativo com |Mapoio| > 0,5·Mvão.

    Mvão: máximo momento positivo do tramo (> 0). Sinal de Mapoio: negativo
    traciona a face superior. No limite exato |Mapoio| = 0,5·Mvão vale 1/3
    (o degrau é da norma). Mapoio positivo não é coberto por c): vale a)
    (armadura do dimensionamento da seção), e a função levanta erro.
    """
    if M_vao_kncm <= 0.0:
        raise FaixaNormativaError(
            "Mvão é o máximo momento positivo do tramo e deve ser > 0 (18.3.2.4 c)."
        )
    if M_apoio_kncm > 0.0:
        raise FaixaNormativaError(
            "Momento positivo no apoio: 18.3.2.4 c) não define a fração; use a "
            "armadura do dimensionamento da seção (18.3.2.4 a)."
        )
    if abs(M_apoio_kncm) <= LIMITE_RELACAO_MAPOIO_MVAO * M_vao_kncm:
        return FRACAO_AS_VAO_MOMENTO_PEQUENO
    return FRACAO_AS_VAO_MOMENTO_GRANDE


@dataclass(frozen=True)
class ResultadoArmaduraApoio:
    As_vao_cm2: float
    fracao: float
    As_min_fracao_cm2: float
    FSd_kn: float | None
    fyd_mpa: float
    As_min_forca_cm2: float | None
    As_necessaria_cm2: float
    As_apoio_cm2: float | None
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def armadura_tracao_apoio(As_vao_cm2: float, M_apoio_kncm: float,
                          M_vao_kncm: float, *, FSd_kn: float | None = None,
                          fyk_mpa: float = 500.0,
                          gama_s: float | None = None,
                          As_apoio_cm2: float | None = None) -> ResultadoArmaduraApoio:
    """Armadura de tração no apoio: a mais severa entre b) e c) de 18.3.2.4 (PDF p. 169-170).

    As,apoio >= máx(fração·As,vão (c); FSd/fyd (b), quando ``FSd_kn`` é dado)

    ``FSd_kn``: força de ``FSd_apoio_extremo_kn`` (apoio extremo) ou de
    ``FSd_apoio_intermediario_max_kn``. fyd = fyk/γs pelo núcleo (γs do
    núcleo se omitido). Com ``As_apoio_cm2`` (armadura levada ao apoio),
    confronta e devolve ``ok``; sem ela, ``ok`` é True e só o mínimo é
    devolvido. Área em cm²; FSd em kN; fyd em MPa (FSd/fyd convertido com
    fyd/10 em kN/cm²).
    """
    if As_vao_cm2 < 0.0:
        raise FaixaNormativaError("As,vão não pode ser negativa (18.3.2.4 c).")
    gs = nbr.GAMA_S if gama_s is None else gama_s
    fyd = nbr.fyd(fyk_mpa, gs)
    fr = fracao_As_vao_no_apoio(M_apoio_kncm, M_vao_kncm)
    As_c = fr * As_vao_cm2
    memoria = [
        f"18.3.2.4 c): |Mapoio| = {_fmt(abs(M_apoio_kncm))} kN·cm, Mvão = "
        f"{_fmt(M_vao_kncm)} kN·cm -> fração {'1/3' if fr > 0.3 else '1/4'}; "
        f"As,apoio >= {_fmt(fr)}·{_fmt(As_vao_cm2)} = {_fmt(As_c)} cm².",
    ]
    As_b = None
    governante = "18.3.2.4 c) fração de As,vão"
    As_nec = As_c
    if FSd_kn is not None:
        if FSd_kn < 0.0:
            raise FaixaNormativaError("FSd não pode ser negativa (18.3.2.4 b).")
        As_b = FSd_kn / (fyd / 10.0)
        memoria.append(
            f"18.3.2.4 b): As >= FSd/fyd = {_fmt(FSd_kn)} kN / "
            f"{_fmt(fyd / 10.0)} kN/cm² = {_fmt(As_b)} cm² (γs = {_fmt(gs)})."
        )
        if As_b > As_nec:
            As_nec = As_b
            governante = "18.3.2.4 b) FSd/fyd"
    ok = True
    if As_apoio_cm2 is not None:
        ok = As_apoio_cm2 >= As_nec * (1.0 - 1e-9)
        memoria.append(
            f"As,apoio = {_fmt(As_apoio_cm2)} cm² {'>=' if ok else '<'} "
            f"{_fmt(As_nec)} cm² -> {'ok' if ok else 'não atende'}."
        )
    return ResultadoArmaduraApoio(
        As_vao_cm2=As_vao_cm2, fracao=fr, As_min_fracao_cm2=As_c, FSd_kn=FSd_kn,
        fyd_mpa=fyd, As_min_forca_cm2=As_b, As_necessaria_cm2=As_nec,
        As_apoio_cm2=As_apoio_cm2, ok=ok, governante=governante,
        memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 18.3.2.4.1 — Ancoragem da armadura de tração no apoio (PDF p. 170)
# ---------------------------------------------------------------------------
ANCORAGEM_APOIO_MIN_MM = 60.0
FATOR_PHI_GANCHO_APOIO = 5.5           # r + 5,5φ
COBRIMENTO_GANCHO_DISPENSA_MM = 70.0   # dispensa do ℓb,nec
FATOR_PHI_APOIO_INTERMEDIARIO_C = 10.0  # 10φ, caso c) em apoio intermediário


@dataclass(frozen=True)
class ResultadoAncoragemApoio:
    phi_mm: float
    aco: str
    lb_nec_cm: float
    r_mm: float
    r_mais_5_5phi_cm: float
    minimo_60mm_cm: float
    lb_nec_dispensado: bool
    caso_intermediario_c: bool
    comprimento_cm: float
    comprimento_disponivel_cm: float | None
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def ancoragem_no_apoio_cm(
    phi_mm: float,
    lb_nec_cm: float,
    aco: str = "CA-50",
    *,
    cobrimento_gancho_mm: float | None = None,
    acoes_variaveis_frequentes: bool = True,
    intermediario_caso_c: bool = False,
    risco_momento_positivo: bool = True,
    comprimento_disponivel_cm: float | None = None,
) -> ResultadoAncoragemApoio:
    """Comprimento de ancoragem da armadura de tração a partir da face do apoio (18.3.2.4.1, PDF p. 170).

    ℓ >= máx(ℓb,nec (9.4.2.5); r + 5,5φ; 60 mm), com r = D/2 o raio de
    curvatura dos ganchos da Tabela 9.1 (``ancoragem_nbr6118.
    diametro_pino_gancho``).

    Vale para 18.3.2.4 a) em apoio intermediário e para b), c) e d) em apoio
    extremo. Dispensas:

    - cobrimento da barra no trecho do gancho, medido normalmente ao plano do
      gancho, >= 70 mm (``cobrimento_gancho_mm``) e ações variáveis de
      utilização sem grande frequência com seu valor máximo
      (``acoes_variaveis_frequentes=False``): despreza-se ℓb,nec e vale
      máx(r + 5,5φ; 60 mm);
    - caso c) em apoio intermediário (``intermediario_caso_c=True``): ℓ = 10φ,
      desde que não haja possibilidade de momento positivo no apoio
      (``risco_momento_positivo=False``). Havendo a possibilidade, a norma
      exige barras contínuas ou emendadas sobre o apoio, e a função levanta
      ``FaixaNormativaError`` com essa orientação.

    ``lb_nec_cm``: de ``ancoragem_nbr6118.comprimento_ancoragem`` (cm).
    ``comprimento_disponivel_cm``: da face do apoio até a ponta da barra,
    quando se quer a verificação. Devolve dataclass com o comprimento em cm.
    """
    aco_n = _aco_padrao(aco)
    if phi_mm <= 0.0 or lb_nec_cm < 0.0:
        raise FaixaNormativaError("φ > 0 e ℓb,nec >= 0 (18.3.2.4.1).")
    memoria: list[str] = []
    if intermediario_caso_c:
        if risco_momento_positivo:
            raise FaixaNormativaError(
                "Apoio intermediário com possibilidade de momento positivo "
                "(vento, recalques, situações imprevistas): as barras devem ser "
                "contínuas ou emendadas sobre o apoio (18.3.2.4.1)."
            )
        comp = FATOR_PHI_APOIO_INTERMEDIARIO_C * phi_mm / 10.0
        memoria.append(
            f"18.3.2.4.1: caso c) em apoio intermediário, sem possibilidade de "
            f"momento positivo -> ℓ = 10φ = 10·{_fmt(phi_mm)} mm = {_fmt(comp)} cm."
        )
        governante = "10φ (caso c) em apoio intermediário)"
        r_mm = float("nan")
        r55 = float("nan")
        minimo = ANCORAGEM_APOIO_MIN_MM / 10.0
        dispensado = False
    else:
        D_phi = anc.diametro_pino_gancho(phi_mm, aco_n)
        r_mm = D_phi * phi_mm / 2.0
        r55 = (r_mm + FATOR_PHI_GANCHO_APOIO * phi_mm) / 10.0
        minimo = ANCORAGEM_APOIO_MIN_MM / 10.0
        dispensado = (cobrimento_gancho_mm is not None
                      and cobrimento_gancho_mm >= COBRIMENTO_GANCHO_DISPENSA_MM
                      and not acoes_variaveis_frequentes)
        candidatos = [("r + 5,5φ", r55), ("60 mm", minimo)]
        if not dispensado:
            candidatos.insert(0, ("ℓb,nec (9.4.2.5)", float(lb_nec_cm)))
        governante, comp = max(candidatos, key=lambda c: c[1])
        memoria.append(
            f"18.3.2.4.1: r = D/2 = {_fmt(D_phi)}φ/2 = {_fmt(r_mm)} mm (Tabela 9.1); "
            f"r + 5,5φ = {_fmt(r55)} cm; 60 mm = {_fmt(minimo)} cm; ℓb,nec = "
            f"{_fmt(lb_nec_cm)} cm"
            + (" (desconsiderado: cobrimento do gancho >= 70 mm e ações variáveis "
               "sem grande frequência no valor máximo)" if dispensado else "")
            + f" -> ℓ >= {_fmt(comp)} cm ({governante})."
        )
    ok = True
    if comprimento_disponivel_cm is not None:
        ok = comprimento_disponivel_cm >= comp * (1.0 - 1e-9)
        memoria.append(
            f"Disponível a partir da face: {_fmt(comprimento_disponivel_cm)} cm "
            f"{'>=' if ok else '<'} {_fmt(comp)} cm -> {'ok' if ok else 'não atende'}."
        )
    return ResultadoAncoragemApoio(
        phi_mm=phi_mm, aco=aco_n, lb_nec_cm=float(lb_nec_cm), r_mm=r_mm,
        r_mais_5_5phi_cm=r55, minimo_60mm_cm=minimo, lb_nec_dispensado=dispensado,
        caso_intermediario_c=intermediario_caso_c, comprimento_cm=comp,
        comprimento_disponivel_cm=comprimento_disponivel_cm, ok=ok,
        governante=governante, memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 18.3.2.3.1 — Cobertura do diagrama de força de tração (Figura 18.3, PDF p. 168-169)
# ---------------------------------------------------------------------------
FATOR_PHI_ALEM_DE_B = 10.0   # prolongamento mínimo de 10φ além do ponto B


@dataclass(frozen=True)
class BarraCorte:
    """Barra (ou grupo de barras cortadas juntas) para ``cobertura_diagrama``.

    ``Rsd_kn``: força resistente de cálculo da barra (As·fyd, kN).
    ``lb_nec_cm``: comprimento de ancoragem necessário (9.4.2.5).
    ``dobrada``: barra dobrada — o dobramento pode começar em B.
    ``distancia_alma_cm``: barra alojada na mesa (18.3.2.3.2), distância à
    face mais próxima da alma; 0 para barra na alma.
    """

    nome: str
    phi_mm: float
    Rsd_kn: float
    lb_nec_cm: float
    dobrada: bool = False
    distancia_alma_cm: float = 0.0


@dataclass(frozen=True)
class CorteBarra:
    """Resultado de uma extremidade de barra em ``cobertura_diagrama``.

    ``lado``: 'esquerdo' ou 'direito' (sentido em que a força decresce).
    ``x_A_cm``/``x_B_cm``: pontos A (início da ancoragem) e B (tensão nula).
    ``x_fim_cm``: ponta da barra (reta) ou início do dobramento (dobrada).
    ``ate_apoio``: a barra precisa chegar à face do apoio (ancoragem no apoio,
    18.3.2.4.1). ``ponto_A_na_face``: A na face do apoio ou além dela — a
    ancoragem é medida a partir dessa face (18.3.2.3.1, remete a 18.3.2.4 b).
    ``Fsd_face_kn``: força decalada na face, quando ``ate_apoio``.
    """

    nome: str
    lado: str
    x_A_cm: float
    x_B_cm: float
    x_fim_cm: float
    governante: str
    dobrada: bool
    ate_apoio: bool
    ponto_A_na_face: bool
    Fsd_face_kn: float | None


@dataclass(frozen=True)
class ResultadoCobertura:
    x_cm: tuple[float, ...]
    Rsd_kn: tuple[float, ...]
    Fsd_cor_kn: tuple[float, ...]
    Fsd_cor_max_kn: float
    R_total_kn: float
    cortes: tuple[CorteBarra, ...]
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def _interp(xs: Sequence[float], ys: Sequence[float], x: float) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    x0, x1 = xs[lo], xs[hi]
    t = (x - x0) / (x1 - x0)
    return ys[lo] + t * (ys[hi] - ys[lo])


def _Fcor(xs, rs, al, x) -> float:
    """máx de Rsd (linear por trechos) na janela [x − aℓ; x + aℓ], truncada ao domínio."""
    a = max(xs[0], x - al)
    b = min(xs[-1], x + al)
    v = max(_interp(xs, rs, a), _interp(xs, rs, b))
    i = bisect.bisect_right(xs, a)
    j = bisect.bisect_left(xs, b)
    if j > i:
        v = max(v, max(rs[i:j]))
    return v


def _cruzamento(f, xa, xb, nivel, it=80) -> float:
    """Bissecção de f(x) = nivel em [xa, xb], com f(xa) e f(xb) em lados opostos."""
    fa = f(xa) - nivel
    for _ in range(it):
        xm = 0.5 * (xa + xb)
        fm = f(xm) - nivel
        if (fm > 0.0) == (fa > 0.0):
            xa, fa = xm, fm
        else:
            xb = xm
    return 0.5 * (xa + xb)


def cobertura_diagrama(
    x_cm: Sequence[float],
    Md_kncm: Sequence[float],
    z_cm: float | Sequence[float],
    a_l_cm: float,
    barras: Sequence[BarraCorte],
    *,
    x_face_esquerda_cm: float | None = None,
    x_face_direita_cm: float | None = None,
    subdivisoes: int = 20,
) -> ResultadoCobertura:
    """Pontos de corte das barras de tração pela cobertura do diagrama decalado (18.3.2.3.1, Figura 18.3, PDF p. 168-169).

    Procedimento (flexão simples, barras ancoradas por aderência):

    1. Rsd(x) = MSd(x)/z, com MSd tomado positivo quando traciona a armadura
       em estudo (para a armadura negativa, passe −M); trechos com MSd < 0
       têm Rsd = 0.
    2. Diagrama decalado de aℓ (17.4.2), equivalente ao Fsd,cor:
       Fsd,cor(x) = máx Rsd(s), |s − x| <= aℓ (translação de aℓ no sentido
       desfavorável, isto é, para os dois lados do trecho tracionado).
    3. As barras são cortadas na ordem da lista (a primeira é a primeira a
       ser interrompida; as últimas vão até o apoio). Para a barra i, com
       R_rest = soma das forças das barras seguintes:
       - ponto A: onde Fsd,cor = R_rest + Rsd,i (início do trecho de
         ancoragem; a tensão na barra começa a diminuir);
       - ponto B: onde Fsd,cor = R_rest (tensão teórica nula);
       - barra reta: ponta a >= ℓb,nec de A e >= 10φ além de B; e, entre A
         e B, o diagrama resistente linearizado (R_rest + Rsd,i·t, com t
         crescendo linearmente de 0 na ponta a 1 a ℓb,nec da ponta) deve
         cobrir Fsd,cor — a ponta é afastada até isso valer;
       - barra dobrada: o dobramento pode começar em B;
       - barra alojada na mesa (18.3.2.3.2): soma-se a distância à face da
         alma.
    4. Se a ponta passar da face do apoio (``x_face_*``, padrão: extremos de
       x), a barra vai até o apoio e se ancora conforme 18.3.2.4.1
       (``ancoragem_no_apoio_cm``) para Fsd,cor na face; se A estiver na
       face ou além dela e Fsd,cor diminuir em direção ao centro do apoio
       (não crescente da face para fora do vão, no trecho de ``x_cm`` além
       da face), a ancoragem é medida a partir da face
       (``ponto_A_na_face``), conforme 18.3.2.4 b). Se o diagrama termina na
       face (padrão), não há trecho a conferir e a condição é tomada como
       satisfeita; para balanços ou momentos que crescem rumo ao centro do
       apoio, estenda ``x_cm`` além da face para que ela seja verificada.

    ``x_cm`` crescente (cm), ``Md_kncm`` (kN·cm) nos mesmos pontos
    (interpolação linear entre eles — use uma malha fina), ``z_cm`` escalar
    ou por ponto, ``a_l_cm`` >= 0. Cada trecho conexo com Fsd,cor > R_rest
    gera um corte à esquerda e um à direita. ``ok`` = soma das Rsd das
    barras >= máx Fsd,cor. Os resultados estão em cm e kN.
    """
    xs = [float(v) for v in x_cm]
    if len(xs) < 2 or len(Md_kncm) != len(xs):
        raise FaixaNormativaError("x e Md devem ter o mesmo tamanho, >= 2 pontos.")
    if any(b <= a for a, b in zip(xs, xs[1:])):
        raise FaixaNormativaError("x deve ser estritamente crescente.")
    if a_l_cm < 0.0:
        raise FaixaNormativaError("aℓ >= 0 (17.4.2).")
    if not barras:
        raise FaixaNormativaError("Informe ao menos uma barra.")
    for b in barras:
        if b.Rsd_kn <= 0.0 or b.phi_mm <= 0.0 or b.lb_nec_cm < 0.0:
            raise FaixaNormativaError(
                f"Barra {b.nome}: Rsd > 0, φ > 0 e ℓb,nec >= 0."
            )
        comprimento_adicional_mesa_cm(b.distancia_alma_cm)
    zs = ([float(z_cm)] * len(xs) if isinstance(z_cm, (int, float))
          else [float(v) for v in z_cm])
    if len(zs) != len(xs) or min(zs) <= 0.0:
        raise FaixaNormativaError("z > 0 em todos os pontos.")
    rs = [max(float(m), 0.0) / z for m, z in zip(Md_kncm, zs)]
    al = float(a_l_cm)
    xf_esq = xs[0] if x_face_esquerda_cm is None else float(x_face_esquerda_cm)
    xf_dir = xs[-1] if x_face_direita_cm is None else float(x_face_direita_cm)

    # malha fina para localizar cruzamentos (refinados por bissecção)
    n_sub = max(1, int(subdivisoes))
    pts = set(xs)
    for a, b in zip(xs, xs[1:]):
        for k in range(1, n_sub):
            pts.add(a + (b - a) * k / n_sub)
    for v in xs:
        for p in (v - al, v + al):
            if xs[0] < p < xs[-1]:
                pts.add(p)
    grade = sorted(pts)
    F = lambda x: _Fcor(xs, rs, al, x)  # noqa: E731
    fg = [F(x) for x in grade]
    fmax = max(fg)
    R_total = sum(b.Rsd_kn for b in barras)
    ok = R_total >= fmax * (1.0 - 1e-9)

    memoria = [
        f"18.3.2.3.1: Rsd = MSd/z decalado de aℓ = {_fmt(al)} cm (17.4.2); "
        f"Fsd,cor,máx = {_fmt(fmax)} kN; Σ Rsd das barras = {_fmt(R_total)} kN -> "
        f"{'cobre' if ok else 'NÃO cobre'} o diagrama.",
    ]

    cortes: list[CorteBarra] = []
    for i, barra in enumerate(barras):
        R_rest = sum(b.Rsd_kn for b in barras[i + 1:])
        R_cheio = R_rest + barra.Rsd_kn
        # trechos conexos da malha com F > R_rest
        trechos: list[tuple[int, int]] = []
        j = 0
        while j < len(grade):
            if fg[j] > R_rest:
                k = j
                while k + 1 < len(grade) and fg[k + 1] > R_rest:
                    k += 1
                trechos.append((j, k))
                j = k + 1
            else:
                j += 1
        for j0, j1 in trechos:
            # ponto de máximo dentro do trecho (A quando a barra não chega a ser plenamente exigida)
            f_pico = max(fg[j0:j1 + 1])
            no_pico = [q for q in range(j0, j1 + 1)
                       if fg[q] >= f_pico * (1.0 - 1e-12)]
            for lado, jm in (("esquerdo", no_pico[0]), ("direito", no_pico[-1])):
                cortes.append(_corte_lado(
                    barra, lado, grade, fg, F, j0, j1, jm, R_rest, R_cheio,
                    xf_esq, xf_dir,
                ))
                c = cortes[-1]
                memoria.append(_linha_memoria(c, barra, R_rest, R_cheio, xs))
    governante = ("cobertura do diagrama decalado" if ok
                  else "Σ Rsd das barras < Fsd,cor,máx")
    return ResultadoCobertura(
        x_cm=tuple(xs), Rsd_kn=tuple(rs), Fsd_cor_kn=tuple(F(x) for x in xs),
        Fsd_cor_max_kn=fmax, R_total_kn=R_total, cortes=tuple(cortes), ok=ok,
        governante=governante, memoria=tuple(memoria),
    )


def _corte_lado(barra, lado, grade, fg, F, j0, j1, jm, R_rest, R_cheio,
                xf_esq, xf_dir) -> CorteBarra:
    esq = lado == "esquerdo"
    # ponto B: saída do trecho F > R_rest nesse lado
    if esq:
        xB = (grade[0] if j0 == 0
              else _cruzamento(F, grade[j0 - 1], grade[j0], R_rest))
    else:
        xB = (grade[-1] if j1 == len(grade) - 1
              else _cruzamento(F, grade[j1], grade[j1 + 1], R_rest))
    # ponto A: primeiro ponto (a partir de B, rumo ao máximo) com F >= R_cheio
    faixa = range(j0, jm + 1) if esq else range(j1, jm - 1, -1)
    xA = None
    if esq:
        anterior = j0 - 1 if j0 > 0 else None
    else:
        anterior = j1 + 1 if j1 + 1 < len(grade) else None
    for q in faixa:
        if fg[q] >= R_cheio:
            if anterior is None:
                xA = grade[q]
            else:
                xA = _cruzamento(F, grade[anterior], grade[q], R_cheio)
            break
        anterior = q
    if xA is None:
        xA = grade[jm]   # barra não chega a ser plenamente exigida
    phi_cm = barra.phi_mm / 10.0
    s = -1.0 if esq else 1.0   # sentido em que a força decresce
    na_face_A = (xA <= xf_esq + 1e-9) if esq else (xA >= xf_dir - 1e-9)
    if na_face_A:
        # 18.3.2.3.1: além de A estar na face (ou além), Fsd deve diminuir em
        # direção ao centro do apoio -- Fsd,cor não crescente da face para
        # fora do vão, no trecho do diagrama que passa da face.
        xf = xf_esq if esq else xf_dir
        fora = [x for x in grade if (x <= xf if esq else x >= xf)] + [xf]
        fora.sort(reverse=esq)   # da face rumo ao centro do apoio
        fv = [F(x) for x in fora]
        tol = 1e-9 * max(1.0, max(fv))
        na_face_A = all(b <= a + tol for a, b in zip(fv, fv[1:]))
    if barra.dobrada:
        x_fim = xB
        governante = "dobramento a partir de B"
    else:
        cand = [(xA + s * barra.lb_nec_cm, "ℓb,nec a partir de A"),
                (xB + s * FATOR_PHI_ALEM_DE_B * phi_cm, "10φ além de B")]
        # cobertura pelo diagrama resistente linearizado entre A e B
        lo, hi = (xB, xA) if esq else (xA, xB)
        pts = [x for x in grade if lo <= x <= hi] + [lo, hi]
        if barra.lb_nec_cm > 0.0:
            for x in pts:
                exc = max(F(x) - R_rest, 0.0)
                cand.append((x + s * barra.lb_nec_cm * exc / barra.Rsd_kn,
                             "diagrama linearizado entre A e B"))
        x_fim, governante = (min(cand, key=lambda c: c[0]) if esq
                             else max(cand, key=lambda c: c[0]))
    x_fim += s * comprimento_adicional_mesa_cm(barra.distancia_alma_cm)
    if barra.distancia_alma_cm > 0.0:
        governante += " + distância à alma (18.3.2.3.2)"
    ate_apoio = (x_fim <= xf_esq + 1e-9) if esq else (x_fim >= xf_dir - 1e-9)
    Fface = F(xf_esq if esq else xf_dir) if ate_apoio else None
    if na_face_A:
        governante = "ponto A na face do apoio: ancoragem a partir da face (18.3.2.4 b)"
    elif ate_apoio:
        governante += "; chega ao apoio: ancorar conforme 18.3.2.4.1"
    return CorteBarra(
        nome=barra.nome, lado=lado, x_A_cm=xA, x_B_cm=xB, x_fim_cm=x_fim,
        governante=governante, dobrada=barra.dobrada, ate_apoio=ate_apoio,
        ponto_A_na_face=na_face_A, Fsd_face_kn=Fface,
    )


def _linha_memoria(c: CorteBarra, barra: BarraCorte, R_rest, R_cheio, xs) -> str:
    if c.x_B_cm <= xs[0] or c.x_B_cm >= xs[-1]:
        txt_B = "extremo do diagrama, Fsd,cor > 0 até o apoio"
    else:
        txt_B = f"Fsd,cor = {_fmt(R_rest)} kN"
    return (
        f"18.3.2.3.1: barra {barra.nome} (φ {_fmt(barra.phi_mm)} mm), lado "
        f"{c.lado}: A em x = {_fmt(c.x_A_cm)} cm (Fsd,cor = {_fmt(R_cheio)} kN), "
        f"B em x = {_fmt(c.x_B_cm)} cm ({txt_B}); "
        f"{'início do dobramento' if c.dobrada else 'ponta'} em x = "
        f"{_fmt(c.x_fim_cm)} cm ({c.governante})."
    )


# === P23: estribos, torção e suspensão (18.2.4, 18.3.3, 18.3.4, 18.3.6 e 18.3.7) ===
import math
from dataclasses import dataclass
from typing import Sequence

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr


_TOL = 1e-9




def _positivo(valor: float, nome: str) -> float:
    v = float(valor)
    if not v > 0.0:
        raise ValueError(f"{nome} deve ser positivo (recebido {valor!r}).")
    return v


# ---------------------------------------------------------------------------
# Tipos de barra do estribo (18.3.3.2)
# ---------------------------------------------------------------------------
TIPOS_ESTRIBO = ("alta_aderencia", "lisa", "tela")

_TIPO_ALIAS = {
    "alta_aderencia": "alta_aderencia", "altaaderencia": "alta_aderencia",
    "nervurada": "alta_aderencia", "ca50": "alta_aderencia", "ca60": "alta_aderencia",
    "lisa": "lisa", "ca25": "lisa",
    "tela": "tela", "tela_soldada": "tela", "telasoldada": "tela",
}


def _tipo_estribo(tipo: str) -> str:
    chave = str(tipo).strip().lower().replace("-", "").replace(" ", "_")
    if chave not in _TIPO_ALIAS:
        chave = chave.replace("_", "")
    if chave not in _TIPO_ALIAS:
        raise ValueError(
            f"tipo de estribo desconhecido: {tipo!r}. Use 'alta_aderencia', "
            "'lisa' ou 'tela'."
        )
    return _TIPO_ALIAS[chave]


# ---------------------------------------------------------------------------
# 18.2.4 — Proteção contra flambagem das barras (PDF p. 167)
# ---------------------------------------------------------------------------
FATOR_TRECHO_PROTEGIDO_PHI_T = 20.0   # 20·φt a partir do canto
N_MAX_BARRAS_TRECHO_PROTEGIDO = 2     # sem contar a barra de canto


def trecho_protegido_flambagem_cm(phi_t_mm: float) -> float:
    """Comprimento do trecho protegido pelo canto do estribo poligonal (18.2.4, p. 167).

    L = 20·φt, com φt o diâmetro do estribo em mm; devolve em cm
    (20·φt/10).
    """
    return FATOR_TRECHO_PROTEGIDO_PHI_T * _positivo(phi_t_mm, "phi_t_mm") / 10.0


@dataclass(frozen=True)
class ResultadoProtecaoFlambagem:
    phi_t_mm: float
    trecho_protegido_cm: float
    distancias_canto_a_cm: tuple[float, ...]
    distancias_canto_b_cm: tuple[float, ...] | None
    n_barras_trecho_a: int
    n_barras_trecho_b: int
    barras_desprotegidas: tuple[int, ...]
    exige_estribo_suplementar: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def protecao_flambagem(posicoes_barras_cm: Sequence[float], phi_t_mm: float,
                       comprimento_face_cm: float | None = None) -> ResultadoProtecaoFlambagem:
    """Verifica se as barras de uma face estão protegidas contra a flambagem
    pelos cantos do estribo poligonal (18.2.4, p. 167, Figura 18.2).

    Regra da norma: o estribo poligonal protege as barras dos cantos e as
    situadas no máximo a 20·φt do canto, **se nesse trecho de 20·φt não
    houver mais de duas barras, não contando a de canto**. Com mais de duas
    barras no trecho, ou com barra fora dele, deve haver estribo
    suplementar (grampo com ganchos, de preferência de 135° a 180°, que
    atravesse a seção e envolva a barra, ou que envolva o estribo principal
    junto a uma barra — Figura 18.2).

    Parâmetros:
        posicoes_barras_cm: posição de cada barra **intermediária** da face
            (as de canto não entram), medida a partir do canto A ao longo da
            face, em cm (na Figura 18.2 a cota ≤ 20·φt parte do canto do
            estribo).
        phi_t_mm: diâmetro do estribo principal, mm.
        comprimento_face_cm: distância entre os cantos A e B da face, em cm.
            Quando informado, cada barra é confrontada com os dois cantos
            (Figura 18.2-b); quando omitido, só com o canto A.

    Critério adotado quando uma barra está a menos de 20·φt dos dois cantos:
    ela está protegida se estiver no trecho de algum canto que tenha até 2
    barras. O caso de estribo curvilíneo (último parágrafo de 18.2.4) não é
    tratado aqui.
    """
    phi_t = _positivo(phi_t_mm, "phi_t_mm")
    L = trecho_protegido_flambagem_cm(phi_t)
    pos = tuple(float(p) for p in posicoes_barras_cm)
    if any(p < 0.0 for p in pos):
        raise ValueError("posicoes_barras_cm devem ser >= 0 (medidas a partir do canto A).")
    dist_b: tuple[float, ...] | None = None
    if comprimento_face_cm is not None:
        face = _positivo(comprimento_face_cm, "comprimento_face_cm")
        if any(p > face + _TOL for p in pos):
            raise ValueError("Há barra além do canto B (posição > comprimento_face_cm).")
        dist_b = tuple(face - p for p in pos)

    no_a = [d <= L + _TOL for d in pos]
    no_b = [d <= L + _TOL for d in dist_b] if dist_b is not None else [False] * len(pos)
    n_a = sum(no_a)
    n_b = sum(no_b)
    canto_a_protege = n_a <= N_MAX_BARRAS_TRECHO_PROTEGIDO
    canto_b_protege = n_b <= N_MAX_BARRAS_TRECHO_PROTEGIDO

    desprotegidas = tuple(
        i for i in range(len(pos))
        if not ((no_a[i] and canto_a_protege) or (no_b[i] and canto_b_protege))
    )
    exige = bool(desprotegidas)

    memoria = [
        f"18.2.4: trecho protegido pelo canto = 20·φt = 20 × {_fmt(phi_t)} mm = {_fmt(L)} cm.",
        f"18.2.4: barras intermediárias a até {_fmt(L)} cm do canto A: {n_a} "
        f"(máximo {N_MAX_BARRAS_TRECHO_PROTEGIDO}, sem contar a de canto).",
    ]
    if dist_b is not None:
        memoria.append(
            f"18.2.4: barras intermediárias a até {_fmt(L)} cm do canto B: {n_b} "
            f"(máximo {N_MAX_BARRAS_TRECHO_PROTEGIDO}, sem contar a de canto)."
        )
    if exige:
        memoria.append(
            "18.2.4: barras sem proteção (índices "
            + ", ".join(str(i) for i in desprotegidas)
            + "): deve haver estribo suplementar (grampo), com ganchos de "
              "preferência de 135° a 180°."
        )
        governante = "18.2.4: barra fora do trecho de 20·φt ou mais de duas barras no trecho"
    else:
        memoria.append("18.2.4: todas as barras protegidas pelos cantos do estribo; "
                       "dispensa estribo suplementar.")
        governante = "18.2.4: barras protegidas pelos cantos do estribo"
    return ResultadoProtecaoFlambagem(
        phi_t_mm=phi_t, trecho_protegido_cm=L,
        distancias_canto_a_cm=pos, distancias_canto_b_cm=dist_b,
        n_barras_trecho_a=n_a, n_barras_trecho_b=n_b,
        barras_desprotegidas=desprotegidas, exige_estribo_suplementar=exige,
        ok=not exige, governante=governante, memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 18.3.3.2 — Diâmetro do estribo (PDF p. 170)
# ---------------------------------------------------------------------------
PHI_ESTRIBO_MIN_MM = 5.0
PHI_ESTRIBO_MIN_TELA_MM = 4.2          # tela soldada, com precaução contra corrosão
PHI_ESTRIBO_MAX_LISA_MM = 12.0
FATOR_PHI_ESTRIBO_MAX_BW = 1.0 / 10.0  # 1/10 da largura da alma


def phi_estribo_limites_mm(bw_cm: float, tipo: str = "alta_aderencia",
                           protecao_corrosao: bool = False) -> tuple[float, float]:
    """Faixa admissível do diâmetro do estribo de viga (18.3.3.2, p. 170).

    5 mm <= φt <= bw/10, com bw a largura da alma em cm (convertida para mm
    dentro da função: φt,máx = bw_cm·10/10). Barra lisa: φt <= 12 mm.
    Estribo de tela soldada: o mínimo pode cair para 4,2 mm **desde que**
    sejam tomadas precauções contra a corrosão (``protecao_corrosao=True``);
    sem isso, vale o mínimo de 5 mm.

    ``tipo``: 'alta_aderencia' (CA-50, CA-60 nervurado), 'lisa' (CA-25) ou
    'tela'. Devolve (φt,mín, φt,máx) em mm.
    """
    bw = _positivo(bw_cm, "bw_cm")
    t = _tipo_estribo(tipo)
    phi_max = bw * 10.0 * FATOR_PHI_ESTRIBO_MAX_BW
    if t == "lisa":
        phi_max = min(phi_max, PHI_ESTRIBO_MAX_LISA_MM)
    phi_min = PHI_ESTRIBO_MIN_TELA_MM if (t == "tela" and protecao_corrosao) else PHI_ESTRIBO_MIN_MM
    if phi_max < phi_min - _TOL:
        raise FaixaNormativaError(
            f"18.3.3.2: com bw = {_fmt(bw)} cm não há diâmetro de estribo admissível "
            f"(φt,máx = bw/10 = {_fmt(phi_max)} mm < φt,mín = {_fmt(phi_min)} mm)."
        )
    return phi_min, phi_max


def phi_min_barra_canto_mm(phi_estribo_mm: float) -> float:
    """Diâmetro mínimo da barra no canto do estribo fechado ou no gancho do
    estribo aberto (18.3.3.2, p. 171).

    Sem barra longitudinal de cálculo no local, colocar barra de amarração
    com φ >= φt; havendo barra longitudinal, ela também deve ter φ >= φt.
    Nos dois casos o mínimo é o próprio φt, em mm.
    """
    return _positivo(phi_estribo_mm, "phi_estribo_mm")


# ---------------------------------------------------------------------------
# 18.3.3.2 — Espaçamentos máximos (PDF p. 171)
# ---------------------------------------------------------------------------
LIMITE_VD_VRD2_LONGITUDINAL = 0.67
S_MAX_BAIXO_FATOR_D = 0.6
S_MAX_BAIXO_CM = 30.0   # 300 mm
S_MAX_ALTO_FATOR_D = 0.3
S_MAX_ALTO_CM = 20.0    # 200 mm

LIMITE_VD_VRD2_TRANSVERSAL = 0.20
ST_MAX_BAIXO_FATOR_D = 1.0
ST_MAX_BAIXO_CM = 80.0  # 800 mm
ST_MAX_ALTO_FATOR_D = 0.6
ST_MAX_ALTO_CM = 35.0   # 350 mm


def _razao_vd_vrd2(Vd_kn: float, VRd2_kn: float) -> float:
    vrd2 = _positivo(VRd2_kn, "VRd2_kn")
    return abs(float(Vd_kn)) / vrd2


def s_max_estribo_cm(Vd_kn: float, VRd2_kn: float, d_cm: float) -> float:
    """Espaçamento longitudinal máximo entre estribos de viga (18.3.3.2, p. 171).

    - Vd <= 0,67·VRd2: smáx = 0,6·d <= 300 mm;
    - Vd >  0,67·VRd2: smáx = 0,3·d <= 200 mm.

    O degrau em 0,67 é da norma (plano, seção 8, risco 5): Vd = 0,67·VRd2
    exato fica no primeiro ramo (tolerância relativa de 1e-9). Vd em kN
    (usa-se |Vd|), VRd2 em kN (de ``cortante_nbr6118``), d em cm; devolve cm.
    """
    d = _positivo(d_cm, "d_cm")
    r = _razao_vd_vrd2(Vd_kn, VRd2_kn)
    if r <= LIMITE_VD_VRD2_LONGITUDINAL * (1.0 + _TOL):
        return min(S_MAX_BAIXO_FATOR_D * d, S_MAX_BAIXO_CM)
    return min(S_MAX_ALTO_FATOR_D * d, S_MAX_ALTO_CM)


def st_max_cm(Vd_kn: float, VRd2_kn: float, d_cm: float) -> float:
    """Espaçamento transversal máximo entre ramos sucessivos de estribo (18.3.3.2, p. 171).

    - Vd <= 0,20·VRd2: st,máx = d <= 800 mm;
    - Vd >  0,20·VRd2: st,máx = 0,6·d <= 350 mm.

    Degrau da norma em 0,20 (Vd = 0,20·VRd2 exato fica no primeiro ramo).
    Vd e VRd2 em kN, d em cm; devolve cm.
    """
    d = _positivo(d_cm, "d_cm")
    r = _razao_vd_vrd2(Vd_kn, VRd2_kn)
    if r <= LIMITE_VD_VRD2_TRANSVERSAL * (1.0 + _TOL):
        return min(ST_MAX_BAIXO_FATOR_D * d, ST_MAX_BAIXO_CM)
    return min(ST_MAX_ALTO_FATOR_D * d, ST_MAX_ALTO_CM)


def emenda_estribo_permitida(tipo: str) -> bool:
    """Emenda por traspasse de estribo é permitida? (18.3.3.2, p. 171).

    Só quando o estribo é de tela soldada ou de barra de alta aderência:
    'tela' e 'alta_aderencia' -> True; 'lisa' -> False.
    """
    return _tipo_estribo(tipo) in ("tela", "alta_aderencia")


# ---------------------------------------------------------------------------
# 18.3.3.3.2 — Espaçamento longitudinal das barras dobradas (PDF p. 171)
# ---------------------------------------------------------------------------
ALFA_MIN_GRAUS = 45.0   # 17.4.1.1.5
ALFA_MAX_GRAUS = 90.0


def s_max_barras_dobradas_cm(d_cm: float, alfa_graus: float) -> float:
    """Espaçamento longitudinal máximo entre barras dobradas (18.3.3.3.2, p. 171).

    smáx = 0,6·d·(1 + cotg α), com α o ângulo de inclinação da barra dobrada
    em relação ao eixo da viga. d em cm; devolve cm. Faixa de α: a de
    17.4.1.1.5 para armadura transversal, 45° <= α <= 90°; fora dela levanta
    ``FaixaNormativaError``.
    """
    d = _positivo(d_cm, "d_cm")
    a = float(alfa_graus)
    if not (ALFA_MIN_GRAUS - 1e-6 <= a <= ALFA_MAX_GRAUS + 1e-6):
        raise FaixaNormativaError(
            f"18.3.3.3.2 / 17.4.1.1.5: α deve estar entre 45° e 90° (recebido {a:g}°)."
        )
    cotg = 0.0 if abs(a - 90.0) <= 1e-6 else 1.0 / math.tan(math.radians(a))
    return 0.6 * d * (1.0 + cotg)


# ---------------------------------------------------------------------------
# 18.3.3.2 — Verificação conjunta dos estribos de força cortante
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoEstribosViga:
    phi_t_mm: float
    phi_t_min_mm: float
    phi_t_max_mm: float
    s_max_cm: float
    s_cm: float | None
    st_max_cm: float
    st_cm: float | None
    razao_vd_vrd2: float
    phi_canto_min_mm: float
    phi_canto_mm: float | None
    emenda_por_traspasse: bool
    emenda_permitida: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_estribos_viga(
    phi_t_mm: float,
    bw_cm: float,
    d_cm: float,
    Vd_kn: float,
    VRd2_kn: float,
    *,
    tipo: str = "alta_aderencia",
    protecao_corrosao: bool = False,
    s_cm: float | None = None,
    st_cm: float | None = None,
    phi_canto_mm: float | None = None,
    emenda_por_traspasse: bool = False,
) -> ResultadoEstribosViga:
    """Reúne as prescrições de 18.3.3.2 (p. 170-171) para os estribos de uma viga.

    Confere o diâmetro (5 mm ou 4,2 mm em tela protegida <= φt <= bw/10; 12 mm
    se lisa), o espaçamento longitudinal ``s_cm`` contra smáx(Vd/VRd2), o
    espaçamento transversal entre ramos ``st_cm`` contra st,máx(Vd/VRd2), o
    diâmetro da barra de canto ``phi_canto_mm`` (>= φt) e a emenda por
    traspasse (só tela ou alta aderência). Os parâmetros opcionais omitidos
    não são confrontados (o limite é devolvido mesmo assim).
    """
    phi_t = _positivo(phi_t_mm, "phi_t_mm")
    phi_min, phi_max = phi_estribo_limites_mm(bw_cm, tipo, protecao_corrosao)
    smax = s_max_estribo_cm(Vd_kn, VRd2_kn, d_cm)
    stmax = st_max_cm(Vd_kn, VRd2_kn, d_cm)
    r = _razao_vd_vrd2(Vd_kn, VRd2_kn)
    phi_canto_min = phi_min_barra_canto_mm(phi_t)
    emenda_ok = emenda_estribo_permitida(tipo)

    checagens: list[tuple[str, bool]] = []
    memoria: list[str] = []

    ok_phi = phi_min - _TOL <= phi_t <= phi_max + _TOL
    checagens.append(("18.3.3.2 diâmetro do estribo", ok_phi))
    memoria.append(
        f"18.3.3.2: {_fmt(phi_min)} mm <= φt = {_fmt(phi_t)} mm <= {_fmt(phi_max)} mm "
        f"(bw/10{' e 12 mm, barra lisa' if _tipo_estribo(tipo) == 'lisa' else ''}) -> "
        f"{'ok' if ok_phi else 'reprovado'}."
    )

    faixa_s = "<=" if r <= LIMITE_VD_VRD2_LONGITUDINAL * (1.0 + _TOL) else ">"
    memoria.append(
        f"18.3.3.2: Vd/VRd2 = {_fmt(r)} {faixa_s} 0,67 -> smáx = {_fmt(smax)} cm."
    )
    if s_cm is not None:
        ok_s = float(s_cm) <= smax + _TOL
        checagens.append(("18.3.3.2 espaçamento longitudinal máximo", ok_s))
        memoria.append(f"18.3.3.2: s = {_fmt(float(s_cm))} cm <= smáx = {_fmt(smax)} cm -> "
                       f"{'ok' if ok_s else 'reprovado'}.")

    faixa_st = "<=" if r <= LIMITE_VD_VRD2_TRANSVERSAL * (1.0 + _TOL) else ">"
    memoria.append(
        f"18.3.3.2: Vd/VRd2 = {_fmt(r)} {faixa_st} 0,20 -> st,máx = {_fmt(stmax)} cm."
    )
    if st_cm is not None:
        ok_st = float(st_cm) <= stmax + _TOL
        checagens.append(("18.3.3.2 espaçamento transversal entre ramos", ok_st))
        memoria.append(f"18.3.3.2: st = {_fmt(float(st_cm))} cm <= st,máx = {_fmt(stmax)} cm -> "
                       f"{'ok' if ok_st else 'reprovado'}.")

    if phi_canto_mm is not None:
        ok_canto = float(phi_canto_mm) + _TOL >= phi_canto_min
        checagens.append(("18.3.3.2 diâmetro da barra de canto", ok_canto))
        memoria.append(f"18.3.3.2: φ da barra de canto = {_fmt(float(phi_canto_mm))} mm >= "
                       f"φt = {_fmt(phi_canto_min)} mm -> {'ok' if ok_canto else 'reprovado'}.")

    if emenda_por_traspasse:
        checagens.append(("18.3.3.2 emenda por traspasse do estribo", emenda_ok))
        memoria.append(
            "18.3.3.2: emenda por traspasse de estribo "
            + ("permitida (tela ou barra de alta aderência)." if emenda_ok
               else "não permitida em barra lisa -> reprovado.")
        )

    ok = all(v for _, v in checagens)
    reprovados = [n for n, v in checagens if not v]
    governante = reprovados[0] if reprovados else "nenhum critério reprovado (18.3.3.2)"
    return ResultadoEstribosViga(
        phi_t_mm=phi_t, phi_t_min_mm=phi_min, phi_t_max_mm=phi_max,
        s_max_cm=smax, s_cm=(float(s_cm) if s_cm is not None else None),
        st_max_cm=stmax, st_cm=(float(st_cm) if st_cm is not None else None),
        razao_vd_vrd2=r, phi_canto_min_mm=phi_canto_min,
        phi_canto_mm=(float(phi_canto_mm) if phi_canto_mm is not None else None),
        emenda_por_traspasse=bool(emenda_por_traspasse), emenda_permitida=emenda_ok,
        ok=ok, governante=governante, memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 18.3.4 — Armadura para torção (PDF p. 171-172)
# ---------------------------------------------------------------------------
ANGULO_GANCHO_TORCAO_GRAUS = 135.0
S_MAX_LONGITUDINAL_TORCAO_CM = 35.0   # 350 mm


@dataclass(frozen=True)
class ResultadoEstriboTorcao:
    fechado: bool
    angulo_gancho_graus: float
    estribos_cortante: ResultadoEstribosViga | None
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_estribo_torcao(
    fechado: bool,
    angulo_gancho_graus: float,
    *,
    phi_t_mm: float | None = None,
    bw_cm: float | None = None,
    d_cm: float | None = None,
    Vd_kn: float | None = None,
    VRd2_kn: float | None = None,
    s_cm: float | None = None,
    tipo: str = "alta_aderencia",
    protecao_corrosao: bool = False,
) -> ResultadoEstriboTorcao:
    """Verifica as regras construtivas do estribo de torção (18.3.4, p. 171).

    - o estribo deve ser fechado em todo o contorno, envolvendo as barras
      longitudinais de tração;
    - as extremidades são ancoradas por ganchos em ângulo de 135°. Aceita-se
      aqui ângulo >= 135° (o gancho semicircular de 180° dá ancoragem não
      menor; decisão declarada: a norma cita só 135°). O comprimento da ponta
      reta do gancho está em ``ancoragem_nbr6118.ponta_reta_estribo_cm`` (P21);
    - valem as prescrições de 18.3.3.2 para o diâmetro e o espaçamento
      longitudinal: com ``phi_t_mm``, ``bw_cm``, ``d_cm``, ``Vd_kn`` e
      ``VRd2_kn`` informados, confere também isso por
      ``verificar_estribos_viga`` (``s_cm`` opcional).
    """
    ang = float(angulo_gancho_graus)
    if not (0.0 < ang <= 180.0 + 1e-6):
        raise ValueError("angulo_gancho_graus deve estar entre 0° e 180°.")
    checagens: list[tuple[str, bool]] = []
    memoria: list[str] = []

    checagens.append(("18.3.4 estribo fechado em todo o contorno", bool(fechado)))
    memoria.append("18.3.4: estribo de torção "
                   + ("fechado em todo o contorno -> ok." if fechado
                      else "aberto -> reprovado (deve ser fechado em todo o contorno)."))
    ok_ang = ang + 1e-6 >= ANGULO_GANCHO_TORCAO_GRAUS
    checagens.append(("18.3.4 gancho a 135°", ok_ang))
    memoria.append(f"18.3.4: gancho a {_fmt(ang)}° (exigido 135°) -> "
                   f"{'ok' if ok_ang else 'reprovado'}.")

    est = None
    dados = (phi_t_mm, bw_cm, d_cm, Vd_kn, VRd2_kn)
    if all(v is not None for v in dados):
        est = verificar_estribos_viga(
            phi_t_mm, bw_cm, d_cm, Vd_kn, VRd2_kn, tipo=tipo,
            protecao_corrosao=protecao_corrosao, s_cm=s_cm,
        )
        checagens.append((f"18.3.4 -> {est.governante}", est.ok))
        memoria.extend(est.memoria)
    elif any(v is not None for v in dados):
        raise ValueError("Para conferir 18.3.3.2 informe phi_t_mm, bw_cm, d_cm, Vd_kn e VRd2_kn juntos.")

    ok = all(v for _, v in checagens)
    reprovados = [n for n, v in checagens if not v]
    governante = reprovados[0] if reprovados else "nenhum critério reprovado (18.3.4)"
    return ResultadoEstriboTorcao(
        fechado=bool(fechado), angulo_gancho_graus=ang, estribos_cortante=est,
        ok=ok, governante=governante, memoria=tuple(memoria),
    )


def n_min_barras_longitudinais_torcao(perimetro_cm: float, n_vertices: int = 4) -> int:
    """Número mínimo de barras longitudinais de torção no perímetro interno
    dos estribos (18.3.4, p. 172).

    Espaçamento máximo de 350 mm ao longo do perímetro interno (contorno
    fechado: n barras dão n intervalos, n >= u/35) e pelo menos uma barra em
    cada vértice: n = máx(⌈u/35⌉; n_vértices). u em cm.
    """
    u = _positivo(perimetro_cm, "perimetro_cm")
    nv = int(n_vertices)
    if nv < 0:
        raise ValueError("n_vertices deve ser >= 0.")
    return max(math.ceil(u / S_MAX_LONGITUDINAL_TORCAO_CM - _TOL), nv)


@dataclass(frozen=True)
class ResultadoBarrasTorcao:
    espacamentos_cm: tuple[float, ...]
    s_max_cm: float
    espacamento_maior_cm: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_espacamento_barras_torcao(espacamentos_cm: Sequence[float]) -> ResultadoBarrasTorcao:
    """Espaçamento das barras longitudinais de torção ao longo do perímetro
    interno dos estribos: no máximo 350 mm (18.3.4, p. 172).

    ``espacamentos_cm``: distância entre barras consecutivas ao longo do
    perímetro, em cm (arranjo distribuído ou concentrado).
    """
    esp = tuple(float(s) for s in espacamentos_cm)
    if not esp:
        raise ValueError("Informe ao menos um espaçamento.")
    if any(s <= 0.0 for s in esp):
        raise ValueError("Os espaçamentos devem ser positivos.")
    maior = max(esp)
    ok = maior <= S_MAX_LONGITUDINAL_TORCAO_CM + _TOL
    memoria = (
        f"18.3.4: maior espaçamento entre barras longitudinais de torção = {_fmt(maior)} cm "
        f"<= 35 cm -> {'ok' if ok else 'reprovado'}.",
    )
    governante = ("18.3.4 espaçamento das barras longitudinais <= 350 mm" if ok
                  else "18.3.4 espaçamento das barras longitudinais > 350 mm")
    return ResultadoBarrasTorcao(esp, S_MAX_LONGITUDINAL_TORCAO_CM, maior, ok, governante, memoria)


@dataclass(frozen=True)
class ResultadoBarraPorVertice:
    barras_por_vertice: tuple[int, ...]
    vertices_sem_barra: tuple[int, ...]
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_barra_por_vertice(barras_por_vertice: Sequence[int]) -> ResultadoBarraPorVertice:
    """Seção poligonal: pelo menos uma barra em cada vértice dos estribos de
    torção (18.3.4, p. 172).

    ``barras_por_vertice``: número de barras longitudinais em cada vértice do
    estribo (uma entrada por vértice; seção retangular = 4 entradas).
    """
    n = tuple(int(x) for x in barras_por_vertice)
    if len(n) < 3:
        raise ValueError("Seção poligonal tem ao menos 3 vértices.")
    if any(x < 0 for x in n):
        raise ValueError("Número de barras por vértice não pode ser negativo.")
    sem = tuple(i for i, x in enumerate(n) if x < 1)
    ok = not sem
    memoria = (
        f"18.3.4: {len(n)} vértices; vértices sem barra: "
        + (", ".join(str(i) for i in sem) if sem else "nenhum")
        + f" -> {'ok' if ok else 'reprovado'}.",
    )
    governante = ("18.3.4 uma barra em cada vértice" if ok
                  else "18.3.4 vértice sem barra longitudinal")
    return ResultadoBarraPorVertice(n, sem, ok, governante, memoria)


def distribuir_As_long_torcao_cm2(As_long_cm2_por_m: float,
                                  trechos_perimetro_cm: Sequence[float]) -> tuple[float, ...]:
    """Área de armadura longitudinal de torção exigida para cada barra ou
    feixe, pela relação ΔAsl/Δu constante (18.3.4, p. 172).

    ΔAsl,i = (As,long/ue)·Δui, com As,long/ue em cm²/m (de
    ``torcao_nbr6118.As_long_torcao_cm2_por_m``) e Δui em cm, o trecho de
    perímetro da seção efetiva correspondente à barra i (conversão: /100).
    A soma das áreas é (As,long/ue)·Σ Δu.
    """
    taxa = float(As_long_cm2_por_m)
    if taxa < 0.0:
        raise ValueError("As_long_cm2_por_m não pode ser negativo.")
    trechos = tuple(_positivo(t, "trecho de perímetro") for t in trechos_perimetro_cm)
    if not trechos:
        raise ValueError("Informe ao menos um trecho de perímetro.")
    return tuple(taxa * t / 100.0 for t in trechos)


@dataclass(frozen=True)
class ResultadoDeltaAslDeltaU:
    As_long_cm2_por_m: float
    exigidas_cm2: tuple[float, ...]
    adotadas_cm2: tuple[float, ...]
    barras_insuficientes: tuple[int, ...]
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_delta_Asl_delta_u(areas_barras_cm2: Sequence[float],
                                trechos_perimetro_cm: Sequence[float],
                                As_long_cm2_por_m: float) -> ResultadoDeltaAslDeltaU:
    """Confere a relação ΔAsl/Δu exigida pelo dimensionamento em cada barra ou
    feixe (18.3.4, p. 172).

    Para cada barra i: ΔAsl,i/Δui >= As,long/ue, isto é,
    ΔAsl,i >= (As,long/ue)·Δui/100 (As,long/ue em cm²/m; Δu em cm; ΔAsl em
    cm²). ``areas_barras_cm2`` e ``trechos_perimetro_cm`` têm o mesmo
    comprimento (uma entrada por barra ou feixe).
    """
    areas = tuple(float(a) for a in areas_barras_cm2)
    exig = distribuir_As_long_torcao_cm2(As_long_cm2_por_m, trechos_perimetro_cm)
    if len(areas) != len(exig):
        raise ValueError("areas_barras_cm2 e trechos_perimetro_cm devem ter o mesmo comprimento.")
    insuf = tuple(i for i, (a, e) in enumerate(zip(areas, exig)) if a < e * (1.0 - _TOL) - _TOL)
    ok = not insuf
    memoria = [
        f"18.3.4: ΔAsl/Δu exigido = As,long/ue = {_fmt(float(As_long_cm2_por_m))} cm²/m.",
    ]
    for i, (a, e, t) in enumerate(zip(areas, exig, trechos_perimetro_cm)):
        memoria.append(
            f"18.3.4: barra {i}: Δu = {_fmt(float(t))} cm, ΔAsl exigida = {_fmt(e)} cm², "
            f"adotada = {_fmt(a)} cm² -> {'ok' if i not in insuf else 'reprovado'}."
        )
    governante = ("18.3.4 relação ΔAsl/Δu atendida" if ok
                  else f"18.3.4 relação ΔAsl/Δu não atendida na barra {insuf[0]}")
    return ResultadoDeltaAslDeltaU(float(As_long_cm2_por_m), exig, areas, insuf, ok,
                                   governante, tuple(memoria))


# ---------------------------------------------------------------------------
# 18.3.6 — Armadura de suspensão de viga apoiada em viga (PDF p. 172)
# ---------------------------------------------------------------------------
FRACAO_MIN_SUSPENSAO_VIGA_APOIO = 0.75
FRACAO_MAX_SUSPENSAO_VIGA_APOIADA = 0.25


def viga_pendurada(cota_face_inferior_apoiada_cm: float,
                   cota_face_inferior_apoio_cm: float) -> bool:
    """Classifica a viga apoiada como pendurada (18.3.6, p. 172).

    "Define-se uma situação de viga pendurada quando a face inferior da viga
    apoiada está abaixo da face inferior da viga de apoio." Cotas absolutas
    (crescem para cima), em cm. Faces no mesmo nível: não pendurada.
    """
    return float(cota_face_inferior_apoiada_cm) < float(cota_face_inferior_apoio_cm) - _TOL


def fator_reducao_suspensao(h_susp_cm: float, h_viga_apoio_cm: float,
                            faces_superiores_coincidentes: bool = True) -> float:
    """Fator de redução da carga de suspensão (18.3.6, p. 172).

    Vigas **não penduradas** com faces superiores coincidentes: pode-se
    aplicar (1 − h_susp/h_viga apoio), com h_susp a diferença de nível entre
    as faces inferiores das vigas e h_viga apoio a altura da viga de apoio
    (cm). Fora desse caso (``faces_superiores_coincidentes=False``) a norma
    não prevê redução, e o fator é 1.

    Faixa: 0 <= h_susp <= h_viga apoio. h_susp < 0 (viga pendurada) ou maior
    que a altura da viga de apoio levanta ``FaixaNormativaError``.
    """
    h_apoio = _positivo(h_viga_apoio_cm, "h_viga_apoio_cm")
    h_susp = float(h_susp_cm)
    if not faces_superiores_coincidentes:
        return 1.0
    if h_susp < -_TOL or h_susp > h_apoio * (1.0 + _TOL):
        raise FaixaNormativaError(
            f"18.3.6: o fator (1 − h_susp/h_viga apoio) vale para 0 <= h_susp <= h_viga apoio "
            f"(recebido h_susp = {_fmt(h_susp)} cm, h_viga apoio = {_fmt(h_apoio)} cm); "
            "h_susp < 0 é viga pendurada, sem redução."
        )
    return 1.0 - max(h_susp, 0.0) / h_apoio


@dataclass(frozen=True)
class ResultadoSuspensaoViga:
    Fd_kn: float
    fator_reducao: float
    fyd_mpa: float
    As_tirante_cm2: float
    pendurada: bool
    As_viga_apoio_min_cm2: float
    extensao_viga_apoio_cm: float
    As_viga_apoiada_max_cm2: float
    extensao_viga_apoiada_cm: float
    taxa_viga_apoio_cm2_por_m: float
    taxa_viga_apoiada_cm2_por_m: float
    Asw_total_viga_apoio_cm2_por_m: float
    Asw_total_viga_apoiada_cm2_por_m: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def As_suspensao_viga(
    Fd_kn: float,
    h_viga_apoio_cm: float,
    h_viga_apoiada_cm: float,
    *,
    fyk_mpa: float = 500.0,
    gama_s: float | None = None,
    pendurada: bool = False,
    fator_reducao: float = 1.0,
    viga_apoio_continua: bool = True,
    viga_apoiada_continua: bool = True,
    fracao_viga_apoio: float = FRACAO_MIN_SUSPENSAO_VIGA_APOIO,
    Asw_cisalhamento_viga_apoio_cm2_por_m: float = 0.0,
    Asw_cisalhamento_viga_apoiada_cm2_por_m: float = 0.0,
) -> ResultadoSuspensaoViga:
    """Armadura de suspensão de viga apoiada em viga e sua distribuição (18.3.6, p. 172).

    Tirante: As,susp = fator·Fd/fyd (Fd em kN, fyd = fyk/γs do núcleo, em
    kN/cm² = MPa/10; As em cm²). ``fator_reducao`` é o de
    ``fator_reducao_suspensao`` (só para viga não pendurada com faces
    superiores coincidentes).

    Viga **não pendurada** (Figura 18.4):
    - na viga de apoio, no mínimo 75 % de As,susp, numa extensão máxima
      h_viga apoio (metade para cada lado do cruzamento);
    - na viga apoiada, no máximo 25 % de As,susp, numa extensão máxima
      h_viga apoiada (metade para cada lado);
    - se a viga não se estende além do cruzamento (``*_continua=False``),
      toda a armadura dela vai na extensão h_viga/2.
    ``fracao_viga_apoio`` (padrão 0,75, entre 0,75 e 1,0) é a parcela posta
    na viga de apoio; o resto vai para a viga apoiada.

    Viga **pendurada**: a norma não dá repartição. Adota-se (decisão
    declarada, a favor da segurança) 100 % na viga de apoio, na mesma
    extensão h_viga apoio; o fator de redução não se aplica (levanta
    ``FaixaNormativaError`` se diferente de 1).

    A armadura de suspensão soma-se à de cisalhamento (força cortante e/ou
    torção) já existente no trecho: informe-a em
    ``Asw_cisalhamento_*_cm2_por_m`` para obter a taxa total. As taxas são
    As/extensão, em cm²/m.
    """
    Fd = abs(float(Fd_kn))
    h_ap = _positivo(h_viga_apoio_cm, "h_viga_apoio_cm")
    h_ad = _positivo(h_viga_apoiada_cm, "h_viga_apoiada_cm")
    fator = float(fator_reducao)
    if not (0.0 - _TOL <= fator <= 1.0 + _TOL):
        raise FaixaNormativaError("18.3.6: o fator de redução deve estar entre 0 e 1.")
    if pendurada and abs(fator - 1.0) > _TOL:
        raise FaixaNormativaError(
            "18.3.6: o fator de redução (1 − h_susp/h_viga apoio) só vale para viga não pendurada."
        )
    frac = float(fracao_viga_apoio)
    if not pendurada and not (FRACAO_MIN_SUSPENSAO_VIGA_APOIO - _TOL <= frac <= 1.0 + _TOL):
        raise FaixaNormativaError(
            "18.3.6: na viga de apoio vai no mínimo 75 % da armadura do tirante "
            f"(fracao_viga_apoio = {frac:g})."
        )
    gs = nbr.GAMA_S if gama_s is None else float(gama_s)
    fyd_mpa = nbr.fyd(fyk_mpa, gs)
    fyd_kncm2 = nbr.mpa_para_kncm2(fyd_mpa)
    As_t = fator * Fd / fyd_kncm2

    if pendurada:
        frac = 1.0
    As_ap = frac * As_t
    As_ad = As_t - As_ap
    ext_ap = h_ap if viga_apoio_continua else h_ap / 2.0
    ext_ad = h_ad if viga_apoiada_continua else h_ad / 2.0
    taxa_ap = As_ap / (ext_ap / 100.0)
    taxa_ad = As_ad / (ext_ad / 100.0) if As_ad > 0.0 else 0.0
    tot_ap = taxa_ap + float(Asw_cisalhamento_viga_apoio_cm2_por_m)
    tot_ad = taxa_ad + float(Asw_cisalhamento_viga_apoiada_cm2_por_m)

    memoria = [
        f"18.3.6: As,susp = fator·Fd/fyd = {_fmt(fator)} × {_fmt(Fd)} kN / "
        f"{_fmt(fyd_kncm2)} kN/cm² = {_fmt(As_t)} cm² (fyd = {_fmt(fyk_mpa)}/{_fmt(gs)} MPa).",
    ]
    if pendurada:
        memoria.append(
            "18.3.6: viga pendurada; a norma não reparte o tirante, adota-se 100 % na viga de apoio."
        )
    else:
        memoria.append(
            f"18.3.6: viga não pendurada; viga de apoio >= 75 %: {_fmt(As_ap)} cm² "
            f"({_fmt(100 * frac)} %); viga apoiada <= 25 %: {_fmt(As_ad)} cm²."
        )
    memoria.append(
        f"18.3.6: extensão na viga de apoio = {_fmt(ext_ap)} cm "
        + ("(h/2 para cada lado do cruzamento)" if viga_apoio_continua
           else "(h/2, a viga não passa do cruzamento)")
        + f" -> {_fmt(taxa_ap)} cm²/m; somada à de cisalhamento: {_fmt(tot_ap)} cm²/m."
    )
    if As_ad > 0.0:
        memoria.append(
            f"18.3.6: extensão na viga apoiada = {_fmt(ext_ad)} cm "
            + ("(h/2 para cada lado do cruzamento)" if viga_apoiada_continua
               else "(h/2, a viga não passa do cruzamento)")
            + f" -> {_fmt(taxa_ad)} cm²/m; somada à de cisalhamento: {_fmt(tot_ad)} cm²/m."
        )
    return ResultadoSuspensaoViga(
        Fd_kn=Fd, fator_reducao=fator, fyd_mpa=fyd_mpa, As_tirante_cm2=As_t,
        pendurada=bool(pendurada),
        As_viga_apoio_min_cm2=As_ap, extensao_viga_apoio_cm=ext_ap,
        As_viga_apoiada_max_cm2=As_ad, extensao_viga_apoiada_cm=ext_ad,
        taxa_viga_apoio_cm2_por_m=taxa_ap, taxa_viga_apoiada_cm2_por_m=taxa_ad,
        Asw_total_viga_apoio_cm2_por_m=tot_ap, Asw_total_viga_apoiada_cm2_por_m=tot_ad,
        ok=True, governante="18.3.6 armadura de suspensão (dimensionamento)",
        memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 18.3.7 — Armadura de ligação mesa-alma ou talão-alma (PDF p. 173)
# ---------------------------------------------------------------------------
AS_LIGACAO_MESA_ALMA_MIN_CM2_POR_M = 1.5


def As_ligacao_mesa_alma_min_cm2_por_m() -> float:
    """Seção mínima da armadura de ligação mesa-alma ou talão-alma (18.3.7, p. 173).

    1,5 cm² por metro de viga, estendendo-se por toda a largura útil e
    adequadamente ancorada.
    """
    return AS_LIGACAO_MESA_ALMA_MIN_CM2_POR_M


@dataclass(frozen=True)
class ResultadoLigacaoMesaAlma:
    As_necessaria_cm2_por_m: float
    As_min_cm2_por_m: float
    As_exigida_cm2_por_m: float
    As_laje_cm2_por_m: float
    As_adicional_cm2_por_m: float
    As_adicional_necessaria_cm2_por_m: float
    As_total_cm2_por_m: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_ligacao_mesa_alma(
    As_necessaria_cm2_por_m: float = 0.0,
    As_flexao_laje_cm2_por_m: float = 0.0,
    As_adicional_cm2_por_m: float = 0.0,
    laje_ancorada: bool = True,
) -> ResultadoLigacaoMesaAlma:
    """Armadura de ligação mesa-alma ou talão-alma (18.3.7, p. 173).

    Exigida: máx(As necessária para as trações do plano de ligação; 1,5 cm²/m).
    A armadura de flexão da laje existente no plano de ligação conta, se
    devidamente ancorada (``laje_ancorada``); a diferença é completada por
    armadura adicional. Todas as taxas em cm²/m.

    A verificação da resistência do concreto aos efeitos tangenciais no plano
    de ligação e o cálculo de ``As_necessaria_cm2_por_m`` não têm fórmula
    neste item e ficam com o usuário.
    """
    nec = float(As_necessaria_cm2_por_m)
    laje = float(As_flexao_laje_cm2_por_m)
    adic = float(As_adicional_cm2_por_m)
    if nec < 0.0 or laje < 0.0 or adic < 0.0:
        raise ValueError("As taxas de armadura não podem ser negativas.")
    amin = As_ligacao_mesa_alma_min_cm2_por_m()
    exig = max(nec, amin)
    laje_conta = laje if laje_ancorada else 0.0
    adic_nec = max(0.0, exig - laje_conta)
    total = laje_conta + adic
    ok = total + _TOL >= exig
    memoria = (
        f"18.3.7: As exigida = máx(As necessária = {_fmt(nec)}; 1,5) = {_fmt(exig)} cm²/m.",
        f"18.3.7: armadura de flexão da laje considerada = {_fmt(laje_conta)} cm²/m"
        + ("" if laje_ancorada else " (não ancorada, não conta)")
        + f"; adicional necessária = {_fmt(adic_nec)} cm²/m.",
        f"18.3.7: As total = {_fmt(total)} cm²/m >= {_fmt(exig)} cm²/m -> "
        f"{'ok' if ok else 'reprovado'}.",
    )
    governante = ("18.3.7 armadura mínima de 1,5 cm²/m" if amin >= nec
                  else "18.3.7 armadura necessária ao plano de ligação")
    return ResultadoLigacaoMesaAlma(
        As_necessaria_cm2_por_m=nec, As_min_cm2_por_m=amin, As_exigida_cm2_por_m=exig,
        As_laje_cm2_por_m=laje_conta, As_adicional_cm2_por_m=adic,
        As_adicional_necessaria_cm2_por_m=adic_nec, As_total_cm2_por_m=total,
        ok=ok, governante=governante, memoria=memoria,
    )
