"""Tensoes em servico (Estadio II) e fissuracao -- NBR 6118:2026 (Pacote P9).

Fecha o ciclo tensao de servico -> abertura de fissura para secao generica
(nao so retangular/T com formula fechada, como em `viga_servico_nbr6118`):
expoe uma verificacao de tensoes em Estadio I/II sobre o kernel de flexao
obliqua (`rotinas.flexao_composta_obliqua`), a geometria da area de
envolvimento Acri (Figura 17.4), a Tabela 17.2 (controle de fissuracao sem
calcular wk) e a armadura minima sob deformacoes impostas.

Itens da NBR 6118:2026 cobertos (pagina do PDF = pagina impressa + 18):
    - 23.5.3 (PDF p. 218) -- alpha_e = Es/Ecs para fadiga (estadio II).
    - 17.3.3.2 (PDF p. 149-150) -- area de envolvimento Acri (Figura 17.4).
    - 17.3.3.3 (PDF p. 150) -- Tabela 17.2, controle de fissuracao sem wk.
    - 19.3.2 (PDF p. 179) -- fissuracao/descompressao em lajes remete a
      17.3.3/17.3.4 (mesmos criterios de viga, com bw da faixa de laje).
    - 17.3.5.2.2 (PDF p. 152-153) -- As,min sob deformacoes impostas.

Convencoes: como o nucleo e o kernel de flexao obliqua -- fck e tensoes em
MPa, geometria em cm, esforcos em kN e kN.cm, deformacao em por mil,
compressao positiva. `sigma_s` no retorno do kernel segue essa mesma
convencao (compressao positiva); os valores de tensao no aco desta
verificacao (sigma_si, Delta sigma_pi, Tabela 17.2) sao tensao de tracao e
entram como magnitude positiva.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
    import viga_servico_nbr6118 as vserv
    from rotinas import flexao_composta_obliqua as fco
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr
    from dimensionamento import viga_servico_nbr6118 as vserv
    from dimensionamento.rotinas import flexao_composta_obliqua as fco


# ---------------------------------------------------------------------------
# 23.5.3 -- alpha_e para fadiga (PDF p. 218) e 17.3.3.2/17.3.3.3 -- alpha_e
# simplificado para fissuracao (PDF p. 150)
# ---------------------------------------------------------------------------
def alpha_e_fadiga(fck_mpa: float | None = None, agregado: str = "granito") -> float:
    """Razao alpha_e = Es/Ecs para a verificacao de fadiga em regime elastico,
    Estadio II (23.5.3, PDF p. 218).

    Formula/regra (imagem conferida): "Para o calculo dos esforcos
    solicitantes e a verificacao das tensoes, admite-se o modelo linear
    elastico com a relacao alpha_e entre os modulos de deformacao do aco e
    do concreto, alpha_e = Es/Ecs, podendo, neste caso, ser adotado igual
    a 10."

    Sem fck_mpa (padrao), devolve o valor simplificado que a norma permite
    adotar (10,0), sem precisar do fck. Com fck_mpa, calcula o valor exato
    -- delega a `viga_servico_nbr6118.alpha_e` (mesma razao Es/Ecs, Eq. 68
    da apostila; nao reimplementa Eci/Ecs, que vem do nucleo).
    """
    if fck_mpa is None:
        return 10.0
    return vserv.alpha_e(fck_mpa, agregado)


ALPHA_E_SIMPLIFICADO_FISSURACAO = 15.0
"""alpha_e = 15 (Es/Ecs), razao simplificada que a NBR 6118:2026 permite
adotar no calculo em Estadio II para controle de fissuracao (17.3.3.2/
17.3.3.3, PDF p. 150, conferido na imagem): "O calculo no estadio II (que
admite comportamento linear dos materiais e despreza a resistencia a
tracao do concreto) pode ser feito considerando a relacao alpha_e entre os
modulos de elasticidade do aco e do concreto igual a 15."

Divergencia registrada em relacao ao JSON do plano: o JSON so lista o
alpha_e=10 do item 23.5.3 (fadiga); a pagina 150 traz uma segunda
simplificacao, para fissuracao, com valor diferente (15) -- as duas
convivem porque sao usos distintos (fadiga x controle de fissuracao).

