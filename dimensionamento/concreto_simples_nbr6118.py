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
