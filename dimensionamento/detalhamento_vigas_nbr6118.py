"""Detalhamento de vigas: armadura longitudinal — ABNT NBR 6118:2026.

Cobre (P22 do plano de implementação):

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
