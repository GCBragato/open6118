"""Ancoragem (secoes_norma/sec9.py legado e dimensionamento/ancoragem_bastos.py)
contra a NBR 6118:2026 -- achados ANC-01 a ANC-08.

Valores esperados das reproducoes verificadas na auditoria de 18/09/2026
(SCRATCH/achados_brutos.md e verificacao_resultados.md: todas as reproducoes
de ANC-01 a ANC-08 foram confirmadas por execucao, sem ajuste de numero),
ou recalculados a partir das formulas e tabelas da propria norma (paginas do
PDF: Tabela 8.2 p.48; 9.3.2.1 p.54; 9.4.2.4/.5 p.57; Tabela 9.1 p.57;
9.4.5.2 p.59; Tabela 9.2 p.60; 9.5.2/Tabela 9.4 p.62-63).

ANC-09 nao entra aqui: e' de sec8.py, escopo de outro agente.
"""

import math
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "dimensionamento"))
sys.path.insert(0, str(_REPO / "secoes_norma"))

import nucleo_nbr6118 as nbr  # noqa: E402
import ancoragem_bastos as A  # noqa: E402
import sec9  # noqa: E402


# Parametros de referencia comuns aos exemplos do achado (C25, CA-50
# nervurada, boa aderencia, phi < 32 mm), os mesmos usados na auditoria:
# fyd = 500/1,15 = 434,78 MPa; fctd = 1,2825 MPa;
# fbd = eta1(2,25)*eta2(1)*eta3(1)*fctd = 2,8856 MPa.
FYD_CA50 = 500.0 / 1.15
FCTD_C25 = nbr.fctd(25.0)
FBD_C25_CA50_NERVURADA = nbr.eta1("CA-50") * FCTD_C25


# --- ANC-01: eta1 pela categoria do aco, nao pela superficie da barra -----
# (Tabela 8.2, PDF p.48: CA-25 1,00; CA-50 2,25; CA-60 1,00)
def test_ANC01_eta1_por_categoria_default_por_tipo_barra():
    """Sem categoria explicita: lisa->CA-25, entalhada->CA-60, nervurada->CA-50."""
    fctd = FCTD_C25
    assert sec9.res_ade_pass('lisa', 'boa', 16, fctd) == pytest.approx(1.00 * fctd)
    assert sec9.res_ade_pass('entalhada', 'boa', 16, fctd) == pytest.approx(1.00 * fctd)
    assert sec9.res_ade_pass('nervurada', 'boa', 16, fctd) == pytest.approx(2.25 * fctd)


def test_ANC01_ca60_nervurado_exige_categoria_explicita():
    """CA-60 nervurado (eta1=1,00) precisa de categoria='CA-60' explicito;
    sem ela, 'nervurada' cai no default CA-50 (eta1=2,25). Repro do achado:
    fbd sai 2,25x maior (CA-60 nervurado, fctd=1,2825 -> fbd 2,8856 no lugar
    de 1,2825), o que compactava lb em 56%."""
    fctd = FCTD_C25
    fbd_ca60 = sec9.res_ade_pass('nervurada', 'boa', 16, fctd, categoria='CA-60')
    fbd_default = sec9.res_ade_pass('nervurada', 'boa', 16, fctd)
    assert fbd_ca60 == pytest.approx(1.2825, abs=0.001)
    assert fbd_default == pytest.approx(2.8856, abs=0.001)
    assert fbd_default / fbd_ca60 == pytest.approx(2.25)


@pytest.mark.parametrize("fck", [20.0, 30.0, 45.0, 50.0, 55.0, 70.0, 90.0])
def test_ANC01_fbd_varre_classes_via_nucleo(fck):
    """eta1 delega ao nucleo (nbr.eta1) em qualquer classe de fck."""
    fctd = nbr.fctd(fck)
    fbd = sec9.res_ade_pass('nervurada', 'boa', 16, fctd)
    assert fbd == pytest.approx(nbr.eta1("CA-50") * fctd)


