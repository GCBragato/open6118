"""Vigas de Concreto Armado - Verificacoes de Servico (NBR 6118:2023).

Nome ate 19/09/2026: viga_servico_bastos.py. O credito as apostilas esta abaixo.

Implementa as verificacoes de servico (estado-limite de servico) seguindo
a apostila "VIGAS DE CONCRETO ARMADO - Dimensionamento, Flecha e
Fissuracao", Prof. Paulo Sergio Bastos, UNESP/Bauru.

A flexao, cortante e ancoragem estao em scripts irmaos:
    vigas_nbr6118.py, cortante_nbr6118.py, ancoragem_nbr6118.py.

Conteudo unico desta apostila implementado aqui:
    - Posicao da linha neutra no Estadio II (Eq. 60 retangular e Eq. 64 T).
    - Momento de inercia no Estadio II (Eq. 61 e Eq. 65).
    - Razao modular alpha_e = Es / Ecs (Eq. 68).
    - Decalagem do diagrama de forcas no banzo tracionado (Eq. 31, 34).
    - Verificacao da fissuracao wk (Eqs. 86 e 87 / NBR 6118 17.3.3.2).

Convencoes:
    - Resistencias em MPa, geometria em cm, momentos em kN.cm,
      tensao no aco em kN/cm2.
"""

from __future__ import annotations

import math
import sys
import warnings
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

try:  # executado como script, ou com dimensionamento/ no sys.path
    import analise_linear_nbr6118 as _analise_linear
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import analise_linear_nbr6118 as _analise_linear


GAMA_C = 1.4
GAMA_S = 1.15

E_S_KNCM2 = 21000.0          # 210 GPa
E_S_MPA = 210000.0


# ---------------------------------------------------------------------------
# Modulos de elasticidade do concreto (NBR 6118 8.2.8)
# ---------------------------------------------------------------------------
def alpha_E(agregado: str = "granito") -> float:
    """Coef alpha_E pela NBR 6118 (Eq. 71/72).

    granito/gnaisse = 1.0; basalto/diabasio = 1.2; calcario = 0.9;
    arenito = 0.7.
    """
    return {
        "granito": 1.0, "gnaisse": 1.0,
        "basalto": 1.2, "diabasio": 1.2,
        "calcario": 0.9,
        "arenito": 0.7,
    }.get(agregado.lower(), 1.0)


def Eci_mpa(fck_mpa: float, agregado: str = "granito") -> float:
    """Modulo de elasticidade inicial Eci (MPa).
    fck <= 50: Eci = alpha_E * 5600 * sqrt(fck);
    fck > 50:  Eci = 21500 * alpha_E * (fck/10 + 1.25)^(1/3)."""
    aE = alpha_E(agregado)
    if fck_mpa <= 50.0:
        return aE * 5600.0 * math.sqrt(fck_mpa)
    return 21500.0 * aE * (fck_mpa / 10.0 + 1.25) ** (1.0 / 3.0)


def Ecs_mpa(fck_mpa: float, agregado: str = "granito") -> float:
    """Modulo secante Ecs = alpha_i * Eci, com
    alpha_i = 0.8 + 0.2 * fck/80 <= 1.0 (Eq. 70)."""
    alpha_i = min(1.0, 0.8 + 0.2 * fck_mpa / 80.0)
    return alpha_i * Eci_mpa(fck_mpa, agregado)


def alpha_e(fck_mpa: float, agregado: str = "granito") -> float:
    """Razao modular alpha_e = Es / Ecs (Eq. 68)."""
    return E_S_MPA / Ecs_mpa(fck_mpa, agregado)


# ---------------------------------------------------------------------------
# Estadio II - Posicao da linha neutra e Inercia
# ---------------------------------------------------------------------------
def x_II_retangular(bw_cm: float, d_cm: float, As_cm2: float,
                    As_linha_cm2: float, d_linha_cm: float,
                    alpha_e_val: float) -> float:
    """Posicao da linha neutra no Estadio II - secao retangular (Eq. 60).

    bw/2 * x^2 + alpha_e * (As + As') * x
        - alpha_e * (As*d + As'*d') = 0
    """
    a = bw_cm / 2.0
    b = alpha_e_val * (As_cm2 + As_linha_cm2)
    c = -alpha_e_val * (As_cm2 * d_cm + As_linha_cm2 * d_linha_cm)
    disc = b * b - 4.0 * a * c
    if disc < 0:
        raise ValueError("discriminante negativo em x_II")
    return (-b + math.sqrt(disc)) / (2.0 * a)


