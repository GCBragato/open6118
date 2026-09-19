"""Testes do P21 -- Ancoragem passiva, ganchos e estribos (NBR 6118:2026,
Seção 9.3.1, 9.3.2.3, 9.4.1.1, 9.4.2.1, 9.4.2.2, 9.4.2.3, 9.4.2.6, 9.4.6).

Valores esperados tirados das imagens das páginas do PDF (SCRATCH/nbr_png):
p053 (9.3.1), p054 (9.3.2.1-9.3.2.3), p055-p056 (9.4.1, 9.4.2.1 a 9.4.2.3,
Tabela 9.1, Figura 9.1), p056-p057 (solda antes/depois do dobramento do
gancho), p057-p058 (9.4.2.4 a 9.4.2.6.2), p060-p061 (9.4.6, Tabela 9.2,
Figuras 9.2 e 9.3). As contas à mão estão nos comentários.
"""

import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import ancoragem_nbr6118 as A  # noqa: E402


# ===========================================================================
# 9.3.1 -- Posição da barra durante a concretagem (PDF p. 53)
# ===========================================================================
def test_931_inclinacao_maior_45_e_sempre_boa():
    """a) inclinação > 45 graus -> boa, independente de h e y."""
    assert A.situacao_aderencia(45.1, h_cm=200.0, y_cm=999.0) is True
    assert A.situacao_aderencia(90.0, h_cm=10.0, y_cm=0.0) is True


def test_931_h_menor_60_boa_ate_30cm_acima_da_face_inferior():
    """b), h < 60 cm: boa até 30 cm acima da face inferior/junta."""
    assert A.situacao_aderencia(0.0, h_cm=40.0, y_cm=20.0) is True
    assert A.situacao_aderencia(0.0, h_cm=40.0, y_cm=30.0) is True   # fronteira
    assert A.situacao_aderencia(0.0, h_cm=40.0, y_cm=35.0) is False


def test_931_inclinacao_45_exata_cai_no_caso_b():
    """45 graus exatos não satisfaz 'maior que 45', então usa o critério b)."""
    assert A.situacao_aderencia(45.0, h_cm=40.0, y_cm=20.0) is True
    assert A.situacao_aderencia(45.0, h_cm=40.0, y_cm=35.0) is False


def test_931_h_maior_igual_60_boa_a_partir_de_30cm_abaixo_da_face_superior():
    """b), h >= 60 cm: boa a partir de 30 cm abaixo da face superior/junta."""
    assert A.situacao_aderencia(0.0, h_cm=80.0, y_cm=25.0) is False  # precisa >= 30
    assert A.situacao_aderencia(0.0, h_cm=80.0, y_cm=30.0) is True   # fronteira
    assert A.situacao_aderencia(0.0, h_cm=80.0, y_cm=40.0) is True
    assert A.situacao_aderencia(0.0, h_cm=60.0, y_cm=30.0) is True   # h=60 usa a regra >=60


def test_931_forma_deslizante_e_sempre_ma():
    """Fôrmas deslizantes são sempre má aderência, mesmo com inclinação > 45."""
    assert A.situacao_aderencia(90.0, h_cm=40.0, y_cm=10.0, forma_deslizante=True) is False


# ===========================================================================
# 9.3.2.3 -- Majoração de 1,75 para escorregamento (PDF p. 54)
# ===========================================================================
def test_9323_fator_escorregamento_e_1_75():
    assert A.FATOR_ESCORREGAMENTO == 1.75


def test_9323_fbd_escorregamento_multiplica_fbd_por_1_75():
    fctd = nbr.fctd(25.0)
    fbd = A.fbd_mpa(25.0, "CA-50", True, 16.0)
    assert A.fbd_escorregamento(fbd) == pytest.approx(1.75 * fbd)


