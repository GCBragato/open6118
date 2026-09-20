"""Tensões em serviço (Estádio II) e fissuração -- NBR 6118:2026 (Pacote P9).

Fecha o ciclo tensão de serviço -> abertura de fissura para seção genérica
(não só retangular/T com fórmula fechada, como em `viga_servico_nbr6118`):
expõe uma verificação de tensões em Estádio I/II sobre o kernel de flexão
oblíqua (`rotinas.flexao_composta_obliqua`), a geometria da área de
envolvimento Acri (Figura 17.4), a Tabela 17.2 (controle de fissuração sem
calcular wk) e a armadura mínima sob deformações impostas.

Itens da NBR 6118:2026 cobertos (página do PDF = página impressa + 18):
    - 23.5.3 (PDF p. 218) -- alpha_e = Es/Ecs para fadiga (estádio II).
    - 17.3.3.2 (PDF p. 149-150) -- área de envolvimento Acri (Figura 17.4).
    - 17.3.3.3 (PDF p. 150) -- Tabela 17.2, controle de fissuração sem wk.
    - 19.3.2 (PDF p. 179) -- fissuração/descompressão em lajes remete a
      17.3.3/17.3.4 (mesmos critérios de viga, com bw da faixa de laje).
    - 17.3.5.2.2 (PDF p. 152-153) -- As,min sob deformações impostas.

Convenções: como o núcleo e o kernel de flexão oblíqua -- fck e tensões em
MPa, geometria em cm, esforços em kN e kN.cm, deformação em por mil,
compressão positiva. `sigma_s` no retorno do kernel segue essa mesma
convenção (compressão positiva); os valores de tensão no aço desta
verificação (sigma_si, Delta sigma_pi, Tabela 17.2) são tensão de tração e
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
# simplificado para fissuração (PDF p. 150)
# ---------------------------------------------------------------------------
def alpha_e_fadiga(fck_mpa: float | None = None, agregado: str = "granito") -> float:
    """Razão alpha_e = Es/Ecs para a verificação de fadiga em regime elástico,
    Estádio II (23.5.3, PDF p. 218).

    Fórmula/regra (imagem conferida): "Para o cálculo dos esforços
    solicitantes e a verificação das tensões, admite-se o modelo linear
    elástico com a relação alpha_e entre os módulos de deformação do aço e
    do concreto, alpha_e = Es/Ecs, podendo, neste caso, ser adotado igual
    a 10."

    Sem fck_mpa (padrão), devolve o valor simplificado que a norma permite
    adotar (10,0), sem precisar do fck. Com fck_mpa, calcula o valor exato
    -- delega a `viga_servico_nbr6118.alpha_e` (mesma razão Es/Ecs, Eq. 68
    da apostila; não reimplementa Eci/Ecs, que vêm do núcleo).
    """
    if fck_mpa is None:
        return 10.0
    return vserv.alpha_e(fck_mpa, agregado)


ALPHA_E_SIMPLIFICADO_FISSURACAO = 15.0
"""alpha_e = 15 (Es/Ecs), razão simplificada que a NBR 6118:2026 permite
adotar no cálculo em Estádio II para controle de fissuração (17.3.3.2/
17.3.3.3, PDF p. 150, conferido na imagem): "O cálculo no estádio II (que
admite comportamento linear dos materiais e despreza a resistência à
tração do concreto) pode ser feito considerando a relação alpha_e entre os
módulos de elasticidade do aço e do concreto igual a 15."

Divergência registrada em relação ao JSON do plano: o JSON só lista o
alpha_e=10 do item 23.5.3 (fadiga); a página 150 traz uma segunda
simplificação, para fissuração, com valor diferente (15) -- as duas
convivem porque são usos distintos (fadiga x controle de fissuração).

