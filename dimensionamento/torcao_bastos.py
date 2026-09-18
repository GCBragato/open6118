"""Torcao em Vigas de Concreto Armado (NBR 6118:2026).

Implementa o dimensionamento a torcao seguindo a apostila
"TORCAO EM VIGAS DE CONCRETO ARMADO", Prof. Paulo Sergio Bastos,
UNESP/Bauru, corrigida contra a NBR 6118:2026 (auditoria de 18/09/2026:
CRT-04, CRT-05, CRT-06, CRT-07). Grandezas de material (fct,m, fcd, fywd)
vem de nucleo_nbr6118.

Casos cobertos:
    - Secao vazada equivalente (Eq. 19/20; 17.5.1.4.1).
    - TRd,2 - diagonais comprimidas (Eq. 22).
    - As/s    - armadura transversal de torcao (Eq. 24).
    - As/ue   - armadura longitudinal de torcao (Eq. 27).
    - Armaduras minimas (Eq. 32/33).
    - Combinacao torcao + cortante: VSd/VRd2 + TSd/TRd2 <= 1 (Eq. 35).

Convencoes:
    - fck, fyk em MPa.
    - bw, h, c1 em cm. TSd em kN.cm. As em cm2 ou cm2/m.
    - 30 deg <= theta <= 45 deg (17.5.1.1, mesma faixa do dimensionamento a
      forca cortante Modelo II).
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr


GAMA_C = nbr.GAMA_C
GAMA_S = nbr.GAMA_S

FYWD_MAX_KNCM2 = 43.5

THETA_MIN_DEG = 30.0    # 17.5.1.1 - inclinacao das diagonais de torcao
THETA_MAX_DEG = 45.0

FYWK_TETO_TORCAO_MPA = 500.0   # 17.5.1.2 - teto de fywk nos minimos de torcao


def fcd_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fcd em kN/cm2 (delega ao nucleo, 12.3.3)."""
    return nbr.mpa_para_kncm2(nbr.fcd(fck_mpa, gama_c))


def fctm_mpa(fck_mpa: float) -> float:
    """fct,m, MPa (NBR 6118 8.2.5; delega ao nucleo).

    CRT-04: copia local sem o ramo fck > 50 subestimava fct,m (e portanto
    Asw,min/As,min de torcao) acima de C50; agora delega ao nucleo, que
    cobre os dois ramos (Grupo I e II).
    """
    return nbr.fct_m(fck_mpa)


def fywd_kncm2(fywk_mpa: float = 500.0,
               gama_s: float = GAMA_S) -> float:
    """fywd em kN/cm2, limitado a 435 MPa (17.4.2.2 b; fyd vem do nucleo)."""
    return nbr.mpa_para_kncm2(min(nbr.fyd(fywk_mpa, gama_s), 435.0))


def alfa_v2(fck_mpa: float) -> float:
    """alpha_v2 = 1 - fck/250 (17.5.1.5). Delega ao nucleo normativo."""
    return nbr.alpha_v2(fck_mpa)


def _validar_theta_torcao(theta_deg: float) -> None:
    """17.5.1.1: 30 deg <= theta <= 45 deg (CRT-07; mesma faixa/forma da
    validacao ja existente em cortante_bastos.modelo_calculo_II)."""
    if not (THETA_MIN_DEG - 1e-6 <= theta_deg <= THETA_MAX_DEG + 1e-6):
        raise ValueError(
            f"theta deve estar entre 30 e 45 deg (recebido {theta_deg})."
        )