def I_II_retangular(bw_cm: float, d_cm: float, x_II_cm: float,
                    As_cm2: float, As_linha_cm2: float, d_linha_cm: float,
                    alpha_e_val: float) -> float:
    """Momento de inercia no Estadio II - secao retangular (Eq. 61).

    III = bw * x^3 / 3 + alpha_e*As*(d - x)^2 + alpha_e*As'*(x - d')^2
    """
    return (bw_cm * x_II_cm ** 3 / 3.0
            + alpha_e_val * As_cm2 * (d_cm - x_II_cm) ** 2
            + alpha_e_val * As_linha_cm2 * (x_II_cm - d_linha_cm) ** 2)


def x_II_secao_T(bf_cm: float, bw_cm: float, hf_cm: float, d_cm: float,
                 As_cm2: float, As_linha_cm2: float, d_linha_cm: float,
                 alpha_e_val: float) -> float:
    """Linha neutra no Estadio II - secao T (Eq. 64), assumindo x > hf.

    bw/2 * x^2 + [alpha_e*(As + As') + (bf - bw)*hf] * x
        - [alpha_e*(As*d + As'*d') + (bf - bw)*hf^2/2] = 0
    """
    a = bw_cm / 2.0
    b = alpha_e_val * (As_cm2 + As_linha_cm2) + (bf_cm - bw_cm) * hf_cm
    c = -(alpha_e_val * (As_cm2 * d_cm + As_linha_cm2 * d_linha_cm)
          + (bf_cm - bw_cm) * hf_cm * hf_cm / 2.0)
    disc = b * b - 4.0 * a * c
    if disc < 0:
        raise ValueError("discriminante negativo em x_II_secao_T")
    return (-b + math.sqrt(disc)) / (2.0 * a)


def I_II_secao_T(bf_cm: float, bw_cm: float, hf_cm: float, d_cm: float,
                 x_II_cm: float, As_cm2: float, As_linha_cm2: float,
                 d_linha_cm: float, alpha_e_val: float) -> float:
    """Inercia Estadio II - secao T (Eq. 65), x > hf.

    III = bf*x^3/3 - (bf-bw)*(x-hf)^3/3
          + alpha_e*As*(d - x)^2 + alpha_e*As'*(x - d')^2
    """
    inercia = bf_cm * x_II_cm ** 3 / 3.0
    if x_II_cm > hf_cm:
        inercia -= (bf_cm - bw_cm) * (x_II_cm - hf_cm) ** 3 / 3.0
    inercia += alpha_e_val * As_cm2 * (d_cm - x_II_cm) ** 2
    inercia += alpha_e_val * As_linha_cm2 * (x_II_cm - d_linha_cm) ** 2
    return inercia


# ---------------------------------------------------------------------------
# Decalagem do diagrama (item 13.1)
# ---------------------------------------------------------------------------
def decalagem_modelo_I(d_cm: float, VSd_kn: float, Vc_kn: float,
                       alfa_deg: float = 90.0) -> float:
    """Decalagem a_l (cm) - Modelo I, banzo tracionado (NBR 6118:2026
    17.4.2.2 c), PDF p. 158; generaliza a Eq. 31 da apostila, que so
    cobria estribos a 90 graus).

    a_l = d, para |VSd,max| <= |Vc| (antes devolvia 0.5*d - VIG-05: erro de
    -50% no caso VSd=45, Vc=49.6, d=46).

    Caso geral (cotg(alfa), antes ignorado - VIG-06):
        a_l = d*[VSd,max/(2*(VSd,max - Vc))*(1 + cotg alfa) - cotg alfa] <= d

    Pisos da norma: a_l >= 0.5*d no caso geral; a_l >= 0.2*d para estribos
    inclinados a 45 graus.
    """
    if abs(VSd_kn) <= abs(Vc_kn):
        return d_cm
    cot_a = 0.0 if alfa_deg == 90.0 else 1.0 / math.tan(math.radians(alfa_deg))
    a = d_cm * (VSd_kn / (2.0 * (VSd_kn - Vc_kn)) * (1.0 + cot_a) - cot_a)
    piso = 0.2 * d_cm if abs(alfa_deg - 45.0) < 1e-9 else 0.5 * d_cm
    return max(min(a, d_cm), piso)


