"""Testes do P24 -- Detalhamento de pilares (NBR 6118:2026, Seção 18.4.2 e
18.4.3).

Valores esperados tirados da imagem da página do PDF (SCRATCH/nbr_png):
p173 (18.4.2.1 diâmetro; 18.4.2.2 distribuição transversal e espaçamento
mínimo), p174 (18.4.2.2 espaçamento máximo entre eixos; 18.4.3 armaduras
transversais, com a fórmula de φt reduzido e a NOTA de dutilidade). As
contas à mão estão nos comentários de cada teste.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import durabilidade_nbr6118 as dur  # noqa: E402
import detalhamento_pilares_nbr6118 as DP  # noqa: E402


# ===========================================================================
# núcleo: phi_n_feixe (9.4.2) -- promovido do P24, também usado por P22/P27
# ===========================================================================
def test_nucleo_phi_n_feixe_formula():
    """phi=20mm, n=3: phi_n = 20*sqrt(3) = 34.6410... mm (9.4.2)."""
    assert nbr.phi_n_feixe(20.0, 3) == pytest.approx(20.0 * 3 ** 0.5)
    assert nbr.phi_n_feixe(20.0, 3) == pytest.approx(34.64, abs=0.01)


def test_nucleo_phi_n_feixe_exige_pelo_menos_2_barras():
    with pytest.raises(ValueError):
        nbr.phi_n_feixe(20.0, 1)


def test_durabilidade_phi_feixe_mm_agora_e_fachada_do_nucleo():
    """durabilidade_nbr6118.phi_feixe_mm foi promovida (P24): mesma conta."""
    assert dur.phi_feixe_mm(20.0, 3) == nbr.phi_n_feixe(20.0, 3)


# ===========================================================================
# 18.4.2.1 -- Diâmetro mínimo e máximo da barra longitudinal (PDF p. 173)
# ===========================================================================
def test_1842_1_phi_min_e_max_menor_dimensao_20cm():
    """b_min=20cm -> phi_max=200mm/8=25mm (do enunciado do pacote)."""
    phi_min, phi_max = DP.phi_longitudinal_limites_mm(20.0)
    assert phi_min == pytest.approx(10.0)
    assert phi_max == pytest.approx(25.0)


def test_1842_1_phi_8mm_sempre_reprovado():
    """phi=8mm < 10mm: reprovado mesmo com pilar grande (b_min=100cm -> phi_max=125mm)."""
    phi_min, phi_max = DP.phi_longitudinal_limites_mm(100.0)
    assert not (phi_min <= 8.0 <= phi_max)


def test_1842_1_bordas_da_faixa():
    """b_min=8cm -> phi_max = 80mm/8=10mm: coincide com phi_min (caso-limite)."""
    phi_min, phi_max = DP.phi_longitudinal_limites_mm(8.0)
    assert phi_min == pytest.approx(10.0)
    assert phi_max == pytest.approx(10.0)


def test_1842_1_ponto_interior():
    """b_min=40cm -> phi_max = 400mm/8 = 50mm."""
    _, phi_max = DP.phi_longitudinal_limites_mm(40.0)
    assert phi_max == pytest.approx(50.0)


def test_1842_1_b_min_invalido():
    with pytest.raises(ValueError):
        DP.phi_longitudinal_limites_mm(0.0)


# ===========================================================================
# 18.4.2.2 -- Número mínimo de barras por geometria (PDF p. 173)
# ===========================================================================
def test_1842_2_pilar_retangular_minimo_4_barras():
    assert DP.n_min_barras("retangular") == 4
    assert DP.n_min_barras(4) == 4  # número de vértices direto


def test_1842_2_pilar_circular_minimo_6_barras():
    assert DP.n_min_barras("circular") == 6


def test_1842_2_pilar_triangular_minimo_3_barras():
    assert DP.n_min_barras("triangular") == 3
    assert DP.n_min_barras(3) == 3


def test_1842_2_forma_invalida_levanta_erro():
    with pytest.raises(ValueError):
        DP.n_min_barras("nonagonal")
    with pytest.raises(ValueError):
        DP.n_min_barras(2)  # polígono precisa de >= 3 vértices


# ===========================================================================
# 18.4.2.2 -- Espaçamento mínimo livre entre barras longitudinais (PDF p. 173)
# ===========================================================================
def test_1842_2_espacamento_min_governado_pelo_dmax():
    """phi=25mm, dmax=19mm: max(20; 25; 1,2*19=22,8) = 25mm = 2,5cm."""
    esp = DP.espacamento_min_livre_cm(25.0, dmax_agregado_mm=19.0)
    assert esp == pytest.approx(2.5)


def test_1842_2_espacamento_min_governado_pelo_absoluto_20mm():
    """phi=15mm, dmax=10mm: max(20; 15; 1,2*10=12) = 20mm = 2,0cm."""
    esp = DP.espacamento_min_livre_cm(15.0, dmax_agregado_mm=10.0)
    assert esp == pytest.approx(2.0)


def test_1842_2_espacamento_min_governado_pelo_dmax_no_limite():
    """phi=20mm, dmax=20mm: 1,2*20=24mm > 20mm e > phi -> 24mm = 2,4cm (ponto interior)."""
    esp = DP.espacamento_min_livre_cm(20.0, dmax_agregado_mm=20.0)
    assert esp == pytest.approx(2.4)


def test_1842_2_espacamento_min_considera_feixe():
    """phi=10mm da barra isolada, mas feixe com phi_n=34,64mm (3 barras de 20mm)
    governa: max(20; 10; 34,64; 1,2*19=22,8) = 34,64mm."""
    phi_n = nbr.phi_n_feixe(20.0, 3)
    esp = DP.espacamento_min_livre_cm(10.0, phi_n_mm=phi_n, dmax_agregado_mm=19.0)
    assert esp == pytest.approx(phi_n / 10.0)


# ===========================================================================
# 18.4.2.2 -- Espaçamento máximo entre eixos das barras (PDF p. 174)
# ===========================================================================
def test_1842_2_espacamento_max_eixos_governado_pelo_absoluto_400mm():
    """b_min=25cm: min(2*25=50cm; 40cm) = 40cm (do enunciado do pacote)."""
    assert DP.espacamento_max_eixos_cm(25.0) == pytest.approx(40.0)


def test_1842_2_espacamento_max_eixos_governado_por_2x_b_min():
    """b_min=15cm: min(2*15=30cm; 40cm) = 30cm (do enunciado do pacote)."""
    assert DP.espacamento_max_eixos_cm(15.0) == pytest.approx(30.0)


def test_1842_2_espacamento_max_eixos_fronteira_exata():
    """b_min=20cm: 2*20=40cm == 400mm -> os dois lados do degrau coincidem."""
    assert DP.espacamento_max_eixos_cm(20.0) == pytest.approx(40.0)


# ===========================================================================
# 18.4.3 -- Diâmetro mínimo do estribo de pilar (PDF p. 174)
# ===========================================================================
def test_1843_phi_estribo_min_governado_pelo_absoluto_5mm():
    """phi_long=20mm: max(5; 20/4=5) = 5mm (do enunciado do pacote)."""
    assert DP.phi_min_estribo_pilar_mm(20.0) == pytest.approx(5.0)


def test_1843_phi_estribo_min_governado_por_phi_sobre_4():
    """phi_long=32mm: max(5; 32/4=8) = 8mm (do enunciado do pacote)."""
    assert DP.phi_min_estribo_pilar_mm(32.0) == pytest.approx(8.0)


def test_1843_phi_estribo_min_fronteira_exata():
    """phi_long=20mm é a fronteira exata onde phi/4 == 5mm (ver teste acima)."""
    assert DP.phi_min_estribo_pilar_mm(20.0) == pytest.approx(5.0)


# ===========================================================================
# 18.4.3 -- Espaçamento máximo básico entre estribos (PDF p. 174)
# ===========================================================================
def test_1843_s_max_basico_governado_pelo_absoluto_200mm_ca50():
    """CA-50, phi_long=20mm, b_min=25cm: min(20; 25; 12*20mm/10=24) = 20cm (200mm)."""
    s = DP.s_max_estribo_pilar_basico_cm(25.0, 20.0, "CA-50")
    assert s == pytest.approx(20.0)


def test_1843_s_max_basico_ca50_outro_ponto_ainda_governado_pelo_absoluto():
    """CA-50, phi_long=25mm, b_min=25cm: min(20; 25; 12*25mm/10=30) = 20cm (200mm)."""
    s = DP.s_max_estribo_pilar_basico_cm(25.0, 25.0, "CA-50")
    assert s == pytest.approx(20.0)


def test_1843_s_max_basico_governado_por_12phi_ca50():
    """CA-50, phi_long=10mm, b_min=25cm: min(20; 25; 12*10mm/10=12) = 12cm."""
    s = DP.s_max_estribo_pilar_basico_cm(25.0, 10.0, "CA-50")
    assert s == pytest.approx(12.0)


def test_1843_s_max_basico_governado_pela_menor_dimensao():
    """CA-50, phi_long=8mm, b_min=9cm: 12*8mm/10=9,6cm; min(20; 9; 9,6) = 9cm."""
    s = DP.s_max_estribo_pilar_basico_cm(9.0, 8.0, "CA-50")
    assert s == pytest.approx(9.0)


def test_1843_s_max_basico_fator_24_para_ca25():
    """CA-25, phi_long=10mm, b_min=25cm: 24*10mm/10=24cm; min(20; 25; 24) = 20cm."""
    s = DP.s_max_estribo_pilar_basico_cm(25.0, 10.0, "CA-25")
    assert s == pytest.approx(20.0)


def test_1843_s_max_basico_fator_24_ca25_governando():
    """CA-25, phi_long=5mm, b_min=25cm: 24*5mm/10=12cm; min(20; 25; 12) = 12cm."""
    s = DP.s_max_estribo_pilar_basico_cm(25.0, 5.0, "CA-25")
    assert s == pytest.approx(12.0)


def test_1843_s_max_basico_categoria_nao_definida_levanta_erro():
    """A norma só dá o fator 24phi/12phi para CA-25 e CA-50 (célula não definida)."""
    with pytest.raises(nbr.FaixaNormativaError):
        DP.s_max_estribo_pilar_basico_cm(25.0, 20.0, "CA-60")


# ===========================================================================
# 18.4.3 -- Limite adicional com φt < φ/4, fórmula com fyk (PDF p. 174)
# ===========================================================================
def test_1843_phi_reduzido_conta_a_mao():
    """phi_t=5mm, phi_long=25mm (phi_t=5 < 25/4=6,25, admissível), fyk=500MPa:
    smax = 90000*(5^2/25)*(1/500) = 90000*(25/25)/500 = 90000/500 = 180mm."""
    s_mm = DP.s_max_estribo_pilar_phi_reduzido_mm(5.0, 25.0, 500.0)
    assert s_mm == pytest.approx(180.0)


def test_1843_phi_reduzido_fronteira_phi_t_igual_phi_sobre_4_reprovado():
    """phi_t=phi/4 exatamente não satisfaz 'phi_t < phi/4': levanta erro."""
    with pytest.raises(nbr.FaixaNormativaError):
        DP.s_max_estribo_pilar_phi_reduzido_mm(6.25, 25.0, 500.0)


def test_1843_phi_reduzido_phi_t_maior_que_phi_sobre_4_reprovado():
    with pytest.raises(nbr.FaixaNormativaError):
        DP.s_max_estribo_pilar_phi_reduzido_mm(10.0, 25.0, 500.0)


def test_1843_phi_reduzido_ponto_interior_fyk_diferente():
    """phi_t=6mm, phi_long=32mm (6 < 8, admissível), fyk=600MPa:
    smax = 90000*(6^2/32)*(1/600) = 90000*(36/32)/600 = 90000*1.125/600 = 168.75mm."""
    s_mm = DP.s_max_estribo_pilar_phi_reduzido_mm(6.0, 32.0, 600.0)
    assert s_mm == pytest.approx(168.75)


# ===========================================================================
# 18.4.3 NOTA -- redução de 50% para C55 a C90 (dutilidade) (PDF p. 174)
# ===========================================================================
def test_1843_nota_reducao_dentro_da_faixa_c55_c90():
    """fck=60MPa: s_max_recomendado = 0,5*s_max."""
    assert DP.s_max_estribo_pilar_reduzido_dutilidade_cm(20.0, 60.0) == pytest.approx(10.0)


def test_1843_nota_sem_reducao_fora_da_faixa():
    """fck=40MPa: sem redução."""
    assert DP.s_max_estribo_pilar_reduzido_dutilidade_cm(20.0, 40.0) == pytest.approx(20.0)


def test_1843_nota_fronteiras_exatas_55_e_90():
    assert DP.s_max_estribo_pilar_reduzido_dutilidade_cm(20.0, 55.0) == pytest.approx(10.0)
    assert DP.s_max_estribo_pilar_reduzido_dutilidade_cm(20.0, 90.0) == pytest.approx(10.0)
    # logo abaixo/acima da faixa: sem redução
    assert DP.s_max_estribo_pilar_reduzido_dutilidade_cm(20.0, 54.9) == pytest.approx(20.0)


def test_1843_nota_fck_fora_da_faixa_da_norma_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        DP.s_max_estribo_pilar_reduzido_dutilidade_cm(20.0, 10.0)


# ===========================================================================
# 18.4.3 -- s_max_estribo_pilar_cm: combinação dos três critérios
# ===========================================================================
def test_s_max_estribo_combinado_so_basico():
    """Sem phi_t/fyk/fck: só o critério básico vale."""
    s = DP.s_max_estribo_pilar_cm(25.0, 20.0, "CA-50")
    assert s == pytest.approx(DP.s_max_estribo_pilar_basico_cm(25.0, 20.0, "CA-50"))


def test_s_max_estribo_combinado_phi_reduzido_prevalece():
    """b_min grande (não governa), phi_long=25mm CA-50 (basico=min(20;100;30)=20cm);
    phi_t=5mm < 25/4 -> reduzido = 180mm = 18cm < 20cm -> prevalece o reduzido."""
    s = DP.s_max_estribo_pilar_cm(100.0, 25.0, "CA-50", phi_t_mm=5.0, fyk_mpa=500.0)
    assert s == pytest.approx(18.0)


def test_s_max_estribo_combinado_phi_t_nao_admissivel_ignora_reduzido():
    """phi_t=10mm >= 25/4=6,25: o critério reduzido não se aplica, prevalece o básico."""
    s = DP.s_max_estribo_pilar_cm(100.0, 25.0, "CA-50", phi_t_mm=10.0, fyk_mpa=500.0)
    assert s == pytest.approx(DP.s_max_estribo_pilar_basico_cm(100.0, 25.0, "CA-50"))


def test_s_max_estribo_combinado_com_reducao_de_dutilidade():
    """Básico=20cm (CA-50, phi=20mm, b_min=25cm); fck=60 (C55-C90) -> reduz para 10cm."""
    s = DP.s_max_estribo_pilar_cm(25.0, 20.0, "CA-50", fck_mpa=60.0)
    assert s == pytest.approx(10.0)


def test_s_max_estribo_combinado_reducao_aplica_apos_o_menor_criterio():
    """phi_t admissivel reduz para 18cm; fck=60 reduz mais 50%: 9cm."""
    s = DP.s_max_estribo_pilar_cm(100.0, 25.0, "CA-50", phi_t_mm=5.0, fyk_mpa=500.0, fck_mpa=60.0)
    assert s == pytest.approx(9.0)


# ===========================================================================
# verificar_detalhamento_pilar -- verificação conjunta
# ===========================================================================
def test_verificar_detalhamento_pilar_tudo_ok():
    r = DP.verificar_detalhamento_pilar(
        b_min_cm=25.0, forma="retangular", n_barras=8, phi_long_mm=16.0,
        phi_estribo_mm=6.3, aco_longitudinal="CA-50",
        espacamento_livre_real_cm=5.0, espacamento_eixos_real_cm=15.0,
        s_estribo_real_cm=15.0,
    )
    assert r.ok is True
    assert r.governante.startswith("nenhum")
    assert r.phi_long_min_mm == pytest.approx(10.0)
    assert r.phi_long_max_mm == pytest.approx(31.25)  # 250mm/8
    assert r.n_min_barras == 4
    assert r.s_estribo_max_cm == pytest.approx(19.2)  # min(20; 25; 12*16/10=19,2) = 19,2
    assert len(r.memoria) > 0


def test_verificar_detalhamento_pilar_reprova_diametro_longitudinal_pequeno():
    r = DP.verificar_detalhamento_pilar(
        b_min_cm=25.0, forma="retangular", n_barras=8, phi_long_mm=8.0,
        phi_estribo_mm=6.3,
    )
    assert r.ok is False
    assert "18.4.2.1" in r.governante


def test_verificar_detalhamento_pilar_reprova_numero_de_barras():
    r = DP.verificar_detalhamento_pilar(
        b_min_cm=25.0, forma="retangular", n_barras=3, phi_long_mm=16.0,
        phi_estribo_mm=6.3,
    )
    assert r.ok is False
    assert "18.4.2.2" in r.governante


def test_verificar_detalhamento_pilar_reprova_estribo_fino_demais():
    """phi_long=32mm -> phi_estribo_min=8mm; phi_estribo=5mm reprova."""
    r = DP.verificar_detalhamento_pilar(
        b_min_cm=30.0, forma="retangular", n_barras=8, phi_long_mm=32.0,
        phi_estribo_mm=5.0,
    )
    assert r.ok is False
    assert "18.4.3" in r.governante


def test_verificar_detalhamento_pilar_com_feixe_usa_phi_n_nos_limites():
    """3 barras de 16mm em feixe -> phi_n = 16*sqrt(3) = 27,71mm; phi_estribo_min
    = max(5; 27,71/4=6,93) = 6,93mm."""
    r = DP.verificar_detalhamento_pilar(
        b_min_cm=40.0, forma="retangular", n_barras=8, phi_long_mm=16.0,
        phi_estribo_mm=6.3, n_barras_feixe=3,
    )
    phi_n_esperado = nbr.phi_n_feixe(16.0, 3)
    assert r.phi_n_feixe_mm == pytest.approx(phi_n_esperado)
    assert r.phi_estribo_min_mm == pytest.approx(max(5.0, phi_n_esperado / 4.0))
    assert r.ok is False  # 6.3mm < 6.93mm


def test_verificar_detalhamento_pilar_espacamento_eixos_reprovado():
    r = DP.verificar_detalhamento_pilar(
        b_min_cm=15.0, forma="retangular", n_barras=8, phi_long_mm=16.0,
        phi_estribo_mm=6.3, espacamento_eixos_real_cm=35.0,
    )
    assert r.ok is False
    assert "espaçamento máximo entre eixos" in r.governante


def test_verificar_detalhamento_pilar_circular():
    r = DP.verificar_detalhamento_pilar(
        b_min_cm=40.0, forma="circular", n_barras=6, phi_long_mm=16.0,
        phi_estribo_mm=6.3,
    )
    assert r.n_min_barras == 6
    assert r.ok is True
