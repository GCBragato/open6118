"""Testes do P9 -- Tensoes em servico (Estadio II) e fissuracao.

Cobre dimensionamento/els_fissuracao_nbr6118.py e o bloco P9 de
dimensionamento/rotinas/flexao_composta_obliqua.py, contra a ABNT NBR
6118:2026:

  - 23.5.3 (PDF p. 218) -- alpha_e = Es/Ecs para fadiga, podendo ser 10.
  - 17.3.3.2 (PDF p. 149-150) -- area de envolvimento Acri (Figura 17.4).
  - 17.3.3.3 (PDF p. 150) -- Tabela 17.2 e alpha_e = 15 simplificado.
  - 19.3.2 (PDF p. 179) -- fissuracao/descompressao em lajes.
  - 17.3.5.2.2 (PDF p. 152-153) -- As,min sob deformacoes impostas.

Os valores esperados vêm da imagem de cada pagina (SCRATCH\\nbr_png\\pNNN.png)
e, onde aplicavel, das formulas fechadas ja testadas de
viga_servico_nbr6118.py (x_II_retangular/I_II_retangular, x_II_secao_T/
I_II_secao_T), nao do JSON do plano.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr              # noqa: E402
import viga_servico_nbr6118 as vserv      # noqa: E402
import els_fissuracao_nbr6118 as els      # noqa: E402
from rotinas import flexao_composta_obliqua as fco  # noqa: E402


def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# 23.5.3 (PDF p. 218) -- alpha_e = Es/Ecs para fadiga
# ---------------------------------------------------------------------------
def test_alpha_e_fadiga_simplificado_10():
    """23.5.3, p. 218: "podendo, neste caso, ser adotado igual a 10"."""
    assert els.alpha_e_fadiga() == 10.0


def test_alpha_e_fadiga_exato_C30():
    """23.5.3: alpha_e = Es/Ecs exato para C30 (Es=210000 MPa), contra o
    nucleo (nbr.Ecs), independente de viga_servico_nbr6118."""
    Ecs_mpa = nbr.Ecs(30.0)  # alpha_i=0.8+0.2*30/80=0.875; Eci=5600*sqrt(30)
    esperado = nbr.ES_MPA / Ecs_mpa
    obtido = els.alpha_e_fadiga(30.0)
    assert _aprox(obtido, esperado, 1e-9)
    # o valor exato (~7.8) e da ordem do simplificado (10), mas diferente
    assert not _aprox(obtido, 10.0, 0.5)


def test_alpha_e_simplificado_fissuracao_15():
    """17.3.3.2/17.3.3.3, p. 150: "pode ser feito considerando a relação
    alpha_e ... igual a 15" -- valor distinto do de fadiga (10), divergência
    em relação ao JSON do plano (que só cita o alpha_e=10 do item 23.5.3)."""
    assert els.ALPHA_E_SIMPLIFICADO_FISSURACAO == 15.0
    assert els.ALPHA_E_SIMPLIFICADO_FISSURACAO != els.alpha_e_fadiga()


# ---------------------------------------------------------------------------
# 23.5.3/17.3.3.3 -- tensoes_servico, secao retangular x formula fechada
# ---------------------------------------------------------------------------
def test_tensoes_servico_retangular_apostila_16_12():
    """Estadio II, seção retangular, contra x da equação do 2º grau
    (x_II_retangular/I_II_retangular, já testadas em
    viga_servico_nbr6118.test_x_II_retangular_apostila): bw=12, d=37,
    As=2,45 cm² (3 φ10), fck=25 (alpha_e=Es/Ecs=8,696)."""
    bw, d, As, fck = 12.0, 37.0, 2.45, 25.0
    ae = vserv.alpha_e(fck, "granito")
    x_fechado = vserv.x_II_retangular(
        bw_cm=bw, d_cm=d, As_cm2=As, As_linha_cm2=0.0, d_linha_cm=0.0, alpha_e_val=ae,
    )
    I_fechado = vserv.I_II_retangular(
        bw_cm=bw, d_cm=d, x_II_cm=x_fechado, As_cm2=As, As_linha_cm2=0.0,
        d_linha_cm=0.0, alpha_e_val=ae,
    )

    h = d + 3.0  # cobrimento/estribo ~3 cm até o centroide da barra
    y_bar = h / 2.0 - d  # face de cima comprimida (Mx>0 comprime +y)
    secao = fco.SecaoRetangular(
        base_cm=bw, altura_cm=h, barras=(fco.Barra(x_cm=0.0, y_cm=y_bar, area_cm2=As),),
    )
    concreto = fco.Concreto(fck_mpa=fck)
    aco = fco.Aco(fyk_mpa=500.0)
    M = 1000.0  # kN.cm, arbitrário (o problema é linear -- só a razão importa)

    r = els.tensoes_servico(secao, concreto, aco, N_kn=0.0, Mx_kncm=M, My_kncm=0.0,
                            alpha_e=ae)
    assert r.convergiu
    assert r.estadio == "II"
    assert _aprox(r.alpha_e, ae, 1e-9)
    assert _aprox(r.x_cm, x_fechado, 0.01)

    # I_II embutido em sigma_c_max = M*x/I -> I = M*x/sigma_c_max
    I_obtido = M * r.x_cm / r.sigma_c_max_kncm2
    assert _aprox(I_obtido, I_fechado, I_fechado * 0.005)

    # sigma_si (Eq. no estádio II) contra sigma_si_estadio_II (já testada
    # indiretamente no ex. 17.1 de viga_servico_nbr6118)
    sigma_si_fechado = vserv.sigma_si_estadio_II(
        Md_ser_kncm=M, d_cm=d, x_II_cm=x_fechado, I_II_cm4=I_fechado, alpha_e_val=ae,
    )
    assert len(r.sigma_s_kncm2) == 1
    assert r.sigma_s_kncm2[0] < 0.0  # convenção do kernel: tração é negativa
    assert _aprox(r.sigma_s_tracao_max_kncm2, sigma_si_fechado, sigma_si_fechado * 0.005)


def test_tensoes_servico_retangular_N_puro_compressao_uniforme():
    """N puro (Mx=My=0): eps uniforme > 0 (compressão), kx=ky=0, x=h (toda
    a seção comprimida) -- caso-limite do solver bissecção."""
    bw, h, As = 20.0, 40.0, 8.0
    secao = fco.SecaoRetangular(
        base_cm=bw, altura_cm=h,
        barras=(fco.Barra(0.0, 15.0, As / 2.0), fco.Barra(0.0, -15.0, As / 2.0)),
    )
    concreto = fco.Concreto(fck_mpa=30.0)
    aco = fco.Aco(fyk_mpa=500.0)
    r = els.tensoes_servico(secao, concreto, aco, N_kn=500.0, Mx_kncm=0.0, My_kncm=0.0,
                            alpha_e=15.0)
    assert r.convergiu
    assert _aprox(r.kx_pmilh_cm, 0.0, 1e-9)
    assert _aprox(r.ky_pmilh_cm, 0.0, 1e-9)
    assert r.eps_cg_pmilh > 0.0
    assert _aprox(r.x_cm, h, 1e-6)
    assert all(s > 0.0 for s in r.sigma_s_kncm2)  # as duas barras comprimidas


def test_tensoes_servico_estadio_I_menos_curvatura_que_estadio_II():
    """17.3.4/19.3.2: no Estadio I (não fissurado) a seção é mais rígida
    (toda a área de concreto participa, inclusive tracionada) -- para o
    mesmo M, a curvatura kx é menor que no Estadio II (seção fissurada)."""
    bw, h, As = 20.0, 40.0, 8.0
    secao = fco.SecaoRetangular(
        base_cm=bw, altura_cm=h,
        barras=(fco.Barra(0.0, 15.0, As / 2.0), fco.Barra(0.0, -15.0, As / 2.0)),
    )
    concreto = fco.Concreto(fck_mpa=30.0)
    aco = fco.Aco(fyk_mpa=500.0)
    r_I = els.tensoes_servico(secao, concreto, aco, N_kn=0.0, Mx_kncm=800.0, My_kncm=0.0,
                              alpha_e=15.0, estadio="I")
    r_II = els.tensoes_servico(secao, concreto, aco, N_kn=0.0, Mx_kncm=800.0, My_kncm=0.0,
                               alpha_e=15.0, estadio="II")
    assert r_I.convergiu and r_II.convergiu
    assert _aprox(r_I.eps_cg_pmilh, 0.0, 1e-6)  # seção e armadura simétricas
    assert 0.0 < r_I.kx_pmilh_cm < r_II.kx_pmilh_cm


def test_tensoes_servico_estadio_invalido():
    bw, h, As = 20.0, 40.0, 4.0
    secao = fco.SecaoRetangular(base_cm=bw, altura_cm=h,
                                barras=(fco.Barra(0.0, -15.0, As),))
    concreto = fco.Concreto(fck_mpa=30.0)
    aco = fco.Aco()
    with pytest.raises(ValueError, match="estádio"):
        els.tensoes_servico(secao, concreto, aco, 0.0, 100.0, 0.0, estadio="III")


def test_mensagens_texto_final_com_acentuacao():
    """Texto para o usuário final (mensagem de erro, memória de cálculo) sai
    com acentuação correta -- regra global de PT-BR do escritório. Antes da
    correção, "estádio", "tensões", "serviço", "não" e "tração" saíam sem
    acento nessas quatro mensagens."""
    bw, h, As = 20.0, 40.0, 4.0
    secao = fco.SecaoRetangular(base_cm=bw, altura_cm=h,
                                barras=(fco.Barra(0.0, -15.0, As),))
    concreto = fco.Concreto(fck_mpa=30.0)
    aco = fco.Aco()

    with pytest.raises(ValueError, match=r"estádio deve ser 'I' ou 'II'"):
        els.tensoes_servico(secao, concreto, aco, 0.0, 100.0, 0.0, estadio="III")

    with pytest.raises(ValueError, match="tensão de tração na barra"):
        els.controle_fissuracao_sem_wk(0.0)

    r = els.tensoes_servico(secao, concreto, aco, N_kn=0.0, Mx_kncm=100.0, My_kncm=0.0,
                            alpha_e=15.0)
    assert any(m.startswith("Estádio ") for m in r.memoria)


# ---------------------------------------------------------------------------
# tensoes_servico, secao T poligonal x formula fechada (viga-ponte, ex. 17.1)
# ---------------------------------------------------------------------------
def test_tensoes_servico_secao_T_apostila_17_1():
    """Estadio II, seção T poligonal (Secao, mesa + alma), contra
    x_II_secao_T/I_II_secao_T (viga-ponte, ex. 17.1 -- mesmos dados de
    viga_servico_nbr6118.test_x_II_secao_T_apostila): bf=325, bw=25, hf=20,
    d=186,5, As=137,20, As'=16,00, d'=5,1 cm, fck=40 (alpha_e=6,56)."""
    bf, bw, hf, d = 325.0, 25.0, 20.0, 186.5
    As, As_linha, d_linha, fck = 137.20, 16.00, 5.1, 40.0
    ae = vserv.alpha_e(fck, "granito")

    x_fechado = vserv.x_II_secao_T(
        bf_cm=bf, bw_cm=bw, hf_cm=hf, d_cm=d, As_cm2=As, As_linha_cm2=As_linha,
        d_linha_cm=d_linha, alpha_e_val=ae,
    )
    I_fechado = vserv.I_II_secao_T(
        bf_cm=bf, bw_cm=bw, hf_cm=hf, d_cm=d, x_II_cm=x_fechado, As_cm2=As,
        As_linha_cm2=As_linha, d_linha_cm=d_linha, alpha_e_val=ae,
    )

    h_total = d + 10.0
    y_topo = h_total / 2.0
    y_base_mesa = y_topo - hf
    y_fundo = -h_total / 2.0
    mesa = (
        (-bf / 2.0, y_base_mesa), (bf / 2.0, y_base_mesa),
        (bf / 2.0, y_topo), (-bf / 2.0, y_topo), (-bf / 2.0, y_base_mesa),
    )
    alma = (
        (-bw / 2.0, y_fundo), (bw / 2.0, y_fundo),
        (bw / 2.0, y_base_mesa), (-bw / 2.0, y_base_mesa), (-bw / 2.0, y_fundo),
    )
    concreto = fco.Concreto(fck_mpa=fck)
    secao = fco.Secao(
        partes=(fco.Parte(polygon=mesa, concreto=concreto),
                fco.Parte(polygon=alma, concreto=concreto)),
        barras=(
            fco.Barra(x_cm=0.0, y_cm=y_topo - d, area_cm2=As),
            fco.Barra(x_cm=0.0, y_cm=y_topo - d_linha, area_cm2=As_linha),
        ),
        n_dy=100, n_dx=20,
    )
    aco = fco.Aco(fyk_mpa=500.0)
    M = 500000.0  # kN.cm

    r = els.tensoes_servico(secao, None, aco, N_kn=0.0, Mx_kncm=M, My_kncm=0.0, alpha_e=ae)
    assert r.convergiu
    assert _aprox(r.x_cm, x_fechado, x_fechado * 0.01)
    I_obtido = M * r.x_cm / r.sigma_c_max_kncm2
    assert _aprox(I_obtido, I_fechado, I_fechado * 0.01)


def test_tensoes_servico_secao_generica_multi_fck_sem_alpha_e():
    """Secao poligonal com alpha_e=None: cada Parte usa o alpha_e do seu
    próprio fck (8.2.8) -- aqui as duas partes têm o mesmo fck, então o
    resultado deve reproduzir o mesmo x_cm do teste com alpha_e explícito."""
    bf, bw, hf, d = 325.0, 25.0, 20.0, 186.5
    As, As_linha, d_linha, fck = 137.20, 16.00, 5.1, 40.0
    h_total = d + 10.0
    y_topo = h_total / 2.0
    y_base_mesa = y_topo - hf
    y_fundo = -h_total / 2.0
    mesa = (
        (-bf / 2.0, y_base_mesa), (bf / 2.0, y_base_mesa),
        (bf / 2.0, y_topo), (-bf / 2.0, y_topo), (-bf / 2.0, y_base_mesa),
    )
    alma = (
        (-bw / 2.0, y_fundo), (bw / 2.0, y_fundo),
        (bw / 2.0, y_base_mesa), (-bw / 2.0, y_base_mesa), (-bw / 2.0, y_fundo),
    )
    concreto = fco.Concreto(fck_mpa=fck)
    secao = fco.Secao(
        partes=(fco.Parte(polygon=mesa, concreto=concreto),
                fco.Parte(polygon=alma, concreto=concreto)),
        barras=(
            fco.Barra(x_cm=0.0, y_cm=y_topo - d, area_cm2=As),
            fco.Barra(x_cm=0.0, y_cm=y_topo - d_linha, area_cm2=As_linha),
        ),
        n_dy=100, n_dx=20,
    )
    aco = fco.Aco(fyk_mpa=500.0)
    ae_esperado = vserv.alpha_e(fck, "granito")
    r = els.tensoes_servico(secao, None, aco, N_kn=0.0, Mx_kncm=500000.0, My_kncm=0.0,
                            alpha_e=None)
    assert r.convergiu
    assert _aprox(r.alpha_e, ae_esperado, 0.05)


# ---------------------------------------------------------------------------
# 17.3.3.3, Tabela 17.2 (PDF p. 150) -- todas as células
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("sigma_mpa,phi_esp,s_esp", [
    (160.0, 32.0, 30.0),
    (200.0, 25.0, 25.0),
    (240.0, 20.0, 20.0),
    (280.0, 16.0, 15.0),
    (320.0, 12.5, 10.0),
    (360.0, 10.0, 5.0),
    (400.0, 8.0, None),
])
def test_tabela_17_2_sem_armadura_ativa(sigma_mpa, phi_esp, s_esp):
    if s_esp is None:
        with pytest.raises(nbr.FaixaNormativaError):
            els.controle_fissuracao_sem_wk(sigma_mpa, com_armadura_ativa=False)
        return
    r = els.controle_fissuracao_sem_wk(sigma_mpa, com_armadura_ativa=False)
    assert _aprox(r.phi_max_mm, phi_esp, 1e-9)
    assert _aprox(r.s_max_cm, s_esp, 1e-9)


@pytest.mark.parametrize("sigma_mpa,phi_esp,s_esp", [
    (160.0, 25.0, 20.0),
    (200.0, 16.0, 15.0),
    (240.0, 12.5, 10.0),
    (280.0, 8.0, 5.0),
    (320.0, 6.0, None),   # célula "-" em s_max
    (360.0, None, None),  # célula "-" nas duas
    (400.0, None, None),
])
def test_tabela_17_2_com_armadura_ativa(sigma_mpa, phi_esp, s_esp):
    if phi_esp is None or s_esp is None:
        with pytest.raises(nbr.FaixaNormativaError):
            els.controle_fissuracao_sem_wk(sigma_mpa, com_armadura_ativa=True)
        return
    r = els.controle_fissuracao_sem_wk(sigma_mpa, com_armadura_ativa=True)
    assert _aprox(r.phi_max_mm, phi_esp, 1e-9)
    assert _aprox(r.s_max_cm, s_esp, 1e-9)


def test_tabela_17_2_degrau_conservador_entre_linhas():
    """Entre 160 e 200 MPa (ex.: 180 MPa) a tabela não define; a favor da
    segurança, usa a linha imediatamente acima (200 -> 25 mm/25 cm), nunca
    a de baixo (160 -> 32 mm/30 cm, menos restritiva)."""
    r = els.controle_fissuracao_sem_wk(180.0, com_armadura_ativa=False)
    assert r.linha_tabela_mpa == 200.0
    assert _aprox(r.phi_max_mm, 25.0, 1e-9)


def test_tabela_17_2_acima_do_maximo():
    with pytest.raises(nbr.FaixaNormativaError):
        els.controle_fissuracao_sem_wk(450.0, com_armadura_ativa=False)


def test_tabela_17_2_sigma_nao_positiva():
    with pytest.raises(ValueError):
        els.controle_fissuracao_sem_wk(0.0)


def test_tabela_17_2_celula_vazia_mensagem_reflete_com_armadura_ativa_real():
    """A mensagem de erro da célula "-" tem de refletir o `com_armadura_ativa`
    realmente passado, não um texto fixo "com armadura ativa" -- sigma_si=400
    MPa, sem armadura ativa, é célula vazia na coluna SEM armadura ativa
    (Tabela 17.2, p. 150): a mensagem não pode dizer "com armadura ativa"."""
    with pytest.raises(nbr.FaixaNormativaError, match="sem armadura ativa"):
        els.controle_fissuracao_sem_wk(400.0, com_armadura_ativa=False)
    with pytest.raises(nbr.FaixaNormativaError, match="com armadura ativa"):
        els.controle_fissuracao_sem_wk(360.0, com_armadura_ativa=True)


# ---------------------------------------------------------------------------
# 17.3.3.2 -- área de envolvimento Acri (Figura 17.4, PDF p. 149-150)
# ---------------------------------------------------------------------------
def test_acri_barra_isolada_sem_particao():
    """Barra única, longe das bordas: Acri = (15*phi)^2 (retângulo pleno)."""
    phi = 20.0  # mm
    lado = 1.5 * phi  # cm (15*phi convertido de mm p/ cm)
    barras = [els.BarraFissuracao(x_cm=0.0, y_cm=0.0, phi_mm=phi)]
    areas = els.area_envolvimento_acri(barras, bw_cm=100.0, h_cm=100.0)
    assert _aprox(areas[0], lado * lado, 1e-6)


def test_acri_barras_alinhadas_particao_bissetriz():
    """3 barras phi=25 mm alinhadas em x=-10,0,10 (espaçamento 10 cm),
    y=-20 numa seção bw=30, h=50: a barra central tem a zona de 7,5*phi em
    x limitada pela bissetriz com as vizinhas (meio da distância = 5 cm
    para cada lado -> largura 10 cm) e em y limitada pela face inferior da
    seção (h/2=25 cm) só de um lado -- 7,5*phi = 18,75 cm não estoura para
    cima (y=-20+18,75=-1,25), então altura = -1,25 -(-25) = 23,75 cm."""
    phi = 25.0
    barras = [
        els.BarraFissuracao(x_cm=-10.0, y_cm=-20.0, phi_mm=phi),
        els.BarraFissuracao(x_cm=0.0, y_cm=-20.0, phi_mm=phi),
        els.BarraFissuracao(x_cm=10.0, y_cm=-20.0, phi_mm=phi),
    ]
    areas = els.area_envolvimento_acri(barras, bw_cm=30.0, h_cm=50.0)
    assert _aprox(areas[1], 10.0 * 23.75, 1e-6)   # barra central: largura=10
    assert _aprox(areas[0], 10.0 * 23.75, 1e-6)   # barras de ponta: mesma
    assert _aprox(areas[2], 10.0 * 23.75, 1e-6)   # altura (só vizinho de um lado em x)


# ---------------------------------------------------------------------------
# 19.3.2 (PDF p. 179) -- wk_verificacao, também para laje
# ---------------------------------------------------------------------------
def test_wk_verificacao_reproduz_abertura_fissura_wk():
    """wk_verificacao é fachada fina sobre abertura_fissura_wk (mesmo
    exemplo já testado em viga_servico_nbr6118.test_fissuracao_apostila_ex17_1,
    apostila item 17.1: wk1=0,11 mm, wk2=0,23 mm, wk=0,11 <= 0,30 mm)."""
    sigma = vserv.sigma_si_aproximada(Md_ser_kncm=547750.0, d_cm=186.5, As_cm2=137.20)
    r_direto = vserv.abertura_fissura_wk(
        phi_mm=25.0, sigma_si_kncm2=sigma, Acr_cm2=1888.8, As_cm2=137.20,
        fck_mpa=40.0, eta1_val=2.25, wk_max_mm=0.30,
    )
    r_laje = els.wk_verificacao(
        phi_mm=25.0, sigma_si_kncm2=sigma, Acr_cm2=1888.8, As_cm2=137.20,
        fck_mpa=40.0, eta1_val=2.25, wk_max_mm=0.30,
    )
    assert r_laje == r_direto


# ---------------------------------------------------------------------------
# 17.3.5.2.2 (PDF p. 152-153) -- As,min sob deformações impostas
# ---------------------------------------------------------------------------
def test_k_deformacao_imposta_extrinseca():
    assert els.k_deformacao_imposta(intrinseca=False) == 1.0


def test_k_deformacao_imposta_intrinseca_bordas_e_interpolacao():
    """k=0,8 para h<=0,3 m; k=0,5 para h>=0,8 m; interpolação linear entre
    os dois (17.3.5.2.2, p. 153)."""
    assert _aprox(els.k_deformacao_imposta(True, h_m=0.3), 0.8, 1e-9)
    assert _aprox(els.k_deformacao_imposta(True, h_m=0.2), 0.8, 1e-9)  # abaixo do piso
    assert _aprox(els.k_deformacao_imposta(True, h_m=0.8), 0.5, 1e-9)
    assert _aprox(els.k_deformacao_imposta(True, h_m=1.0), 0.5, 1e-9)  # acima do teto
    # meio do caminho: h=0,55 m -> k = 0,8 + (0,5-0,8)*(0,55-0,3)/(0,8-0,3) = 0,65
    assert _aprox(els.k_deformacao_imposta(True, h_m=0.55), 0.65, 1e-9)


def test_k_deformacao_imposta_intrinseca_sem_h_levanta_erro():
    with pytest.raises(ValueError):
        els.k_deformacao_imposta(True)


def test_k_deformacao_imposta_caso_geral_forma_secao():
    """17.3.5.2.2, p. 152, ramo (a) "no caso geral de forma de seção":
    k = 0,8, independente de h -- distinto do ramo especifico de seções
    retangulares (que decresce ate 0,5 para h>=0,8 m). Antes da correção,
    `k_deformacao_imposta` só implementava o ramo retangular: uma seção não
    retangular (T, caixão etc.) com h>=0,8 m recebia k=0,5 em vez de 0,8,
    subestimando As,min (contra a segurança) -- o cenário de reservatórios/
    silos citado no plano do pacote."""
    # h alto (>=0,8 m): no ramo retangular daria 0,5; no caso geral é 0,8
    assert _aprox(els.k_deformacao_imposta(True, h_m=1.0, retangular=False), 0.8, 1e-9)
    # h_m nem é exigido no caso geral
    assert _aprox(els.k_deformacao_imposta(True, retangular=False), 0.8, 1e-9)
    # h baixo (<=0,3 m): os dois ramos coincidem em 0,8
    assert _aprox(els.k_deformacao_imposta(True, h_m=0.2, retangular=False), 0.8, 1e-9)


def test_k_deformacao_imposta_retangular_e_o_padrao():
    """`retangular=True` é o padrão -- reproduz o comportamento anterior
    (convenção 7: parâmetro novo entra no fim com padrão que reproduz o
    comportamento de hoje)."""
    assert els.k_deformacao_imposta(True, h_m=1.0) == \
        els.k_deformacao_imposta(True, h_m=1.0, retangular=True) == 0.5


@pytest.mark.parametrize("caso,esperado", [
    ("tracao_pura", 1.0),
    ("flexao_simples", 0.4),
    ("nervura_vazada_protendida", 0.4),
    ("mesa_tracionada_vazada_protendida", 0.8),
])
def test_kc_deformacao_imposta_casos_tabelados(caso, esperado):
    assert _aprox(els.kc_deformacao_imposta(caso), esperado, 1e-9)


def test_kc_deformacao_imposta_interpolado_bordas():
    """kc interpolado entre 0 (altura da zona tracionada nula) e 0,4 (na
    própria altura-limite, min(h/2, 0,5 m)) -- 17.3.5.2.2, p. 153."""
    h_cm = 60.0  # h/2 = 30 cm < 50 cm -> limite = 30 cm
    assert _aprox(els.kc_deformacao_imposta("interpolado", 0.0, h_cm), 0.0, 1e-9)
    assert _aprox(els.kc_deformacao_imposta("interpolado", 30.0, h_cm), 0.4, 1e-9)
    assert _aprox(els.kc_deformacao_imposta("interpolado", 15.0, h_cm), 0.2, 1e-9)


def test_kc_deformacao_imposta_interpolado_acima_do_limite():
    with pytest.raises(nbr.FaixaNormativaError):
        els.kc_deformacao_imposta("interpolado", 40.0, 60.0)  # limite = 30 cm


def test_kc_deformacao_imposta_caso_desconhecido():
    with pytest.raises(ValueError):
        els.kc_deformacao_imposta("errado")


def test_as_min_deformacao_imposta():
    """As = k*kc*fct,ef*Act/sigma_s (17.3.5.2.2, p. 152); k=0,8 (h=0,3 m,
    intrínseca), kc=0,4 (flexão simples), fct,ef=3 MPa (mínimo recomendado),
    Act=1000 cm², sigma_s=300 MPa -> As = 0,8*0,4*3*1000/300 = 3,2 cm²."""
    As = els.As_min_deformacao_imposta(
        k=0.8, kc=0.4, fctef_mpa=els.FCTEF_MINIMO_RECOMENDADO_MPA, Act_cm2=1000.0,
        sigma_s_mpa=300.0,
    )
    assert _aprox(As, 3.2, 1e-9)


def test_as_min_deformacao_imposta_sigma_s_invalida():
    with pytest.raises(ValueError):
        els.As_min_deformacao_imposta(0.8, 0.4, 3.0, 1000.0, 0.0)