Use `tensoes_servico(..., alpha_e=ALPHA_E_SIMPLIFICADO_FISSURACAO)` para
adotar essa razão, ou `alpha_e=None` (padrão) para o valor exato pelo fck
real de cada parte da seção.
"""


# ---------------------------------------------------------------------------
# 23.5.3/17.3.3.3 -- tensões em serviço, Estádio I/II, seção genérica
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoTensoes:
    """Estado de tensões em serviço (Estádio I ou II), NBR 6118:2026
    17.3.3.3 (PDF p. 150) e 23.5.3 (PDF p. 218).

    x_cm: profundidade da linha neutra a partir da fibra mais comprimida,
        medida ao longo do eixo perpendicular a ela (mesma convenção de
        `viga_servico_nbr6118.x_II_retangular`/`x_II_secao_T`). Rigoroso em
        flexão uniaxial (Mx ou My nulo -- o caso das fórmulas fechadas de
        comparação); em flexão oblíqua (os dois momentos simultâneos), usa
        o mesmo critério mas deixa de ser uma única "profundidade reta" --
        para esse caso prefira o estado completo (eps_cg/kx/ky) ao x_cm
        isolado.
    sigma_c_max_kncm2: tensão máxima de compressão no concreto (>= 0).
        Calculada nos 4 cantos do retângulo envolvente da seção: exata para
        seção retangular e para seção T/L com a mesa (parte de largura
        total) do lado comprimido; pode subestimar/não se aplicar se a
        fibra mais comprimida cair numa reentrância do polígono (ex.: alma
        estreita de uma seção T invertida) -- caso fora do escopo testado
        neste pacote.
    sigma_s_kncm2: tensão em cada barra (ordem de `secao.barras`), na
        convenção do kernel (compressão positiva): uma barra tracionada
        aparece com valor negativo. Use `sigma_s_tracao_max_kncm2` para a
        magnitude de tração da barra mais tracionada.
    alpha_e: razão Es/Ecs efetivamente usada (informada ou calculada pelo
        fck). Com Secao poligonal multi-fck e alpha_e=None, e a razão da
        primeira parte (a memória de cálculo lista o alpha_e de cada uma).
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
        """Maior tensão de tração entre as barras (>= 0; 0 se nenhuma tracionada)."""
        if not self.sigma_s_kncm2:
            return 0.0
        return max(0.0, -min(self.sigma_s_kncm2))


