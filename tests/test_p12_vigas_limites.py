"""Testes do P12 — Vigas: armaduras minima, maxima e de pele; instabilidade
lateral.

Cobre o bloco "# === P12" acrescentado a dimensionamento/vigas_nbr6118.py
contra a ABNT NBR 6118:2026:

  - 17.1 (taxa mecanica minima de armadura de flexao, wmin), p. 140
  - 17.2.3 (dutilidade em vigas: limite de x/d, remete a 14.6.4.3), p. 142
  - 17.2.4.1 (concentracao de forcas de barras no centroide, 10% de h), p. 143
  - 17.3.5.2.3 (armadura de pele em vigas), p. 153
  - 17.3.5.2.4 (soma maxima de As e A's, 4% Ac), p. 153
  - 18.3.5 (espacamento maximo da armadura de pele), p. 172
  - 19.3.3.3 (armadura maxima de flexao de laje remete a 17.3.5.2), p. 181
  - 15.10 (instabilidade lateral de vigas, Tabela 15.1), p. 134

Os valores esperados vem da imagem de cada pagina (SCRATCH\\nbr_png\\pNNN.png),
nao do JSON do plano.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr                # noqa: E402
import vigas_nbr6118 as vig                 # noqa: E402


# =============================================================================
# 17.1 — Taxa mecanica minima de armadura de flexao, wmin (p. 140)
# =============================================================================
def test_omega_min_reproduz_As_min_via_rho_min():
    """wmin = rho_min(fck) * fyd / fcd  =>  wmin * Ac * fcd / fyd = As,min.

    fck = 30 MPa, fyk = 500 MPa. rho_min(30) = 0,150% (Tabela 17.3).
    fyd = 500/1,15 = 434,78 MPa; fcd = 30/1,4 = 21,43 MPa.
    wmin esperado = 0,0015 * 434,78 / 21,43 = 0,030435...
    """
    fck, fyk = 30.0, 500.0
    w = vig.omega_min(fck, fyk)
    rho_min = nbr.rho_min_flexao(fck)
    fyd = nbr.fyd(fyk, vig.GAMA_S)
    fcd = nbr.fcd(fck, vig.GAMA_C)
    assert w == pytest.approx(rho_min * fyd / fcd, rel=1e-9)

    # Ac = 20 * 50 = 1000 cm2 -> As,min = rho_min * Ac = 0,0015*1000 = 1,5 cm2.
    Ac = 20.0 * 50.0
    As_min_via_wmin = w * Ac * fcd / fyd
    As_min_via_rho = rho_min * Ac
    assert As_min_via_wmin == pytest.approx(As_min_via_rho, rel=1e-9)
    assert As_min_via_rho == pytest.approx(1.5, rel=1e-6)


def test_omega_min_independe_de_geometria():
    """wmin e uma taxa (adimensional), nao depende de bw/h - so de fck/fyk."""
    w1 = vig.omega_min(25.0, 500.0)
    w2 = vig.omega_min(25.0, 500.0)
    assert w1 == pytest.approx(w2)


def test_omega_min_recusa_fyk_fora_do_padrao_da_tabela_17_3():
    """A Tabela 17.3 (nbr.rho_min_flexao) pressupoe CA-50 (fyk=500 MPa),
    gama_c=1,4 e gama_s=1,15 (docstring de rho_min_flexao). Fora disso,
    rho_min(fck)*fyd/fcd nao reproduz As,min/Ac quando o momento minimo (nao
    o piso de 0,15%) e' quem governa: para fck=30, bw=20, h=200, d=195,
    fyk=250 (CA-25), As_min_flexao_retangular = 9,616 cm2 (> piso de 0,15%*
    Ac = 6,0 cm2, entao o momento minimo governa), o que da'
    w_correto = 9,616*fyd/(Ac*fcd) = 0,024389 - bem diferente do que a
    formula tabelada (CA-50) devolveria para fyk=250 (0,015217, ~38% menor).
    omega_min deve recusar fyk_mpa != 500 (e gama_c/gama_s fora do padrao)
    em vez de devolver esse numero errado."""
    with pytest.raises(nbr.FaixaNormativaError):
        vig.omega_min(30.0, fyk_mpa=250.0)
    with pytest.raises(nbr.FaixaNormativaError):
        vig.omega_min(30.0, fyk_mpa=500.0, gama_c=1.3)
    with pytest.raises(nbr.FaixaNormativaError):
        vig.omega_min(30.0, fyk_mpa=500.0, gama_s=1.2)
    # fyk=500 (padrao da tabela) continua funcionando normalmente.
    vig.omega_min(30.0, fyk_mpa=500.0)


# =============================================================================
# 17.3.5.2.3 e 18.3.5 — Armadura de pele (p. 153 e 172)
# =============================================================================
def test_pele_dispensada_h_igual_60cm():
    """17.3.5.2.3: 'em vigas com altura igual ou inferior a 60 cm, pode ser
    dispensada a utilizacao da armadura de pele.' h = 60 cm exato -> 0,0."""
    assert vig.armadura_pele_cm2_por_face(bw_cm=20.0, h_cm=60.0) == 0.0