def test_9323_fbd_escorregamento_serve_tambem_para_fbpd():
    """9.3.2.3 diz 'os valores dados em 9.3.2.1 e 9.3.2.2' -- vale para fbpd."""
    fbpd = nbr.fbpd(25.0, "cordoalha", True)
    assert A.fbd_escorregamento(fbpd) == pytest.approx(1.75 * fbpd)


# ===========================================================================
# 9.4.1.1 -- Ancoragem por aderência: dispensa de confinamento (PDF p. 55)
# ===========================================================================
def test_9411_dispensa_confinamento_cobrimento_e_espacamento_maiores_3phi():
    # phi=10mm -> limite = 3 cm
    assert A.dispensa_confinamento(cobrimento_cm=3.0, espacamento_cm=3.0, phi_mm=10.0) is True
    assert A.dispensa_confinamento(cobrimento_cm=2.9, espacamento_cm=5.0, phi_mm=10.0) is False
    assert A.dispensa_confinamento(cobrimento_cm=5.0, espacamento_cm=2.9, phi_mm=10.0) is False


# ===========================================================================
# 9.4.2.1 -- Condições de ancoragem reta, com ou sem gancho (PDF p. 55)
# ===========================================================================
def test_9421_barra_lisa_sem_gancho_levanta_erro():
    with pytest.raises(ValueError):
        A.validar_uso_gancho("lisa", "tracao", 10.0, com_gancho=False)


def test_9421_barra_lisa_com_gancho_e_permitido():
    A.validar_uso_gancho("lisa", "tracao", 10.0, com_gancho=True)  # não levanta


def test_9421_solicitacao_alternada_com_gancho_levanta_erro():
    with pytest.raises(ValueError):
        A.validar_uso_gancho("nervurada", "alternada", 16.0, com_gancho=True)


def test_9421_solicitacao_alternada_sem_gancho_e_permitido():
    A.validar_uso_gancho("nervurada", "alternada", 16.0, com_gancho=False)


def test_9421_barra_comprimida_com_gancho_levanta_erro():
    with pytest.raises(ValueError):
        A.validar_uso_gancho("nervurada", "compressao", 16.0, com_gancho=True)


def test_9421_barra_comprimida_sem_gancho_e_permitido():
    A.validar_uso_gancho("nervurada", "compressao", 16.0, com_gancho=False)


def test_9421_gancho_com_phi_maior_32_emite_aviso_mas_nao_bloqueia():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        A.validar_uso_gancho("nervurada", "tracao", 40.0, com_gancho=True)
        assert any(issubclass(x.category, nbr.AvisoNBR6118) for x in w)


def test_9421_gancho_em_feixe_emite_aviso_mas_nao_bloqueia():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        A.validar_uso_gancho("nervurada", "tracao", 16.0, com_gancho=True, em_feixe=True)
        assert any(issubclass(x.category, nbr.AvisoNBR6118) for x in w)


def test_9421_demais_casos_com_ou_sem_gancho_nao_levanta_nada():
    A.validar_uso_gancho("nervurada", "tracao", 16.0, com_gancho=True)
    A.validar_uso_gancho("nervurada", "tracao", 16.0, com_gancho=False)


# ===========================================================================
# 9.4.2.2 -- Barras transversais soldadas na ancoragem (PDF p. 55-56)
# ===========================================================================
def test_9422_phi_t_05_phi_reprova():
    """phi_t = 0,5*phi deve reprovar (norma exige >= 0,60*phi)."""
    r = A.verificar_barra_transversal_soldada(
        phi_mm=20.0, phi_t_mm=10.0, distancia_cm=10.0,
        forca_solda_kn=1000.0, As_cm2=3.0, fyd_mpa=434.78,
    )
    assert r.ok_diametro is False
    assert r.ok is False


def test_9422_phi_t_06_phi_passa_no_diametro():
    """phi_t = 0,60*phi deve passar nessa condição (fronteira)."""
    r = A.verificar_barra_transversal_soldada(
        phi_mm=20.0, phi_t_mm=12.0, distancia_cm=10.0,
        forca_solda_kn=1000.0, As_cm2=3.0, fyd_mpa=434.78,
    )
    assert r.ok_diametro is True


