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
from dataclasses import dataclass

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
_ROMANOS_CAA = ("I", "II", "III", "IV")
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


def _cnom_tabela_bruta(caa: str, elemento: str, protendido: bool = False) -> float:
    """cnom tal como impresso na Tabela 7.2 (Δc = 10 mm já embutido), em mm."""
    i = _ROMANOS_CAA.index(normalizar_caa(caa))
    el = _ELEMENTO.get(_chave(elemento).replace("/", ""))
    if el is None:
        raise ValueError(f"Elemento desconhecido: {elemento!r}. Use laje, viga, pilar, solo ou 'pilar solo'.")
    tipo = "protendido" if protendido else "armado"
    if el == "pilarsolo":
        if protendido:
            raise ValueError("A nota d da Tabela 7.2 trata da armadura passiva de pilar em contato com o solo.")
        return float(max(_COBRIMENTO_TABELA_7_2[("armado", "solo")][i], 45))
    if (tipo, el) not in _COBRIMENTO_TABELA_7_2:
        raise ValueError("A Tabela 7.2 não dá cobrimento de concreto protendido em contato com o solo.")
    return float(_COBRIMENTO_TABELA_7_2[(tipo, el)][i])


def cobrimento_nominal(caa: str, elemento: str, protendido: bool = False,
                       delta_c_mm: float = 10.0,
                       reducao_classe_superior: bool = False,
                       face_revestida: bool = False,
                       superficie_exposta_agressiva: bool = False) -> float:
    """Cobrimento nominal cnom = cmín + Δc, em mm (7.4.7.1-7.4.7.4, Tabela 7.2).

    caa: 'I', 'II', 'III' ou 'IV' (aceita 'CAA II', 'CAII', '2'...; ver
    normalizar_caa).
    elemento: 'laje', 'viga', 'pilar', 'solo' (elementos estruturais em
    contato com o solo) ou 'pilar solo' (trecho de pilar em contato com o
    solo junto à fundação: cnom >= 45 mm, nota d).
    protendido=True dá o cobrimento da bainha ou dos fios, cabos e cordoalhas
    (nota a); a armadura passiva segue a linha de concreto armado.

    delta_c_mm: tolerância de execução, Δc >= 10 mm em obras correntes
    (7.4.7.3); Δc = 5 mm é admitido em estruturas pré-moldadas com controle
    rigoroso de qualidade, conforme a ABNT NBR 9062 (7.4.7.4).
    reducao_classe_superior: True desconta 5 mm quando o concreto empregado
    é de classe de resistência superior à mínima exigida pela Tabela 7.1
    (nota logo após a Tabela 7.2, p. 39).
    face_revestida: True usa a nota b da Tabela 7.2 (face superior de laje
    ou viga que será revestida com argamassa de contrapiso, piso cerâmico
    etc.): as exigências desta tabela são substituídas pelas de 7.4.7.5,
    respeitado cnom >= 15 mm (confira phi/feixe/bainha com
    verificar_cobrimento, em durabilidade_nbr6118). Só vale para
    elemento='laje' ou 'viga' em concreto armado.
    superficie_exposta_agressiva: True força os cobrimentos da CAA IV (nota
    c da Tabela 7.2: reservatórios, estações de tratamento de água e
    esgoto, condutos de esgoto, canaletas de efluentes e outras obras em
    ambiente químico e intensamente agressivo), qualquer que seja a CAA
    informada.

    Não verifica cnom >= φ da barra, φn do feixe e 0,5·φ da bainha
    (7.4.7.5): use durabilidade_nbr6118.verificar_cobrimento para isso.
    """
    if face_revestida:
        if protendido:
            raise ValueError("A nota b da Tabela 7.2 vale só para concreto armado (laje/viga).")
        el_chave = _chave(elemento).replace("/", "")
        if el_chave not in ("laje", "viga"):
            raise ValueError(
                "A nota b da Tabela 7.2 (face revestida) vale só para 'laje' e 'viga', "
                f"não para {elemento!r}."
            )
        return 15.0
    cmin = cobrimento_minimo_mm(caa, elemento, protendido, reducao_classe_superior,
                                superficie_exposta_agressiva)
    return cmin + delta_c_mm


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


