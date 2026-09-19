"""Verificacao de secao de pilar: momento minimo e envoltoria minima
(NBR 6118:2026).

11.3.3.4.3 e Figura 11.3 (PDF p. 80-81): o efeito das imperfeicoes locais
pode ser substituido pelo momento minimo de 1a ordem

    M1d,min = Nd (0,015 + 0,03 h),   h em metros, na direcao considerada.

Para secao retangular, a envoltoria minima de 1a ordem e a elipse

    (M1d,min,x / M1d,min,xx)^2 + (M1d,min,y / M1d,min,yy)^2 = 1,

com M1d,min,xx = Nd (0,015 + 0,03 h) e M1d,min,yy = Nd (0,015 + 0,03 b), e
a verificacao do momento minimo e atendida quando a envoltoria resistente
(para o Nd de calculo) engloba essa elipse.

15.3.2 e Figura 15.2 (PDF p. 122): quando ha efeitos locais de 2a ordem, a
envoltoria minima com 2a ordem tem por semi-eixos os momentos totais
Md,tot,min,xx e Md,tot,min,yy, calculados a partir dos minimos de 1a ordem
(15.8.3). Passe-os em `Md_tot_min_xx_kncm` / `Md_tot_min_yy_kncm`; a direcao
sem 2a ordem fica com o minimo de 1a ordem.

O kernel de flexao obliqua continua verificando so a secao (decisao 8 da
auditoria): aqui se monta a envoltoria minima e se chama o kernel, com N
fixo, em cada direcao.

Convencoes do kernel (`flexao_composta_obliqua`): Mxd em torno de x (flexao
no plano y, dimensao h = altura_cm); Myd em torno de y (dimensao b =
base_cm). Compressao positiva. Unidades: kN, cm, kN.cm.
"""

from __future__ import annotations

import math
import os
import sys
from collections import Counter

from scipy.optimize import minimize_scalar

try:  # importado como pacote (dimensionamento.rotinas.verificacao_pilar)
    from . import fco_dispatch
    from . import flexao_composta_obliqua as fco
except ImportError:  # executado como script: poe a raiz do repositorio no sys.path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from dimensionamento.rotinas import fco_dispatch
    from dimensionamento.rotinas import flexao_composta_obliqua as fco

nbr = fco.nbr   # o mesmo nucleo normativo que o kernel usa


_PRIORIDADE = {"OK": 0, "NAO_VERIFICA": 1, "NAO_CONVERGIU": 2, "FORA_RANGE": 3}


# ---------------------------------------------------------------------------
# Momento minimo e envoltoria minima -- 11.3.3.4.3, Figura 11.3
# ---------------------------------------------------------------------------
def momento_minimo_1a_ordem_kncm(Nd_kn: float, h_cm: float) -> float:
    """M1d,min = Nd (0,015 + 0,03 h), h em metros (11.3.3.4.3), em kN.cm.

    Com Nd em kN e h em cm: M1d,min = Nd (1,5 + 0,03 h). O momento minimo
    representa as imperfeicoes locais de pilar comprimido; com Nd <= 0
    (tracao) devolve 0.
    """
    return nbr.M1d_min_kncm(Nd_kn, h_cm)


def momentos_minimos_1a_ordem(Nd_kn: float, base_cm: float, altura_cm: float) -> tuple[float, float]:
    """(M1d,min,xx, M1d,min,yy), kN.cm (Figura 11.3).

    xx: em torno de x, com h = altura_cm; yy: em torno de y, com b = base_cm.
    """
    return (momento_minimo_1a_ordem_kncm(Nd_kn, altura_cm),
            momento_minimo_1a_ordem_kncm(Nd_kn, base_cm))


def _semi_eixos(Nd_kn, base_cm, altura_cm, Md_tot_min_xx_kncm, Md_tot_min_yy_kncm):
    m_xx, m_yy = momentos_minimos_1a_ordem(Nd_kn, base_cm, altura_cm)
    a = m_xx if Md_tot_min_xx_kncm is None else max(m_xx, abs(float(Md_tot_min_xx_kncm)))
    b = m_yy if Md_tot_min_yy_kncm is None else max(m_yy, abs(float(Md_tot_min_yy_kncm)))
    segunda = Md_tot_min_xx_kncm is not None or Md_tot_min_yy_kncm is not None
    return m_xx, m_yy, a, b, segunda


def envoltoria_minima(
    Nd_kn: float,
    base_cm: float,
    altura_cm: float,
    n_pontos: int = 24,
    Md_tot_min_xx_kncm: float | None = None,
    Md_tot_min_yy_kncm: float | None = None,
) -> list[tuple[float, float]]:
    """Pontos (Mx, My), kN.cm, da envoltoria minima (elipse), a partir de +Mx
    no sentido anti-horario. Com os Md,tot,min, e a envoltoria com 2a ordem
    (Figura 15.2)."""
    _, _, a, b, _ = _semi_eixos(Nd_kn, base_cm, altura_cm, Md_tot_min_xx_kncm, Md_tot_min_yy_kncm)
    return [(a * math.cos(2.0 * math.pi * i / n_pontos), b * math.sin(2.0 * math.pi * i / n_pontos))
            for i in range(n_pontos)]


# ---------------------------------------------------------------------------
# Verificacao
# ---------------------------------------------------------------------------
def _dimensoes(secao) -> tuple[float, float]:
    """(base_cm, altura_cm) da secao; a Figura 11.3 vale para secao retangular."""
    if isinstance(secao, fco.SecaoRetangular):
        return float(secao.base_cm), float(secao.altura_cm)
    if isinstance(secao, fco.Secao):
        x0, y0, x1, y1 = fco._bbox_secao(secao)
        b, h = x1 - x0, y1 - y0
        if abs(secao.Ac_cm2 - b * h) > 1e-6 * b * h:
            raise ValueError(
                "A envoltória mínima da Figura 11.3 (NBR 6118:2026) é definida para "
                "seção retangular; a seção informada não é retangular."
            )
        return b, h
    raise TypeError("secao deve ser SecaoRetangular ou Secao (retangular).")


def _duplamente_simetrica(secao) -> bool:
    """Retangulo centrado com barras simetricas em x e em y (mesma area)."""
    if not isinstance(secao, fco.SecaoRetangular):
        return False

    def chave(x: float, y: float, A: float) -> tuple[float, float, float]:
        return (round(x, 6) + 0.0, round(y, 6) + 0.0, round(A, 9))

    barras = Counter(chave(b.x_cm, b.y_cm, b.area_cm2) for b in secao.barras)
    espelho_x = Counter(chave(-x, y, A) for (x, y, A), n in barras.items() for _ in range(n))
    espelho_y = Counter(chave(x, -y, A) for (x, y, A), n in barras.items() for _ in range(n))
    return barras == espelho_x == espelho_y


