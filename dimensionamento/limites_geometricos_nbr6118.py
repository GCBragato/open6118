"""Limites geométricos e coeficiente γn — ABNT NBR 6118:2026, Seção 13.2 e 22.2.

Reúne os limites-dimensões de 13.2 (vigas e vigas-parede, pilares e
pilares-parede, lajes maciças, lajes nervuradas, furos e aberturas,
canalizações embutidas) e o coeficiente adicional γn que a norma manda
aplicar aos esforços solicitantes de cálculo de elementos esbeltos críticos
(13.2.3, Tabela 13.1; 13.2.4.1, Tabela 13.2; 22.2), com a remissão de 11.7.1.

As Tabelas 13.1 (pilares, em b) e 13.2 (lajes em balanço, em h) têm a mesma
forma γn = 1,95 − 0,05·dimensão; as duas funções públicas (``gama_n_pilar``
e ``gama_n_laje_balanco``) usam a mesma função interna, ``_gama_n_por_dimensao``.

``gama_n_laje_balanco`` morava em ``lajes_nbr6118.py``; agora mora aqui, e
``lajes_nbr6118.gama_n_laje_balanco`` é uma reexportação desta mesma função
(sem quebra de import).

Convenções: geometria em cm; página do PDF citada em cada função (impressa
= PDF − 18). Fora da faixa de validade de uma fórmula, as funções levantam
``FaixaNormativaError`` (subclasse de ``ValueError``, importada do núcleo).
Função de verificação devolve ``@dataclass(frozen=True)`` com ``ok``,
``governante`` e ``memoria`` (a memória de cálculo), em vez de levantar erro.
"""

from __future__ import annotations

from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError


# ---------------------------------------------------------------------------
# 13.2.2 — Vigas e vigas-parede (PDF p. 93)
# ---------------------------------------------------------------------------
LARGURA_MINIMA_VIGA_CM = 12.0
LARGURA_MINIMA_VIGA_PAREDE_CM = 15.0
LARGURA_MINIMA_ABSOLUTA_EXCEPCIONAL_CM = 10.0


def largura_minima_viga_cm(viga_parede: bool = False, excepcional: bool = False) -> float:
    """Largura mínima da seção transversal de viga ou viga-parede (13.2.2, p. 93).

    12 cm para viga comum, 15 cm para viga-parede. Em casos excepcionais,
    a norma admite reduzir esses limites até o mínimo absoluto de 10 cm,
    desde que respeitadas simultaneamente 13.2.2 a) (alojamento das
    armaduras e suas interferências com armaduras de outros elementos,
    respeitando espaçamentos e cobrimentos) e b) (lançamento e vibração do
    concreto conforme a ABNT NBR 14931) — condições que esta função não
    verifica, por dependerem do detalhamento.

    Devolve a largura mínima exigida, em cm; o chamador confere ``bw`` contra
    esse valor.
    """
    if excepcional:
        return LARGURA_MINIMA_ABSOLUTA_EXCEPCIONAL_CM
    return LARGURA_MINIMA_VIGA_PAREDE_CM if viga_parede else LARGURA_MINIMA_VIGA_CM


# ---------------------------------------------------------------------------
# 13.2.3 e 13.2.4.1 — Coeficiente adicional γn (Tabelas 13.1 e 13.2, p. 93-94)
# ---------------------------------------------------------------------------
GAMA_N_DIMENSAO_LIMITE_CM = 19.0            # a partir daqui, gama_n = 1,00
DIMENSAO_MINIMA_PILAR_CM = 14.0             # 13.2.3: abaixo disso, pilar proibido
AREA_MINIMA_PILAR_CM2 = 360.0               # 13.2.3: área mínima absoluta
ESPESSURA_MINIMA_LAJE_BALANCO_CM = 10.0     # 13.2.4.1 c)


def _gama_n_por_dimensao(dim_cm: float, minimo_absoluto_cm: float, item: str) -> float:
    """γn = 1,95 − 0,05·dim para minimo_absoluto <= dim < 19 cm; 1,00 para
    dim >= 19 cm (forma comum às Tabelas 13.1 e 13.2). Abaixo do mínimo
    absoluto da norma, a tabela não define o caso e a função levanta
    ``FaixaNormativaError``.
    """
    dim = float(dim_cm)
    if dim < minimo_absoluto_cm - 1e-9:
        raise FaixaNormativaError(
            f"dimensão = {dim:g} cm abaixo do mínimo de {minimo_absoluto_cm:g} cm "
            f"que a NBR 6118:2026 {item} admite."
        )
    if dim >= GAMA_N_DIMENSAO_LIMITE_CM - 1e-9:
        return 1.0
    return 1.95 - 0.05 * dim