# --- ANC-02: unidade de comp_ancor_basico e piso de comp_ancor_necessario -
# (9.4.2.4/9.4.2.5, PDF p.57)
def test_ANC02_comp_ancor_basico_em_cm_nao_em_mm():
    """Repro do achado: comp_ancor_basico(16, 434,78, 2,8856) -> 60,27 cm
    (antes saia 602,70: dez vezes maior, com rotulo de cm mas valor em mm)."""
    lb = sec9.comp_ancor_basico(16, FYD_CA50, FBD_C25_CA50_NERVURADA)
    assert lb == pytest.approx(60.27, abs=0.05)


def test_ANC02_piso_100mm_em_comp_ancor_necessario():
    """phi=6 mm: lb_min = max(0,3*lb, 10*phi, 100 mm) tem que bater
    exatamente no piso de 100 mm = 10 cm. Achado: o piso buggy dava so
    67,80% do valor fisico de 100 mm exigido pela norma (-32%, contra a
    seguranca) porque "10*bitola" nao convertia mm->cm e o piso aparecia
    como "10" em vez de "100"."""
    lb = sec9.comp_ancor_basico(6, FYD_CA50, FBD_C25_CA50_NERVURADA)
    lb_nec = sec9.comp_ancor_necessario(1.0, lb, 0.4, 1.0, 6)
    assert lb_nec == pytest.approx(10.0, abs=0.01)  # 100 mm


# --- ANC-03: piso de 200 mm no traspasse, mesma conversao de phi ----------
# (9.5.2.2.1 e 9.5.2.3, PDF p.62-63)
def test_ANC03_piso_200mm_traspasse_tracionado():
    """phi=8 mm, C25, 20% emendadas, As,calc/As,ef=0,5: o piso de 200 mm
    domina (achado: 180,81 mm x 200,00 mm, -9,6%, porque "15*bitola" nao
    convertia mm->cm)."""
    lb = sec9.comp_ancor_basico(8, FYD_CA50, FBD_C25_CA50_NERVURADA)
    lb_nec = sec9.comp_ancor_necessario(1.0, lb, 0.5, 1.0, 8)
    l0t = sec9.comp_transpasse_trac(20, lb_nec, lb, 8)
    assert l0t == pytest.approx(20.0, abs=0.01)  # 200 mm


def test_ANC03_piso_200mm_traspasse_comprimido():
    lb = sec9.comp_ancor_basico(8, FYD_CA50, FBD_C25_CA50_NERVURADA)
    lb_nec = sec9.comp_ancor_necessario(1.0, lb, 0.5, 1.0, 8)
    l0c = sec9.comp_transpasse_comp(lb_nec, lb, 8)
    assert l0c == pytest.approx(20.0, abs=0.01)  # 200 mm


# --- ANC-04: coeficientes de lbpt (nao os de lbp) e liberacao subita ------
# (9.4.5.2, PDF p.59)
@pytest.mark.parametrize("tipo, esperado", [
    ('isolado', 0.7 * 100 * 1300 / 1450),   # fios dentados/lisos: 62,76 cm
    ('grupo', 0.5 * 100 * 1300 / 1450),     # cordoalhas de 3/7 fios: 44,83 cm
])
def test_ANC04_lbpt_coeficientes_corretos(tipo, esperado):
    """Achado: usava os coeficientes de lbp (1/4 e 7/36, de 9.4.5.1) em vez
    de 0,7 e 0,5 (9.4.5.2): lbpt saia 61% a 64% menor."""
    assert sec9.comp_transferencia(100, 1300, 1450, tipo) == pytest.approx(esperado, rel=1e-9)


def test_ANC04_liberacao_subita_multiplica_1_25():
    """9.4.5.2 b): liberacao nao gradual (subita) multiplica lbpt por 1,25."""
    gradual = sec9.comp_transferencia(100, 1300, 1450, 'isolado')
    subita = sec9.comp_transferencia(100, 1300, 1450, 'isolado', liberacao_gradual=False)
    assert subita == pytest.approx(gradual * 1.25)
    assert subita == pytest.approx(78.4483, abs=0.001)