def _verificar_direcao(secao, concreto, aco, Nd_kn, Mx, My, n_grid, use_cpp) -> dict:
    if isinstance(secao, fco.SecaoRetangular):
        return fco_dispatch.verificar_fco(secao, concreto, aco, Nd_kn, Mx, My, n_grid,
                                          use_cpp=use_cpp)
    return fco.verificar_fco_pol(secao, aco, Nd_kn, Mx, My)


def verificar_envoltoria_minima(
    secao,
    concreto,
    aco,
    Nd_kn: float,
    n_pontos: int = 24,
    Md_tot_min_xx_kncm: float | None = None,
    Md_tot_min_yy_kncm: float | None = None,
    n_grid: int = 80,
    use_cpp: bool | None = None,
) -> dict:
    """Confere se a envoltoria resistente, com N = Nd, engloba a envoltoria
    minima de 1a ordem (11.3.3.4.3, Figura 11.3) -- ou a com 2a ordem
    (15.3.2, Figura 15.2), se os Md,tot,min forem informados.

    Para cada direcao da elipse, o kernel devolve a razao MR/|M| ao longo do
    raio; a elipse esta dentro da envoltoria resistente quando a menor razao
    e >= 1. A menor razao e refinada entre as amostras (busca limitada).
    Secao duplamente simetrica: basta o primeiro quadrante.

    `secao`: SecaoRetangular (via `fco_dispatch`, C++ se `use_cpp`) ou Secao
    poligonal retangular. `concreto` e ignorado para Secao poligonal (cada
    parte tem o seu).

    Retorna dict com status ("OK" | "NAO_VERIFICA" | "FORA_RANGE" |
    "NAO_CONVERGIU"), razao_min, ponto critico, semi-eixos e as amostras.
    """
    base, altura = _dimensoes(secao)
    m_xx, m_yy, a, b, segunda = _semi_eixos(Nd_kn, base, altura,
                                            Md_tot_min_xx_kncm, Md_tot_min_yy_kncm)
    resultado = {
        "M1d_min_xx_kncm": m_xx,
        "M1d_min_yy_kncm": m_yy,
        "semi_eixo_xx_kncm": a,
        "semi_eixo_yy_kncm": b,
        "envoltoria": "2ª ordem (Figura 15.2)" if segunda else "1ª ordem (Figura 11.3)",
    }
    if a <= 0.0 or b <= 0.0:
        resultado.update({
            "status": "OK", "razao_min": float("inf"), "pontos": [],
            "comentario": "Sem compressão (Nd <= 0): não há momento mínimo.",
        })
        return resultado

    simetrica = _duplamente_simetrica(secao)
    t_max = math.pi / 2.0 if simetrica else 2.0 * math.pi
    n = max(2, int(math.ceil(n_pontos * t_max / (2.0 * math.pi))))
    ts = [t_max * i / (n - 1) for i in range(n)] if simetrica else \
         [t_max * i / n for i in range(n)]

    cache: dict[float, dict] = {}

    def avaliar(t: float) -> dict:
        if t not in cache:
            Mx, My = a * math.cos(t), b * math.sin(t)
            r = _verificar_direcao(secao, concreto, aco, Nd_kn, Mx, My, n_grid, use_cpp)
            cache[t] = {"theta_graus": math.degrees(t), "Mx_kncm": Mx, "My_kncm": My,
                        "razao": r.get("razao", -1.0), "status": r["status"],
                        "mensagem": r.get("mensagem")}
        return cache[t]

    pontos = [avaliar(t) for t in ts]
    ruins = [p for p in pontos if p["status"] in ("FORA_RANGE", "NAO_CONVERGIU")]
    if ruins:
        pior = max(ruins, key=lambda p: _PRIORIDADE[p["status"]])
        resultado.update({
            "status": pior["status"], "razao_min": float("nan"), "pontos": pontos,
            "mensagem": pior.get("mensagem"),
        })
        return resultado

    i_min = min(range(len(pontos)), key=lambda i: pontos[i]["razao"])
    t0 = ts[i_min]
    passo = (ts[1] - ts[0])
    lo, hi = t0 - passo, t0 + passo
    if simetrica:
        lo, hi = max(lo, 0.0), min(hi, t_max)

    def razao_t(t: float) -> float:
        p = avaliar(float(t))
        return p["razao"] if p["status"] in ("OK", "NAO_VERIFICA") else float("inf")

    ref = minimize_scalar(razao_t, bounds=(lo, hi), method="bounded",
                          options={"xatol": 1e-3})
    critico = min((avaliar(t0), avaliar(float(ref.x))), key=lambda p: p["razao"])
    resultado.update({
        "status": "OK" if critico["razao"] >= 1.0 else "NAO_VERIFICA",
        "razao_min": critico["razao"],
        "theta_critico_graus": critico["theta_graus"],
        "Mx_critico_kncm": critico["Mx_kncm"],
        "My_critico_kncm": critico["My_kncm"],
        "pontos": pontos,
    })
    return resultado


def verificar_secao_pilar(
    secao,
    concreto,
    aco,
    Nd_kn: float,
    Mxd_kncm: float,
    Myd_kncm: float,
    Md_tot_min_xx_kncm: float | None = None,
    Md_tot_min_yy_kncm: float | None = None,
    n_pontos: int = 24,
    n_grid: int = 80,
    use_cpp: bool | None = None,
) -> dict:
    """Verificacao da secao de pilar: esforcos de calculo (Nd, Mxd, Myd) e
    envoltoria minima (11.3.3.4.3 / 15.3.2).

    Os momentos de calculo ja devem incluir os efeitos de 2a ordem, quando
    houver. O status e OK so se as duas verificacoes passarem; senao, vale o
    pior (FORA_RANGE > NAO_CONVERGIU > NAO_VERIFICA).
    """
    r_sol = _verificar_direcao(secao, concreto, aco, Nd_kn, Mxd_kncm, Myd_kncm, n_grid, use_cpp)
    r_env = verificar_envoltoria_minima(secao, concreto, aco, Nd_kn, n_pontos,
                                        Md_tot_min_xx_kncm, Md_tot_min_yy_kncm,
                                        n_grid, use_cpp)
    status = max((r_sol["status"], r_env["status"]), key=lambda s: _PRIORIDADE[s])
    return {"status": status, "solicitacao": r_sol, "envoltoria_minima": r_env}


# === P25: envoltória mínima com 2ª ordem (15.3.2) e pilar-padrão em flexão oblíqua (15.8.3.3.5) ===
from dataclasses import dataclass as _dataclass_p25