# ---------------------------------------------------------------------------
# === P2: Propriedades complementares dos materiais ===
# ---------------------------------------------------------------------------
# Massa específica do concreto — 8.2.2 (PDF p. 42)
MASSA_ESPECIFICA_CONCRETO_MIN_KG_M3 = 2000.0   # 8.2.2 — faixa do concreto de massa específica normal
MASSA_ESPECIFICA_CONCRETO_MAX_KG_M3 = 2800.0
MASSA_ESPECIFICA_CONCRETO_SIMPLES_KG_M3 = 2400.0   # 8.2.2 — na falta de valor real, concreto simples
MASSA_ESPECIFICA_CONCRETO_ARMADO_KG_M3 = 2500.0    # 8.2.2 — na falta de valor real, concreto armado
MASSA_ESPECIFICA_CONCRETO_ACRESCIMO_MIN_KG_M3 = 100.0   # 8.2.2 — acréscimo sobre o simples real conhecido
MASSA_ESPECIFICA_CONCRETO_ACRESCIMO_MAX_KG_M3 = 150.0


def massa_especifica_concreto_armado_kg_m3(rho_simples_kg_m3: float,
                                           acrescimo_kg_m3: float = 125.0) -> float:
    """Massa específica do concreto armado a partir da do concreto simples conhecida, kg/m³ (8.2.2).

    ρ_armado = ρ_simples + acréscimo, com o acréscimo entre 100 kg/m³ e
    150 kg/m³ (o padrão usado aqui, 125 kg/m³, é o meio da faixa; a norma não
    dá um valor único). Fora dessa faixa levanta ``FaixaNormativaError``. Na
    falta de ρ_simples real, use direto as constantes
    ``MASSA_ESPECIFICA_CONCRETO_SIMPLES_KG_M3`` (2400) e
    ``MASSA_ESPECIFICA_CONCRETO_ARMADO_KG_M3`` (2500).
    """
    if not (MASSA_ESPECIFICA_CONCRETO_ACRESCIMO_MIN_KG_M3 <= acrescimo_kg_m3
            <= MASSA_ESPECIFICA_CONCRETO_ACRESCIMO_MAX_KG_M3):
        raise FaixaNormativaError(
            f"Acréscimo de {acrescimo_kg_m3:g} kg/m³ fora da faixa de 8.2.2 "
            f"({MASSA_ESPECIFICA_CONCRETO_ACRESCIMO_MIN_KG_M3:g} a "
            f"{MASSA_ESPECIFICA_CONCRETO_ACRESCIMO_MAX_KG_M3:g} kg/m³)."
        )
    return float(rho_simples_kg_m3) + float(acrescimo_kg_m3)


# ---------------------------------------------------------------------------
# Dilatação térmica e Poisson do concreto — 8.2.3, 8.2.9, 14.7.3 (PDF p. 42, 45, 116)
# ---------------------------------------------------------------------------
ALFA_TERMICO_CONCRETO = 1.0e-5   # 1/°C (8.2.3)
POISSON_CONCRETO = 0.2           # 8.2.9 (tensão de compressão < 0,5·fc e de tração < fct) e 14.7.3 (placas)


# ---------------------------------------------------------------------------
# fct de ensaios indiretos — 8.2.5 (PDF p. 42)
# ---------------------------------------------------------------------------
def fct_de_ensaio(fct_sp_mpa: float | None = None, fct_f_mpa: float | None = None) -> float:
    """fct direta a partir de ensaio indireto, MPa (8.2.5).

    fct = 0,9·fct,sp (tração indireta, ABNT NBR 7222) ou fct = 0,7·fct,f
    (tração na flexão, ABNT NBR 12142). Informe exatamente um dos dois.
    """
    if (fct_sp_mpa is None) == (fct_f_mpa is None):
        raise ValueError("Informe exatamente um dos dois: fct_sp_mpa ou fct_f_mpa.")
    if fct_sp_mpa is not None:
        return 0.9 * float(fct_sp_mpa)
    return 0.7 * float(fct_f_mpa)