def decalagem_modelo_II(d_cm: float, theta_deg: float = 30.0,
                        alfa_deg: float = 90.0,
                        VSd_kn: float | None = None,
                        Vc_kn: float | None = None) -> float:
    """Decalagem a_l (cm) - Modelo II, banzo tracionado (NBR 6118:2026
    17.4.2.3 c), PDF p. 159: "mantidas a notacao e as limitacoes definidas
    em 17.4.2.2").

    Formula completa (usada quando VSd_kn e Vc_kn sao informados; Vc = Vc1
    na flexao simples, 17.4.1.1):
        a_l = 0.5*d*[VSd,max/(VSd,max - Vc)*(cotg theta + cotg alfa) - cotg alfa] <= d
    a_l = d, para |VSd,max| <= |Vc|. Pisos: a_l >= 0.5*d no caso geral;
    a_l >= 0.2*d para estribos inclinados a 45 graus.

    Sem VSd_kn e Vc_kn a formula da norma nao pode ser calculada (falta
    Vc). A apostila simplifica fazendo Vc = 0 (a_l = 0.5*cotg(theta)*d),
    mas isso sempre SUBESTIMA a_l - contra a seguranca (VIG-07: -13,4% no
    caso d=46, theta=30, VSd=153, Vc=49.6, onde o correto e a_l = d).
    Em vez de repetir esse atalho, a funcao avisa e devolve o limite
    conservador a_l = d.
    """
    piso = 0.2 * d_cm if abs(alfa_deg - 45.0) < 1e-9 else 0.5 * d_cm
    if VSd_kn is None or Vc_kn is None:
        warnings.warn(
            "decalagem_modelo_II sem VSd_kn/Vc_kn: a formula completa da "
            "NBR 6118:2026 17.4.2.3 c) exige Vc (= Vc1 na flexao simples). "
            "O atalho antigo (Vc = 0) subestima a_l; adotado o limite "
            "conservador a_l = d. Informe VSd_kn e Vc_kn para o valor exato.",
            stacklevel=2,
        )
        return d_cm
    if abs(VSd_kn) <= abs(Vc_kn):
        return d_cm
    cot_t = 0.0 if theta_deg == 90.0 else 1.0 / math.tan(math.radians(theta_deg))
    cot_a = 0.0 if alfa_deg == 90.0 else 1.0 / math.tan(math.radians(alfa_deg))
    a = 0.5 * d_cm * (VSd_kn / (VSd_kn - Vc_kn) * (cot_t + cot_a) - cot_a)
    return max(min(a, d_cm), piso)


# ---------------------------------------------------------------------------
# Verificacao de fissuracao (NBR 6118 17.3.3.2)
# ---------------------------------------------------------------------------
@dataclass
class ResultadoFissuracao:
    sigma_si_kncm2: float
    rho_ri: float
    Acr_cm2: float
    eta1: float
    fctm_kncm2: float
    wk1_mm: float
    wk2_mm: float
    wk_mm: float
    wk_max_mm: float
    ok: bool


def fctm_kncm2(fck_mpa: float) -> float:
    """fct,m em kN/cm2, delegado ao nucleo normativo (8.2.5).

    Antes sempre 0,3*fck^(2/3) (valido so ate C50); a NBR 6118:2026 usa
    2,12*ln[1 + 0,1*(fck + 8)] acima disso (nbr.fct_m). Usada em
    abertura_fissura_wk (wk2): sem o ramo, fctm saia alto demais para
    fck > 50 e wk2 saia baixo demais - 9,5% (C70) a 16,3% (C90), contra a
    seguranca (VIG-10)."""
    return nbr.mpa_para_kncm2(nbr.fct_m(fck_mpa))


# ---------------------------------------------------------------------------
# Largura efetiva de mesa colaborante (NBR 6118 14.6.2.2)
# ---------------------------------------------------------------------------
# Promovidas para analise_linear_nbr6118.py no P14 (19/09/2026): a formula
# (com o caso de borda/b4 da Figura 14.2 que faltava aqui) agora mora la.
# Mantidas aqui como fachada de uma linha para nao quebrar quem ja importava
# vao_a_para_mesa/largura_efetiva_mesa deste modulo - mesma assinatura e
# mesmo resultado de antes.
vao_a_para_mesa = _analise_linear.vao_a_para_mesa
largura_efetiva_mesa = _analise_linear.largura_efetiva_mesa