try:  # importado como pacote (dimensionamento.rotinas.verificacao_pilar)
    from dimensionamento import pilares_nbr6118 as _pil
except ImportError:  # executado com dimensionamento/ no sys.path
    import pilares_nbr6118 as _pil


def _fmt_vp25(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


@_dataclass_p25(frozen=True)
class ResultadoEnvoltoriaMinima2aOrdem:
    """Envoltória mínima com 2ª ordem (15.3.2, Figura 15.2)."""
    Nd_kn: float
    Md_tot_min_xx_kncm: float
    Md_tot_min_yy_kncm: float
    direcao_xx: object | None       # ResultadoPilarPadraoDirecao, ou None sem 2ª ordem
    direcao_yy: object | None
    status: str
    razao_min: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]
    envoltoria: dict                # o dicionário de verificar_envoltoria_minima


def _secao_retangular_p25(secao, concreto):
    if not isinstance(secao, fco.SecaoRetangular):
        raise TypeError(
            "O pilar-padrão de 15.3.2 e 15.8.3.3.5 (NBR 6118:2026) é para seção "
            "retangular: passe uma SecaoRetangular."
        )
    if concreto is None or not hasattr(concreto, "fck_mpa"):
        raise TypeError("concreto deve ser um Concreto (com fck_mpa).")
    return float(secao.base_cm), float(secao.altura_cm)


def verificar_envoltoria_minima_2a_ordem(
    secao,
    concreto,
    aco,
    Nd_kn: float,
    le_xx_cm: float,
    le_yy_cm: float | None = None,
    metodo: str = "curvatura",
    segunda_ordem_xx: bool = True,
    segunda_ordem_yy: bool = True,
    n_pontos: int = 24,
    n_grid: int = 80,
    use_cpp: bool | None = None,
    metodo_yy: str | None = None,
) -> ResultadoEnvoltoriaMinima2aOrdem:
    """Envoltória mínima com 2ª ordem, com Md,tot,mín calculados (15.3.2, PDF p. 122).

    Para pilar de seção retangular com efeitos locais de 2ª ordem, a
    verificação do momento mínimo é atendida quando a envoltória resistente
    engloba a envoltória mínima com 2ª ordem (Figura 15.2):

        (Md,tot,mín,x / Md,tot,mín,xx)² + (Md,tot,mín,y / Md,tot,mín,yy)² = 1,

    com Md,tot,mín,xx e Md,tot,mín,yy calculados em cada direção, isolada, a
    partir de M1d,mín = Nd(1,5 + 0,03h) (11.3.3.4.3) pelo pilar-padrão de
    15.8.3 (``pilares_nbr6118.momento_total_minimo_direcao``, αb = 1,0 por
    15.8.2 d).

    Direções (convenção do kernel): xx é a flexão em torno de x, com
    h = altura_cm e ℓe = ``le_xx_cm``; yy é em torno de y, com h = base_cm
    e ℓe = ``le_yy_cm`` (padrão: o mesmo ℓe). ``segunda_ordem_xx/yy=False``
    diz que naquela direção os efeitos de 2ª ordem são dispensados
    (λ < λ1, 15.8.2); o semi-eixo fica com o mínimo de 1ª ordem. Nd em kN
    (compressão positiva), ℓe em cm, momentos em kN·cm.

    ``metodo``: "curvatura" (15.8.3.3.2) ou "rigidez" (15.8.3.3.3), nas duas
    direções, salvo ``metodo_yy``; os dois só valem para λ <= 90 e levantam
    ``FaixaNormativaError`` acima disso.
    """
    base, altura = _secao_retangular_p25(secao, concreto)
    Nd = float(Nd_kn)
    le_yy = le_xx_cm if le_yy_cm is None else le_yy_cm
    Ac = secao.Ac_cm2
    gc = concreto.gama_c
    rx = (_pil.momento_total_minimo_direcao(Nd, le_xx_cm, altura, Ac, concreto.fck_mpa,
                                            metodo, direcao="xx", gama_c=gc)
          if segunda_ordem_xx else None)
    ry = (_pil.momento_total_minimo_direcao(Nd, le_yy, base, Ac, concreto.fck_mpa,
                                            metodo_yy or metodo, direcao="yy", gama_c=gc)
          if segunda_ordem_yy else None)
    m_xx, m_yy = momentos_minimos_1a_ordem(Nd, base, altura)
    Mxx = rx.Md_tot_kncm if rx is not None else m_xx
    Myy = ry.Md_tot_kncm if ry is not None else m_yy
    env = verificar_envoltoria_minima(secao, concreto, aco, Nd, n_pontos,
                                      Mxx, Myy, n_grid, use_cpp)
    status = env["status"]
    ok = status == "OK"
    razao = env.get("razao_min", float("nan"))
    memoria = [f"15.3.2: envoltória mínima com 2ª ordem (Figura 15.2), Nd = {_fmt_vp25(Nd)} kN."]
    for nome, r, m1 in (("xx", rx, m_xx), ("yy", ry, m_yy)):
        if r is None:
            memoria.append(f"15.3.2 [{nome}]: sem 2ª ordem na direção; semi-eixo = M1d,mín = "
                           f"{_fmt_vp25(m1)} kN·cm.")
        else:
            memoria.extend(r.memoria)
            memoria.append(f"15.3.2 [{nome}]: Md,tot,mín,{nome} = {_fmt_vp25(r.Md_tot_kncm)} kN·cm.")
    memoria.append(f"15.3.2: (Mx/{_fmt_vp25(Mxx)})² + (My/{_fmt_vp25(Myy)})² = 1; "
                   f"razão mínima MR/MS = {_fmt_vp25(razao)} -> {status}.")
    governante = (f"envoltória mínima com 2ª ordem: MR/MS = {_fmt_vp25(razao)}"
                  + ("" if ok else f" — {status}"))
    return ResultadoEnvoltoriaMinima2aOrdem(
        Nd_kn=Nd, Md_tot_min_xx_kncm=Mxx, Md_tot_min_yy_kncm=Myy,
        direcao_xx=rx, direcao_yy=ry, status=status, razao_min=razao, ok=ok,
        governante=governante, memoria=tuple(memoria), envoltoria=env,
    )