# ---------------------------------------------------------------------------
# Resistência no estado multiaxial de tensões — 8.2.6, Figura 8.1 (PDF p. 43)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoTensaoMultiaxial:
    sigma1_mpa: float
    sigma2_mpa: float
    sigma3_mpa: float
    fck_mpa: float
    fctk_mpa: float
    sigma3_lim_mpa: float
    ok_tracao: bool
    ok_compressao: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_tensao_multiaxial(sigma1_mpa: float, sigma2_mpa: float, sigma3_mpa: float,
                                fck_mpa: float) -> ResultadoTensaoMultiaxial:
    """Verifica as tensões principais no estado multiaxial, MPa (8.2.6, Figura 8.1).

    Com as tensões principais ordenadas σ3 >= σ2 >= σ1 (compressão positiva,
    tração negativa):
        σ1 >= −fctk
        σ3 <= fck + 4·σ1
    fctk é tomado como fctk,inf (8.2.5): a norma não diz qual dos dois usar
    aqui, e fctk,inf é o valor a favor da segurança, como em fctd = fctk,inf/γc.
    """
    s1, s2, s3 = float(sigma1_mpa), float(sigma2_mpa), float(sigma3_mpa)
    if not (s3 >= s2 - 1e-9 and s2 >= s1 - 1e-9):
        raise ValueError(
            "As tensões principais devem vir ordenadas σ3 >= σ2 >= σ1 "
            f"(recebido σ1={s1:g}, σ2={s2:g}, σ3={s3:g})."
        )
    fck = validar_fck(fck_mpa)
    fctk = fctk_inf(fck)
    ok_tracao = s1 >= -fctk - 1e-9
    sigma3_lim = fck + 4.0 * s1
    ok_compressao = s3 <= sigma3_lim + 1e-9
    ok = ok_tracao and ok_compressao
    if not ok_tracao:
        governante = "σ1 < −fctk,inf (8.2.6)"
    elif not ok_compressao:
        governante = "σ3 > fck + 4·σ1 (8.2.6)"
    else:
        governante = "dentro dos limites de 8.2.6"
    memoria = (
        f"8.2.6: σ1={s1:g} MPa, σ2={s2:g} MPa, σ3={s3:g} MPa, "
        f"fck={fck:g} MPa, fctk,inf={fctk:.4g} MPa.",
        f"σ1 >= −fctk,inf: {s1:g} >= {-fctk:.4g} -> {'ok' if ok_tracao else 'não ok'}.",
        f"σ3 <= fck + 4·σ1: {s3:g} <= {sigma3_lim:.4g} -> {'ok' if ok_compressao else 'não ok'}.",
    )
    return ResultadoTensaoMultiaxial(
        sigma1_mpa=s1, sigma2_mpa=s2, sigma3_mpa=s3, fck_mpa=fck, fctk_mpa=fctk,
        sigma3_lim_mpa=sigma3_lim, ok_tracao=ok_tracao, ok_compressao=ok_compressao,
        ok=ok, governante=governante, memoria=memoria,
    )


# ---------------------------------------------------------------------------
# Diagrama tensão-deformação para análise não linear — 8.2.10.1, Figura 8.3 (PDF p. 46)
# ---------------------------------------------------------------------------
def _eps_c1_pmil_fig_8_3(fcm_mpa: float) -> float:
    """εc1 = 0,7·fcm^0,31 <= 2,8 ‰ (Figura 8.3)."""
    return min(0.7 * float(fcm_mpa) ** 0.31, 2.8)


def _eps_cu1_pmil_fig_8_3(fcm_mpa: float) -> float:
    """εcu1 da Figura 8.3: εcu (8.2.10.1) se fck <= 50 MPa; fórmula própria acima disso.

    fck é obtido de volta de fcm = fck + 8 (a relação que a própria Figura 8.3
    manda usar).
    """
    fcm = float(fcm_mpa)
    fck = fcm - 8.0
    if fck <= 50.0:
        return eps_cu(fck)
    return 2.8 + 27.0 * ((98.0 - fcm) / 100.0) ** 4


