"""Núcleo normativo — ABNT NBR 6118:2026.

Fonte única das grandezas de material e dos parâmetros da norma usados por
todos os módulos de dimensionamento do open6118. Nenhum módulo deve
reimplementar estas fórmulas: importe daqui.

Norma: ABNT NBR 6118:2026, 5ª edição (11/03/2026), equivalente à
NBR 6118:2023 Versão Corrigida 2:2024 + Emenda 1. As páginas citadas são as
do PDF (a página impressa é 18 a menos).

Unidades:
    - fck, tensões e módulos de elasticidade em MPa
      (as funções com sufixo ``_kncm2`` devolvem kN/cm², 1 kN/cm² = 10 MPa);
    - deformações em ‰ (por mil);
    - diâmetros em mm; comprimentos de seção em cm; idades em dias.

Faixa de validade: C20 a C90 (8.2.1), com C25 no mínimo quando há armadura
ativa. Fora dela as funções levantam ``FaixaNormativaError`` (subclasse de
``ValueError``) em vez de devolver um número calculado com a fórmula errada.
"""

from __future__ import annotations

import math
import unicodedata

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
FCK_MIN = 20.0              # 8.2.1 — concreto com armadura passiva
FCK_MIN_PROTENDIDO = 25.0   # 8.2.1 — concreto com armadura ativa
FCK_MAX = 90.0              # 8.2.1 — Grupo II vai até C90
FCKJ_MIN = 7.0              # 8.2.5 — expressões de fct valem para fckj >= 7 MPa

ES_MPA = 210000.0           # 8.3.5 — aço de armadura passiva
EP_MPA = 200000.0           # 8.4.4 — aço de armadura ativa
EPS_SU = 10.0               # Figura 17.1 — alongamento-limite da armadura (pivô A), ‰

# Tabela 12.1 — coeficientes de ponderação das resistências no ELU
GAMA_C = 1.4
GAMA_S = 1.15
GAMAS_TABELA_12_1 = {
    "normal": (1.4, 1.15),
    "especial": (1.2, 1.15),
    "construcao": (1.2, 1.15),
    "excepcional": (1.2, 1.0),
}


class FaixaNormativaError(ValueError):
    """Entrada fora da faixa em que a NBR 6118:2026 (ou a fórmula) vale."""


def _chave(texto: str) -> str:
    """Normaliza um rótulo: minúsculas, sem acento, sem espaço, hífen ou sublinhado."""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower().replace(" ", "").replace("-", "").replace("_", "")


# ---------------------------------------------------------------------------
# Faixa de validade — 8.2.1 (PDF p. 41-42)
# ---------------------------------------------------------------------------
def validar_fck(fck_mpa: float, protendido: bool = False) -> float:
    """Confere 20 <= fck <= 90 MPa (25 <= fck com armadura ativa) e devolve fck."""
    fck = float(fck_mpa)
    minimo = FCK_MIN_PROTENDIDO if protendido else FCK_MIN
    if not (minimo <= fck <= FCK_MAX):
        raise FaixaNormativaError(
            f"fck = {fck:g} MPa fora da faixa da NBR 6118:2026 "
            f"({minimo:g} a {FCK_MAX:g} MPa{', com armadura ativa' if protendido else ''})."
        )
    return fck


def grupo_resistencia(fck_mpa: float) -> str:
    """'I' para C20 a C50, 'II' para C55 a C90 (8.2.1)."""
    return "I" if validar_fck(fck_mpa) <= 50.0 else "II"


def mpa_para_kncm2(valor_mpa: float) -> float:
    """1 MPa = 0,1 kN/cm²."""
    return valor_mpa / 10.0


# ---------------------------------------------------------------------------
# Cobrimento nominal — Tabela 7.2 (PDF p. 39), Δc = 10 mm
# ---------------------------------------------------------------------------
_CAA = {"i": 0, "1": 0, "ii": 1, "2": 1, "iii": 2, "3": 2, "iv": 3, "4": 3}
_COBRIMENTO_TABELA_7_2 = {   # mm, CAA I, II, III, IV
    ("armado", "laje"): (20, 25, 35, 45),
    ("armado", "vigapilar"): (25, 30, 40, 50),
    ("armado", "solo"): (30, 30, 40, 50),
    ("protendido", "laje"): (25, 30, 40, 50),
    ("protendido", "vigapilar"): (30, 35, 45, 55),
}
_ELEMENTO = {"laje": "laje", "viga": "vigapilar", "pilar": "vigapilar",
             "vigapilar": "vigapilar", "solo": "solo",
             "contatocomosolo": "solo", "pilarsolo": "pilarsolo"}