def _extensao_y(secao) -> tuple[float, float]:
    """(y_min, y_max) da seção, retangular ou poligonal."""
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
    """Tensões em serviço (sigma_c máximo, sigma_s por barra e a posição da
    linha neutra) para seção genérica em concreto armado ou protendido, no
    Estádio I ou II (17.3.3.3, PDF p. 150; 23.5.3, PDF p. 218).

    Modelo linear elástico (a norma: "admite-se o modelo linear elástico").
    No Estádio II (`estadio="II"`, padrão), despreza a resistência à tração
    do concreto (seção fissurada, o caso normal de cálculo de sigma_si para
    wk). No Estádio I (`estadio="I"`), o concreto trabalha linearmente nos
    dois sentidos (seção íntegra) -- usado para checar a descompressão ou o
    início de fissuração (17.3.4, referida por 19.3.2 para lajes).

    `secao` aceita tanto `SecaoRetangular` quanto `Secao` poligonal (T, L,
    U, multi-fck) do kernel `rotinas.flexao_composta_obliqua`. `concreto` é
    o Concreto real da peça quando `secao` é retangular (usado só para
    achar Ecs a partir do fck, a menos que `alpha_e` seja informado); passe
    None com `Secao` poligonal -- cada Parte já tem o próprio Concreto.

    `alpha_e`: razão Es/Ecs a plugar na curva linear do concreto. None
    (padrão) calcula Ecs pelo fck real de cada parte (núcleo, 8.2.8) e usa
    o Es de `aco`. Informe um valor -- por exemplo, `alpha_e_fadiga()` (10,
    23.5.3) ou `ALPHA_E_SIMPLIFICADO_FISSURACAO` (15, 17.3.3.2/17.3.3.3) --
    para forcar a razão modular simplificada que a norma permite adotar
    nesses dois contextos; nesse caso Ecs_kncm2 = aco.Es_kncm2/alpha_e para
    a seção inteira (uniforme, mesmo com Secao multi-fck).

    Reusa a integração numérica do kernel de flexão oblíqua
    (`_esforcos_internos_els`/`_esforcos_internos_els_pol`, já usadas por
    `solver_els`/`solver_els_generico`): o único elemento novo é o modelo
    constitutivo linear do concreto (`CurvaCLinearFissurada`/
    `CurvaCLinearNaoFissurada`) no lugar da parábola-retângulo do ELU.

    N_kn, Mx_kncm, My_kncm: esforços de serviço -- o chamador já aplicou a
    combinação adequada (ELS-W usa a frequente, 11.8.3.2;
    `acoes_nbr6118.combinacao_servico`). Mx em torno de x (comprime +y), My
    em torno de y (comprime +x) -- convenção do kernel de flexão oblíqua.
    """
    if estadio not in ("I", "II"):
        raise nbr.FaixaNormativaError(f"estádio deve ser 'I' ou 'II', recebido {estadio!r}.")
    if x0 is None:
        # x0=(0,0,0) é um ponto degenerado quando N_kn=0 (flexão pura): toda
        # fibra fica exatamente em eps=0, que é o "kink" das curvas lineares
        # (derivada descontínua entre tração e compressão), e o jacobiano
        # numérico do fsolve fica singular ali -- não converge. Uma
        # semente pequena na direção do momento pedido tira o chute inicial
        # do kink sem alterar a solução (só a convergência).
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
        raise ValueError(f"Estado de tensões em serviço não convergiu: {r.get('mensagem')}.")

    eps_cg, kx, ky = r["eps_cg_pmilh"], r["kx_pmilh_cm"], r["ky_pmilh_cm"]
    y_min, y_max = _extensao_y(secao)
    if abs(kx) > 1e-12:
        y0 = -eps_cg / kx
        x_cm = (y_max - y0) if kx > 0.0 else (y0 - y_min)
    elif eps_cg > 0.0:
        x_cm = y_max - y_min   # compressão uniforme: seção inteira comprimida
    else:
        x_cm = 0.0             # tração uniforme: nenhuma fibra comprimida
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
# 17.3.3.2 -- área de envolvimento Acri (Figura 17.4, PDF p. 149)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BarraFissuracao:
    """Barra usada só para a geometria de Acri (17.3.3.2): posição e
    diâmetro. Distinta de `flexao_composta_obliqua.Barra` (posição + área),
    que não carrega o diâmetro."""
    x_cm: float
    y_cm: float
    phi_mm: float