@_dataclass_p25(frozen=True)
class ResultadoPilarPadraoObliquo:
    """Pilar-padrão em flexão composta oblíqua (15.8.3.3.5)."""
    gama_n: float
    Nd_kn: float                    # já multiplicado por γn
    direcao_xx: object              # ResultadoPilarPadraoDirecao
    direcao_yy: object
    secoes: tuple[dict, ...]        # A (topo), intermediária, B (base)
    envoltoria_minima: ResultadoEnvoltoriaMinima2aOrdem | None
    status: str
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def pilar_padrao_obliquo(
    secao,
    concreto,
    aco,
    Nd_kn: float,
    le_xx_cm: float,
    le_yy_cm: float,
    M_topo_xx_kncm: float,
    M_base_xx_kncm: float,
    M_topo_yy_kncm: float,
    M_base_yy_kncm: float,
    metodo: str = "curvatura",
    tipo: str = "biapoiado",
    metodo_yy: str | None = None,
    tipo_yy: str | None = None,
    verificar_minimo: bool = True,
    aplicar_gama_n: bool = True,
    n_pontos: int = 24,
    n_grid: int = 80,
    use_cpp: bool | None = None,
) -> ResultadoPilarPadraoObliquo:
    """Pilar-padrão em flexão composta oblíqua (15.8.3.3.5, PDF p. 131).

    "Quando a esbeltez de um pilar de seção retangular submetido à flexão
    composta oblíqua for menor ou igual que 90 (λ <= 90) nas duas direções
    principais, podem ser aplicados os processos aproximados [...]
    simultaneamente, em cada uma das duas direções." A verificação da
    composição dos momentos totais contra a envoltória resistente da
    armadura escolhida é feita em três seções: nas extremidades A (topo) e B
    (base), com os momentos de 1ª ordem, e num ponto intermediário, onde
    atuam juntos os Md,tot das duas direções (com o sentido de MA de cada
    direção).

    Entradas: Nd em kN (compressão positiva) e os momentos de cálculo de
    1ª ordem nos extremos, em kN·cm, com sinal na convenção do kernel (xx
    em torno de x, h = altura_cm, ℓe = ``le_xx_cm``; yy em torno de y,
    h = base_cm, ℓe = ``le_yy_cm``). Em estrutura de nós móveis, passe os
    momentos da análise global de 2ª ordem (15.7.4).

    - γn de 13.2.3 (Tabela 13.1, ``limites_geometricos_nbr6118.gama_n_pilar``)
      multiplica Nd e os momentos quando a menor dimensão é menor que 19 cm
      (``aplicar_gama_n``; passe False se os esforços já vierem majorados).
    - Em cada direção, ``pilares_nbr6118.pilar_padrao_direcao`` com
      ``aplicar_minimo=False`` (αb, λ1, dispensa, Md,tot); ``metodo`` e
      ``tipo`` valem para as duas direções, salvo ``metodo_yy``/``tipo_yy``.
    - O momento mínimo é verificado pela envoltória mínima com 2ª ordem
      (15.3.2, ``verificar_envoltoria_minima_2a_ordem``), com 2ª ordem só nas
      direções em que ela não foi dispensada. ``verificar_minimo=False``
      pula essa verificação (a memória registra).

    O status final é o pior entre as três seções e a envoltória mínima
    (FORA_RANGE > NAO_CONVERGIU > NAO_VERIFICA > OK).
    """
    base, altura = _secao_retangular_p25(secao, concreto)
    gn = _pil._limites.gama_n_pilar(min(base, altura)) if aplicar_gama_n else 1.0
    Nd = float(Nd_kn) * gn
    Ac = secao.Ac_cm2
    fck, gc = concreto.fck_mpa, concreto.gama_c
    mt_x, mb_x = gn * float(M_topo_xx_kncm), gn * float(M_base_xx_kncm)
    mt_y, mb_y = gn * float(M_topo_yy_kncm), gn * float(M_base_yy_kncm)
    rx = _pil.pilar_padrao_direcao(Nd, le_xx_cm, altura, Ac, fck, mt_x, mb_x,
                                   metodo=metodo, tipo=tipo, aplicar_minimo=False,
                                   verificar_dispensa=True, direcao="xx", gama_c=gc)
    ry = _pil.pilar_padrao_direcao(Nd, le_yy_cm, base, Ac, fck, mt_y, mb_y,
                                   metodo=metodo_yy or metodo, tipo=tipo_yy or tipo,
                                   aplicar_minimo=False, verificar_dispensa=True,
                                   direcao="yy", gama_c=gc)

    memoria = [f"15.8.3.3.5: pilar-padrão nas duas direções (λx = {_fmt_vp25(rx.lambda_)}, "
               f"λy = {_fmt_vp25(ry.lambda_)}, ambos <= 90)."]
    if aplicar_gama_n:
        memoria.append(f"13.2.3: menor dimensão b = {_fmt_vp25(min(base, altura))} cm -> "
                       f"γn = {_fmt_vp25(gn)}; Nd = {_fmt_vp25(Nd)} kN e momentos multiplicados por γn.")
    memoria.extend(rx.memoria)
    memoria.extend(ry.memoria)

    alvo = (("A (topo)", mt_x, mt_y),
            ("intermediária", rx.sinal * rx.Md_tot_kncm, ry.sinal * ry.Md_tot_kncm),
            ("B (base)", mb_x, mb_y))
    secoes = []
    for nome, mx, my in alvo:
        r = _verificar_direcao(secao, concreto, aco, Nd, mx, my, n_grid, use_cpp)
        razao = r.get("razao", float("nan"))
        secoes.append({"secao": nome, "Mx_kncm": mx, "My_kncm": my,
                       "status": r["status"], "razao": razao, "mensagem": r.get("mensagem")})
        memoria.append(f"15.8.3.3.5: seção {nome}: Mx = {_fmt_vp25(mx)}, My = {_fmt_vp25(my)} kN·cm; "
                       f"MR/MS = {_fmt_vp25(razao)} -> {r['status']}.")

    env = None
    if verificar_minimo:
        env = verificar_envoltoria_minima_2a_ordem(
            secao, concreto, aco, Nd, le_xx_cm, le_yy_cm, metodo=metodo,
            segunda_ordem_xx=not rx.dispensa_2a_ordem,
            segunda_ordem_yy=not ry.dispensa_2a_ordem,
            n_pontos=n_pontos, n_grid=n_grid, use_cpp=use_cpp,
            metodo_yy=metodo_yy)
        memoria.extend(env.memoria)
    else:
        memoria.append("15.3.2: envoltória mínima não verificada (verificar_minimo=False).")

    estados = [s["status"] for s in secoes] + ([env.status] if env is not None else [])
    status = max(estados, key=lambda s: _PRIORIDADE[s])
    ok = status == "OK"
    candidatos = [(s["razao"], f"seção {s['secao']}") for s in secoes]
    if env is not None:
        candidatos.append((env.razao_min, "envoltória mínima com 2ª ordem"))
    validos = [c for c in candidatos if not math.isnan(c[0])]
    if validos:
        razao, onde = min(validos, key=lambda c: c[0])
        governante = f"{onde}: MR/MS = {_fmt_vp25(razao)}" + ("" if ok else f" — {status}")
    else:
        governante = status
    memoria.append(f"Resultado: {governante} -> {'ok' if ok else 'não ok'}.")
    return ResultadoPilarPadraoObliquo(
        gama_n=gn, Nd_kn=Nd, direcao_xx=rx, direcao_yy=ry, secoes=tuple(secoes),
        envoltoria_minima=env, status=status, ok=ok, governante=governante,
        memoria=tuple(memoria),
    )