# --- ANC-05: pino de dobramento tem que retornar, nao None ----------------
# (Tabelas 9.1 e 9.2, PDF p.57 e p.60)
def test_ANC05_diam_pino_dobramento_retorna_valor_tabela_9_1():
    """Antes, o `return D` ficava dentro de um `else` inalcancavel: a
    funcao sempre devolvia None. Repro do achado: (16,'CA50') -> 5 phi."""
    assert sec9.diam_pino_dobramento(16, 'CA50') == 5    # < 20 mm
    assert sec9.diam_pino_dobramento(24, 'CA25') == 5    # >= 20 mm
    assert sec9.diam_pino_dobramento(8, 'CA60') == 6     # < 20 mm


def test_ANC05_diam_pino_dobramento_transversal_retorna_valor_tabela_9_2():
    """Repro do achado: (8,'CA50') -> 3 phi."""
    assert sec9.diam_pino_dobramento_transversal(8, 'CA50') == 3    # <= 10 mm
    assert sec9.diam_pino_dobramento_transversal(15, 'CA50') == 5   # 10-20 mm
    assert sec9.diam_pino_dobramento_transversal(25, 'CA25') == 5   # >= 20 mm


def test_ANC05_combinacao_sem_valor_na_tabela_levanta_erro():
    """CA-60 com bitola >= 20 mm (Tabela 9.1) ou > 10 mm (Tabela 9.2) nao
    tem valor definido na norma ('-' na tabela); a funcao deve dizer isso
    em vez de devolver None em silencio para qualquer combinacao."""
    with pytest.raises(ValueError):
        sec9.diam_pino_dobramento(25, 'CA60')
    with pytest.raises(ValueError):
        sec9.diam_pino_dobramento_transversal(15, 'CA60')


# --- ANC-06: 'ma' e 'ma' acentuado sao a mesma situacao (9.3.2.1) ---------
def test_ANC06_aceita_ma_com_e_sem_acento():
    """A docstring sempre pediu 'ma' (com acento); antes so 'ma' (sem
    acento) funcionava e 'ma' acentuado quebrava adiante."""
    fctd = FCTD_C25
    v_ma = sec9.res_ade_pass('nervurada', 'ma', 16, fctd)
    v_maacc = sec9.res_ade_pass('nervurada', 'má', 16, fctd)
    assert v_ma == pytest.approx(v_maacc)
    assert v_ma == pytest.approx(0.7 * 2.25 * fctd)

    v_ati_ma = sec9.res_ade_ati('cordoalha', 'ma', fctd)
    v_ati_maacc = sec9.res_ade_ati('cordoalha', 'má', fctd)
    assert v_ati_ma == pytest.approx(v_ati_maacc)


def test_ANC06_qual_ader_invalido_levanta_valueerror_nao_typeerror():
    """Antes, um qual_ader desconhecido virava o sentinela 'erro' (string) e
    so explodia mais adiante, na multiplicacao, como TypeError confuso."""
    with pytest.raises(ValueError):
        sec9.res_ade_pass('nervurada', 'excelente', 16, FCTD_C25)


# --- ANC-07: fctm_mpa com o ramo de fck > 50 (ancoragem_bastos.py) --------
# (8.2.5, PDF p.42-43)
@pytest.mark.parametrize("fck, esperado", [
    (45.0, 0.3 * 45 ** (2 / 3)),
    (50.0, 0.3 * 50 ** (2 / 3)),
    (55.0, 2.12 * math.log(1 + 0.1 * 63)),
    (70.0, 2.12 * math.log(1 + 0.1 * 78)),
    (90.0, 2.12 * math.log(1 + 0.1 * 98)),
])
def test_ANC07_fctm_mpa_varre_classes(fck, esperado):
    assert A.fctm_mpa(fck) == pytest.approx(esperado, rel=1e-9)


def test_ANC07_lb_basico_cm_c90_reproducao_achado():
    """Repro do achado: fctm(90) 6,0249 (buggy, sem o ramo >50) x 5,0446
    (correto); lb(phi16, C90) 25,66 x 30,64 cm -- o valor antigo era menor
    (contra a seguranca)."""
    assert A.fctm_mpa(90.0) == pytest.approx(5.0446, abs=0.001)
    assert A.fctm_mpa(90.0) != pytest.approx(6.0249, abs=0.001)
    lb = A.lb_basico_cm(16.0, 90.0)
    assert lb == pytest.approx(30.64, abs=0.05)