def area_envolvimento_acri(
    barras: Sequence[BarraFissuracao],
    bw_cm: float,
    h_cm: float,
) -> list[float]:
    """Área de envolvimento Acri de cada barra (Figura 17.4, 17.3.3.2,
    PDF p. 149-150).

    Fórmula/regra (imagem conferida): "deve ser considerada uma área Acri
    do concreto de envolvimento, constituída por um retângulo cujos lados
    não distem mais que 7,5*phi do eixo da barra" -- ou seja, um retângulo
    de lado 15*phi (mm convertido para cm) centrado no eixo de cada barra.

    A norma não detalha a regra de partição entre barras vizinhas quando
    as regiões 7,5*phi se sobrepõem (só diz "particionada... quando as
    regiões se sobrepõem" -- risco 8.6 do plano: escolha declarada aqui). A
    função parte a zona disputada pela bissetriz (metade da distância entre
    os eixos das duas barras), o critério usual (Bastos, item 17.1), e só o
    faz entre barras exatamente alinhadas na mesma linha (mesmo y) ou na
    mesma coluna (mesmo x) -- o caso comum de viga (uma ou mais camadas
    horizontais de barras). Para arranjo genérico não alinhado, barras
    vizinhas fora de uma linha/coluna comum não são particionadas entre si
    (a função devolve a área plena, só recortada pelo contorno físico da
    seção bw_cm x h_cm centrada na origem -- pode então se sobrepor à de
    outra barra não alinhada; registre essa limitação ao usar arranjos
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
# 17.3.3.3 -- Tabela 17.2, controle de fissuração sem verificar wk (PDF p. 150)
# ---------------------------------------------------------------------------
# (sigma_si/Delta_sigma_pi em MPa) -> (phi_max sem armaduras ativas [mm],
#  s_max sem armaduras ativas [cm], phi_max com armaduras ativas [mm] ou
#  None, s_max com armaduras ativas [cm] ou None). None = célula "-" da
#  tabela (a norma não define esse par tensão/armadura-ativa).
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
    cálculo de wk (aberturas esperadas da ordem de 0,3 mm em concreto
    armado e 0,2 mm com armaduras ativas). sigma_si (ou Delta sigma_pi) em
    MPa, calculada no Estádio II (`tensoes_servico`).

    A tabela não diz como tratar tensão entre as 7 linhas tabeladas (160 a
    400 MPa, de 40 em 40 MPa); phi_max e s_max só decrescem com a tensão
    (mais restritivos quanto maior sigma). Na ausência de regra de
    interpolação (a NBR não diz que pode, risco 8.6 do plano: só interpolar
    quando a norma manda), a função usa o degrau imediatamente igual ou
    acima de sigma_si -- a favor da segurança (o mesmo critério usado hoje
    para alpha_0t, Tabela 9.4). Acima de 400 MPa, ou numa célula "-" (a
    tabela não define esse par tensão/armadura-ativa), levanta
    FaixaNormativaError.

    Divergência registrada em relação ao "O que criar" do plano do pacote,
    que descreve `controle_fissuracao_sem_wk(sigma_s_mpa, phi_mm, s_cm,
    tipo)` -- uma verificação completa (compara o phi/espaçamento REAIS do
    detalhamento contra os limites da tabela e devolve ok: bool). Esta
    função é uma consulta aos limites phi_max/s_max da Tabela 17.2 para uma
    tensão dada, no mesmo espírito de `ResultadoTensoes` (que também não
    carrega ok/governante por não ser, ela própria, uma verificação) --
    por isso `ResultadoControleFissuracao` não segue aqui a convenção 3.3
    item 4 (dataclass de verificação com ok/governante), que vale para
    dataclasses que checam um resultado, não para as que só expõem um valor
    calculado ou tabelado. Quem for verificar um detalhamento real (phi_mm,
    s_cm escolhidos) compara na mão com phi_max_mm/s_max_cm devolvidos
    aqui: `ok = phi_mm <= r.phi_max_mm and s_cm <= r.s_max_cm`.
    """
    if sigma_si_mpa <= 0.0:
        raise nbr.FaixaNormativaError("sigma_si_mpa deve ser positiva (tensão de tração na barra).")
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
# 19.3.2 -- fissuração/descompressão em lajes remete a 17.3.3/17.3.4 (PDF p. 179)
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
    """Fecha o ciclo sigma_si (Estádio II) -> Acri -> wk (17.3.3.2/17.3.3.3),
    valendo também para lajes: 19.3.2 (PDF p. 179) remete, sem fórmula
    própria, aos "critérios dados em 17.3.3 e 17.3.4" -- os mesmos de viga,
    trocando só bw pela largura da faixa de laje considerada (o teste
    sugerido no plano, bw=100 cm, e exatamente isso).

    Fachada fina sobre `viga_servico_nbr6118.abertura_fissura_wk` (não
    reimplementa a Eq. 86/87 nem a Tabela 13.4 -- só reúne os três insumos:
    sigma_si de `tensoes_servico`, Acri de `area_envolvimento_acri` e o
    wk_max de `nucleo_nbr6118.wk_max_mm`, esse último via `caa`). Os
    parâmetros são os mesmos de `abertura_fissura_wk`; ver lá a
    documentação completa (inclusive do `caa`).
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
# 17.3.5.2.2 -- As,min sob deformações impostas (PDF p. 152-153)
# ---------------------------------------------------------------------------
def k_deformacao_imposta(
    intrinseca: bool, h_m: float | None = None, retangular: bool = True,
) -> float:
    """Coeficiente k da NBR 6118:2026 17.3.5.2.2 (PDF p. 152), armadura
    mínima de tração sob deformações impostas.

    a) deformações intrínsecas (ex.: calor de hidratação, retração
       restringida) -- a imagem da página 152 traz DOIS ramos, não um só:
         - caso geral de qualquer forma de seção (`retangular=False`):
           k = 0,8, sem depender de h;
         - caso específico de seções retangulares (`retangular=True`,
           padrão -- mantém o comportamento anterior desta função): k = 0,8
           para h <= 0,3 m; k = 0,5 para h >= 0,8 m; interpolação linear
           entre 0,3 m e 0,8 m (`h_m` obrigatório nesse ramo);
    b) deformações extrínsecas (ex.: recalque de apoio): k = 1,0
       (`intrinseca=False`, `h_m` e `retangular` dispensados).

    Para seção não retangular (T, caixão, celular etc.) com deformação
    intrínseca, use `retangular=False`: usar o ramo retangular nesse caso
    aplicaria k=0,5 (h>=0,8 m) em vez do k=0,8 do caso geral, subestimando
    As,min -- contra a segurança.
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
    da distribuição de tensões na seção imediatamente antes da fissuração.

    caso:
        'tracao_pura'                          -> kc = 1,0
        'flexao_simples'                       -> kc = 0,4
        'nervura_vazada_protendida'             -> kc = 0,4 (nervuras de
            elementos protendidos ou sob flexão composta, seções vazadas
            celular ou caixão)
        'mesa_tracionada_vazada_protendida'     -> kc = 0,8 (mesa
            tracionada, mesmo tipo de elemento)
        'interpolado' -> interpola linearmente entre 0 e 0,4 conforme a
            altura da zona tracionada calculada no Estádio II sob os
            esforços que conduzem ao início da fissuração
            (`altura_zona_tracionada_cm`), quando essa altura não exceder
            o menor dos dois valores h/2 e 0,5 m (`h_cm` obrigatório, para
            achar h/2). A norma não detalha o sentido da interpolação
            (risco 8.6 do plano: registrar a leitura adotada); esta função
            lê kc crescendo de 0 (altura da zona tracionada nula) até 0,4
            (na própria altura-limite, aproximando-se do caso de flexão
            simples) -- a leitura mais direta do texto ("interpolado entre
            0,4 ... e zero" conforme a altura se aproxima ou se afasta do
            limite), mas é uma decisão de leitura, não uma fórmula
            explícita da norma.
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
            raise nbr.FaixaNormativaError("altura_zona_tracionada_cm não pode ser negativa.")
        if altura_zona_tracionada_cm > limite_cm:
            raise nbr.FaixaNormativaError(
                f"altura da zona tracionada = {altura_zona_tracionada_cm:g} cm acima "
                f"do limite = {limite_cm:g} cm (menor entre h/2 e 0,5 m): a "
                "interpolação de kc só vale dentro desse limite (17.3.5.2.2, PDF p. 153)."
            )
        return 0.4 * altura_zona_tracionada_cm / limite_cm
    raise nbr.FaixaNormativaError(
        f"caso desconhecido: {caso!r}. Use 'tracao_pura', 'flexao_simples', "
        "'nervura_vazada_protendida', 'mesa_tracionada_vazada_protendida' ou "
        "'interpolado'."
    )