def gama_n_pilar(b_cm: float) -> float:
    """Coeficiente adicional γn para pilares e pilares-parede (13.2.3,
    Tabela 13.1, PDF p. 94).

    γn = 1,95 − 0,05·b para 14 <= b < 19 cm; γn = 1,00 para b >= 19 cm.
    b é a menor dimensão da seção transversal, em cm. Abaixo de 14 cm a
    norma não permite pilar/pilar-parede maciço (13.2.3), e a função
    levanta ``FaixaNormativaError``.
    """
    return _gama_n_por_dimensao(b_cm, DIMENSAO_MINIMA_PILAR_CM, "13.2.3")


def gama_n_laje_balanco(h_cm: float) -> float:
    """Coeficiente adicional γn para laje em balanço (13.2.4.1, Tabela 13.2,
    PDF p. 94).

    γn = 1,95 − 0,05·h para 10 <= h < 19 cm; γn = 1,00 para h >= 19 cm. A
    NBR 6118 13.2.4.1 c) exige espessura mínima de 10 cm para laje em
    balanço; abaixo disso a Tabela 13.2 não se aplica e a função levanta
    ``FaixaNormativaError``.
    """
    return _gama_n_por_dimensao(h_cm, ESPESSURA_MINIMA_LAJE_BALANCO_CM, "13.2.4.1 c)")


def gama_n_esbeltos(tipo: str, dimensao_cm: float) -> float:
    """γn para elementos esbeltos críticos com espessura < 19 cm (11.7.1,
    PDF p. 84): remissão a 13.2.3 (pilares/pilares-parede) e a 13.2.4.1
    (lajes em balanço) — "os esforços solicitantes de cálculo devem ser
    multiplicados pelo coeficiente de ajustamento γn".

    Despacha para ``gama_n_pilar`` ou ``gama_n_laje_balanco`` conforme
    ``tipo`` ('pilar', 'pilar-parede' ou 'laje-balanco'), sem reimplementar
    a fórmula. Pura conveniência para quem só tem o elemento e a dimensão,
    sem saber qual tabela consultar.
    """
    chave = nbr._chave(tipo)
    if chave in ("pilar", "pilarparede"):
        return gama_n_pilar(dimensao_cm)
    if chave in ("lajebalanco", "laje"):
        return gama_n_laje_balanco(dimensao_cm)
    raise ValueError(
        f"tipo desconhecido: {tipo!r}. Use 'pilar', 'pilar-parede' ou 'laje-balanco'."
    )


@dataclass(frozen=True)
class ResultadoDimensaoPilar:
    b_cm: float
    Ac_cm2: float
    gama_n: float
    b_minimo_ok: bool
    area_minima_ok: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_dimensao_pilar(b_cm: float, Ac_cm2: float) -> ResultadoDimensaoPilar:
    """Verifica a dimensão mínima e a área mínima de pilar/pilar-parede
    maciço (13.2.3, PDF p. 93), com o γn da Tabela 13.1 quando 14 <= b < 19 cm.

    - b >= 19 cm: sem majoração (γn = 1,00);
    - 14 <= b < 19 cm: permitido em casos especiais, com os esforços
      solicitantes de cálculo majorados por γn (Tabela 13.1);
    - b < 14 cm: reprovado — a norma não permite essa dimensão;
    - Ac < 360 cm²: reprovado em qualquer caso (área mínima absoluta).
    """
    b = float(b_cm)
    Ac = float(Ac_cm2)
    memoria: list[str] = []

    b_minimo_ok = b >= DIMENSAO_MINIMA_PILAR_CM - 1e-9
    if b >= GAMA_N_DIMENSAO_LIMITE_CM - 1e-9:
        gn = 1.0
        memoria.append(f"13.2.3: b = {b:g} cm >= 19 cm -> sem majoração (γn = 1,00).")
    elif b_minimo_ok:
        gn = gama_n_pilar(b)
        memoria.append(
            f"13.2.3, Tabela 13.1: 14 <= b = {b:g} < 19 cm -> "
            f"γn = 1,95 - 0,05*{b:g} = {gn:.3f}."
        )
    else:
        gn = float("nan")
        memoria.append(
            f"13.2.3: b = {b:g} cm < 14 cm — dimensão não permitida para "
            "pilar/pilar-parede maciço."
        )

    area_minima_ok = Ac + 1e-9 >= AREA_MINIMA_PILAR_CM2
    memoria.append(
        f"13.2.3: Ac = {Ac:g} cm² "
        f"{'>= 360 cm² -> ok.' if area_minima_ok else '< 360 cm² -> reprovado.'}"
    )

    ok = b_minimo_ok and area_minima_ok
    if ok:
        governante = "atende 13.2.3"
    elif not b_minimo_ok and not area_minima_ok:
        governante = "dimensão mínima b >= 14 cm e área mínima Ac >= 360 cm² (13.2.3)"
    elif not b_minimo_ok:
        governante = "dimensão mínima b >= 14 cm (13.2.3)"
    else:
        governante = "área mínima Ac >= 360 cm² (13.2.3)"

    return ResultadoDimensaoPilar(
        b_cm=b, Ac_cm2=Ac, gama_n=gn, b_minimo_ok=b_minimo_ok,
        area_minima_ok=area_minima_ok, ok=ok, governante=governante,
        memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 13.2.4.1 — Espessuras mínimas de lajes maciças, lista a) a g) (PDF p. 94)
