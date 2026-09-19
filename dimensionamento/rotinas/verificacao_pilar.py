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
