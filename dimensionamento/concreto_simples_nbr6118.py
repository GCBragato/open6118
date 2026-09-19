"""Concreto simples estrutural — ABNT NBR 6118:2026, Seção 24 (24.2 a 24.5.6).

Núcleo do concreto simples: campo de aplicação (24.2), classes de concreto
(24.3), juntas e disposições construtivas (24.4), tensões resistentes de
cálculo (24.5.2), altura de cálculo do concreto lançado contra o solo
(24.5.3), tensões e deformações na flexão (24.5.4), tensões de cisalhamento
(24.5.5) e torção (24.5.6). Os elementos (seção comprimida excêntrica,
pilar-parede, bloco, arco — 24.5.7 e 24.6) ficam para o P41, no mesmo módulo.

γc do concreto simples
----------------------
24.5.2.1: "Em todos os casos de aplicação do concreto simples estrutural, deve
ser adotado γc = 1,2 × 1,4 = 1,68". O valor mora na constante local
``GAMA_C_SIMPLES`` e **nenhuma** função deste módulo usa o γc padrão do núcleo
(``nucleo_nbr6118.GAMA_C = 1,4``) nem chama ``nucleo_nbr6118.fctd`` ou
``nucleo_nbr6118.fcd`` com o padrão — assim o 1,4 do concreto armado não é
herdado em silêncio (risco 4 da seção 8 do plano).

Faixa de fck
------------
24.3 admite C15 a C40, e o núcleo (8.2.1) só aceita C20 a C90. Por isso este
módulo valida o fck com ``validar_fck_simples`` e usa, do núcleo, as expressões
de 8.2.5 pela função interna ``_fct_m`` (válidas para fck >= 7 MPa, 8.2.5) e o
β1 de 12.3.3 (``beta1``), sem passar pela validação C20 do concreto armado.

Duas tensões de tração diferentes (risco 3 da seção 8 do plano)
---------------------------------------------------------------
- 24.5.2.2, fibra extrema à tração: σctRd = 0,85·fctd → ``sigma_ctRd``;
- 24.5.4.3, simplificação adicional na flexão, região tracionada:
  σctRd = 0,8·fctd constante → ``sigma_ctRd_flexao_simplificada``.

Convenções: tensões e fck em MPa; seção em cm; esforço em kN (1 kN/cm² =
10 MPa, conversão dentro da função); deformação em ‰. Páginas do PDF citadas
em cada função (impressa = PDF − 18). Fora da faixa, ``FaixaNormativaError``.
Verificações devolvem ``@dataclass(frozen=True)`` com ``ok``, ``governante`` e
``memoria`` (tupla de linhas da memória de cálculo).
"""

from __future__ import annotations

from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
    import seguranca_nbr6118 as seg
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr
    from dimensionamento import seguranca_nbr6118 as seg

FaixaNormativaError = nbr.FaixaNormativaError

# ---------------------------------------------------------------------------
# Constantes da Seção 24
# ---------------------------------------------------------------------------
GAMA_C_SIMPLES = 1.2 * 1.4       # 24.5.2.1 — γc = 1,2 × 1,4 = 1,68 (PDF p. 225)
FCK_MIN_SIMPLES = 15.0           # 24.3 — C15 (PDF p. 224)
FCK_MAX_SIMPLES = 40.0           # 24.3 — C40 (PDF p. 224)
JUNTA_MAX_M = 15.0               # 24.4 — juntas de dilatação pelo menos a cada 15 m (PDF p. 224)
DIST_ARMADURA_JUNTA_CM = 6.0     # 24.4 — armadura termina pelo menos a 6 cm das juntas (PDF p. 224)
REDUCAO_H_CONTRA_SOLO_CM = 5.0   # 24.5.3 — h considerado 5 cm menor que o real (PDF p. 226)

COEF_FIBRA_EXTREMA = 0.85        # 24.5.2.2 — σcRd = 0,85·fcd; σctRd = 0,85·fctd (PDF p. 225)
COEF_TRACAO_FLEXAO_SIMPLIFICADA = 0.8   # 24.5.4.3 — σctRd = 0,8·fctd (PDF p. 227)
COEF_TAU = 0.30                  # 24.5.2.3 a 24.5.2.6 — τ = 0,30·fctd (PDF p. 225-226)
FATOR_COMPRESSAO_MAX = 2.0       # 24.5.2.3 — (1 + 3·σcmd/fck) <= 2 (PDF p. 225)
TAU_RD_MAX_MPA = 1.0             # 24.5.2.4 a 24.5.2.6 — τRd = 0,30·fctd <= 1,0 MPa (PDF p. 225-226)

EPS_C_LIM_PMIL = 3.5             # 24.5.4.1 — εc,lim = 0,0035 (PDF p. 226)
EPS_CT_LIM_PMIL = 0.35           # 24.5.4.1 — εct,lim = 0,00035 (PDF p. 226)
EPS_C_MEDIA_PMIL = 2.0           # 24.5.4.2 — εc <= 0,002 a 0,43·h (PDF p. 227)
EPS_CT_MEDIA_PMIL = 0.2          # 24.5.4.2 — εct <= 0,0002 a 0,43·h (PDF p. 227)
DIST_FIBRA_MEDIA_REL = 0.43      # 24.5.4.2 — fibra distante 0,43·h da extrema (PDF p. 227)


