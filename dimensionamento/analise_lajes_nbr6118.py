"""Análise de lajes por grelha e por pórtico equivalente (ABNT NBR 6118:2026, 14.7).

Módulo do pacote P45 do plano de implementação. Calcula laje nervurada e
laje lisa pelos processos que a norma prescreve, sobre o cálculo de barras
do P44 (``analise_barras_nbr6118``). Itens cobertos (páginas do PDF):

    - 14.7.3.1 Valores de rigidez (p. 116): rigidez do estádio I, com o
      módulo secante, na verificação de deformação excessiva de placas, só
      com os momentos abaixo do de fissuração; senão, fissuração e fluência
      pela Seção 17 (P8). ``verificar_rigidez_estadio_I``.
    - 14.7.7   Lajes nervuradas (p. 117-118): fora das condições de 13.2.4.2,
      a capa é laje maciça apoiada numa grelha de vigas
      (``grelha_nervurada``); as unidirecionais são calculadas na direção
      das nervuras, sem rigidez transversal e sem rigidez à torção
      (``nervurada_unidirecional``).
    - 14.7.8   Lajes-cogumelo (p. 118): análise de laje lisa por
      procedimento numérico, aqui a grelha equivalente
      (``grelha_equivalente_laje_lisa``); e o processo elástico aproximado
      dos pórticos múltiplos, com a carga total em cada direção e a
      repartição entre as faixas da Figura 14.9 (``portico_equivalente``,
      com as condições de uso em
      ``verificar_condicoes_portico_equivalente``).

Dependências: P44 (``Modelo``, ``resolver``), P14 (largura colaborante e
rigidez à torção reduzida em ``analise_linear_nbr6118``), P17 (repartição
entre faixas em ``lajes_nbr6118.repartir_momentos_faixas``), P10
(classificação da nervurada de 13.2.4.2 em
``limites_geometricos_nbr6118.classificar_laje_nervurada``) e P8 (momento
de fissuração e rigidez equivalente em ``els_deformacao_nbr6118``).

Unidades: coordenadas, vãos e seções em cm; carga de superfície em kN/m²;
forças em kN; momentos em kN·cm (por barra) e em kN·m/m (por unidade de
largura, numericamente igual a kN·cm/cm); módulos em MPa; deslocamentos em
cm. Convenção de sinais: a do P44 — a carga da gravidade é −Z (grelha) ou
−Y (pórtico plano), e o momento positivo é o de vão (traciona a face
inferior).

A análise não tem valor esperado na norma: os testes usam solução fechada
(placa de Timoshenko, viga contínua, pórtico simétrico) e o equilíbrio, que
o P44 confere em todo resultado.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
    import analise_barras_nbr6118 as ab
    import analise_linear_nbr6118 as al
    import lajes_nbr6118 as laj
    import limites_geometricos_nbr6118 as lg
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr
    from dimensionamento import analise_barras_nbr6118 as ab
    from dimensionamento import analise_linear_nbr6118 as al
    from dimensionamento import lajes_nbr6118 as laj
    from dimensionamento import limites_geometricos_nbr6118 as lg

FaixaNormativaError = nbr.FaixaNormativaError

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
POISSON_PLACA = 0.2   # 14.7.3 (p. 116): teoria da elasticidade com ν = 0,2

# 14.7.8 (p. 118) só diz "vãos pouco diferentes", sem número. O critério
# adotado aqui é o de vãos sucessivos com diferença de no máximo um terço do
# maior (menor/maior >= 2/3); é escolha da biblioteca, declarada, e pode ser
# mudada por argumento.
RAZAO_MINIMA_VAOS_PORTICO = 2.0 / 3.0

BORDAS = ("x0", "x1", "y0", "y1")
CONDICOES_BORDA = ("apoio", "engaste", "livre")

_TOL = 1e-9


def _fmt(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


# ---------------------------------------------------------------------------
# 14.7.3.1 — Rigidez do estádio I em placas (PDF p. 116)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoRigidezEstadioI:
    M_max_kncm: float
    Mr_kncm: float
    razao: float
    usar_estadio_I: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_rigidez_estadio_I(M_max_kncm, Mr_kncm: float) -> ResultadoRigidezEstadioI:
    """Autoriza a rigidez do estádio I na flecha de placa (14.7.3.1, PDF p. 116).

    Regra (texto da norma): na verificação do estado-limite de deformação
    excessiva de placas, podem ser usados valores de rigidez do estádio I,
    com o módulo de elasticidade secante do concreto (Ecs·Ic), desde que os
    momentos fletores sejam menores que o de fissuração:

        |M| < Mr   em todas as seções   →   rigidez Ecs·Ic
        |M| ≥ Mr   em alguma seção      →   fissuração e fluência pela
                                            Seção 17 (P8)

    M_max_kncm: momento da combinação de serviço da verificação de flecha
    (número ou sequência de momentos; vale o maior em módulo), kN·cm, ou
    kN·cm/cm por unidade de largura. Pode vir da grelha deste módulo
    (``ResultadoGrelhaLaje``) ou de um programa externo.
    Mr_kncm: momento de fissuração na mesma unidade (17.3.1, com fct,m:
    ``els_deformacao_nbr6118.momento_fissuracao_kncm``).

    A desigualdade é estrita, como no texto ("menores que"). ``ok`` é True
    quando a rigidez bruta está autorizada; com ``ok`` False, a flecha tem
    de usar a rigidez equivalente de 17.3.2.1.1
    (``els_deformacao_nbr6118.rigidez_equivalente_kncm2``) e a fluência de
    17.3.2.1.2 (``els_deformacao_nbr6118.alpha_f``).
    """
    if isinstance(M_max_kncm, (int, float)):
        valores = [float(M_max_kncm)]
    else:
        valores = [float(v) for v in np.ravel(np.asarray(M_max_kncm, dtype=float))]
    if not valores:
        raise ValueError("M_max_kncm vazio.")
    if Mr_kncm <= 0.0:
        raise FaixaNormativaError(f"Mr = {_fmt(Mr_kncm)} kN·cm: o momento de fissuração tem de ser positivo.")
    M = max(abs(v) for v in valores)
    razao = M / Mr_kncm
    usar = M < Mr_kncm
    memoria = [
        f"14.7.3.1 (p. 116): |M|máx = {_fmt(M)} kN·cm; Mr = {_fmt(Mr_kncm)} kN·cm; "
        f"|M|/Mr = {_fmt(razao)}.",
    ]
    if usar:
        memoria.append("|M|máx < Mr: permitida a rigidez do estádio I (Ecs·Ic, seção bruta) na "
                       "verificação de deformação excessiva da placa.")
        governante = "estádio I (14.7.3.1)"
    else:
        memoria.append("|M|máx ≥ Mr: a rigidez bruta não é permitida; considerar a fissuração e a "
                       "fluência pela Seção 17 (17.3.2.1, rigidez equivalente e αf; P8).")
        governante = "fissuração: Seção 17 (P8)"
    return ResultadoRigidezEstadioI(M_max_kncm=M, Mr_kncm=float(Mr_kncm), razao=razao,
                                    usar_estadio_I=usar, ok=usar, governante=governante,
                                    memoria=tuple(memoria))


# ---------------------------------------------------------------------------
# Seção T da nervura — 14.6.2.2 (P14) e 14.7.7 (PDF p. 118)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SecaoNervura:
    """Seção T (ou L) da nervura, bruta (14.6.4.1).

    bf_cm: largura colaborante da mesa (14.6.2.2, P14). yt_cm: distância do
    centroide à fibra inferior (tracionada no momento positivo). ys_cm: do
    centroide à fibra superior. secao: ``analise_barras_nbr6118.Secao`` com
    A, I (flexão no plano vertical) e J.
    """

    bw_cm: float
    h_cm: float
    hf_cm: float
    bf_cm: float
    A_cm2: float
    I_cm4: float
    J_cm4: float
    yt_cm: float
    ys_cm: float
    secao: object


def secao_T_nervura(bw_cm: float, h_cm: float, hf_cm: float, bf_cm: float) -> SecaoNervura:
    """Propriedades brutas da seção T da nervura (14.6.4.1 e 14.7.7).

    A = bf·hf + bw·(h − hf); centroide pela média das áreas; I pelo teorema
    de Steiner. J (torção de Saint-Venant) pela soma dos retângulos da alma
    (bw × h) e das abas (bf − bw) × hf, cada um com
    ``analise_barras_nbr6118.constante_torcao_retangulo_cm4`` — a
    aproximação usual de seção aberta composta; a norma não dá fórmula.
    Com bf = bw a seção é retangular.

    Faixa: bw, h, hf > 0; hf < h; bf ≥ bw.
    """
    if bw_cm <= 0.0 or h_cm <= 0.0 or hf_cm <= 0.0:
        raise FaixaNormativaError("bw, h e hf da nervura têm de ser positivos.")
    if hf_cm >= h_cm:
        raise FaixaNormativaError(f"hf = {_fmt(hf_cm)} cm tem de ser menor que h = {_fmt(h_cm)} cm.")
    if bf_cm < bw_cm - _TOL:
        raise FaixaNormativaError(f"bf = {_fmt(bf_cm)} cm menor que bw = {_fmt(bw_cm)} cm.")
    hw = h_cm - hf_cm
    A1, A2 = bf_cm * hf_cm, bw_cm * hw
    A = A1 + A2
    y1, y2 = hf_cm / 2.0, hf_cm + hw / 2.0          # a partir do topo
    ys = (A1 * y1 + A2 * y2) / A
    I = (bf_cm * hf_cm ** 3 / 12.0 + A1 * (ys - y1) ** 2
         + bw_cm * hw ** 3 / 12.0 + A2 * (ys - y2) ** 2)
    J = ab.constante_torcao_retangulo_cm4(bw_cm, h_cm)
    if bf_cm - bw_cm > _TOL:
        J += ab.constante_torcao_retangulo_cm4(bf_cm - bw_cm, hf_cm)
    sec = ab.Secao(A_cm2=A, I_cm4=I, I2_cm4=hf_cm * bf_cm ** 3 / 12.0 + hw * bw_cm ** 3 / 12.0,
                   J_cm4=J)
    return SecaoNervura(bw_cm=bw_cm, h_cm=h_cm, hf_cm=hf_cm, bf_cm=bf_cm, A_cm2=A, I_cm4=I,
                        J_cm4=J, yt_cm=h_cm - ys, ys_cm=ys, secao=sec)


def largura_colaborante_nervura_cm(bw_cm: float, espacamento_cm: float, a_cm: float,
                                   borda: bool = False) -> float:
    """Largura colaborante da nervura (14.6.2.2, Figura 14.2, PDF p. 109-110; P14).

    A nervura tem vizinhas a ``espacamento_cm`` entre eixos, então
    b2 = espaçamento − bw dos dois lados, e bf = bw + b1 + b3 com
    b1, b3 ≤ 0,5·b2 e ≤ 0,1·a (``analise_linear_nbr6118.largura_colaborante_cm``).
    Com ``borda=True`` (nervura de borda livre), a mesa só existe de um lado:
    seção L, b4 = 0.

    a_cm: distância entre pontos de momento nulo (``analise_linear_nbr6118.vao_a_para_mesa``).
    """
    if espacamento_cm <= bw_cm:
        raise FaixaNormativaError(
            f"Espaçamento entre eixos {_fmt(espacamento_cm)} cm ≤ bw = {_fmt(bw_cm)} cm.")
    b2 = espacamento_cm - bw_cm
    if borda:
        return al.largura_colaborante_cm(bw_cm, b2, 0.0, a_cm, borda=True, b4_cm=0.0)
    return al.largura_colaborante_cm(bw_cm, b2, b2, a_cm)


# ---------------------------------------------------------------------------
# Geração da malha
# ---------------------------------------------------------------------------
def _linhas(L: float, n: int, extras: Iterable[float] = ()) -> np.ndarray:
    """Coordenadas das linhas da malha de 0 a L: divisão uniforme em n mais
    as coordenadas obrigatórias (pilares), sem duplicar."""
    pts = list(np.linspace(0.0, L, n + 1)) + [float(e) for e in extras]
    pts = sorted(pts)
    saida = [pts[0]]
    tol = 1e-6 * max(L, 1.0)
    for p in pts[1:]:
        if p - saida[-1] > tol:
            saida.append(p)
        else:
            # mantém a coordenada obrigatória (pilar) no lugar da uniforme
            if any(abs(p - e) <= tol for e in extras):
                saida[-1] = p
    return np.array(saida)


def _larguras_tributarias(c: np.ndarray) -> np.ndarray:
    """Largura de influência de cada linha: metade do espaço até as vizinhas."""
    w = np.zeros(len(c))
    d = np.diff(c)
    w[:-1] += d / 2.0
    w[1:] += d / 2.0
    return w


def _validar_bordas(bordas: dict | None, padrao: str) -> dict:
    b = {k: padrao for k in BORDAS}
    for k, v in (bordas or {}).items():
        if k not in BORDAS:
            raise ValueError(f"Borda {k!r} inválida: use {', '.join(BORDAS)}.")
        cv = nbr._chave(v)
        if cv not in CONDICOES_BORDA:
            raise ValueError(f"Condição {v!r} inválida: use {', '.join(CONDICOES_BORDA)}.")
        b[k] = cv
    return b


def _no_id(i: int, j: int) -> tuple:
    return (i, j)


@dataclass(frozen=True)
class PilarLajeLisa:
    """Pilar sob a laje lisa, apoio elástico da grelha equivalente (14.7.8).

    x_cm, y_cm: posição do eixo. bx_cm, by_cm: dimensões da seção nas
    direções X e Y. h_inf_cm, h_sup_cm: altura do lance abaixo e acima da
    laje (None = não existe). extremo_engastado: extremo oposto do lance
    engastado (rigidez 4·E·I/h) ou articulado (3·E·I/h). rigido_vertical:
    apoio vertical rígido (True) ou mola axial E·A/h_inf (False).
    """

    x_cm: float
    y_cm: float
    bx_cm: float
    by_cm: float
    h_inf_cm: float | None = 280.0
    h_sup_cm: float | None = None
    extremo_engastado: bool = True
    rigido_vertical: bool = True

    def __post_init__(self):
        if self.bx_cm <= 0.0 or self.by_cm <= 0.0:
            raise FaixaNormativaError("Dimensões do pilar têm de ser positivas.")
        for h in (self.h_inf_cm, self.h_sup_cm):
            if h is not None and h <= 0.0:
                raise FaixaNormativaError("Altura de lance de pilar tem de ser positiva.")
        if not self.rigido_vertical and self.h_inf_cm is None:
            raise FaixaNormativaError("Mola axial exige o lance inferior (h_inf_cm).")


def rigidez_rotacao_pilar_kncm_rad(E_mpa: float, I_cm4: float, h_cm: float,
                                   extremo_engastado: bool = True) -> float:
    """Rigidez à rotação do topo (ou da base) de um lance de pilar, kN·cm/rad.

    k = 4·E·I/h com o extremo oposto engastado; 3·E·I/h com ele articulado
    (resistência dos materiais; E em MPa, convertido para kN/cm² dividindo
    por 10). É a mola de rotação do pilar como apoio elástico da laje
    (14.7.8, PDF p. 118).
    """
    if E_mpa <= 0.0 or I_cm4 <= 0.0 or h_cm <= 0.0:
        raise FaixaNormativaError("E, I e h do pilar têm de ser positivos.")
    return (4.0 if extremo_engastado else 3.0) * (E_mpa / 10.0) * I_cm4 / h_cm


def _molas_pilar(p: PilarLajeLisa, E_mpa: float) -> tuple[dict, list[str]]:
    """Molas do pilar no nó da grelha: rx (flexão no plano YZ, I = bx·by³/12)
    e ry (plano XZ, I = by·bx³/12), somando os lances inferior e superior;
    uz como mola axial se ``rigido_vertical`` for False."""
    molas = {}
    mem = []
    Ix = p.bx_cm * p.by_cm ** 3 / 12.0   # giro em torno de X
    Iy = p.by_cm * p.bx_cm ** 3 / 12.0   # giro em torno de Y
    kx = ky = 0.0
    for h in (p.h_inf_cm, p.h_sup_cm):
        if h is not None:
            kx += rigidez_rotacao_pilar_kncm_rad(E_mpa, Ix, h, p.extremo_engastado)
            ky += rigidez_rotacao_pilar_kncm_rad(E_mpa, Iy, h, p.extremo_engastado)
    if kx > 0.0:
        molas["rx"] = kx
        molas["ry"] = ky
        mem.append(f"Pilar ({_fmt(p.x_cm)}; {_fmt(p.y_cm)}) {_fmt(p.bx_cm)}×{_fmt(p.by_cm)} cm: "
                   f"molas de rotação kθx = {_fmt(kx)} e kθy = {_fmt(ky)} kN·cm/rad "
                   f"({'4' if p.extremo_engastado else '3'}·E·I/h por lance).")
    if not p.rigido_vertical:
        molas["uz"] = (E_mpa / 10.0) * p.bx_cm * p.by_cm / p.h_inf_cm
        mem.append(f"   mola axial kz = E·A/h = {_fmt(molas['uz'])} kN/cm.")
    return molas, mem


# ---------------------------------------------------------------------------
# Resultado das grelhas
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoGrelhaLaje:
    """Resultado de ``grelha_nervurada`` e ``grelha_equivalente_laje_lisa``.

    xs_cm, ys_cm: linhas da malha. largura_barra_cm: {id da barra: largura
    representada (faixa ou espaçamento das nervuras)}. modelo, analise: o
    ``Modelo`` e o ``ResultadoAnalise`` do P44. w_max_cm: maior deslocamento
    vertical em módulo (seção bruta, sem fissuração nem fluência).
    M_x_pos_kncm, M_x_neg_kncm (e _y_): maior momento positivo e negativo
    nas barras paralelas a X (e a Y), por barra. m_x_pos_knm_por_m etc.:
    na grelha de nervuras, os mesmos divididos pela largura representada
    pela barra; na grelha equivalente, os extremos dos momentos nodais com
    a correção de Poisson (kN·m/m = kN·cm/cm).
    reacoes_pilares: {índice do pilar: reação vertical, kN}.
    momentos_nodais: {nó (i, j): (mx, my)} em kN·m/m (só grelha
    equivalente).
    """

    xs_cm: tuple
    ys_cm: tuple
    largura_barra_cm: dict
    modelo: object
    analise: object
    w_max_cm: float
    M_x_pos_kncm: float
    M_x_neg_kncm: float
    M_y_pos_kncm: float
    M_y_neg_kncm: float
    m_x_pos_knm_por_m: float
    m_x_neg_knm_por_m: float
    m_y_pos_knm_por_m: float
    m_y_neg_knm_por_m: float
    reacoes_pilares: dict
    carga_total_kn: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]
    momentos_nodais: dict = field(default_factory=dict)

    def deslocamento_cm(self, x_cm: float, y_cm: float) -> float:
        """Deslocamento vertical do nó da malha mais próximo de (x, y), cm."""
        i = int(np.argmin(np.abs(np.asarray(self.xs_cm) - x_cm)))
        j = int(np.argmin(np.abs(np.asarray(self.ys_cm) - y_cm)))
        return self.analise.deslocamentos[_no_id(i, j)]["uz"]


def _extremos_momento(analise, largura: dict, direcao_barra: dict):
    """Maiores momentos positivo e negativo por direção, por barra e por
    unidade de largura."""
    out = {"x": [0.0, 0.0, 0.0, 0.0], "y": [0.0, 0.0, 0.0, 0.0]}
    for bid, rb in analise.barras.items():
        d = direcao_barra[bid]
        M = rb.M
        mpos, mneg = float(np.max(M)), float(np.min(M))
        w = largura[bid]
        o = out[d]
        o[0] = max(o[0], mpos)
        o[1] = min(o[1], mneg)
        o[2] = max(o[2], mpos / w)
        o[3] = min(o[3], mneg / w)
    return out


def _momentos_nodais(analise, nx: int, ny: int, larg_x, larg_y, nu: float) -> dict:
    """Momentos por unidade de largura em cada nó da grelha equivalente:
    média dos momentos de extremidade das barras de cada direção que chegam
    ao nó, divididos pela largura, com a correção de Poisson
    mx = Mx/b + ν·My/b e my = My/b + ν·Mx/b (kN·cm/cm = kN·m/m)."""
    br = analise.barras
    out = {}
    for i in range(nx):
        for j in range(ny):
            vx = []
            if i > 0:
                vx.append(br[("x", i - 1, j)].extremidade_j["My"])
            if i < nx - 1:
                vx.append(br[("x", i, j)].extremidade_i["My"])
            vy = []
            if j > 0:
                vy.append(br[("y", i, j - 1)].extremidade_j["My"])
            if j < ny - 1:
                vy.append(br[("y", i, j)].extremidade_i["My"])
            kx = float(np.mean(vx)) / larg_x[j] if vx else 0.0
            ky = float(np.mean(vy)) / larg_y[i] if vy else 0.0
            out[_no_id(i, j)] = (kx + nu * ky, ky + nu * kx)
    return out


def _montar_grelha(xs, ys, secao_x, secao_y, largura_x, largura_y, material, fator_GJ,
                   bordas, omitir_barras_apoiadas: bool):
    """Monta o modelo de grelha com barras nas linhas xs (paralelas a Y) e ys
    (paralelas a X). secao_x(j) é a seção da barra paralela a X na linha
    ys[j]; secao_y(i), da paralela a Y na linha xs[i]."""
    m = ab.Modelo("grelha")
    nx, ny = len(xs), len(ys)
    for i in range(nx):
        for j in range(ny):
            m.no(_no_id(i, j), xs[i], ys[j])
    largura, direcao = {}, {}
    borda_linha_y = {0: bordas["y0"], ny - 1: bordas["y1"]}
    borda_linha_x = {0: bordas["x0"], nx - 1: bordas["x1"]}
    for j in range(ny):
        if omitir_barras_apoiadas and borda_linha_y.get(j, "livre") != "livre":
            continue
        s = secao_x(j)
        for i in range(nx - 1):
            bid = ("x", i, j)
            m.barra(bid, _no_id(i, j), _no_id(i + 1, j), s, material, fator_GJ=fator_GJ)
            largura[bid], direcao[bid] = largura_x[j], "x"
    for i in range(nx):
        if omitir_barras_apoiadas and borda_linha_x.get(i, "livre") != "livre":
            continue
        s = secao_y(i)
        for j in range(ny - 1):
            bid = ("y", i, j)
            m.barra(bid, _no_id(i, j), _no_id(i, j + 1), s, material, fator_GJ=fator_GJ)
            largura[bid], direcao[bid] = largura_y[i], "y"
    # apoios de borda
    for i in range(nx):
        for j in range(ny):
            graus = []
            for chave, cond in (("x0", i == 0), ("x1", i == nx - 1), ("y0", j == 0), ("y1", j == ny - 1)):
                if not cond or bordas[chave] == "livre":
                    continue
                graus.append("uz")
                if bordas[chave] == "engaste":
                    graus.append("ry" if chave[0] == "x" else "rx")
            if graus:
                m.apoio(_no_id(i, j), *sorted(set(graus)))
    return m, largura, direcao


def _carga_nodal_area(m, xs, ys, q_kn_m2: float, nome: str) -> tuple:
    """Carga de superfície q (kN/m²) nos nós, pela área de influência de cada
    nó (retângulo das meias distâncias às linhas vizinhas). A soma das
    cargas nodais é q·área, exata."""
    caso = ab.CasoCarga(nome)
    wx, wy = _larguras_tributarias(np.asarray(xs)), _larguras_tributarias(np.asarray(ys))
    total = 0.0
    q = q_kn_m2 / 1.0e4   # kN/cm²
    for i in range(len(xs)):
        for j in range(len(ys)):
            F = q * wx[i] * wy[j]
            if F != 0.0:
                caso.nodal(_no_id(i, j), Fz=-F)
                total += F
    return caso, total


# ---------------------------------------------------------------------------
# 14.7.7 — Laje nervurada como grelha de vigas (PDF p. 118)
# ---------------------------------------------------------------------------
def grelha_nervurada(Lx_cm: float, Ly_cm: float, ex_cm: float, ey_cm: float,
                     bw_cm: float, h_cm: float, hf_cm: float, fck_mpa: float,
                     q_kn_m2: float, bordas: dict | None = None,
                     a_x_cm: float | None = None, a_y_cm: float | None = None,
                     fator_torcao: float | None = None,
                     largura_media_nervura_cm: float | None = None,
                     alpha_e: float = 1.0) -> ResultadoGrelhaLaje:
    """Laje nervurada bidirecional calculada como grelha de vigas (14.7.7,
    PDF p. 118).

    Texto da norma: as prescrições de laje maciça valem para a nervurada que
    obedece a 13.2.4.2; quando essas hipóteses não forem verificadas, a laje
    nervurada é analisada com a capa como laje maciça apoiada numa grelha
    de vigas. Esta função gera a grelha das nervuras e a resolve pelo P44.

    Geometria: painel retangular Lx × Ly (cm, entre eixos de apoio), com
    nervuras paralelas a X espaçadas de ey e paralelas a Y espaçadas de ex
    (entre eixos). O número de nervuras é arredondado para que caibam
    inteiras no painel, e o espaçamento efetivo vai para a memória. Cada
    nervura é uma barra de seção T (``secao_T_nervura``) com a largura
    colaborante de 14.6.2.2 (``largura_colaborante_nervura_cm``, P14):
    b2 = e − bw, e a = a_x_cm (nervuras paralelas a X) ou a_y_cm; o padrão é
    o vão, como em viga biapoiada (``vao_a_para_mesa``). As nervuras sobre
    borda apoiada ou engastada não entram (a viga de apoio é outro
    elemento); as de borda livre entram com seção L.

    bordas: {'x0', 'x1', 'y0', 'y1'} -> 'apoio' (padrão), 'engaste' ou
    'livre'; x0 é a borda x = 0, e assim por diante.
    fator_torcao: fator sobre o GJ elástico das nervuras; o padrão é o de
    14.6.6.2 para vigas de grelha de concreto armado, 0,15
    (``analise_barras_nbr6118.fator_rigidez_torcao``, P14).
    q_kn_m2: carga de superfície total (peso próprio incluído), aplicada nos
    nós pela área de influência.

    Classificação de 13.2.4.2 (P10, ``classificar_laje_nervurada``) com o
    maior espaçamento: a memória diz se a mesa precisa de verificação à
    flexão e se ela é laje maciça apoiada na grelha (espaçamento > 110 cm),
    caso em que a capa se calcula como laje maciça de vão igual ao
    espaçamento (P17).

    Deslocamentos com seção bruta e Ecs (14.6.4.1): para flecha, ver
    ``verificar_rigidez_estadio_I`` e o P8.
    """
    for nome, v in (("Lx", Lx_cm), ("Ly", Ly_cm), ("ex", ex_cm), ("ey", ey_cm)):
        if v <= 0.0:
            raise FaixaNormativaError(f"{nome} = {_fmt(v)} cm tem de ser positivo.")
    if q_kn_m2 < 0.0:
        raise FaixaNormativaError("q_kn_m2 não pode ser negativa.")
    brd = _validar_bordas(bordas, "apoio")
    if all(v == "livre" for v in brd.values()):
        raise FaixaNormativaError("Painel sem nenhuma borda apoiada: grelha hipostática.")
    nx = max(1, int(round(Lx_cm / ex_cm)))
    ny = max(1, int(round(Ly_cm / ey_cm)))
    xs, ys = _linhas(Lx_cm, nx), _linhas(Ly_cm, ny)
    ex_ef, ey_ef = Lx_cm / nx, Ly_cm / ny
    ax = Lx_cm if a_x_cm is None else a_x_cm
    ay = Ly_cm if a_y_cm is None else a_y_cm
    mat = ab.Material.concreto(fck_mpa, alpha_e)
    fGJ = ab.fator_rigidez_torcao() if fator_torcao is None else float(fator_torcao)
    if fGJ < 0.0:
        raise FaixaNormativaError("fator_torcao não pode ser negativo.")

    bf_x = largura_colaborante_nervura_cm(bw_cm, ey_ef, ax)
    bf_y = largura_colaborante_nervura_cm(bw_cm, ex_ef, ay)
    bf_x_b = largura_colaborante_nervura_cm(bw_cm, ey_ef, ax, borda=True)
    bf_y_b = largura_colaborante_nervura_cm(bw_cm, ex_ef, ay, borda=True)
    sx, sy = secao_T_nervura(bw_cm, h_cm, hf_cm, bf_x), secao_T_nervura(bw_cm, h_cm, hf_cm, bf_y)
    sxb = secao_T_nervura(bw_cm, h_cm, hf_cm, bf_x_b)
    syb = secao_T_nervura(bw_cm, h_cm, hf_cm, bf_y_b)
    nyl, nxl = len(ys), len(xs)

    def secao_x(j):
        return (sxb if j in (0, nyl - 1) else sx).secao

    def secao_y(i):
        return (syb if i in (0, nxl - 1) else sy).secao

    # largura representada por barra: o espaçamento (metade na borda)
    larg_x = _larguras_tributarias(ys)
    larg_y = _larguras_tributarias(xs)
    m, largura, direcao = _montar_grelha(xs, ys, secao_x, secao_y, larg_x, larg_y, mat, fGJ, brd,
                                         omitir_barras_apoiadas=True)
    caso, total = _carga_nodal_area(m, xs, ys, q_kn_m2, "q (grelha de nervuras)")
    r = ab.resolver(m, caso)
    ext = _extremos_momento(r, largura, direcao)
    wmax = max(abs(d["uz"]) for d in r.deslocamentos.values())

    clas = lg.classificar_laje_nervurada(max(ex_ef, ey_ef), largura_media_nervura_cm)
    memoria = [
        "14.7.7 (p. 118): laje nervurada analisada como grelha de vigas (nervuras), com a capa "
        "como laje maciça apoiada na grelha.",
        f"Painel {_fmt(Lx_cm)} × {_fmt(Ly_cm)} cm; {nx + 1} linhas em X e {ny + 1} em Y; "
        f"espaçamento efetivo ex = {_fmt(ex_ef)} cm, ey = {_fmt(ey_ef)} cm.",
        f"Seção T das nervuras: bw = {_fmt(bw_cm)} cm, h = {_fmt(h_cm)} cm, hf = {_fmt(hf_cm)} cm; "
        f"bf (14.6.2.2) = {_fmt(bf_x)} cm nas paralelas a X (a = {_fmt(ax)} cm) e "
        f"{_fmt(bf_y)} cm nas paralelas a Y (a = {_fmt(ay)} cm).",
        f"I = {_fmt(sx.I_cm4)} cm⁴ (X) e {_fmt(sy.I_cm4)} cm⁴ (Y); GJ multiplicado por "
        f"{_fmt(fGJ)} (14.6.6.2).",
        mat.descricao,
        f"Bordas: {', '.join(f'{k} = {v}' for k, v in brd.items())}.",
        f"Carga q = {_fmt(q_kn_m2)} kN/m² nos nós por área de influência: total {_fmt(total)} kN.",
    ]
    memoria += list(clas.memoria)
    if clas.mesa_como_laje_macica:
        memoria.append("Espaçamento > 110 cm: a capa deve ser calculada como laje maciça apoiada "
                       "nas nervuras (13.2.4.2 c e 14.7.7), com vão igual ao espaçamento.")
    memoria += [
        f"Momentos por nervura: X de {_fmt(ext['x'][1])} a {_fmt(ext['x'][0])} kN·cm; "
        f"Y de {_fmt(ext['y'][1])} a {_fmt(ext['y'][0])} kN·cm.",
        f"Deslocamento máximo (seção bruta, Ecs) = {_fmt(wmax)} cm; a flecha exige 14.7.3.1 e a "
        "Seção 17.",
    ]
    return ResultadoGrelhaLaje(
        xs_cm=tuple(float(v) for v in xs), ys_cm=tuple(float(v) for v in ys),
        largura_barra_cm=largura, modelo=m, analise=r, w_max_cm=wmax,
        M_x_pos_kncm=ext["x"][0], M_x_neg_kncm=ext["x"][1],
        M_y_pos_kncm=ext["y"][0], M_y_neg_kncm=ext["y"][1],
        m_x_pos_knm_por_m=ext["x"][2], m_x_neg_knm_por_m=ext["x"][3],
        m_y_pos_knm_por_m=ext["y"][2], m_y_neg_knm_por_m=ext["y"][3],
        reacoes_pilares={}, carga_total_kn=total, ok=True,
        governante=f"categoria {clas.categoria} (13.2.4.2)", memoria=tuple(memoria))


# ---------------------------------------------------------------------------
# 14.7.7 — Laje nervurada unidirecional (PDF p. 118)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoNervuradaUnidirecional:
    """Resultado de ``nervurada_unidirecional``.

    vaos_cm: vãos da nervura. secoes: seção T de cada vão. M_apoios_kncm:
    momento em cada apoio (eixo), por nervura. M_vao_max_kncm: maior
    momento positivo de cada vão, por nervura. reacoes_kn: reação de cada
    apoio, por nervura. m_*_knm_por_m: os mesmos por metro de largura
    (divididos pelo espaçamento). modelo, analise: do P44.
    """

    vaos_cm: tuple
    espacamento_cm: float
    carga_nervura_kn_m: float
    secoes: tuple
    M_apoios_kncm: tuple
    M_vao_max_kncm: tuple
    reacoes_kn: tuple
    m_apoios_knm_por_m: tuple
    m_vao_max_knm_por_m: tuple
    modelo: object
    analise: object
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def _momento_max_vao(rb) -> float:
    """Maior momento no vão: nas estações e no ponto de cortante nulo."""
    M = rb.M
    mx = float(np.max(M))
    V = rb.V
    x = rb.x_cm
    for k in range(len(x) - 1):
        if V[k] == 0.0 or V[k] * V[k + 1] < 0.0:
            # cortante muda de sinal: refina por bisseção
            a, b = x[k], x[k + 1]
            va = rb.em(a)
            key = "Vy" if rb.plano_principal == "y" else "Vz"
            for _ in range(60):
                c = 0.5 * (a + b)
                vc = rb.em(c)
                if vc[key] * va[key] <= 0.0:
                    b = c
                else:
                    a, va = c, vc
            key_m = "Mz" if rb.plano_principal == "y" else "My"
            mx = max(mx, rb.em(0.5 * (a + b))[key_m])
    return mx


def nervurada_unidirecional(vaos_cm: Sequence[float], espacamento_cm: float, bw_cm: float,
                            h_cm: float, hf_cm: float, fck_mpa: float, q_kn_m2: float,
                            engaste_inicio: bool = False, engaste_fim: bool = False,
                            a_cm: Sequence[float] | None = None,
                            largura_media_nervura_cm: float | None = None,
                            alpha_e: float = 1.0) -> ResultadoNervuradaUnidirecional:
    """Laje nervurada unidirecional calculada na direção das nervuras
    (14.7.7, PDF p. 118).

    Texto da norma: as lajes nervuradas unidirecionais devem ser calculadas
    segundo a direção das nervuras, desprezadas a rigidez transversal e a
    rigidez à torção. Cada nervura é, então, uma viga contínua independente
    (pórtico plano do P44, sem ligação com as vizinhas e sem torção), com a
    carga da sua faixa: q_nervura = q·espaçamento (kN/m² × m = kN/m).

    vaos_cm: vãos sucessivos entre eixos de apoio. Apoios extremos
    articulados, salvo ``engaste_inicio``/``engaste_fim``.
    Seção T de cada vão com a largura colaborante de 14.6.2.2
    (``largura_colaborante_nervura_cm``, P14): a = a_cm[k] se dado; senão
    ``vao_a_para_mesa``, com 'biapoiada' no vão único, 'continua' (0,75·L)
    nos vãos extremos e 'continua-intermediaria' (0,60·L) nos internos.

    Classificação de 13.2.4.2 pelo espaçamento (P10) na memória. Os
    momentos saem por nervura (kN·cm) e por metro de largura (kN·m/m).
    """
    vaos = [float(v) for v in vaos_cm]
    if not vaos or any(v <= 0.0 for v in vaos):
        raise FaixaNormativaError("vaos_cm: lista de vãos positivos.")
    if espacamento_cm <= 0.0:
        raise FaixaNormativaError("Espaçamento entre nervuras tem de ser positivo.")
    if q_kn_m2 < 0.0:
        raise FaixaNormativaError("q_kn_m2 não pode ser negativa.")
    n = len(vaos)
    if a_cm is not None and len(a_cm) != n:
        raise ValueError("a_cm deve ter um valor por vão.")
    mat = ab.Material.concreto(fck_mpa, alpha_e)
    secoes = []
    for k, L in enumerate(vaos):
        if a_cm is not None:
            a = float(a_cm[k])
        elif n == 1:
            a = al.vao_a_para_mesa(L, "biapoiada")
        elif k in (0, n - 1):
            a = al.vao_a_para_mesa(L, "continua")
        else:
            a = al.vao_a_para_mesa(L, "continua-intermediaria")
        bf = largura_colaborante_nervura_cm(bw_cm, espacamento_cm, a)
        secoes.append(secao_T_nervura(bw_cm, h_cm, hf_cm, bf))

    m = ab.Modelo("portico_plano")
    x = 0.0
    m.no(0, 0.0, 0.0)
    for k, L in enumerate(vaos):
        x += L
        m.no(k + 1, x, 0.0)
        m.barra(k, k, k + 1, secoes[k].secao, mat)
    m.apoio(0, "ux", "uy", *(("rz",) if engaste_inicio else ()))
    for k in range(1, n + 1):
        m.apoio(k, "uy", *(("rz",) if (k == n and engaste_fim) else ()))
    qn = q_kn_m2 * espacamento_cm / 100.0      # kN/m por nervura
    caso = ab.CasoCarga("q (nervura)")
    for k in range(n):
        caso.distribuida(k, -qn, direcao="Y")
    r = ab.resolver(m, caso, n_estacoes=41)

    M_ap = [r.barras[0].extremidade_i["Mz"]] + [r.barras[k].extremidade_j["Mz"] for k in range(n)]
    M_vao = [_momento_max_vao(r.barras[k]) for k in range(n)]
    reac = [r.reacoes[k]["uy"] for k in range(n + 1)]
    e_m = espacamento_cm / 100.0
    clas = lg.classificar_laje_nervurada(espacamento_cm, largura_media_nervura_cm)
    memoria = [
        "14.7.7 (p. 118): laje nervurada unidirecional calculada na direção das nervuras, "
        "desprezadas a rigidez transversal e a rigidez à torção: cada nervura é uma viga "
        "contínua independente.",
        f"Espaçamento {_fmt(espacamento_cm)} cm; q = {_fmt(q_kn_m2)} kN/m² → "
        f"q·e = {_fmt(qn)} kN/m por nervura.",
        f"Vãos: {'; '.join(_fmt(v) for v in vaos)} cm; bf (14.6.2.2) por vão: "
        f"{'; '.join(_fmt(s.bf_cm) for s in secoes)} cm.",
        mat.descricao,
    ]
    memoria += list(clas.memoria)
    memoria += [
        f"Momentos nos apoios (por nervura): {'; '.join(_fmt(v) for v in M_ap)} kN·cm.",
        f"Momentos máximos nos vãos (por nervura): {'; '.join(_fmt(v) for v in M_vao)} kN·cm.",
    ]
    return ResultadoNervuradaUnidirecional(
        vaos_cm=tuple(vaos), espacamento_cm=float(espacamento_cm), carga_nervura_kn_m=qn,
        secoes=tuple(secoes), M_apoios_kncm=tuple(float(v) for v in M_ap),
        M_vao_max_kncm=tuple(float(v) for v in M_vao), reacoes_kn=tuple(float(v) for v in reac),
        m_apoios_knm_por_m=tuple(float(v) / 100.0 / e_m for v in M_ap),
        m_vao_max_knm_por_m=tuple(float(v) / 100.0 / e_m for v in M_vao),
        modelo=m, analise=r, ok=True, governante=f"categoria {clas.categoria} (13.2.4.2)",
        memoria=tuple(memoria))


# ---------------------------------------------------------------------------
# 14.7.8 — Laje lisa por grelha equivalente (PDF p. 118)
# ---------------------------------------------------------------------------
def grelha_equivalente_laje_lisa(Lx_cm: float, Ly_cm: float, h_cm: float, fck_mpa: float,
                                 q_kn_m2: float, pilares: Sequence[PilarLajeLisa] = (),
                                 n_div_x: int = 12, n_div_y: int | None = None,
                                 bordas: dict | None = None, torcao: str = "isotropica",
                                 fator_torcao: float = 1.0,
                                 alpha_e: float = 1.0) -> ResultadoGrelhaLaje:
    """Laje lisa (ou maciça) calculada por grelha equivalente (14.7.8, PDF p. 118).

    Texto da norma: a análise estrutural de lajes lisas e cogumelo deve ser
    feita por procedimento numérico adequado, por exemplo diferenças
    finitas, elementos finitos, grelha equivalente ou elementos de contorno.
    Esta função é a grelha equivalente.

    Malha: painel retangular Lx × Ly (cm) dividido em ``n_div_x`` ×
    ``n_div_y`` faixas (padrão n_div_y = n_div_x), mais as linhas que passam
    pelos pilares. Cada linha é uma barra que representa a faixa de laje de
    largura b (metade da distância às linhas vizinhas; metade disso na
    borda), com:

        rigidez à flexão:  E·I, I = b·h³/12 e E = Ecs/(1 − ν²), isto é, a
                           rigidez de placa D = Ecs·h³/[12·(1 − ν²)] por
                           unidade de largura;
        rigidez à torção:  G·J, J = b·h³/6 e G = Gc = Ecs/[2·(1 + ν)]
                           (8.2.9), o que dá G·h³/6 = D·(1 − ν) por unidade
                           de largura, a rigidez à torção da placa
                           (``torcao="placa"``). Com ``torcao="isotropica"``
                           (padrão), a rigidez à torção por unidade de
                           largura é D (fator 1/(1 − ν) sobre a da placa):
                           a grelha não tem o acoplamento de Poisson, e é
                           assim que a soma das rigidezes à torção das duas
                           direções (2·D) iguala o termo 2·H = 2·D da
                           equação da placa isótropa D·∇⁴w = q. Com
                           "placa", a grelha fica cerca de 12 % mais
                           flexível que a placa (ν = 0,2). ``fator_torcao``
                           multiplica o resultado (padrão 1,0: a redução de
                           14.6.6.2 é de vigas, não de placa).

    Momentos por unidade de largura nos nós (``momentos_nodais``): média
    dos momentos das barras que chegam ao nó, divididos pela largura, com a
    correção de Poisson da placa: mx = Mx/b + ν·My/b e my = My/b + ν·Mx/b
    (as barras têm M/b = D·κ). Os extremos m_x_pos_knm_por_m etc. são os
    desses momentos nodais.

    ν = 0,2 (14.7.3 e 8.2.9). Módulo Ecs (14.6.4.1).

    pilares: ``PilarLajeLisa``, apoios elásticos — apoio vertical (rígido ou
    mola axial) e molas de rotação iguais à rigidez dos lances de pilar
    (``rigidez_rotacao_pilar_kncm_rad``). Pilares entram como apoio pontual
    no eixo; o pico de momento sobre o pilar depende da malha (arredonde
    com 14.6.3, P14, se for o caso).
    bordas: {'x0', 'x1', 'y0', 'y1'} -> 'livre' (padrão da laje lisa),
    'apoio' ou 'engaste' (parede ou viga rígida).
    q_kn_m2: carga total de superfície, aplicada nos nós por área de
    influência.

    A aproximação da grelha converge para a solução de placa com o
    refinamento, mas não reproduz o acoplamento de Poisson dos momentos:
    os testes declaram a tolerância contra a solução de Timoshenko.
    Deslocamentos com seção bruta: para flecha, ``verificar_rigidez_estadio_I``
    e o P8.
    """
    for nome, v in (("Lx", Lx_cm), ("Ly", Ly_cm), ("h", h_cm)):
        if v <= 0.0:
            raise FaixaNormativaError(f"{nome} = {_fmt(v)} cm tem de ser positivo.")
    if q_kn_m2 < 0.0:
        raise FaixaNormativaError("q_kn_m2 não pode ser negativa.")
    if fator_torcao < 0.0:
        raise FaixaNormativaError("fator_torcao não pode ser negativo.")
    chave_t = nbr._chave(torcao)
    if chave_t not in ("isotropica", "placa"):
        raise ValueError("torcao deve ser 'isotropica' ou 'placa'.")
    n_div_y = n_div_x if n_div_y is None else n_div_y
    if n_div_x < 1 or n_div_y < 1:
        raise ValueError("n_div_x e n_div_y têm de ser ≥ 1.")
    brd = _validar_bordas(bordas, "livre")
    pilares = list(pilares)
    for p in pilares:
        if not (-_TOL <= p.x_cm <= Lx_cm + _TOL and -_TOL <= p.y_cm <= Ly_cm + _TOL):
            raise FaixaNormativaError(f"Pilar em ({_fmt(p.x_cm)}; {_fmt(p.y_cm)}) fora do painel.")
    if not pilares and all(v == "livre" for v in brd.values()):
        raise FaixaNormativaError("Laje sem pilares e sem bordas apoiadas: grelha hipostática.")
    xs = _linhas(Lx_cm, n_div_x, (p.x_cm for p in pilares))
    ys = _linhas(Ly_cm, n_div_y, (p.y_cm for p in pilares))

    Ecs = nbr.Ecs(fck_mpa, alpha_e)
    G = nbr.Gc(fck_mpa, alpha_e)
    nu = POISSON_PLACA
    E_flex = Ecs / (1.0 - nu ** 2)
    # Material da barra: Ecs e Gc; fator_EI leva Ecs a Ecs/(1 − ν²)
    mat = ab.Material(E_mpa=Ecs, G_mpa=G, descricao=(
        f"Concreto C{_fmt(fck_mpa)}: Ecs = {_fmt(Ecs)} MPa, Gc = {_fmt(G)} MPa (8.2.8 e 8.2.9); "
        f"ν = 0,2 (14.7.3)"))
    fator_EI = 1.0 / (1.0 - nu ** 2)
    fator_GJ = fator_torcao * (1.0 / (1.0 - nu) if chave_t == "isotropica" else 1.0)
    larg_x, larg_y = _larguras_tributarias(ys), _larguras_tributarias(xs)

    def sec(b):
        return ab.Secao(A_cm2=b * h_cm, I_cm4=b * h_cm ** 3 / 12.0, J_cm4=b * h_cm ** 3 / 6.0)

    m = ab.Modelo("grelha")
    nx, ny = len(xs), len(ys)
    for i in range(nx):
        for j in range(ny):
            m.no(_no_id(i, j), xs[i], ys[j])
    largura, direcao = {}, {}
    for j in range(ny):
        s = sec(larg_x[j])
        for i in range(nx - 1):
            bid = ("x", i, j)
            m.barra(bid, _no_id(i, j), _no_id(i + 1, j), s, mat, fator_EI=fator_EI,
                    fator_GJ=fator_GJ)
            largura[bid], direcao[bid] = larg_x[j], "x"
    for i in range(nx):
        s = sec(larg_y[i])
        for j in range(ny - 1):
            bid = ("y", i, j)
            m.barra(bid, _no_id(i, j), _no_id(i, j + 1), s, mat, fator_EI=fator_EI,
                    fator_GJ=fator_GJ)
            largura[bid], direcao[bid] = larg_y[i], "y"
    for i in range(nx):
        for j in range(ny):
            graus = []
            for chave, cond in (("x0", i == 0), ("x1", i == nx - 1), ("y0", j == 0), ("y1", j == ny - 1)):
                if cond and brd[chave] != "livre":
                    graus.append("uz")
                    if brd[chave] == "engaste":
                        graus.append("ry" if chave[0] == "x" else "rx")
            if graus:
                m.apoio(_no_id(i, j), *sorted(set(graus)))

    mem_pil = []
    nos_pilar = {}
    tol = 1e-6 * max(Lx_cm, Ly_cm)
    for k, p in enumerate(pilares):
        i = int(np.argmin(np.abs(xs - p.x_cm)))
        j = int(np.argmin(np.abs(ys - p.y_cm)))
        if abs(xs[i] - p.x_cm) > tol or abs(ys[j] - p.y_cm) > tol:
            raise RuntimeError("Pilar fora das linhas da malha.")   # não ocorre: linhas incluem os pilares
        no = _no_id(i, j)
        if no in nos_pilar.values():
            raise ValueError(f"Dois pilares no mesmo ponto ({_fmt(p.x_cm)}; {_fmt(p.y_cm)}).")
        nos_pilar[k] = no
        molas, mm = _molas_pilar(p, Ecs)
        mem_pil += mm
        restr = set(m.apoios.get(no, set()))
        graus = [] if (not p.rigido_vertical or 2 in restr) else ["uz"]
        molas = {g: v for g, v in molas.items() if ab._IDX[g] not in restr}
        m.apoio(no, *graus, molas=molas)

    caso, total = _carga_nodal_area(m, xs, ys, q_kn_m2, "q (grelha equivalente)")
    r = ab.resolver(m, caso)
    ext = _extremos_momento(r, largura, direcao)
    mnod = _momentos_nodais(r, nx, ny, larg_x, larg_y, nu)
    mxs = [v[0] for v in mnod.values()]
    mys = [v[1] for v in mnod.values()]
    ext["x"][2], ext["x"][3] = max(0.0, max(mxs)), min(0.0, min(mxs))
    ext["y"][2], ext["y"][3] = max(0.0, max(mys)), min(0.0, min(mys))
    wmax = max(abs(d["uz"]) for d in r.deslocamentos.values())
    reac = {k: r.reacoes[no]["uz"] for k, no in nos_pilar.items() if "uz" in r.reacoes.get(no, {})}

    memoria = [
        "14.7.8 (p. 118): laje analisada por procedimento numérico — grelha equivalente.",
        f"Painel {_fmt(Lx_cm)} × {_fmt(Ly_cm)} cm, h = {_fmt(h_cm)} cm; malha de {nx} × {ny} linhas.",
        mat.descricao + ".",
        f"Flexão: I = b·h³/12 com E = Ecs/(1 − ν²) = {_fmt(E_flex)} MPa (rigidez de placa D); "
        f"torção: J = b·h³/6 com Gc × {_fmt(fator_GJ)} "
        f"({'D por unidade de largura, equação da placa isótropa' if chave_t == 'isotropica' else 'D·(1 − ν), rigidez à torção da placa'}).",
        "Momentos nodais por unidade de largura com a correção de Poisson: mx = Mx/b + ν·My/b.",
        f"Bordas: {', '.join(f'{k} = {v}' for k, v in brd.items())}; {len(pilares)} pilar(es) "
        "como apoios elásticos.",
    ]
    memoria += mem_pil
    memoria += [
        f"Carga q = {_fmt(q_kn_m2)} kN/m² nos nós por área de influência: total {_fmt(total)} kN.",
        f"mx de {_fmt(ext['x'][3])} a {_fmt(ext['x'][2])} kN·m/m; my de {_fmt(ext['y'][3])} a "
        f"{_fmt(ext['y'][2])} kN·m/m.",
        f"Deslocamento máximo (seção bruta, Ecs) = {_fmt(wmax)} cm; a flecha exige 14.7.3.1 e a "
        "Seção 17.",
        "Verificar a punção (19.5) e as ligações laje-pilar, obrigatoriamente os momentos de "
        "ligação com os pilares extremos (14.7.8).",
    ]
    return ResultadoGrelhaLaje(
        xs_cm=tuple(float(v) for v in xs), ys_cm=tuple(float(v) for v in ys),
        largura_barra_cm=largura, modelo=m, analise=r, w_max_cm=wmax,
        M_x_pos_kncm=ext["x"][0], M_x_neg_kncm=ext["x"][1],
        M_y_pos_kncm=ext["y"][0], M_y_neg_kncm=ext["y"][1],
        m_x_pos_knm_por_m=ext["x"][2], m_x_neg_knm_por_m=ext["x"][3],
        m_y_pos_knm_por_m=ext["y"][2], m_y_neg_knm_por_m=ext["y"][3],
        reacoes_pilares=reac, carga_total_kn=total, ok=True, governante="grelha equivalente",
        memoria=tuple(memoria), momentos_nodais=mnod)


# ---------------------------------------------------------------------------
# 14.7.8 — Pórtico equivalente (pórticos múltiplos) (PDF p. 118)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoCondicoesPortico:
    xs_cm: tuple
    ys_cm: tuple
    vaos_x_cm: tuple
    vaos_y_cm: tuple
    filas_ortogonais: bool
    vaos_pouco_diferentes: bool
    razao_minima_vaos: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def _agrupar(valores, tol) -> list[float]:
    grupos: list[list[float]] = []
    for v in sorted(valores):
        if grupos and v - grupos[-1][-1] <= tol:
            grupos[-1].append(v)
        else:
            grupos.append([v])
    return [float(np.mean(g)) for g in grupos]


def verificar_condicoes_portico_equivalente(
        pilares_xy: Sequence[tuple[float, float]], tol_alinhamento_cm: float = 1.0,
        razao_minima_vaos: float = RAZAO_MINIMA_VAOS_PORTICO,
        concreto_armado: bool = True) -> ResultadoCondicoesPortico:
    """Condições de uso do processo elástico aproximado dos pórticos
    múltiplos (14.7.8, PDF p. 118).

    Texto da norma: nas lajes em concreto armado em que os pilares estiverem
    dispostos em filas ortogonais, de maneira regular e com vãos pouco
    diferentes, os esforços podem ser calculados pelo processo elástico
    aproximado, com redistribuição, de pórticos múltiplos em cada direção.

    Verifica:
      1. concreto armado (``concreto_armado``); laje protendida não se
         enquadra no texto;
      2. filas ortogonais regulares: as coordenadas X dos pilares formam
         colunas e as Y formam linhas (agrupadas com ``tol_alinhamento_cm``),
         e há um pilar em cada cruzamento de linha e coluna;
      3. vãos pouco diferentes: a norma não dá número; o critério adotado
         (escolha da biblioteca) é que, em cada direção, vãos sucessivos
         tenham menor/maior ≥ ``razao_minima_vaos`` (padrão 2/3, isto é,
         diferença de no máximo um terço do maior).

    ``ok`` False quer dizer que o processo não se aplica e a laje deve ir
    para um procedimento numérico (``grelha_equivalente_laje_lisa``).
    """
    pts = [(float(x), float(y)) for x, y in pilares_xy]
    if len(pts) < 4:
        raise FaixaNormativaError("O pórtico equivalente exige ao menos 2 × 2 pilares.")
    if not (0.0 < razao_minima_vaos <= 1.0):
        raise FaixaNormativaError("razao_minima_vaos tem de estar em (0; 1].")
    xs = _agrupar([p[0] for p in pts], tol_alinhamento_cm)
    ys = _agrupar([p[1] for p in pts], tol_alinhamento_cm)
    memoria = []
    ocupados = set()
    alinhados = True
    for x, y in pts:
        i = int(np.argmin([abs(x - v) for v in xs]))
        j = int(np.argmin([abs(y - v) for v in ys]))
        if abs(x - xs[i]) > tol_alinhamento_cm or abs(y - ys[j]) > tol_alinhamento_cm:
            alinhados = False
        ocupados.add((i, j))
    completo = len(ocupados) == len(xs) * len(ys) and len(pts) == len(ocupados)
    filas = alinhados and completo and len(xs) >= 2 and len(ys) >= 2
    memoria.append(
        f"14.7.8 (p. 118): {len(pts)} pilares em {len(xs)} fila(s) paralela(s) a Y e {len(ys)} "
        "paralela(s) a X: " + ("filas ortogonais regulares." if filas else
                               "os pilares não formam filas ortogonais regulares completas."))
    vx, vy = tuple(np.diff(xs)), tuple(np.diff(ys))
    razoes = []
    for v in (vx, vy):
        for a, b in zip(v[:-1], v[1:]):
            razoes.append(min(a, b) / max(a, b))
    rmin = min(razoes) if razoes else 1.0
    pouco_dif = rmin >= razao_minima_vaos - _TOL
    memoria.append(
        f"Vãos em X: {'; '.join(_fmt(v) for v in vx)} cm; em Y: {'; '.join(_fmt(v) for v in vy)} cm; "
        f"menor razão entre vãos sucessivos = {_fmt(rmin)} "
        f"({'≥' if pouco_dif else '<'} {_fmt(razao_minima_vaos)}, critério adotado para "
        "\"vãos pouco diferentes\", que a norma não quantifica).")
    if not concreto_armado:
        memoria.append("14.7.8 prevê os pórticos múltiplos só para lajes em concreto armado.")
    ok = filas and pouco_dif and concreto_armado
    if ok:
        governante = "pórtico equivalente aplicável"
    elif not concreto_armado:
        governante = "laje não é de concreto armado"
    elif not filas:
        governante = "pilares fora de filas ortogonais"
    else:
        governante = "vãos muito diferentes"
    if not ok:
        memoria.append("O processo dos pórticos múltiplos não se aplica: usar procedimento "
                       "numérico (grelha equivalente).")
    return ResultadoCondicoesPortico(
        xs_cm=tuple(xs), ys_cm=tuple(ys), vaos_x_cm=vx, vaos_y_cm=vy, filas_ortogonais=filas,
        vaos_pouco_diferentes=pouco_dif, razao_minima_vaos=rmin, ok=ok, governante=governante,
        memoria=tuple(memoria))


@dataclass(frozen=True)
class FaixasVao:
    """Momentos de um vão de um pórtico e a repartição da Figura 14.9.

    M_neg_i_kncm, M_neg_j_kncm: momentos nos apoios (eixo dos pilares) do
    início e do fim do vão; M_pos_kncm: maior momento positivo. faixas:
    {'M_neg_i' | 'M_neg_j' | 'M_pos': {'faixa_externa_<lado>': valor,
    'faixa_interna_<lado>': valor}}, lado 'a' (lado de coordenada menor) e
    'b' (maior). A soma de cada grupo é o momento do pórtico.
    """

    vao: int
    L_cm: float
    M_neg_i_kncm: float
    M_neg_j_kncm: float
    M_pos_kncm: float
    faixas: dict


@dataclass(frozen=True)
class PorticoLinha:
    direcao: str
    coordenada_cm: float
    largura_a_cm: float
    largura_b_cm: float
    carga_kn_m: float
    vaos: tuple
    momentos_pilares_kncm: dict
    reacoes_kn: dict
    analise: object


@dataclass(frozen=True)
class ResultadoPorticoEquivalente:
    condicoes: ResultadoCondicoesPortico
    porticos: tuple
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def _repartir(M: float, tipo: str, wa: float, wb: float) -> dict:
    """Reparte o momento do pórtico entre as faixas de cada lado da fila de
    pilares (Figura 14.9, via ``lajes_nbr6118.repartir_momentos_faixas``, P17).

    Cada lado recebe a fração da sua largura, s = w_lado/(wa + wb). Dentro
    do lado, o momento 2·s·M é repartido pela Figura 14.9 como se fosse o de
    um painel inteiro: a faixa externa (a de largura l2/4 junto à fila de
    pilares) recebe a parcela de uma faixa externa, e a meia faixa interna
    a metade das internas. Com lados iguais, isto é exatamente 27,5 % / 45 %
    (positivos) e 37,5 % / 25 % (negativos) do momento do pórtico.
    """
    w = wa + wb
    out = {}
    for lado, wl in (("a", wa), ("b", wb)):
        if wl <= 0.0:
            continue
        rep = laj.repartir_momentos_faixas(2.0 * wl / w * M, tipo)
        out[f"faixa_externa_{lado}"] = rep["faixa_externa"]
        out[f"faixa_interna_{lado}"] = rep["faixas_internas"] / 2.0
    return out


def portico_equivalente(pilares_xy: Sequence[tuple[float, float]], h_laje_cm: float,
                        fck_mpa: float, q_kn_m2: float, bx_pilar_cm: float, by_pilar_cm: float,
                        h_inf_cm: float | None = 280.0, h_sup_cm: float | None = None,
                        direcao: str = "ambas", balanco_a_cm: float = 0.0,
                        balanco_b_cm: float = 0.0, tol_alinhamento_cm: float = 1.0,
                        razao_minima_vaos: float = RAZAO_MINIMA_VAOS_PORTICO,
                        concreto_armado: bool = True, alpha_e: float = 1.0,
                        n_estacoes: int = 41) -> ResultadoPorticoEquivalente:
    """Laje lisa ou cogumelo pelo processo elástico aproximado dos pórticos
    múltiplos (14.7.8, PDF p. 118).

    Texto da norma: com os pilares em filas ortogonais regulares e vãos
    pouco diferentes (conferido antes por
    ``verificar_condicoes_portico_equivalente``; se não atender, levanta
    ``FaixaNormativaError``), adotam-se, em cada direção, pórticos múltiplos;
    para cada pórtico deve ser considerada a carga total, e os momentos são
    distribuídos entre as faixas da Figura 14.9:

        a) 45 % dos momentos positivos para as duas faixas internas;
        b) 27,5 % dos momentos positivos para cada faixa externa;
        c) 25 % dos momentos negativos para as duas faixas internas;
        d) 37,5 % dos momentos negativos para cada faixa externa.

    Montagem (uma por fila de pilares e por direção): pórtico plano do P44
    com a laje como viga de largura l2 = la + lb (la, lb: metade do vão
    transversal de cada lado da fila, ou o balanço na fila de borda),
    I = l2·h³/12 e carga total q·l2; e os pilares da fila, com o lance
    inferior (h_inf_cm) e o superior (h_sup_cm, se houver), engastados no
    outro extremo, com I = b_transversal·b_na_direção³/12. Os momentos de
    ligação laje-pilar saem do próprio pórtico, como a norma exige nos
    pilares extremos.

    Repartição: ``lajes_nbr6118.repartir_momentos_faixas`` (P17), aplicada
    a cada lado da fila na proporção da largura (ver ``_repartir``): a
    faixa externa de cada lado é a de largura l2/4 junto aos pilares, e a
    interna, a meia faixa central restante. Na fila de borda sem balanço
    só existe um lado.

    A norma fala em processo "com redistribuição": os momentos daqui são os
    elásticos; a redistribuição, se feita, segue 14.6.4.3 e 14.7.3.2 (P13).
    Os momentos negativos estão no eixo dos pilares; o arredondamento de
    14.6.3 é do P14. A punção é verificada por 19.5.

    direcao: 'x' (pórticos paralelos a X), 'y' ou 'ambas'. balanco_a_cm e
    balanco_b_cm: balanço da laje além da primeira e da última fila,
    na direção transversal (só entram na largura do pórtico de borda).
    """
    cond = verificar_condicoes_portico_equivalente(pilares_xy, tol_alinhamento_cm,
                                                   razao_minima_vaos, concreto_armado)
    if not cond.ok:
        raise FaixaNormativaError(
            "Pórtico equivalente não aplicável (14.7.8): " + cond.governante
            + ". Use a grelha equivalente (procedimento numérico).")
    if h_laje_cm <= 0.0 or bx_pilar_cm <= 0.0 or by_pilar_cm <= 0.0:
        raise FaixaNormativaError("h da laje e dimensões dos pilares têm de ser positivos.")
    if q_kn_m2 < 0.0:
        raise FaixaNormativaError("q_kn_m2 não pode ser negativa.")
    if h_inf_cm is None and h_sup_cm is None:
        raise FaixaNormativaError("O pórtico precisa de ao menos um lance de pilar.")
    if balanco_a_cm < 0.0 or balanco_b_cm < 0.0:
        raise FaixaNormativaError("Balanço não pode ser negativo.")
    chave = nbr._chave(direcao)
    if chave not in ("x", "y", "ambas"):
        raise ValueError("direcao deve ser 'x', 'y' ou 'ambas'.")
    mat = ab.Material.concreto(fck_mpa, alpha_e)
    dirs = ("x", "y") if chave == "ambas" else (chave,)
    porticos = []
    memoria = list(cond.memoria) + [mat.descricao]
    for d in dirs:
        # ao longo: coordenadas dos pilares na direção do pórtico; filas: transversal
        ao_longo = cond.xs_cm if d == "x" else cond.ys_cm
        filas = cond.ys_cm if d == "x" else cond.xs_cm
        b_dir, b_tr = (bx_pilar_cm, by_pilar_cm) if d == "x" else (by_pilar_cm, bx_pilar_cm)
        I_pil = b_tr * b_dir ** 3 / 12.0
        sec_pil = ab.Secao(A_cm2=b_tr * b_dir, I_cm4=I_pil)
        for k, c in enumerate(filas):
            wa = (c - filas[k - 1]) / 2.0 if k > 0 else balanco_a_cm
            wb = (filas[k + 1] - c) / 2.0 if k < len(filas) - 1 else balanco_b_cm
            l2 = wa + wb
            if l2 <= 0.0:
                raise FaixaNormativaError("Largura do pórtico nula.")
            sec_laje = ab.Secao(A_cm2=l2 * h_laje_cm, I_cm4=l2 * h_laje_cm ** 3 / 12.0)
            m = ab.Modelo("portico_plano")
            n = len(ao_longo)
            x0 = ao_longo[0]
            for i, x in enumerate(ao_longo):
                m.no(("L", i), x - x0, 0.0)
                if h_inf_cm is not None:
                    m.no(("I", i), x - x0, -h_inf_cm)
                    m.barra(("PI", i), ("I", i), ("L", i), sec_pil, mat)
                    m.apoio(("I", i), "engaste")
                if h_sup_cm is not None:
                    m.no(("S", i), x - x0, h_sup_cm)
                    m.barra(("PS", i), ("L", i), ("S", i), sec_pil, mat)
                    m.apoio(("S", i), "engaste")
            for i in range(n - 1):
                m.barra(("V", i), ("L", i), ("L", i + 1), sec_laje, mat)
            q_lin = q_kn_m2 * l2 / 100.0   # kN/m
            caso = ab.CasoCarga(f"carga total, pórtico {d} = {_fmt(c)} cm")
            for i in range(n - 1):
                caso.distribuida(("V", i), -q_lin, direcao="Y")
            r = ab.resolver(m, caso, n_estacoes=n_estacoes)
            vaos = []
            for i in range(n - 1):
                rb = r.barras[("V", i)]
                Mi, Mj = rb.extremidade_i["Mz"], rb.extremidade_j["Mz"]
                Mp = _momento_max_vao(rb)
                faixas = {"M_neg_i": _repartir(Mi, "negativo", wa, wb),
                          "M_neg_j": _repartir(Mj, "negativo", wa, wb),
                          "M_pos": _repartir(Mp, "positivo", wa, wb)}
                vaos.append(FaixasVao(vao=i, L_cm=ao_longo[i + 1] - ao_longo[i], M_neg_i_kncm=Mi,
                                      M_neg_j_kncm=Mj, M_pos_kncm=Mp, faixas=faixas))
            mpil = {}
            reac = {}
            for i in range(n):
                mi = r.barras[("PI", i)].extremidade_j["Mz"] if h_inf_cm is not None else 0.0
                ms = r.barras[("PS", i)].extremidade_i["Mz"] if h_sup_cm is not None else 0.0
                mpil[i] = {"inferior": float(mi), "superior": float(ms)}
                reac[i] = sum(r.reacoes[(t, i)]["uy"] for t, h in (("I", h_inf_cm), ("S", h_sup_cm))
                              if h is not None)
            porticos.append(PorticoLinha(direcao=d, coordenada_cm=c, largura_a_cm=wa,
                                         largura_b_cm=wb, carga_kn_m=q_lin, vaos=tuple(vaos),
                                         momentos_pilares_kncm=mpil, reacoes_kn=reac, analise=r))
            memoria.append(
                f"Pórtico {d.upper()} na fila {_fmt(c)} cm: l2 = {_fmt(wa)} + {_fmt(wb)} = {_fmt(l2)} cm, "
                f"I = {_fmt(sec_laje.I_cm4)} cm⁴, carga total q·l2 = {_fmt(q_lin)} kN/m; "
                + "; ".join(f"vão {v.vao + 1}: M− = {_fmt(v.M_neg_i_kncm)} / {_fmt(v.M_neg_j_kncm)}, "
                            f"M+ = {_fmt(v.M_pos_kncm)} kN·cm" for v in vaos) + ".")
    memoria.append("Repartição entre faixas pela Figura 14.9 (14.7.8 a a d): positivos 45 % nas "
                   "internas e 27,5 % em cada externa; negativos 25 % e 37,5 %.")
    memoria.append("Momentos elásticos, sem redistribuição (se feita: 14.6.4.3 e 14.7.3.2, P13). "
                   "Verificar a punção (19.5).")
    return ResultadoPorticoEquivalente(condicoes=cond, porticos=tuple(porticos), ok=True,
                                       governante="pórticos múltiplos (14.7.8)",
                                       memoria=tuple(memoria))