def test_9422_distancia_fronteira_5phi():
    # phi=16mm -> distância mínima = 5*16/10 = 8,0 cm
    ok = A.verificar_barra_transversal_soldada(
        phi_mm=16.0, phi_t_mm=16.0, distancia_cm=8.0,
        forca_solda_kn=1000.0, As_cm2=1.0, fyd_mpa=434.78,
    )
    nok = A.verificar_barra_transversal_soldada(
        phi_mm=16.0, phi_t_mm=16.0, distancia_cm=7.9,
        forca_solda_kn=1000.0, As_cm2=1.0, fyd_mpa=434.78,
    )
    assert ok.ok_distancia is True and ok.distancia_min_cm == pytest.approx(8.0)
    assert nok.ok_distancia is False


def test_9422_resistencia_solda_fronteira_03_As_fyd():
    # As=2 cm2, fyd=434,78 MPa -> força_min = 0,3*2*43,478 kN/cm2... espera:
    # 1 MPa = 0,1 kN/cm2 -> fyd em kN/cm2 = 43,478; força_min = 0,3*2*43,478
    As_cm2 = 2.0
    fyd_mpa = 434.78
    forca_min_kn = 0.3 * As_cm2 * (fyd_mpa / 10.0)
    ok = A.verificar_barra_transversal_soldada(
        phi_mm=10.0, phi_t_mm=10.0, distancia_cm=10.0,
        forca_solda_kn=forca_min_kn, As_cm2=As_cm2, fyd_mpa=fyd_mpa,
    )
    nok = A.verificar_barra_transversal_soldada(
        phi_mm=10.0, phi_t_mm=10.0, distancia_cm=10.0,
        forca_solda_kn=forca_min_kn - 0.01, As_cm2=As_cm2, fyd_mpa=fyd_mpa,
    )
    assert ok.ok_solda is True
    assert nok.ok_solda is False
    assert ok.forca_resistente_min_kn == pytest.approx(forca_min_kn)


def test_9422_tudo_ok_resultado_final_ok():
    r = A.verificar_barra_transversal_soldada(
        phi_mm=10.0, phi_t_mm=10.0, distancia_cm=10.0,
        forca_solda_kn=100.0, As_cm2=2.0, fyd_mpa=434.78,
    )
    assert r.ok is True
    assert r.governante == "atende 9.4.2.2 a), b) e c)"


def test_9422_memoria_e_governante_com_acentuacao_correta():
    """Regressão: memória de cálculo e ``governante`` de
    verificar_barra_transversal_soldada devem sair com acentuação correta
    ('distância', 'resistência', 'mínimo', 'início', 'força', 'não ok'),
    não em ASCII puro ('distancia', 'resistencia', 'nao ok' etc.)."""
    reprovado = A.verificar_barra_transversal_soldada(
        phi_mm=20.0, phi_t_mm=10.0, distancia_cm=1.0,
        forca_solda_kn=0.0, As_cm2=3.0, fyd_mpa=434.78,
    )
    assert reprovado.governante == "9.4.2.2 a) phi_t >= 0,60*phi"
    texto = " ".join(reprovado.memoria)
    assert "não ok" in texto
    assert "mínimo" in texto
    assert "distância" in texto
    assert "início" in texto
    assert "força" in texto
    # nenhuma dessas grafias sem acento deve sobreviver na memória
    for sem_acento in ("nao ok", "minimo", "distancia ao inicio", "forca da solda"):
        assert sem_acento not in texto

    reprova_distancia = A.verificar_barra_transversal_soldada(
        phi_mm=20.0, phi_t_mm=12.0, distancia_cm=1.0,
        forca_solda_kn=1000.0, As_cm2=1.0, fyd_mpa=434.78,
    )
    assert reprova_distancia.governante == "9.4.2.2 b) distância >= 5*phi"

    reprova_solda = A.verificar_barra_transversal_soldada(
        phi_mm=20.0, phi_t_mm=12.0, distancia_cm=10.0,
        forca_solda_kn=0.0, As_cm2=1.0, fyd_mpa=434.78,
    )
    assert reprova_solda.governante == "9.4.2.2 c) resistência da solda >= 0,3*As*fyd"