# ---------------------------------------------------------------------------
ESPESSURA_MINIMA_LAJE_COBERTURA_CM = 7.0
ESPESSURA_MINIMA_LAJE_PISO_CM = 8.0
ESPESSURA_MINIMA_LAJE_PISO_VEICULO_LEVE_CM = 10.0    # peso total <= 30 kN
ESPESSURA_MINIMA_LAJE_PISO_VEICULO_PESADO_CM = 12.0  # peso total > 30 kN
ESPESSURA_MINIMA_LAJE_PROTENDIDA_ABSOLUTA_CM = 15.0
ESPESSURA_MINIMA_LAJE_LISA_CM = 16.0
ESPESSURA_MINIMA_LAJE_COGUMELO_FORA_CAPITEL_CM = 14.0
PESO_VEICULO_LIMITE_KN = 30.0


def espessura_minima_laje_cm(
    categoria: str,
    *,
    peso_veiculo_kn: float | None = None,
    vao_efetivo_cm: float | None = None,
    continua: bool = False,
) -> float:
    """Espessura mínima de laje maciça pela categoria de uso, 13.2.4.1 a) a
    g) (PDF p. 94):

    a) 'cobertura'      -> 7 cm (cobertura não em balanço);
    b) 'piso'           -> 8 cm (laje de piso não em balanço);
    c) 'balanco'        -> 10 cm (laje em balanço);
    d) e e) 'piso_veiculo' -> 10 cm se ``peso_veiculo_kn`` <= 30 kN, 12 cm se
       > 30 kN (``peso_veiculo_kn`` é obrigatório nesta categoria);
    f) 'protendida'     -> max(15, l/42) para laje de piso biapoiada, ou
       max(15, l/50) para laje de piso contínua (``continua=True``), com l =
       ``vao_efetivo_cm`` (obrigatório nesta categoria) — lajes protendidas
       apoiadas em vigas;
    g) 'lisa'           -> 16 cm; 'cogumelo' -> 14 cm, fora do capitel.

    ``categoria`` aceita variantes usuais (maiúscula/minúscula, com ou sem
    acento/hífen/espaço).
    """
    chave = nbr._chave(categoria)
    if chave == "cobertura":
        return ESPESSURA_MINIMA_LAJE_COBERTURA_CM
    if chave == "piso":
        return ESPESSURA_MINIMA_LAJE_PISO_CM
    if chave == "balanco":
        return ESPESSURA_MINIMA_LAJE_BALANCO_CM
    if chave == "pisoveiculo":
        if peso_veiculo_kn is None:
            raise ValueError(
                "peso_veiculo_kn é obrigatório para a categoria 'piso_veiculo' "
                "(13.2.4.1 d, e)."
            )
        return (ESPESSURA_MINIMA_LAJE_PISO_VEICULO_LEVE_CM
                if peso_veiculo_kn <= PESO_VEICULO_LIMITE_KN
                else ESPESSURA_MINIMA_LAJE_PISO_VEICULO_PESADO_CM)
    if chave == "protendida":
        if vao_efetivo_cm is None:
            raise ValueError(
                "vao_efetivo_cm é obrigatório para a categoria 'protendida' (13.2.4.1 f)."
            )
        divisor = 50.0 if continua else 42.0
        return max(ESPESSURA_MINIMA_LAJE_PROTENDIDA_ABSOLUTA_CM, vao_efetivo_cm / divisor)
    if chave == "lisa":
        return ESPESSURA_MINIMA_LAJE_LISA_CM
    if chave == "cogumelo":
        return ESPESSURA_MINIMA_LAJE_COGUMELO_FORA_CAPITEL_CM
    raise ValueError(
        f"Categoria desconhecida: {categoria!r}. Use: cobertura, piso, balanço, "
        "piso_veiculo, protendida, lisa ou cogumelo."
    )