@pytest.mark.parametrize("fck", [45.0, 50.0, 55.0, 70.0, 90.0])
def test_ANC07_delega_ao_nucleo_em_toda_classe(fck):
    """fctm_mpa, fctd_mpa, eta1, eta2 e eta3 tem que ser invólucros do
    nucleo normativo unico (mesma fonte, sem copia local), e as funcoes
    encadeadas (comprimento_ancoragem, transpasse) nao podem quebrar em
    nenhuma classe de C45 a C90."""
    assert A.fctm_mpa(fck) == nbr.fct_m(fck)
    assert A.fctd_mpa(fck) == nbr.fctd(fck)
    assert A.eta1("CA-50") == nbr.eta1("CA-50")
    assert A.eta2(True) == nbr.eta2(True)
    assert A.eta3(40.0) == nbr.eta3(40.0)

    r = A.comprimento_ancoragem(phi_mm=16.0, fck_mpa=fck)
    assert r.lb_cm > 0.0
    assert r.fbd_mpa == pytest.approx(nbr.fbd(fck, "CA-50", True, 16.0))

    t = A.transpasse_tracionado_cm(phi_mm=16.0, fck_mpa=fck, percent_emendadas=20.0)
    assert t["l0t_cm"] > 0.0
    c = A.transpasse_comprimido_cm(phi_mm=16.0, fck_mpa=fck)
    assert c["l0c_cm"] > 0.0


# --- ANC-08: traspasse proibido para bitola > 32 mm, nas quatro funcoes --
# (9.5.2, PDF p.62)
@pytest.mark.parametrize("chamada", [
    lambda: sec9.comp_transpasse_trac(20, 10.0, 10.0, 40.0),
    lambda: sec9.comp_transpasse_comp(10.0, 10.0, 40.0),
    lambda: A.transpasse_tracionado_cm(40.0, 25.0, 20.0),
    lambda: A.transpasse_comprimido_cm(40.0, 25.0),
], ids=["sec9.trac", "sec9.comp", "bastos.trac", "bastos.comp"])
def test_ANC08_bitola_maior_32mm_levanta_erro(chamada):
    """Achado: as quatro funcoes calculavam traspasse para phi=40 mm (l0t =
    196,53 cm) sem aviso; a norma proibe esse tipo de emenda acima de 32 mm."""
    with pytest.raises(ValueError):
        chamada()


def test_ANC08_bitola_igual_32mm_nao_levanta():
    """O limite e' 'bitola MAIOR que 32 mm' (9.5.2): 32 mm exato continua permitido."""
    sec9.comp_transpasse_trac(20, 10.0, 10.0, 32.0)
    sec9.comp_transpasse_comp(10.0, 10.0, 32.0)
    A.transpasse_tracionado_cm(32.0, 25.0, 20.0)
    A.transpasse_comprimido_cm(32.0, 25.0)


# --- Ajustes da consolidação (mesma classe de ANC-02 e ANC-06) -------------
def test_comp_ancor_basico_ativo_em_cm():
    """9.4.5.1: lbp = (phi/4)(fpyd/fbpd) para fios; (7 phi/36)(fpyd/fbpd) para
    cordoalhas. phi entra em mm e o resultado sai em cm, coerente com
    comp_ancor_basico depois da correção do ANC-02."""
    fbpd = nbr.fbpd(30.0, "cordoalha", True)
    assert sec9.comp_ancor_basico_ativo(12.7, 1450.0, fbpd, "grupo") == pytest.approx(
        7 * 12.7 / 36 * 1450.0 / fbpd / 10.0)
    assert sec9.comp_ancor_basico_ativo(5.0, 1450.0, fbpd, "isolado") == pytest.approx(
        5.0 / 4 * 1450.0 / fbpd / 10.0)
    with pytest.raises(ValueError):
        sec9.comp_ancor_basico_ativo(12.7, 1450.0, fbpd, "feixe")


def test_res_ade_ati_tipo_fio_invalido_levanta_valueerror():
    """Antes, um tipo_fio desconhecido virava a string 'erro' e quebrava com TypeError."""
    assert sec9.res_ade_ati("cordoalha", "boa", 1.0) == pytest.approx(1.2)
    with pytest.raises(ValueError):
        sec9.res_ade_ati("barra", "boa", 1.0)