# ===========================================================================
# 9.4.2.3 -- Tabela 9.1 (diâmetro do pino de gancho, PDF p. 56)
# ===========================================================================
@pytest.mark.parametrize("phi_mm, aco, esperado", [
    (10.0, "CA-25", 4.0), (10.0, "CA-50", 5.0), (10.0, "CA-60", 6.0),
    (19.9, "CA-25", 4.0), (19.9, "CA-50", 5.0), (19.9, "CA-60", 6.0),
    (20.0, "CA-25", 5.0), (20.0, "CA-50", 8.0),
    (32.0, "CA-25", 5.0), (32.0, "CA-50", 8.0),
])
def test_9423_tabela_9_1_completa(phi_mm, aco, esperado):
    assert A.diametro_pino_gancho(phi_mm, aco) == esperado


def test_9423_tabela_9_1_ca60_phi_maior_igual_20_levanta_erro():
    """Célula '-' da Tabela 9.1 (CA-60, phi >= 20mm) não tem valor definido."""
    with pytest.raises(nbr.FaixaNormativaError):
        A.diametro_pino_gancho(20.0, "CA-60")
    with pytest.raises(nbr.FaixaNormativaError):
        A.diametro_pino_gancho(25.0, "CA-60")


def test_9423_phi_20mm_e_a_fronteira_entre_faixas():
    assert A.diametro_pino_gancho(19.999, "CA-50") == 5.0
    assert A.diametro_pino_gancho(20.0, "CA-50") == 8.0


def test_9423_aco_invalido_levanta_valueerror():
    with pytest.raises(ValueError):
        A.diametro_pino_gancho(10.0, "CA-35")


# --- comprimento da ponta reta do gancho (9.4.2.3, PDF p. 56) --------------
def test_9423_comprimento_gancho_semicircular_2phi():
    assert A.comprimento_gancho(10.0, "semicircular") == pytest.approx(2.0)  # 20mm=2cm


def test_9423_comprimento_gancho_45_graus_4phi():
    """phi=10mm, gancho 45 graus: ponta reta mínima = 40mm = 4cm."""
    assert A.comprimento_gancho(10.0, "45") == pytest.approx(4.0)


def test_9423_comprimento_gancho_angulo_reto_8phi():
    assert A.comprimento_gancho(10.0, "reto") == pytest.approx(8.0)


def test_9423_comprimento_gancho_tipo_invalido():
    with pytest.raises(ValueError):
        A.comprimento_gancho(10.0, "oitenta_graus")


def test_9423_barra_lisa_so_pode_gancho_semicircular():
    A.comprimento_gancho(10.0, "semicircular", tipo_barra="lisa")  # ok
    with pytest.raises(ValueError):
        A.comprimento_gancho(10.0, "45", tipo_barra="lisa")
    with pytest.raises(ValueError):
        A.comprimento_gancho(10.0, "reto", tipo_barra="lisa")


# --- pino com barra soldada transversal ao gancho (9.4.2.3, PDF p. 56-57) --
# A regra "solda depois do dobramento mantém sempre a Tabela 9.1" está no
# início da página 57 (a de "solda antes do dobramento" está na página 56).
def test_9423_docstring_de_pino_com_solda_transversal_cita_p56_e_p57():
    """Regressão: a citação da página tem de cobrir as duas páginas da
    norma usadas pela função (p. 56 e p. 57), não só a p. 56."""
    doc = A.pino_com_solda_transversal.__doc__ or ""
    assert "56-57" in doc