def test_pele_dispensada_h_abaixo_60cm():
    assert vig.armadura_pele_cm2_por_face(bw_cm=30.0, h_cm=45.0) == 0.0


def test_pele_exigida_h_acima_60cm():
    """h = 61 cm (1 cm acima do limite de dispensa): passa a exigir pele.
    bw = 20 cm -> taxa = 0,0010 * 20 * 100 = 2,0 cm2/m (nao atinge o teto)."""
    taxa = vig.armadura_pele_cm2_por_face(bw_cm=20.0, h_cm=61.0)
    assert taxa == pytest.approx(2.0)


def test_pele_teto_5cm2_por_m():
    """bw = 50 cm -> 0,0010*50*100 = 5,0 cm2/m: exatamente no teto."""
    taxa = vig.armadura_pele_cm2_por_face(bw_cm=50.0, h_cm=100.0)
    assert taxa == pytest.approx(5.0)


def test_pele_teto_nao_ultrapassa_5cm2_por_m():
    """bw = 80 cm -> 0,0010*80*100 = 8,0 cm2/m, mas o teto e 5,0 cm2/m."""
    taxa = vig.armadura_pele_cm2_por_face(bw_cm=80.0, h_cm=100.0)
    assert taxa == pytest.approx(5.0)


def test_espacamento_max_pele_governado_por_20cm():
    """18.3.5: afastamento <= min(d/3, 20 cm). d = 90 cm -> d/3 = 30 cm,
    logo o teto de 20 cm governa."""
    assert vig.espacamento_max_pele_cm(d_cm=90.0) == pytest.approx(20.0)


def test_espacamento_max_pele_governado_por_d3():
    """d = 45 cm -> d/3 = 15 cm < 20 cm, logo d/3 governa."""
    assert vig.espacamento_max_pele_cm(d_cm=45.0) == pytest.approx(15.0)


def test_espacamento_max_pele_ponto_de_igualdade():
    """d = 60 cm -> d/3 = 20 cm = teto: os dois lados coincidem."""
    assert vig.espacamento_max_pele_cm(d_cm=60.0) == pytest.approx(20.0)


# =============================================================================
# 17.3.5.2.4 e 19.3.3.3 — Soma maxima de As e A's, 4% Ac (p. 153 e 181)
# =============================================================================
def test_as_max_viga_exatamente_no_limite_4pct():
    """Ac = 20*50 = 1000 cm2 -> limite = 4%*1000 = 40 cm2.
    As + A's = 40,00 cm2 exatos -> ok (limite e '<=', nao '<')."""
    Ac = 20.0 * 50.0
    r = vig.verificar_As_max_viga(As_cm2=30.0, As_linha_cm2=10.0, Ac_cm2=Ac)
    assert r.soma == pytest.approx(40.0)
    assert r.limite == pytest.approx(40.0)
    assert r.ok is True


def test_as_max_viga_acima_do_limite_4pct():
    Ac = 20.0 * 50.0  # limite = 40 cm2
    r = vig.verificar_As_max_viga(As_cm2=30.0, As_linha_cm2=10.01, Ac_cm2=Ac)
    assert r.ok is False
    assert "4%" in r.governante or "As" in r.governante


def test_as_max_viga_sem_armadura_comprimida():
    Ac = 20.0 * 60.0  # limite = 48 cm2
    r = vig.verificar_As_max_viga(As_cm2=20.0, As_linha_cm2=0.0, Ac_cm2=Ac)
    assert r.soma == pytest.approx(20.0)
    assert r.ok is True


def test_as_max_viga_vale_tambem_para_laje_19_3_3_3():
    """19.3.3.3: 'o valor maximo da armadura de flexao deve respeitar o
    limite dado em 17.3.5.2' - mesma funcao serve para laje, so trocando Ac."""
    Ac_laje = 100.0 * 12.0  # faixa de 1 m de largura, h = 12 cm
    limite = 0.04 * Ac_laje
    r = vig.verificar_As_max_viga(As_cm2=limite, As_linha_cm2=0.0, Ac_cm2=Ac_laje)
    assert r.ok is True
    r2 = vig.verificar_As_max_viga(As_cm2=limite + 0.01, As_linha_cm2=0.0, Ac_cm2=Ac_laje)
    assert r2.ok is False


def test_verificar_limites_armadura_viga_ok():
    """Combina 17.3.5.2.4 (As+A's<=4%Ac) e a dutilidade de x/d (17.2.3):
    caso dentro dos dois limites."""
    r_flexao = vig.secao_retangular_simples(
        Md_kncm=14000.0, bw_cm=20.0, d_cm=47.0, h_cm=50.0, fck_mpa=20.0,
    )
    assert not r_flexao.erro
    r = vig.verificar_limites_armadura_viga(r_flexao)
    assert r.ok_dutilidade is True
    assert r.as_max.ok is True
    assert r.ok is True