# ---------------------------------------------------------------------------
# Secao vazada equivalente
# ---------------------------------------------------------------------------
def secao_vazada_retangular(
    bw_cm: float, h_cm: float, c1_cm: float,
    he_adotado_cm: float | None = None,
) -> dict:
    """Define he, Ae e ue para secao retangular cheia (17.5.1.4.1, Eq. 19/20).

    Caso geral (A/u >= 2*c1): he <= A/u (limite superior) e he >= 2*c1
    (limite inferior); adota-se he = A/u. Ae = (bw-he)*(h-he);
    ue = 2*[(bw-he)+(h-he)] (eixos no meio da parede equivalente).

    CRT-06 - caso A/u < 2*c1 (secao "cheia" demais para a parede media
    caber entre a face e o eixo das barras de canto): a norma manda
    adotar he = A/u, limitado a bw - 2*c1, com Ae e ue determinados pelos
    eixos das armaduras de canto (retangulo (bw-2c1) x (h-2c1)), e nao
    mais pela parede de espessura he. Antes desta correcao o codigo
    adotava he = 2*c1 (o limite inferior, nao o previsto pela norma) com a
    formula generica de Ae, o que reduzia Ae/TRd2/Asw sem base normativa.
    """
    A = bw_cm * h_cm
    u = 2.0 * (bw_cm + h_cm)
    he_max = A / u
    he_min = 2.0 * c1_cm
    caso_esbelto = he_max < he_min
    if he_adotado_cm is None:
        he = min(he_max, bw_cm - 2.0 * c1_cm) if caso_esbelto else he_max
    else:
        he = he_adotado_cm
    if caso_esbelto:
        Ae = (bw_cm - 2.0 * c1_cm) * (h_cm - 2.0 * c1_cm)
        ue = 2.0 * ((bw_cm - 2.0 * c1_cm) + (h_cm - 2.0 * c1_cm))
    else:
        Ae = (bw_cm - he) * (h_cm - he)
        ue = 2.0 * ((bw_cm - he) + (h_cm - he))
    return {
        "he_min_cm": he_min,
        "he_max_cm": he_max,
        "he_cm": he,
        "Ae_cm2": Ae,
        "ue_cm": ue,
        "caso_esbelto": caso_esbelto,
    }


# ---------------------------------------------------------------------------
# TRd,2 - diagonais comprimidas (Eq. 22)
# ---------------------------------------------------------------------------
def TRd2_kncm(fck_mpa: float, Ae_cm2: float, he_cm: float,
              theta_deg: float = 45.0,
              gama_c: float = GAMA_C) -> float:
    """TRd,2 = 0.5 * alpha_v2 * fcd * Ae * he * sin(2 theta)  (17.5.1.5, Eq. 22).

    CRT-07 (17.5.1.1): 30 deg <= theta <= 45 deg.
    """
    _validar_theta_torcao(theta_deg)
    fcd = fcd_kncm2(fck_mpa, gama_c)
    return (0.5 * alfa_v2(fck_mpa) * fcd * Ae_cm2 * he_cm
            * math.sin(2.0 * math.radians(theta_deg)))


# ---------------------------------------------------------------------------
# Armaduras
# ---------------------------------------------------------------------------
def Asw_torcao_cm2_por_m(
    TSd_kncm: float, Ae_cm2: float, theta_deg: float = 45.0,
    fywk_mpa: float = 500.0, gama_s: float = GAMA_S,
) -> float:
    """Asw/s para torcao (Eq. 24): por unidade de comprimento (cm2/m).

    Asw/s = (TSd * tan(theta)) / (2 * Ae * fywd) -> cm2/cm.

    CRT-07 (17.5.1.1): 30 deg <= theta <= 45 deg.
    """
    _validar_theta_torcao(theta_deg)
    fywd = fywd_kncm2(fywk_mpa, gama_s)
    asw_s = TSd_kncm * math.tan(math.radians(theta_deg)) / (2.0 * Ae_cm2 * fywd)
    return asw_s * 100.0