def test_9423_solda_depois_do_dobramento_mantem_tabela_9_1():
    assert A.pino_com_solda_transversal(
        10.0, "CA-50", solda_antes_dobramento=False,
    ) == A.diametro_pino_gancho(10.0, "CA-50")


def test_9423_solda_antes_dobramento_distancia_maior_4phi_mantem_tabela():
    # phi=10mm -> 4*phi = 40mm
    assert A.pino_com_solda_transversal(
        10.0, "CA-50", solda_antes_dobramento=True,
        distancia_ao_inicio_curva_mm=40.0,
    ) == 5.0
    assert A.pino_com_solda_transversal(
        10.0, "CA-50", solda_antes_dobramento=True,
        distancia_ao_inicio_curva_mm=50.0,
    ) == 5.0


def test_9423_solda_antes_dobramento_distancia_menor_4phi_pino_20phi():
    assert A.pino_com_solda_transversal(
        10.0, "CA-50", solda_antes_dobramento=True,
        distancia_ao_inicio_curva_mm=39.9,
    ) == 20.0


def test_9423_solda_sobre_trecho_curvo_pino_20phi():
    assert A.pino_com_solda_transversal(
        10.0, "CA-50", solda_antes_dobramento=True,
        sobre_trecho_curvo=True,
    ) == 20.0


def test_9423_solda_antes_dobramento_sem_distancia_nem_curva_levanta_erro():
    with pytest.raises(ValueError):
        A.pino_com_solda_transversal(10.0, "CA-50", solda_antes_dobramento=True)


# ===========================================================================
# 9.4.2.6 -- Armadura transversal na ancoragem (PDF p. 57-58)
# ===========================================================================
def test_94261_phi_menor_32_ast_min_25_pct_mesmo_aco():
    # As=5 cm2, mesmo aço -> Ast,min = 0,25*5 = 1,25 cm2 (fyd's se cancelam)
    r = A.Ast_ancoragem(phi_mm=25.0, As_barra_cm2=5.0, fyd_barra_mpa=434.78)
    assert r.duas_direcoes is False
    assert r.Ast_min_cm2 == pytest.approx(1.25)
    assert r.barra_adicional_alem_extremidade_cm is None


def test_94261_phi_menor_32_ast_min_com_aco_transversal_diferente():
    # As=4 cm2 CA-50 (fyd=434,78), transversal CA-60 (fyd=521,74 = 600/1,15)
    fyd_barra = 434.78
    fyd_transv = 600.0 / 1.15
    r = A.Ast_ancoragem(
        phi_mm=20.0, As_barra_cm2=4.0, fyd_barra_mpa=fyd_barra,
        fyd_transversal_mpa=fyd_transv,
    )
    esperado = 0.25 * 4.0 * fyd_barra / fyd_transv
    assert r.Ast_min_cm2 == pytest.approx(esperado)


def test_94261_fronteira_phi_31_9_usa_25_pct():
    r = A.Ast_ancoragem(phi_mm=31.9, As_barra_cm2=8.0, fyd_barra_mpa=434.78)
    assert r.duas_direcoes is False
    assert r.Ast_min_cm2 == pytest.approx(2.0)


def test_94262_phi_40mm_espacamento_maximo_200mm():
    """phi=40mm -> espaçamento máximo = 5*40mm = 200mm = 20cm."""
    r = A.Ast_ancoragem(phi_mm=40.0, As_barra_cm2=10.0, fyd_barra_mpa=434.78)
    assert r.duas_direcoes is True
    assert r.espacamento_max_cm == pytest.approx(20.0)
    assert r.Ast_min_cm2 is None


def test_94262_fronteira_phi_32_usa_regra_de_duas_direcoes():
    r = A.Ast_ancoragem(phi_mm=32.0, As_barra_cm2=10.0, fyd_barra_mpa=434.78)
    assert r.duas_direcoes is True
    assert r.espacamento_max_cm == pytest.approx(16.0)  # 5*32/10


