"""Testes do P35 -- bielas e tirantes (22.3) e vigas-parede (22.4.4).

Valores esperados tirados da NBR 6118:2026 (PDF p. 204-206) e das contas
nos comentarios de cada teste.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import bielas_tirantes_nbr6118 as bt  # noqa: E402
import blocos_nbr6118 as blo  # noqa: E402
import nucleo_nbr6118 as nbr  # noqa: E402
import vigas_parede_nbr6118 as vp  # noqa: E402


# ---------------------------------------------------------------------------
# 22.3.1 -- faixa de inclinacao admissivel das bielas (PDF p. 204)
# ---------------------------------------------------------------------------
def test_inclinacao_biela_dentro_da_faixa():
    # theta = 45 graus -> tan = 1,0, dentro de [0,57; 2,0]
    r = bt.verificar_inclinacao_biela(1.0)
    assert r.ok is True
    assert r.governante == "22.3.1"


def test_inclinacao_biela_limite_inferior_exato():
    r = bt.verificar_inclinacao_biela(0.57)
    assert r.ok is True


def test_inclinacao_biela_abaixo_do_limite_inferior():
    r = bt.verificar_inclinacao_biela(0.56)
    assert r.ok is False


def test_inclinacao_biela_limite_superior_exato():
    # theta = 63,43 graus -> tan(63,43 deg) = 2,0 (limite superior)
    r = bt.verificar_inclinacao_biela(2.0)
    assert r.ok is True


def test_inclinacao_biela_acima_do_limite_superior():
    r = bt.verificar_inclinacao_biela(2.01)
    assert r.ok is False


# ---------------------------------------------------------------------------
# 22.3.2 -- fcd1, fcd2, fcd3 (PDF p. 204)
# ---------------------------------------------------------------------------
def test_fcd2_c25():
    # C25: fcd = 25/1,4 = 17,857 MPa = 1,7857 kN/cm2; alpha_v2 = 1-25/250 = 0,9
    # fcd2 = 0,60*0,9*1,7857 = 0,9643 kN/cm2 = 9,643 MPa
    fcd2 = bt.fcd2_kncm2(25.0)
    assert fcd2 == pytest.approx(0.96428571, abs=1e-6)
    assert fcd2 * 10.0 == pytest.approx(9.6428571, abs=1e-4)


def test_fcd1_fcd3_c25_expressao():
    fcd_kncm2 = nbr.mpa_para_kncm2(nbr.fcd(25.0, 1.4))
    av2 = nbr.alpha_v2(25.0)
    assert bt.fcd1_kncm2(25.0) == pytest.approx(0.85 * av2 * fcd_kncm2)
    assert bt.fcd3_kncm2(25.0) == pytest.approx(0.72 * av2 * fcd_kncm2)


def test_fcd1_fcd3_menor_que_fcd2_relacao_de_ordem():
    # 22.3.2: fcd1 (0,85) > fcd3 (0,72) > fcd2 (0,60) -- mesma base alpha_v2*fcd
    fcd1 = bt.fcd1_kncm2(30.0)
    fcd2 = bt.fcd2_kncm2(30.0)
    fcd3 = bt.fcd3_kncm2(30.0)
    assert fcd1 > fcd3 > fcd2


@pytest.mark.parametrize("fck_mpa", [20.0, 25.0, 40.0, 50.0])
def test_fcd1_fcd3_mesmos_numeros_de_blocos_nbr6118(fck_mpa):
    # Aceite do P35: fcd1 e fcd3 dao os mesmos numeros que blocos_nbr6118
    # (reexportacao fina apos a promocao para bielas_tirantes_nbr6118).
    assert bt.fcd1_kncm2(fck_mpa) == blo.fcd1_no_pilar_kncm2(fck_mpa)
    assert bt.fcd3_kncm2(fck_mpa) == blo.fcd3_na_estaca_kncm2(fck_mpa)


# ---------------------------------------------------------------------------
# 22.3.3 -- area de aco de um tirante generico (PDF p. 204)
# ---------------------------------------------------------------------------
def test_as_tirante_ca50():
    # FSd = 500 kN, CA-50: fyd = 500/1,15 = 434,78 MPa = 43,478 kN/cm2
    # As = 500 / 43,478 = 11,5 cm2
    fyd_kncm2 = nbr.mpa_para_kncm2(nbr.fyd(500.0, 1.15))
    As = bt.As_tirante_cm2(FSd_kn=500.0, fyd_kncm2=fyd_kncm2)
    assert As == pytest.approx(11.5, abs=1e-3)


def test_as_tirante_fyd_nao_positivo_levanta():
    with pytest.raises(nbr.FaixaNormativaError):
        bt.As_tirante_cm2(FSd_kn=500.0, fyd_kncm2=0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        bt.As_tirante_cm2(FSd_kn=500.0, fyd_kncm2=-1.0)


# ---------------------------------------------------------------------------
# 22.3.2 -- verificar_no (fachada sobre fcd1/fcd2/fcd3)
# ---------------------------------------------------------------------------
def test_verificar_no_ccc_usa_fcd1():
    fcd1 = bt.fcd1_kncm2(25.0)
    r_ok = bt.verificar_no("CCC", sigma_kncm2=fcd1 - 0.01, fck_mpa=25.0)
    r_falha = bt.verificar_no("ccc", sigma_kncm2=fcd1 + 0.01, fck_mpa=25.0)
    assert r_ok.fcd_no_kncm2 == pytest.approx(fcd1)
    assert r_ok.ok is True
    assert r_falha.ok is False


def test_verificar_no_cct_usa_fcd3():
    fcd3 = bt.fcd3_kncm2(25.0)
    r = bt.verificar_no("CCT", sigma_kncm2=fcd3, fck_mpa=25.0)
    assert r.fcd_no_kncm2 == pytest.approx(fcd3)
    assert r.ok is True


@pytest.mark.parametrize("tipo", ["CTT", "TTT"])
def test_verificar_no_ctt_ttt_usam_fcd2(tipo):
    fcd2 = bt.fcd2_kncm2(25.0)
    r = bt.verificar_no(tipo, sigma_kncm2=fcd2, fck_mpa=25.0)
    assert r.fcd_no_kncm2 == pytest.approx(fcd2)
    assert r.ok is True


def test_verificar_no_tipo_desconhecido_levanta():
    with pytest.raises(ValueError):
        bt.verificar_no("XYZ", sigma_kncm2=1.0, fck_mpa=25.0)


# ---------------------------------------------------------------------------
# 22.4.4.1 -- distribuicao da armadura negativa em viga-parede continua
# (PDF p. 205)
# ---------------------------------------------------------------------------
def test_repartir_As_negativa_l_h_igual_1():
    # l/h = 1 (fronteira): As1 = (0,5-0,5)*As = 0; As2 = (1,5-0,5)*As = As; As3 = 0
    As1, As2, As3 = vp.repartir_As_negativa(As_cm2=10.0, l_h=1.0)
    assert As1 == pytest.approx(0.0)
    assert As2 == pytest.approx(10.0)
    assert As3 == pytest.approx(0.0)
    assert As1 + As2 + As3 == pytest.approx(10.0)


def test_repartir_As_negativa_l_h_igual_3():
    # l/h = 3 (fronteira): As1 = (1,5-0,5)*As = As; As2 = (1,5-1,5)*As = 0; As3 = 0
    As1, As2, As3 = vp.repartir_As_negativa(As_cm2=10.0, l_h=3.0)
    assert As1 == pytest.approx(10.0)
    assert As2 == pytest.approx(0.0)
    assert As3 == pytest.approx(0.0)
    assert As1 + As2 + As3 == pytest.approx(10.0)


def test_repartir_As_negativa_l_h_igual_2_ponto_interior():
    # l/h = 2: As1 = (1,0-0,5)*As = 0,5*As; As2 = (1,5-1,0)*As = 0,5*As; As3 = 0
    As1, As2, As3 = vp.repartir_As_negativa(As_cm2=8.0, l_h=2.0)
    assert As1 == pytest.approx(4.0)
    assert As2 == pytest.approx(4.0)
    assert As3 == pytest.approx(0.0)


@pytest.mark.parametrize("l_h", [0.99, 3.01])
def test_repartir_As_negativa_fora_da_faixa_levanta(l_h):
    with pytest.raises(nbr.FaixaNormativaError):
        vp.repartir_As_negativa(As_cm2=10.0, l_h=l_h)


# ---------------------------------------------------------------------------
# 22.4.4.1 e 22.4.4.3 -- armadura minima horizontal e vertical (PDF p. 205-206)
# ---------------------------------------------------------------------------
def test_as_horizontal_min_b_20():
    # b = 20 cm: As,h,min = 0,00075*20*100 = 1,5 cm2/m por face
    assert vp.As_horizontal_min_cm2_por_m(20.0) == pytest.approx(1.5)


def test_as_vertical_min_b_20_mesmo_valor_da_horizontal():
    # 22.4.4.3: mesma taxa de 22.4.4.1 -> mesmo valor numerico
    assert vp.As_vertical_min_cm2_por_m(20.0) == pytest.approx(1.5)
    assert vp.As_vertical_min_cm2_por_m(20.0) == vp.As_horizontal_min_cm2_por_m(20.0)


@pytest.mark.parametrize("b_cm", [0.0, -5.0])
def test_as_min_b_nao_positivo_levanta(b_cm):
    with pytest.raises(ValueError):
        vp.As_horizontal_min_cm2_por_m(b_cm)
    with pytest.raises(ValueError):
        vp.As_vertical_min_cm2_por_m(b_cm)


# ---------------------------------------------------------------------------
# 22.4.4.3 -- suspensao da carga aplicada pela face inferior (PDF p. 206)
# ---------------------------------------------------------------------------
def test_suspensao_carga_inferior_mesma_relacao_de_tirante():
    # A norma nao da formula fechada (conferido_na_imagem=False no item);
    # este modulo usa As = F/fyd (22.3.3). F=500 kN, CA-50 -> As=11,5 cm2,
    # igual ao teste do tirante generico.
    fyd_kncm2 = nbr.mpa_para_kncm2(nbr.fyd(500.0, 1.15))
    As = vp.suspensao_carga_inferior(F_kn=500.0, fyd_kncm2=fyd_kncm2)
    assert As == pytest.approx(11.5, abs=1e-3)
    assert As == pytest.approx(bt.As_tirante_cm2(500.0, fyd_kncm2))


def test_verificar_suspensao_carga_inferior_ok_e_reprovado():
    fyd_kncm2 = nbr.mpa_para_kncm2(nbr.fyd(500.0, 1.15))  # 43,478 kN/cm2
    r_ok = vp.verificar_suspensao_carga_inferior(
        F_kn=500.0, fyd_kncm2=fyd_kncm2, As_vertical_disponivel_cm2=12.0,
    )
    r_falha = vp.verificar_suspensao_carga_inferior(
        F_kn=500.0, fyd_kncm2=fyd_kncm2, As_vertical_disponivel_cm2=10.0,
    )
    assert r_ok.As_susp_cm2 == pytest.approx(11.5, abs=1e-3)
    assert r_ok.ok is True
    assert r_falha.ok is False
    assert r_ok.governante == "22.4.4.3"


def test_verificar_suspensao_carga_inferior_sem_as_disponivel():
    fyd_kncm2 = nbr.mpa_para_kncm2(nbr.fyd(500.0, 1.15))
    r = vp.verificar_suspensao_carga_inferior(F_kn=500.0, fyd_kncm2=fyd_kncm2)
    assert r.ok is True
    assert r.As_susp_cm2 == pytest.approx(11.5, abs=1e-3)


# ---------------------------------------------------------------------------
# Verificação (volta 1) -- texto ao usuário (memória de cálculo) com
# acentuação e pontuação corretas, conforme a convenção do plano (secao 3.3,
# item 5). Falhavam antes da correção, quando a memória saía em ASCII puro
# ("faixa admissivel", "inclinacao... nao admissivel", "nao informada",
# "area necessaria", "formula fechada", "relacao generica").
# ---------------------------------------------------------------------------
def test_memoria_inclinacao_biela_admissivel_tem_acentuacao():
    r = bt.verificar_inclinacao_biela(1.0)
    texto = " ".join(r.memoria)
    assert "faixa admissível" in texto
    assert "inclinação admissível" in texto
    # nao deve sobrar a forma sem acento que a verificacao independente achou
    assert "admissivel" not in texto
    assert "inclinacao" not in texto


def test_memoria_inclinacao_biela_nao_admissivel_tem_acentuacao():
    r = bt.verificar_inclinacao_biela(2.5)
    texto = " ".join(r.memoria)
    assert "inclinação da biela não admissível" in texto
    assert "admissivel" not in texto
    assert "inclinacao" not in texto


def test_memoria_suspensao_carga_inferior_tem_acentuacao():
    fyd_kncm2 = nbr.mpa_para_kncm2(nbr.fyd(500.0, 1.15))
    r_sem = vp.verificar_suspensao_carga_inferior(F_kn=500.0, fyd_kncm2=fyd_kncm2)
    texto_sem = " ".join(r_sem.memoria)
    assert "não informada" in texto_sem
    assert "só a área necessária" in texto_sem
    assert "fórmula fechada" in texto_sem
    assert "relação genérica" in texto_sem
    # nenhuma das formas sem acento que a verificacao independente achou
    for forma_ascii in (
        "nao informada", "area necessaria", "formula fechada",
        "relacao generica",
    ):
        assert forma_ascii not in texto_sem

    r_com = vp.verificar_suspensao_carga_inferior(
        F_kn=500.0, fyd_kncm2=fyd_kncm2, As_vertical_disponivel_cm2=10.0,
    )
    texto_com = " ".join(r_com.memoria)
    assert "As,necessária" in texto_com
    assert "As,necessaria" not in texto_com