def As_min_deformacao_imposta(
    k: float, kc: float, fctef_mpa: float, Act_cm2: float, sigma_s_mpa: float,
) -> float:
    """Armadura mínima de tração sob deformações impostas (17.3.5.2.2,
    PDF p. 152): As = k*kc*fct,ef*Act/sigma_s.

    k: `k_deformacao_imposta`. kc: `kc_deformacao_imposta`. fctef_mpa:
    resistência média à tração efetiva do concreto na idade em que se
    formam as primeiras fissuras (8.2.5); a norma recomenda o mínimo de
    3 MPa quando essa idade não puder ser definida com confiança. Act_cm2:
    área de concreto na zona tracionada. sigma_s_mpa: tensão máxima
    permitida na armadura logo após a fissuração (pode ser limitada pela
    Tabela 17.2). fctef_mpa e sigma_s_mpa devem estar na mesma unidade (a
    razão é adimensional); devolve As em cm^2 (mesma unidade de Act_cm2).
    """
    if sigma_s_mpa <= 0.0:
        raise nbr.FaixaNormativaError("sigma_s_mpa deve ser positiva.")
    return k * kc * fctef_mpa * Act_cm2 / sigma_s_mpa


FCTEF_MINIMO_RECOMENDADO_MPA = 3.0
"""Valor mínimo de fct,ef recomendado pela norma (17.3.5.2.2, PDF p. 152)
quando a idade de fissuração não puder ser definida com valor confiável."""