def test_94262_barra_comprimida_posiciona_barra_a_4phi_da_extremidade():
    r = A.Ast_ancoragem(
        phi_mm=40.0, As_barra_cm2=10.0, fyd_barra_mpa=434.78,
        barra_comprimida=True,
    )
    assert r.barra_adicional_alem_extremidade_cm == pytest.approx(16.0)  # 4*40/10


def test_9426_ast_ancoragem_tem_governante_para_os_dois_ramos():
    """Regressão: convenção 3.3 do plano pede ``governante`` em resultado de
    dimensionamento. ResultadoArmaduraTransversalAncoragem não o tinha."""
    menor = A.Ast_ancoragem(phi_mm=25.0, As_barra_cm2=5.0, fyd_barra_mpa=434.78)
    maior = A.Ast_ancoragem(phi_mm=40.0, As_barra_cm2=10.0, fyd_barra_mpa=434.78)
    assert menor.governante == "9.4.2.6.1: phi < 32 mm"
    assert maior.governante == "9.4.2.6.2: phi >= 32 mm"
    # a ausência do campo `ok` (não há valor a comparar, só a exigência
    # calculada) é documentada no docstring da classe, como em
    # ResultadoCombinacao (acoes_nbr6118.py)
    assert "ok" in (A.ResultadoArmaduraTransversalAncoragem.__doc__ or "").lower()


# ===========================================================================
# 9.4.6.1 -- Tabela 9.2 (diâmetro do pino de estribo, PDF p. 60)
# ===========================================================================
@pytest.mark.parametrize("phi_t_mm, aco, esperado", [
    (5.0, "CA-25", 3.0), (10.0, "CA-25", 3.0),
    (5.0, "CA-50", 3.0), (10.0, "CA-50", 3.0),
    (5.0, "CA-60", 3.0), (10.0, "CA-60", 3.0),
    (15.0, "CA-25", 4.0), (15.0, "CA-50", 5.0),
    (20.0, "CA-25", 5.0), (25.0, "CA-25", 5.0),
    (20.0, "CA-50", 8.0), (25.0, "CA-50", 8.0),
])
def test_9461_tabela_9_2_completa(phi_t_mm, aco, esperado):
    assert A.diametro_pino_estribo(phi_t_mm, aco) == esperado


def test_9461_tabela_9_2_ca60_fora_de_ate_10mm_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        A.diametro_pino_estribo(15.0, "CA-60")
    with pytest.raises(nbr.FaixaNormativaError):
        A.diametro_pino_estribo(20.0, "CA-60")


def test_9461_fronteiras_da_tabela_9_2():
    assert A.diametro_pino_estribo(10.0, "CA-50") == 3.0    # <= 10
    assert A.diametro_pino_estribo(10.001, "CA-50") == 5.0  # 10 < phi < 20
    assert A.diametro_pino_estribo(19.999, "CA-50") == 5.0
    assert A.diametro_pino_estribo(20.0, "CA-50") == 8.0    # >= 20


# --- ponta reta do gancho de estribo (9.4.6.1, PDF p. 60) ------------------
def test_9461_ponta_reta_135_fronteira_5cm():
    """phi_t=6,3mm, 135 graus: ponta reta = max(5*6,3mm; 50mm) = 50mm = 5cm."""
    assert A.ponta_reta_estribo_cm(6.3, "135") == pytest.approx(5.0)


def test_9461_ponta_reta_135_domina_5phi_quando_maior_que_5cm():
    # phi_t=20mm: 5*20=100mm=10cm > 5cm
    assert A.ponta_reta_estribo_cm(20.0, "semicircular") == pytest.approx(10.0)


def test_9461_ponta_reta_angulo_reto_10phi():
    """phi_t=10mm, ângulo reto: ponta reta = max(100mm; 70mm) = 100mm = 10cm."""
    assert A.ponta_reta_estribo_cm(10.0, "reto") == pytest.approx(10.0)


