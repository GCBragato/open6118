"""Testes do P34 — Regiões especiais: furos, aberturas e pressão de contato.

Cobre dimensionamento/regioes_especiais_nbr6118.py contra a ABNT
NBR 6118:2026:

  - 21.2.1 (pressão de contato em área reduzida; proporção de lados de
    Ac0), p. 197
  - 21.2.2, Figura 21.2 (articulações de concreto), p. 198
  - 21.3.3, Figura 21.5 (furos que atravessam vigas na direção da altura:
    diâmetro máximo, distância mínima à face, conjunto de furos alinhados,
    seção remanescente), p. 200
  - 21.3.4 a) e b) (seção remanescente e armadura de reforço de abertura
    em laje), p. 201

Os valores esperados vêm da imagem de cada página (SCRATCH\\nbr_png\\pNNN.png),
não do JSON do plano.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr                       # noqa: E402
import vigas_nbr6118 as vig                         # noqa: E402
import cortante_nbr6118 as crt                      # noqa: E402
import lajes_nbr6118 as laj                         # noqa: E402
import ancoragem_nbr6118 as anc                     # noqa: E402
import regioes_especiais_nbr6118 as re              # noqa: E402


FCK = 20.0  # MPa, gama_c padrao 1.4 -> fcd = 20/1.4 = 14.285714... MPa


# =============================================================================
# 21.2.1 — FRd, esmagamento em área reduzida (p. 197)
# =============================================================================
def test_FRd_area_reduzida_Ac1_igual_Ac0():
    """Ac1 = Ac0 -> raiz(Ac1/Ac0) = 1 -> FRd = Ac0*fcd (não bate no teto).

    fcd = 20/1,4 = 14,285714... MPa = 1,4285714... kN/cm2.
    FRd = 400 * 1,4285714... = 571,42857... kN.
    Teto = 3,3*fcd*Ac0 = 3,3*571,42857 = 1885,71... kN > 571,43 -> não governa.
    """
    fcd_kncm2 = (FCK / 1.4) / 10.0
    esperado = 400.0 * fcd_kncm2
    assert re.FRd_area_reduzida(400.0, 400.0, FCK) == pytest.approx(esperado, rel=1e-9)


def test_FRd_area_reduzida_transicao_teto():
    """Transição: raiz(Ac1/Ac0) = 3,3 <-> Ac1/Ac0 = 10,89 -> o teto passa a governar.

    Ac0 = 100 cm2, Ac1 = 1089 cm2 (10,89*100): raiz(10,89) = 3,3 exatamente,
    então valor = Ac0*fcd*3,3 = teto = 3,3*fcd*Ac0 -> as duas expressões
    coincidem neste ponto (o valor exato do limite).
    """
    fcd_kncm2 = (FCK / 1.4) / 10.0
    teto = 3.3 * fcd_kncm2 * 100.0
    assert re.FRd_area_reduzida(100.0, 1089.0, FCK) == pytest.approx(teto, rel=1e-9)


def test_FRd_area_reduzida_acima_da_transicao_satura_no_teto():
    """Ac1/Ac0 = 11 > 10,89: sem o teto, raiz(11)=3,3166 > 3,3 -> valor bruto
    passaria do limite; a função tem de saturar em 3,3*fcd*Ac0."""
    fcd_kncm2 = (FCK / 1.4) / 10.0
    teto = 3.3 * fcd_kncm2 * 100.0
    assert re.FRd_area_reduzida(100.0, 1100.0, FCK) == pytest.approx(teto, rel=1e-9)


def test_FRd_area_reduzida_Ac1_menor_que_Ac0_erro():
    """Ac1 < Ac0 não é geometricamente possível (Ac1 contém Ac0) -> erro."""
    with pytest.raises(nbr.FaixaNormativaError):
        re.FRd_area_reduzida(100.0, 50.0, FCK)


def test_FRd_area_reduzida_com_proporcao_ok_e_ruim():
    """FRd_area_reduzida aplica também o limite de proporção quando os
    lados de Ac0 são informados: 20x40 (razão 2,0) passa; 20x45 (2,25) falha."""
    valor = re.FRd_area_reduzida(
        800.0, 800.0, FCK, lado_maior_cm=40.0, lado_menor_cm=20.0,
    )
    assert valor > 0.0
    with pytest.raises(nbr.FaixaNormativaError):
        re.FRd_area_reduzida(
            900.0, 900.0, FCK, lado_maior_cm=45.0, lado_menor_cm=20.0,
        )


# =============================================================================
# 21.2.1 — Proporção máxima entre lados de Ac0 (p. 197)
# =============================================================================
def test_proporcao_ac0_no_limite_passa():
    """20 cm x 40 cm -> razão = 2,0 (limite exato) -> passa, devolve 2,0."""
    assert re.validar_proporcao_ac0(40.0, 20.0) == pytest.approx(2.0)


def test_proporcao_ac0_acima_do_limite_reprova():
    """20 cm x 45 cm -> razão = 2,25 > 2 -> reprova (FaixaNormativaError)."""
    with pytest.raises(nbr.FaixaNormativaError):
        re.validar_proporcao_ac0(45.0, 20.0)


def test_proporcao_ac0_ordem_dos_lados_nao_importa():
    """A função aceita os lados em qualquer ordem e usa o maior/menor."""
    assert re.validar_proporcao_ac0(20.0, 40.0) == pytest.approx(2.0)


# =============================================================================
# 21.2.2 — Articulações de concreto, Figura 21.2 (p. 198)
# =============================================================================
def test_articulacao_c20_limite_governante_2cm():
    """c = 20 cm -> c/8 = 2,5 cm > 2 cm -> limite governante = 2 cm (o teto
    absoluto). Deslocamento = 2,0 cm (limite exato) e inclinação = 1/8
    (limite exato) -> ok."""
    r = re.verificar_articulacao_concreto(20.0, deslocamento_cm=2.0, inclinacao=0.125)
    assert r.limite_deslocamento_cm == pytest.approx(2.0)
    assert r.ok is True


def test_articulacao_c20_deslocamento_acima_do_limite_falha():
    r = re.verificar_articulacao_concreto(20.0, deslocamento_cm=2.01, inclinacao=0.0)
    assert r.ok_deslocamento is False
    assert r.ok is False


def test_articulacao_c10_limite_governante_c_sobre_8():
    """c = 10 cm -> c/8 = 1,25 cm < 2 cm -> limite governante = 1,25 cm
    (c/8, não o teto absoluto). No limite exato, passa."""
    r = re.verificar_articulacao_concreto(10.0, deslocamento_cm=1.25, inclinacao=0.125)
    assert r.limite_deslocamento_cm == pytest.approx(1.25)
    assert r.ok is True


def test_articulacao_c10_acima_do_limite_e_inclinacao_excessiva_falham():
    r = re.verificar_articulacao_concreto(10.0, deslocamento_cm=1.26, inclinacao=0.126)
    assert r.ok_deslocamento is False
    assert r.ok_inclinacao is False
    assert r.ok is False


def test_articulacao_extensao_volume_fretado_3c():
    r = re.verificar_articulacao_concreto(20.0)
    assert r.extensao_volume_fretado_cm == pytest.approx(60.0)


# =============================================================================
# 21.3.3 — Diâmetro máximo de furo vertical em viga (p. 200)
# =============================================================================
def test_phi_max_furo_viga_bw30():
    """bw = 30 cm -> phi_max = 30/3 = 10 cm."""
    assert re.phi_max_furo_viga(30.0) == pytest.approx(10.0)


def test_phi_max_furo_viga_bw45():
    assert re.phi_max_furo_viga(45.0) == pytest.approx(15.0)


# =============================================================================
# 21.3.3 — Distância mínima do furo à face da viga (p. 200)
# =============================================================================
def test_distancia_min_furo_face_cobrimento_governa():
    """cobrimento = 3 cm -> 2*3 = 6 cm > 5 cm -> dist_min = 6 cm."""
    assert re.distancia_min_furo_face(3.0) == pytest.approx(6.0)


def test_distancia_min_furo_face_absoluta_governa():
    """cobrimento = 2 cm -> 2*2 = 4 cm < 5 cm -> dist_min = 5 cm (absoluto)."""
    assert re.distancia_min_furo_face(2.0) == pytest.approx(5.0)


def test_distancia_min_furo_face_no_limite_exato():
    """cobrimento = 2,5 cm -> 2*2,5 = 5 cm = limite absoluto -> dist_min = 5 cm."""
    assert re.distancia_min_furo_face(2.5) == pytest.approx(5.0)


# =============================================================================
# 21.3.3 — Conjunto de furos alinhados (p. 200)
# =============================================================================
def test_conjunto_furos_phi_governa_distancia():
    """phi_furo = 8 cm > 5 cm -> dist_min entre faces = max(5, 8) = 8 cm."""
    r = re.verificar_conjunto_furos(8.0, [8.0, 10.0], [True, True])
    assert r.dist_min_entre_faces_cm == pytest.approx(8.0)
    assert r.ok is True


def test_conjunto_furos_distancia_insuficiente_falha():
    r = re.verificar_conjunto_furos(8.0, [7.9], [True])
    assert r.ok_distancias is False
    assert r.ok is False


def test_conjunto_furos_sem_estribo_no_intervalo_falha():
    """Distância ok, mas falta estribo no intervalo -> reprova mesmo assim."""
    r = re.verificar_conjunto_furos(8.0, [8.0], [False])
    assert r.ok_distancias is True
    assert r.ok_estribos is False
    assert r.ok is False


def test_conjunto_furos_absoluta_governa_quando_phi_pequeno():
    """phi_furo = 3 cm < 5 cm -> dist_min entre faces = max(5, 3) = 5 cm."""
    r = re.verificar_conjunto_furos(3.0, [5.0], [True])
    assert r.dist_min_entre_faces_cm == pytest.approx(5.0)
    assert r.ok is True


def test_conjunto_furos_tamanhos_incompativeis_erro():
    with pytest.raises(ValueError):
        re.verificar_conjunto_furos(8.0, [8.0, 10.0], [True])


# =============================================================================
# 21.3.3 — Seção remanescente da viga na região do furo (p. 200)
# =============================================================================
def test_secao_remanescente_furo_viga_ok():
    """bw = 30 cm, furo no limite phi = bw/3 = 10 cm -> bw remanescente = 20 cm.

    MRd = vigas_nbr6118.momento_resistente_simples(As=8 cm2, bw=20 cm,
    d=45 cm, fck=25 MPa, fyk=500 MPa) = 13659,51... kN.cm (conferido
    chamando a própria função do P12, já testada em separado — aqui só se
    confere que a seção remanescente usa bw - phi_furo).
    VRd = cortante_nbr6118.simplificada_modelo_I(0, bw=20, d=45,
    fck=25).VRd2 = 390,54... kN.
    Msd = 13 000 kN.cm < MRd e Vsd = 300 kN < VRd -> ok nas duas.
    """
    MRd_esperado, _, _ = vig.momento_resistente_simples(8.0, 20.0, 45.0, 25.0, 500.0)
    VRd_esperado = crt.simplificada_modelo_I(0.0, 20.0, 45.0, 25.0).VRd2

    r = re.secao_remanescente_furo_viga(30.0, 10.0, 45.0, 8.0, 25.0, 13000.0, 300.0)
    assert r.bw_remanescente_cm == pytest.approx(20.0)
    assert r.MRd_kncm == pytest.approx(MRd_esperado, rel=1e-9)
    assert r.VRd_kn == pytest.approx(VRd_esperado, rel=1e-9)
    assert r.ok_flexao is True
    assert r.ok_cortante is True
    assert r.ok is True


def test_secao_remanescente_furo_viga_falha_flexao():
    """Msd = 14 000 kN.cm > MRd = 13 659,5 kN.cm -> reprova em flexão."""
    r = re.secao_remanescente_furo_viga(30.0, 10.0, 45.0, 8.0, 25.0, 14000.0, 300.0)
    assert r.ok_flexao is False
    assert r.ok is False


def test_secao_remanescente_furo_viga_falha_cortante():
    """Vsd = 450 kN > VRd2 = 390,5 kN -> reprova em cortante."""
    r = re.secao_remanescente_furo_viga(30.0, 10.0, 45.0, 8.0, 25.0, 13000.0, 450.0)
    assert r.ok_cortante is False
    assert r.ok is False


def test_secao_remanescente_furo_viga_furo_maior_que_bw_erro():
    """phi_furo >= bw -> seção remanescente nula/negativa -> erro."""
    with pytest.raises(nbr.FaixaNormativaError):
        re.secao_remanescente_furo_viga(10.0, 15.0, 20.0, 2.0, 25.0, 100.0, 10.0)


# =============================================================================
# 21.3.4 a) — Seção remanescente de laje com abertura (p. 201)
# =============================================================================
def test_secao_remanescente_abertura_laje_ok():
    """Faixa de b = 100 cm (1 m) com abertura de 30 cm -> b remanescente = 70 cm.

    MRd = vigas_nbr6118.momento_resistente_simples(As=5 cm2/m, bw=70 cm,
    d=12 cm, fck=25 MPa, fyk=500 MPa) = 2386,30... kN.cm/m.
    Msd = 2000 kN.cm/m < MRd -> ok.
    """
    MRd_esperado, _, _ = vig.momento_resistente_simples(5.0, 70.0, 12.0, 25.0, 500.0)
    r = re.secao_remanescente_abertura_laje(100.0, 30.0, 12.0, 5.0, 25.0, 2000.0)
    assert r.b_remanescente_cm == pytest.approx(70.0)
    assert r.MRd_kncm == pytest.approx(MRd_esperado, rel=1e-9)
    assert r.ok_flexao is True
    assert r.ok is True
    assert r.ok_cortante is None  # VSd_kn não informado -> cortante nao verificado


def test_secao_remanescente_abertura_laje_falha_flexao():
    """Msd = 2500 kN.cm/m > MRd = 2386,3 kN.cm/m -> reprova."""
    r = re.secao_remanescente_abertura_laje(100.0, 30.0, 12.0, 5.0, 25.0, 2500.0)
    assert r.ok_flexao is False
    assert r.ok is False


def test_secao_remanescente_abertura_laje_cortante_ok():
    """Com VSd_kn informado, também verifica VRd1 = lajes_nbr6118
    .cortante_resistente_laje(70, 12, 5, 25) = 57,32... kN. Vsd = 50 kN
    < VRd1 -> ok."""
    VRd_esperado = laj.cortante_resistente_laje(70.0, 12.0, 5.0, 25.0)
    r = re.secao_remanescente_abertura_laje(
        100.0, 30.0, 12.0, 5.0, 25.0, 2000.0, VSd_kn=50.0,
    )
    assert r.VRd_kn == pytest.approx(VRd_esperado, rel=1e-9)
    assert r.ok_cortante is True
    assert r.ok is True


def test_secao_remanescente_abertura_laje_cortante_falha():
    """Vsd = 60 kN > VRd1 = 57,32 kN -> reprova em cortante mesmo com
    flexão ok."""
    r = re.secao_remanescente_abertura_laje(
        100.0, 30.0, 12.0, 5.0, 25.0, 2000.0, VSd_kn=60.0,
    )
    assert r.ok_flexao is True
    assert r.ok_cortante is False
    assert r.ok is False


def test_secao_remanescente_abertura_laje_abertura_maior_que_b_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        re.secao_remanescente_abertura_laje(50.0, 60.0, 12.0, 5.0, 25.0, 100.0)


# =============================================================================
# 21.3.4 b) — Armadura de reforço equivalente (p. 201)
# =============================================================================
def test_As_reforco_abertura_3_barras_10mm():
    """3 barras de 10 mm interrompidas: área de cada = pi/4*1,0^2 =
    0,7853981634 cm2; soma = 3*0,7853981634 = 2,3561944902 cm2 ~= 2,36 cm2,
    como no exemplo do plano."""
    area_barra = math.pi / 4.0 * 1.0 ** 2
    r = re.As_reforco_abertura([area_barra, area_barra, area_barra])
    assert r.As_reforco_cm2 == pytest.approx(2.3561944902, rel=1e-6)
    assert r.As_reforco_cm2 == pytest.approx(2.36, rel=2e-3)
    assert r.ok is True


def test_As_reforco_abertura_com_ancoragem():
    """Com phi_reforco_mm e fck_mpa informados, calcula lb_nec via
    ancoragem_nbr6118.comprimento_ancoragem(phi=10mm, fck=25 MPa,
    fyk=500 MPa, CA-50, boa aderência, sem gancho, As_calc=As_ef=1)."""
    area_barra = math.pi / 4.0 * 1.0 ** 2
    esperado = anc.comprimento_ancoragem(10.0, 25.0, 500.0).lb_nec_cm
    r = re.As_reforco_abertura(
        [area_barra] * 3, phi_reforco_mm=10.0, fck_mpa=25.0,
    )
    assert r.lb_nec_cm == pytest.approx(esperado, rel=1e-9)


def test_As_reforco_abertura_sem_ancoragem_lb_none():
    r = re.As_reforco_abertura([1.0])
    assert r.lb_nec_cm is None


def test_As_reforco_abertura_lista_vazia_erro():
    with pytest.raises(ValueError):
        re.As_reforco_abertura([])


def test_As_reforco_abertura_area_negativa_erro():
    with pytest.raises(ValueError):
        re.As_reforco_abertura([-1.0])