# ---------------------------------------------------------------------------
# 13.2.4.2 — Lajes nervuradas: mesa, nervura e classificação (PDF p. 95)
# ---------------------------------------------------------------------------
MESA_NERVURADA_ESPESSURA_MINIMA_ABSOLUTA_CM = 4.0
MESA_NERVURADA_ESPESSURA_MINIMA_COM_TUBO_CM = 5.0
NERVURA_ESPESSURA_MINIMA_CM = 5.0
NERVURA_LARGURA_MINIMA_ARMADURA_COMPRESSAO_CM = 8.0
NERVURA_ESPACAMENTO_LIMITE_DISPENSA_MESA_CM = 65.0
NERVURA_ESPACAMENTO_LIMITE_VIGA_CM = 110.0
NERVURA_ESPACAMENTO_LIMITE_EXCECAO_LAJE_CM = 90.0
NERVURA_LARGURA_MEDIA_MINIMA_EXCECAO_CM = 12.0


def espessura_minima_mesa_nervurada_cm(
    l0_cm: float, phi_mm: float | None = None, cruzamento: bool = False,
) -> float:
    """Espessura mínima da mesa de laje nervurada, 13.2.4.2 (PDF p. 95).

    Sem tubulação horizontal embutida: hf >= max(l0/15, 4) cm, com l0 a
    distância entre as faces das nervuras.

    Com tubulação embutida: o mínimo absoluto passa a ser 5 cm para
    diâmetro φ <= 10 mm; para φ > 10 mm, hf >= 4 cm + φ (em cm); havendo
    cruzamento de tubulações, hf >= 4 cm + 2φ. O resultado é o maior valor
    entre esse mínimo com tubulação e o mínimo geral (l0/15, 4).
    """
    base = max(l0_cm / 15.0, MESA_NERVURADA_ESPESSURA_MINIMA_ABSOLUTA_CM)
    if phi_mm is None:
        return base
    phi_cm = float(phi_mm) / 10.0
    if phi_mm <= 10.0:
        candidato_tubo = MESA_NERVURADA_ESPESSURA_MINIMA_COM_TUBO_CM
    elif not cruzamento:
        candidato_tubo = 4.0 + phi_cm
    else:
        candidato_tubo = 4.0 + 2.0 * phi_cm
    return max(base, candidato_tubo)


def espessura_minima_nervura_cm() -> float:
    """Espessura mínima da nervura de laje nervurada, 13.2.4.2 (PDF p. 95): 5 cm."""
    return NERVURA_ESPESSURA_MINIMA_CM


@dataclass(frozen=True)
class ResultadoNervura:
    b_cm: float
    As_comp_cm2: float
    espessura_minima_ok: bool
    armadura_compressao_permitida: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_nervura(b_cm: float, As_comp_cm2: float = 0.0) -> ResultadoNervura:
    """Verifica a espessura mínima da nervura e a restrição à armadura de
    compressão, 13.2.4.2 (PDF p. 95).

    A espessura da nervura não pode ser inferior a 5 cm. Nervuras com
    espessura menor que 8 cm não podem conter armadura de compressão.
    """
    b = float(b_cm)
    As_comp = float(As_comp_cm2)
    memoria: list[str] = []

    espessura_minima_ok = b + 1e-9 >= NERVURA_ESPESSURA_MINIMA_CM
    memoria.append(
        f"13.2.4.2: b = {b:g} cm "
        f"{'>= 5 cm -> ok.' if espessura_minima_ok else '< 5 cm -> reprovado.'}"
    )

    largura_permite_compressao = b + 1e-9 >= NERVURA_LARGURA_MINIMA_ARMADURA_COMPRESSAO_CM
    tem_armadura_compressao = As_comp > 1e-9
    armadura_compressao_permitida = largura_permite_compressao or not tem_armadura_compressao
    if tem_armadura_compressao:
        memoria.append(
            f"13.2.4.2: As_comp = {As_comp:g} cm² > 0 com b = {b:g} cm "
            f"{'>= 8 cm -> permitido.' if largura_permite_compressao else '< 8 cm -> proibido.'}"
        )
    else:
        memoria.append("13.2.4.2: sem armadura de compressão -> restrição não se aplica.")

    ok = espessura_minima_ok and armadura_compressao_permitida
    if ok:
        governante = "atende 13.2.4.2"
    elif not espessura_minima_ok:
        governante = "espessura mínima de nervura (13.2.4.2)"
    else:
        governante = "armadura de compressão proibida em nervura < 8 cm (13.2.4.2)"

    return ResultadoNervura(
        b_cm=b, As_comp_cm2=As_comp, espessura_minima_ok=espessura_minima_ok,
        armadura_compressao_permitida=armadura_compressao_permitida, ok=ok,
        governante=governante, memoria=tuple(memoria),
    )