# === F2: 19.3.2 -- descompressão e formação de fissuras em laje protendida
# (17.3.4, PDF p. 150-151) e ponto de entrada único do ELS de fissuração de
# laje (PDF p. 179) ===
try:  # executado como script, ou com dimensionamento/ no sys.path
    import protendido_nbr6118 as _pt_f2
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import protendido_nbr6118 as _pt_f2


def verificar_descompressao_laje(
    P_kn: float, ep_cm: float, M_kncm: float,
    b_cm: float, h_cm: float,
    estado: str = "ELS-D", fck_mpa: float | None = None,
    sinal_P: int = -1,
) -> "_pt_f2.ResultadoDescompressaoFissuracao":
    """Estado-limite de descompressão (ELS-D) ou de formação de fissuras
    (ELS-F) de uma faixa de laje protendida, NBR 6118:2026 19.3.2 (PDF
    p. 179), que remete aos "critérios dados em 17.3.3 e 17.3.4", e 17.3.4
    (PDF p. 150-151): "nos elementos estruturais onde se utilizam armaduras
    de protensão, pode ser necessária a verificação da segurança em relação
    aos estados-limites de descompressão e de formação de fissuras. Essa
    verificação pode ser feita calculando-se a máxima tensão de tração do
    concreto no estádio I (concreto não fissurado e comportamento elástico
    linear dos materiais)".

    A laje entra como uma faixa retangular de largura b_cm (a largura da
    faixa considerada, tipicamente 100 cm) e altura h_cm, com

        Ac = b·h    e    Wb = Wt = b·h²/6

    (``protendido_nbr6118.Ac_retangular`` e ``W_retangular``), e a
    verificação em si é a de viga, ``protendido_nbr6118.
    verificar_descompressao_fissuracao`` — a norma não dá fórmula própria
    para laje, e é exatamente isso que 19.3.2 quer dizer.

    P_kn: força de protensão na faixa, depois das perdas consideradas na
    combinação (kN). ep_cm: excentricidade do cabo em relação ao centroide
    da faixa (cm). M_kncm: momento fletor na faixa para a combinação de
    ações do estado-limite verificado (kN.cm; qual combinação vai com cada
    estado-limite está na Tabela 13.4 — ``nucleo_nbr6118.wk_max_mm``, e
    ``verificar_els_laje_protendida`` já faz essa escolha).
    estado: 'ELS-D' (tensão-limite de tração nula) ou 'ELS-F' (tensão-limite
    de 17.2.4.4.2, que exige fck_mpa). sinal_P: convenção de
    ``protendido_nbr6118.sigma_base_topo`` (-1, o padrão, com P entrando em
    módulo e comprimindo a seção).
    """
    if b_cm <= 0.0 or h_cm <= 0.0:
        raise nbr.FaixaNormativaError("b_cm e h_cm devem ser positivos.")
    Ac = _pt_f2.Ac_retangular(b_cm, h_cm)
    W = _pt_f2.W_retangular(b_cm, h_cm)
    return _pt_f2.verificar_descompressao_fissuracao(
        P_kn=P_kn, ep_cm=ep_cm, M_kncm=M_kncm,
        Ac_cm2=Ac, Wb_cm3=W, Wt_cm3=W,
        estado=estado, fck_mpa=fck_mpa, secao="retangular", sinal_P=sinal_P,
    )


