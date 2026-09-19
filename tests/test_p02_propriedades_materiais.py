"""Testes do pacote P2 — Propriedades complementares dos materiais.

Valores esperados tirados do texto da NBR 6118:2026 (página do PDF citada em
cada teste), não de apostila. Itens do pacote: 8.2.2, 8.2.3, 8.2.5, 8.2.6,
8.2.9, 8.2.10.1 (Figura 8.3), 8.2.10.2 (Figura 8.4), 8.3.3/8.4.2, 8.3.4/8.4.3,
8.3.7 e 14.7.3.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402


# --- 8.2.2 massa específica do concreto (p. 42) -----------------------------
def test_massa_especifica_concreto_valores_fixos():
    """Na falta de ensaio: simples 2400 kg/m3, armado 2500 kg/m3 (8.2.2, p. 42)."""
    assert nbr.MASSA_ESPECIFICA_CONCRETO_SIMPLES_KG_M3 == 2400.0
    assert nbr.MASSA_ESPECIFICA_CONCRETO_ARMADO_KG_M3 == 2500.0


def test_massa_especifica_concreto_faixa_normal():
    """A norma define concreto de massa específica normal entre 2000 e 2800 kg/m3."""
    assert nbr.MASSA_ESPECIFICA_CONCRETO_MIN_KG_M3 == 2000.0
    assert nbr.MASSA_ESPECIFICA_CONCRETO_MAX_KG_M3 == 2800.0


@pytest.mark.parametrize("rho_simples, acrescimo, esperado", [
    (2350.0, 100.0, 2450.0),   # borda inferior do acréscimo
    (2350.0, 150.0, 2500.0),   # borda superior do acréscimo
    (2350.0, 125.0, 2475.0),   # ponto interior (padrão da função)
])
def test_massa_especifica_concreto_armado_com_simples_conhecida(rho_simples, acrescimo, esperado):
    """Com a massa específica real do concreto simples conhecida: armado = simples + 100 a 150 kg/m3."""
    assert nbr.massa_especifica_concreto_armado_kg_m3(rho_simples, acrescimo) == pytest.approx(esperado)


@pytest.mark.parametrize("acrescimo", [99.9, 150.1])
def test_massa_especifica_concreto_armado_acrescimo_fora_da_faixa(acrescimo):
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.massa_especifica_concreto_armado_kg_m3(2350.0, acrescimo)


# --- 8.2.3 dilatação térmica do concreto (p. 42) ----------------------------
def test_alfa_termico_concreto():
    assert nbr.ALFA_TERMICO_CONCRETO == pytest.approx(1.0e-5)


# --- 8.2.9 Poisson do concreto (p. 45) e 14.7.3 (p. 116) --------------------
def test_poisson_concreto():
    """nu = 0,2 para tensão de compressão < 0,5*fc e de tração < fct (8.2.9);
    mesmo valor para a teoria da elasticidade aplicada a placas (14.7.3)."""
    assert nbr.POISSON_CONCRETO == 0.2


def test_Gc_ja_usa_2_4_consistente_com_poisson():
    """Gc = Ecs/2,4 já existia; aqui só se confere que continua valendo (8.2.9, p. 45)."""
    assert nbr.Gc(30) == pytest.approx(nbr.Ecs(30) / 2.4)


# --- 8.2.5 fct de ensaios indiretos (p. 42) ---------------------------------
def test_fct_de_ensaio_fct_sp():
    assert nbr.fct_de_ensaio(fct_sp_mpa=3.0) == pytest.approx(0.9 * 3.0)   # 2,7


def test_fct_de_ensaio_fct_f():
    assert nbr.fct_de_ensaio(fct_f_mpa=4.0) == pytest.approx(0.7 * 4.0)   # 2,8


def test_fct_de_ensaio_exige_exatamente_um():
    with pytest.raises(ValueError):
        nbr.fct_de_ensaio()
    with pytest.raises(ValueError):
        nbr.fct_de_ensaio(fct_sp_mpa=3.0, fct_f_mpa=4.0)


# --- 8.2.6 resistência no estado multiaxial de tensões (p. 43) -------------
def test_verificar_tensao_multiaxial_dentro_dos_limites():
    """fck=25: fctk,inf = 0,7*0,3*25^(2/3) = 1,7955 MPa (8.2.5).

    sigma1 = -1,5 MPa >= -1,7955 MPa (ok) e sigma3 = 25 <= fck + 4*sigma1 = 19
    é falso -> escolhe sigma1=0 para não confundir os dois critérios: então
    sigma3_lim = 25 + 0 = 25, e sigma3 = 25 está exatamente no limite.
    """
    fctk = 0.7 * 0.3 * 25 ** (2 / 3)
    r = nbr.verificar_tensao_multiaxial(0.0, 10.0, 25.0, 25.0)
    assert r.fctk_mpa == pytest.approx(fctk)
    assert r.sigma3_lim_mpa == pytest.approx(25.0)
    assert r.ok_compressao is True
    assert r.ok_tracao is True
    assert r.ok is True


def test_verificar_tensao_multiaxial_sigma1_no_limite_de_tracao():
    """sigma1 = -fctk,inf exatamente: ainda ok (>=)."""
    fctk = 0.7 * 0.3 * 25 ** (2 / 3)
    r = nbr.verificar_tensao_multiaxial(-fctk, -fctk, 0.0, 25.0)
    assert r.ok_tracao is True


def test_verificar_tensao_multiaxial_sigma1_viola_tracao():
    """sigma1 = -2 MPa < -fctk,inf (~-1,7955 MPa, fck=25) -> não ok (JSON: 'fctk~1,8MPa')."""
    r = nbr.verificar_tensao_multiaxial(-2.0, -2.0, 0.0, 25.0)
    assert r.ok_tracao is False
    assert r.ok is False
    assert "8.2.6" in r.governante


def test_verificar_tensao_multiaxial_sigma3_no_limite_de_compressao():
    """sigma1=0 -> sigma3_lim = fck = 25; sigma3=25 ok, sigma3=25,1 não."""
    ok = nbr.verificar_tensao_multiaxial(0.0, 0.0, 25.0, 25.0)
    assert ok.ok_compressao is True
    nao_ok = nbr.verificar_tensao_multiaxial(0.0, 0.0, 25.1, 25.0)
    assert nao_ok.ok_compressao is False
    assert nao_ok.ok is False


def test_verificar_tensao_multiaxial_exige_ordem_sigma3_sigma2_sigma1():
    with pytest.raises(ValueError):
        nbr.verificar_tensao_multiaxial(10.0, 0.0, 5.0, 25.0)   # sigma2 < sigma1


# --- 8.2.10.1, Figura 8.3 — diagrama não linear (p. 46) ---------------------
def test_sigma_c_nao_linear_zero_e_negativo():
    assert nbr.sigma_c_nao_linear(0.0, 38.0, 30672.46) == 0.0
    assert nbr.sigma_c_nao_linear(-1.0, 38.0, 30672.46) == 0.0


def test_sigma_c_nao_linear_pico_em_eps_c1_igual_fcm():
    """C30: fcm = 38 MPa; eps_c1 = 0,7*38^0,31 = 2,1619 permil; no pico, sigma_c = fcm."""
    fcm = 38.0
    eci = 5600.0 * math.sqrt(30.0)   # Eci(30)
    eps_c1 = 0.7 * fcm ** 0.31
    assert eps_c1 == pytest.approx(2.1619, abs=1e-3)
    assert nbr.sigma_c_nao_linear(eps_c1, fcm, eci) == pytest.approx(fcm, rel=1e-9)


def test_sigma_c_nao_linear_ponto_interior():
    """Ponto interior eta=0,5 (eps_c = eps_c1/2): sigma_c = fcm*(k*eta-eta^2)/(1+(k-2)*eta)."""
    fcm = 38.0
    eci = 5600.0 * math.sqrt(30.0)
    eps_c1 = 0.7 * fcm ** 0.31
    k = 1.05 * eci * (eps_c1 / 1000.0) / fcm
    eta = 0.5
    esperado = fcm * (k * eta - eta ** 2) / (1.0 + (k - 2.0) * eta)
    assert nbr.sigma_c_nao_linear(eta * eps_c1, fcm, eci) == pytest.approx(esperado, rel=1e-9)


def test_sigma_c_nao_linear_eps_cu1_fck_ate_50_usa_eps_cu():
    """fck=30 (<=50): eps_cu1 = eps_cu(30) = 3,5 permil — vale no limite, falha logo acima."""
    fcm = 38.0
    eci = 5600.0 * math.sqrt(30.0)
    nbr.sigma_c_nao_linear(3.5, fcm, eci)   # não levanta
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.sigma_c_nao_linear(3.5001, fcm, eci)


def test_sigma_c_nao_linear_eps_cu1_fck_acima_de_50():
    """C70: fcm=78; eps_cu1 = 2,8 + 27*[(98-78)/100]^4 = 2,8432 permil."""
    fck, fcm = 70.0, 78.0
    eps_cu1 = 2.8 + 27.0 * ((98.0 - fcm) / 100.0) ** 4
    assert eps_cu1 == pytest.approx(2.8432, abs=1e-4)
    eci = 21.5e3 * (fck / 10.0 + 1.25) ** (1 / 3)
    nbr.sigma_c_nao_linear(eps_cu1, fcm, eci)   # não levanta, está no limite
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.sigma_c_nao_linear(eps_cu1 + 0.01, fcm, eci)


# --- 8.2.10.2, Figura 8.4 — diagrama bilinear de tração (p. 46) -------------
def test_sigma_ct_zero():
    assert nbr.sigma_ct(0.0, 25.0) == 0.0


def test_sigma_ct_primeiro_trecho_elastico():
    """fck=25: Eci=28000 MPa, fctk,inf~1,7955 MPa (JSON usa fctk=1,8; Eci=28000).

    eps a 0,9*fctk: 0,9*1,7955/28000*1000 = 0,05771 permil (JSON arredonda a
    0,0579 com fctk=1,8 exato). No primeiro trecho, sigma = Eci*eps/1000.
    """
    fck = 25.0
    eci = 5600.0 * math.sqrt(fck)
    fctk = 0.7 * 0.3 * fck ** (2 / 3)
    eps_transicao = 0.9 * fctk / eci * 1000.0
    assert eps_transicao == pytest.approx(0.05771, abs=1e-5)
    eps_meio = eps_transicao / 2.0
    assert nbr.sigma_ct(eps_meio, fck) == pytest.approx(eci * eps_meio / 1000.0, rel=1e-9)
    assert nbr.sigma_ct(eps_transicao, fck) == pytest.approx(0.9 * fctk, rel=1e-6)


def test_sigma_ct_segundo_trecho_ate_ponto_final():
    """Depois do cotovelo, reta até (0,15 permil; fctk); em 0,15 permil vale fctk."""
    fck = 25.0
    fctk = 0.7 * 0.3 * fck ** (2 / 3)
    assert nbr.sigma_ct(0.15, fck) == pytest.approx(fctk, rel=1e-9)


def test_sigma_ct_fora_da_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.sigma_ct(-0.001, 25.0)
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.sigma_ct(0.1501, 25.0)


# --- 8.3.3, 8.4.2 massa específica do aço (p. 48, 49) -----------------------
def test_massa_especifica_aco():
    assert nbr.MASSA_ESPECIFICA_ACO_KG_M3 == 7850.0


# --- 8.3.4, 8.4.3 dilatação térmica do aço (p. 48, 50) ----------------------
def test_alfa_termico_aco_valor_fixo():
    assert nbr.ALFA_TERMICO_ACO == pytest.approx(1.0e-5)


@pytest.mark.parametrize("temperatura", [-20.0, 0.0, 150.0])
def test_alfa_termico_aco_passivo_dentro_da_faixa(temperatura):
    assert nbr.alfa_termico_aco("passivo", temperatura) == pytest.approx(1.0e-5)


@pytest.mark.parametrize("temperatura", [-20.1, 150.1])
def test_alfa_termico_aco_passivo_fora_da_faixa(temperatura):
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.alfa_termico_aco("passivo", temperatura)


@pytest.mark.parametrize("temperatura", [-20.0, 0.0, 100.0])
def test_alfa_termico_aco_ativo_dentro_da_faixa(temperatura):
    assert nbr.alfa_termico_aco("ativo", temperatura) == pytest.approx(1.0e-5)


@pytest.mark.parametrize("temperatura", [-20.1, 100.1])
def test_alfa_termico_aco_ativo_fora_da_faixa(temperatura):
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.alfa_termico_aco("ativo", temperatura)


def test_alfa_termico_aco_tipo_desconhecido():
    with pytest.raises(ValueError):
        nbr.alfa_termico_aco("desconhecido", 20.0)


# --- 8.3.7 dutilidade do aço passivo (p. 49) --------------------------------
@pytest.mark.parametrize("categoria, esperado", [
    ("CA-25", "alta"),
    ("CA-50", "alta"),
    ("CA-60", "normal"),
])
def test_dutilidade_aco_passivo(categoria, esperado):
    assert nbr.dutilidade_aco_passivo(categoria) == esperado


def test_dutilidade_aco_passivo_categoria_desconhecida():
    with pytest.raises(ValueError):
        nbr.dutilidade_aco_passivo("CA-70")