def _fmt(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


def _positivo(valor: float, nome: str) -> float:
    v = float(valor)
    if not v > 0.0:
        raise FaixaNormativaError(f"{nome} deve ser positivo (recebido {v:g}).")
    return v


def _nao_negativo(valor: float, nome: str) -> float:
    v = float(valor)
    if v < 0.0:
        raise FaixaNormativaError(f"{nome} não pode ser negativo (recebido {v:g}).")
    return v


# ---------------------------------------------------------------------------
# 24.2 — Campo de aplicação (PDF p. 224) e 24.5.2.5 (PDF p. 226)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoAplicabilidade:
    """Resultado de ``concreto_simples_aplicavel`` (24.2 e 24.5.2.5)."""

    condicoes_basicas: tuple[str, ...]
    impedimentos: tuple[str, ...]
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def concreto_simples_aplicavel(confinamento_lateral: bool = False,
                               compressao_toda_secao: bool = False,
                               apoio_vertical_continuo: bool = False,
                               outra_condicao: str = "",
                               sujeita_a_sismo: bool = False,
                               sujeita_a_explosao: bool = False,
                               dutilidade_importante: bool = False,
                               peca_curva: bool = False,
                               torcao_de_equilibrio: bool = False
                               ) -> ResultadoAplicabilidade:
    """Diz se o elemento pode ser de concreto simples estrutural (24.2, PDF p. 224; 24.5.2.5, PDF p. 226).

    24.2: "O concreto simples estrutural deve ter garantidas algumas condições
    básicas, como confinamento lateral (caso de estacas ou tubos), compressão
    em toda seção transversal (caso de arcos), apoio vertical contínuo no solo
    ou em outra peça estrutural (caso de pilares, paredes, blocos ou
    pedestais)." e "Não é permitido o uso de concreto simples em estruturas
    sujeitas a sismos ou a explosões, e em casos onde a dutilidade seja
    qualidade importante da estrutura."

    24.5.2.5: "Peças curvas ou que estejam sujeitas a torção de equilíbrio não
    podem ser de concreto simples."

    Critério adotado: é preciso ao menos uma condição básica. A lista da norma
    é exemplificativa ("como"); uma condição básica diferente das três entra
    por ``outra_condicao`` (texto não vazio, registrado na memória). Qualquer
    impedimento reprova. ``peca_curva`` refere-se à restrição de 24.5.2.5;
    o arco, que 24.2 cita como exemplo e 24.6.4 trata expressamente, não deve
    ser marcado como peça curva aqui.
    """
    basicas = []
    if confinamento_lateral:
        basicas.append("confinamento lateral (estacas ou tubos)")
    if compressao_toda_secao:
        basicas.append("compressão em toda a seção transversal (arcos)")
    if apoio_vertical_continuo:
        basicas.append("apoio vertical contínuo no solo ou em outra peça "
                       "(pilares, paredes, blocos ou pedestais)")
    if str(outra_condicao).strip():
        basicas.append(f"outra condição básica: {str(outra_condicao).strip()}")

    impedimentos = []
    if sujeita_a_sismo:
        impedimentos.append("estrutura sujeita a sismos (24.2)")
    if sujeita_a_explosao:
        impedimentos.append("estrutura sujeita a explosões (24.2)")
    if dutilidade_importante:
        impedimentos.append("a dutilidade é qualidade importante da estrutura (24.2)")
    if peca_curva:
        impedimentos.append("peça curva (24.5.2.5)")
    if torcao_de_equilibrio:
        impedimentos.append("peça sujeita a torção de equilíbrio (24.5.2.5)")

    ok = bool(basicas) and not impedimentos
    if impedimentos:
        governante = "Não permitido: " + "; ".join(impedimentos) + "."
    elif not basicas:
        governante = ("Não permitido: nenhuma condição básica de 24.2 garantida "
                      "(confinamento lateral, compressão em toda a seção ou apoio "
                      "vertical contínuo).")
    else:
        governante = "Concreto simples aplicável."
    memoria = (
        "24.2 — Campo de aplicação do concreto simples (PDF p. 224).",
        "Condições básicas garantidas: "
        + ("; ".join(basicas) if basicas else "nenhuma") + ".",
        "Impedimentos (24.2 e 24.5.2.5): "
        + ("; ".join(impedimentos) if impedimentos else "nenhum") + ".",
        governante,
    )
    return ResultadoAplicabilidade(tuple(basicas), tuple(impedimentos), ok,
                                   governante, memoria)


# ---------------------------------------------------------------------------
# 24.3 — Materiais e propriedades (PDF p. 224)
# ---------------------------------------------------------------------------
def validar_fck_simples(fck_mpa: float) -> float:
    """Confere a classe do concreto simples, C15 a C40 (24.3, PDF p. 224), e devolve fck em MPa.

    24.3: "utilizando-se concreto da classe C15 a C40 (ABNT NBR 8953)".
    Fora de 15 <= fck <= 40 MPa levanta ``FaixaNormativaError``.
    """
    fck = float(fck_mpa)
    if not (FCK_MIN_SIMPLES <= fck <= FCK_MAX_SIMPLES):
        raise FaixaNormativaError(
            f"fck = {fck:g} MPa fora da faixa do concreto simples "
            f"(24.3: C{FCK_MIN_SIMPLES:g} a C{FCK_MAX_SIMPLES:g})."
        )
    return fck


# ---------------------------------------------------------------------------
# 24.4 — Juntas e disposições construtivas (PDF p. 224)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoJuntas:
    """Resultado de ``verificar_juntas`` (24.4)."""

    espacamento_m: float
    espacamento_max_m: float
    exige_efeitos_termicos_retracao: bool
    efeitos_considerados: bool
    dist_armadura_junta_cm: float | None
    dist_armadura_min_cm: float
    ok_espacamento: bool
    ok_armadura: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_juntas(espacamento_m: float,
                     dist_armadura_junta_cm: float | None = None,
                     efeitos_considerados: bool = False) -> ResultadoJuntas:
    """Verifica o espaçamento das juntas de dilatação e a distância da armadura à junta (24.4, PDF p. 224).

    24.4: "As juntas de dilatação devem ser previstas pelo menos a cada 15 m.
    No caso de ser necessário afastamento maior, devem ser considerados no
    cálculo os efeitos da retração térmica do concreto (como consequência do
    calor de hidratação), da retração hidráulica e das variações de
    temperatura." e "Qualquer armadura eventualmente existente no concreto
    simples deve terminar pelo menos a 6 cm das juntas."

    - espaçamento <= 15 m: ok sem exigência adicional;
    - espaçamento > 15 m: ``exige_efeitos_termicos_retracao`` = True, e só
      passa com ``efeitos_considerados=True`` (o chamador declara que esses
      efeitos entraram no cálculo);
    - ``dist_armadura_junta_cm`` (cm): None quando não há armadura; senão
      tem de ser >= 6 cm.

    Os limites usam ``seguranca_nbr6118.verificar_seguranca`` (tolerância 1e-9).
    """
    esp = _positivo(espacamento_m, "O espaçamento entre juntas")
    r_esp = seg.verificar_seguranca(JUNTA_MAX_M, esp, "espaçamento de juntas", "24.4")
    exige = not r_esp.ok
    ok_esp = r_esp.ok or bool(efeitos_considerados)
    memoria = [
        "24.4 — Juntas e disposições construtivas (PDF p. 224).",
        f"Espaçamento entre juntas = {_fmt(esp)} m; máximo sem cálculo dos efeitos "
        f"térmicos e de retração = {_fmt(JUNTA_MAX_M)} m.",
    ]
    if exige:
        memoria.append(
            "Espaçamento maior que 15 m: devem ser considerados no cálculo a retração "
            "térmica (calor de hidratação), a retração hidráulica e as variações de "
            "temperatura — " + ("considerados." if efeitos_considerados
                                else "não considerados, não passa."))
    else:
        memoria.append("Espaçamento <= 15 m -> ok.")

    if dist_armadura_junta_cm is None:
        ok_arm = True
        dist = None
        memoria.append("Sem armadura: a distância mínima de 6 cm à junta não se aplica.")
    else:
        dist = _nao_negativo(dist_armadura_junta_cm, "A distância da armadura à junta")
        ok_arm = seg.verificar_seguranca(dist, DIST_ARMADURA_JUNTA_CM,
                                         "distância da armadura à junta", "24.4").ok
        memoria.append(
            f"Armadura termina a {_fmt(dist)} cm da junta; mínimo "
            f"{_fmt(DIST_ARMADURA_JUNTA_CM)} cm -> {'ok' if ok_arm else 'não ok'}.")

    ok = ok_esp and ok_arm
    falhas = []
    if not ok_esp:
        falhas.append("espaçamento entre juntas maior que 15 m sem considerar os "
                      "efeitos térmicos e de retração")
    if not ok_arm:
        falhas.append("armadura a menos de 6 cm da junta")
    governante = ("Juntas atendem 24.4." if ok else
                  "Não atende 24.4: " + "; ".join(falhas) + ".")
    memoria.append(governante)
    return ResultadoJuntas(esp, JUNTA_MAX_M, exige, bool(efeitos_considerados),
                           dist, DIST_ARMADURA_JUNTA_CM, ok_esp, ok_arm, ok,
                           governante, tuple(memoria))


# ---------------------------------------------------------------------------
# 24.5.2.1 — Resistências de cálculo com γc = 1,68 (PDF p. 225)
# ---------------------------------------------------------------------------
def fctk_inf_simples(fck_mpa: float) -> float:
    """fctk,inf do concreto simples, MPa (24.5.2.1 remetendo a 8.2.5, PDF p. 225 e 42-43).

    fctk,inf = 0,7·fct,m, com fct,m = 0,3·fck^(2/3) (fck <= 50 MPa, 8.2.5).
    fct,m vem do núcleo (``nucleo_nbr6118._fct_m``, as expressões de 8.2.5,
    válidas para fck >= 7 MPa); não se usa ``nucleo_nbr6118.fctk_inf`` porque
    ele valida a faixa C20 a C90 do concreto armado e rejeitaria o C15 que 24.3
    admite. Faixa: C15 a C40 (24.3).
    """
    fck = validar_fck_simples(fck_mpa)
    return 0.7 * nbr._fct_m(fck)


def fctd_simples(fck_mpa: float) -> float:
    """Resistência de cálculo à tração do concreto simples, MPa (24.5.2.1, PDF p. 225).

    fctd = fctk,inf/γc, com γc = 1,2 × 1,4 = 1,68 (``GAMA_C_SIMPLES``) em todos
    os casos de concreto simples estrutural. Não usa o γc = 1,4 do núcleo.
    Faixa: C15 a C40 (24.3).
    """
    return fctk_inf_simples(fck_mpa) / GAMA_C_SIMPLES


def fcd_simples(fck_mpa: float, t_dias: float = 28.0, cimento: str = "CPII") -> float:
    """Resistência de cálculo à compressão do concreto simples, MPa (24.5.2.1 e 12.3.3, PDF p. 225 e 90-91).

    t >= 28 dias: fcd = fck/γc; t < 28 dias: fcd = β1·fck/γc (12.3.3, β1 do
    núcleo, ``nucleo_nbr6118.beta1``), com γc = 1,68 (``GAMA_C_SIMPLES``).
    Não usa ``nucleo_nbr6118.fcd`` porque ele valida a faixa C20 a C90 e
    rejeitaria o C15. Faixa: C15 a C40 (24.3).
    """
    fck = validar_fck_simples(fck_mpa)
    fckj = fck if float(t_dias) >= 28.0 else nbr.beta1(t_dias, cimento, fck) * fck
    return fckj / GAMA_C_SIMPLES


# ---------------------------------------------------------------------------
# 24.5.2.2 — Tensões resistentes nas fibras extremas (PDF p. 225)
# ---------------------------------------------------------------------------
def sigma_cRd(fck_mpa: float) -> float:
    """Tensão resistente de cálculo na fibra extrema à compressão, MPa (24.5.2.2, PDF p. 225).

    σcRd = 0,85·fcd, com fcd = fck/1,68 (24.5.2.1). Faixa: C15 a C40 (24.3).
    """
    return COEF_FIBRA_EXTREMA * fcd_simples(fck_mpa)


def sigma_ctRd(fck_mpa: float) -> float:
    """Tensão resistente de cálculo na fibra extrema à tração, MPa (24.5.2.2, PDF p. 225).

    σctRd = 0,85·fctd, com fctd = fctk,inf/1,68 (24.5.2.1).
    Não confundir com a simplificação da flexão de 24.5.4.3 (0,8·fctd,
    ``sigma_ctRd_flexao_simplificada``). Faixa: C15 a C40 (24.3).
    """
    return COEF_FIBRA_EXTREMA * fctd_simples(fck_mpa)


# ---------------------------------------------------------------------------
# 24.5.2.3 a 24.5.2.6 — Tensões de cisalhamento resistentes (PDF p. 225-226)
# ---------------------------------------------------------------------------
def fator_compressao_cisalhamento(fck_mpa: float, sigma_cmd_mpa: float = 0.0) -> float:
    """Fator de influência da compressão (1 + 3·σcmd/fck) <= 2 (24.5.2.3, PDF p. 225).

    σcmd é a tensão média de compressão de cálculo no concreto (MPa, positiva
    na compressão). Na flexão simples e na flexo-tração use σcmd = 0 (fator
    1,0); valor negativo levanta ``FaixaNormativaError``. O fator é limitado a
    2,0, o que ocorre para σcmd >= fck/3. Faixa: C15 a C40 (24.3).
    """
    fck = validar_fck_simples(fck_mpa)
    s = float(sigma_cmd_mpa)
    if s < 0.0:
        raise FaixaNormativaError(
            f"σcmd = {s:g} MPa: informe a tensão média de compressão positiva; "
            "na flexão simples e na flexo-tração use σcmd = 0 (24.5.2.3).")
    return min(1.0 + 3.0 * s / fck, FATOR_COMPRESSAO_MAX)


def tau_wRd(fck_mpa: float, sigma_cmd_mpa: float = 0.0) -> float:
    """Tensão de cisalhamento resistente de cálculo à força cortante em peças lineares, MPa (24.5.2.3, PDF p. 225).

    τwRd = 0,30·fctd, na flexão simples e na flexo-tração (σcmd = 0);
    τwRd = 0,30·fctd·(1 + 3·σcmd/fck), na flexo-compressão, com
    (1 + 3·σcmd/fck) <= 2.
    fctd com γc = 1,68 (24.5.2.1); σcmd em MPa, positiva na compressão.
    Faixa: C15 a C40 (24.3).
    """
    return COEF_TAU * fctd_simples(fck_mpa) * fator_compressao_cisalhamento(
        fck_mpa, sigma_cmd_mpa)


_CASOS_TAU_RD = {
    "laje": ("24.5.2.4", "lajes submetidas a flexão ou flexo-tração", "τRd", "PDF p. 225"),
    "torcao": ("24.5.2.5", "torção simples", "τTRd", "PDF p. 225"),
    "puncao": ("24.5.2.6", "punção no contorno C' (19.5.2.6)", "τRd", "PDF p. 226"),
}


def tau_Rd_laje_torcao_puncao(fck_mpa: float, caso: str = "laje") -> float:
    """Tensão de cisalhamento resistente de cálculo em lajes, torção simples ou punção, MPa (24.5.2.4 a 24.5.2.6, PDF p. 225-226).

    A mesma expressão nos três casos:
    - laje submetida a flexão ou flexo-tração (24.5.2.4): τRd = 0,30·fctd <= 1,0 MPa;
    - torção simples (24.5.2.5): τTRd = 0,30·fctd <= 1,0 MPa;
    - punção no contorno C' (24.5.2.6): τRd = 0,30·fctd <= 1,0 MPa.
    ``caso`` ∈ {'laje', 'torcao', 'puncao'}. fctd com γc = 1,68 (24.5.2.1).

    Observação: com C15 a C40 e γc = 1,68, 0,30·fctd vai de 0,228 MPa (C15)
    a 0,439 MPa (C40); o teto de 1,0 MPa da norma é aplicado, mas não governa
    dentro da faixa de 24.3. Faixa: C15 a C40 (24.3).
    """
    chave = nbr._chave(caso)
    if chave not in _CASOS_TAU_RD:
        raise ValueError(
            f"Caso desconhecido: {caso!r}. Use 'laje' (24.5.2.4), 'torcao' "
            "(24.5.2.5) ou 'puncao' (24.5.2.6).")
    return min(COEF_TAU * fctd_simples(fck_mpa), TAU_RD_MAX_MPA)


# ---------------------------------------------------------------------------
# 24.5.3 — Altura de cálculo do concreto lançado contra o solo (PDF p. 226)
# ---------------------------------------------------------------------------
def altura_contra_solo_cm(h_cm: float, lancado_contra_solo: bool = True) -> float:
    """Altura total a considerar no cálculo das tensões, cm (24.5.3, PDF p. 226).

    24.5.3: "No cálculo de tensões causadas por flexão, flexão composta e
    tensões tangenciais, deve ser considerada a seção transversal total do
    elemento, exceto no caso de concreto lançado contra o solo, onde a altura
    total h a ser considerada deve ser 5 cm menor que a real."

    h_calc = h − 5 cm, se lançado contra o solo; h_calc = h, caso contrário.
    h em cm; h <= 5 cm contra o solo levanta ``FaixaNormativaError``.
    """
    h = _positivo(h_cm, "A altura h")
    if not lancado_contra_solo:
        return h
    if h <= REDUCAO_H_CONTRA_SOLO_CM:
        raise FaixaNormativaError(
            f"h = {h:g} cm: com a redução de 5 cm do concreto lançado contra o solo "
            "(24.5.3), a altura de cálculo não seria positiva.")
    return h - REDUCAO_H_CONTRA_SOLO_CM


# ---------------------------------------------------------------------------
# 24.5.4.1 e 24.5.4.2 — Limites de deformação na flexão (PDF p. 226-227)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoDeformacoes:
    """Resultado de ``verificar_deformacoes_extremas``/``verificar_deformacoes_medias``."""

    eps_c_pmil: float
    eps_ct_pmil: float
    eps_c_lim_pmil: float
    eps_ct_lim_pmil: float
    ok_compressao: bool
    ok_tracao: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def _verificar_deformacoes(eps_c_pmil, eps_ct_pmil, lim_c, lim_ct, item, pagina,
                           onde) -> ResultadoDeformacoes:
    ec = _nao_negativo(eps_c_pmil, "εc (valor absoluto, em ‰)")
    ect = _nao_negativo(eps_ct_pmil, "εct (valor absoluto, em ‰)")
    ok_c = seg.verificar_seguranca(lim_c, ec, "εc", item).ok
    ok_t = seg.verificar_seguranca(lim_ct, ect, "εct", item).ok
    ok = ok_c and ok_t
    if ok:
        governante = f"Deformações {onde} dentro dos limites de {item}."
    else:
        falhas = []
        if not ok_c:
            falhas.append(f"εc = {_fmt(ec)} ‰ > {_fmt(lim_c)} ‰")
        if not ok_t:
            falhas.append(f"εct = {_fmt(ect)} ‰ > {_fmt(lim_ct)} ‰")
        governante = f"Não atende {item}: " + "; ".join(falhas) + "."
    memoria = (
        f"{item} — Limites das deformações {onde} ({pagina}).",
        f"Compressão: εc = {_fmt(ec)} ‰ <= {_fmt(lim_c)} ‰ -> {'ok' if ok_c else 'não ok'}.",
        f"Tração: εct = {_fmt(ect)} ‰ <= {_fmt(lim_ct)} ‰ -> {'ok' if ok_t else 'não ok'}.",
        governante,
    )
    return ResultadoDeformacoes(ec, ect, lim_c, lim_ct, ok_c, ok_t, ok, governante, memoria)


def verificar_deformacoes_extremas(eps_c_pmil: float,
                                   eps_ct_pmil: float = 0.0) -> ResultadoDeformacoes:
    """Verifica as deformações nas fibras extremas na flexão (24.5.4.1, PDF p. 226).

    εc <= εc,lim = 0,0035 (3,5 ‰) na fibra mais comprimida;
    εct <= εct,lim = 0,00035 (0,35 ‰) na fibra mais tracionada.
    Entradas em ‰, em valor absoluto (>= 0). A fluência nos carregamentos de
    longa duração (Figura 24.1) deve estar incluída nas deformações informadas.
    """
    return _verificar_deformacoes(eps_c_pmil, eps_ct_pmil, EPS_C_LIM_PMIL,
                                  EPS_CT_LIM_PMIL, "24.5.4.1", "PDF p. 226",
                                  "nas fibras extremas")


def verificar_deformacoes_medias(eps_c_043h_pmil: float,
                                 eps_ct_043h_pmil: float = 0.0) -> ResultadoDeformacoes:
    """Verifica as deformações médias com pequena excentricidade (24.5.4.2, PDF p. 227).

    Na compressão, na fibra distante 0,43·h da mais comprimida: εc <= 0,002 (2,0 ‰);
    na tração, na fibra distante 0,43·h da mais tracionada: εct <= 0,0002 (0,2 ‰).
    Entradas em ‰, em valor absoluto (>= 0), lidas nas fibras a 0,43·h
    (``fibra_deformacao_media_cm``).
    """
    return _verificar_deformacoes(eps_c_043h_pmil, eps_ct_043h_pmil, EPS_C_MEDIA_PMIL,
                                  EPS_CT_MEDIA_PMIL, "24.5.4.2", "PDF p. 227",
                                  "médias (fibras a 0,43·h)")


def fibra_deformacao_media_cm(h_cm: float) -> float:
    """Distância da fibra de deformação média à fibra extrema, 0,43·h, cm (24.5.4.2, PDF p. 227)."""
    return DIST_FIBRA_MEDIA_REL * _positivo(h_cm, "A altura h")


def sigma_c_simples(eps_pmil: float, fck_mpa: float) -> float:
    """Tensão no diagrama parábola-retângulo simplificado do concreto simples, MPa (24.5.4.1, Figura 24.1, PDF p. 226).

    Convenção: compressão positiva (ε > 0, σ > 0); tração negativa.
    - Compressão, 0 <= ε <= 2 ‰: σ = 0,85·fcd·[1 − (1 − ε/2)²];
      2 ‰ <= ε <= 3,5 ‰: σ = 0,85·fcd.
    - Tração, 0 <= |ε| <= 0,2 ‰: σ = −0,85·fctd·[1 − (1 − |ε|/0,2)²];
      0,2 ‰ <= |ε| <= 0,35 ‰: σ = −0,85·fctd.
    Deformação além de εc,lim = 3,5 ‰ ou εct,lim = 0,35 ‰ levanta
    ``FaixaNormativaError``.

    O que vem da norma: o pico de compressão 0,85·fcd, os pontos 0,002 e
    0,0035 e, na tração, 0,0002 e 0,00035 (Figura 24.1); a forma
    parábola-retângulo "tanto na compressão como na tração" (24.5.4.1). O que
    foi adotado: expoente 2 nas duas parábolas (o mesmo do núcleo para fck <=
    50 MPa) e o patamar de tração em 0,85·fctd (σctRd de 24.5.2.2), porque a
    Figura 24.1 não cota a ordenada do ramo tracionado. A fluência não está
    incluída: a deformação informada já deve considerá-la (24.5.4.1).
    fcd e fctd com γc = 1,68. Faixa: C15 a C40 (24.3).
    """
    e = float(eps_pmil)
    if e >= 0.0:
        if e > EPS_C_LIM_PMIL * (1.0 + 1e-12):
            raise FaixaNormativaError(
                f"εc = {e:g} ‰ além de εc,lim = 3,5 ‰ (24.5.4.1).")
        pico = sigma_cRd(fck_mpa)
        r = min(e / EPS_C_MEDIA_PMIL, 1.0)
        return pico * (1.0 - (1.0 - r) ** 2)
    a = -e
    if a > EPS_CT_LIM_PMIL * (1.0 + 1e-12):
        raise FaixaNormativaError(
            f"εct = {a:g} ‰ além de εct,lim = 0,35 ‰ (24.5.4.1).")
    pico = sigma_ctRd(fck_mpa)
    r = min(a / EPS_CT_MEDIA_PMIL, 1.0)
    return -pico * (1.0 - (1.0 - r) ** 2)


# ---------------------------------------------------------------------------
# 24.5.4.3 — Tensões resistentes simplificadas na flexão (PDF p. 227)
# ---------------------------------------------------------------------------
def sigma_ctRd_flexao_simplificada(fck_mpa: float) -> float:
    """Tensão resistente de cálculo constante na região tracionada, simplificação da flexão, MPa (24.5.4.3, PDF p. 227).

    σctRd = 0,8·fctd, constante na região tracionada, com fctd calculado com o
    valor inferior (fctk,inf) e γc = 1,68 (24.5.2.1). É um coeficiente
    diferente do 0,85 da fibra extrema de 24.5.2.2 (``sigma_ctRd``).
    Faixa: C15 a C40 (24.3).
    """
    return COEF_TRACAO_FLEXAO_SIMPLIFICADA * fctd_simples(fck_mpa)


@dataclass(frozen=True)
class TensoesFlexaoSimplificada:
    """Tensões resistentes da simplificação adicional da flexão (24.5.4.3)."""

    fck_mpa: float
    fctd_mpa: float
    fcd_mpa: float
    sigma_ctRd_mpa: float
    sigma_cRd_mpa: float
    memoria: tuple[str, ...]


def tensoes_flexao_simplificada(fck_mpa: float) -> TensoesFlexaoSimplificada:
    """Tensões resistentes de cálculo simplificadas para a flexão (24.5.4.3, PDF p. 227).

    - região tracionada: σctRd = 0,8·fctd, constante (valor inferior de fct);
    - região comprimida: diagrama linear de tensões com pico σcRd = 0,85·fcd.
    fcd e fctd com γc = 1,68 (24.5.2.1). Faixa: C15 a C40 (24.3).
    """
    fck = validar_fck_simples(fck_mpa)
    fctd = fctd_simples(fck)
    fcd = fcd_simples(fck)
    s_ct = sigma_ctRd_flexao_simplificada(fck)
    s_c = sigma_cRd(fck)
    memoria = (
        "24.5.4.3 — Tensões resistentes de cálculo, simplificação adicional na flexão (PDF p. 227).",
        f"γc = {_fmt(GAMA_C_SIMPLES)} (24.5.2.1); fctd = fctk,inf/γc = {_fmt(fctd)} MPa; "
        f"fcd = fck/γc = {_fmt(fcd)} MPa.",
        f"Região tracionada: σctRd = 0,8·fctd = 0,8 × {_fmt(fctd)} = {_fmt(s_ct)} MPa (constante).",
        f"Região comprimida: diagrama linear com pico σcRd = 0,85·fcd = 0,85 × {_fmt(fcd)} "
        f"= {_fmt(s_c)} MPa.",
    )
    return TensoesFlexaoSimplificada(fck, fctd, fcd, s_ct, s_c, memoria)


# ---------------------------------------------------------------------------
# 24.5.5 — Tensões de cisalhamento (PDF p. 227)
# ---------------------------------------------------------------------------
def tau_wd_retangular_mpa(Vsd_kn: float, b_cm: float, h_cm: float,
                          lancado_contra_solo: bool = False) -> float:
    """Tensão de cisalhamento de cálculo em seção retangular, MPa (24.5.5.1, PDF p. 227).

    τwd = (3·VSd)/(2·b·h), com h a altura total da seção (não a altura útil d).
    VSd em kN, b e h em cm: τwd sai em kN/cm² e é convertido para MPa (× 10).
    Com ``lancado_contra_solo=True``, h é reduzido de 5 cm (24.5.3,
    ``altura_contra_solo_cm``). VSd em valor absoluto.
    """
    V = abs(float(Vsd_kn))
    b = _positivo(b_cm, "A largura b")
    h = altura_contra_solo_cm(h_cm, lancado_contra_solo)
    return 3.0 * V / (2.0 * b * h) * 10.0


@dataclass(frozen=True)
class SecaoCriticaCisalhamento:
    """Posição da seção de cálculo do cisalhamento (24.5.5.2 e 24.5.5.3)."""

    x_face_cm: float
    reducao_no_apoio: bool
    memoria: tuple[str, ...]


def secao_critica_cisalhamento(h_cm: float, laje: bool = False) -> SecaoCriticaCisalhamento:
    """Posição, a partir da face do apoio, da força cortante de cálculo de τwd (24.5.5.2 e 24.5.5.3, PDF p. 227).

    24.5.5.2: τwd "deve ser calculada para a força cortante a uma distância h
    da face do apoio. Para seções mais próximas do apoio, admite-se esse mesmo
    valor de força cortante." — x = h (altura total, não d).
    24.5.5.3: "No caso de lajes, não pode ser feita a redução do valor da força
    cortante nos apoios" — x = 0 (força cortante na face do apoio).
    h em cm (para concreto lançado contra o solo, passe a altura de 24.5.3).
    """
    h = _positivo(h_cm, "A altura h")
    if laje:
        return SecaoCriticaCisalhamento(0.0, False, (
            "24.5.5.3 — Lajes: não pode ser feita a redução da força cortante nos "
            "apoios; VSd tomada na face do apoio (x = 0) (PDF p. 227).",))
    return SecaoCriticaCisalhamento(h, True, (
        f"24.5.5.2 — VSd tomada a x = h = {_fmt(h)} cm da face do apoio; nas seções "
        "mais próximas do apoio admite-se o mesmo valor (PDF p. 227).",))


def cortante_de_calculo_kn(Vsd_face_kn: float, Vsd_a_h_kn: float,
                           laje: bool = False) -> float:
    """Força cortante a usar em τwd, kN (24.5.5.2 e 24.5.5.3, PDF p. 227).

    Peça linear: VSd na seção a h da face do apoio (``Vsd_a_h_kn``), que vale
    também para as seções mais próximas (24.5.5.2). Laje: VSd na face do
    apoio (``Vsd_face_kn``), sem redução (24.5.5.3). Valores em kN.
    """
    return abs(float(Vsd_face_kn)) if laje else abs(float(Vsd_a_h_kn))


@dataclass(frozen=True)
class ResultadoCisalhamentoSimples:
    """Resultado de ``verificar_cisalhamento`` (24.5.5)."""

    tau_wd_mpa: float
    tau_Rd_mpa: float
    h_calculo_cm: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_cisalhamento(Vsd_kn: float, b_cm: float, h_cm: float, fck_mpa: float,
                           sigma_cmd_mpa: float = 0.0, laje: bool = False,
                           lancado_contra_solo: bool = False
                           ) -> ResultadoCisalhamentoSimples:
    """Verifica τwd <= τRd em seção retangular de concreto simples (24.5.5.1 e 24.5.5.3, PDF p. 227).

    τwd = 3·VSd/(2·b·h) (24.5.5.1). Resistência: peça linear, τwRd de
    24.5.2.3 (``tau_wRd``, com σcmd na flexo-compressão); laje, τRd de
    24.5.2.4 (``tau_Rd_laje_torcao_puncao``, sem σcmd). VSd já tomada na seção
    de cálculo (``cortante_de_calculo_kn``). VSd em kN, b e h em cm, σcmd e fck
    em MPa. Condição Rd >= Sd por ``seguranca_nbr6118.verificar_seguranca``.
    """
    h_calc = altura_contra_solo_cm(h_cm, lancado_contra_solo)
    tau_wd = tau_wd_retangular_mpa(Vsd_kn, b_cm, h_cm, lancado_contra_solo)
    if laje:
        if float(sigma_cmd_mpa) != 0.0:
            raise FaixaNormativaError(
                "24.5.2.4 não prevê majoração pela compressão em lajes: use "
                "sigma_cmd_mpa = 0 com laje=True.")
        tau_R = tau_Rd_laje_torcao_puncao(fck_mpa, "laje")
        rot, item_R = "τwd x τRd (laje)", "24.5.2.4 e 24.5.5.3"
    else:
        tau_R = tau_wRd(fck_mpa, sigma_cmd_mpa)
        rot, item_R = "τwd x τwRd", "24.5.2.3 e 24.5.5.1"
    r = seg.verificar_seguranca(tau_R, tau_wd, rot, "24.5.5.1")
    memoria = (
        "24.5.5 — Tensões de cisalhamento em seção retangular (PDF p. 227).",
        f"h de cálculo = {_fmt(h_calc)} cm"
        + (" (lançado contra o solo, h − 5 cm, 24.5.3)" if lancado_contra_solo else "")
        + ".",
        f"τwd = 3·VSd/(2·b·h) = 3 × {_fmt(abs(float(Vsd_kn)))}/(2 × {_fmt(float(b_cm))} × "
        f"{_fmt(h_calc)}) × 10 = {_fmt(tau_wd)} MPa.",
        f"Resistência ({item_R}): {_fmt(tau_R)} MPa (γc = {_fmt(GAMA_C_SIMPLES)}).",
    ) + r.memoria
    return ResultadoCisalhamentoSimples(tau_wd, tau_R, h_calc, r.ok, r.governante, memoria)


# ---------------------------------------------------------------------------
# 24.5.6 — Torção (PDF p. 227)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoTorcaoCortante:
    """Resultado de ``verificar_torcao_cortante`` (24.5.6)."""

    tau_Td_mpa: float
    tau_TRd_mpa: float
    tau_wd_mpa: float
    tau_wRd_mpa: float
    razao_torcao: float
    razao_cortante: float
    interacao: float
    ok_torcao: bool
    ok_cortante: bool
    ok_interacao: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_torcao_cortante(tau_Td_mpa: float, tau_wd_mpa: float, fck_mpa: float,
                              sigma_cmd_mpa: float = 0.0) -> ResultadoTorcaoCortante:
    """Verifica torção, força cortante e a interação das duas em concreto simples (24.5.6, PDF p. 227).

    - torção: τTd <= τTRd, τTRd = 0,30·fctd <= 1,0 MPa (24.5.2.5);
    - força cortante: τwd <= τwRd (24.5.2.3, com σcmd na flexo-compressão);
    - torção e força cortante: τwd/τwRd + τTd/τTRd <= 1.
    τTd vem da teoria da elasticidade (24.5.6 não dá fórmula fechada) e τwd de
    ``tau_wd_retangular_mpa`` (24.5.5.1), ambas em MPa e em valor absoluto,
    calculadas separadamente. As três condições usam
    ``seguranca_nbr6118.verificar_seguranca`` (tolerância 1e-9).
    Peças sujeitas a torção de equilíbrio não podem ser de concreto simples
    (24.5.2.5, ``concreto_simples_aplicavel``).
    """
    tTd = abs(float(tau_Td_mpa))
    twd = abs(float(tau_wd_mpa))
    tTRd = tau_Rd_laje_torcao_puncao(fck_mpa, "torcao")
    twRd = tau_wRd(fck_mpa, sigma_cmd_mpa)
    r_T = seg.verificar_seguranca(tTRd, tTd, "τTd x τTRd", "24.5.6")
    r_w = seg.verificar_seguranca(twRd, twd, "τwd x τwRd", "24.5.6")
    rz_T = tTd / tTRd
    rz_w = twd / twRd
    inter = rz_w + rz_T
    r_i = seg.verificar_seguranca(1.0, inter, "τwd/τwRd + τTd/τTRd", "24.5.6")
    ok = r_T.ok and r_w.ok and r_i.ok
    candidatos = (("torção (τTd <= τTRd)", rz_T),
                  ("força cortante (τwd <= τwRd)", rz_w),
                  ("interação τwd/τwRd + τTd/τTRd <= 1", inter))
    nome, valor = max(candidatos, key=lambda c: c[1])
    governante = (f"Governa: {nome}, razão {_fmt(valor)}"
                  + (" -> ok." if ok else " -> não passa."))
    memoria = (
        "24.5.6 — Torção e força cortante em concreto simples (PDF p. 227).",
        f"τTRd = 0,30·fctd <= 1,0 MPa = {_fmt(tTRd)} MPa (24.5.2.5); "
        f"τwRd = {_fmt(twRd)} MPa (24.5.2.3); γc = {_fmt(GAMA_C_SIMPLES)}.",
        f"Torção: τTd = {_fmt(tTd)} <= τTRd = {_fmt(tTRd)} -> {'ok' if r_T.ok else 'não ok'}.",
        f"Força cortante: τwd = {_fmt(twd)} <= τwRd = {_fmt(twRd)} -> "
        f"{'ok' if r_w.ok else 'não ok'}.",
        f"Interação: {_fmt(twd)}/{_fmt(twRd)} + {_fmt(tTd)}/{_fmt(tTRd)} = {_fmt(inter)} <= 1 -> "
        f"{'ok' if r_i.ok else 'não ok'}.",
        governante,
    )
    return ResultadoTorcaoCortante(tTd, tTRd, twd, twRd, rz_T, rz_w, inter,
                                   r_T.ok, r_w.ok, r_i.ok, ok, governante, memoria)


# === P41: Concreto simples — elementos (24.5.7 e 24.6) ===
# Seção comprimida excêntrica e com força cortante (24.5.7.2 e 24.5.7.3),
# pilar-parede (24.6.1), bloco de fundação (24.6.2), pilar (24.6.3) e arco
# (24.6.4). Tudo em seção retangular; tensões em MPa, seção em cm, esforço em
# kN e kN·cm (1 kN/cm² = 10 MPa, conversão dentro de cada função).
import math as _p41_math

try:  # executado como script, ou com dimensionamento/ no sys.path
    import sapatas_nbr6118 as _p41_sap
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import sapatas_nbr6118 as _p41_sap

EXC_ADICIONAL_REL = 0.05          # 24.5.7.2 — exa = 0,05·hx; eya = 0,05·hy (PDF p. 228)
EXC_ADICIONAL_MIN_CM = 2.0        # 24.5.7.2 — exa, eya >= 2 cm (PDF p. 228)
COEF_NRD_PILAR_PAREDE = 0.63      # 24.6.1 — NRd = 0,63·fcd·Ac·[1 − (α·ℓ/32h)²] (PDF p. 229)
DIVISOR_ESBELTEZ_PILAR_PAREDE = 32.0   # 24.6.1 — α·ℓ/(32·h) (PDF p. 229)
ALFA_SEM_RESTRICAO = 1.0          # 24.6.1 — sem restrição à rotação no topo e na base (PDF p. 229)
ALFA_COM_RESTRICAO = 0.8          # 24.6.1 — alguma restrição à rotação (PDF p. 229)
ESPESSURA_PAREDE_REL = 1.0 / 24.0  # 24.6.1 — 1/24 da altura ou do comprimento não apoiado (PDF p. 229)
ESPESSURA_PAREDE_MIN_CM = 10.0    # 24.6.1 — 10 cm (PDF p. 229)
ESPESSURA_PAREDE_FUNDACAO_MIN_CM = 15.0  # 24.6.1 — 15 cm em paredes de fundação ou sapatas corridas (PDF p. 230)
ABERTURA_N_BARRAS_MIN = 2         # 24.6.1 — pelo menos duas barras (PDF p. 230)
ABERTURA_PHI_MM = 10.0            # 24.6.1 — φ = 10 mm (PDF p. 230)
ABERTURA_PROLONGAMENTO_CM = 50.0  # 24.6.1 — prolongam-se 50 cm dos ângulos reentrantes (PDF p. 230)
ESPESSURA_MEDIA_BLOCO_MIN_CM = 20.0   # 24.6.2 — espessura média do bloco >= 20 cm (PDF p. 230)
DIMENSAO_PILAR_MIN_CM = 20.0      # 24.6.3 — menor dimensão de pilares: 20 cm (PDF p. 230)
DIMENSAO_PILAR_REL = 0.10         # 24.6.3 — ou 1/10 de sua altura (PDF p. 230)
MAJORACAO_2A_ORDEM_ARCO_MAX = 1.10  # 24.6.4 — até 10 % acima dos momentos de 1ª ordem (PDF p. 230)

_P41_TOL = 1e-9


def _p41_ok(x: bool) -> str:
    return "ok" if x else "não ok"


# ---------------------------------------------------------------------------
# 24.5.7.2 — Cálculo simplificado de seções comprimidas (PDF p. 228)
# ---------------------------------------------------------------------------
def excentricidade_adicional_cm(h_cm: float) -> float:
    """Excentricidade adicional da seção comprimida de concreto simples, cm (24.5.7.2, PDF p. 228).

    exa = 0,05·hx >= 2 cm; eya = 0,05·hy >= 2 cm, com hx e hy as dimensões
    máximas da seção na direção considerada. h em cm.
    """
    h = _positivo(h_cm, "A dimensão h da seção")
    return max(EXC_ADICIONAL_REL * h, EXC_ADICIONAL_MIN_CM)


def _area_triangulo_eficaz_cm2(ax: float, ay: float, hx: float, hy: float) -> tuple[float, float]:
    """Área do triângulo eficaz de catetos 3·ax e 3·ay e a parte dele dentro do retângulo hx × hy.

    O triângulo tem o ângulo reto no canto da seção do lado de G1 e os catetos
    sobre os dois lados que concorrem nesse canto (Figura 24.2 b); com isso o
    baricentro fica a ax e ay desses lados, isto é, em G1. Devolve (área do
    triângulo, área do triângulo recortada pelo retângulo). O recorte só atua
    quando 3·ax > hx ou 3·ay > hy (excentricidade pequena); as duas pontas
    que sobram são triângulos semelhantes e não se sobrepõem (hx/3ax + hy/3ay
    >= 4/3 > 1, pois ax <= hx/2 e ay <= hy/2).
    """
    Lx, Ly = 3.0 * ax, 3.0 * ay
    area = Lx * Ly / 2.0
    corte = 0.0
    if Lx > hx:
        corte += (Lx - hx) ** 2 * (Ly / Lx) / 2.0
    if Ly > hy:
        corte += (Ly - hy) ** 2 * (Lx / Ly) / 2.0
    return area, area - corte


@dataclass(frozen=True)
class PontoVirtualG1:
    """Um ponto de aplicação virtual G1 de 24.5.7.2 e a área eficaz correspondente."""

    nome: str
    e1x_cm: float
    e1y_cm: float
    ax_cm: float
    ay_cm: float
    Ae_triangulo_cm2: float
    Ae_cm2: float
    recortado: bool


@dataclass(frozen=True)
class ResultadoSecaoComprimidaSimples:
    """Resultado de ``secao_comprimida_excentrica`` (24.5.7.2)."""

    Nsd_kn: float
    exa_cm: float
    eya_cm: float
    G1: PontoVirtualG1
    G1x: PontoVirtualG1
    G1y: PontoVirtualG1
    Ae_cm2: float
    sigma_Sd_mpa: float
    sigma_cRd_mpa: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def _ponto_virtual(nome: str, e1x: float, e1y: float, hx: float, hy: float) -> PontoVirtualG1:
    ax = hx / 2.0 - abs(e1x)
    ay = hy / 2.0 - abs(e1y)
    if not (ax > 0.0 and ay > 0.0):
        raise FaixaNormativaError(
            f"24.5.7.2: o ponto virtual {nome} = ({e1x:g}; {e1y:g}) cm cai fora da seção "
            f"{hx:g} × {hy:g} cm; não há área eficaz com baricentro nele.")
    tri, rec = _area_triangulo_eficaz_cm2(ax, ay, hx, hy)
    return PontoVirtualG1(nome, e1x, e1y, ax, ay, tri, rec, rec < tri * (1.0 - _P41_TOL))


def secao_comprimida_excentrica(Nsd_kn: float, ex_cm: float, ey_cm: float,
                                hx_cm: float, hy_cm: float,
                                fck_mpa: float) -> ResultadoSecaoComprimidaSimples:
    """Verifica a seção retangular de concreto simples comprimida com excentricidade (24.5.7.2, PDF p. 228).

    A força Nd, aplicada em G (ex, ey) em relação aos eixos x e y que passam
    pelo centro da seção, é aplicada no ponto virtual G1 mais desfavorável
    entre G1x (ex + exa, ey) e G1y (ex, ey + eya), com exa = 0,05·hx >= 2 cm e
    eya = 0,05·hy >= 2 cm (``excentricidade_adicional_cm``). A tensão é
    uniforme na seção eficaz triangular de área Ae, com baricentro em G1
    (Figura 24.2): catetos 3·ax e 3·ay, ax e ay as distâncias de G1 aos lados
    da seção, Ae = 3ax·3ay/2. Condição de segurança:

        σSd = NSd/Ae <= σcRd = 0,85·fcd  (fcd = fck/1,68, 24.5.2.1)

    Decisões deste módulo (a norma não trata):
    - a excentricidade adicional soma-se no sentido de ex (ou ey): e1x =
      ex + exa se ex >= 0 e ex − exa se ex < 0, que é o lado desfavorável;
    - "mais desfavorável" é o G1 de menor Ae (maior σSd);
    - com excentricidade pequena o triângulo ultrapassa a seção (3·ax > hx ou
      3·ay > hy); a parte de fora é descontada de Ae (``recortado`` = True),
      o que reduz Ae e fica a favor da segurança. Sem esse recorte, a carga
      centrada daria Ae maior que a própria seção.
    - G1 fora da seção levanta ``FaixaNormativaError``.

    NSd em kN (compressão positiva), excentricidades e dimensões em cm, fck em
    MPa (C15 a C40). σSd = NSd/Ae × 10 (kN/cm² → MPa).
    """
    N = _positivo(Nsd_kn, "A força normal de compressão NSd")
    hx = _positivo(hx_cm, "A dimensão hx")
    hy = _positivo(hy_cm, "A dimensão hy")
    ex, ey = float(ex_cm), float(ey_cm)
    s_cRd = sigma_cRd(fck_mpa)
    exa = excentricidade_adicional_cm(hx)
    eya = excentricidade_adicional_cm(hy)
    sx = 1.0 if ex >= 0.0 else -1.0
    sy = 1.0 if ey >= 0.0 else -1.0
    g1x = _ponto_virtual("G1x", ex + sx * exa, ey, hx, hy)
    g1y = _ponto_virtual("G1y", ex, ey + sy * eya, hx, hy)
    g1 = g1x if g1x.Ae_cm2 <= g1y.Ae_cm2 else g1y
    Ae = g1.Ae_cm2
    sigma = N / Ae * 10.0
    r = seg.verificar_seguranca(s_cRd, sigma, "σSd x σcRd", "24.5.7.2")
    memoria = [
        "24.5.7.2 — Seção comprimida de concreto simples, cálculo simplificado (PDF p. 228).",
        f"exa = 0,05·hx >= 2 cm = {_fmt(exa)} cm; eya = 0,05·hy >= 2 cm = {_fmt(eya)} cm.",
    ]
    for p in (g1x, g1y):
        memoria.append(
            f"{p.nome} = ({_fmt(p.e1x_cm)}; {_fmt(p.e1y_cm)}) cm: ax = {_fmt(p.ax_cm)} cm, "
            f"ay = {_fmt(p.ay_cm)} cm, Ae = 3ax·3ay/2 = {_fmt(p.Ae_triangulo_cm2)} cm²"
            + (f", recortada pela seção: {_fmt(p.Ae_cm2)} cm²" if p.recortado else "")
            + ".")
    memoria += [
        f"Mais desfavorável: {g1.nome} (menor Ae = {_fmt(Ae)} cm²).",
        f"σSd = NSd/Ae = {_fmt(N)}/{_fmt(Ae)} × 10 = {_fmt(sigma)} MPa; "
        f"σcRd = 0,85·fcd = {_fmt(s_cRd)} MPa (γc = {_fmt(GAMA_C_SIMPLES)}).",
    ]
    memoria += list(r.memoria)
    return ResultadoSecaoComprimidaSimples(N, exa, eya, g1, g1x, g1y, Ae, sigma, s_cRd,
                                           r.ok, r.governante, tuple(memoria))


# ---------------------------------------------------------------------------
# 24.5.7.3 — Seção à compressão e à força cortante (PDF p. 229)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoCompressaoCortanteSimples:
    """Resultado de ``secao_comprimida_com_cortante`` (24.5.7.3)."""

    secao: ResultadoSecaoComprimidaSimples
    Vsd_kn: float
    tau_wd_mpa: float
    tau_wRd_mpa: float
    ok_normal: bool
    ok_cortante: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def secao_comprimida_com_cortante(Nsd_kn: float, Vsd_kn: float, ex_cm: float, ey_cm: float,
                                  hx_cm: float, hy_cm: float, fck_mpa: float,
                                  sigma_cmd_mpa: float = 0.0
                                  ) -> ResultadoCompressaoCortanteSimples:
    """Verifica a seção de concreto simples sob força de compressão inclinada (24.5.7.3, PDF p. 229).

    G1 e Ae como em 24.5.7.2 (``secao_comprimida_excentrica``), com as
    componentes de cálculo NSd e VSd aplicadas em G. Condições:

        σSd = NSd/Ae <= σcRd = 0,85·fcd
        τwd = VSd/Ae <= τwRd

    τwRd de 24.5.2.3 (``tau_wRd``): 0,30·fctd·(1 + 3·σcmd/fck), fator <= 2.
    σcmd (MPa) é a tensão média de compressão que o usuário adota; o padrão 0
    reproduz τwRd = 0,30·fctd, que fica a favor da segurança. NSd e VSd em kN;
    τwd = VSd/Ae × 10 (MPa). Com VSd = 0 recai em 24.5.7.2.
    """
    sec = secao_comprimida_excentrica(Nsd_kn, ex_cm, ey_cm, hx_cm, hy_cm, fck_mpa)
    V = abs(float(Vsd_kn))
    tau_wd = V / sec.Ae_cm2 * 10.0
    tau_R = tau_wRd(fck_mpa, sigma_cmd_mpa)
    r_t = seg.verificar_seguranca(tau_R, tau_wd, "τwd x τwRd", "24.5.7.3")
    ok = sec.ok and r_t.ok
    rz_n = sec.sigma_Sd_mpa / sec.sigma_cRd_mpa
    rz_t = tau_wd / tau_R
    if rz_n >= rz_t:
        governante = f"Governa: tensão normal (σSd/σcRd = {_fmt(rz_n)})"
    else:
        governante = f"Governa: cisalhamento (τwd/τwRd = {_fmt(rz_t)})"
    governante += " -> ok." if ok else " -> não passa."
    memoria = (
        ("24.5.7.3 — Seção à compressão e à força cortante (PDF p. 229); G1 e Ae de 24.5.7.2.",)
        + sec.memoria
        + (f"τwd = VSd/Ae = {_fmt(V)}/{_fmt(sec.Ae_cm2)} × 10 = {_fmt(tau_wd)} MPa; "
           f"τwRd = {_fmt(tau_R)} MPa (24.5.2.3, σcmd = {_fmt(float(sigma_cmd_mpa))} MPa).",)
        + r_t.memoria + (governante,))
    return ResultadoCompressaoCortanteSimples(sec, V, tau_wd, tau_R, sec.ok, r_t.ok, ok,
                                              governante, memoria)


# ---------------------------------------------------------------------------
# 24.6.1 — Pilares-parede (PDF p. 229-230)
# ---------------------------------------------------------------------------
def _validar_alfa(alfa: float) -> float:
    a = float(alfa)
    if not any(abs(a - v) <= 1e-12 for v in (ALFA_SEM_RESTRICAO, ALFA_COM_RESTRICAO)):
        raise FaixaNormativaError(
            f"α = {a:g}: 24.6.1 só define α = 1,0 (sem restrição à rotação no topo e na "
            "base) e α = 0,8 (alguma restrição contra rotação).")
    return a


def NRd_pilar_parede_kn(fck_mpa: float, Ac_cm2: float, h_cm: float, l_cm: float,
                        alfa: float = ALFA_SEM_RESTRICAO) -> float:
    """Força normal resistente de cálculo do pilar-parede de concreto simples, kN (24.6.1, PDF p. 229).

        NRd = 0,63·fcd·Ac·[1 − (α·ℓ/32h)²]

    fcd = fck/1,68 (24.5.2.1, ``fcd_simples``); Ac em cm² (área da seção do
    trecho considerado); h = espessura (altura total da seção transversal), cm;
    ℓ = distância vertical entre apoios, cm; α = 1,0 sem restrição à rotação no
    topo e na base, α = 0,8 com alguma restrição. NRd = 0,63·fcd/10·Ac (kN).

    Vale quando a resultante das cargas de cálculo está no terço central da
    espessura (verificado em ``verificar_pilar_parede_simples``). Para
    α·ℓ/32h > 1 a expressão deixa de ter sentido (o colchete fica negativo) e
    a função levanta ``FaixaNormativaError``; em α·ℓ = 32h, NRd = 0.
    """
    fcd = fcd_simples(fck_mpa)
    Ac = _positivo(Ac_cm2, "A área Ac")
    h = _positivo(h_cm, "A espessura h")
    l = _nao_negativo(l_cm, "A distância entre apoios ℓ")
    a = _validar_alfa(alfa)
    r = a * l / (DIVISOR_ESBELTEZ_PILAR_PAREDE * h)
    if r > 1.0 + _P41_TOL:
        raise FaixaNormativaError(
            f"24.6.1: α·ℓ/(32·h) = {r:.4g} > 1 — o pilar-parede é esbelto demais para a "
            "expressão de NRd (colchete negativo).")
    return COEF_NRD_PILAR_PAREDE * fcd / 10.0 * Ac * max(0.0, 1.0 - r * r)


def comprimento_horizontal_carga_cm(h_cm: float, dist_entre_apoios_cm: float,
                                    dist_entre_cargas_cm: float | None = None) -> float:
    """Comprimento horizontal do pilar-parede considerado para cada carga concentrada no topo, cm (24.6.1, PDF p. 229).

    Não pode ultrapassar:
    - a distância de centro a centro entre cargas (``dist_entre_cargas_cm``;
      None quando só há uma carga);
    - a distância entre apoios acrescida de quatro vezes a espessura do
      pilar-parede (``dist_entre_apoios_cm`` + 4·h).
    Transcrição literal de 24.6.1; o termo "distância entre apoios" é usado
    como está no texto. Valores em cm.
    """
    h = _positivo(h_cm, "A espessura h")
    b_ap = _nao_negativo(dist_entre_apoios_cm, "A distância entre apoios")
    lim = b_ap + 4.0 * h
    if dist_entre_cargas_cm is not None:
        lim = min(lim, _positivo(dist_entre_cargas_cm, "A distância entre cargas"))
    return lim


def espessura_minima_pilar_parede_cm(l_cm: float, fundacao: bool = False) -> float:
    """Espessura mínima do pilar-parede de concreto simples, cm (24.6.1, PDF p. 229-230).

    A espessura não pode ser menor que:
    - 1/24 da altura total ou do comprimento vertical não apoiado (``l_cm``);
    - 10 cm;
    - 15 cm, no caso de pilares-parede paredes de fundações ou de sapatas
      corridas (``fundacao=True``).
    Devolve o maior desses valores. l em cm.
    """
    l = _nao_negativo(l_cm, "A altura ou comprimento não apoiado")
    e = max(ESPESSURA_PAREDE_REL * l, ESPESSURA_PAREDE_MIN_CM)
    if fundacao:
        e = max(e, ESPESSURA_PAREDE_FUNDACAO_MIN_CM)
    return e


@dataclass(frozen=True)
class ResultadoPilarParedeSimples:
    """Resultado de ``verificar_pilar_parede_simples`` (24.6.1)."""

    Nsd_kn: float
    NRd_kn: float
    Ac_cm2: float
    esbeltez: float
    e_cm: float
    e_lim_cm: float
    h_cm: float
    h_min_cm: float
    ok_resistencia: bool
    ok_espessura: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_pilar_parede_simples(Nsd_kn: float, fck_mpa: float, b_cm: float, h_cm: float,
                                   l_cm: float, alfa: float = ALFA_SEM_RESTRICAO,
                                   e_cm: float = 0.0, fundacao: bool = False) -> ResultadoPilarParedeSimples:
    """Verifica NSd <= NRd e a espessura mínima do pilar-parede de concreto simples (24.6.1, PDF p. 229-230).

    NRd = 0,63·fcd·Ac·[1 − (α·ℓ/32h)²] (``NRd_pilar_parede_kn``), Ac = b·h,
    com b o comprimento horizontal considerado (``comprimento_horizontal_carga_cm``
    para carga concentrada) e h a espessura. A expressão só vale com a
    resultante das cargas de cálculo no terço central da espessura: |e| <= h/6;
    fora dele levanta ``FaixaNormativaError``. Espessura mínima:
    ``espessura_minima_pilar_parede_cm(ℓ, fundacao)``. NSd em kN, dimensões
    em cm, fck em MPa. Rd >= Sd por ``seguranca_nbr6118.verificar_seguranca``.
    """
    N = _positivo(Nsd_kn, "A força normal de compressão NSd")
    b = _positivo(b_cm, "O comprimento b")
    h = _positivo(h_cm, "A espessura h")
    e = abs(float(e_cm))
    e_lim = h / 6.0
    if e > e_lim * (1.0 + _P41_TOL):
        raise FaixaNormativaError(
            f"24.6.1: excentricidade e = {e:g} cm fora do terço central da espessura "
            f"(|e| <= h/6 = {e_lim:.4g} cm); a expressão de NRd de 24.6.1 não se aplica.")
    Ac = b * h
    NRd = NRd_pilar_parede_kn(fck_mpa, Ac, h, l_cm, alfa)
    esb = float(alfa) * float(l_cm) / (DIVISOR_ESBELTEZ_PILAR_PAREDE * h)
    h_min = espessura_minima_pilar_parede_cm(l_cm, fundacao)
    r = seg.verificar_seguranca(NRd, N, "NSd x NRd", "24.6.1")
    ok_h = h >= h_min * (1.0 - _P41_TOL)
    ok = r.ok and ok_h
    if not r.ok:
        governante = "NSd > NRd — não passa."
    elif not ok_h:
        governante = f"Espessura h = {_fmt(h)} cm < mínima {_fmt(h_min)} cm — não passa."
    else:
        governante = f"NSd/NRd = {_fmt(N / NRd)} e espessura >= mínima -> ok."
    memoria = (
        "24.6.1 — Pilar-parede de concreto simples (PDF p. 229-230).",
        f"Terço central: |e| = {_fmt(e)} cm <= h/6 = {_fmt(e_lim)} cm -> ok.",
        f"α·ℓ/(32·h) = {_fmt(float(alfa))} × {_fmt(float(l_cm))}/(32 × {_fmt(h)}) = {_fmt(esb)}.",
        f"NRd = 0,63·fcd·Ac·[1 − (α·ℓ/32h)²] = 0,63 × {_fmt(fcd_simples(fck_mpa))}/10 × "
        f"{_fmt(Ac)} × (1 − {_fmt(esb)}²) = {_fmt(NRd)} kN (γc = {_fmt(GAMA_C_SIMPLES)}).",
    ) + r.memoria + (
        f"Espessura mínima: max(ℓ/24; 10 cm"
        + ("; 15 cm (fundação/sapata corrida)" if fundacao else "")
        + f") = {_fmt(h_min)} cm; h = {_fmt(h)} cm -> {_p41_ok(ok_h)}.",
        governante,
    )
    return ResultadoPilarParedeSimples(N, NRd, Ac, esb, e, e_lim, h, h_min, r.ok, ok_h, ok,
                                       governante, memoria)


@dataclass(frozen=True)
class ResultadoArmaduraAberturas:
    """Resultado de ``verificar_armadura_aberturas`` (24.6.1)."""

    n_barras: int
    phi_mm: float
    prolongamento_cm: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_armadura_aberturas(n_barras: int, phi_mm: float,
                                 prolongamento_cm: float) -> ResultadoArmaduraAberturas:
    """Confere a armadura nas aberturas de portas e janelas do pilar-parede (24.6.1, PDF p. 230).

    "devem ser previstas pelo menos duas barras de φ = 10 mm, que se
    prolonguem 50 cm a partir dos ângulos reentrantes". Critério adotado:
    n >= 2, φ >= 10 mm (bitola maior atende) e prolongamento >= 50 cm.
    """
    n = int(n_barras)
    phi = _positivo(phi_mm, "O diâmetro φ")
    lp = _nao_negativo(prolongamento_cm, "O prolongamento")
    falhas = []
    if n < ABERTURA_N_BARRAS_MIN:
        falhas.append(f"{n} barra(s) < 2")
    if phi < ABERTURA_PHI_MM - _P41_TOL:
        falhas.append(f"φ = {_fmt(phi)} mm < 10 mm")
    if lp < ABERTURA_PROLONGAMENTO_CM - _P41_TOL:
        falhas.append(f"prolongamento {_fmt(lp)} cm < 50 cm")
    ok = not falhas
    governante = ("Armadura das aberturas atende 24.6.1." if ok
                  else "Não atende 24.6.1: " + "; ".join(falhas) + ".")
    memoria = (
        "24.6.1 — Aberturas de portas ou janelas: pelo menos 2 barras de φ = 10 mm, "
        "prolongadas 50 cm a partir dos ângulos reentrantes (PDF p. 230).",
        f"Proposto: {n} barra(s) de φ {_fmt(phi)} mm, prolongamento {_fmt(lp)} cm.",
        governante,
    )
    return ResultadoArmaduraAberturas(n, phi, lp, ok, governante, memoria)


# ---------------------------------------------------------------------------
# 24.6.2 — Blocos de fundação (PDF p. 230)
# ---------------------------------------------------------------------------
def bloco_simples_permitido(sobre_estacas: bool) -> bool:
    """Diz se o bloco de fundação pode ser de concreto simples (24.6.2, PDF p. 230).

    "Não pode ser usado concreto simples para blocos sobre estacas." Devolve
    False para bloco sobre estacas e True para bloco apoiado no solo.
    """
    return not bool(sobre_estacas)


def area_base_bloco_simples_cm2(Nk_kn: float, sigma_adm_kncm2: float,
                                K_maj: float = 1.1) -> float:
    """Área da base do bloco de fundação de concreto simples, cm² (24.6.2, PDF p. 230).

    "A área da base de blocos de fundação deve ser determinada a partir da
    tensão admissível do solo para cargas não majoradas." Reusa
    ``sapatas_nbr6118.area_base_cm2``: A = K_maj·Nk/σadm, com Nk a carga
    característica (não majorada) em kN, σadm em kN/cm² e K_maj o acréscimo
    para peso próprio do bloco e do solo (padrão 1,1, como nas sapatas; use
    1,0 se Nk já os incluir).
    """
    Nk = _positivo(Nk_kn, "A carga característica Nk")
    s = _positivo(sigma_adm_kncm2, "A tensão admissível do solo")
    k = _positivo(K_maj, "O fator K_maj")
    return _p41_sap.area_base_cm2(Nk, s, k)


def verificar_espessura_bloco_simples(h_medio_cm: float) -> bool:
    """Confere a espessura média do bloco de fundação de concreto simples (24.6.2, PDF p. 230).

    "A espessura média do bloco não pode ser menor do que 20 cm." h em cm;
    devolve True quando h_médio >= 20 cm.
    """
    h = _positivo(h_medio_cm, "A espessura média do bloco")
    return h >= ESPESSURA_MEDIA_BLOCO_MIN_CM * (1.0 - _P41_TOL)


def momento_secao_critica_bloco_kncm(Nsd_kn: float, L_cm: float, a_cm: float) -> float:
    """Momento fletor majorado na seção crítica do bloco, face da coluna ou parede, kN·cm (24.6.2, PDF p. 230).

    24.6.2: "O momento fletor majorado deve ser determinado na seção crítica,
    que pode ser considerada na face da coluna ou parede." Com carga centrada
    e reação do solo uniforme p = NSd/(L·B), o balanço na direção considerada
    é c = (L − a)/2 e o momento em toda a largura B do bloco é

        MSd = p·B·c²/2 = NSd·c²/(2·L)

    NSd em kN (majorada), L = dimensão do bloco na direção, a = dimensão da
    coluna ou parede na mesma direção, ambas em cm. a > L levanta erro.
    """
    N = _positivo(Nsd_kn, "A força NSd")
    L = _positivo(L_cm, "A dimensão L do bloco")
    a = _positivo(a_cm, "A dimensão a da coluna")
    if a > L:
        raise FaixaNormativaError(f"A coluna (a = {a:g} cm) é maior que o bloco (L = {L:g} cm).")
    c = (L - a) / 2.0
    return N * c * c / (2.0 * L)


def cortante_secao_critica_bloco_kn(Nsd_kn: float, L_cm: float, a_cm: float) -> float:
    """Força cortante majorada na seção crítica do bloco, face da coluna, pedestal ou parede, kN (24.6.2, PDF p. 230).

    Reação do solo uniforme p = NSd/(L·B), balanço c = (L − a)/2:
    VSd = p·B·c = NSd·c/L. NSd em kN, L e a em cm.
    """
    N = _positivo(Nsd_kn, "A força NSd")
    L = _positivo(L_cm, "A dimensão L do bloco")
    a = _positivo(a_cm, "A dimensão a da coluna")
    if a > L:
        raise FaixaNormativaError(f"A coluna (a = {a:g} cm) é maior que o bloco (L = {L:g} cm).")
    return N * (L - a) / 2.0 / L


@dataclass(frozen=True)
class ResultadoBlocoSimples:
    """Resultado de ``verificar_bloco_fundacao_simples`` (24.6.2)."""

    h_calculo_cm: float
    Msd_x_kncm: float
    Msd_y_kncm: float
    sigma_ct_x_mpa: float
    sigma_ct_y_mpa: float
    sigma_ctRd_mpa: float
    Vsd_x_kn: float
    Vsd_y_kn: float
    VRd_x_kn: float
    VRd_y_kn: float
    tau_wRd_mpa: float
    h_medio_cm: float
    ok_espessura: bool
    ok_flexao: bool
    ok_cortante: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_bloco_fundacao_simples(Nsd_kn: float, A_cm: float, B_cm: float,
                                     a_cm: float, b_cm: float, h_cm: float,
                                     fck_mpa: float, h_medio_cm: float | None = None,
                                     sobre_estacas: bool = False,
                                     lancado_contra_solo: bool = True
                                     ) -> ResultadoBlocoSimples:
    """Verifica o bloco de fundação de concreto simples apoiado no solo (24.6.2, PDF p. 230).

    - bloco sobre estacas levanta ``FaixaNormativaError`` (não pode ser de
      concreto simples);
    - espessura média >= 20 cm (``h_medio_cm``; padrão h);
    - momento na face da coluna em cada direção
      (``momento_secao_critica_bloco_kncm``) e tensão de tração na fibra
      extrema, em regime linear, σct = 6·MSd/(largura·h²) <= σctRd =
      0,85·fctd (24.5.2.1 e 24.5.2.2);
    - força cortante na face da coluna (``cortante_secao_critica_bloco_kn``):
      VSd <= Ac·τwRd, Ac = largura·h, τwRd = 0,30·fctd (24.5.2.3, flexão
      simples, σcmd = 0).

    Carga centrada e reação do solo uniforme. A = dimensão do bloco em x e
    a = da coluna em x; B e b em y; h = altura do bloco na face da coluna.
    Concreto lançado contra o solo (padrão): h de cálculo = h − 5 cm (24.5.3).
    NSd em kN, dimensões em cm, fck em MPa.
    """
    if not bloco_simples_permitido(sobre_estacas):
        raise FaixaNormativaError(
            "24.6.2: não pode ser usado concreto simples para blocos sobre estacas.")
    A = _positivo(A_cm, "A dimensão A do bloco")
    B = _positivo(B_cm, "A dimensão B do bloco")
    hm = float(h_cm) if h_medio_cm is None else float(h_medio_cm)
    ok_h = verificar_espessura_bloco_simples(hm)
    hc = altura_contra_solo_cm(h_cm, lancado_contra_solo)
    Mx = momento_secao_critica_bloco_kncm(Nsd_kn, A, a_cm)
    My = momento_secao_critica_bloco_kncm(Nsd_kn, B, b_cm)
    Vx = cortante_secao_critica_bloco_kn(Nsd_kn, A, a_cm)
    Vy = cortante_secao_critica_bloco_kn(Nsd_kn, B, b_cm)
    # Seção crítica perpendicular a x tem largura B; perpendicular a y, largura A.
    s_x = 6.0 * Mx / (B * hc * hc) * 10.0
    s_y = 6.0 * My / (A * hc * hc) * 10.0
    s_Rd = sigma_ctRd(fck_mpa)
    t_Rd = tau_wRd(fck_mpa, 0.0)
    VRx = B * hc * t_Rd / 10.0
    VRy = A * hc * t_Rd / 10.0
    r_fx = seg.verificar_seguranca(s_Rd, s_x, "σct,x x σctRd", "24.6.2")
    r_fy = seg.verificar_seguranca(s_Rd, s_y, "σct,y x σctRd", "24.6.2")
    r_vx = seg.verificar_seguranca(VRx, Vx, "VSd,x x Ac·τwRd", "24.6.2")
    r_vy = seg.verificar_seguranca(VRy, Vy, "VSd,y x Ac·τwRd", "24.6.2")
    ok_f = r_fx.ok and r_fy.ok
    ok_v = r_vx.ok and r_vy.ok
    ok = ok_h and ok_f and ok_v
    razoes = (("flexão em x", s_x / s_Rd), ("flexão em y", s_y / s_Rd),
              ("cortante em x", Vx / VRx), ("cortante em y", Vy / VRy))
    nome, val = max(razoes, key=lambda t: t[1])
    if not ok_h:
        governante = f"Espessura média {_fmt(hm)} cm < 20 cm — não passa."
    else:
        governante = f"Governa: {nome}, razão {_fmt(val)}" + (" -> ok." if ok else " -> não passa.")
    memoria = (
        "24.6.2 — Bloco de fundação de concreto simples, apoiado no solo (PDF p. 230).",
        f"Espessura média = {_fmt(hm)} cm >= 20 cm -> {_p41_ok(ok_h)}.",
        f"h de cálculo = {_fmt(hc)} cm"
        + (" (lançado contra o solo, h − 5 cm, 24.5.3)" if lancado_contra_solo else "") + ".",
        f"Face da coluna, direção x: MSd = NSd·c²/(2A) = {_fmt(Mx)} kN·cm; "
        f"σct = 6M/(B·h²) = {_fmt(s_x)} MPa; VSd = NSd·c/A = {_fmt(Vx)} kN; "
        f"Ac·τwRd = {_fmt(VRx)} kN.",
        f"Face da coluna, direção y: MSd = NSd·c²/(2B) = {_fmt(My)} kN·cm; "
        f"σct = 6M/(A·h²) = {_fmt(s_y)} MPa; VSd = NSd·c/B = {_fmt(Vy)} kN; "
        f"Ac·τwRd = {_fmt(VRy)} kN.",
        f"σctRd = 0,85·fctd = {_fmt(s_Rd)} MPa; τwRd = 0,30·fctd = {_fmt(t_Rd)} MPa "
        f"(γc = {_fmt(GAMA_C_SIMPLES)}).",
    ) + r_fx.memoria + r_fy.memoria + r_vx.memoria + r_vy.memoria + (governante,)
    return ResultadoBlocoSimples(hc, Mx, My, s_x, s_y, s_Rd, Vx, Vy, VRx, VRy, t_Rd, hm,
                                 ok_h, ok_f, ok_v, ok, governante, memoria)


# ---------------------------------------------------------------------------
# 24.6.3 — Pilares (PDF p. 230)
# ---------------------------------------------------------------------------
def NRd_pilar_simples_kn(fck_mpa: float, b_cm: float, h_cm: float, l_cm: float,
                         alfa: float = ALFA_SEM_RESTRICAO) -> float:
    """Força normal resistente do pilar de concreto simples, kN (24.6.3 remetendo a 24.6.1, PDF p. 229-230).

    "Pilares de concreto simples devem ser calculados da mesma maneira que os
    pilares-parede (ver 24.6.1)": NRd = 0,63·fcd·Ac·[1 − (α·ℓ/32h)²], com
    Ac = b·h e h a menor dimensão da seção (a que dá a maior esbeltez, já que
    ℓ e α são os mesmos nas duas direções). Dimensões em cm.
    """
    b = _positivo(b_cm, "A dimensão b")
    h = _positivo(h_cm, "A dimensão h")
    return NRd_pilar_parede_kn(fck_mpa, b * h, min(b, h), l_cm, alfa)


def dentro_nucleo_central(ex_cm: float, ey_cm: float, hx_cm: float, hy_cm: float) -> bool:
    """Diz se a carga está dentro ou no limite do núcleo central de inércia da seção retangular (24.6.3, PDF p. 230).

    Núcleo central do retângulo hx × hy (resistência dos materiais): losango
    de semidiagonais hx/6 e hy/6, isto é, 6·|ex|/hx + 6·|ey|/hy <= 1. Na
    excentricidade reta, |e| <= h/6. O limite (igualdade) está dentro, com
    tolerância relativa de 1e-9.
    """
    hx = _positivo(hx_cm, "A dimensão hx")
    hy = _positivo(hy_cm, "A dimensão hy")
    return 6.0 * abs(float(ex_cm)) / hx + 6.0 * abs(float(ey_cm)) / hy <= 1.0 + _P41_TOL


def dimensao_minima_pilar_simples_cm(altura_cm: float) -> float:
    """Menor dimensão mínima do pilar de concreto simples, cm (24.6.3, PDF p. 230).

    "A menor dimensão de pilares deve ser 20 cm ou 1/10 de sua altura."
    Leitura adotada: o maior dos dois, max(20 cm; altura/10), a favor da
    segurança (a norma não diz qual prevalece). Altura em cm.
    """
    H = _nao_negativo(altura_cm, "A altura do pilar")
    return max(DIMENSAO_PILAR_MIN_CM, DIMENSAO_PILAR_REL * H)


@dataclass(frozen=True)
class ResultadoPilarSimples:
    """Resultado de ``verificar_pilar_simples`` (24.6.3)."""

    Nsd_kn: float
    NRd_kn: float
    nucleo_central: bool
    dimensao_min_cm: float
    ok_resistencia: bool
    ok_nucleo: bool
    ok_dimensao: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_pilar_simples(Nsd_kn: float, fck_mpa: float, b_cm: float, h_cm: float,
                            l_cm: float, alfa: float = ALFA_SEM_RESTRICAO,
                            ex_cm: float = 0.0, ey_cm: float = 0.0,
                            altura_cm: float | None = None) -> ResultadoPilarSimples:
    """Verifica o pilar de concreto simples sem ações laterais (24.6.3, PDF p. 230).

    - NSd <= NRd pelo método dos pilares-parede (``NRd_pilar_simples_kn``);
    - na ausência de ações laterais, a carga dentro ou no limite do núcleo
      central de inércia (``dentro_nucleo_central``; ex na direção de b, ey na
      de h);
    - menor dimensão >= max(20 cm; altura/10) (``dimensao_minima_pilar_simples_cm``;
      altura padrão = ℓ).
    Com ações laterais, use ``verificar_pilar_simples_acao_lateral``.
    NSd em kN, dimensões em cm, fck em MPa.
    """
    N = _positivo(Nsd_kn, "A força normal de compressão NSd")
    b = _positivo(b_cm, "A dimensão b")
    h = _positivo(h_cm, "A dimensão h")
    H = float(l_cm) if altura_cm is None else float(altura_cm)
    NRd = NRd_pilar_simples_kn(fck_mpa, b, h, l_cm, alfa)
    nuc = dentro_nucleo_central(ex_cm, ey_cm, b, h)
    d_min = dimensao_minima_pilar_simples_cm(H)
    ok_d = min(b, h) >= d_min * (1.0 - _P41_TOL)
    r = seg.verificar_seguranca(NRd, N, "NSd x NRd", "24.6.3")
    ok = r.ok and nuc and ok_d
    falhas = []
    if not r.ok:
        falhas.append("NSd > NRd")
    if not nuc:
        falhas.append("carga fora do núcleo central de inércia")
    if not ok_d:
        falhas.append(f"menor dimensão {_fmt(min(b, h))} cm < {_fmt(d_min)} cm")
    governante = (f"NSd/NRd = {_fmt(N / NRd) if NRd > 0 else 'inf'} -> ok." if ok
                  else "Não passa: " + "; ".join(falhas) + ".")
    memoria = (
        "24.6.3 — Pilar de concreto simples, calculado como pilar-parede (24.6.1) (PDF p. 230).",
        f"NRd = 0,63·fcd·b·h·[1 − (α·ℓ/32·hmin)²] = {_fmt(NRd)} kN "
        f"(b = {_fmt(b)} cm, h = {_fmt(h)} cm, ℓ = {_fmt(float(l_cm))} cm, α = {_fmt(float(alfa))}).",
    ) + r.memoria + (
        f"Núcleo central: 6·|ex|/b + 6·|ey|/h = "
        f"{_fmt(6 * abs(float(ex_cm)) / b + 6 * abs(float(ey_cm)) / h)} <= 1 -> {_p41_ok(nuc)}.",
        f"Menor dimensão: max(20 cm; altura/10) = {_fmt(d_min)} cm; min(b, h) = "
        f"{_fmt(min(b, h))} cm -> {_p41_ok(ok_d)}.",
        governante,
    )
    return ResultadoPilarSimples(N, NRd, nuc, d_min, r.ok, nuc, ok_d, ok, governante, memoria)


@dataclass(frozen=True)
class ResultadoSemTracao:
    """Resultado de ``verificar_pilar_simples_acao_lateral`` e ``verificar_sem_tracao``."""

    Nsd_kn: float
    Msd_kncm: float
    e_cm: float
    x_comprimido_cm: float
    sigma_max_mpa: float
    sigma_min_mpa: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def _tensoes_sem_tracao(N: float, M: float, b: float, h: float) -> tuple[float, float, float, float]:
    """(e, x comprimido, σmax, σmin elástico) de seção retangular sem resistência à tração, em cm e MPa."""
    e = abs(M) / N
    if e <= h / 6.0 * (1.0 + _P41_TOL):
        smax = N / (b * h) * (1.0 + 6.0 * e / h) * 10.0
        smin = N / (b * h) * (1.0 - 6.0 * e / h) * 10.0
        return e, h, smax, smin
    x = 3.0 * (h / 2.0 - e)
    if x <= 0.0:
        return e, 0.0, _p41_math.inf, N / (b * h) * (1.0 - 6.0 * e / h) * 10.0
    return e, x, 2.0 * N / (b * x) * 10.0, N / (b * h) * (1.0 - 6.0 * e / h) * 10.0


def verificar_pilar_simples_acao_lateral(Nsd_kn: float, Msd_kncm: float, b_cm: float,
                                         h_cm: float, fck_mpa: float) -> ResultadoSemTracao:
    """Verifica a seção de pilar de concreto simples com ações laterais, sem resistência à tração (24.6.3, PDF p. 230).

    "No caso de atuarem concomitantemente ações laterais, como o vento, as
    seções devem ser verificadas sem considerar a resistência à tração do
    concreto. Nesse caso a parte comprimida da seção deve conter o centroide.
    A máxima tensão de compressão no estado-limite último, com ações
    majoradas, não pode ultrapassar o valor de σcRd."

    Seção retangular b × h, flexão reta no plano de h, distribuição linear:
    e = MSd/NSd; se e <= h/6 a seção toda está comprimida e
    σmax = NSd/(b·h)·(1 + 6e/h); se e > h/6, x = 3·(h/2 − e) e
    σmax = 2·NSd/(b·x). A parte comprimida contém o centroide quando x >= h/2,
    isto é, e <= h/3. σcRd = 0,85·fcd (24.5.2.2). NSd em kN (compressão
    positiva), MSd em kN·cm, dimensões em cm. Flexão oblíqua não é tratada.
    """
    N = _positivo(Nsd_kn, "A força normal de compressão NSd")
    M = float(Msd_kncm)
    b = _positivo(b_cm, "A dimensão b")
    h = _positivo(h_cm, "A dimensão h")
    s_cRd = sigma_cRd(fck_mpa)
    e, x, smax, smin = _tensoes_sem_tracao(N, M, b, h)
    ok_c = x >= h / 2.0 * (1.0 - _P41_TOL)
    r = seg.verificar_seguranca(s_cRd, smax, "σc,max x σcRd", "24.6.3")
    ok = ok_c and r.ok
    if not ok_c:
        governante = (f"A parte comprimida (x = {_fmt(x)} cm) não contém o centroide "
                      f"(x < h/2 = {_fmt(h / 2)} cm) — não passa.")
    else:
        governante = f"σc,max/σcRd = {_fmt(smax / s_cRd)}" + (" -> ok." if ok else " -> não passa.")
    memoria = (
        "24.6.3 — Pilar de concreto simples com ações laterais, sem tração no concreto (PDF p. 230).",
        f"e = MSd/NSd = {_fmt(abs(M))}/{_fmt(N)} = {_fmt(e)} cm; h/6 = {_fmt(h / 6)} cm.",
        f"Parte comprimida x = {_fmt(x)} cm; contém o centroide (x >= h/2 = {_fmt(h / 2)} cm) -> "
        f"{_p41_ok(ok_c)}.",
        f"σc,max = {_fmt(smax)} MPa; σcRd = 0,85·fcd = {_fmt(s_cRd)} MPa.",
    ) + r.memoria + (governante,)
    return ResultadoSemTracao(N, M, e, x, smax, smin, ok, governante, memoria)


# ---------------------------------------------------------------------------
# 24.6.4 — Arcos (PDF p. 230)
# ---------------------------------------------------------------------------
def verificar_sem_tracao(Nsd_kn: float, Msd_kncm: float, b_cm: float,
                         h_cm: float) -> ResultadoSemTracao:
    """Verifica que a seção retangular do arco não tem tensão de tração no ELU (24.6.4, PDF p. 230).

    "Os arcos de concreto simples devem ser projetados de tal forma que, no
    estado-limite último, não apareçam tensões de tração em nenhuma seção
    transversal." Em regime linear: σ = NSd/(b·h) ∓ 6·MSd/(b·h²), e a
    condição é σmin >= 0, o que equivale a e = MSd/NSd <= h/6 (núcleo
    central). Na borda do núcleo σmin = 0 e a seção passa. NSd em kN
    (compressão positiva; tração levanta erro), MSd em kN·cm, dimensões em cm.
    """
    N = _positivo(Nsd_kn, "A força normal de compressão NSd do arco")
    M = float(Msd_kncm)
    b = _positivo(b_cm, "A dimensão b")
    h = _positivo(h_cm, "A dimensão h")
    A = b * h
    W = b * h * h / 6.0
    smax = (N / A + abs(M) / W) * 10.0
    smin = (N / A - abs(M) / W) * 10.0
    e = abs(M) / N
    ok = smin >= -_P41_TOL * smax
    governante = (f"σmin = {_fmt(smin)} MPa >= 0 -> ok." if ok
                  else f"σmin = {_fmt(smin)} MPa < 0: tração na seção — não passa.")
    memoria = (
        "24.6.4 — Arco de concreto simples: sem tração no ELU (PDF p. 230).",
        f"σ = NSd/A ∓ MSd/W = {_fmt(N)}/{_fmt(A)} ∓ {_fmt(abs(M))}/{_fmt(W)} (× 10): "
        f"σmax = {_fmt(smax)} MPa, σmin = {_fmt(smin)} MPa.",
        f"e = {_fmt(e)} cm; núcleo central h/6 = {_fmt(h / 6)} cm.",
        governante,
    )
    return ResultadoSemTracao(N, M, e, h if ok else max(0.0, 3.0 * (h / 2.0 - e)), smax, smin, ok,
                              governante, memoria)


@dataclass(frozen=True)
class ResultadoArcoSemTracao:
    """Resultado de ``verificar_arco_sem_tracao`` (24.6.4)."""

    secoes: tuple[ResultadoSemTracao, ...]
    indice_critico: int
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_arco_sem_tracao(esforcos, b_cm: float, h_cm: float) -> ResultadoArcoSemTracao:
    """Aplica ``verificar_sem_tracao`` a todas as seções do arco (24.6.4, PDF p. 230).

    ``esforcos``: sequência de pares (NSd em kN, MSd em kN·cm), uma por seção
    ao longo do eixo; seção constante b × h (cm). A seção crítica é a de menor
    σmin. O arco passa se nenhuma seção tiver tração.
    """
    res = tuple(verificar_sem_tracao(N, M, b_cm, h_cm) for N, M in esforcos)
    if not res:
        raise FaixaNormativaError("Informe ao menos uma seção do arco.")
    i = min(range(len(res)), key=lambda k: res[k].sigma_min_mpa)
    ok = all(r.ok for r in res)
    governante = (f"Seção crítica {i}: σmin = {_fmt(res[i].sigma_min_mpa)} MPa"
                  + (" -> ok." if ok else " -> não passa."))
    memoria = (f"24.6.4 — Arco: {len(res)} seções verificadas sem tração (PDF p. 230).",
               ) + res[i].memoria + (governante,)
    return ResultadoArcoSemTracao(res, i, ok, governante, memoria)


def momento_2a_ordem_max_arco_kncm(M1d_kncm: float) -> float:
    """Maior momento com efeitos de 2ª ordem admitido no arco de concreto simples, kN·cm (24.6.4, PDF p. 230).

    "podendo ser considerado um aumento de momentos fletores por efeitos de 2ª
    ordem até um máximo de 10 % acima dos momentos de 1ª ordem":
    M2d,max = 1,10·|M1d|. M em kN·cm.
    """
    return MAJORACAO_2A_ORDEM_ARCO_MAX * abs(float(M1d_kncm))


@dataclass(frozen=True)
class ResultadoMajoracao2aOrdemArco:
    """Resultado de ``verificar_majoracao_2a_ordem_arco`` (24.6.4)."""

    M1d_kncm: float
    M2d_kncm: float
    M2d_max_kncm: float
    majoracao: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_majoracao_2a_ordem_arco(M1d_kncm: float,
                                      M2d_kncm: float) -> ResultadoMajoracao2aOrdemArco:
    """Confere o teto de 10 % dos efeitos de 2ª ordem no arco de concreto simples (24.6.4, PDF p. 230).

    Condição: |M2d| <= 1,10·|M1d|. Majoração acima de 10 % reprova (ok =
    False); a função **não** trunca o momento em 1,10·M1d, porque isso
    esconderia um arco instável — a norma exige garantir a estabilidade global
    e só admite considerar até 10 %. M em kN·cm (M1d ≠ 0).
    """
    M1 = abs(float(M1d_kncm))
    M2 = abs(float(M2d_kncm))
    if M1 == 0.0:
        raise FaixaNormativaError("M1d = 0: a majoração relativa de 24.6.4 não se define.")
    Mmax = momento_2a_ordem_max_arco_kncm(M1)
    r = seg.verificar_seguranca(Mmax, M2, "M2d x 1,10·M1d", "24.6.4")
    maj = M2 / M1 - 1.0
    governante = (f"Majoração de 2ª ordem = {_fmt(100 * maj)} %"
                  + (" <= 10 % -> ok." if r.ok else " > 10 % — não passa."))
    memoria = (
        "24.6.4 — Arco: aumento de momentos por efeitos de 2ª ordem de até 10 % (PDF p. 230).",
        f"M2d,max = 1,10·M1d = 1,10 × {_fmt(M1)} = {_fmt(Mmax)} kN·cm; M2d = {_fmt(M2)} kN·cm.",
    ) + r.memoria + (governante,)
    return ResultadoMajoracao2aOrdemArco(M1, M2, Mmax, maj, r.ok, governante, memoria)


# === F3: núcleo central de inércia — seção poligonal genérica (24.6.3, fechamento do P41) ===
# Fecha os dois pontos que ficaram de fora do P41 (ver observação do pacote):
# "carga dentro do núcleo central" para uma seção QUALQUER (não só retangular)
# e a verificação sem tração com excentricidade nas DUAS direções ao mesmo
# tempo (flexão oblíqua com ações laterais). A 6118, em 24.6.3, só dá a
# condição física (carga dentro do núcleo; ou parte comprimida contendo o
# centroide e σc,max <= σcRd) — nenhuma das duas contas tem fórmula fechada
# geral na norma para seção qualquer, e o método abaixo é da biblioteca,
# resolvido por primeiros princípios de Resistência dos Materiais (como a
# seção 3.1 do plano manda para análise sem valor tabelado: conferido contra
# solução fechada e o equilíbrio checado nos testes). Tudo em cm e kN;
# tensão em MPa (1 kN/cm² = 10 MPa, conversão dentro de cada função).
import math as _f3_math

_F3_TOL = 1e-9


def _f3_propriedades_poligono_cm(poligono):
    """(A_cm2, cx_cm, cy_cm, Ixx_cm4, Iyy_cm4, Ixy_cm4) de um polígono, pelo somatório de Green.

    ``poligono``: sequência de (x, y) em cm, convexo, em qualquer sentido, sem
    repetir o primeiro ponto no fim. Ixx = ∫y²dA, Iyy = ∫x²dA, Ixy = ∫xy dA,
    todos já centrados no centroide do próprio polígono (translação pelo
    teorema dos eixos paralelos). Sentido horário troca o sinal do somatório
    inteiro (área e momentos); a área devolvida é sempre positiva porque o
    sinal é corrigido no final, e o centroide não muda (numerador e
    denominador trocam de sinal junto).
    """
    pts = [(float(x), float(y)) for x, y in poligono]
    n = len(pts)
    if n < 3:
        raise ValueError("O polígono da seção precisa de pelo menos 3 vértices.")
    A2 = Cx = Cy = Ixx_o = Iyy_o = Ixy_o = 0.0
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        cr = x0 * y1 - x1 * y0
        A2 += cr
        Cx += (x0 + x1) * cr
        Cy += (y0 + y1) * cr
        Ixx_o += (y0 * y0 + y0 * y1 + y1 * y1) * cr
        Iyy_o += (x0 * x0 + x0 * x1 + x1 * x1) * cr
        Ixy_o += (x0 * y1 + 2.0 * x0 * y0 + 2.0 * x1 * y1 + x1 * y0) * cr
    A = A2 / 2.0
    if abs(A) < 1e-9:
        raise ValueError("Polígono da seção degenerado: área nula.")
    cx = Cx / (6.0 * A)
    cy = Cy / (6.0 * A)
    Ixx = Ixx_o / 12.0 - A * cy * cy
    Iyy = Iyy_o / 12.0 - A * cx * cx
    Ixy = Ixy_o / 24.0 - A * cx * cy
    sinal = 1.0 if A >= 0.0 else -1.0
    return abs(A), cx, cy, Ixx * sinal, Iyy * sinal, Ixy * sinal


def _f3_girar(ponto, theta):
    x, y = ponto
    c, s = _f3_math.cos(theta), _f3_math.sin(theta)
    return (c * x + s * y, -s * x + c * y)


def _f3_girar_inv(ponto, theta):
    return _f3_girar(ponto, -theta)


def _f3_base_principal(poligono, A, cx, cy, Ixx, Iyy, Ixy):
    """Ângulo principal (rad), o polígono centrado e girado para os eixos principais, e (Iu, Iv).

    Iu = ∫v²dA (em torno do eixo u), Iv = ∫u²dA (em torno do eixo v) — depois
    de girar, o produto de inércia sai ~0 (conferido nos testes).
    """
    if abs(Ixx - Iyy) < 1e-9 and abs(Ixy) < 1e-9:
        theta = 0.0
    else:
        theta = 0.5 * _f3_math.atan2(-2.0 * Ixy, Ixx - Iyy)
    centrado = [(float(x) - cx, float(y) - cy) for x, y in poligono]
    girado = [_f3_girar(p, theta) for p in centrado]
    _, _, _, Iu, Iv, _ = _f3_propriedades_poligono_cm(girado)
    return theta, girado, Iu, Iv


def dentro_nucleo_central_poligono(ex_cm: float, ey_cm: float, poligono) -> bool:
    """Diz se a carga está dentro (ou no limite) do núcleo central de inércia de uma seção poligonal qualquer (24.6.3, PDF p. 230).

    Generaliza ``dentro_nucleo_central`` (só retângulo) para qualquer seção
    poligonal convexa: com N unitário aplicado em (ex, ey), a tensão em cada
    ponto (u, v) nos eixos principais é σ = 1/A + eu·u/Iv + ev·v/Iu (flexão
    composta oblíqua elástica); como σ é afim em (u, v), o mínimo sobre a
    seção ocorre num vértice do polígono (convexo) — a carga está dentro do
    núcleo sse σ >= 0 em todos os vértices. Para o retângulo, reproduz
    exatamente 6·|ex|/hx + 6·|ey|/hy <= 1 (``dentro_nucleo_central``, conferido
    nos testes). Excentricidades em cm, relativas ao centroide do polígono.
    """
    A, cx, cy, Ixx, Iyy, Ixy = _f3_propriedades_poligono_cm(poligono)
    theta, girado, Iu, Iv = _f3_base_principal(poligono, A, cx, cy, Ixx, Iyy, Ixy)
    eu, ev = _f3_girar((float(ex_cm), float(ey_cm)), theta)
    tol = _F3_TOL / A
    for (u, v) in girado:
        if 1.0 / A + eu * u / Iv + ev * v / Iu < -tol:
            return False
    return True


def nucleo_central_poligono_cm(poligono) -> tuple[tuple[float, float], ...]:
    """Vértices do núcleo central de inércia de uma seção poligonal convexa qualquer, cm (24.6.3, PDF p. 230).

    Para cada aresta do polígono (candidata a reta neutra que zera a tensão
    ali), o ponto conjugado — a excentricidade que faz exatamente aquela reta
    ser a de tensão nula, com a seção toda comprimida — é, nos eixos
    principais (u, v): eu = −Iv·nu/(A·a), ev = −Iu·nv/(A·a), com (nu, nv) a
    normal unitária da aresta apontando para fora e a a distância do
    centroide à reta que contém a aresta (relação clássica de reciprocidade
    entre reta neutra e núcleo central — Resistência dos Materiais; conferida
    no retângulo contra h/6 e b/6 nos testes). Os vértices do núcleo saem na
    mesma ordem das arestas, no referencial do polígono de entrada.

    ``poligono``: sequência de (x, y) em cm, convexo, em qualquer sentido.
    Levanta ``ValueError`` se alguma aresta passar pelo centroide (núcleo
    central infinito, seção não fechada/convexa nesse ponto).
    """
    A, cx, cy, Ixx, Iyy, Ixy = _f3_propriedades_poligono_cm(poligono)
    theta, girado, Iu, Iv = _f3_base_principal(poligono, A, cx, cy, Ixx, Iyy, Ixy)
    n = len(girado)
    pontos = []
    for i in range(n):
        x0, y0 = girado[i]
        x1, y1 = girado[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        comp = _f3_math.hypot(dx, dy)
        if comp < 1e-9:
            continue
        nx, ny = dy / comp, -dx / comp
        a = x0 * nx + y0 * ny
        if a < 0.0:
            nx, ny, a = -nx, -ny, -a
        if a < 1e-9 * max(1.0, comp):
            raise ValueError("Aresta do polígono passa pelo centroide: núcleo central não definido "
                             "para esta seção (24.6.3).")
        eu = -Iv * nx / (A * a)
        ev = -Iu * ny / (A * a)
        pontos.append(_f3_girar_inv((eu, ev), theta))
    return tuple((px + cx, py + cy) for px, py in pontos)


def _f3_clip_semiplano(poligono, nx, ny, a, tol=1e-9):
    """Recorta ``poligono`` (relativo ao centroide) no semiplano nx·x+ny·y >= a (Sutherland-Hodgman)."""
    n = len(poligono)
    saida = []

    def valor(p):
        return p[0] * nx + p[1] * ny - a

    for i in range(n):
        atual, prox = poligono[i], poligono[(i + 1) % n]
        va, vp = valor(atual), valor(prox)
        a_dentro, p_dentro = va >= -tol, vp >= -tol
        if a_dentro:
            saida.append(atual)
        if a_dentro != p_dentro:
            t = va / (va - vp)
            saida.append((atual[0] + t * (prox[0] - atual[0]), atual[1] + t * (prox[1] - atual[1])))
    return saida


def _f3_resultante_pq(poligono_centrado, p, q):
    """Ponto de aplicação (x, y), a área comprimida, a profundidade do centroide dela e a
    profundidade máxima (fibra mais comprimida), tudo relativo ao centroide da seção, para
    a distribuição linear de tensão nula na reta p·x+q·y=1 (lado comprimido: p·x+q·y <= 1,
    que contém sempre a origem — a condição de 24.6.3 de a parte comprimida conter o
    centroide vem de graça dessa forma da reta). ``None`` se a reta não deixa contorno
    comprimido válido (fora do polígono, ou profundidade do centroide não positiva).

    O ponto de aplicação sai por analogia com o centro de pressão hidrostático sobre uma
    superfície plana submersa (mesma matemática: pressão proporcional à profundidade a
    partir de uma "superfície livre", aqui a reta neutra): com (u, d) as coordenadas
    tangencial e de profundidade da área comprimida, dR = dc + Idd/(dc·Ac) e
    uR = uc + Iud/(dc·Ac) — Idd e Iud são os momentos de inércia e produto de inércia da
    área comprimida em torno do próprio centroide dela (conferido contra a solução fechada
    do retângulo nos testes).
    """
    norma = _f3_math.hypot(p, q)
    if norma < 1e-13:
        return None
    nx, ny = p / norma, q / norma
    a = 1.0 / norma
    recorte = _f3_clip_semiplano(poligono_centrado, -nx, -ny, -a)
    if len(recorte) < 3:
        return None
    tx, ty = -ny, nx
    uv = [(px * tx + py * ty, a - (px * nx + py * ny)) for px, py in recorte]
    Ac, uc, dc, Idd, _, Iud = _f3_propriedades_poligono_cm(uv)
    if dc <= 1e-9 or Ac <= 1e-9:
        return None
    d_r = dc + Idd / (dc * Ac)
    u_r = uc + Iud / (dc * Ac)
    v_r = a - d_r
    Rx = v_r * nx + u_r * tx
    Ry = v_r * ny + u_r * ty
    d_max = max(a - (px * nx + py * ny) for px, py in recorte)
    return Rx, Ry, Ac, dc, d_max


def _f3_resolver_eixo_neutro(poligono_centrado, A, Iu_Iv_theta, ex_cm, ey_cm,
                             tol_cm=1e-7, max_iter=60):
    """Newton amortecido em (p, q) até a resultante de ``_f3_resultante_pq`` cair em (ex, ey).

    Chute inicial pela relação elástica de seção cheia (a mesma do núcleo
    central, sem o recorte): serve mesmo fora do núcleo porque a reta que
    ela indica já aponta na direção certa. ``RuntimeError`` quando não existe
    reta com a parte comprimida contendo o centroide para essa excentricidade
    (o Newton fica mal-condicionado bem nessa fronteira, e é isso que o
    detecta — conferido contra e <= h/3 do retângulo nos testes).

    Limite conhecido: (p, q) são os coeficientes da reta p·x+q·y=1, isto é,
    (nx, ny)/a com a a distância do centroide à reta — essa forma não
    representa uma reta que passe exatamente pelo centroide (a = 0 ⟹ p, q →
    ∞). Isso só importa bem na fronteira em que a área comprimida é exatamente
    metade da seção (o e = h/3 do retângulo, x = h/2): perto dela a função
    ainda converge (testada até 0,01 cm da fronteira), mas exatamente nela
    ``RuntimeError`` é levantado e o chamador vê ``ok = False`` — mesmo a
    excentricidade sendo, no limite, admissível. Na prática de projeto isso
    não é uma perda: ninguém dimensiona exatamente no limite matemático de
    uma verificação sem tração, sempre com alguma folga.
    """
    theta, Iu, Iv = Iu_Iv_theta
    eu, ev = _f3_girar((float(ex_cm), float(ey_cm)), theta)
    pu = -eu * A / Iv if abs(Iv) > 1e-9 else 0.0
    pv = -ev * A / Iu if abs(Iu) > 1e-9 else 0.0
    p, q = _f3_girar_inv((pu, pv), theta)
    h = 1e-6
    for _ in range(max_iter):
        r0 = _f3_resultante_pq(poligono_centrado, p, q)
        if r0 is None:
            raise RuntimeError("Reta neutra inicial fora do polígono.")
        Rx, Ry = r0[0], r0[1]
        Fx, Fy = Rx - float(ex_cm), Ry - float(ey_cm)
        if abs(Fx) < tol_cm and abs(Fy) < tol_cm:
            return p, q, r0
        passo = h
        rp = _f3_resultante_pq(poligono_centrado, p + passo, q)
        rq = _f3_resultante_pq(poligono_centrado, p, q + passo)
        if rp is None or rq is None:
            passo = h * 10.0
            rp = _f3_resultante_pq(poligono_centrado, p + passo, q)
            rq = _f3_resultante_pq(poligono_centrado, p, q + passo)
        if rp is None or rq is None:
            raise RuntimeError("Não foi possível estimar a jacobiana perto da reta neutra: carga "
                               "provavelmente fora da região onde a parte comprimida contém o "
                               "centroide (24.6.3).")
        dFxdp, dFydp = (rp[0] - Rx) / passo, (rp[1] - Ry) / passo
        dFxdq, dFydq = (rq[0] - Rx) / passo, (rq[1] - Ry) / passo
        det = dFxdp * dFydq - dFxdq * dFydp
        if abs(det) < 1e-14:
            raise RuntimeError("Sistema mal-condicionado perto da reta neutra: carga provavelmente "
                               "fora da região onde a parte comprimida contém o centroide (24.6.3).")
        dp = (Fx * dFydq - Fy * dFxdq) / det
        dq = (Fy * dFxdp - Fx * dFydp) / det
        amortecimento = 1.0
        candidato = None
        for _tentativa in range(30):
            teste = (p - amortecimento * dp, q - amortecimento * dq)
            if _f3_resultante_pq(poligono_centrado, *teste) is not None:
                candidato = teste
                break
            amortecimento *= 0.5
        if candidato is None:
            raise RuntimeError("Iteração da reta neutra não convergiu: carga provavelmente fora da "
                               "região onde a parte comprimida contém o centroide (24.6.3).")
        p, q = candidato
    raise RuntimeError("Iteração da reta neutra não convergiu no número máximo de passos (24.6.3).")


@dataclass(frozen=True)
class ResultadoSemTracaoPoligono:
    """Resultado de ``verificar_secao_sem_tracao_poligono`` (24.6.3, seção poligonal qualquer)."""

    Nsd_kn: float
    ex_cm: float
    ey_cm: float
    dentro_nucleo: bool
    area_bruta_cm2: float
    area_comprimida_cm2: float
    sigma_max_mpa: float
    sigma_cRd_mpa: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_secao_sem_tracao_poligono(Nsd_kn: float, ex_cm: float, ey_cm: float, poligono,
                                        fck_mpa: float) -> ResultadoSemTracaoPoligono:
    """Verifica seção poligonal convexa qualquer, sem tração, com excentricidade em uma ou duas direções (24.6.3, PDF p. 230).

    Generaliza, para **qualquer seção poligonal convexa** e **excentricidade
    nas duas direções ao mesmo tempo** (flexão oblíqua), o que o P41 deixou de
    fora: ``verificar_pilar_simples`` (só sem ações laterais) e
    ``verificar_pilar_simples_acao_lateral`` (só retângulo, uma direção). A
    6118 dá, em 24.6.3, só a condição física: "as seções devem ser
    verificadas sem considerar a resistência à tração do concreto[...] a
    parte comprimida da seção deve conter o centroide[...] a máxima tensão de
    compressão[...] não pode ultrapassar o valor de σcRd." A norma não
    prescreve o método para seção qualquer com as duas excentricidades — o
    que segue é da biblioteca, por primeiros princípios (ver
    ``_f3_resultante_pq`` e ``_f3_resolver_eixo_neutro``), do jeito que a
    seção 3.1 do plano manda para análise sem valor tabelado: conferido
    contra solução fechada (reduz a ``dentro_nucleo_central_poligono`` dentro
    do núcleo, e ao caso uniaxial retangular de
    ``verificar_pilar_simples_acao_lateral`` quando ex ou ey é zero — os dois
    nos testes) e com o equilíbrio da reta neutra checado a cada chamada
    (é exatamente o que ``_f3_resolver_eixo_neutro`` resolve).

    - **Carga dentro do núcleo** (``dentro_nucleo_central_poligono``): seção
      toda comprimida, σ = N·[1/A + eu·u/Iv + ev·v/Iu] nos eixos principais
      (u, v); o máximo está num vértice do polígono.
    - **Carga fora do núcleo**: só parte da seção resiste; a reta neutra é
      achada por ``_f3_resolver_eixo_neutro`` e a tensão máxima (na fibra mais
      comprimida) sai como no centro de pressão hidrostático: σc,max =
      N·dmax/(Ac·dc), com dc a profundidade do centroide da área comprimida e
      dmax a da fibra mais funda, ambas a partir da reta neutra. Sem reta
      possível (excentricidade grande demais para a parte comprimida ainda
      conter o centroide), ``ok = False``. Bem na fronteira exata em que a
      área comprimida seria metade da seção (a reta neutra passando pelo
      centroide), a busca da reta também devolve ``ok = False`` por limite
      numérico do método (ver ``_f3_resolver_eixo_neutro``), mesmo sendo o
      último ponto ainda admissível — não afeta o projeto na prática (ninguém
      dimensiona exatamente nesse limite).

    ``poligono``: sequência de (x, y) em cm, convexo, em qualquer sentido,
    relativo a qualquer origem (a função acha o centroide). ``Nsd_kn`` de
    compressão (> 0); ``ex_cm``/``ey_cm`` a excentricidade da força em torno
    do centroide; ``fck_mpa`` para σcRd = 0,85·fcd (``sigma_cRd``).
    """
    N = _positivo(Nsd_kn, "A força normal de compressão NSd")
    ex, ey = float(ex_cm), float(ey_cm)
    A, cx, cy, Ixx, Iyy, Ixy = _f3_propriedades_poligono_cm(poligono)
    s_cRd = sigma_cRd(fck_mpa)
    theta, girado, Iu, Iv = _f3_base_principal(poligono, A, cx, cy, Ixx, Iyy, Ixy)
    eu, ev = _f3_girar((ex, ey), theta)
    dentro = dentro_nucleo_central_poligono(ex, ey, poligono)
    if dentro:
        smax_rel = max(1.0 / A + eu * u / Iv + ev * v / Iu for u, v in girado)
        smax = N * smax_rel * 10.0
        r = seg.verificar_seguranca(s_cRd, smax, "σc,max x σcRd", "24.6.3")
        governante = ("Carga dentro do núcleo central: seção toda comprimida; "
                      f"σc,max/σcRd = {_fmt(smax / s_cRd)}" + (" -> ok." if r.ok else " -> não passa."))
        memoria = (
            "24.6.3 — Seção poligonal, carga dentro do núcleo central: flexão composta oblíqua "
            "elástica, seção toda comprimida (PDF p. 230).",
            f"eu = {_fmt(eu)} cm, ev = {_fmt(ev)} cm (eixos principais); "
            f"σc,max = N·max[1/A + eu·u/Iv + ev·v/Iu] = {_fmt(smax)} MPa.",
        ) + r.memoria + (governante,)
        return ResultadoSemTracaoPoligono(N, ex, ey, True, A, A, smax, s_cRd, r.ok, governante, memoria)
    centrado = [(float(x) - cx, float(y) - cy) for x, y in poligono]
    try:
        _, _, r0 = _f3_resolver_eixo_neutro(centrado, A, (theta, Iu, Iv), ex, ey)
    except RuntimeError:
        governante = ("Não passa: não existe reta neutra para esta excentricidade com a parte "
                      "comprimida contendo o centroide (24.6.3).")
        memoria = (
            "24.6.3 — Seção poligonal com ações laterais, sem tração no concreto (PDF p. 230).",
            f"ex = {_fmt(ex)} cm, ey = {_fmt(ey)} cm: fora da região onde existe reta neutra com a "
            "parte comprimida contendo o centroide.",
            governante,
        )
        return ResultadoSemTracaoPoligono(N, ex, ey, False, A, 0.0, float("inf"), s_cRd, False,
                                          governante, memoria)
    _, _, area_c, dc, d_max = r0
    smax = N * d_max / (area_c * dc) * 10.0
    r = seg.verificar_seguranca(s_cRd, smax, "σc,max x σcRd", "24.6.3")
    governante = f"σc,max/σcRd = {_fmt(smax / s_cRd)}" + (" -> ok." if r.ok else " -> não passa.")
    memoria = (
        "24.6.3 — Seção poligonal com ações laterais, sem tração no concreto (PDF p. 230); reta "
        "neutra achada por iteração (método da biblioteca — ver docstring).",
        f"Área comprimida = {_fmt(area_c)} cm² (bruta = {_fmt(A)} cm²); σc,max = {_fmt(smax)} MPa.",
    ) + r.memoria + (governante,)
    return ResultadoSemTracaoPoligono(N, ex, ey, False, A, area_c, smax, s_cRd, r.ok, governante, memoria)