def cobrimento_nominal(caa: str, elemento: str, protendido: bool = False) -> int:
    """Cobrimento nominal da Tabela 7.2, em mm (Δc = 10 mm).

    caa: 'I', 'II', 'III' ou 'IV' (aceita 'CAA II', 'CAII', '2'...).
    elemento: 'laje', 'viga', 'pilar', 'solo' (elementos estruturais em
    contato com o solo) ou 'pilar solo' (trecho de pilar em contato com o
    solo junto à fundação: cnom >= 45 mm, nota d).
    protendido=True dá o cobrimento da bainha ou dos fios, cabos e cordoalhas
    (nota a); a armadura passiva segue a linha de concreto armado.

    A tabela não inclui as reduções permitidas: até 5 mm com concreto de
    classe acima da mínima exigida, e a da nota b (face superior revestida,
    >= 15 mm). Também não verifica cnom >= φ da barra, φn do feixe e
    0,5·φ da bainha (7.4.7.5).
    """
    chave = _chave(caa)
    for prefixo in ("caa", "ca"):   # 'CAA II', 'CAII' -> 'ii'
        if chave.startswith(prefixo):
            chave = chave[len(prefixo):]
            break
    if chave not in _CAA:
        raise ValueError(f"Classe de agressividade desconhecida: {caa!r}. Use I, II, III ou IV.")
    i = _CAA[chave]
    el = _ELEMENTO.get(_chave(elemento).replace("/", ""))
    if el is None:
        raise ValueError(f"Elemento desconhecido: {elemento!r}. Use laje, viga, pilar, solo ou 'pilar solo'.")
    tipo = "protendido" if protendido else "armado"
    if el == "pilarsolo":
        if protendido:
            raise ValueError("A nota d da Tabela 7.2 trata da armadura passiva de pilar em contato com o solo.")
        return max(_COBRIMENTO_TABELA_7_2[("armado", "solo")][i], 45)
    if (tipo, el) not in _COBRIMENTO_TABELA_7_2:
        raise ValueError("A Tabela 7.2 não dá cobrimento de concreto protendido em contato com o solo.")
    return _COBRIMENTO_TABELA_7_2[(tipo, el)][i]


# ---------------------------------------------------------------------------
# Resistência à tração — 8.2.5 (PDF p. 42-43)
# ---------------------------------------------------------------------------
def _fct_m(f_mpa: float) -> float:
    if f_mpa <= 50.0:
        return 0.3 * f_mpa ** (2.0 / 3.0)
    return 2.12 * math.log(1.0 + 0.1 * (f_mpa + 8.0))


def fct_m(fck_mpa: float) -> float:
    """Resistência média à tração direta, MPa (8.2.5).

    fck <= 50 MPa: fct,m = 0,3·fck^(2/3)
    fck  > 50 MPa: fct,m = 2,12·ln[1 + 0,1·(fck + 8)]
    """
    return _fct_m(validar_fck(fck_mpa))


def fct_m_idade(fckj_mpa: float) -> float:
    """fct,m para idade diferente de 28 dias, com fckj em lugar de fck (8.2.5).

    A norma admite as mesmas expressões para fckj >= 7 MPa.
    """
    f = float(fckj_mpa)
    if not (FCKJ_MIN <= f <= FCK_MAX):
        raise FaixaNormativaError(
            f"fckj = {f:g} MPa fora da faixa das expressões de 8.2.5 "
            f"({FCKJ_MIN:g} a {FCK_MAX:g} MPa)."
        )
    return _fct_m(f)


def fctk_inf(fck_mpa: float) -> float:
    """fctk,inf = 0,7·fct,m, MPa (8.2.5)."""
    return 0.7 * fct_m(fck_mpa)


def fctk_sup(fck_mpa: float) -> float:
    """fctk,sup = 1,3·fct,m, MPa (8.2.5)."""
    return 1.3 * fct_m(fck_mpa)