def sigma_si_aproximada(Md_ser_kncm: float, d_cm: float,
                        As_cm2: float) -> float:
    """sigma_si = Md,ser / (0.85 * d * As)  (Eq. 89, kN/cm2)."""
    return Md_ser_kncm / (0.85 * d_cm * As_cm2)


def sigma_si_estadio_II(Md_ser_kncm: float, d_cm: float, x_II_cm: float,
                        I_II_cm4: float, alpha_e_val: float) -> float:
    """sigma_si na armadura tracionada, Estadio II (secao fissurada), kN/cm2.

    sigma_si = alpha_e * Md,ser * (d - x_II) / I_II, pela mecanica da secao
    transformada fissurada. Usa x_II e I_II ja calculados por
    x_II_retangular/x_II_secao_T e I_II_retangular/I_II_secao_T (o chamador
    escolhe a formula pela forma da secao).

    NBR 6118 17.3.3.2/17.3.3.3 pedem sigma_si no Estadio II para o calculo
    de wk. sigma_si_aproximada() (Eq. 89 da apostila) usa braco fixo 0.85d
    e fica a favor da seguranca (VIG-09, escolha documentada: +12,3% no
    exemplo da apostila item 17.1 - viga-ponte); esta funcao usa a rigidez
    fissurada real e reproduz o valor da norma nesse exemplo (22.43 kN/cm2
    contra os 25.18 kN/cm2 de sigma_si_aproximada). Nao substitui
    sigma_si_aproximada, que continua disponivel para o calculo rapido.
    """
    return alpha_e_val * Md_ser_kncm * (d_cm - x_II_cm) / I_II_cm4