def As_long_torcao_cm2_por_m(
    TSd_kncm: float, Ae_cm2: float, theta_deg: float = 45.0,
    fywk_mpa: float = 500.0, gama_s: float = GAMA_S,
) -> float:
    """As,long/ue para torcao (Eq. 27): por unidade de perimetro (cm2/m).

    As/ue = TSd / (2 * Ae * fywd * tan(theta)) -> cm2/cm.

    CRT-07 (17.5.1.1): 30 deg <= theta <= 45 deg.
    """
    _validar_theta_torcao(theta_deg)
    fywd = fywd_kncm2(fywk_mpa, gama_s)
    as_ue = TSd_kncm / (2.0 * Ae_cm2 * fywd
                        * math.tan(math.radians(theta_deg)))
    return as_ue * 100.0


def Asw_min_cm2_por_m(bw_cm: float, fck_mpa: float,
                      fywk_mpa: float = 500.0) -> float:
    """Eq. 33: As,90,min = 20 * fctm * bw / fywk  (cm2/m).

    CRT-05 (17.5.1.2): fywk e limitado a 500 MPa nesta verificacao (o teto
    e especifico dos minimos de torcao; nao existe em 17.4.1.1.1, cortante).
    """
    fctm_kncm2 = fctm_mpa(fck_mpa) * 0.1
    fywk_kncm2 = min(fywk_mpa, FYWK_TETO_TORCAO_MPA) * 0.1
    return 20.0 * fctm_kncm2 * bw_cm / fywk_kncm2


def As_long_min_cm2_por_m(he_cm: float, fck_mpa: float,
                          fywk_mpa: float = 500.0) -> float:
    """Eq. 32: As,min = 20 * fctm * he / fywk  (cm2/m).

    CRT-05 (17.5.1.2): fywk e limitado a 500 MPa nesta verificacao.
    """
    fctm_kncm2 = fctm_mpa(fck_mpa) * 0.1
    fywk_kncm2 = min(fywk_mpa, FYWK_TETO_TORCAO_MPA) * 0.1
    return 20.0 * fctm_kncm2 * he_cm / fywk_kncm2


# ---------------------------------------------------------------------------
# Combinacao torcao + cortante (Eq. 35)
# ---------------------------------------------------------------------------
def verifica_combinacao(VSd_kn: float, VRd2_kn: float,
                        TSd_kncm: float, TRd2_kncm: float) -> dict:
    """Verifica VSd/VRd2 + TSd/TRd2 <= 1.0 (NBR 6118 17.7.2)."""
    razao = VSd_kn / VRd2_kn + TSd_kncm / TRd2_kncm
    return {
        "razao": razao,
        "ok": razao <= 1.0,
    }


# ---------------------------------------------------------------------------
# Resultado consolidado
# ---------------------------------------------------------------------------
@dataclass
class ResultadoTorcao:
    bw: float
    h: float
    fck: float
    fywk: float
    theta_deg: float
    TSd_kncm: float

    he: float
    Ae: float
    ue: float
    TRd2_kncm: float
    Asw_m: float           # cm2/m (transversal de torcao)
    As_long_total_cm2: float  # As longitudinal total (= As/ue * ue)
    Asw_min_m: float
    As_long_min_m: float
    ok_bielas: bool