def fctd(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fctd = fctk,inf/γc, MPa (9.3.2.1, 19.4.1)."""
    return fctk_inf(fck_mpa) / gama_c


# ---------------------------------------------------------------------------
# Módulo de elasticidade — 8.2.8 (PDF p. 44)
# ---------------------------------------------------------------------------
ALPHA_E_AGREGADO = {
    "basalto": 1.2,
    "diabasio": 1.2,
    "granito": 1.0,
    "gnaisse": 1.0,
    "calcario": 0.9,
    "arenito": 0.7,
}


def alpha_E(agregado: str = "granito") -> float:
    """αE pelo tipo de agregado graúdo (8.2.8)."""
    chave = _chave(agregado)
    if chave not in ALPHA_E_AGREGADO:
        raise ValueError(
            f"Agregado desconhecido: {agregado!r}. "
            f"Use um destes: {', '.join(sorted(ALPHA_E_AGREGADO))}."
        )
    return ALPHA_E_AGREGADO[chave]


def Eci(fck_mpa: float, alpha_e: float = 1.0) -> float:
    """Módulo de elasticidade tangente inicial, MPa (8.2.8).

    fck <= 50 MPa: Eci = αE·5600·√fck
    fck  > 50 MPa: Eci = 21,5·10³·αE·(fck/10 + 1,25)^(1/3)
    """
    fck = validar_fck(fck_mpa)
    if fck <= 50.0:
        return alpha_e * 5600.0 * math.sqrt(fck)
    return 21.5e3 * alpha_e * (fck / 10.0 + 1.25) ** (1.0 / 3.0)


def alpha_i(fck_mpa: float) -> float:
    """αi = 0,8 + 0,2·fck/80 <= 1,0 (8.2.8)."""
    return min(0.8 + 0.2 * validar_fck(fck_mpa) / 80.0, 1.0)


def Ecs(fck_mpa: float, alpha_e: float = 1.0) -> float:
    """Módulo de deformação secante Ecs = αi·Eci, MPa (8.2.8)."""
    return alpha_i(fck_mpa) * Eci(fck_mpa, alpha_e)


def Eci_idade(fck_mpa: float, fckj_mpa: float, alpha_e: float = 1.0) -> float:
    """Eci(t) para idade entre 7 e 28 dias, MPa (8.2.8).

    Eci(t) = (fckj/fck)^0,5·Eci (fck <= 50) ou (fckj/fck)^0,3·Eci (fck > 50),
    com Eci calculado com o fck de 28 dias.
    """
    fck = validar_fck(fck_mpa)
    expoente = 0.5 if fck <= 50.0 else 0.3
    return (float(fckj_mpa) / fck) ** expoente * Eci(fck, alpha_e)


def Gc(fck_mpa: float, alpha_e: float = 1.0) -> float:
    """Módulo de elasticidade transversal Gc = Ecs/2,4, MPa (8.2.9)."""
    return Ecs(fck_mpa, alpha_e) / 2.4


# ---------------------------------------------------------------------------
# Resistência de cálculo e idade — 12.3.3 (PDF p. 90-91)
# ---------------------------------------------------------------------------
S_CIMENTO = {
    "cpi": 0.25,
    "cpii": 0.25,
    "cpiii": 0.38,
    "cpiv": 0.38,
    "cpv": 0.20,
    "cpvari": 0.20,
}


def s_cimento(cimento: str, fck_mpa: float | None = None) -> float:
    """Coeficiente s de β1 (12.3.3).

    0,38 para CP III e CP IV; 0,25 para CP I e CP II; 0,20 para CPV-ARI **e para
    todo concreto de classe C60 ou superior**, qualquer que seja o cimento.
    """
    if fck_mpa is not None and float(fck_mpa) >= 60.0:
        return 0.20
    chave = _chave(cimento)
    if chave not in S_CIMENTO:
        raise ValueError(
            f"Cimento desconhecido: {cimento!r}. Use CPI, CPII, CPIII, CPIV ou CPV-ARI."
        )
    return S_CIMENTO[chave]


def beta1(t_dias: float, cimento: str = "CPII", fck_mpa: float | None = None) -> float:
    """β1 = fckj/fck = exp{s·[1 − (28/t)^(1/2)]} (12.3.3)."""
    t = float(t_dias)
    if t <= 0.0:
        raise ValueError("A idade t deve ser positiva (dias).")
    return math.exp(s_cimento(cimento, fck_mpa) * (1.0 - math.sqrt(28.0 / t)))


def fckj(fck_mpa: float, t_dias: float, cimento: str = "CPII") -> float:
    """Resistência característica na idade t, MPa (12.3.3).

    Para t < 28 dias devolve β1·fck. Para t >= 28 dias devolve fck: a norma
    não credita o ganho de resistência depois dos 28 dias no cálculo.
    """
    fck = validar_fck(fck_mpa)
    if float(t_dias) >= 28.0:
        return fck
    return beta1(t_dias, cimento, fck) * fck


def fcd(fck_mpa: float, gama_c: float = GAMA_C, t_dias: float = 28.0,
        cimento: str = "CPII") -> float:
    """Resistência de cálculo à compressão, MPa (12.3.3).

    a) t >= 28 dias: fcd = fck/γc
    b) t  < 28 dias: fcd = fckj/γc ≅ β1·fck/γc
    """
    return fckj(fck_mpa, t_dias, cimento) / gama_c


# ---------------------------------------------------------------------------
# Diagrama tensão-deformação do concreto — 8.2.10.1, Figura 8.2 (PDF p. 45)
# ---------------------------------------------------------------------------
def eta_c(fck_mpa: float) -> float:
    """ηc = 1,0 para fck <= 40 MPa; (40/fck)^(1/3) para fck > 40 MPa."""
    fck = validar_fck(fck_mpa)
    return 1.0 if fck <= 40.0 else (40.0 / fck) ** (1.0 / 3.0)


def eps_c2(fck_mpa: float) -> float:
    """Deformação de início do patamar, ‰: 2,0 até C50; 2,0 + 0,085·(fck − 50)^0,53 acima."""
    fck = validar_fck(fck_mpa)
    return 2.0 if fck <= 50.0 else 2.0 + 0.085 * (fck - 50.0) ** 0.53


def eps_cu(fck_mpa: float) -> float:
    """Deformação de ruptura, ‰: 3,5 até C50; 2,6 + 35·[(90 − fck)/100]^4 acima."""
    fck = validar_fck(fck_mpa)
    return 3.5 if fck <= 50.0 else 2.6 + 35.0 * ((90.0 - fck) / 100.0) ** 4


def n_parabola(fck_mpa: float) -> float:
    """Expoente da parábola: 2 até C50; 1,4 + 23,4·[(90 − fck)/100]^4 acima."""
    fck = validar_fck(fck_mpa)
    return 2.0 if fck <= 50.0 else 1.4 + 23.4 * ((90.0 - fck) / 100.0) ** 4


def sigma_c_pico(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """Tensão de pico do diagrama idealizado, 0,85·ηc·fcd, MPa."""
    return 0.85 * eta_c(fck_mpa) * fcd(fck_mpa, gama_c)


def sigma_c(eps_c_pmil: float, fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """Tensão de compressão no diagrama parábola-retângulo, MPa (Figura 8.2).

    σc = 0,85·ηc·fcd·[1 − (1 − εc/εc2)^n] para 0 <= εc < εc2 e
    σc = 0,85·ηc·fcd para εc2 <= εc <= εcu. Deformação de compressão positiva;
    tração devolve zero (17.2.2 d). Além de εcu o diagrama não é definido pela
    norma; a função devolve o patamar, para uso numérico em solvers.
    """
    eps = float(eps_c_pmil)
    if eps <= 0.0:
        return 0.0
    pico = sigma_c_pico(fck_mpa, gama_c)
    e2 = eps_c2(fck_mpa)
    if eps < e2:
        return pico * (1.0 - (1.0 - eps / e2) ** n_parabola(fck_mpa))
    return pico


# ---------------------------------------------------------------------------
# Diagrama retangular simplificado — 17.2.2 e) (PDF p. 141)
# ---------------------------------------------------------------------------
def lambda_retangulo(fck_mpa: float) -> float:
    """λ (y = λ·x): 0,8 até C50; 0,8 − (fck − 50)/400 acima."""
    fck = validar_fck(fck_mpa)
    return 0.8 if fck <= 50.0 else 0.8 - (fck - 50.0) / 400.0


def alpha_c(fck_mpa: float) -> float:
    """αc: 0,85 até C50; 0,85·[1 − (fck − 50)/200] acima."""
    fck = validar_fck(fck_mpa)
    return 0.85 if fck <= 50.0 else 0.85 * (1.0 - (fck - 50.0) / 200.0)


def tensao_retangulo(fck_mpa: float, gama_c: float = GAMA_C,
                     largura_diminui: bool = False) -> float:
    """Tensão constante do retângulo, MPa: αc·ηc·fcd.

    Usa 0,9·αc·ηc·fcd quando a largura da seção, medida paralelamente à linha
    neutra, diminui a partir dela em direção à borda comprimida (seção
    circular, T invertido etc.).
    """
    fator = 0.9 if largura_diminui else 1.0
    return fator * alpha_c(fck_mpa) * eta_c(fck_mpa) * fcd(fck_mpa, gama_c)


# ---------------------------------------------------------------------------
# Domínios de deformação — Figura 17.1 (PDF p. 142)
# ---------------------------------------------------------------------------
def pivo_C_distancia_relativa(fck_mpa: float) -> float:
    """Posição do pivô C: (εcu − εc2)/εcu, fração de h a partir da borda mais comprimida.

    Vale 3/7 até C50 e diminui acima disso. Em C90 a própria norma dá
    εc2 = 2,6006 ‰ > εcu = 2,6 ‰; a distância é então tomada como zero.
    """
    ecu = eps_cu(fck_mpa)
    return max(0.0, (ecu - eps_c2(fck_mpa)) / ecu)


def x_lim_dominio_2_3(d: float, fck_mpa: float) -> float:
    """Profundidade da linha neutra no limite entre os domínios 2 e 3: εcu/(εcu + 10‰)·d."""
    ecu = eps_cu(fck_mpa)
    return ecu / (ecu + EPS_SU) * d


def x_lim_dominio_3_4(d: float, fck_mpa: float, fyk_mpa: float = 500.0,
                      gama_s: float = GAMA_S, Es_mpa: float = ES_MPA) -> float:
    """Profundidade da linha neutra no limite entre os domínios 3 e 4: εcu/(εcu + εyd)·d."""
    ecu = eps_cu(fck_mpa)
    return ecu / (ecu + eps_yd(fyk_mpa, gama_s, Es_mpa)) * d


def eps_compressao_uniforme(fck_mpa: float) -> float:
    """Encurtamento da compressão uniforme (reta b da Figura 17.1), ‰.

    É εc2; em C90 a norma dá εc2 = 2,6006 ‰ > εcu = 2,6 ‰, e adota-se o
    menor dos dois.
    """
    return min(eps_c2(fck_mpa), eps_cu(fck_mpa))


# ---------------------------------------------------------------------------
# Pilares — 11.3.3.4.3 (PDF p. 80), 15.3.1 (PDF p. 121), 17.3.5.3 (PDF p. 153)
# ---------------------------------------------------------------------------
GAMA_F3 = 1.1   # 15.3.1 — formulação de segurança da relação momento-curvatura


def M1d_min_kncm(Nd_kn: float, h_cm: float) -> float:
    """Momento mínimo de 1ª ordem, kN·cm (11.3.3.4.3).

    M1d,mín = Nd·(0,015 + 0,03·h), h em metros; com Nd em kN e h em cm,
    M1d,mín = Nd·(1,5 + 0,03·h). Substitui o efeito das imperfeições locais
    de pilar comprimido; com Nd <= 0 (tração) devolve 0.
    """
    return max(float(Nd_kn), 0.0) * (1.5 + 0.03 * float(h_cm))


def As_min_pilar_cm2(Nd_kn: float, Ac_cm2: float, fyk_mpa: float = 500.0,
                     gama_s: float = GAMA_S) -> float:
    """Armadura longitudinal mínima de pilar, cm²: 0,15·Nd/fyd >= 0,004·Ac (17.3.5.3.1)."""
    fyd_kncm2 = mpa_para_kncm2(fyd(fyk_mpa, gama_s))
    return max(0.15 * max(float(Nd_kn), 0.0) / fyd_kncm2, 0.004 * Ac_cm2)


def As_max_pilar_cm2(Ac_cm2: float) -> float:
    """Armadura longitudinal máxima de pilar, cm²: 0,08·Ac (17.3.5.3.2).

    Vale inclusive na região de emenda, contando a sobreposição das barras.
    """
    return 0.08 * Ac_cm2


# ---------------------------------------------------------------------------
# Dutilidade — 14.6.4.3 (PDF p. 112)
# ---------------------------------------------------------------------------
def xd_limite_dutilidade(fck_mpa: float) -> float:
    """Limite de x/d para comportamento dútil de vigas e lajes: 0,45 até C50; 0,35 acima."""
    return 0.45 if validar_fck(fck_mpa) <= 50.0 else 0.35


# ---------------------------------------------------------------------------
# Armadura mínima de flexão — 17.3.5.2.1 e Tabela 17.3 (PDF p. 151)
# ---------------------------------------------------------------------------
RHO_MIN_TABELA_17_3 = {   # ρmín = As,mín/Ac, em %
    20: 0.150, 25: 0.150, 30: 0.150, 35: 0.164, 40: 0.179, 45: 0.194,
    50: 0.208, 55: 0.211, 60: 0.219, 65: 0.226, 70: 0.233, 75: 0.239,
    80: 0.245, 85: 0.251, 90: 0.256,
}


def rho_min_flexao(fck_mpa: float) -> float:
    """ρmín da Tabela 17.3 como fração (ex.: 0,0015), interpolado entre as classes.

    A tabela pressupõe aço CA-50, d/h = 0,8, γc = 1,4 e γs = 1,15; com outros
    valores, use ``As_min_flexao_retangular``, que aplica a definição da norma.
    """
    fck = validar_fck(fck_mpa)
    classes = sorted(RHO_MIN_TABELA_17_3)
    for f0, f1 in zip(classes, classes[1:]):
        if f0 <= fck <= f1:
            r0, r1 = RHO_MIN_TABELA_17_3[f0], RHO_MIN_TABELA_17_3[f1]
            return (r0 + (r1 - r0) * (fck - f0) / (f1 - f0)) / 100.0
    raise FaixaNormativaError(f"fck = {fck:g} MPa fora da Tabela 17.3.")  # inalcançável


def As_min_flexao_retangular(bw_cm: float, h_cm: float, d_cm: float,
                             fck_mpa: float, fyk_mpa: float = 500.0,
                             gama_c: float = GAMA_C, gama_s: float = GAMA_S) -> float:
    """As,mín de seção retangular pela definição de 17.3.5.2.1, em cm².

    Dimensiona a seção para Md,mín = 0,8·W0·fctk,sup (W0 = bw·h²/6) com o
    diagrama retangular e respeita a taxa mínima absoluta de 0,15 %·bw·h.
    Com CA-50, d/h = 0,8, γc = 1,4 e γs = 1,15, reproduz a Tabela 17.3 com
    diferença de até 1,6 %: de C55 a C90 a tabela foi calculada com o fct,m de
    2014 (2,12·ln(1 + 0,11·fck)) e não foi refeita quando a fórmula mudou em
    2023. As duas vias são normativas (a tabela é a alternativa de 17.3.5.2.1).
    """
    W0 = bw_cm * h_cm ** 2 / 6.0
    Md_min = 0.8 * W0 * mpa_para_kncm2(fctk_sup(fck_mpa))          # kN·cm
    sigma = mpa_para_kncm2(tensao_retangulo(fck_mpa, gama_c))       # kN/cm²
    disc = d_cm ** 2 - 2.0 * Md_min / (sigma * bw_cm)
    if disc < 0.0:
        raise ValueError("Seção insuficiente para o momento mínimo (discriminante negativo).")
    y = d_cm - math.sqrt(disc)
    As = Md_min / (mpa_para_kncm2(fyd(fyk_mpa, gama_s)) * (d_cm - 0.5 * y))
    return max(As, 0.0015 * bw_cm * h_cm)


# ---------------------------------------------------------------------------
# Aço de armadura passiva — 8.3 (PDF p. 47-49)
# ---------------------------------------------------------------------------
FYK_CATEGORIA = {"ca25": 250.0, "ca50": 500.0, "ca60": 600.0}


def fyk_categoria(categoria: str) -> float:
    """fyk pela categoria (CA-25, CA-50, CA-60), MPa."""
    chave = _chave(categoria)
    if chave not in FYK_CATEGORIA:
        raise ValueError(f"Categoria de aço desconhecida: {categoria!r}. Use CA-25, CA-50 ou CA-60.")
    return FYK_CATEGORIA[chave]


def fyd(fyk_mpa: float = 500.0, gama_s: float = GAMA_S) -> float:
    """fyd = fyk/γs, MPa."""
    return fyk_mpa / gama_s


def eps_yd(fyk_mpa: float = 500.0, gama_s: float = GAMA_S, Es_mpa: float = ES_MPA) -> float:
    """Deformação de escoamento de cálculo, ‰."""
    return fyd(fyk_mpa, gama_s) / Es_mpa * 1000.0


def sigma_s(eps_s_pmil: float, fyk_mpa: float = 500.0, gama_s: float = GAMA_S,
            Es_mpa: float = ES_MPA) -> float:
    """Tensão no aço pelo diagrama bilinear da Figura 8.5, MPa (sinal de εs)."""
    s = Es_mpa * float(eps_s_pmil) / 1000.0
    lim = fyd(fyk_mpa, gama_s)
    return max(-lim, min(lim, s))


# ---------------------------------------------------------------------------
# Aderência — Tabela 8.2 (PDF p. 48) e 9.3.2 (PDF p. 54)
# ---------------------------------------------------------------------------
ETA1_CATEGORIA = {"ca25": 1.00, "ca50": 2.25, "ca60": 1.00}


def eta1(categoria: str = "CA-50") -> float:
    """η1 pela categoria do aço (Tabela 8.2): CA-25 1,00; CA-50 2,25; CA-60 1,00."""
    chave = _chave(categoria)
    if chave not in ETA1_CATEGORIA:
        raise ValueError(f"Categoria de aço desconhecida: {categoria!r}. Use CA-25, CA-50 ou CA-60.")
    return ETA1_CATEGORIA[chave]


def eta2(boa_aderencia: bool = True) -> float:
    """η2 = 1,0 em boa aderência; 0,7 em má aderência (9.3.2.1)."""
    return 1.0 if boa_aderencia else 0.7


def eta3(phi_mm: float) -> float:
    """η3 = 1,0 para φ < 32 mm; (132 − φ)/100 para φ >= 32 mm (9.3.2.1)."""
    return 1.0 if phi_mm < 32.0 else (132.0 - phi_mm) / 100.0


def fbd(fck_mpa: float, categoria: str = "CA-50", boa_aderencia: bool = True,
        phi_mm: float = 10.0, gama_c: float = GAMA_C) -> float:
    """Resistência de aderência de cálculo da armadura passiva, MPa (9.3.2.1)."""
    return eta1(categoria) * eta2(boa_aderencia) * eta3(phi_mm) * fctd(fck_mpa, gama_c)


ETA_P1 = {"fioliso": 1.0, "cordoalha": 1.2, "fiodentado": 1.4}


def eta_p1(tipo: str) -> float:
    """ηp1 (9.3.2.2): fio liso 1,0; cordoalha de 3 ou 7 fios 1,2; fio dentado 1,4."""
    chave = _chave(tipo)
    if chave not in ETA_P1:
        raise ValueError(f"Tipo de armadura ativa desconhecido: {tipo!r}. "
                         "Use 'fio liso', 'cordoalha' ou 'fio dentado'.")
    return ETA_P1[chave]


def fbpd(f_mpa: float, tipo: str = "cordoalha", boa_aderencia: bool = True,
         gama_c: float = GAMA_C) -> float:
    """Resistência de aderência da armadura ativa pré-tracionada, MPa (9.3.2.2).

    ``f_mpa`` é o fckj na idade de aplicação da protensão (comprimento de
    transferência) ou o fck aos 28 dias (comprimento de ancoragem).
    """
    fctd_j = 0.7 * fct_m_idade(f_mpa) / gama_c
    return eta_p1(tipo) * eta2(boa_aderencia) * fctd_j


# ---------------------------------------------------------------------------
# Redução da resistência das bielas — 17.4.2.2, 17.5.1.5, 19.5.3.1, 22.3.2
# ---------------------------------------------------------------------------
def alpha_v2(fck_mpa: float) -> float:
    """αv2 = 1 − fck/250, fck em MPa.

    Mesma expressão em VRd2 da força cortante (17.4.2.2 e 17.4.2.3), TRd2 da
    torção (17.5.1.5), τRd2 da punção (19.5.3.1, onde se chama αv) e fcd1,
    fcd2 e fcd3 de bielas e regiões nodais (22.3.2).
    """
    return 1.0 - validar_fck(fck_mpa) / 250.0


# ---------------------------------------------------------------------------
# Força cortante em lajes — 19.4.1 (PDF p. 181)
# ---------------------------------------------------------------------------
FCK_TETO_TAU_RD = 60.0


def tau_Rd(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """τRd = 0,25·fctd, MPa, com fck limitado a 60 MPa (19.4.1)."""
    fck = validar_fck(fck_mpa)
    return 0.25 * fctd(min(fck, FCK_TETO_TAU_RD), gama_c)


# === P6: fluência e retração (Tabela 8.1, promovida de protendido_nbr6118) ===
# ---------------------------------------------------------------------------
# Tabela 8.1 — valores característicos superiores de εcs(t∞,t0) e φ(t∞,t0)
# (8.2.11, PDF p. 47). O procedimento completo do Anexo A mora em
# tempo_concreto_nbr6118.py.
# ---------------------------------------------------------------------------
# φ(t∞,t0) depende da classe do concreto (bloco "C20-C45" × "C50-C90");
# εcs(t∞,t0), em ‰, é comum às duas classes. Cada par de valores é
# (2Ac/u = 20 cm, 2Ac/u = 60 cm). Eixos: t0 em dias (5, 30, 60) e umidade
# média ambiente em % (40, 55, 75, 90).
TABELA_8_1_PHI = {
    "C20-C45": {
        5.0:  {40.0: (4.6, 3.8), 55.0: (3.9, 3.3), 75.0: (2.8, 2.4), 90.0: (2.0, 1.9)},
        30.0: {40.0: (3.4, 3.0), 55.0: (2.9, 2.6), 75.0: (2.2, 2.0), 90.0: (1.6, 1.5)},
        60.0: {40.0: (2.9, 2.7), 55.0: (2.5, 2.3), 75.0: (1.9, 1.8), 90.0: (1.4, 1.4)},
    },
    "C50-C90": {
        5.0:  {40.0: (2.7, 2.4), 55.0: (2.4, 2.1), 75.0: (1.9, 1.8), 90.0: (1.6, 1.5)},
        30.0: {40.0: (2.0, 1.8), 55.0: (1.7, 1.6), 75.0: (1.4, 1.3), 90.0: (1.1, 1.1)},
        60.0: {40.0: (1.7, 1.6), 55.0: (1.5, 1.4), 75.0: (1.2, 1.2), 90.0: (1.0, 1.0)},
    },
}
TABELA_8_1_EPS_CS = {
    5.0:  {40.0: (-0.53, -0.47), 55.0: (-0.48, -0.43), 75.0: (-0.36, -0.32), 90.0: (-0.18, -0.15)},
    30.0: {40.0: (-0.44, -0.45), 55.0: (-0.41, -0.41), 75.0: (-0.33, -0.31), 90.0: (-0.17, -0.15)},
    60.0: {40.0: (-0.39, -0.43), 55.0: (-0.36, -0.40), 75.0: (-0.30, -0.31), 90.0: (-0.17, -0.15)},
}
_T0_TAB_8_1 = (5.0, 30.0, 60.0)
_UMIDADE_TAB_8_1 = (40.0, 55.0, 75.0, 90.0)
_HFIC_TAB_8_1 = (20.0, 60.0)


def _bloco_classe_tabela_8_1(fck_mpa: float) -> str:
    """Bloco de classe da Tabela 8.1 e do Anexo A: 'C20-C45' ou 'C50-C90'.

    A norma não tem classe padrão entre C45 e C50; fck nesse vão (46 a
    49 MPa) é tratado como 'C50-C90' (bloco mais próximo por cima).
    """
    return "C20-C45" if float(fck_mpa) <= 45.0 else "C50-C90"


def _interp_1d_tabela_8_1(x: float, pontos: tuple, valores: dict) -> float:
    """Interpolação linear de uma variável entre pontos consecutivos da
    Tabela 8.1; x fora de [pontos[0], pontos[-1]] levanta FaixaNormativaError."""
    if x < pontos[0] or x > pontos[-1]:
        raise FaixaNormativaError(
            f"Valor {x:g} fora da faixa da Tabela 8.1 "
            f"({pontos[0]:g} a {pontos[-1]:g})."
        )
    for p0, p1 in zip(pontos, pontos[1:]):
        if p0 <= x <= p1:
            v0, v1 = valores[p0], valores[p1]
            return v0 + (v1 - v0) * (x - p0) / (p1 - p0)
    raise AssertionError("Faixa inalcançável.")  # pragma: no cover


def _interp_tabela_8_1(tabela: dict, umidade_pct: float, h_fic_cm: float,
                       to_dias: float) -> float:
    """Interpolação linear em t0, umidade e espessura fictícia (8.2.11:
    “podem ser obtidos, por interpolação linear, a partir da Tabela 8.1”)."""
    if to_dias < _T0_TAB_8_1[0] or to_dias > _T0_TAB_8_1[-1]:
        raise FaixaNormativaError(
            f"t0 = {to_dias:g} dias fora da faixa da Tabela 8.1 "
            f"({_T0_TAB_8_1[0]:g} a {_T0_TAB_8_1[-1]:g} dias)."
        )

    def valor_no_t0(t0: float) -> float:
        por_umidade = {
            u: _interp_1d_tabela_8_1(h_fic_cm, _HFIC_TAB_8_1,
                                     {20.0: par[0], 60.0: par[1]})
            for u, par in tabela[t0].items()
        }
        return _interp_1d_tabela_8_1(umidade_pct, _UMIDADE_TAB_8_1, por_umidade)

    valores_por_t0 = {t0: valor_no_t0(t0) for t0 in _T0_TAB_8_1}
    return _interp_1d_tabela_8_1(to_dias, _T0_TAB_8_1, valores_por_t0)


def phi_eps_cs_NBR(umidade_pct: float, h_fic_cm: float,
                   to_dias: float = 30.0, fck_mpa: float = 30.0) -> tuple[float, float]:
    """φ(t∞,t0) e εcs(t∞,t0) pela Tabela 8.1 (8.2.11, PDF p. 47).

    Interpolação linear em t0, na umidade e na espessura fictícia
    h_fic = 2·Ac/u (sem a ponderação γ do Anexo A), como o 8.2.11 permite.
    t0 é a idade **real** do concreto no carregamento (não a idade fictícia
    do Anexo A). φ depende da classe do concreto (bloco escolhido por
    fck_mpa: C20-C45 ou C50-C90); εcs é comum às duas classes.

    Faixa: t0 de 5 a 60 dias, umidade de 40 % a 90 %, h_fic de 20 cm a
    60 cm; fora dela levanta FaixaNormativaError (subclasse de ValueError).

    Retorna (φ(t∞,t0), εcs(t∞,t0) em ‰).
    """
    bloco = _bloco_classe_tabela_8_1(fck_mpa)
    phi = _interp_tabela_8_1(TABELA_8_1_PHI[bloco], umidade_pct, h_fic_cm, to_dias)
    eps = _interp_tabela_8_1(TABELA_8_1_EPS_CS, umidade_pct, h_fic_cm, to_dias)
    return phi, eps