# === P28: pilar-padrão acoplado a diagramas M, N, 1/r (15.8.3.3.4) e método geral (15.8.3.2) ===
from dataclasses import dataclass as _dataclass_p28

import numpy as _np_p28
from scipy.optimize import brentq as _brentq_p28

try:  # importado como pacote (dimensionamento.rotinas.verificacao_pilar)
    from . import momento_curvatura as _mc
except ImportError:  # executado como script
    from dimensionamento.rotinas import momento_curvatura as _mc

try:
    from dimensionamento import seguranca_nbr6118 as _seg_p28
except ImportError:  # executado com dimensionamento/ no sys.path
    import seguranca_nbr6118 as _seg_p28

LAMBDA_MAX_MN1R = 140.0   # 15.8.3.3.4 (PDF p. 130)
_ERROS_FAIXA_P28 = (nbr.FaixaNormativaError, _pil.nbr.FaixaNormativaError)


def _fmt_p28(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


def _geometria_p28(secao, concreto, eixo: str) -> tuple[float, float, float]:
    """(h, λ por unidade de ℓe, Ac) na direção do eixo: h = altura (x) ou base (y)."""
    base, altura = _secao_retangular_p25(secao, concreto)
    if eixo not in ("x", "y"):
        raise ValueError(f"eixo deve ser 'x' ou 'y', recebido {eixo!r}.")
    h, b = (altura, base) if eixo == "x" else (base, altura)
    Ac = b * h
    I = b * h ** 3 / 12.0
    return h, _pil.esbeltez(1.0, I, Ac), Ac


def _exigir_fluencia_p28(lam: float, ecc_cm, item: str) -> float:
    """15.8.3.1 e 15.8.4: λ > 90 exige a excentricidade de fluência ecc."""
    if ecc_cm is None:
        if lam > _pil.LAMBDA_FLUENCIA + _pil._TOL_P25:
            raise nbr.FaixaNormativaError(
                f"λ = {lam:.1f} > 90: a consideração da fluência é obrigatória (15.8.3.1 e "
                f"15.8.4). Passe ecc_cm, de pilares_nbr6118.ecc_fluencia_cm ({item})."
            )
        return 0.0
    ecc = float(ecc_cm)
    if ecc < 0.0 or math.isnan(ecc) or math.isinf(ecc):
        raise nbr.FaixaNormativaError(f"ecc = {ecc:g} cm inválido: tem de ser >= 0 (15.8.4).")
    return ecc


@_dataclass_p28(frozen=True)
class ResultadoPilarPadraoMN1r:
    """Pilar-padrão acoplado a diagramas M, N, 1/r numa direção (15.8.3.3.4)."""
    eixo: str
    h_cm: float
    le_cm: float
    lambda_: float
    lambda1: float
    dispensa_2a_ordem: bool
    MA_kncm: float
    MB_kncm: float
    alpha_b: float
    M1d_min_kncm: float
    ecc_cm: float
    M1d_A_ef_kncm: float            # max(|MA|, M1d,mín) + Nd·ecc
    curvatura_1_cm: float           # 1/r na seção crítica
    M2d_kncm: float
    gama_n1: float
    Md_tot_kncm: float              # valor absoluto (nan se instável)
    MRd_kncm: float
    estavel: bool
    diagrama: object                # DiagramaMNCurvatura
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def pilar_padrao_MN1r(
    secao,
    concreto,
    aco,
    Nd_kn: float,
    le_cm: float,
    MA_kncm: float,
    MB_kncm: float,
    eixo: str = "x",
    tipo: str = "biapoiado",
    ecc_cm: float | None = None,
    aplicar_minimo: bool = True,
    verificar_dispensa: bool = True,
    linearizar: bool = False,
    gama_f3: float = fco.GAMA_F3,
    n_pontos: int = 40,
    n_grid: int = 60,
) -> ResultadoPilarPadraoMN1r:
    """Pilar-padrão acoplado a diagramas M, N, 1/r (15.8.3.3.4, PDF p. 130).

    "A determinação dos esforços locais de 2ª ordem em pilares com λ <= 140
    pode ser feita pelo método do pilar-padrão [...], utilizando-se para a
    curvatura da seção crítica os valores obtidos de diagramas M, N, 1/r
    específicos para o caso." Mesma expressão de 15.8.3.3.2 (PDF p. 129):

        Md,tot = αb·M1d,A + Nd·(ℓe²/10)·(1/r) >= M1d,A

    com 1/r lido do diagrama M, N, 1/r da seção (``momento_curvatura``,
    curva AB de 15.3.1, pico 1,10·fcd e N = Nd/γf3) para o momento Md,tot/γf3
    (formulação Sd,tot = γf3·S(F/γf3) de 15.3.1). Como 1/r depende de
    Md,tot, a equação é resolvida por busca de raiz: a primeira raiz de
    f(M) = αb·M1d,A + Nd·ℓe²/10·(1/r)(M/γf3) − M é o equilíbrio estável.
    Sem raiz no diagrama (o momento passa do máximo da curva AB), o pilar
    é instável: ``estavel=False``, ``ok=False``.

    ``linearizar=True`` usa a reta AB, (1/r) = M/(γf3·(EI)sec), que "a
    favor da segurança pode ser linearizada" (15.3.1), e dá a forma fechada
    Md,tot = αb·M1d,A/[1 − Nd·ℓe²/(10·γf3·(EI)sec)].

    - λ = ℓe/i da seção bruta (15.8.2); λ > 140 levanta
      ``FaixaNormativaError`` (use o método geral, 15.8.3.2).
    - λ > 90: fluência obrigatória (15.8.4): ``ecc_cm`` (de
      ``pilares_nbr6118.ecc_fluencia_cm``) soma-se à excentricidade de
      1ª ordem, M1d,A = max(|MA|, M1d,mín) + Nd·ecc; sem ele, erro.
    - αb e λ1 de 15.8.2 e M1d,mín de 11.3.3.4.3, como em
      ``pilares_nbr6118.pilar_padrao_direcao`` (``aplicar_minimo`` e
      ``verificar_dispensa`` iguais aos de lá).
    - A seção crítica é verificada no ELU: Md,tot <= MRd (curva de
      0,85·ηc·fcd com NRd = Nd), por ``seguranca_nbr6118.verificar_seguranca``.

    Seção retangular (``SecaoRetangular``); ``eixo`` "x" (h = altura_cm) ou
    "y" (h = base_cm); Nd em kN (compressão positiva), ℓe em cm, momentos
    em kN·cm com sinal na convenção do kernel (MB positivo se tracionar a
    mesma face que MA). γn1 (15.8.1) vale 1,0 porque λ <= 140.
    """
    h, lam_por_le, Ac = _geometria_p28(secao, concreto, eixo)
    Nd = float(Nd_kn)
    if not (Nd > 0.0):
        raise nbr.FaixaNormativaError(
            f"Nd = {Nd:g} kN: o pilar-padrão vale para flexo-compressão (Nd > 0; 15.8.3.3.4)."
        )
    le = _pil._positivo_p25(le_cm, "ℓe", "15.8.3.3.4")
    lam = lam_por_le * le
    if lam > LAMBDA_MAX_MN1R + _pil._TOL_P25:
        raise nbr.FaixaNormativaError(
            f"λ = {lam:.1f} > 140: o pilar-padrão acoplado a diagramas M, N, 1/r só vale para "
            "λ <= 140 (15.8.3.3.4); acima disso o método geral é obrigatório (15.8.3.2)."
        )
    ecc = _exigir_fluencia_p28(lam, ecc_cm, "15.8.3.3.4")
    gf3 = float(gama_f3)

    MA, MB = float(MA_kncm), float(MB_kncm)
    if abs(MB) > abs(MA):
        MA, MB = MB, MA
    M1d_min = _pil.M1d_min_kncm(Nd, h)
    ab = _pil.alpha_b(MA, MB, tipo=tipo, M1d_min_kncm=M1d_min)
    if aplicar_minimo:
        M1dA, ab_ef, _ = _pil.M1d_A_efetivo(Nd, h, MA, ab)
    else:
        M1dA, ab_ef = abs(MA), ab
    M1dA_ef = M1dA + Nd * ecc
    e1 = abs(MA) / Nd
    lam1 = _pil.lambda1_limite(e1, h, ab_ef)
    dispensa = verificar_dispensa and lam < lam1
    sinal = -1.0 if MA < 0.0 else 1.0

    diag = _mc.diagrama_M_N_curvatura(secao, concreto, aco, Nd, n_pontos=n_pontos,
                                      eixo=eixo, sentido=sinal, gama_f3=gf3, n_grid=n_grid)
    memoria = [
        f"15.8.3.3.4 [{eixo}]: λ = ℓe/i = {_fmt_p28(lam)} (<= 140); ℓe = {_fmt_p28(le)} cm, h = {_fmt_p28(h)} cm.",
        f"15.8.2: MA = {_fmt_p28(MA)} kN·cm, MB = {_fmt_p28(MB)} kN·cm, tipo = {tipo}; αb = {_fmt_p28(ab_ef)}.",
        f"11.3.3.4.3: M1d,mín = Nd·(1,5 + 0,03h) = {_fmt_p28(M1d_min)} kN·cm"
        + ("; aplicado a M1d,A." if aplicar_minimo else "; não aplicado."),
        (f"15.8.4: ecc = {_fmt_p28(ecc)} cm; M1d,A = {_fmt_p28(M1dA)} + Nd·ecc = {_fmt_p28(M1dA_ef)} kN·cm."
         if ecc > 0.0 else f"15.8.4: sem excentricidade de fluência (λ = {_fmt_p28(lam)}); "
                           f"M1d,A = {_fmt_p28(M1dA_ef)} kN·cm."),
        f"15.8.2: λ1 = (25 + 12,5·e1/h)/αb, 35 <= λ1 <= 90, e1 = {_fmt_p28(e1)} cm -> λ1 = {_fmt_p28(lam1)}.",
    ]
    memoria.extend(diag.memoria)

    c2 = Nd * le * le / 10.0
    estavel = True
    if dispensa:
        cur, M2d, Md_tot = 0.0, 0.0, M1dA_ef
        memoria.append(f"15.8.2: λ = {_fmt_p28(lam)} < λ1 = {_fmt_p28(lam1)}: efeitos locais de 2ª ordem "
                       f"desprezados; Md,tot = M1d,A = {_fmt_p28(Md_tot)} kN·cm.")
    elif linearizar:
        den = 1.0 - c2 / (gf3 * diag.EI_sec_kncm2)
        if den <= 0.0:
            estavel = False
            cur, M2d, Md_tot = float("nan"), float("nan"), float("nan")
        else:
            Md_tot = ab_ef * M1dA_ef / den
            cur = Md_tot / (gf3 * diag.EI_sec_kncm2)
            M2d = Md_tot - ab_ef * M1dA_ef
        memoria.append("15.3.1: curva AB linearizada pela reta AB: 1/r = M/(γf3·(EI)sec); "
                       f"Md,tot = αb·M1d,A/[1 − Nd·ℓe²/(10·γf3·(EI)sec)] = {_fmt_p28(Md_tot)} kN·cm.")
    else:
        def f(M):
            return ab_ef * M1dA_ef + c2 * diag.curvatura(M / gf3) - M
        M_lo = ab_ef * M1dA_ef
        M_hi = gf3 * diag.M_max_curva_kncm
        if M_lo >= M_hi:
            estavel = False
        else:
            grade = _np_p28.linspace(M_lo, M_hi, 401)
            valores = [f(m) for m in grade]
            raiz = None
            for i in range(1, len(grade)):
                if valores[i - 1] >= 0.0 and valores[i] <= 0.0:
                    raiz = (_brentq_p28(f, grade[i - 1], grade[i], xtol=1e-9, rtol=1e-12)
                            if valores[i] < 0.0 else float(grade[i]))
                    break
            estavel = raiz is not None
        if estavel:
            Md_tot = raiz
            cur = diag.curvatura(Md_tot / gf3)
            M2d = c2 * cur
        else:
            cur, M2d, Md_tot = float("nan"), float("nan"), float("nan")
        memoria.append("15.8.3.3.4: Md,tot = αb·M1d,A + Nd·ℓe²/10·(1/r), 1/r do diagrama M, N, 1/r "
                       "para Md,tot/γf3 (15.3.1).")
    if estavel and not dispensa:
        M2d, gn1 = _pil.aplicar_gama_n1(M2d, lam)
        Md_tot = max(ab_ef * M1dA_ef + M2d, M1dA_ef)
        memoria.append(f"15.8.3.3.4: 1/r = {_fmt_p28(cur)} 1/cm; M2d = Nd·ℓe²/10·1/r = {_fmt_p28(M2d)} kN·cm; "
                       f"Md,tot = {_fmt_p28(ab_ef)} × {_fmt_p28(M1dA_ef)} + {_fmt_p28(M2d)} = "
                       f"{_fmt_p28(Md_tot)} kN·cm (>= M1d,A = {_fmt_p28(M1dA_ef)}).")
    else:
        gn1 = 1.0

    if not estavel:
        ok = False
        governante = ("instabilidade ou esgotamento da seção: não há equilíbrio na curva "
                      f"M, N, 1/r (Nd·ℓe²/10 = {_fmt_p28(c2)} kN·cm²)")
        memoria.append(f"15.8.3.3.4: {governante} -> não ok.")
    else:
        seg = _seg_p28.verificar_seguranca(diag.MRd_kncm, Md_tot, rotulo="MRd x Md,tot",
                                           item="15.8.3.3.4")
        ok = seg.ok
        governante = f"seção crítica: MRd = {_fmt_p28(diag.MRd_kncm)} kN·cm, Md,tot = {_fmt_p28(Md_tot)} kN·cm" + (
            "" if ok else " — não passa")
        memoria.extend(seg.memoria)
    return ResultadoPilarPadraoMN1r(
        eixo=eixo, h_cm=h, le_cm=le, lambda_=lam, lambda1=lam1, dispensa_2a_ordem=dispensa,
        MA_kncm=MA, MB_kncm=MB, alpha_b=ab_ef, M1d_min_kncm=M1d_min, ecc_cm=ecc,
        M1d_A_ef_kncm=M1dA_ef, curvatura_1_cm=cur, M2d_kncm=M2d, gama_n1=gn1,
        Md_tot_kncm=Md_tot, MRd_kncm=diag.MRd_kncm, estavel=estavel, diagrama=diag,
        ok=ok, governante=governante, memoria=tuple(memoria),
    )


@_dataclass_p28(frozen=True)
class ResultadoMetodoGeral:
    """Método geral de 2ª ordem de uma barra (15.8.3.2)."""
    eixo: str
    le_cm: float
    lambda_: float
    gama_n1: float
    ecc_cm: float
    n_segmentos: int
    x_cm: tuple[float, ...]          # posição a partir do topo
    y_cm: tuple[float, ...]          # deslocamento transversal (2ª ordem)
    M1d_kncm: tuple[float, ...]      # 1ª ordem (com mínimo e fluência)
    Md_tot_kncm: tuple[float, ...]   # M1d + γn1·Nd·y
    Md_tot_max_kncm: float           # maior valor absoluto
    x_Md_tot_max_cm: float
    M2d_max_kncm: float              # γn1·Nd·|y| máximo
    MRd_kncm: float                  # no sentido de Md,tot,máx
    convergiu: bool
    estavel: bool
    n_iter: int
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def metodo_geral_pilar(
    secao,
    concreto,
    aco,
    le_cm: float,
    Nd_kn: float,
    M1_topo_kncm: float,
    M1_base_kncm: float,
    n_segmentos: int = 20,
    eixo: str = "x",
    ecc_cm: float | None = None,
    aplicar_minimo: bool = True,
    gama_f3: float = fco.GAMA_F3,
    n_pontos: int = 40,
    n_grid: int = 60,
    tol_cm: float = 1e-7,
    iter_max: int = 2000,
    diagramas: tuple | None = None,
) -> ResultadoMetodoGeral:
    """Método geral: 2ª ordem local por discretização da barra (15.8.3.2, PDF p. 129).

    "Consiste na análise não linear de 2ª ordem efetuada com discretização
    adequada da barra, consideração da relação momento-curvatura real em
    cada seção e consideração da não linearidade geométrica de maneira não
    aproximada." Obrigatório para λ > 140.

    Modelo: barra birrotulada de comprimento ℓe, força normal Nd constante
    e momentos de 1ª ordem M1_topo (x = 0) e M1_base (x = ℓe), com variação
    linear entre eles. A barra é dividida em ``n_segmentos`` trechos iguais;
    em cada nó i:

        Md(xi) = M1d(xi) + Nd·y(xi)
        (1/r)i = curvatura do diagrama M, N, 1/r para Md(xi)/γf3 (15.3.1)
        y'' = −1/r,  y(0) = y(ℓe) = 0   (diferenças finitas centradas)

    A linha elástica é iterada (ponto fixo) até |Δy| < ``tol_cm``; o
    equilíbrio é tomado na geometria deformada, sem a aproximação senoidal
    do pilar-padrão. Se algum Md/γf3 passa do máximo da curva AB ou a
    iteração não converge, o pilar é instável (``estavel=False``, ``ok=False``).

    - Formulação de segurança de 15.3.1: curva AB com 1,10·fcd e Nd/γf3; os
      esforços majorados por γf3 dão Md = M1d + Nd·y, com a curvatura lida
      em Md/γf3.
    - λ = ℓe/i (15.8.2); λ > 200 só com Nd < 0,10·fcd·Ac (15.8.1,
      ``pilares_nbr6118.verificar_esbeltez_limite``); para λ > 140 a parcela
      de 2ª ordem é majorada por γn1 = 1 + (λ − 140)/140 (15.8.1):
      Md,tot = M1d + γn1·Nd·y.
    - λ > 90: fluência obrigatória (15.8.4); ``ecc_cm`` soma-se à
      excentricidade de 1ª ordem ao longo de toda a barra, no sentido do
      maior momento de extremidade.
    - ``aplicar_minimo``: se max(|M1_topo|, |M1_base|) < M1d,mín =
      Nd(1,5 + 0,03h) (11.3.3.4.3), usa-se M1d,mín uniforme na barra, no
      sentido do maior momento (equivale a αb = 1,0 de 15.8.2 d).
    - ELU: max |Md,tot| <= MRd (curva de ELU com NRd = Nd), por
      ``seguranca_nbr6118.verificar_seguranca``.

    ``diagramas`` aceita um par (sentido +, sentido −) já construído, por
    exemplo para reusar num laço; cada um precisa de ``curvatura(M)``,
    ``M_max_curva_kncm`` e ``MRd_kncm``. Seção retangular; ``eixo`` "x"
    (h = altura_cm) ou "y" (h = base_cm); kN, cm, kN·cm.
    """
    h, lam_por_le, Ac = _geometria_p28(secao, concreto, eixo)
    Nd = float(Nd_kn)
    if not (Nd > 0.0):
        raise nbr.FaixaNormativaError(
            f"Nd = {Nd:g} kN: o método geral de 15.8.3.2 é para barra comprimida (Nd > 0)."
        )
    le = _pil._positivo_p25(le_cm, "ℓe", "15.8.3.2")
    n = int(n_segmentos)
    if n < 4:
        raise ValueError("n_segmentos deve ser pelo menos 4 (discretização adequada, 15.8.3.2).")
    lam = lam_por_le * le
    lim = _pil.verificar_esbeltez_limite(lam, Nd, concreto.fck_mpa, Ac, concreto.gama_c)
    if not lim.ok:
        raise nbr.FaixaNormativaError(f"15.8.1: {lim.governante}.")
    ecc = _exigir_fluencia_p28(lam, ecc_cm, "15.8.3.2")
    gn1 = _pil.gama_n1(lam)
    gf3 = float(gama_f3)

    Mt, Mb = float(M1_topo_kncm), float(M1_base_kncm)
    MA = Mt if abs(Mt) >= abs(Mb) else Mb
    sinal = -1.0 if MA < 0.0 else 1.0
    M1d_min = _pil.M1d_min_kncm(Nd, h)
    memoria = [
        f"15.8.3.2 [{eixo}]: barra birrotulada de ℓe = {_fmt_p28(le)} cm em {n} trechos; "
        f"Nd = {_fmt_p28(Nd)} kN; λ = {_fmt_p28(lam)}.",
    ]
    memoria.extend(lim.memoria[:-1])
    if aplicar_minimo and abs(MA) < M1d_min:
        Mt = Mb = sinal * M1d_min
        memoria.append(f"11.3.3.4.3: max(|M1,topo|, |M1,base|) < M1d,mín = {_fmt_p28(M1d_min)} kN·cm: "
                       "M1d,mín uniforme na barra (15.8.2 d).")
    x = _np_p28.linspace(0.0, le, n + 1)
    M1 = Mt + (Mb - Mt) * x / le + sinal * Nd * ecc
    if ecc > 0.0:
        memoria.append(f"15.8.4: ecc = {_fmt_p28(ecc)} cm; Nd·ecc = {_fmt_p28(Nd * ecc)} kN·cm somado a M1d.")

    if diagramas is None:
        dpos = _mc.diagrama_M_N_curvatura(secao, concreto, aco, Nd, n_pontos, eixo, 1.0, gf3, n_grid)
        dneg = _mc.diagrama_M_N_curvatura(secao, concreto, aco, Nd, n_pontos, eixo, -1.0, gf3, n_grid)
        memoria.extend(dpos.memoria)
    else:
        dpos, dneg = diagramas

    # Operador de 2ª diferença nos nós internos: (y[i-1] − 2y[i] + y[i+1])/Δ² = −k[i].
    dx = le / n
    m = n - 1
    A = (_np_p28.diag(-2.0 * _np_p28.ones(m)) + _np_p28.diag(_np_p28.ones(m - 1), 1)
         + _np_p28.diag(_np_p28.ones(m - 1), -1)) / (dx * dx)
    A_inv = _np_p28.linalg.inv(A)

    def curvaturas(M):
        k = _np_p28.empty_like(M)
        for i, Mi in enumerate(M):
            dg = dpos if Mi >= 0.0 else dneg
            k[i] = (1.0 if Mi >= 0.0 else -1.0) * dg.curvatura(abs(Mi) / gf3)
        return k

    y = _np_p28.zeros(n + 1)
    convergiu = estavel = False
    passou_curva = False
    it = 0
    try:
        for it in range(1, int(iter_max) + 1):
            M = M1 + Nd * y
            k = curvaturas(M)
            y_novo = _np_p28.zeros(n + 1)
            y_novo[1:-1] = A_inv @ (-k[1:-1])
            dy = float(_np_p28.max(_np_p28.abs(y_novo - y)))
            y = y_novo
            if not _np_p28.all(_np_p28.isfinite(y)):
                break
            if dy < float(tol_cm):
                convergiu = estavel = True
                break
    except _ERROS_FAIXA_P28:
        convergiu = estavel = False
        passou_curva = True

    M2 = gn1 * Nd * y
    Mtot = M1 + M2
    i_max = int(_np_p28.argmax(_np_p28.abs(Mtot)))
    Mmax = float(abs(Mtot[i_max]))
    MRd = (dpos if Mtot[i_max] >= 0.0 else dneg).MRd_kncm
    if gn1 > 1.0:
        memoria.append(f"15.8.1: λ > 140: parcela de 2ª ordem majorada por γn1 = {_fmt_p28(gn1)}.")
    if not estavel:
        ok = False
        governante = ("instabilidade ou esgotamento da seção: o momento passa do máximo "
                      f"da curva M, N, 1/r na iteração {it}" if passou_curva else
                      f"instabilidade: a linha elástica não converge em {it} iterações")
        memoria.append(f"15.8.3.2: {governante} -> não ok.")
    else:
        memoria.append(f"15.8.3.2: convergência em {it} iterações (|Δy| < {_fmt_p28(tol_cm)} cm); "
                       f"y,máx = {_fmt_p28(float(_np_p28.max(_np_p28.abs(y))))} cm.")
        memoria.append(f"15.8.3.2: Md,tot,máx = {_fmt_p28(Mmax)} kN·cm em x = {_fmt_p28(float(x[i_max]))} cm "
                       f"(M1d = {_fmt_p28(float(M1[i_max]))}, M2d = {_fmt_p28(float(M2[i_max]))} kN·cm).")
        seg = _seg_p28.verificar_seguranca(MRd, Mmax, rotulo="MRd x Md,tot,máx", item="15.8.3.2")
        ok = seg.ok
        governante = (f"seção x = {_fmt_p28(float(x[i_max]))} cm: MRd = {_fmt_p28(MRd)} kN·cm, "
                      f"Md,tot = {_fmt_p28(Mmax)} kN·cm" + ("" if ok else " — não passa"))
        memoria.extend(seg.memoria)
    return ResultadoMetodoGeral(
        eixo=eixo, le_cm=le, lambda_=lam, gama_n1=gn1, ecc_cm=ecc, n_segmentos=n,
        x_cm=tuple(float(v) for v in x), y_cm=tuple(float(v) for v in y),
        M1d_kncm=tuple(float(v) for v in M1), Md_tot_kncm=tuple(float(v) for v in Mtot),
        Md_tot_max_kncm=Mmax, x_Md_tot_max_cm=float(x[i_max]),
        M2d_max_kncm=float(_np_p28.max(_np_p28.abs(M2))), MRd_kncm=MRd,
        convergiu=convergiu, estavel=estavel, n_iter=it, ok=ok,
        governante=governante, memoria=tuple(memoria),
    )