def abertura_fissura_wk(
    phi_mm: float,
    sigma_si_kncm2: float,
    Acr_cm2: float,
    As_cm2: float,
    fck_mpa: float,
    eta1_val: float = 2.25,
    Es_kncm2: float = E_S_KNCM2,
    wk_max_mm: float = 0.30,
    caa: str | None = None,
    tipo_concreto: str = "armado",
    nivel_protensao: int | None = None,
    tipo_protensao: str | None = None,
) -> ResultadoFissuracao:
    """wk (mm) pelo menor entre Eq. 86 e Eq. 87.

    wk1 = (phi / (12.5 * eta1)) * (sigma_si / Es) * (4 / rho_ri + 45)
    wk2 = (phi / (12.5 * eta1)) * (sigma_si / Es) * (3 * sigma_si / fctm)
    Resultados em mm (entrada phi em mm).

    caa (P1, 13.4.2): se informado, wk_max_mm passa a vir da Tabela 13.4
    (nucleo_nbr6118.wk_max_mm), com tipo_concreto/nivel_protensao/
    tipo_protensao; o wk_max_mm explícito continua como alternativa (usado
    quando caa é None, que é o padrão — compatível com o comportamento
    anterior a este pacote). Para tipo_concreto='protendido' com nível 2 ou
    3, a Tabela 13.4 não dá um wk_max numérico (a exigência é ELS-F/ELS-D,
    não wk): a função levanta ValueError nesse caso, citando a exigência.
    """
    if caa is not None:
        limite, combinacao = nbr.wk_max_mm(tipo_concreto, caa, nivel_protensao, tipo_protensao)
        if limite is None:
            raise ValueError(
                f"A Tabela 13.4 não dá wk_max para {tipo_concreto!r} nesse caso "
                f"(exigência: {combinacao}); verifique ELS-F/ELS-D, não wk."
            )
        wk_max_mm = limite
    rho = As_cm2 / Acr_cm2
    fctm = fctm_kncm2(fck_mpa)
    base = (phi_mm / (12.5 * eta1_val)) * (sigma_si_kncm2 / Es_kncm2)
    wk1 = base * (4.0 / rho + 45.0)
    wk2 = base * (3.0 * sigma_si_kncm2 / fctm)
    wk = min(wk1, wk2)
    return ResultadoFissuracao(
        sigma_si_kncm2=sigma_si_kncm2,
        rho_ri=rho,
        Acr_cm2=Acr_cm2,
        eta1=eta1_val,
        fctm_kncm2=fctm,
        wk1_mm=wk1,
        wk2_mm=wk2,
        wk_mm=wk,
        wk_max_mm=wk_max_mm,
        ok=wk <= wk_max_mm,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def test_alpha_e_C40() -> None:
    """C40, granito: Ecs = 32 GPa -> alpha_e = 21000/3200 = 6.56."""
    ae = alpha_e(40.0, "granito")
    assert _aprox(ae, 6.56, 0.10), f"alpha_e={ae:.2f}"
    print(f"  OK  alpha_e(C40, granito) = {ae:.2f}  (apostila: 6.56)")


def test_x_II_retangular_apostila() -> None:
    """Apostila ex. 16.12: bw=12, d=37, As=2.45 (3 phi 10), As'=0,
    fck=25 (Ecs=24 GPa), alpha_e=21000/2400=8.75.
    Esperado x_II ~ 8.75 cm e III ~ 19.860 cm4 (apostila item 16.12.3)."""
    ae = alpha_e(25.0, "granito")
    x_II = x_II_retangular(bw_cm=12.0, d_cm=37.0, As_cm2=2.45,
                           As_linha_cm2=0.0, d_linha_cm=0.0,
                           alpha_e_val=ae)
    III = I_II_retangular(bw_cm=12.0, d_cm=37.0, x_II_cm=x_II,
                          As_cm2=2.45, As_linha_cm2=0.0, d_linha_cm=0.0,
                          alpha_e_val=ae)
    # Verificacao auto-consistente: somando momentos estaticos em x_II = 0
    momento_estatico = (12.0 * x_II * x_II / 2.0
                        - ae * 2.45 * (37.0 - x_II))
    assert abs(momento_estatico) < 0.5, f"M_estatico={momento_estatico:.3f}"
    print(f"  OK  x_II = {x_II:.2f} cm  III = {III:.0f} cm4 "
          f"(M.estatico=0)")


def test_x_II_secao_T_apostila() -> None:
    """Apostila ex. 17.1 (viga ponte): C40, T com bf=325, bw=25, hf=20,
    d=186.5, As=137.20, As'=16.00, d'=3.5+0.8+0.8=5.1 cm.
    Apostila informa alpha_e ~ 6.56."""
    ae = alpha_e(40.0, "granito")
    x_II = x_II_secao_T(
        bf_cm=325.0, bw_cm=25.0, hf_cm=20.0, d_cm=186.5,
        As_cm2=137.20, As_linha_cm2=16.00, d_linha_cm=5.1,
        alpha_e_val=ae,
    )
    # Apostila chega proximo a x_II = 24-26 cm
    assert 18.0 < x_II < 35.0, f"x_II fora do esperado: {x_II:.2f}"
    III = I_II_secao_T(
        bf_cm=325.0, bw_cm=25.0, hf_cm=20.0, d_cm=186.5, x_II_cm=x_II,
        As_cm2=137.20, As_linha_cm2=16.00, d_linha_cm=5.1, alpha_e_val=ae,
    )
    print(f"  OK  Sec T: x_II = {x_II:.2f} cm  III = {III:.0f} cm4")


def test_decalagem_modelo_I() -> None:
    """NBR 6118:2026 17.4.2.2 c). Com alfa=90 (cotg=0) o caso geral se
    reduz a 0.5*d*VSd/(VSd-Vc), igual a apostila; por isso a1/a2 nao mudam
    (atualizado apenas o comentario, para a formula certa). Casos novos:
    a3 cobre VIG-05 (|VSd|<=|Vc| -> a_l = d, antes 0.5d) e a4 cobre VIG-06
    (cotg(alfa), antes ignorado)."""
    d = 46.0
    a1 = decalagem_modelo_I(d_cm=d, VSd_kn=153.0, Vc_kn=49.6)
    # d*[153/(2*(153-49.6))*(1+0) - 0] = 46*153/206.8 = 34.04 cm; <= d
    assert _aprox(a1, 34.04, 0.5), f"a_l={a1:.2f}"
    # caso Vsd ~ Vc (mas ainda > Vc) -> formula geral estoura d e e limitada a d
    a2 = decalagem_modelo_I(d_cm=d, VSd_kn=51.0, Vc_kn=49.6)
    assert _aprox(a2, d, 0.5), f"a_l={a2:.2f}"
    # VIG-05: |VSd| <= |Vc| -> a_l = d (achado: d=46,VSd=45,Vc=49.6 -> 46.0;
    # o codigo antigo devolvia 23.0 = 0.5d, -50%).
    a3 = decalagem_modelo_I(d_cm=d, VSd_kn=45.0, Vc_kn=49.6)
    assert _aprox(a3, d, 0.01), f"a_l={a3:.2f}"
    # VIG-06: cotg(alfa) com alfa=45 (achado: d=46,VSd=153,Vc=49.6,alfa=45
    # -> 22.07; o codigo antigo ignorava alfa e devolvia 34.03).
    a4 = decalagem_modelo_I(d_cm=d, VSd_kn=153.0, Vc_kn=49.6, alfa_deg=45.0)
    assert _aprox(a4, 22.07, 0.05), f"a_l={a4:.2f}"
    print(f"  OK  Modelo I: a_l(VSd=153,Vc=49.6) = {a1:.2f} cm  "
          f"a_l(VSd=51) = {a2:.2f} cm  a_l(VSd=45,|VSd|<=|Vc|) = {a3:.2f} cm  "
          f"a_l(alfa=45) = {a4:.2f} cm")


def test_decalagem_modelo_II() -> None:
    """NBR 6118:2026 17.4.2.3 c). Sem VSd_kn/Vc_kn a formula com Vc=0 da
    apostila subestima a_l (VIG-07): a funcao agora avisa e devolve o
    limite conservador a_l = d, em vez do antigo 0.5*cotg(theta)*d = 39.84.
    Com VSd_kn/Vc_kn informados (achado: d=46, theta=30, VSd=153, Vc=49.6),
    o valor correto e a_l = d = 46.0 cm (o raw da formula, 58.94, e limitado
    a d) - o codigo antigo dava 39.84 (-13,4%)."""
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        a_sem_dados = decalagem_modelo_II(d_cm=46.0, theta_deg=30.0)
    assert _aprox(a_sem_dados, 46.0, 0.01), f"a_l={a_sem_dados:.2f}"
    assert len(avisos) == 1 and issubclass(avisos[0].category, UserWarning)

    a = decalagem_modelo_II(d_cm=46.0, theta_deg=30.0, VSd_kn=153.0, Vc_kn=49.6)
    assert _aprox(a, 46.0, 0.05), f"a_l={a:.2f}"
    print(f"  OK  Modelo II theta=30 (sem VSd/Vc, avisa e usa d): "
          f"a_l = {a_sem_dados:.2f} cm;  (VSd=153,Vc=49.6): a_l = {a:.2f} cm")


def test_fissuracao_apostila_ex17_1() -> None:
    """Apostila item 17.1 (ex. ponte): wk1 = 0.11 mm, wk2 = 0.23 mm,
    wk adotado = 0.11 mm <= wk,max = 0.30 mm."""
    sigma = sigma_si_aproximada(
        Md_ser_kncm=547750.0, d_cm=186.5, As_cm2=137.20,
    )
    assert _aprox(sigma, 25.18, 0.05), f"sigma_si={sigma:.2f}"
    r = abertura_fissura_wk(
        phi_mm=25.0,
        sigma_si_kncm2=sigma,
        Acr_cm2=1888.8,
        As_cm2=137.20,
        fck_mpa=40.0,
        eta1_val=2.25,
        wk_max_mm=0.30,
    )
    assert _aprox(r.wk1_mm, 0.11, 0.02), f"wk1={r.wk1_mm:.3f}"
    assert _aprox(r.wk2_mm, 0.23, 0.02), f"wk2={r.wk2_mm:.3f}"
    assert _aprox(r.wk_mm, 0.11, 0.02), f"wk={r.wk_mm:.3f}"
    assert r.ok, "deveria atender wk <= 0.30"
    print(f"  OK  Fissuracao: sigma={sigma:.2f}, wk1={r.wk1_mm:.3f}, "
          f"wk2={r.wk2_mm:.3f}, wk={r.wk_mm:.3f} mm  (ok={r.ok})")


def test_modulos_elasticidade_C25() -> None:
    """C25 granito: Eci = 28000 MPa, Ecs = 24150 MPa (apostila)."""
    eci = Eci_mpa(25.0, "granito")
    ecs = Ecs_mpa(25.0, "granito")
    assert _aprox(eci, 28000.0, 200.0), f"Eci={eci:.0f}"
    # alpha_i = 0.8 + 0.2*25/80 = 0.8625; Ecs = 0.8625 * 28000 = 24150
    assert _aprox(ecs, 24150.0, 200.0), f"Ecs={ecs:.0f}"
    print(f"  OK  Eci(C25) = {eci:.0f} MPa  Ecs(C25) = {ecs:.0f} MPa")


def test_largura_efetiva_mesa_T_biapoiada() -> None:
    """Viga T biapoiada L=500 cm, bw=20 cm, b2_l_esq=b2_l_dir=300 cm.
    a = 500; b1 = b3 = min(0.5*300, 0.10*500) = min(150, 50) = 50.
    bf = 50 + 20 + 50 = 120 cm."""
    r = largura_efetiva_mesa(
        bw_cm=20.0, b2_l_esq_cm=300.0, b2_l_dir_cm=300.0,
        L_cm=500.0, tipo_vao="biapoiada", tipo_secao="T",
    )
    assert _aprox(r["a_cm"], 500.0, 0.1)
    assert _aprox(r["b1_cm"], 50.0, 0.1)
    assert _aprox(r["b3_cm"], 50.0, 0.1)
    assert _aprox(r["bf_cm"], 120.0, 0.1)
    print(f"  OK  Mesa T biapoiada L=500: bf = {r['bf_cm']:.0f} cm "
          f"(b1={r['b1_cm']:.0f}, b3={r['b3_cm']:.0f})")


def test_largura_efetiva_mesa_L_continua() -> None:
    """Viga L (extremidade), L=600, bw=20, b2_l=80 (apenas um lado).
    Vao continuo extremo: a=0.75*600=450.
    b1 = min(0.5*80, 0.10*450) = min(40, 45) = 40.
    bf = 40 + 20 = 60."""
    r = largura_efetiva_mesa(
        bw_cm=20.0, b2_l_esq_cm=80.0, b2_l_dir_cm=0.0,
        L_cm=600.0, tipo_vao="continua-extrema", tipo_secao="L",
    )
    assert _aprox(r["a_cm"], 450.0, 0.1)
    assert _aprox(r["b1_cm"], 40.0, 0.1)
    assert _aprox(r["b3_cm"], 0.0, 0.1)
    assert _aprox(r["bf_cm"], 60.0, 0.1)
    print(f"  OK  Mesa L continua: bf = {r['bf_cm']:.0f} cm")


def test_largura_efetiva_mesa_balanco() -> None:
    """Balanco L=200, bw=20, b2_l=400.
    a = 2*200 = 400; b1 = b3 = min(0.5*400, 0.10*400) = min(200, 40) = 40.
    bf = 40+20+40 = 100."""
    r = largura_efetiva_mesa(
        bw_cm=20.0, b2_l_esq_cm=400.0, b2_l_dir_cm=400.0,
        L_cm=200.0, tipo_vao="balanco", tipo_secao="T",
    )
    assert _aprox(r["bf_cm"], 100.0, 0.1)
    print(f"  OK  Mesa T balanco: bf = {r['bf_cm']:.0f} cm")


def run_tests() -> int:
    tests = [
        test_modulos_elasticidade_C25,
        test_alpha_e_C40,
        test_x_II_retangular_apostila,
        test_x_II_secao_T_apostila,
        test_decalagem_modelo_I,
        test_decalagem_modelo_II,
        test_fissuracao_apostila_ex17_1,
        test_largura_efetiva_mesa_T_biapoiada,
        test_largura_efetiva_mesa_L_continua,
        test_largura_efetiva_mesa_balanco,
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
    print("=== Verificacao de fissuracao - viga ponte (Apostila 17.1) ===")
    sigma = sigma_si_aproximada(547750.0, 186.5, 137.20)
    r = abertura_fissura_wk(
        phi_mm=25.0, sigma_si_kncm2=sigma, Acr_cm2=1888.8,
        As_cm2=137.20, fck_mpa=40.0, eta1_val=2.25, wk_max_mm=0.30,
    )
    print(f"  sigma_si = {sigma:.2f} kN/cm2")
    print(f"  rho_ri   = {r.rho_ri:.4f}")
    print(f"  wk1      = {r.wk1_mm:.3f} mm")
    print(f"  wk2      = {r.wk2_mm:.3f} mm")
    print(f"  wk       = {r.wk_mm:.3f} mm  (max = {r.wk_max_mm} mm)")
    print(f"  ok       = {r.ok}")


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