def sigma_c_nao_linear(eps_c_pmil: float, fcm_mpa: float, Eci_mpa: float) -> float:
    """Tensão do diagrama para análise não linear de curta duração, MPa (8.2.10.1, Figura 8.3).

    σc/fcm = (k·η − η²)/[1 + (k−2)·η], com
    k = 1,05·Ecm·|εc1|/fcm (εc1 em ‰, convertido para adimensional),
    η = εc/εc1, εc1 = 0,7·fcm^0,31 <= 2,8 ‰.
    A norma chama o módulo de ``Ecm`` só nesta figura; em nenhum outro lugar
    da 6118:2026 há um Ecm distinto de Eci (8.2.8), então ``Eci_mpa`` aqui é
    o Eci de 8.2.8. fcm = fck + 8 (MPa) é calculado pelo chamador e passado
    pronto, porque esta função não recebe fck.
    Deformação de compressão positiva; tração devolve 0 (mesma convenção do
    diagrama parábola-retângulo). Além de εcu1 levanta ``FaixaNormativaError``.
    O diagrama é contínuo em εc1 (onde vale exatamente fcm, o pico) porque em
    η=1 a expressão (k−1)/(k−1) vale 1 para qualquer k.
    """
    fcm = float(fcm_mpa)
    eps = float(eps_c_pmil)
    if eps <= 0.0:
        return 0.0
    eps_c1 = _eps_c1_pmil_fig_8_3(fcm)
    eps_cu1 = _eps_cu1_pmil_fig_8_3(fcm)
    if eps > eps_cu1 + 1e-9:
        raise FaixaNormativaError(
            f"εc = {eps:g} ‰ além de εcu1 = {eps_cu1:.4g} ‰ (Figura 8.3)."
        )
    k = 1.05 * float(Eci_mpa) * (eps_c1 / 1000.0) / fcm
    eta = eps / eps_c1
    return fcm * (k * eta - eta ** 2) / (1.0 + (k - 2.0) * eta)


# ---------------------------------------------------------------------------
# Diagrama bilinear de tração — 8.2.10.2, Figura 8.4 (PDF p. 46)
# ---------------------------------------------------------------------------
EPS_CT_MAX_FIG_8_4 = 0.15   # ‰ — ponto final do diagrama, onde σct = fctk


def sigma_ct(eps_ct_pmil: float, fck_mpa: float) -> float:
    """Tensão do diagrama bilinear de tração do concreto não fissurado, MPa (8.2.10.2, Figura 8.4).

    Para σct <= 0,9·fctk: reta elástica σct = Eci·εct (εct em ‰, /1000 para
    adimensionalizar). Daí até o ponto final (0,15 ‰; fctk): segunda reta.
    fctk é tomado como fctk,inf (8.2.5), pela mesma razão de 8.2.6: a norma
    não diz qual dos dois usar, e fctk,inf é o valor a favor da segurança.
    Eci é o de 8.2.8 com o agregado padrão (αE = 1,0); para outro agregado,
    informe o Eci correto e monte a reta na mão com os dois pontos aqui
    descritos. εct em ‰, tração positiva; fora de [0; 0,15 ‰] levanta
    ``FaixaNormativaError``.
    """
    eps = float(eps_ct_pmil)
    if not (0.0 <= eps <= EPS_CT_MAX_FIG_8_4 + 1e-9):
        raise FaixaNormativaError(
            f"εct = {eps:g} ‰ fora da faixa da Figura 8.4 (0 a {EPS_CT_MAX_FIG_8_4:g} ‰)."
        )
    fck = validar_fck(fck_mpa)
    fctk = fctk_inf(fck)
    eci = Eci(fck)
    sigma_transicao = 0.9 * fctk
    eps_transicao = sigma_transicao / eci * 1000.0
    if eps <= eps_transicao:
        return eci * eps / 1000.0
    return sigma_transicao + (fctk - sigma_transicao) * (eps - eps_transicao) / (EPS_CT_MAX_FIG_8_4 - eps_transicao)


# ---------------------------------------------------------------------------
# Aço passivo e ativo — massa específica, dilatação térmica e dutilidade
# 8.3.3, 8.3.4, 8.3.7, 8.4.2, 8.4.3 (PDF p. 48-50)
# ---------------------------------------------------------------------------
MASSA_ESPECIFICA_ACO_KG_M3 = 7850.0   # 8.3.3 (passivo) e 8.4.2 (ativo)

ALFA_TERMICO_ACO = 1.0e-5   # 1/°C (8.3.4 passivo, 8.4.3 ativo)
_FAIXA_TEMPERATURA_ALFA_ACO = {   # (temperatura mínima, máxima), °C
    "passivo": (-20.0, 150.0),
    "ativo": (-20.0, 100.0),
}