@dataclass(frozen=True)
class ResultadoClassificacaoNervurada:
    espacamento_cm: float
    largura_media_nervura_cm: float | None
    categoria: str                # 'a', 'b' ou 'c' (13.2.4.2)
    dispensa_flexao_mesa: bool
    cisalhamento_como: str        # 'laje' ou 'viga'
    mesa_como_laje_macica: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def classificar_laje_nervurada(
    espacamento_cm: float, largura_media_nervura_cm: float | None = None,
) -> ResultadoClassificacaoNervurada:
    """Classifica o espaçamento entre eixos de nervuras e a regra de
    verificação aplicável, 13.2.4.2 a) a c) (PDF p. 95).

    a) espaçamento <= 65 cm: dispensa a verificação da flexão da mesa; o
       cisalhamento da região das nervuras pode ser verificado como laje;
    b) 65 cm < espaçamento <= 110 cm: exige a verificação da flexão da mesa
       e o cisalhamento das nervuras verificado como viga — exceto quando
       espaçamento <= 90 cm e a largura média das nervuras > 12 cm, caso em
       que o cisalhamento pode ser verificado como laje;
    c) espaçamento > 110 cm: a mesa deve ser projetada como laje maciça,
       apoiada na grelha de vigas, respeitando os limites mínimos de
       espessura de 13.2.4.1.
    """
    e = float(espacamento_cm)

    if e <= NERVURA_ESPACAMENTO_LIMITE_DISPENSA_MESA_CM + 1e-9:
        return ResultadoClassificacaoNervurada(
            espacamento_cm=e, largura_media_nervura_cm=largura_media_nervura_cm,
            categoria="a", dispensa_flexao_mesa=True, cisalhamento_como="laje",
            mesa_como_laje_macica=False,
            ok=True, governante="categoria a (13.2.4.2 a)",
            memoria=(
                f"13.2.4.2 a): espaçamento = {e:g} cm <= 65 cm -> dispensa a "
                "verificação da flexão da mesa; cisalhamento pode ser verificado "
                "como laje.",
            ),
        )

    if e <= NERVURA_ESPACAMENTO_LIMITE_VIGA_CM + 1e-9:
        excecao = (
            largura_media_nervura_cm is not None
            and e <= NERVURA_ESPACAMENTO_LIMITE_EXCECAO_LAJE_CM + 1e-9
            and largura_media_nervura_cm > NERVURA_LARGURA_MEDIA_MINIMA_EXCECAO_CM
        )
        cisalhamento = "laje" if excecao else "viga"
        memoria = [
            f"13.2.4.2 b): 65 < espaçamento = {e:g} <= 110 cm -> exige a "
            "verificação da flexão da mesa."
        ]
        if excecao:
            memoria.append(
                f"13.2.4.2 b): espaçamento <= 90 cm e largura média = "
                f"{largura_media_nervura_cm:g} cm > 12 cm -> cisalhamento pode "
                "ser verificado como laje."
            )
        else:
            memoria.append(
                "13.2.4.2 b): cisalhamento das nervuras verificado como viga."
            )
        governante_b = (
            "categoria b, exceção 13.2.4.2 b) (cisalhamento como laje)" if excecao
            else "categoria b (13.2.4.2 b)"
        )
        return ResultadoClassificacaoNervurada(
            espacamento_cm=e, largura_media_nervura_cm=largura_media_nervura_cm,
            categoria="b", dispensa_flexao_mesa=False, cisalhamento_como=cisalhamento,
            mesa_como_laje_macica=False,
            ok=True, governante=governante_b, memoria=tuple(memoria),
        )

    return ResultadoClassificacaoNervurada(
        espacamento_cm=e, largura_media_nervura_cm=largura_media_nervura_cm,
        categoria="c", dispensa_flexao_mesa=False, cisalhamento_como="viga",
        mesa_como_laje_macica=True,
        ok=True, governante="categoria c (13.2.4.2 c)",
        memoria=(
            f"13.2.4.2 c): espaçamento = {e:g} cm > 110 cm -> mesa projetada "
            "como laje maciça, apoiada na grelha de vigas.",
        ),
    )


# ---------------------------------------------------------------------------
# 13.2.5.1 — Furos que atravessam vigas na direção da largura (PDF p. 95-96)
# ---------------------------------------------------------------------------
FURO_VIGA_DIST_FACE_MINIMA_ABSOLUTA_CM = 5.0
FURO_VIGA_DIMENSAO_MAXIMA_RETANGULAR_CM = 12.0
FURO_VIGA_DIMENSAO_MAXIMA_CIRCULAR_CM = 12.5