def dimensionar_torcao(
    TSd_kncm: float, bw_cm: float, h_cm: float, c1_cm: float,
    fck_mpa: float, fywk_mpa: float = 500.0, theta_deg: float = 45.0,
    gama_c: float = GAMA_C, gama_s: float = GAMA_S,
    he_adotado_cm: float | None = None,
) -> ResultadoTorcao:
    """Dimensiona viga retangular cheia a torcao."""
    sec = secao_vazada_retangular(bw_cm, h_cm, c1_cm, he_adotado_cm)
    Ae, he, ue = sec["Ae_cm2"], sec["he_cm"], sec["ue_cm"]
    TRd2 = TRd2_kncm(fck_mpa, Ae, he, theta_deg, gama_c)
    asw_m = Asw_torcao_cm2_por_m(TSd_kncm, Ae, theta_deg, fywk_mpa, gama_s)
    as_ue_m = As_long_torcao_cm2_por_m(TSd_kncm, Ae, theta_deg,
                                        fywk_mpa, gama_s)
    as_long_total = as_ue_m / 100.0 * ue   # cm2 distribuido no perimetro
    asw_min = Asw_min_cm2_por_m(bw_cm, fck_mpa, fywk_mpa)
    as_long_min = As_long_min_cm2_por_m(he, fck_mpa, fywk_mpa)
    return ResultadoTorcao(
        bw=bw_cm, h=h_cm, fck=fck_mpa, fywk=fywk_mpa,
        theta_deg=theta_deg, TSd_kncm=TSd_kncm,
        he=he, Ae=Ae, ue=ue, TRd2_kncm=TRd2,
        Asw_m=asw_m, As_long_total_cm2=as_long_total,
        Asw_min_m=asw_min, As_long_min_m=as_long_min,
        ok_bielas=TSd_kncm <= TRd2,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def test_secao_vazada_apostila() -> None:
    """Apostila ex. 14.3.6: bw=35, h=50, c1=4.125 (phi=12.5, t=10, c=2.5).
    he_max = 1750/170 = 10.3 cm; he_min = 2 * 4.125 = 8.3 cm.
    Adota-se he = 10.0 cm; Ae = 25*40 = 1000; ue = 2*(25+40) = 130."""
    sec = secao_vazada_retangular(35.0, 50.0, 4.125, he_adotado_cm=10.0)
    assert _aprox(sec["he_max_cm"], 10.29, 0.05), f"he_max={sec['he_max_cm']}"
    assert _aprox(sec["he_min_cm"], 8.25, 0.05), f"he_min={sec['he_min_cm']}"
    assert _aprox(sec["Ae_cm2"], 1000.0, 0.5), f"Ae={sec['Ae_cm2']}"
    assert _aprox(sec["ue_cm"], 130.0, 0.5), f"ue={sec['ue_cm']}"
    print(f"  OK  Secao: he={sec['he_cm']:.2f} cm  Ae={sec['Ae_cm2']:.0f} "
          f"ue={sec['ue_cm']:.0f}")


def test_TRd2_apostila() -> None:
    """Apostila: C25, theta=38, Ae=1000, he=10 -> TRd,2 = 7797 kN.cm."""
    TRd = TRd2_kncm(fck_mpa=25.0, Ae_cm2=1000.0, he_cm=10.0, theta_deg=38.0)
    assert _aprox(TRd, 7797.0, 5.0), f"TRd2={TRd:.1f}"
    print(f"  OK  TRd,2 = {TRd:.1f} kN.cm  (apostila: 7797)")


def test_Asw_apostila() -> None:
    """Apostila: TSd=6808, Ae=1000, theta=38 -> Asw = 6.12 cm2/m."""
    asw = Asw_torcao_cm2_por_m(TSd_kncm=6808.0, Ae_cm2=1000.0,
                               theta_deg=38.0)
    assert _aprox(asw, 6.12, 0.05), f"Asw={asw:.3f}"
    print(f"  OK  Asw_torcao = {asw:.2f} cm2/m  (apostila: 6.12)")


def test_As_long_apostila() -> None:
    """Apostila: TSd=6808, Ae=1000, theta=38 -> As/ue = 10.02 cm2/m."""
    as_m = As_long_torcao_cm2_por_m(TSd_kncm=6808.0, Ae_cm2=1000.0,
                                    theta_deg=38.0)
    assert _aprox(as_m, 10.02, 0.05), f"As/ue={as_m:.3f}"
    # Total no perimetro ue=130 cm: 13.03 cm2
    print(f"  OK  As_long/ue = {as_m:.2f} cm2/m  (apostila: 10.02)")


def test_armaduras_minimas_apostila() -> None:
    """Apostila: As,min = 1.03 cm2/m; As,90,min = 3.58 cm2/m
       (C25, he=10, bw=35, fywk=500)."""
    asw_min = Asw_min_cm2_por_m(bw_cm=35.0, fck_mpa=25.0)
    as_long_min = As_long_min_cm2_por_m(he_cm=10.0, fck_mpa=25.0)
    assert _aprox(asw_min, 3.58, 0.05), f"As,90,min={asw_min:.3f}"
    assert _aprox(as_long_min, 1.025, 0.05), f"As,min={as_long_min:.3f}"
    print(f"  OK  As,90,min = {asw_min:.2f} cm2/m  "
          f"As,min(long) = {as_long_min:.2f} cm2/m")


def test_combinacao_apostila() -> None:
    """Apostila: VSd=83.4, VRd2=679.5, TSd=6808, TRd2=7797.
    Razao = 83.4/679.5 + 6808/7797 = 0.123 + 0.873 = 0.996 <= 1 OK."""
    r = verifica_combinacao(VSd_kn=83.4, VRd2_kn=679.5,
                            TSd_kncm=6808.0, TRd2_kncm=7797.0)
    assert _aprox(r["razao"], 0.996, 0.005), f"razao={r['razao']:.4f}"
    assert r["ok"], "deveria atender"
    print(f"  OK  Combinacao V+T: razao = {r['razao']:.3f}  ok={r['ok']}")


def test_dimensionar_completo() -> None:
    """Reproduz o exemplo 14.3.6 da apostila."""
    r = dimensionar_torcao(
        TSd_kncm=6808.0, bw_cm=35.0, h_cm=50.0, c1_cm=4.125,
        fck_mpa=25.0, fywk_mpa=500.0, theta_deg=38.0,
        he_adotado_cm=10.0,
    )
    assert _aprox(r.TRd2_kncm, 7797.0, 5.0)
    assert _aprox(r.Asw_m, 6.12, 0.05)
    assert _aprox(r.As_long_total_cm2, 13.03, 0.10), \
        f"As,long,total={r.As_long_total_cm2}"
    assert r.ok_bielas
    print(f"  OK  Completo: TRd2={r.TRd2_kncm:.0f}, Asw={r.Asw_m:.2f} cm2/m, "
          f"As,long,total={r.As_long_total_cm2:.2f} cm2")


def run_tests() -> int:
    tests = [
        test_secao_vazada_apostila,
        test_TRd2_apostila,
        test_Asw_apostila,
        test_As_long_apostila,
        test_armaduras_minimas_apostila,
        test_combinacao_apostila,
        test_dimensionar_completo,
    ]
    falhas = 0
    for t in tests:
        try:
            print(f"[{t.__name__}]")
            t()
        except AssertionError as e:
            falhas += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception as e:
            falhas += 1
            print(f"  ERRO {t.__name__}: {e}")
    print(f"\n{len(tests) - falhas}/{len(tests)} OK")
    return falhas


def _demo() -> None:
    print("=== Exemplo 14.3.6 - viga 35x50, C25, TSd=6808 kN.cm ===")
    r = dimensionar_torcao(
        TSd_kncm=6808.0, bw_cm=35.0, h_cm=50.0, c1_cm=4.125,
        fck_mpa=25.0, fywk_mpa=500.0, theta_deg=38.0, he_adotado_cm=10.0,
    )
    print(f"  he   = {r.he:.2f} cm")
    print(f"  Ae   = {r.Ae:.0f} cm2")
    print(f"  ue   = {r.ue:.0f} cm")
    print(f"  TRd,2 = {r.TRd2_kncm:.0f} kN.cm  (TSd={r.TSd_kncm:.0f})")
    print(f"  Asw  = {r.Asw_m:.2f} cm2/m  (min={r.Asw_min_m:.2f})")
    print(f"  As,long,total = {r.As_long_total_cm2:.2f} cm2 "
          f"(distribuir nos 4 lados)")


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