@dataclass(frozen=True)
class ResultadoELSLajeProtendida:
    """ELS de fissuração/descompressão de uma faixa de laje, NBR 6118:2026
    19.3.2 (PDF p. 179), com o critério escolhido pela Tabela 13.4."""
    criterio: str
    exigencia_tabela_13_4: str
    wk_max_mm: float | None
    fissuracao: "vserv.ResultadoFissuracao | None"
    els_f: "_pt_f2.ResultadoDescompressaoFissuracao | None"
    els_d: "_pt_f2.ResultadoDescompressaoFissuracao | None"
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_els_laje_protendida(
    caa: str, b_cm: float, h_cm: float, fck_mpa: float,
    tipo_concreto: str = "protendido",
    nivel_protensao: int | None = None,
    tipo_protensao: str | None = None,
    P_kn: float | None = None, ep_cm: float = 0.0,
    M_els_f_kncm: float | None = None, M_els_d_kncm: float | None = None,
    phi_mm: float | None = None, sigma_si_kncm2: float | None = None,
    Acr_cm2: float | None = None, As_cm2: float | None = None,
    eta1_val: float = 2.25, sinal_P: int = -1,
) -> ResultadoELSLajeProtendida:
    """Ponto de entrada único do estado-limite de fissuração de uma faixa de
    laje, NBR 6118:2026 19.3.2 (PDF p. 179): "devem ser usados os critérios
    dados em 17.3.3 e 17.3.4".

    Qual dos dois critérios se aplica não está em 19.3.2, e sim na Tabela
    13.4 (13.4.2, PDF p. 100-101), consultada aqui por
    ``nucleo_nbr6118.wk_max_mm``:

    - quando a Tabela 13.4 dá um wk,máx (concreto armado, e protendido de
      nível 1 — protensão parcial), o critério é o de 17.3.3, abertura de
      fissura, e a função chama ``wk_verificacao`` (que é a mesma
      ``viga_servico_nbr6118.abertura_fissura_wk``, com a largura da faixa
      de laje no lugar de bw): exige phi_mm, sigma_si_kncm2, Acr_cm2 e
      As_cm2;
    - quando a Tabela 13.4 não dá wk,máx (protendido de níveis 2 e 3), a
      exigência são duas verificações de tensão de 17.3.4, ELS-F e ELS-D,
      cada uma com a sua combinação de ações, e a função chama
      ``verificar_descompressao_laje`` duas vezes: exige P_kn,
      M_els_f_kncm e M_els_d_kncm (os momentos da faixa em cada uma das
      duas combinações, calculados por quem chama — ``acoes_nbr6118``, P4).

    O texto da exigência da Tabela 13.4 (com o nome da combinação de cada
    verificação) vai em ``exigencia_tabela_13_4`` e na memória de cálculo.
    Par CAA/nível fora da Tabela 13.4 levanta ``FaixaNormativaError`` (vem
    do núcleo). b_cm é a largura da faixa de laje considerada (tipicamente
    100 cm) e h_cm a espessura.
    """
    limite_wk, exigencia = nbr.wk_max_mm(
        tipo_concreto, caa, nivel_protensao, tipo_protensao)
    memoria = [
        f"19.3.2 (p. 179): os critérios do ELS de fissuração de laje são os "
        f"de 17.3.3 e 17.3.4, aplicados à faixa de b = {b_cm:g} cm e "
        f"h = {h_cm:g} cm.",
        f"Tabela 13.4 (13.4.2, p. 100-101), {tipo_concreto}, CAA "
        f"{nbr.normalizar_caa(caa)}: exigência = {exigencia}.",
    ]

    if limite_wk is not None:
        faltando = [nome for nome, valor in (
            ("phi_mm", phi_mm), ("sigma_si_kncm2", sigma_si_kncm2),
            ("Acr_cm2", Acr_cm2), ("As_cm2", As_cm2)) if valor is None]
        if faltando:
            raise ValueError(
                "A Tabela 13.4 exige a verificação da abertura de fissura "
                f"(17.3.3, wk,máx = {limite_wk:g} mm) neste caso: informe "
                + ", ".join(faltando) + "."
            )
        r_wk = wk_verificacao(
            phi_mm=phi_mm, sigma_si_kncm2=sigma_si_kncm2, Acr_cm2=Acr_cm2,
            As_cm2=As_cm2, fck_mpa=fck_mpa, eta1_val=eta1_val,
            caa=caa, tipo_concreto=tipo_concreto,
            nivel_protensao=nivel_protensao, tipo_protensao=tipo_protensao,
        )
        memoria.append(
            f"17.3.3 (p. 149-150): wk = {r_wk.wk_mm:.4f} mm "
            f"{'<=' if r_wk.ok else '>'} wk,máx = {r_wk.wk_max_mm:g} mm -> "
            f"{'ok' if r_wk.ok else 'não ok'}."
        )
        return ResultadoELSLajeProtendida(
            criterio="17.3.3 (abertura de fissura)",
            exigencia_tabela_13_4=exigencia,
            wk_max_mm=limite_wk,
            fissuracao=r_wk, els_f=None, els_d=None,
            ok=bool(r_wk.ok),
            governante=("abertura de fissura dentro do limite" if r_wk.ok
                        else "abertura de fissura acima do limite"),
            memoria=tuple(memoria),
        )

    faltando = [nome for nome, valor in (
        ("P_kn", P_kn), ("M_els_f_kncm", M_els_f_kncm),
        ("M_els_d_kncm", M_els_d_kncm)) if valor is None]
    if faltando:
        raise ValueError(
            "A Tabela 13.4 exige as verificações de tensão de 17.3.4 neste "
            f"caso ({exigencia}): informe " + ", ".join(faltando) + "."
        )
    r_f = verificar_descompressao_laje(
        P_kn=P_kn, ep_cm=ep_cm, M_kncm=M_els_f_kncm, b_cm=b_cm, h_cm=h_cm,
        estado="ELS-F", fck_mpa=fck_mpa, sinal_P=sinal_P)
    r_d = verificar_descompressao_laje(
        P_kn=P_kn, ep_cm=ep_cm, M_kncm=M_els_d_kncm, b_cm=b_cm, h_cm=h_cm,
        estado="ELS-D", fck_mpa=fck_mpa, sinal_P=sinal_P)
    memoria.extend(r_f.memoria)
    memoria.extend(r_d.memoria)
    ok = bool(r_f.ok and r_d.ok)
    if ok:
        governante = "ELS-F e ELS-D atendidos"
    elif not r_f.ok and not r_d.ok:
        governante = "ELS-F e ELS-D não atendidos"
    elif not r_f.ok:
        governante = "ELS-F não atendido"
    else:
        governante = "ELS-D não atendido"
    return ResultadoELSLajeProtendida(
        criterio="17.3.4 (descompressão e formação de fissuras)",
        exigencia_tabela_13_4=exigencia,
        wk_max_mm=None,
        fissuracao=None, els_f=r_f, els_d=r_d,
        ok=ok, governante=governante, memoria=tuple(memoria),
    )
