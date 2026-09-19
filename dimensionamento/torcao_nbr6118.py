"""Torcao em Vigas de Concreto Armado (NBR 6118:2026).

Nome ate 19/09/2026: torcao_bastos.py. O credito as apostilas esta abaixo.

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
    validacao ja existente em cortante_nbr6118.modelo_calculo_II).

    P16 (achado da verificacao independente, volta 1): o erro fora da faixa
    normativa tem de ser ``nbr.FaixaNormativaError`` (subclasse de
    ValueError), nao um ValueError generico -- convencao 3.3 item 3 do
    plano. FaixaNormativaError e ValueError, entao quem hoje captura
    ValueError continua funcionando sem mudanca.
    """
    if not (THETA_MIN_DEG - 1e-6 <= theta_deg <= THETA_MAX_DEG + 1e-6):
        raise nbr.FaixaNormativaError(
            f"theta deve estar entre 30 e 45 graus (recebido {theta_deg})."
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


# === P16: Torcao completa e combinacao com flexao e cortante ===
#
# Completa a torção de 17.5: dispensa da torção de compatibilidade e limite
# de VSd em trecho curto (17.5.1.2), condição tripla de resistência à
# torção pura em modo verificação (17.5.1.3), seção composta de retângulos
# (17.5.1.4.2), seções já vazadas reais (17.5.1.4.3) e arranjo da armadura
# longitudinal nos vértices do estribo poligonal (17.5.1.6). A combinação
# com flexão e cortante (17.7) fica em combinacao_esforcos_nbr6118.py.
# As páginas citadas são as do PDF (impressa + 18).
# ---------------------------------------------------------------------------
try:
    import seguranca_nbr6118 as _seg_p16
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import seguranca_nbr6118 as _seg_p16

FaixaNormativaError = nbr.FaixaNormativaError


def _fmt_p16(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


# ---------------------------------------------------------------------------
# 17.5.1.2 -- dispensa da torção de compatibilidade (PDF p. 160)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoDispensaTorcaoCompatibilidade:
    """17.5.1.2: pode-se desprezar a torção de compatibilidade?"""

    necessaria_ao_equilibrio: bool
    adaptacao_plastica_adequada: bool
    pode_desprezar: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def torcao_compatibilidade_dispensavel(
    necessaria_ao_equilibrio: bool,
    adaptacao_plastica_adequada: bool,
) -> ResultadoDispensaTorcaoCompatibilidade:
    """Decide se a torção pode ser desprezada (17.5.1.2, PDF p. 160).

    "Quando a torção não for necessária ao equilíbrio, caso da torção de
    compatibilidade, é possível desprezá-la, desde que o elemento
    estrutural tenha a capacidade adequada de adaptação plástica e que
    todos os outros esforços sejam calculados sem considerar os efeitos por
    ela provocados." Isto é, só se desconsidera a torção quando ela NÃO for
    necessária ao equilíbrio (torção de compatibilidade) E o elemento tiver
    adaptação plástica adequada; caso contrário, a torção tem de ser
    considerada no dimensionamento. Quando dispensada, os demais esforços
    (M, V) devem ser recalculados sem os efeitos da torção desprezada --
    isso é responsabilidade do chamador, fora desta função.

    ``ok`` é sinônimo de ``pode_desprezar`` (uniformiza a API com os demais
    ``Resultado*`` do módulo, que sempre trazem ``ok`` ao lado do campo
    específico da classificação).
    """
    pode_desprezar = (not necessaria_ao_equilibrio) and adaptacao_plastica_adequada
    if necessaria_ao_equilibrio:
        motivo = "torção necessária ao equilíbrio -> não pode ser desprezada"
    elif not adaptacao_plastica_adequada:
        motivo = ("torção de compatibilidade, mas sem adaptação plástica "
                  "adequada -> não pode ser desprezada")
    else:
        motivo = ("torção de compatibilidade com adaptação plástica "
                  "adequada -> pode ser desprezada")
    memoria = (
        f"17.5.1.2: necessária ao equilíbrio = {necessaria_ao_equilibrio}; "
        f"adaptação plástica adequada = {adaptacao_plastica_adequada}.",
        f"17.5.1.2: {motivo}.",
    )
    return ResultadoDispensaTorcaoCompatibilidade(
        necessaria_ao_equilibrio=necessaria_ao_equilibrio,
        adaptacao_plastica_adequada=adaptacao_plastica_adequada,
        pode_desprezar=pode_desprezar,
        ok=pode_desprezar,
        governante=motivo,
        memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 17.5.1.2 -- limite de VSd em trecho curto de torção (PDF p. 160)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoTrechoCurtoTorcao:
    """17.5.1.2: limite de VSd quando o trecho sob torção é curto (<= 2h)."""

    l_cm: float
    h_cm: float
    VSd_kn: float
    VRd2_kn: float
    limite_VSd_kn: float
    trecho_curto: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_trecho_curto(l_cm: float, h_cm: float, VSd_kn: float,
                           VRd2_kn: float) -> ResultadoTrechoCurtoTorcao:
    """Em região com comprimento sob torção <= 2h, limita VSd <= 0,7 VRd2
    (17.5.1.2, PDF p. 160).

    "Em regiões onde o comprimento do elemento sujeito à torção seja menor
    ou igual a 2h, para garantir um nível razoável de capacidade de
    adaptação plástica, deve-se respeitar a armadura mínima de torção e
    limitar a força cortante, tal que: VSd <= 0,7 VRd2." Fora do trecho
    curto (l > 2h) esta função não impõe limite algum -- só verifica; a
    armadura mínima de torção (Asw,min, As,long,min) fica a cargo de
    Asw_min_cm2_por_m / As_long_min_cm2_por_m, sempre exigível.

    A comparação VSd <= 0,7 VRd2 (Rd >= Sd) passa por
    seguranca_nbr6118.verificar_seguranca, fonte única de tolerância e
    semântica dessa condição.

    l_cm: comprimento do trecho do elemento sujeito à torção; h_cm: altura
    da seção. VSd_kn, VRd2_kn: kN.
    """
    trecho_curto = l_cm <= 2.0 * h_cm + 1e-9
    limite = 0.7 * VRd2_kn
    if trecho_curto:
        seg = _seg_p16.verificar_seguranca(limite, VSd_kn, "VSd x 0,7 VRd2",
                                           "17.5.1.2")
        ok = seg.ok
        governante = (f"17.5.1.2: trecho curto (l={_fmt_p16(l_cm)} <= "
                     f"2h={_fmt_p16(2.0 * h_cm)}), VSd <= 0,7 VRd2 -> "
                     f"{'ok' if ok else 'não ok'}")
        seg_memoria = seg.memoria
    else:
        ok = True
        governante = (f"17.5.1.2: trecho não curto (l={_fmt_p16(l_cm)} > "
                     f"2h={_fmt_p16(2.0 * h_cm)}) -> limite não se aplica")
        seg_memoria = ()
    memoria = (
        f"17.5.1.2: l = {_fmt_p16(l_cm)} cm, h = {_fmt_p16(h_cm)} cm, "
        f"2h = {_fmt_p16(2.0 * h_cm)} cm -> trecho "
        f"{'curto' if trecho_curto else 'não curto'}.",
        f"17.5.1.2: 0,7 VRd2 = 0,7 x {_fmt_p16(VRd2_kn)} = "
        f"{_fmt_p16(limite)} kN; VSd = {_fmt_p16(VSd_kn)} kN -> "
        f"{'ok' if ok else 'não ok'}.",
        *seg_memoria,
    )
    return ResultadoTrechoCurtoTorcao(
        l_cm=l_cm, h_cm=h_cm, VSd_kn=VSd_kn, VRd2_kn=VRd2_kn,
        limite_VSd_kn=limite, trecho_curto=trecho_curto, ok=ok,
        governante=governante, memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 17.5.1.3 -- condição tripla de resistência à torção pura, modo verificação
# (PDF p. 160, com TRd3/TRd4 de 17.5.1.6, PDF p. 162)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoVerificacaoTorcao:
    """Verificação de seção com Asw e Asl existentes (17.5.1.3)."""

    TSd_kncm: float
    Asw_cm2_por_m: float
    Asl_cm2: float
    theta_deg: float
    he_cm: float
    Ae_cm2: float
    ue_cm: float
    TRd2_kncm: float
    TRd3_kncm: float
    TRd4_kncm: float
    ok_TRd2: bool
    ok_TRd3: bool
    ok_TRd4: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_torcao(
    TSd_kncm: float,
    Asw_cm2_por_m: float,
    Asl_cm2: float,
    bw_cm: float,
    h_cm: float,
    c1_cm: float,
    fck_mpa: float,
    fywk_mpa: float = 500.0,
    theta_deg: float = 45.0,
    gama_c: float = GAMA_C,
    gama_s: float = GAMA_S,
    he_adotado_cm: float | None = None,
) -> ResultadoVerificacaoTorcao:
    """Verifica se a seção com Asw e Asl EXISTENTES resiste a TSd (17.5.1.3,
    PDF p. 160): admite-se satisfeita a resistência quando, simultaneamente,
    TSd <= TRd2, TSd <= TRd3 e TSd <= TRd4.

        TRd2 (17.5.1.5, PDF p. 161) -- ver TRd2_kncm.
        TRd3 = (Asw/s)*fywd*2*Ae*cotg(theta)  (17.5.1.6 a, PDF p. 162)
        TRd4 = (Asl/ue)*2*Ae*fywd*tan(theta)  (17.5.1.6 b, PDF p. 162)

    Ao contrário de ``dimensionar_torcao`` (que resolve Asw/Asl a partir de
    TSd e portanto sempre "acerta" TRd3 = TRd4 = TSd por construção), aqui
    Asw_cm2_por_m e Asl_cm2 são dados (armadura já lançada) e TRd3/TRd4 são
    calculados e comparados com TSd.

    Asw_cm2_por_m: armadura transversal de torção existente (cm2/m); Asl_cm2:
    soma das áreas das barras longitudinais de torção existentes (cm2, já
    distribuída no perímetro ue). As comparações Rd >= Sd passam por
    seguranca_nbr6118.verificar_seguranca.
    """
    _validar_theta_torcao(theta_deg)
    sec = secao_vazada_retangular(bw_cm, h_cm, c1_cm, he_adotado_cm)
    Ae, he, ue = sec["Ae_cm2"], sec["he_cm"], sec["ue_cm"]
    TRd2 = TRd2_kncm(fck_mpa, Ae, he, theta_deg, gama_c)
    fywd = fywd_kncm2(fywk_mpa, gama_s)
    theta_rad = math.radians(theta_deg)
    asw_s = Asw_cm2_por_m / 100.0  # cm2/cm
    TRd3 = asw_s * fywd * 2.0 * Ae / math.tan(theta_rad)
    TRd4 = (Asl_cm2 / ue) * 2.0 * Ae * fywd * math.tan(theta_rad)

    s2 = _seg_p16.verificar_seguranca(TRd2, TSd_kncm, "TSd x TRd2", "17.5.1.3")
    s3 = _seg_p16.verificar_seguranca(TRd3, TSd_kncm, "TSd x TRd3", "17.5.1.3")
    s4 = _seg_p16.verificar_seguranca(TRd4, TSd_kncm, "TSd x TRd4", "17.5.1.3")

    falhas = []
    if not s2.ok:
        falhas.append("TSd > TRd2 (bielas comprimidas)")
    if not s3.ok:
        falhas.append("TSd > TRd3 (estribos)")
    if not s4.ok:
        falhas.append("TSd > TRd4 (armadura longitudinal)")
    ok = not falhas
    governante = ("17.5.1.3: ok (TSd <= TRd2, TRd3 e TRd4)" if ok
                 else "; ".join(falhas))

    memoria = (
        f"17.5.1.3: TSd = {_fmt_p16(TSd_kncm)} kN.cm; "
        f"theta = {_fmt_p16(theta_deg)} graus.",
        f"17.5.1.5: TRd2 = {_fmt_p16(TRd2)} kN.cm.",
        f"17.5.1.6 a): TRd3 = (Asw/s).fywd.2.Ae.cotg(theta) = "
        f"{_fmt_p16(asw_s)} x {_fmt_p16(fywd)} x 2 x {_fmt_p16(Ae)} / "
        f"tan({_fmt_p16(theta_deg)}) = {_fmt_p16(TRd3)} kN.cm.",
        f"17.5.1.6 b): TRd4 = (Asl/ue).2.Ae.fywd.tan(theta) = "
        f"({_fmt_p16(Asl_cm2)}/{_fmt_p16(ue)}) x 2 x {_fmt_p16(Ae)} x "
        f"{_fmt_p16(fywd)} x tan({_fmt_p16(theta_deg)}) = "
        f"{_fmt_p16(TRd4)} kN.cm.",
        *s2.memoria, *s3.memoria, *s4.memoria,
    )
    return ResultadoVerificacaoTorcao(
        TSd_kncm=TSd_kncm, Asw_cm2_por_m=Asw_cm2_por_m, Asl_cm2=Asl_cm2,
        theta_deg=theta_deg, he_cm=he, Ae_cm2=Ae, ue_cm=ue,
        TRd2_kncm=TRd2, TRd3_kncm=TRd3, TRd4_kncm=TRd4,
        ok_TRd2=s2.ok, ok_TRd3=s3.ok, ok_TRd4=s4.ok, ok=ok,
        governante=governante, memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 17.5.1.4.2 -- seção composta de retângulos (PDF p. 161)
# ---------------------------------------------------------------------------
def repartir_torcao_secao_composta(
    retangulos: "list[tuple[float, float]] | tuple[tuple[float, float], ...]",
    TSd_kncm: float,
) -> tuple[float, ...]:
    """Reparte TSd entre os retângulos de uma seção composta -- T, L, I
    maciço -- proporcionalmente à rigidez elástica linear de cada um
    (17.5.1.4.2, PDF p. 161):

        TSdi = TSd * (ai^3 * bi) / soma(ai^3 * bi)

    onde ai é o lado menor e bi o lado maior de cada retângulo i. Cada
    retângulo deve depois ser verificado isoladamente com a seção vazada
    equivalente de 17.5.1.4.1 (``secao_vazada_retangular``/``TRd2_kncm``/
    ``dimensionar_torcao``, com TSdi no lugar de TSd).

    retangulos: sequência de pares (ai_cm, bi_cm), ai <= bi. Devolve a
    tupla (TSd1, TSd2, ...) na mesma ordem, em kN.cm.
    """
    if not retangulos:
        raise ValueError("informe ao menos um retângulo da seção composta.")
    rigidezes = []
    for i, (a, b) in enumerate(retangulos):
        if a <= 0.0 or b <= 0.0:
            raise FaixaNormativaError(
                f"retângulo {i}: lados têm de ser positivos (a={a}, b={b})."
            )
        if a > b:
            raise FaixaNormativaError(
                f"retângulo {i}: a (lado menor) = {a} > b (lado maior) = "
                f"{b}; troque a ordem (17.5.1.4.2)."
            )
        rigidezes.append(a ** 3 * b)
    soma = sum(rigidezes)
    return tuple(TSd_kncm * r / soma for r in rigidezes)


# ---------------------------------------------------------------------------
# 17.5.1.4.3 -- seções já vazadas reais (caixão, celular) (PDF p. 161)
# ---------------------------------------------------------------------------
def espessura_parede_vazada_real(he_real_cm: float, bw_cm: float,
                                 h_cm: float) -> float:
    """Espessura de parede a considerar em seção JÁ vazada -- viga caixão,
    laje celular -- (17.5.1.4.3, PDF p. 161), diferente da seção vazada
    EQUIVALENTE de uma seção cheia (17.5.1.4.1).

    "Deve ser considerada a menor espessura de parede entre: a espessura
    real da parede; a espessura equivalente calculada supondo a seção
    cheia de mesmo contorno externo da seção vazada."

        he = min(he_real, A/u)

    onde A e u são a área e o perímetro da seção CHEIA de contorno externo
    bw_cm x h_cm (mesmo contorno da seção vazada real). he_real_cm: espessura
    real da parede, medida no ponto considerado.
    """
    if he_real_cm <= 0.0:
        raise FaixaNormativaError("he_real tem de ser positiva (17.5.1.4.3).")
    A = bw_cm * h_cm
    u = 2.0 * (bw_cm + h_cm)
    he_equivalente = A / u
    return min(he_real_cm, he_equivalente)


# ---------------------------------------------------------------------------
# 17.5.1.6 -- arranjo da armadura longitudinal de torção (PDF p. 162)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoDistribuicaoAslTorcao:
    """17.5.1.6: distribuição de As,l pelos trechos do perímetro ue."""

    As_long_total_cm2: float
    ue_cm: float
    taxa_cm2_por_cm: float
    trechos_cm: tuple[float, ...]
    As_por_trecho_cm2: tuple[float, ...]
    barras_por_vertice: "tuple[int, ...] | None"
    ok_vertices: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def distribuir_armadura_longitudinal_torcao(
    As_long_total_cm2: float,
    ue_cm: float,
    trechos_cm: "list[float] | tuple[float, ...]",
    barras_por_vertice: "list[int] | tuple[int, ...] | None" = None,
) -> ResultadoDistribuicaoAslTorcao:
    """Distribui a armadura longitudinal total de torção pelos trechos do
    perímetro do estribo poligonal, mantendo delta_As,l/delta_u constante
    (17.5.1.6, PDF p. 162):

        delta_As,l / delta_u = As,l,total / ue  (constante ao longo do
        perímetro)

    e confere a exigência de pelo menos uma barra longitudinal em cada
    vértice do estribo poligonal ("Nas seções poligonais, em cada vértice
    dos estribos de torção, deve ser colocada pelo menos uma barra
    longitudinal.").

    trechos_cm: comprimento de cada trecho do perímetro Ae (a soma tem de
    ser igual a ue_cm, com tolerância relativa de 1e-6). barras_por_vertice:
    número de barras longitudinais alocadas em cada vértice do estribo
    poligonal (um valor por vértice); None pula essa verificação (só
    calcula a distribuição proporcional).
    """
    soma = sum(trechos_cm)
    tol = 1e-6 * max(ue_cm, 1.0)
    if abs(soma - ue_cm) > tol:
        raise FaixaNormativaError(
            f"soma dos trechos ({_fmt_p16(soma)} cm) tem de ser igual a "
            f"ue ({_fmt_p16(ue_cm)} cm) (17.5.1.6)."
        )
    taxa = As_long_total_cm2 / ue_cm
    as_trechos = tuple(taxa * t for t in trechos_cm)

    if barras_por_vertice is None:
        ok_vertices = True
        barras_tupla = None
        vert_txt = "não informado (verificação pulada)"
    else:
        barras_tupla = tuple(barras_por_vertice)
        ok_vertices = all(n >= 1 for n in barras_tupla)
        vert_txt = str(barras_tupla)

    ok = ok_vertices
    governante = ("17.5.1.6: ok" if ok else
                 "17.5.1.6: há vértice do estribo poligonal sem barra "
                 "longitudinal")
    memoria = (
        f"17.5.1.6: delta_As,l/delta_u = As,l,total/ue = "
        f"{_fmt_p16(As_long_total_cm2)} / {_fmt_p16(ue_cm)} = "
        f"{_fmt_p16(taxa)} cm2/cm (constante ao longo do perímetro).",
        f"17.5.1.6: trechos (cm) = {tuple(round(t, 4) for t in trechos_cm)}; "
        f"As por trecho (cm2) = {tuple(round(a, 4) for a in as_trechos)}.",
        f"17.5.1.6: barras por vértice = {vert_txt} -> "
        f"{'ok' if ok_vertices else 'não ok'}.",
    )
    return ResultadoDistribuicaoAslTorcao(
        As_long_total_cm2=As_long_total_cm2, ue_cm=ue_cm,
        taxa_cm2_por_cm=taxa, trechos_cm=tuple(trechos_cm),
        As_por_trecho_cm2=as_trechos, barras_por_vertice=barras_tupla,
        ok_vertices=ok_vertices, ok=ok, governante=governante,
        memoria=memoria,
    )


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