def alfa_termico_aco(tipo: str = "passivo", temperatura_c: float | None = None) -> float:
    """Coeficiente de dilatação térmica do aço, 1/°C (8.3.4 passivo; 8.4.3 ativo).

    Vale 1·10⁻⁵/°C entre −20 °C e 150 °C para armadura passiva e entre
    −20 °C e 100 °C para armadura ativa. ``temperatura_c`` é opcional; quando
    informada e fora da faixa do tipo, levanta ``FaixaNormativaError``.
    """
    chave = _chave(tipo)
    if chave not in _FAIXA_TEMPERATURA_ALFA_ACO:
        raise ValueError(f"Tipo de armadura desconhecido: {tipo!r}. Use 'passivo' ou 'ativo'.")
    if temperatura_c is not None:
        tmin, tmax = _FAIXA_TEMPERATURA_ALFA_ACO[chave]
        t = float(temperatura_c)
        if not (tmin <= t <= tmax):
            raise FaixaNormativaError(
                f"Temperatura de {t:g} °C fora da faixa de validade do coeficiente de "
                f"dilatação térmica do aço {tipo} ({tmin:g} a {tmax:g} °C)."
            )
    return ALFA_TERMICO_ACO


DUTILIDADE_ACO_CATEGORIA = {"ca25": "alta", "ca50": "alta", "ca60": "normal"}


def dutilidade_aco_passivo(categoria: str) -> str:
    """Classifica a dutilidade do aço passivo pela categoria, 'alta' ou 'normal' (8.3.7).

    CA-25 e CA-50 são considerados de alta dutilidade, e CA-60 de dutilidade
    normal, desde que atendam aos mínimos de fst/fy e εuk da ABNT NBR 7480
    (dados do lote do fabricante, fora do escopo desta função e desta
    biblioteca: aqui a classificação é só pela categoria declarada).
    """
    chave = _chave(categoria)
    if chave not in DUTILIDADE_ACO_CATEGORIA:
        raise ValueError(f"Categoria de aço desconhecida: {categoria!r}. Use CA-25, CA-50 ou CA-60.")
    return DUTILIDADE_ACO_CATEGORIA[chave]


# ---------------------------------------------------------------------------
# === P1: Durabilidade, cobrimento e abertura de fissura admissível ===
# ---------------------------------------------------------------------------
class AvisoNBR6118(UserWarning):
    """Aviso de uso fora do que a NBR 6118:2026 prevê (o cálculo prossegue).

    Antes vivia em dimensionamento/rotinas/flexao_composta_obliqua.py, que
    agora reexporta este mesmo tipo (P1: precisava dele fora do kernel).
    """



# --- Normalização única de CAA — Tabela 6.1 (PDF p. 36) ---------------------
def normalizar_caa(caa: str) -> str:
    """Normaliza a Classe de Agressividade Ambiental para 'I', 'II', 'III' ou 'IV'.

    Aceita as variantes usuais de entrada: 'I', 'CAA II', 'CAIII', 'CA IV',
    '4'... É a normalização única de CAA da biblioteca (decisão do P1),
    usada por cobrimento_nominal, cobrimento_minimo_mm, wk_max_mm e por
    durabilidade_nbr6118 (relacao_ac_maxima, classe_concreto_minima).
    """
    chave = _chave(caa)
    for prefixo in ("caa", "ca"):   # 'CAA II', 'CAII' -> 'ii'
        if chave.startswith(prefixo):
            chave = chave[len(prefixo):]
            break
    if chave not in _CAA:
        raise ValueError(f"Classe de agressividade desconhecida: {caa!r}. Use I, II, III ou IV.")
    return _ROMANOS_CAA[_CAA[chave]]


# --- Cobrimento mínimo — 7.4.7.1, 7.4.7.2 (PDF p. 38-39) --------------------
def cobrimento_minimo_mm(caa: str, elemento: str, protendido: bool = False,
                         reducao_classe_superior: bool = False,
                         superficie_exposta_agressiva: bool = False) -> float:
    """Cobrimento mínimo cmín, em mm (7.4.7.1: cnom = cmín + Δc).

    cmín é o valor da Tabela 7.2 (impressa para Δc = 10 mm) menos 10 mm,
    com o desconto de até 5 mm quando o concreto é de classe superior à
    mínima exigida pela Tabela 7.1 (nota após a Tabela 7.2, p. 39).
    Mesmos argumentos caa/elemento/protendido de cobrimento_nominal;
    superficie_exposta_agressiva força os valores da CAA IV (nota c da
    Tabela 7.2). O piso de 45 mm da nota d (pilar em contato com o solo,
    elemento='pilar solo') não sofre a redução por classe superior: é um
    mínimo absoluto da norma, não decomposto em cmín/Δc.
    """
    el_chave = _chave(elemento).replace("/", "")
    if el_chave == "pilarsolo":
        return _cnom_tabela_bruta(caa, elemento, protendido) - 10.0
    caa_usar = "IV" if superficie_exposta_agressiva else caa
    cmin = _cnom_tabela_bruta(caa_usar, elemento, protendido) - 10.0
    if reducao_classe_superior:
        cmin -= 5.0
    return cmin