def test_9461_ponta_reta_angulo_reto_domina_piso_7cm():
    # phi_t=6mm: 10*6=60mm=6cm < 7cm -> piso de 7cm domina
    assert A.ponta_reta_estribo_cm(6.0, "reto") == pytest.approx(7.0)


def test_9461_angulo_reto_proibido_para_aco_liso():
    with pytest.raises(ValueError):
        A.ponta_reta_estribo_cm(10.0, "reto", aco_liso=True)
    A.ponta_reta_estribo_cm(10.0, "135", aco_liso=True)  # 135 permitido p/ liso


def test_9461_tipo_gancho_estribo_invalido():
    with pytest.raises(ValueError):
        A.ponta_reta_estribo_cm(10.0, "quarenta_graus")


# ===========================================================================
# 9.4.6.2 -- Ancoragem de estribo por barra transversal soldada (PDF p. 60-61)
# ===========================================================================
def test_9462_duas_barras_phi_t_8mm():
    """phi_t=8mm, 2 barras: phi_t1_min = 5,6mm (desigualdade estrita: 5,6mm
    exato reprova; 5,7mm passa)."""
    r_no_limite = A.ancoragem_estribo_barra_soldada(
        phi_t_mm=8.0, phi_t1_mm=5.6, num_barras_soldadas=2,
    )
    r_acima = A.ancoragem_estribo_barra_soldada(
        phi_t_mm=8.0, phi_t1_mm=5.7, num_barras_soldadas=2,
    )
    assert r_no_limite.phi_t1_min_mm == pytest.approx(5.6)
    assert r_no_limite.ok is False
    assert r_acima.ok is True


def test_9462_uma_barra_phi_t_8mm():
    """phi_t=8mm, 1 barra (estribo 2 ramos): phi_t1_min = 11,2mm, fronteira
    inclusiva (>=)."""
    r_no_limite = A.ancoragem_estribo_barra_soldada(
        phi_t_mm=8.0, phi_t1_mm=11.2, num_barras_soldadas=1,
    )
    r_abaixo = A.ancoragem_estribo_barra_soldada(
        phi_t_mm=8.0, phi_t1_mm=11.1, num_barras_soldadas=1,
    )
    assert r_no_limite.phi_t1_min_mm == pytest.approx(11.2)
    assert r_no_limite.ok is True
    assert r_abaixo.ok is False


def test_9462_num_barras_soldadas_invalido_levanta_erro():
    with pytest.raises(ValueError):
        A.ancoragem_estribo_barra_soldada(phi_t_mm=8.0, phi_t1_mm=10.0, num_barras_soldadas=3)


def test_9462_memoria_com_acentuacao_correta_em_nao_ok():
    """Regressão: a memória de ancoragem_estribo_barra_soldada usava
    'nao ok' em ASCII quando a verificação reprovava."""
    reprovado = A.ancoragem_estribo_barra_soldada(
        phi_t_mm=8.0, phi_t1_mm=5.0, num_barras_soldadas=2,
    )
    assert reprovado.ok is False
    texto = " ".join(reprovado.memoria)
    assert "não ok" in texto
    assert "nao ok" not in texto


# ===========================================================================
# Risco 6 do plano -- Tabelas degrau contra interpolação: alpha_0t (Tabela
# 9.4) confirmado por degrau (não interpola) em 30% e 40% de barras emendadas.
# ===========================================================================
def test_risco6_alpha_0t_degrau_30_pct():
    """30% cai na faixa '<=33' -> alpha_0t = 1,6 (não interpola entre 1,4 e 1,6)."""
    assert A.alpha_0t(30.0) == 1.6


def test_risco6_alpha_0t_degrau_40_pct():
    """40% cai na faixa '<=50' -> alpha_0t = 1,8 (não interpola entre 1,6 e 1,8)."""
    assert A.alpha_0t(40.0) == 1.8