Use `tensoes_servico(..., alpha_e=ALPHA_E_SIMPLIFICADO_FISSURACAO)` para
adotar essa razao, ou `alpha_e=None` (padrao) para o valor exato pelo fck
real de cada parte da secao.
"""


# ---------------------------------------------------------------------------
# 23.5.3/17.3.3.3 -- tensoes em servico, Estadio I/II, secao generica
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoTensoes:
    """Estado de tensoes em servico (Estadio I ou II), NBR 6118:2026
    17.3.3.3 (PDF p. 150) e 23.5.3 (PDF p. 218).

    x_cm: profundidade da linha neutra a partir da fibra mais comprimida,
        medida ao longo do eixo perpendicular a ela (mesma convencao de
        `viga_servico_nbr6118.x_II_retangular`/`x_II_secao_T`). Rigoroso em
        flexao uniaxial (Mx ou My nulo -- o caso das formulas fechadas de
        comparacao); em flexao obliqua (os dois momentos simultaneos), usa
        o mesmo criterio mas deixa de ser uma unica "profundidade reta" --
        para esse caso prefira o estado completo (eps_cg/kx/ky) ao x_cm
        isolado.
    sigma_c_max_kncm2: tensao maxima de compressao no concreto (>= 0).
        Calculada nos 4 cantos do retangulo envolvente da secao: exata para
        secao retangular e para secao T/L com a mesa (parte de largura
        total) do lado comprimido; pode subestimar/nao se aplicar se a
        fibra mais comprimida cair numa reentrancia do poligono (ex.: alma
        estreita de uma secao T invertida) -- caso fora do escopo testado
        neste pacote.
    sigma_s_kncm2: tensao em cada barra (ordem de `secao.barras`), na
        convencao do kernel (compressao positiva): uma barra tracionada
        aparece com valor negativo. Use `sigma_s_tracao_max_kncm2` para a
        magnitude de tracao da barra mais tracionada.
    alpha_e: razao Es/Ecs efetivamente usada (informada ou calculada pelo
        fck). Com Secao poligonal multi-fck e alpha_e=None, e a razao da
        primeira parte (a memoria de calculo lista o alpha_e de cada uma).
    """
    estadio: str
    alpha_e: float
    x_cm: float
    sigma_c_max_kncm2: float
    sigma_s_kncm2: tuple[float, ...]
    eps_cg_pmilh: float
    kx_pmilh_cm: float
    ky_pmilh_cm: float
    convergiu: bool
    memoria: tuple[str, ...]

    @property
    def sigma_s_tracao_max_kncm2(self) -> float:
        """Maior tensao de tracao entre as barras (>= 0; 0 se nenhuma tracionada)."""
        if not self.sigma_s_kncm2:
            return 0.0
        return max(0.0, -min(self.sigma_s_kncm2))


def _extensao_y(secao) -> tuple[float, float]:
    """(y_min, y_max) da secao, retangular ou poligonal."""
    if hasattr(secao, "partes"):
        _, y_min, _, y_max = fco._bbox_secao(secao)
        return y_min, y_max
    h = secao.altura_cm
    return -h / 2.0, h / 2.0


def tensoes_servico(
    secao,
    concreto,
    aco,
    N_kn: float,
    Mx_kncm: float,
    My_kncm: float = 0.0,
    alpha_e: float | None = None,
    estadio: str = "II",
    agregado: str = "granito",
    n_grid: int = 80,
    x0: tuple[float, float, float] | None = None,
) -> ResultadoTensoes:
    """Tensoes em servico (sigma_c maximo, sigma_s por barra e a posicao da
    linha neutra) para secao generica em concreto armado ou protendido, no
    Estadio I ou II (17.3.3.3, PDF p. 150; 23.5.3, PDF p. 218).

    Modelo linear elastico (a norma: "admite-se o modelo linear elastico").
    No Estadio II (`estadio="II"`, padrao), despreza a resistencia a tracao
    do concreto (secao fissurada, o caso normal de calculo de sigma_si para
    wk). No Estadio I (`estadio="I"`), o concreto trabalha linearmente nos
    dois sentidos (secao integra) -- usado para checar a descompressao ou o
    inicio de fissuracao (17.3.4, referida por 19.3.2 para lajes).

    `secao` aceita tanto `SecaoRetangular` quanto `Secao` poligonal (T, L,
    U, multi-fck) do kernel `rotinas.flexao_composta_obliqua`. `concreto` e
    o Concreto real da peca quando `secao` e retangular (usado so para
    achar Ecs a partir do fck, a menos que `alpha_e` seja informado); passe
    None com `Secao` poligonal -- cada Parte ja tem o proprio Concreto.

    `alpha_e`: razao Es/Ecs a plugar na curva linear do concreto. None
    (padrao) calcula Ecs pelo fck real de cada parte (nucleo, 8.2.8) e usa
    o Es de `aco`. Informe um valor -- por exemplo, `alpha_e_fadiga()` (10,
    23.5.3) ou `ALPHA_E_SIMPLIFICADO_FISSURACAO` (15, 17.3.3.2/17.3.3.3) --
    para forcar a razao modular simplificada que a norma permite adotar
    nesses dois contextos; nesse caso Ecs_kncm2 = aco.Es_kncm2/alpha_e para
    a secao inteira (uniforme, mesmo com Secao multi-fck).

    Reusa a integracao numerica do kernel de flexao obliqua
    (`_esforcos_internos_els`/`_esforcos_internos_els_pol`, ja usadas por
    `solver_els`/`solver_els_generico`): o unico elemento novo e o modelo
    constitutivo linear do concreto (`CurvaCLinearFissurada`/
    `CurvaCLinearNaoFissurada`) no lugar da parabola-retangulo do ELU.

    N_kn, Mx_kncm, My_kncm: esforcos de servico -- o chamador ja aplicou a
    combinacao adequada (ELS-W usa a frequente, 11.8.3.2;
    `acoes_nbr6118.combinacao_servico`). Mx em torno de x (comprime +y), My
    em torno de y (comprime +x) -- convencao do kernel de flexao obliqua.
    """
    if estadio not in ("I", "II"):
        raise ValueError(f"estádio deve ser 'I' ou 'II', recebido {estadio!r}.")
    if x0 is None:
        # x0=(0,0,0) e um ponto degenerado quando N_kn=0 (flexao pura): toda
        # fibra fica exatamente em eps=0, que e o "kink" das curvas lineares
        # (derivada descontinua entre tracao e compressao), e o jacobiano
        # numerico do fsolve fica singular ali -- nao converge. Uma
        # semente pequena na direcao do momento pedido tira o chute inicial
        # do kink sem alterar a solucao (so a convergencia).
        kx0 = 1e-3 if Mx_kncm > 0.0 else (-1e-3 if Mx_kncm < 0.0 else 0.0)
        ky0 = 1e-3 if My_kncm > 0.0 else (-1e-3 if My_kncm < 0.0 else 0.0)
        x0 = (0.0, kx0, ky0)
    e_generica = hasattr(secao, "partes")
    CurvaLinear = (
        fco.CurvaCLinearFissurada if estadio == "II" else fco.CurvaCLinearNaoFissurada
    )
    aE = vserv.alpha_E(agregado)
    memoria: list[str] = []

    if e_generica:
        if alpha_e is not None:
            Ecs_uniforme = aco.Es_kncm2 / alpha_e
            partes_lin = tuple(
                fco.Parte(
                    polygon=p.polygon,
                    concreto=fco.Concreto(
                        fck_mpa=p.concreto.fck_mpa, gama_c=p.concreto.gama_c,
                        curva=CurvaLinear(Ecs_kncm2=Ecs_uniforme),
                    ),
                )
                for p in secao.partes
            )
            memoria.append(
                f"alpha_e = {alpha_e:g} informado -> Ecs = Es/alpha_e = "
                f"{Ecs_uniforme:.1f} kN/cm2 (uniforme em todas as partes)."
            )
            alpha_e_usado = float(alpha_e)
        else:
            partes_lin_list = []
            ecs_valores = []
            for p in secao.partes:
                Ecs_p = nbr.mpa_para_kncm2(nbr.Ecs(p.concreto.fck_mpa, alpha_e=aE))
                ecs_valores.append(Ecs_p)
                partes_lin_list.append(fco.Parte(
                    polygon=p.polygon,
                    concreto=fco.Concreto(
                        fck_mpa=p.concreto.fck_mpa, gama_c=p.concreto.gama_c,
                        curva=CurvaLinear(Ecs_kncm2=Ecs_p),
                    ),
                ))
                memoria.append(
                    f"fck = {p.concreto.fck_mpa:g} MPa -> Ecs = {Ecs_p * 10:.0f} MPa "
                    f"(8.2.8), alpha_e = Es/Ecs = {aco.Es_kncm2 / Ecs_p:.2f}."
                )
            partes_lin = tuple(partes_lin_list)
            alpha_e_usado = aco.Es_kncm2 / ecs_valores[0]
        secao_lin = fco.Secao(
            partes=partes_lin, barras=secao.barras, cabos=(),
            n_dy=secao.n_dy, n_dx=secao.n_dx,
        )
        r = fco.solver_els_generico(secao_lin, aco, N_kn, Mx_kncm, My_kncm, x0=x0)
    else:
        if concreto is None and alpha_e is None:
            raise ValueError(
                "Com SecaoRetangular, informe `concreto` (para achar Ecs pelo fck) "
                "ou `alpha_e` diretamente."
            )
        if alpha_e is not None:
            Ecs_kncm2 = aco.Es_kncm2 / alpha_e
            fck_ref = concreto.fck_mpa if concreto is not None else nbr.FCK_MIN
            gama_c_ref = concreto.gama_c if concreto is not None else nbr.GAMA_C
            memoria.append(
                f"alpha_e = {alpha_e:g} informado -> Ecs = Es/alpha_e = "
                f"{Ecs_kncm2:.1f} kN/cm2."
            )
        else:
            Ecs_kncm2 = nbr.mpa_para_kncm2(nbr.Ecs(concreto.fck_mpa, alpha_e=aE))
            fck_ref = concreto.fck_mpa
            gama_c_ref = concreto.gama_c
            memoria.append(
                f"fck = {concreto.fck_mpa:g} MPa -> Ecs = {Ecs_kncm2 * 10:.0f} MPa (8.2.8)."
            )
        concreto_lin = fco.Concreto(
            fck_mpa=fck_ref, gama_c=gama_c_ref, curva=CurvaLinear(Ecs_kncm2=Ecs_kncm2),
        )
        alpha_e_usado = aco.Es_kncm2 / Ecs_kncm2
        r = fco.solver_els_generico(
            secao, aco, N_kn, Mx_kncm, My_kncm, concreto=concreto_lin,
            n_grid=n_grid, x0=x0,
        )

    if not r["convergiu"]:
        raise ValueError(f"Estado de tensões em serviço não convergiu: {r.get('mensagem')}")

    eps_cg, kx, ky = r["eps_cg_pmilh"], r["kx_pmilh_cm"], r["ky_pmilh_cm"]
    y_min, y_max = _extensao_y(secao)
    if abs(kx) > 1e-12:
        y0 = -eps_cg / kx
        x_cm = (y_max - y0) if kx > 0.0 else (y0 - y_min)
    elif eps_cg > 0.0:
        x_cm = y_max - y_min   # compressao uniforme: secao inteira comprimida
    else:
        x_cm = 0.0             # tracao uniforme: nenhuma fibra comprimida
    x_cm = max(0.0, min(x_cm, y_max - y_min))

    barras = secao.barras
    if barras:
        xb = np.array([b.x_cm for b in barras])
        yb = np.array([b.y_cm for b in barras])
        eps_b = eps_cg + kx * yb + ky * xb
        sigma_s = fco._sigma_aco(eps_b, aco.fyd_kncm2, aco.Es_kncm2, aco.eps_yd_pmilh)
        sigma_s_tup = tuple(float(v) for v in sigma_s)
    else:
        sigma_s_tup = ()

    memoria.append(
        f"Estádio {estadio}: eps_cg = {eps_cg:.4f} por mil, kx = {kx:.6f} por mil/cm, "
        f"ky = {ky:.6f} por mil/cm -> x = {x_cm:.2f} cm."
    )
    memoria.append(f"sigma_c,max = {r['sigma_c_max_kncm2'] * 10:.2f} MPa.")

    return ResultadoTensoes(
        estadio=estadio,
        alpha_e=float(alpha_e_usado),
        x_cm=float(x_cm),
        sigma_c_max_kncm2=float(r["sigma_c_max_kncm2"]),
        sigma_s_kncm2=sigma_s_tup,
        eps_cg_pmilh=float(eps_cg),
        kx_pmilh_cm=float(kx),
        ky_pmilh_cm=float(ky),
        convergiu=True,
        memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 17.3.3.2 -- area de envolvimento Acri (Figura 17.4, PDF p. 149)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BarraFissuracao:
    """Barra usada so para a geometria de Acri (17.3.3.2): posicao e
    diametro. Distinta de `flexao_composta_obliqua.Barra` (posicao + area),
    que nao carrega o diametro."""
    x_cm: float
    y_cm: float
    phi_mm: float


def area_envolvimento_acri(
    barras: Sequence[BarraFissuracao],
    bw_cm: float,
    h_cm: float,
) -> list[float]:
    """Area de envolvimento Acri de cada barra (Figura 17.4, 17.3.3.2,
    PDF p. 149-150).

    Formula/regra (imagem conferida): "deve ser considerada uma area Acri
    do concreto de envolvimento, constituida por um retangulo cujos lados
    nao distem mais que 7,5*phi do eixo da barra" -- ou seja, um retangulo
    de lado 15*phi (mm convertido para cm) centrado no eixo de cada barra.

    A norma nao detalha a regra de particao entre barras vizinhas quando
    as regioes 7,5*phi se sobrepoem (so diz "particionada... quando as
    regioes se sobrepoem" -- risco 8.6 do plano: escolha declarada aqui). A
    funcao parte a zona disputada pela bissetriz (metade da distancia entre
    os eixos das duas barras), o criterio usual (Bastos, item 17.1), e so o
    faz entre barras exatamente alinhadas na mesma linha (mesmo y) ou na
    mesma coluna (mesmo x) -- o caso comum de viga (uma ou mais camadas
    horizontais de barras). Para arranjo generico nao alinhado, barras
    vizinhas fora de uma linha/coluna comum nao sao particionadas entre si
    (a funcao devolve a area plena, so recortada pelo contorno fisico da
    secao bw_cm x h_cm centrada na origem -- pode entao se sobrepor a de
    outra barra nao alinhada; registre essa limitacao ao usar arranjos
    irregulares).

    Retorna Acri (cm^2) na mesma ordem de `barras`.
    """
    areas: list[float] = []
    for i, b in enumerate(barras):
        meio = 7.5 * b.phi_mm / 10.0
        x_lo, x_hi = b.x_cm - meio, b.x_cm + meio
        y_lo, y_hi = b.y_cm - meio, b.y_cm + meio
        for j, o in enumerate(barras):
            if j == i:
                continue
            if abs(o.y_cm - b.y_cm) < 1e-9 and abs(o.x_cm - b.x_cm) > 1e-9:
                meio_dist = (o.x_cm - b.x_cm) / 2.0
                if o.x_cm > b.x_cm:
                    x_hi = min(x_hi, b.x_cm + meio_dist)
                else:
                    x_lo = max(x_lo, b.x_cm + meio_dist)
            if abs(o.x_cm - b.x_cm) < 1e-9 and abs(o.y_cm - b.y_cm) > 1e-9:
                meio_dist = (o.y_cm - b.y_cm) / 2.0
                if o.y_cm > b.y_cm:
                    y_hi = min(y_hi, b.y_cm + meio_dist)
                else:
                    y_lo = max(y_lo, b.y_cm + meio_dist)
        x_lo = max(x_lo, -bw_cm / 2.0)
        x_hi = min(x_hi, bw_cm / 2.0)
        y_lo = max(y_lo, -h_cm / 2.0)
        y_hi = min(y_hi, h_cm / 2.0)
        largura = max(0.0, x_hi - x_lo)
        altura = max(0.0, y_hi - y_lo)
        areas.append(largura * altura)
    return areas


# ---------------------------------------------------------------------------
# 17.3.3.3 -- Tabela 17.2, controle de fissuracao sem verificar wk (PDF p. 150)
# ---------------------------------------------------------------------------
# (sigma_si/Delta_sigma_pi em MPa) -> (phi_max sem armaduras ativas [mm],
#  s_max sem armaduras ativas [cm], phi_max com armaduras ativas [mm] ou
#  None, s_max com armaduras ativas [cm] ou None). None = celula "-" da
#  tabela (a norma nao define esse par tensao/armadura-ativa).
TABELA_17_2 = {
    160.0: (32.0, 30.0, 25.0, 20.0),
    200.0: (25.0, 25.0, 16.0, 15.0),
    240.0: (20.0, 20.0, 12.5, 10.0),
    280.0: (16.0, 15.0, 8.0, 5.0),
    320.0: (12.5, 10.0, 6.0, None),
    360.0: (10.0, 5.0, None, None),
    400.0: (8.0, None, None, None),
}


@dataclass(frozen=True)
class ResultadoControleFissuracao:
    sigma_si_mpa: float
    linha_tabela_mpa: float
    com_armadura_ativa: bool
    phi_max_mm: float
    s_max_cm: float
    memoria: tuple[str, ...]


def controle_fissuracao_sem_wk(
    sigma_si_mpa: float, com_armadura_ativa: bool = False,
) -> ResultadoControleFissuracao:
    """phi_max e s_max da Tabela 17.2 (17.3.3.3, PDF p. 150), dispensando o
    calculo de wk (aberturas esperadas da ordem de 0,3 mm em concreto
    armado e 0,2 mm com armaduras ativas). sigma_si (ou Delta sigma_pi) em
    MPa, calculada no Estadio II (`tensoes_servico`).

    A tabela nao diz como tratar tensao entre as 7 linhas tabeladas (160 a
    400 MPa, de 40 em 40 MPa); phi_max e s_max so decrescem com a tensao
    (mais restritivos quanto maior sigma). Na ausencia de regra de
    interpolacao (a NBR nao diz que pode, risco 8.6 do plano: so interpolar
    quando a norma manda), a funcao usa o degrau imediatamente igual ou
    acima de sigma_si -- a favor da seguranca (o mesmo criterio usado hoje
    para alpha_0t, Tabela 9.4). Acima de 400 MPa, ou numa celula "-" (a
    tabela nao define esse par tensao/armadura-ativa), levanta
    FaixaNormativaError.

    Divergencia registrada em relacao ao "O que criar" do plano do pacote,
    que descreve `controle_fissuracao_sem_wk(sigma_s_mpa, phi_mm, s_cm,
    tipo)` -- uma verificacao completa (compara o phi/espacamento REAIS do
    detalhamento contra os limites da tabela e devolve ok: bool). Esta
    funcao e uma consulta aos limites phi_max/s_max da Tabela 17.2 para uma
    tensao dada, no mesmo espirito de `ResultadoTensoes` (que tambem nao
    carrega ok/governante por nao ser, ela propria, uma verificacao) --
    por isso `ResultadoControleFissuracao` nao segue aqui a convencao 3.3
    item 4 (dataclass de verificacao com ok/governante), que vale para
    dataclasses que checam um resultado, nao para as que so expoem um valor
    calculado ou tabelado. Quem for verificar um detalhamento real (phi_mm,
    s_cm escolhidos) compara na mao com phi_max_mm/s_max_cm devolvidos
    aqui: `ok = phi_mm <= r.phi_max_mm and s_cm <= r.s_max_cm`.
    """
    if sigma_si_mpa <= 0.0:
        raise ValueError("sigma_si_mpa deve ser positiva (tensão de tração na barra).")
    linhas = sorted(TABELA_17_2)
    linha = next((L for L in linhas if sigma_si_mpa <= L), None)
    if linha is None:
        raise nbr.FaixaNormativaError(
            f"sigma_si = {sigma_si_mpa:g} MPa acima de {linhas[-1]:g} MPa: a "
            "Tabela 17.2 não define phi_max/s_max acima disso (17.3.3.3, PDF p. 150)."
        )
    sem_phi, sem_s, com_phi, com_s = TABELA_17_2[linha]
    phi_max, s_max = (com_phi, com_s) if com_armadura_ativa else (sem_phi, sem_s)
    if phi_max is None or s_max is None:
        raise nbr.FaixaNormativaError(
            f"A Tabela 17.2 não define {'phi_max' if phi_max is None else 's_max'} "
            f"para sigma_si = {linha:g} MPa "
            f"{'com' if com_armadura_ativa else 'sem'} armadura ativa "
            "(17.3.3.3, PDF p. 150)."
        )
    return ResultadoControleFissuracao(
        sigma_si_mpa=sigma_si_mpa,
        linha_tabela_mpa=linha,
        com_armadura_ativa=com_armadura_ativa,
        phi_max_mm=phi_max,
        s_max_cm=s_max,
        memoria=(
            f"Tabela 17.2 (17.3.3.3, PDF p. 150): sigma_si = {sigma_si_mpa:g} MPa -> "
            f"linha {linha:g} MPa ({'com' if com_armadura_ativa else 'sem'} armadura "
            f"ativa) -> phi_max = {phi_max:g} mm, s_max = {s_max:g} cm.",
        ),
    )


# ---------------------------------------------------------------------------
# 19.3.2 -- fissuracao/descompressao em lajes remete a 17.3.3/17.3.4 (PDF p. 179)
# ---------------------------------------------------------------------------
def wk_verificacao(
    phi_mm: float,
    sigma_si_kncm2: float,
    Acr_cm2: float,
    As_cm2: float,
    fck_mpa: float,
    eta1_val: float = 2.25,
    wk_max_mm: float = 0.30,
    caa: str | None = None,
    tipo_concreto: str = "armado",
    nivel_protensao: int | None = None,
    tipo_protensao: str | None = None,
) -> "vserv.ResultadoFissuracao":
    """Fecha o ciclo sigma_si (Estadio II) -> Acri -> wk (17.3.3.2/17.3.3.3),
    valendo tambem para lajes: 19.3.2 (PDF p. 179) remete, sem formula
    propria, aos "critérios dados em 17.3.3 e 17.3.4" -- os mesmos de viga,
    trocando so bw pela largura da faixa de laje considerada (o teste
    sugerido no plano, bw=100 cm, e exatamente isso).

    Fachada fina sobre `viga_servico_nbr6118.abertura_fissura_wk` (nao
    reimplementa a Eq. 86/87 nem a Tabela 13.4 -- so reune os tres insumos:
    sigma_si de `tensoes_servico`, Acri de `area_envolvimento_acri` e o
    wk_max de `nucleo_nbr6118.wk_max_mm`, esse ultimo via `caa`). Os
    parametros sao os mesmos de `abertura_fissura_wk`; ver la a
    documentacao completa (inclusive do `caa`).
    """
    return vserv.abertura_fissura_wk(
        phi_mm=phi_mm,
        sigma_si_kncm2=sigma_si_kncm2,
        Acr_cm2=Acr_cm2,
        As_cm2=As_cm2,
        fck_mpa=fck_mpa,
        eta1_val=eta1_val,
        wk_max_mm=wk_max_mm,
        caa=caa,
        tipo_concreto=tipo_concreto,
        nivel_protensao=nivel_protensao,
        tipo_protensao=tipo_protensao,
    )


# ---------------------------------------------------------------------------
# 17.3.5.2.2 -- As,min sob deformacoes impostas (PDF p. 152-153)
# ---------------------------------------------------------------------------
def k_deformacao_imposta(
    intrinseca: bool, h_m: float | None = None, retangular: bool = True,
) -> float:
    """Coeficiente k da NBR 6118:2026 17.3.5.2.2 (PDF p. 152), armadura
    minima de tracao sob deformacoes impostas.

    a) deformacoes intrinsecas (ex.: calor de hidratacao, retracao
       restringida) -- a imagem da pagina 152 traz DOIS ramos, nao um so:
         - caso geral de qualquer forma de secao (`retangular=False`):
           k = 0,8, sem depender de h;
         - caso especifico de secoes retangulares (`retangular=True`,
           padrao -- mantem o comportamento anterior desta funcao): k = 0,8
           para h <= 0,3 m; k = 0,5 para h >= 0,8 m; interpolacao linear
           entre 0,3 m e 0,8 m (`h_m` obrigatorio nesse ramo);
    b) deformacoes extrinsecas (ex.: recalque de apoio): k = 1,0
       (`intrinseca=False`, `h_m` e `retangular` dispensados).

    Para secao nao retangular (T, caixao, celular etc.) com deformacao
    intrinseca, use `retangular=False`: usar o ramo retangular nesse caso
    aplicaria k=0,5 (h>=0,8 m) em vez do k=0,8 do caso geral, subestimando
    As,min -- contra a seguranca.
    """
    if not intrinseca:
        return 1.0
    if not retangular:
        return 0.8
    if h_m is None:
        raise ValueError(
            "Para deformação intrínseca em seção retangular, informe h_m "
            "(altura da seção, em metros) -- 17.3.5.2.2 interpola k entre "
            "0,3 m e 0,8 m; para seção não retangular, use retangular=False."
        )
    if h_m <= 0.3:
        return 0.8
    if h_m >= 0.8:
        return 0.5
    return 0.8 + (0.5 - 0.8) * (h_m - 0.3) / (0.8 - 0.3)


def kc_deformacao_imposta(
    caso: str,
    altura_zona_tracionada_cm: float | None = None,
    h_cm: float | None = None,
) -> float:
    """Coeficiente kc da NBR 6118:2026 17.3.5.2.2 (PDF p. 152-153), natureza
    da distribuicao de tensoes na secao imediatamente antes da fissuracao.

    caso:
        'tracao_pura'                          -> kc = 1,0
        'flexao_simples'                       -> kc = 0,4
        'nervura_vazada_protendida'             -> kc = 0,4 (nervuras de
            elementos protendidos ou sob flexao composta, secoes vazadas
            celular ou caixao)
        'mesa_tracionada_vazada_protendida'     -> kc = 0,8 (mesa
            tracionada, mesmo tipo de elemento)
        'interpolado' -> interpola linearmente entre 0 e 0,4 conforme a
            altura da zona tracionada calculada no Estadio II sob os
            esforcos que conduzem ao inicio da fissuracao
            (`altura_zona_tracionada_cm`), quando essa altura nao exceder
            o menor dos dois valores h/2 e 0,5 m (`h_cm` obrigatorio, para
            achar h/2). A norma nao detalha o sentido da interpolacao
            (risco 8.6 do plano: registrar a leitura adotada); esta funcao
            le kc crescendo de 0 (altura da zona tracionada nula) ate 0,4
            (na propria altura-limite, aproximando-se do caso de flexao
            simples) -- a leitura mais direta do texto ("interpolado entre
            0,4 ... e zero" conforme a altura se aproxima ou se afasta do
            limite), mas e uma decisao de leitura, nao uma formula
            explicita da norma.
    """
    valores = {
        "tracao_pura": 1.0,
        "flexao_simples": 0.4,
        "nervura_vazada_protendida": 0.4,
        "mesa_tracionada_vazada_protendida": 0.8,
    }
    if caso in valores:
        return valores[caso]
    if caso == "interpolado":
        if altura_zona_tracionada_cm is None or h_cm is None:
            raise ValueError(
                "caso='interpolado' exige altura_zona_tracionada_cm e h_cm "
                "(17.3.5.2.2, PDF p. 153)."
            )
        limite_cm = min(h_cm / 2.0, 50.0)
        if altura_zona_tracionada_cm < 0.0:
            raise ValueError("altura_zona_tracionada_cm não pode ser negativa.")
        if altura_zona_tracionada_cm > limite_cm:
            raise nbr.FaixaNormativaError(
                f"altura da zona tracionada = {altura_zona_tracionada_cm:g} cm acima "
                f"do limite = {limite_cm:g} cm (menor entre h/2 e 0,5 m): a "
                "interpolação de kc só vale dentro desse limite (17.3.5.2.2, PDF p. 153)."
            )
        return 0.4 * altura_zona_tracionada_cm / limite_cm
    raise ValueError(
        f"caso desconhecido: {caso!r}. Use 'tracao_pura', 'flexao_simples', "
        "'nervura_vazada_protendida', 'mesa_tracionada_vazada_protendida' ou "
        "'interpolado'."
    )


def As_min_deformacao_imposta(
    k: float, kc: float, fctef_mpa: float, Act_cm2: float, sigma_s_mpa: float,
) -> float:
    """Armadura minima de tracao sob deformacoes impostas (17.3.5.2.2,
    PDF p. 152): As = k*kc*fct,ef*Act/sigma_s.

    k: `k_deformacao_imposta`. kc: `kc_deformacao_imposta`. fctef_mpa:
    resistencia media a tracao efetiva do concreto na idade em que se
    formam as primeiras fissuras (8.2.5); a norma recomenda o minimo de
    3 MPa quando essa idade nao puder ser definida com confianca. Act_cm2:
    area de concreto na zona tracionada. sigma_s_mpa: tensao maxima
    permitida na armadura logo apos a fissuracao (pode ser limitada pela
    Tabela 17.2). fctef_mpa e sigma_s_mpa devem estar na mesma unidade (a
    razao e adimensional); devolve As em cm^2 (mesma unidade de Act_cm2).
    """
    if sigma_s_mpa <= 0.0:
        raise ValueError("sigma_s_mpa deve ser positiva.")
    return k * kc * fctef_mpa * Act_cm2 / sigma_s_mpa


FCTEF_MINIMO_RECOMENDADO_MPA = 3.0
"""Valor minimo de fct,ef recomendado pela norma (17.3.5.2.2, PDF p. 152)
quando a idade de fissuracao nao puder ser definida com valor confiavel."""