@dataclass(frozen=True)
class ResultadoFuroViga:
    dist_face_minima_cm: float
    dist_face_ok: bool
    dispensa_verificacao: bool
    condicoes_atendidas: tuple[str, ...]
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def dispensa_verificacao_furo_viga(
    h_cm: float,
    dist_furo_apoio_cm: float,
    dist_face_cm: float,
    cobrimento_cm: float,
    *,
    largura_furo_cm: float | None = None,
    altura_furo_cm: float | None = None,
    diametro_furo_cm: float | None = None,
    zona_tracao: bool = True,
    dist_entre_furos_cm: float | None = None,
    armadura_seccionada: bool = False,
) -> ResultadoFuroViga:
    """Furo que atravessa viga na direção da largura, 13.2.5.1 (PDF p. 95-96).

    A distância mínima do furo à face mais próxima da viga é sempre
    obrigatória: dist_face >= max(5 cm, 2·cobrimento).

    A dispensa da verificação específica exige simultaneamente:
      a) furo em zona de tração e a uma distância do apoio >= 2h;
      b) dimensão do furo <= 12 cm x 12 cm (retangular: informe
         ``largura_furo_cm`` e ``altura_furo_cm``) ou <= 12,5 cm (circular:
         informe ``diametro_furo_cm``), ambos limitados também a h/3;
      c) distância entre faces de furos em um mesmo tramo >= 2h (se houver
         mais de um furo; sem outro furo informado, a condição não se aplica);
      d) cobrimentos suficientes (a distância mínima de a) atendida) e
         armadura não seccionada.
    """
    h = float(h_cm)
    memoria: list[str] = []

    dist_face_minima = max(
        FURO_VIGA_DIST_FACE_MINIMA_ABSOLUTA_CM, 2.0 * float(cobrimento_cm)
    )
    dist_face_ok = float(dist_face_cm) + 1e-9 >= dist_face_minima
    memoria.append(
        f"13.2.5.1: distância mínima furo-face = max(5, 2*{cobrimento_cm:g}) = "
        f"{dist_face_minima:g} cm; informada {dist_face_cm:g} cm -> "
        f"{'ok' if dist_face_ok else 'não ok'}."
    )

    cond_a = zona_tracao and (float(dist_furo_apoio_cm) + 1e-9 >= 2.0 * h)
    memoria.append(
        f"13.2.5.1 a): {'zona de tração,' if zona_tracao else 'fora da zona de tração,'} "
        f"distância ao apoio = {dist_furo_apoio_cm:g} cm "
        f"({'>=' if float(dist_furo_apoio_cm) + 1e-9 >= 2.0*h else '<'} 2h = {2*h:g} cm) -> "
        f"{'ok' if cond_a else 'não ok'}."
    )

    if diametro_furo_cm is not None:
        d = float(diametro_furo_cm)
        cond_b_dim = d <= FURO_VIGA_DIMENSAO_MAXIMA_CIRCULAR_CM + 1e-9
        cond_b_h3 = d <= h / 3.0 + 1e-9
    elif largura_furo_cm is not None and altura_furo_cm is not None:
        lf, af = float(largura_furo_cm), float(altura_furo_cm)
        cond_b_dim = (lf <= FURO_VIGA_DIMENSAO_MAXIMA_RETANGULAR_CM + 1e-9
                     and af <= FURO_VIGA_DIMENSAO_MAXIMA_RETANGULAR_CM + 1e-9)
        cond_b_h3 = lf <= h / 3.0 + 1e-9 and af <= h / 3.0 + 1e-9
    else:
        raise ValueError(
            "Informe diametro_furo_cm (furo circular) ou largura_furo_cm e "
            "altura_furo_cm (furo retangular)."
        )
    cond_b = cond_b_dim and cond_b_h3
    memoria.append(
        f"13.2.5.1 b): dimensão do furo e limite h/3 = {h/3.0:g} cm -> "
        f"{'ok' if cond_b else 'não ok'}."
    )

    if dist_entre_furos_cm is None:
        cond_c = True
        memoria.append("13.2.5.1 c): sem outro furo informado no tramo -> não se aplica.")
    else:
        cond_c = float(dist_entre_furos_cm) + 1e-9 >= 2.0 * h
        memoria.append(
            f"13.2.5.1 c): distância entre furos = {dist_entre_furos_cm:g} cm "
            f"({'>=' if cond_c else '<'} 2h = {2*h:g} cm) -> {'ok' if cond_c else 'não ok'}."
        )

    cond_d = dist_face_ok and not armadura_seccionada
    memoria.append(
        f"13.2.5.1 d): cobrimentos {'suficientes' if dist_face_ok else 'insuficientes'} "
        f"e armadura {'não seccionada' if not armadura_seccionada else 'seccionada'} -> "
        f"{'ok' if cond_d else 'não ok'}."
    )

    condicoes = {"a": cond_a, "b": cond_b, "c": cond_c, "d": cond_d}
    dispensa = all(condicoes.values())
    memoria.append(
        f"13.2.5.1: verificação específica {'dispensada' if dispensa else 'não dispensada'}."
    )

    return ResultadoFuroViga(
        dist_face_minima_cm=dist_face_minima,
        dist_face_ok=dist_face_ok,
        dispensa_verificacao=dispensa,
        condicoes_atendidas=tuple(k for k, v in condicoes.items() if v),
        ok=dist_face_ok,
        governante=(
            "dispensado (a-d atendidas)" if dispensa
            else "não dispensado (verificação específica exigida)"
        ),
        memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 13.2.5.2 — Aberturas que atravessam lajes na direção da espessura (PDF p. 96)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoAberturaLaje:
    lx_cm: float
    ly_cm: float
    ax_cm: float
    ay_cm: float
    dispensa_verificacao: bool
    condicoes_atendidas: tuple[str, ...]
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def dispensa_verificacao_abertura_laje(
    lx_cm: float,
    ly_cm: float,
    ax_cm: float,
    ay_cm: float,
    *,
    tipo_laje: str = "normal",
    dist_face_apoio_x_cm: float | None = None,
    dist_face_apoio_y_cm: float | None = None,
    dist_entre_aberturas_cm: float | None = None,
) -> ResultadoAberturaLaje:
    """Dispensa de verificação de abertura em laje armada em duas direções,
    13.2.5.2 e Figura 13.1 (PDF p. 96).

    Lajes lisas ou lajes-cogumelo (``tipo_laje='lisa'`` ou ``'cogumelo'``)
    sempre exigem a verificação de resistência e deformação de 13.2.5 —
    nunca dispensam. Para as demais lajes, armadas em duas direções, a
    dispensa exige simultaneamente (``lx_cm`` tem de ser o menor vão, como
    na Figura 13.1; ``dist_face_apoio_x_cm``/``_y_cm`` são as distâncias na
    direção de ``lx``/``ly``, respectivamente — a função não troca os eixos,
    para não desassociar essas distâncias do vão errado):
      a) ax < lx/10 e ay < lx/10;
      b) a distância entre a face da abertura e o eixo teórico de apoio é
         >= 1/4 do vão na direção considerada (lx/4 na direção x, ly/4 na y);
      c) a distância entre faces de aberturas adjacentes é maior que a
         metade do menor vão (lx/2) — condição que só se aplica quando há
         mais de uma abertura (``dist_entre_aberturas_cm`` informado).
    """
    lx = float(lx_cm)
    ly = float(ly_cm)
    if lx > ly:
        raise ValueError(
            f"lx_cm = {lx:g} cm > ly_cm = {ly:g} cm: por convenção (Figura 13.1), "
            "lx_cm tem de ser o menor vão. Troque lx_cm e ly_cm (e as distâncias "
            "x/y correspondentes) antes de chamar esta função."
        )
    ax = float(ax_cm)
    ay = float(ay_cm)

    chave_tipo = nbr._chave(tipo_laje)
    if chave_tipo in ("lisa", "cogumelo"):
        return ResultadoAberturaLaje(
            lx_cm=lx, ly_cm=ly, ax_cm=ax, ay_cm=ay,
            dispensa_verificacao=False, condicoes_atendidas=(), ok=False,
            governante="laje lisa/cogumelo: verificação de 13.2.5 sempre exigida",
            memoria=(
                f"13.2.5.2: laje {tipo_laje} -> a verificação de resistência e "
                "deformação de 13.2.5 é sempre exigida, nunca dispensa.",
            ),
        )

    memoria: list[str] = []
    limite_a = lx / 10.0
    cond_a = (ax < limite_a - 1e-9) and (ay < limite_a - 1e-9)
    memoria.append(
        f"13.2.5.2 a): ax = {ax:g} cm, ay = {ay:g} cm, lx/10 = {limite_a:g} cm -> "
        f"{'ok' if cond_a else 'não ok'}."
    )

    if dist_face_apoio_x_cm is None or dist_face_apoio_y_cm is None:
        cond_b = False
        memoria.append(
            "13.2.5.2 b): distâncias face-apoio não informadas -> não verificado."
        )
    else:
        limite_x = lx / 4.0
        limite_y = ly / 4.0
        cond_b = (float(dist_face_apoio_x_cm) + 1e-9 >= limite_x
                 and float(dist_face_apoio_y_cm) + 1e-9 >= limite_y)
        memoria.append(
            f"13.2.5.2 b): dist_x = {dist_face_apoio_x_cm:g} cm >= lx/4 = {limite_x:g} cm "
            f"e dist_y = {dist_face_apoio_y_cm:g} cm >= ly/4 = {limite_y:g} cm -> "
            f"{'ok' if cond_b else 'não ok'}."
        )

    if dist_entre_aberturas_cm is None:
        cond_c = True
        memoria.append("13.2.5.2 c): sem outra abertura informada -> não se aplica.")
    else:
        cond_c = float(dist_entre_aberturas_cm) > lx / 2.0 + 1e-9
        memoria.append(
            f"13.2.5.2 c): distância entre aberturas = {dist_entre_aberturas_cm:g} cm "
            f"> lx/2 = {lx/2.0:g} cm -> {'ok' if cond_c else 'não ok'}."
        )

    condicoes = {"a": cond_a, "b": cond_b, "c": cond_c}
    dispensa = all(condicoes.values())
    memoria.append(
        f"13.2.5.2: verificação {'dispensada' if dispensa else 'não dispensada'}."
    )

    return ResultadoAberturaLaje(
        lx_cm=lx, ly_cm=ly, ax_cm=ax, ay_cm=ay,
        dispensa_verificacao=dispensa,
        condicoes_atendidas=tuple(k for k, v in condicoes.items() if v),
        ok=dispensa,
        governante=(
            "dispensada (a-c atendidas)" if dispensa
            else "não dispensada (verificação de 13.2.5 exigida)"
        ),
        memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 13.2.6 — Canalizações embutidas: casos proibidos (PDF p. 96)
# ---------------------------------------------------------------------------
CANALIZACAO_DELTA_T_LIMITE_C = 15.0
CANALIZACAO_PRESSAO_LIMITE_MPA = 0.3


@dataclass(frozen=True)
class ResultadoCanalizacaoEmbutida:
    permitido: bool
    proibicoes: tuple[str, ...]
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def canalizacao_embutida_permitida(
    *,
    delta_temperatura_c: float | None = None,
    isolamento_ou_verificacao: bool = False,
    pressao_interna_mpa: float | None = None,
    em_pilar: bool = False,
    abertura_drenagem: bool = False,
) -> ResultadoCanalizacaoEmbutida:
    """Casos proibidos de canalização embutida, 13.2.6 (PDF p. 96).

    Os elementos estruturais não podem conter canalizações embutidas nos
    seguintes casos:
      a) sem isolamento adequado, quando destinadas a fluido com temperatura
         que se afaste em mais de 15 °C da temperatura ambiente, a menos que
         seja feita uma verificação específica do efeito da temperatura
         (``isolamento_ou_verificacao=True`` cobre as duas exceções);
      b) destinadas a suportar pressões internas maiores que 0,3 MPa;
      c) embutidas em pilares de concreto, imersas no material ou em
         espaços vazios internos, sem abertura de drenagem.

    Cada verificação só entra quando o argumento correspondente é informado
    (``None`` = não se aplica ao caso).
    """
    memoria: list[str] = []
    proibicoes: list[str] = []

    if delta_temperatura_c is not None:
        delta = abs(float(delta_temperatura_c))
        viola_a = delta > CANALIZACAO_DELTA_T_LIMITE_C + 1e-9 and not isolamento_ou_verificacao
        if viola_a:
            proibicoes.append("13.2.6 a)")
        memoria.append(
            f"13.2.6 a): |ΔT| = {delta:g} °C, isolamento/verificação = "
            f"{isolamento_ou_verificacao} -> {'proibido' if viola_a else 'ok'}."
        )

    if pressao_interna_mpa is not None:
        p = float(pressao_interna_mpa)
        viola_b = p > CANALIZACAO_PRESSAO_LIMITE_MPA + 1e-9
        if viola_b:
            proibicoes.append("13.2.6 b)")
        memoria.append(
            f"13.2.6 b): pressão interna = {p:g} MPa -> "
            f"{'proibido' if viola_b else 'ok'} (limite 0,3 MPa)."
        )

    if em_pilar:
        viola_c = not abertura_drenagem
        if viola_c:
            proibicoes.append("13.2.6 c)")
        memoria.append(
            f"13.2.6 c): canalização embutida em pilar, abertura de drenagem = "
            f"{abertura_drenagem} -> {'proibido' if viola_c else 'ok'}."
        )

    permitido = not proibicoes
    memoria.append(
        f"13.2.6: {'permitido' if permitido else 'proibido (' + ', '.join(proibicoes) + ')'}."
    )
    governante = (
        "atende 13.2.6" if permitido
        else "proibido por " + ", ".join(proibicoes) + " (13.2.6)"
    )

    return ResultadoCanalizacaoEmbutida(
        permitido=permitido, proibicoes=tuple(proibicoes), ok=permitido,
        governante=governante, memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 22.2 — Coeficiente adicional γn de consolos e dentes Gerber (PDF p. 203)
# ---------------------------------------------------------------------------
GAMA_N_CONSOLO_GERBER_MINIMO = 1.2


def gama_n_consolo_gerber() -> float:
    """Coeficiente adicional γn mínimo para consolos, dentes Gerber e
    elementos que se comportam como tais (22.2, PDF p. 203): γn >= 1,2.

    Devolve o valor mínimo exigido pela norma; o projetista pode adotar um
    valor maior, mas nunca menor.
    """
    return GAMA_N_CONSOLO_GERBER_MINIMO