# --- Abertura máxima de fissura wk,máx — 13.4.2, Tabela 13.4 (PDF p. 100-101)
CAA_ARMADO_WK_MM = {"I": 0.4, "II": 0.3, "III": 0.3, "IV": 0.2}


def wk_max_mm(tipo_concreto: str, caa: str, nivel_protensao: int | None = None,
             tipo_protensao: str | None = None) -> tuple[float | None, str]:
    """wk,máx (mm) e a combinação de serviço a usar, pela Tabela 13.4 (p. 100-101).

    tipo_concreto: 'simples', 'armado' ou 'protendido'.
    nivel_protensao (só para 'protendido'): 1 (parcial), 2 (limitada) ou 3
    (completa).
    tipo_protensao (só para 'protendido'): 'pré-tração' ou 'pós-tração'
    (aceita sem acento e sem hífen).

    'simples' devolve (None, '-'): a tabela não exige fissuração.
    'armado' devolve (wk,máx, 'frequente'): 0,4/0,3/0,3/0,2 mm para
    CAA I/II/III/IV, sempre com a combinação frequente (ELS-W).
    'protendido' nível 1 (protensão parcial) devolve (0,2, 'frequente')
    (ELS-W), respeitada a faixa de CAA de cada tipo de protensão:
    pré-tração só CAA I; pós-tração CAA I e II. Fora da faixa, levanta
    FaixaNormativaError (a Tabela 13.4 não define esse caso).
    'protendido' níveis 2 (protensão limitada, pré-tração CAA I/II ou
    pós-tração CAA I a IV) e 3 (protensão completa, CAA I a IV para os dois
    tipos de protensão) não têm limite de wk: a exigência são duas
    verificações de tensão, ELS-F e ELS-D (a critério do projetista,
    ELS-D pode virar ELS-DP com ap = 50 mm — Figura 3.1). A função devolve
    (None, <as duas verificações e a combinação de cada uma>); o cálculo de
    tensão do ELS-F/ELS-D em si não é deste pacote.
    """
    tipo = _chave(tipo_concreto)
    if tipo == "simples":
        return (None, "-")
    if tipo == "armado":
        return (CAA_ARMADO_WK_MM[normalizar_caa(caa)], "frequente")
    if tipo != "protendido":
        raise ValueError(
            f"tipo_concreto desconhecido: {tipo_concreto!r}. Use 'simples', 'armado' ou 'protendido'."
        )
    if nivel_protensao not in (1, 2, 3):
        raise ValueError("protendido exige nivel_protensao em {1, 2, 3} (parcial/limitada/completa).")
    tp = _chave(tipo_protensao or "")
    if tp not in ("pretracao", "postracao"):
        raise ValueError("protendido exige tipo_protensao 'pré-tração' ou 'pós-tração'.")
    romano = normalizar_caa(caa)
    idx = _ROMANOS_CAA.index(romano)
    if nivel_protensao == 1:
        faixa = (0,) if tp == "pretracao" else (0, 1)
        if idx not in faixa:
            raise FaixaNormativaError(
                f"Tabela 13.4 não dá nível 1 (protensão parcial) para CAA {romano} em "
                f"{'pré-tração (só CAA I)' if tp == 'pretracao' else 'pós-tração (só CAA I e II)'}."
            )
        return (0.2, "frequente")
    if nivel_protensao == 2:
        faixa = (0, 1) if tp == "pretracao" else (0, 1, 2, 3)
        if idx not in faixa:
            raise FaixaNormativaError(
                f"Tabela 13.4 não dá nível 2 (protensão limitada) para CAA {romano} em "
                "pré-tração (só CAA I e II)."
            )
        return (None, "ELS-F (combinação frequente) e ELS-D (combinação quase-permanente; "
                      "a critério do projetista, ELS-DP com ap = 50 mm no lugar do ELS-D)")
    return (None, "ELS-F (combinação rara) e ELS-D (combinação frequente)")