def test_verificar_limites_armadura_viga_reprova_dutilidade():
    """Momento excessivo para a secao -> x/d estoura o limite de dutilidade
    (dominio 4), refletido em ok_dutilidade=False dentro da verificacao
    combinada."""
    r_flexao = vig.secao_retangular_simples(
        Md_kncm=25000.0, bw_cm=30.0, d_cm=45.0, h_cm=50.0, fck_mpa=20.0,
    )
    assert r_flexao.beta_x > nbr.xd_limite_dutilidade(20.0)
    r = vig.verificar_limites_armadura_viga(r_flexao)
    assert r.ok_dutilidade is False
    assert r.ok is False


# =============================================================================
# 17.2.4.1 — Concentracao de forcas de barras no centroide, 10% de h (p. 143)
# =============================================================================
def test_agrupamento_permitido_abaixo_de_10pct_h():
    assert vig.agrupamento_barras_permitido(dist_cm=5.0, h_cm=60.0) is True


def test_agrupamento_nao_permitido_no_limite_exato():
    """A norma usa '<' (estritamente menor) que 10% de h: no ponto exato de
    igualdade, a condicao nao e satisfeita."""
    assert vig.agrupamento_barras_permitido(dist_cm=6.0, h_cm=60.0) is False


def test_agrupamento_nao_permitido_acima_de_10pct_h():
    assert vig.agrupamento_barras_permitido(dist_cm=7.0, h_cm=60.0) is False


# =============================================================================
# 15.10 — Instabilidade lateral de vigas, Tabela 15.1 (p. 134)
# =============================================================================
@pytest.mark.parametrize("tipo, beta_fl_esperado", [
    ("retangular", 0.40),
    ("t", 0.40),
    ("i", 0.40),
    ("duplo_t", 0.20),
    ("caixao", 0.20),
])
def test_tabela_15_1_todas_as_celulas(tipo, beta_fl_esperado):
    assert vig.TABELA_15_1[tipo] == pytest.approx(beta_fl_esperado)


def test_instabilidade_lateral_limite_vao_exato():
    """b = l0/50 exatamente, com b >= beta_fl*h tambem satisfeito -> ok."""
    l0 = 500.0
    b = l0 / 50.0  # 10 cm
    h = 20.0       # beta_fl*h = 0,40*20 = 8 cm <= b
    r = vig.verificar_instabilidade_lateral(b_cm=b, h_cm=h, l0_cm=l0, tipo="retangular")
    assert r.ok_vao is True
    assert r.ok_altura is True
    assert r.ok is True


def test_instabilidade_lateral_limite_altura_exato_retangular():
    """b = 0,40*h exatamente (retangular), com b >= l0/50 tambem satisfeito."""
    h = 40.0
    b = 0.40 * h  # 16 cm
    l0 = 500.0    # l0/50 = 10 cm <= b
    r = vig.verificar_instabilidade_lateral(b_cm=b, h_cm=h, l0_cm=l0, tipo="retangular")
    assert r.ok_altura is True
    assert r.ok_vao is True
    assert r.ok is True


def test_instabilidade_lateral_retangular_reprova_onde_duplo_t_passa():
    """Mesmo b/h/l0: beta_fl cai de 0,40 (retangular/T/I) para 0,20 (duplo T
    ou caixao, mesa comprimida compartilhada por duas almas) - a Tabela 15.1
    afrouxa o limite de altura para duplo T (0,20*h < 0,40*h), entao um b que
    so atende o duplo T reprova a tipologia retangular.

    h = 40 cm, b = 0,20*40 = 8 cm (exatamente no limite de duplo T);
    l0 = 200 cm -> l0/50 = 4 cm, nao governa em nenhum dos dois casos."""
    h, b, l0 = 40.0, 8.0, 200.0
    r_duplo = vig.verificar_instabilidade_lateral(b_cm=b, h_cm=h, l0_cm=l0, tipo="duplo_t")
    assert r_duplo.ok_altura is True
    assert r_duplo.ok is True

    r_ret = vig.verificar_instabilidade_lateral(b_cm=b, h_cm=h, l0_cm=l0, tipo="retangular")
    assert r_ret.ok_altura is False
    assert r_ret.ok is False


def test_instabilidade_lateral_tipo_desconhecido():
    """Tipologia fora da Tabela 15.1 e' celula sem valor definido: levanta
    FaixaNormativaError (convencao 3.3, item 3), nao ValueError generico."""
    with pytest.raises(nbr.FaixaNormativaError):
        vig.verificar_instabilidade_lateral(b_cm=10.0, h_cm=20.0, l0_cm=100.0, tipo="hexagonal")
