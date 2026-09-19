"""Testes do P16 -- Torcao completa e combinacao com flexao e cortante
(NBR 6118:2026, 17.5.1.2, 17.5.1.3, 17.5.1.4.2, 17.5.1.4.3, 17.5.1.6,
17.7.1.2, 17.7.1.4 e 17.7.2.3).

Valores esperados tirados das imagens das paginas do PDF (SCRATCH/nbr_png):
    p160 (17.5.1.2, 17.5.1.3), p161 (17.5.1.4.2, 17.5.1.4.3), p162
    (17.5.1.6), p164 (17.7.1.1 a 17.7.1.4), p165 (17.7.2).

Caso de referencia (mesmo da apostila, ja usado nos testes embutidos de
torcao_nbr6118.py, exemplo 14.3.6): viga 35 x 50, C25, c1 = 4,125 cm,
theta = 38 graus, TSd = 6808 kN.cm -> he = 10 cm, Ae = 1000 cm2, ue = 130 cm,
TRd2 = 7797 kN.cm, Asw = 6,1168 cm2/m, As,long,total = 13,0272 cm2.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import cortante_nbr6118 as V  # noqa: E402
import torcao_nbr6118 as T  # noqa: E402
import combinacao_esforcos_nbr6118 as C  # noqa: E402

BW, H, C1, FCK, THETA = 35.0, 50.0, 4.125, 25.0, 38.0
TSD = 6808.0
R_REF = T.dimensionar_torcao(TSd_kncm=TSD, bw_cm=BW, h_cm=H, c1_cm=C1,
                             fck_mpa=FCK, fywk_mpa=500.0, theta_deg=THETA,
                             he_adotado_cm=10.0)


# ===========================================================================
# 17.5.1.2 -- dispensa da torcao de compatibilidade (PDF p. 160)
# ===========================================================================
def test_dispensa_torcao_necessaria_ao_equilibrio_nunca_dispensa():
    """Torcao necessaria ao equilibrio nao pode ser desprezada, mesmo com
    adaptacao plastica adequada (17.5.1.2, PDF p. 160)."""
    r = T.torcao_compatibilidade_dispensavel(
        necessaria_ao_equilibrio=True, adaptacao_plastica_adequada=True)
    assert r.pode_desprezar is False


def test_dispensa_torcao_compatibilidade_sem_adaptacao_plastica():
    """Torcao de compatibilidade, mas sem adaptacao plastica adequada, nao
    pode ser desprezada (17.5.1.2)."""
    r = T.torcao_compatibilidade_dispensavel(
        necessaria_ao_equilibrio=False, adaptacao_plastica_adequada=False)
    assert r.pode_desprezar is False


def test_dispensa_torcao_compatibilidade_com_adaptacao_plastica():
    """Torcao de compatibilidade com adaptacao plastica adequada pode ser
    desprezada (17.5.1.2, o unico dos 3 casos que permite dispensar)."""
    r = T.torcao_compatibilidade_dispensavel(
        necessaria_ao_equilibrio=False, adaptacao_plastica_adequada=True)
    assert r.pode_desprezar is True


# ===========================================================================
# 17.5.1.2 -- limite de VSd em trecho curto (PDF p. 160)
# ===========================================================================
def test_trecho_curto_VSd_acima_do_limite_falha():
    """l = 1,5h (<= 2h, trecho curto); VSd = 0,71 VRd2 > 0,7 VRd2 -> falha
    (teste sugerido no plano)."""
    VRd2 = 679.5
    r = T.verificar_trecho_curto(l_cm=1.5 * 50.0, h_cm=50.0,
                                 VSd_kn=0.71 * VRd2, VRd2_kn=VRd2)
    assert r.trecho_curto is True
    assert r.ok is False


def test_trecho_curto_VSd_abaixo_do_limite_passa():
    """Mesmo trecho curto, VSd = 0,69 VRd2 <= 0,7 VRd2 -> passa (teste
    sugerido no plano)."""
    VRd2 = 679.5
    r = T.verificar_trecho_curto(l_cm=1.5 * 50.0, h_cm=50.0,
                                 VSd_kn=0.69 * VRd2, VRd2_kn=VRd2)
    assert r.trecho_curto is True
    assert r.ok is True


def test_trecho_nao_curto_nao_limita_VSd():
    """l = 2,5h (> 2h): o limite de 17.5.1.2 nao se aplica, mesmo com VSd
    acima de 0,7 VRd2."""
    VRd2 = 679.5
    r = T.verificar_trecho_curto(l_cm=2.5 * 50.0, h_cm=50.0,
                                 VSd_kn=0.9 * VRd2, VRd2_kn=VRd2)
    assert r.trecho_curto is False
    assert r.ok is True


def test_trecho_curto_degrau_exato_l_igual_2h():
    """l = 2h exatamente ainda conta como trecho curto (limite <=, nao <)."""
    r = T.verificar_trecho_curto(l_cm=2.0 * 50.0, h_cm=50.0,
                                 VSd_kn=100.0, VRd2_kn=679.5)
    assert r.trecho_curto is True


# ===========================================================================
# 17.5.1.3 -- condicao tripla de resistencia a torcao pura, modo
# verificacao (PDF p. 160, com TRd3/TRd4 de 17.5.1.6, PDF p. 162)
# ===========================================================================
def test_verificar_torcao_reproduz_TSd_por_construcao():
    """Com Asw e Asl vindos de dimensionar_torcao para o proprio TSd, a
    verificacao tem de "fechar": TRd3 = TRd4 = TSd (dentro da precisao de
    ponto flutuante) e as tres condicoes passam -- e o caso da apostila
    (TRd2 = 7797, TSd = 6808)."""
    v = T.verificar_torcao(
        TSd_kncm=TSD, Asw_cm2_por_m=R_REF.Asw_m,
        Asl_cm2=R_REF.As_long_total_cm2, bw_cm=BW, h_cm=H, c1_cm=C1,
        fck_mpa=FCK, fywk_mpa=500.0, theta_deg=THETA, he_adotado_cm=10.0)
    assert v.TRd2_kncm == pytest.approx(7797.0, abs=5.0)
    assert v.TRd3_kncm == pytest.approx(TSD, abs=1e-6)
    assert v.TRd4_kncm == pytest.approx(TSD, abs=1e-6)
    assert v.ok_TRd2 and v.ok_TRd3 and v.ok_TRd4
    assert v.ok is True


def test_verificar_torcao_falha_com_armadura_insuficiente():
    """Metade do Asw e do Asl necessarios: TRd3 e TRd4 caem pela metade e
    ficam abaixo de TSd -> reprova em estribos e em longitudinal (bielas
    continuam ok, pois nao dependem da armadura)."""
    v = T.verificar_torcao(
        TSd_kncm=TSD, Asw_cm2_por_m=R_REF.Asw_m / 2.0,
        Asl_cm2=R_REF.As_long_total_cm2 / 2.0, bw_cm=BW, h_cm=H, c1_cm=C1,
        fck_mpa=FCK, fywk_mpa=500.0, theta_deg=THETA, he_adotado_cm=10.0)
    assert v.TRd3_kncm == pytest.approx(TSD / 2.0, abs=1e-6)
    assert v.TRd4_kncm == pytest.approx(TSD / 2.0, abs=1e-6)
    assert v.ok_TRd2 is True
    assert v.ok_TRd3 is False
    assert v.ok_TRd4 is False
    assert v.ok is False


def test_verificar_torcao_falha_bielas_TSd_maior_que_TRd2():
    """TSd acima de TRd,2 (apostila: 7797) reprova nas bielas, mesmo com
    armadura suficiente para TRd3/TRd4 desse TSd maior."""
    v = T.verificar_torcao(
        TSd_kncm=8000.0, Asw_cm2_por_m=100.0, Asl_cm2=100.0,
        bw_cm=BW, h_cm=H, c1_cm=C1, fck_mpa=FCK, fywk_mpa=500.0,
        theta_deg=THETA, he_adotado_cm=10.0)
    assert v.ok_TRd2 is False
    assert v.ok is False


def test_verificar_torcao_theta_fora_da_faixa_levanta_FaixaNormativaError():
    """17.5.1.1 (PDF p. 160): 30 <= theta <= 45 graus, mesma faixa do
    dimensionamento (CRT-07). verificar_torcao herda a validacao de
    _validar_theta_torcao e tem de levantar FaixaNormativaError (nao um
    ValueError generico) para theta fora da faixa -- achado da verificacao
    independente (volta 1), convencao 3.3 item 3 do plano: fora da faixa
    normativa e sempre FaixaNormativaError, nunca outro tipo de erro nem um
    numero."""
    with pytest.raises(nbr.FaixaNormativaError):
        T.verificar_torcao(
            TSd_kncm=100.0, Asw_cm2_por_m=5.0, Asl_cm2=5.0, bw_cm=30.0,
            h_cm=60.0, c1_cm=4.0, fck_mpa=30.0, theta_deg=50.0)
    with pytest.raises(nbr.FaixaNormativaError):
        T.verificar_torcao(
            TSd_kncm=100.0, Asw_cm2_por_m=5.0, Asl_cm2=5.0, bw_cm=30.0,
            h_cm=60.0, c1_cm=4.0, fck_mpa=30.0, theta_deg=25.0)


# ===========================================================================
# 17.5.1.4.2 -- secao composta de retangulos (PDF p. 161)
# ===========================================================================
def test_secao_T_dois_retangulos_iguais_reparte_meio_a_meio():
    """Secao T decomposta a mao em 2 retangulos iguais (10x20 cada) deve
    dar TSdi = TSd/2 para cada um (teste sugerido no plano)."""
    TSdi = T.repartir_torcao_secao_composta([(10.0, 20.0), (10.0, 20.0)],
                                            TSd_kncm=100.0)
    assert TSdi == pytest.approx((50.0, 50.0))


def test_secao_composta_proporcional_a_a3b():
    """Secao com 2 retangulos desiguais reparte proporcionalmente a
    ai^3*bi (17.5.1.4.2): retangulo 1 (10x20) tem rigidez 10^3*20=20000;
    retangulo 2 (20x40) tem rigidez 20^3*40=320000; total=340000.
    TSd1 = 100*20000/340000 = 5,882; TSd2 = 100*320000/340000 = 94,118."""
    TSdi = T.repartir_torcao_secao_composta(
        [(10.0, 20.0), (20.0, 40.0)], TSd_kncm=100.0)
    assert TSdi[0] == pytest.approx(100.0 * 20000.0 / 340000.0, rel=1e-9)
    assert TSdi[1] == pytest.approx(100.0 * 320000.0 / 340000.0, rel=1e-9)
    assert sum(TSdi) == pytest.approx(100.0)


def test_secao_composta_a_maior_que_b_e_erro():
    """a (lado menor) > b (lado maior) e entrada invertida -> erro
    (17.5.1.4.2 define a como o lado menor)."""
    with pytest.raises(nbr.FaixaNormativaError):
        T.repartir_torcao_secao_composta([(20.0, 10.0)], TSd_kncm=100.0)


# ===========================================================================
# 17.5.1.4.1/.3 -- caso A/u < 2c1 (secao esbelta) e secao ja vazada real
# (PDF p. 160-161)
# ===========================================================================
def test_secao_esbelta_A_sobre_u_menor_que_2c1():
    """bw=20, h=20, c1=6: A/u = 400/80 = 5 cm; 2c1 = 12 cm; como
    A/u < 2c1, he = min(A/u, bw-2c1) = min(5, 8) = 5 cm; Ae e ue pelos
    eixos das armaduras de canto: Ae=(20-12)*(20-12)=64 cm2;
    ue=2*((20-12)+(20-12))=32 cm. Caso que a auditoria (CRT-06) deixou sem
    cobertura em pytest (17.5.1.4.1, PDF p. 160-161)."""
    sec = T.secao_vazada_retangular(bw_cm=20.0, h_cm=20.0, c1_cm=6.0)
    assert sec["caso_esbelto"] is True
    assert sec["he_max_cm"] == pytest.approx(5.0)
    assert sec["he_min_cm"] == pytest.approx(12.0)
    assert sec["he_cm"] == pytest.approx(5.0)
    assert sec["Ae_cm2"] == pytest.approx(64.0)
    assert sec["ue_cm"] == pytest.approx(32.0)


def test_secao_vazada_real_espessura_governa_a_real():
    """Viga caixao bw=100, h=60 (contorno externo), parede real = 8 cm:
    A/u = 6000/320 = 18,75 cm (espessura equivalente da secao cheia); como
    a parede real (8 cm) e menor, ela governa (17.5.1.4.3, PDF p. 161)."""
    he = T.espessura_parede_vazada_real(he_real_cm=8.0, bw_cm=100.0,
                                        h_cm=60.0)
    assert he == pytest.approx(8.0)


def test_secao_vazada_real_equivalente_governa_quando_parede_e_grossa():
    """Mesma secao (A/u = 18,75 cm), com parede real = 25 cm (mais grossa
    que a equivalente): nesse caso a espessura equivalente da secao cheia
    e que governa (menor das duas), confirmando o outro lado do "min" de
    17.5.1.4.3."""
    he = T.espessura_parede_vazada_real(he_real_cm=25.0, bw_cm=100.0,
                                        h_cm=60.0)
    assert he == pytest.approx(18.75)


# ===========================================================================
# 17.5.1.6 -- arranjo da armadura longitudinal de torcao (PDF p. 162)
# ===========================================================================
def test_distribuicao_asl_proporcional_ao_trecho():
    """Retangulo Ae com lados (25, 40, 25, 40) cm, ue = 130 cm, com
    As,l,total = 13,03 cm2 (caso de referencia): a taxa constante
    As,l,total/ue = 0,1002 cm2/cm reparte 2,506 cm2 nos trechos de 25 cm e
    4,009 cm2 nos de 40 cm (17.5.1.6)."""
    dist = T.distribuir_armadura_longitudinal_torcao(
        As_long_total_cm2=R_REF.As_long_total_cm2, ue_cm=R_REF.ue,
        trechos_cm=[25.0, 40.0, 25.0, 40.0],
        barras_por_vertice=[2, 2, 2, 2])
    taxa_esperada = R_REF.As_long_total_cm2 / R_REF.ue
    assert dist.taxa_cm2_por_cm == pytest.approx(taxa_esperada)
    assert dist.As_por_trecho_cm2[0] == pytest.approx(25.0 * taxa_esperada)
    assert dist.As_por_trecho_cm2[1] == pytest.approx(40.0 * taxa_esperada)
    assert dist.ok_vertices is True
    assert dist.ok is True


def test_distribuicao_asl_falha_sem_barra_em_um_vertice():
    """Um vertice sem nenhuma barra longitudinal reprova a exigencia de
    17.5.1.6 ("em cada vertice ... pelo menos uma barra longitudinal"),
    mesmo com a taxa proporcional correta."""
    dist = T.distribuir_armadura_longitudinal_torcao(
        As_long_total_cm2=R_REF.As_long_total_cm2, ue_cm=R_REF.ue,
        trechos_cm=[25.0, 40.0, 25.0, 40.0],
        barras_por_vertice=[2, 0, 2, 2])
    assert dist.ok_vertices is False
    assert dist.ok is False


def test_distribuicao_asl_soma_trechos_diferente_de_ue_e_erro():
    """Soma dos trechos != ue e entrada inconsistente -> erro (17.5.1.6)."""
    with pytest.raises(nbr.FaixaNormativaError):
        T.distribuir_armadura_longitudinal_torcao(
            As_long_total_cm2=13.03, ue_cm=130.0,
            trechos_cm=[25.0, 40.0, 25.0, 30.0])  # soma = 120, não 130


def test_distribuicao_asl_sem_vertices_pula_verificacao():
    """barras_por_vertice=None so calcula a distribuicao proporcional, sem
    reprovar por falta de barra (verificacao pulada por falta de dado)."""
    dist = T.distribuir_armadura_longitudinal_torcao(
        As_long_total_cm2=13.03, ue_cm=130.0,
        trechos_cm=[25.0, 40.0, 25.0, 40.0])
    assert dist.barras_por_vertice is None
    assert dist.ok is True


# ===========================================================================
# 17.7.1.2 -- soma da armadura longitudinal de torcao com a de flexao
# (PDF p. 164)
# ===========================================================================
def test_As_longitudinal_total_soma_flexao_e_torcao():
    """Viga com M e T conhecidos: As total esperado = As(so M) +
    As,long,torcao/4 (uma face), teste sugerido no plano. Usa 1/4 do
    As,long,total do caso de referencia (secao retangular, 4 lados)."""
    As_flexao = 8.0
    As_torcao_face = R_REF.As_long_total_cm2 / 4.0
    total = C.As_longitudinal_total(As_flexao, As_torcao_face)
    assert total == pytest.approx(As_flexao + As_torcao_face)
    assert total == pytest.approx(8.0 + R_REF.As_long_total_cm2 / 4.0)


def test_As_longitudinal_total_negativo_e_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        C.As_longitudinal_total(-1.0, 2.0)


# ===========================================================================
# 17.7.2.3 -- soma das armaduras transversais para V e T (PDF p. 165)
# ===========================================================================
def test_Asw_total_soma_os_dois_modulos_separados():
    """Soma a Asw da viga de referencia de cortante (test_p15_cortante,
    C25, bw=14, d=46, VSd=153 kN, Modelo I) com a Asw de torcao da secao
    de referencia deste pacote (apostila, TSd=6808), e confere que bate
    com a soma feita fora da biblioteca."""
    asw_V = V.modelo_calculo_I(VSd_kn=153.0, bw_cm=14.0, d_cm=46.0,
                               fck_mpa=25.0).Asw_m
    asw_T = R_REF.Asw_m
    total = C.Asw_total(asw_V, asw_T)
    assert total == pytest.approx(asw_V + asw_T)
    # Conferido com os dois testes de apostila já existentes:
    # cortante Asw = 5,7469 cm2/m (test_exemplo_5_15_modeloI, VSd=153 kN,
    # Modelo I); torção Asw = 6,1168 cm2/m (exemplo 14.3.6).
    assert asw_V == pytest.approx(5.7469, abs=0.001)
    assert asw_T == pytest.approx(6.1168, abs=0.001)


def test_Asw_total_negativo_e_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        C.Asw_total(-1.0, 2.0)


# ===========================================================================
# 17.7.1.4 -- tensao principal de compressao no banzo comprimido (PDF p. 164)
# ===========================================================================
def test_tau_Td_formula():
    """tau_Td = Td / (2 Ae he): TSd=6808 kN.cm, Ae=1000 cm2, he=10 cm ->
    tau_Td = 6808/(2*1000*10) = 0,3404 kN/cm2 = 3,404 MPa."""
    tau = C.tau_Td_kncm2(TSd_kncm=6808.0, Ae_cm2=1000.0, he_cm=10.0)
    assert tau == pytest.approx(0.3404)


def test_tensao_principal_sem_torcao_recai_na_flexao_pura():
    """Caso sem torcao (Td=0): tau_Td=0 -> tensao principal = tensao
    normal media do banzo (verificacao recai na flexao pura) -- teste
    sugerido no plano."""
    r = C.tensao_principal_banzo_comprimido(
        sigma_cd_mpa=10.0, TSd_kncm=0.0, Ae_cm2=1000.0, he_cm=10.0)
    assert r.tau_Td_mpa == pytest.approx(0.0)
    assert r.sigma_c_principal_mpa == pytest.approx(10.0)


def test_tensao_principal_com_torcao_supera_tensao_normal():
    """Com torcao (TSd=6808 kN.cm), a tensao principal de compressao
    supera a tensao normal media pura (sigma_cd=10 MPa), pelo termo de
    Mohr: sigma_c,principal = sigma_cd/2 + raiz((sigma_cd/2)^2+tau^2) =
    5 + raiz(25+3,404^2) = 5 + raiz(36,587) = 5 + 6,0487 = 11,0487 MPa."""
    r = C.tensao_principal_banzo_comprimido(
        sigma_cd_mpa=10.0, TSd_kncm=6808.0, Ae_cm2=1000.0, he_cm=10.0)
    assert r.tau_Td_mpa == pytest.approx(3.404, abs=0.001)
    assert r.sigma_c_principal_mpa == pytest.approx(11.0487, abs=0.001)
    assert r.sigma_c_principal_mpa > 10.0
    assert r.ok is None  # sem limite informado (Secao 22, fora do pacote)


def test_tensao_principal_com_limite_informado():
    """Com sigma_limite_mpa informado, a funcao compara e devolve ok."""
    r_ok = C.tensao_principal_banzo_comprimido(
        sigma_cd_mpa=10.0, TSd_kncm=6808.0, Ae_cm2=1000.0, he_cm=10.0,
        sigma_limite_mpa=20.0)
    assert r_ok.ok is True
    r_falha = C.tensao_principal_banzo_comprimido(
        sigma_cd_mpa=10.0, TSd_kncm=6808.0, Ae_cm2=1000.0, he_cm=10.0,
        sigma_limite_mpa=10.0)
    assert r_falha.ok is False


def test_tau_Td_area_ou_espessura_nao_positiva_e_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        C.tau_Td_kncm2(TSd_kncm=100.0, Ae_cm2=0.0, he_cm=10.0)
