"""Testes do P25 — Pilares: 2ª ordem local pelo pilar-padrão (NBR 6118:2026).

Cobre:
  - 15.3.1, κsec = (EI)sec/(Ac·h²·fcd), PDF p. 122;
  - 15.3.2, envoltória mínima com 2ª ordem (Figura 15.2), PDF p. 122;
  - 15.6, ℓe = menor de (ℓ0 + h, ℓ), PDF p. 125-126; ℓe = 2ℓ em balanço
    (15.8.2, PDF p. 128);
  - 15.7.4, efeitos locais em nós móveis, PDF p. 127;
  - 15.8.1, λ <= 200 (exceção Nd < 0,10·fcd·Ac) e γn1, PDF p. 127;
  - 15.8.2, λ = ℓe/i, PDF p. 127, e λ1, PDF p. 128;
  - 15.8.3.3.2 e 15.8.3.3.3, pilar-padrão, PDF p. 129-130;
  - 15.8.3.3.5, pilar-padrão em flexão oblíqua, PDF p. 131;
  - 15.8.4, excentricidade de fluência ecc, PDF p. 131.

Os valores esperados vêm das imagens das páginas (SCRATCH/nbr_png) e as
contas à mão estão nos comentários.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import pilares_nbr6118 as P  # noqa: E402
from dimensionamento.rotinas import flexao_composta_obliqua as F  # noqa: E402
from dimensionamento.rotinas import verificacao_pilar as VP  # noqa: E402

Erro = P.nbr.FaixaNormativaError

# Exemplo de referência: pilar 20x50, Nd = 1400 kN, C30, ℓe = 280 cm, Ac = 1000 cm²
EX = dict(Nd_kn=1400.0, le_cm=280.0, h_cm=20.0, Ac_cm2=1000.0, fck_mpa=30.0)
ACO = F.Aco()


# ===========================================================================
# 15.3.1 — κsec (PDF p. 122)
# ===========================================================================
def test_1531_kappa_sec_conta_a_mao():
    # κsec = 1e8 / (1000 × 50² × 2,0 kN/cm²) = 1e8 / 5e6 = 20 (fcd = 20 MPa = 2 kN/cm²)
    assert P.kappa_sec(1.0e8, 1000.0, 50.0, 20.0) == pytest.approx(20.0, rel=1e-12)


def test_1531_kappa_sec_reproduz_ei_secante():
    """Identidade: κsec·Ac·h²·fcd = (EI)sec de ei_secante."""
    c = F.Concreto(fck_mpa=30.0)
    s = F.SecaoRetangular(20.0, 50.0, 3.0, F.armadura_perimetral_retangular(20, 50, 3.0, 2, 4, 16.0))
    EI = F.ei_secante(s, c, ACO, 1400.0, 5000.0, "x")
    fcd_mpa = 30.0 / 1.4
    k = P.kappa_sec(EI, s.Ac_cm2, 50.0, fcd_mpa)
    assert k * s.Ac_cm2 * 50.0 ** 2 * (fcd_mpa / 10.0) == pytest.approx(EI, rel=1e-12)


@pytest.mark.parametrize("args", [(0.0, 1000, 50, 20), (1e8, 0.0, 50, 20),
                                  (1e8, 1000, -1, 20), (1e8, 1000, 50, 0.0)])
def test_1531_kappa_sec_entrada_invalida(args):
    with pytest.raises(Erro):
        P.kappa_sec(*args)


# ===========================================================================
# 15.6 — Comprimento equivalente (PDF p. 126) e 15.8.2 balanço (PDF p. 128)
# ===========================================================================
def test_156_le_l0_mais_h_menor_que_l():
    # ℓ0 + h = 250 + 20 = 270 < ℓ = 280 -> ℓe = 270
    assert P.comprimento_equivalente_cm(250.0, 20.0, 280.0) == pytest.approx(270.0)


def test_156_le_l_menor_que_l0_mais_h():
    # ℓ0 + h = 260 + 50 = 310 > ℓ = 280 -> ℓe = 280
    assert P.comprimento_equivalente_cm(260.0, 50.0, 280.0) == pytest.approx(280.0)


def test_156_le_igualdade():
    # ℓ0 + h = 260 + 20 = 280 = ℓ
    assert P.comprimento_equivalente_cm(260.0, 20.0, 280.0) == pytest.approx(280.0)


def test_1582_le_engastado_livre_2l():
    # 15.8.2 (p. 128): pilar engastado na base e livre no topo, ℓe = 2ℓ
    assert P.comprimento_equivalente_cm(250.0, 20.0, 300.0, engastado_livre=True) == pytest.approx(600.0)


@pytest.mark.parametrize("args", [(290.0, 20.0, 280.0), (0.0, 20.0, 280.0),
                                  (250.0, 0.0, 280.0), (250.0, 20.0, 0.0)])
def test_156_le_entrada_invalida(args):
    with pytest.raises(Erro):
        P.comprimento_equivalente_cm(*args)


# ===========================================================================
# 15.8.2 — λ = ℓe/i (PDF p. 127)
# ===========================================================================
def test_1582_lambda_circular():
    # D = 40: i = D/4 = 10 cm; ℓe = 300 -> λ = 30 = 4·ℓe/D
    D = 40.0
    I, A = math.pi * D ** 4 / 64.0, math.pi * D ** 2 / 4.0
    assert P.raio_giracao_cm(I, A) == pytest.approx(10.0, rel=1e-12)
    assert P.esbeltez(300.0, I, A) == pytest.approx(30.0, rel=1e-12)


def test_1582_lambda_retangular_bate_com_346():
    # 20x50, flexão no plano de h = 20: λ = √12·280/20 = 48,4974; a fórmula 3,46·ℓe/h dá 48,44
    I, A = 50.0 * 20.0 ** 3 / 12.0, 1000.0
    lam = P.esbeltez(280.0, I, A)
    assert lam == pytest.approx(math.sqrt(12.0) * 280.0 / 20.0, rel=1e-12)
    assert lam == pytest.approx(P.esbeltez_lambda(280.0, 20.0), rel=2e-3)


def test_1582_lambda_entrada_invalida():
    with pytest.raises(Erro):
        P.esbeltez(0.0, 1.0, 1.0)
    with pytest.raises(Erro):
        P.raio_giracao_cm(-1.0, 1.0)


# ===========================================================================
# 15.8.1 — λ <= 200 e γn1 (PDF p. 127)
# ===========================================================================
# C30, Ac = 1000 cm²: fcd = 30/1,4 = 21,4286 MPa = 2,14286 kN/cm²; 0,10·fcd·Ac = 214,286 kN
N_LIM = 0.10 * (30.0 / 1.4 / 10.0) * 1000.0


def test_1581_lambda_200_aceito():
    r = P.verificar_esbeltez_limite(200.0, 1000.0, 30.0, 1000.0)
    assert r.ok and not r.pouco_comprimido
    assert r.Nd_pouco_comprimido_kn == pytest.approx(N_LIM)
    assert r.gama_n1 == pytest.approx(1.0 + 60.0 / 140.0)
    assert r.exige_metodo_geral and r.exige_fluencia and not r.pilar_padrao_permitido
    assert r.memoria and all(isinstance(m, str) for m in r.memoria)


def test_1581_lambda_acima_200_recusado():
    r = P.verificar_esbeltez_limite(200.01, 1000.0, 30.0, 1000.0)
    assert not r.ok
    assert "não passa" in r.governante


def test_1581_lambda_acima_200_pouco_comprimido_aceito():
    r = P.verificar_esbeltez_limite(250.0, 200.0, 30.0, 1000.0)   # 200 < 214,286
    assert r.ok and r.pouco_comprimido


def test_1581_excecao_estrita_em_0_10_fcd_ac():
    # Nd = 0,10·fcd·Ac exatamente: "menor que" não é atendido
    r = P.verificar_esbeltez_limite(250.0, N_LIM, 30.0, 1000.0)
    assert not r.pouco_comprimido and not r.ok


@pytest.mark.parametrize("lam, fluencia, geral, padrao", [
    (90.0, False, False, True),      # 15.8.3.3.2/3: λ <= 90
    (90.01, True, False, False),     # 15.8.3.1: fluência para λ > 90
    (140.0, True, False, False),     # 15.8.3.2: método geral para λ > 140
    (140.01, True, True, False),
])
def test_1581_faixas_de_lambda(lam, fluencia, geral, padrao):
    r = P.verificar_esbeltez_limite(lam, 1000.0, 30.0, 1000.0)
    assert (r.exige_fluencia, r.exige_metodo_geral, r.pilar_padrao_permitido) == (fluencia, geral, padrao)


@pytest.mark.parametrize("lam, esperado", [
    (0.0, 1.0), (140.0, 1.0),                 # λ <= 140 -> 1,0
    (140.01, 1.0 + 0.01 / 140.0),
    (175.0, 1.25),                            # 1 + 35/140
    (200.0, 1.0 + 60.0 / 140.0),              # 1,428571
    (280.0, 2.0),                             # 1 + 140/140
])
def test_1581_gama_n1(lam, esperado):
    assert P.gama_n1(lam) == pytest.approx(esperado, rel=1e-12)


def test_1581_aplicar_gama_n1_majora_so_a_2a_ordem():
    # λ = 175: γn1 = 1,25; M2d = 1000 -> 1250
    assert P.aplicar_gama_n1(1000.0, 175.0) == pytest.approx((1250.0, 1.25))
    assert P.aplicar_gama_n1(1000.0, 140.0) == pytest.approx((1000.0, 1.0))


def test_1581_gama_n1_integrado_ao_pilar_padrao():
    """No pilar-padrão (λ <= 90) γn1 = 1 e o M2d entra sem majoração."""
    r = P.pilar_padrao_direcao(MA_kncm=0.0, MB_kncm=0.0, verificar_dispensa=False, **EX)
    assert r.gama_n1 == 1.0
    assert r.M2d_kncm == pytest.approx(2379.19, abs=0.05)


def test_1581_entrada_invalida():
    with pytest.raises(Erro):
        P.gama_n1(-1.0)
    with pytest.raises(Erro):
        P.verificar_esbeltez_limite(float("nan"), 1000.0, 30.0, 1000.0)


@pytest.mark.parametrize("Nd", [-500.0, 0.0, float("nan"), float("inf")])
def test_1581_nd_nao_comprimido_recusado(Nd):
    """15.8.1 (PDF p. 127): a exceção a λ <= 200 é para elementos "pouco
    comprimidos"; tração (Nd < 0) ou Nd nulo não pode admitir λ = 300."""
    with pytest.raises(Erro):
        P.verificar_esbeltez_limite(300.0, Nd, 30.0, 1000.0)


# ===========================================================================
# 15.8.4 — Fluência (PDF p. 131)
# ===========================================================================
def test_1584_ne_conta_a_mao():
    # Ne = 10·Eci·Ic/ℓe² = 10 × 3000 kN/cm² × 1e5 cm⁴ / 500² = 12 000 kN
    assert P.carga_euler_Ne_kn(30000.0, 1.0e5, 500.0) == pytest.approx(12000.0, rel=1e-12)


def test_1584_ecc_conta_a_mao():
    # Msg = 1000 kN·cm, Nsg = 500 kN, ea = 1 cm, φ = 2, Ne = 12 000 kN
    # expoente = 2 × 500/(12 000 − 500) = 0,0869565
    # ecc = (1000/500 + 1)·(e^0,0869565 − 1) = 3 × 0,0908490 = 0,272548 cm
    ecc = P.ecc_fluencia_cm(1000.0, 500.0, 1.0, 2.0, 30000.0, 1.0e5, 500.0)
    assert ecc == pytest.approx(3.0 * (math.exp(1000.0 / 11500.0) - 1.0), rel=1e-12)
    assert ecc == pytest.approx(0.272548, abs=1e-6)
    # com a base 2,718 impressa na norma a diferença é de ~1,1e-4 (relativa): desprezível
    assert ecc == pytest.approx(3.0 * (2.718 ** (1000.0 / 11500.0) - 1.0), rel=2e-4)


def test_1584_ecc_phi_zero_e_nulo():
    assert P.ecc_fluencia_cm(1000.0, 500.0, 1.0, 0.0, 30000.0, 1.0e5, 500.0) == 0.0


def test_1584_ecc_sinal_de_msg_nao_reduz():
    a = P.ecc_fluencia_cm(1000.0, 500.0, 1.0, 2.0, 30000.0, 1.0e5, 500.0)
    b = P.ecc_fluencia_cm(-1000.0, 500.0, 1.0, 2.0, 30000.0, 1.0e5, 500.0)
    assert a == pytest.approx(b)


def test_1584_ecc_diverge_perto_de_ne():
    # Nsg -> Ne: o expoente cresce sem limite
    # Nsg = 11 900: expoente = 2 × 11 900/100 = 238 -> ecc ≈ (0,084 + 1)·e^238 > 1e100
    perto = P.ecc_fluencia_cm(1000.0, 11900.0, 1.0, 2.0, 30000.0, 1.0e5, 500.0)
    assert perto > 1.0e100
    with pytest.raises(Erro):   # Nsg = 11 999: e^23 998 não é representável
        P.ecc_fluencia_cm(1000.0, 11999.0, 1.0, 2.0, 30000.0, 1.0e5, 500.0)
    with pytest.raises(Erro):
        P.ecc_fluencia_cm(1000.0, 12000.0, 1.0, 2.0, 30000.0, 1.0e5, 500.0)   # Nsg = Ne
    with pytest.raises(Erro):
        P.ecc_fluencia_cm(1000.0, 13000.0, 1.0, 2.0, 30000.0, 1.0e5, 500.0)   # Nsg > Ne


@pytest.mark.parametrize("kw", [dict(Nsg_kn=0.0), dict(Nsg_kn=-10.0), dict(phi=-0.1), dict(ea_cm=-1.0),
                                dict(Ic_cm4=0.0), dict(le_cm=0.0), dict(Eci_mpa=0.0)])
def test_1584_ecc_entrada_invalida(kw):
    base = dict(Msg_kncm=1000.0, Nsg_kn=500.0, ea_cm=1.0, phi=2.0, Eci_mpa=30000.0, Ic_cm4=1.0e5, le_cm=500.0)
    base.update(kw)
    with pytest.raises(Erro):
        P.ecc_fluencia_cm(**base)


def test_1584_ecc_com_phi_da_tabela_8_1():
    """φ pela Tabela 8.1 do núcleo (U = 75 %, h_fic = 20 cm, t0 = 30 dias, C30)."""
    phi, _ = P.nbr.phi_eps_cs_NBR(75.0, 20.0, 30.0, 30.0)
    Eci = P.nbr.Eci(30.0)
    ecc = P.ecc_fluencia_cm(1000.0, 500.0, 1.0, phi, Eci, 1.0e5, 500.0)
    Ne = 10.0 * Eci / 10.0 * 1.0e5 / 500.0 ** 2
    assert ecc == pytest.approx(3.0 * (math.exp(phi * 500.0 / (Ne - 500.0)) - 1.0), rel=1e-12)


# ===========================================================================
# 15.8.3.3.2 e 15.8.3.3.3 — pilar-padrão numa direção (PDF p. 129-130)
# ===========================================================================
@pytest.mark.parametrize("MA, MB, ab", [(0.0, 0.0, 1.0), (500.0, 200.0, 1.0), (5000.0, 2500.0, 0.8),
                                        (8000.0, -8000.0, 0.4)])
def test_15833_direcao_reproduz_funcoes_existentes(MA, MB, ab):
    """Com o mínimo aplicado e sem dispensa, o resultado é o de Mdtot_*_aprox."""
    rc = P.pilar_padrao_direcao(MA_kncm=MA, MB_kncm=MB, metodo="curvatura", verificar_dispensa=False, **EX)
    rr = P.pilar_padrao_direcao(MA_kncm=MA, MB_kncm=MB, metodo="rigidez", verificar_dispensa=False, **EX)
    kw = dict(Nd_kn=1400.0, le_cm=280.0, h_cm=20.0, fck_mpa=30.0, Ac_cm2=1000.0,
              M1d_A_kncm=MA, alpha_b_val=ab)
    assert rc.Md_tot_kncm == pytest.approx(P.Mdtot_curvatura_aprox(**kw)["Md_tot_kncm"], rel=1e-12)
    assert rr.Md_tot_kncm == pytest.approx(P.Mdtot_rigidez_aprox(**kw)["Md_tot_kncm"], rel=1e-12)
    assert rr.kappa == pytest.approx(P.Mdtot_rigidez_aprox(**kw)["kappa_aprox"], rel=1e-12)


def test_15833_valores_do_exemplo():
    # Curvatura: 2940 + 1400·280²/10·0,005/(20·1,15333) = 2940 + 2379,19 = 5319,19
    # Rigidez: a = 100, b = 400·1400 − 1400·78400/320 − 100·2940 = −77 000,
    #          c = −1400·400·2940 = −1,6464e9 -> Md,tot = 4460,81
    assert P.momento_total_minimo_direcao(1400.0, 280.0, 20.0, 1000.0, 30.0).Md_tot_kncm == \
        pytest.approx(5319.19, abs=0.01)
    assert P.momento_total_minimo_direcao(1400.0, 280.0, 20.0, 1000.0, 30.0, "rigidez").Md_tot_kncm == \
        pytest.approx(4460.81, abs=0.01)


def test_1582_dispensa_pelos_dois_lados_de_lambda1():
    # λ = 3,46·280/20 = 48,44; αb = 1 (MB = MA); λ1 = 25 + 12,5·e1/20
    # e1 = 37,6 -> λ1 = 48,5 > λ: dispensa; e1 = 37,4 -> λ1 = 48,375 < λ: calcula 2ª ordem
    Nd = 1400.0
    r1 = P.pilar_padrao_direcao(MA_kncm=37.6 * Nd, MB_kncm=37.6 * Nd, **EX)
    assert r1.lambda1 == pytest.approx(48.5)
    assert r1.dispensa_2a_ordem and r1.M2d_kncm == 0.0
    assert r1.Md_tot_kncm == pytest.approx(37.6 * Nd)
    r2 = P.pilar_padrao_direcao(MA_kncm=37.4 * Nd, MB_kncm=37.4 * Nd, **EX)
    assert r2.lambda1 == pytest.approx(48.375)
    assert not r2.dispensa_2a_ordem and r2.M2d_kncm > 0.0
    assert r2.Md_tot_kncm == pytest.approx(37.4 * Nd + r2.M2d_kncm)


def test_15833_sem_minimo_para_flexao_obliqua():
    # MA = 0 e sem mínimo: curvatura -> Md,tot = M2d = 2379,19; rigidez -> 0 (b > 0, c = 0)
    rc = P.pilar_padrao_direcao(MA_kncm=0.0, MB_kncm=0.0, aplicar_minimo=False, verificar_dispensa=False, **EX)
    assert rc.Md_tot_kncm == pytest.approx(2379.19, abs=0.01)
    rr = P.pilar_padrao_direcao(MA_kncm=0.0, MB_kncm=0.0, metodo="rigidez", aplicar_minimo=False,
                                verificar_dispensa=False, **EX)
    assert rr.Md_tot_kncm == pytest.approx(0.0, abs=1e-9)


def test_15833_ma_e_o_maior_em_valor_absoluto_e_da_o_sinal():
    r = P.pilar_padrao_direcao(MA_kncm=2000.0, MB_kncm=-6000.0, **EX)
    assert r.MA_kncm == -6000.0 and r.MB_kncm == 2000.0 and r.sinal == -1.0
    # αb = 0,6 + 0,4·(2000/−6000) = 0,4667
    assert r.alpha_b == pytest.approx(0.6 - 0.4 / 3.0)


def test_15833_lambda_90_na_fronteira_e_acima():
    le90 = 90.0 * 20.0 / 3.46
    r = P.pilar_padrao_direcao(1400.0, le90, 20.0, 1000.0, 30.0, 0.0, 0.0)
    assert r.lambda_ == pytest.approx(90.0)
    with pytest.raises(Erro):
        P.pilar_padrao_direcao(1400.0, le90 * 1.001, 20.0, 1000.0, 30.0, 0.0, 0.0)


def test_15833_entrada_invalida():
    with pytest.raises(Erro):
        P.pilar_padrao_direcao(0.0, 280.0, 20.0, 1000.0, 30.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        P.pilar_padrao_direcao(MA_kncm=0.0, MB_kncm=0.0, metodo="geral", **EX)


# ===========================================================================
# 15.7.4 — Nós móveis (PDF p. 127)
# ===========================================================================
def test_1574_nos_fixos_coincide_com_caminho_normal():
    # MA = 5000, MB = 2500 -> αb = 0,8; e1 = 3,571 cm; λ1 = (25 + 2,232)/0,8 = 34,04 -> 35 < 48,44
    r = P.efeitos_locais_nos_moveis(1400.0, 280.0, 20.0, 1000.0, 30.0, 5000.0, 2500.0)
    esperado = P.Mdtot_curvatura_aprox(1400.0, 280.0, 20.0, 30.0, 5000.0, 0.8, 1000.0)["Md_tot_kncm"]
    assert r.Md_tot_kncm == pytest.approx(esperado, rel=1e-12)
    assert r.memoria[0].startswith("15.7.4")


def test_1574_momentos_da_analise_global_entram_como_ma_mb():
    # Momentos maiores da 2ª ordem global aumentam Md,tot pela mesma regra
    r1 = P.efeitos_locais_nos_moveis(1400.0, 280.0, 20.0, 1000.0, 30.0, 5000.0, 2500.0, metodo="rigidez")
    r2 = P.efeitos_locais_nos_moveis(1400.0, 280.0, 20.0, 1000.0, 30.0, 6000.0, 3000.0, metodo="rigidez")
    assert r2.Md_tot_kncm > r1.Md_tot_kncm
    esperado = P.Mdtot_rigidez_aprox(1400.0, 280.0, 20.0, 30.0, 6000.0, 0.8, 1000.0)["Md_tot_kncm"]
    assert r2.Md_tot_kncm == pytest.approx(esperado, rel=1e-12)


# ===========================================================================
# 15.3.2 — Envoltória mínima com 2ª ordem (PDF p. 122)
# ===========================================================================
C30 = F.Concreto(fck_mpa=30.0)
SEC_40 = F.SecaoRetangular(40.0, 40.0, 3.0, F.armadura_perimetral_retangular(40, 40, 3.0, 3, 3, 16.0))
SEC_20x50 = F.SecaoRetangular(20.0, 50.0, 3.0, F.armadura_perimetral_retangular(20, 50, 3.0, 2, 4, 16.0))


def test_1532_semi_eixos_calculados_pelo_pilar_padrao():
    r = VP.verificar_envoltoria_minima_2a_ordem(SEC_20x50, C30, ACO, 1400.0, 280.0)
    # xx: h = 50, λ = 19,376: 4200 + 1400·280²/10·0,005/(50·1,15333) = 4200 + 951,68 = 5151,68
    # yy: h = 20: 2940 + 2379,19 = 5319,19
    assert r.Md_tot_min_xx_kncm == pytest.approx(4200.0 + 1400.0 * 7840.0 * 0.005 / (50.0 * (1400.0 / (1000.0 * 30.0 / 14.0) + 0.5)), rel=1e-12)
    assert r.Md_tot_min_yy_kncm == pytest.approx(5319.19, abs=0.01)
    ref = VP.verificar_envoltoria_minima(SEC_20x50, C30, ACO, 1400.0,
                                         Md_tot_min_xx_kncm=r.Md_tot_min_xx_kncm,
                                         Md_tot_min_yy_kncm=r.Md_tot_min_yy_kncm)
    assert r.razao_min == pytest.approx(ref["razao_min"], rel=1e-12)
    assert r.status == ref["status"] and r.ok == (ref["status"] == "OK")


def test_1532_caso_simetrico():
    """Seção quadrada, mesmo ℓe: Md,tot,mín,xx = Md,tot,mín,yy (a elipse vira círculo)."""
    r = VP.verificar_envoltoria_minima_2a_ordem(SEC_40, C30, ACO, 1500.0, 400.0)
    assert r.Md_tot_min_xx_kncm == pytest.approx(r.Md_tot_min_yy_kncm, rel=1e-12)
    for mx, my in VP.envoltoria_minima(1500.0, 40.0, 40.0, 16, r.Md_tot_min_xx_kncm, r.Md_tot_min_yy_kncm):
        assert mx ** 2 + my ** 2 == pytest.approx(r.Md_tot_min_xx_kncm ** 2)


def test_1532_direcao_sem_2a_ordem_fica_com_minimo():
    r = VP.verificar_envoltoria_minima_2a_ordem(SEC_20x50, C30, ACO, 1400.0, 280.0, segunda_ordem_xx=False)
    assert r.Md_tot_min_xx_kncm == pytest.approx(4200.0)     # 1400·(1,5 + 0,03·50)
    assert r.direcao_xx is None
    assert any("sem 2ª ordem" in m for m in r.memoria)


def test_1532_nao_verifica_com_nd_alto():
    r = VP.verificar_envoltoria_minima_2a_ordem(SEC_20x50, C30, ACO, 2100.0, 280.0)
    assert not r.ok and r.status == "NAO_VERIFICA"
    assert "NAO_VERIFICA" in r.governante


def test_1532_secao_nao_retangular_recusada():
    with pytest.raises(TypeError):
        VP.verificar_envoltoria_minima_2a_ordem(object(), C30, ACO, 1400.0, 280.0)


# ===========================================================================
# 15.8.3.3.5 — Pilar-padrão em flexão oblíqua (PDF p. 131)
# ===========================================================================
def test_158335_simetrico_nas_duas_direcoes():
    r = VP.pilar_padrao_obliquo(SEC_40, C30, ACO, 1500.0, 400.0, 400.0,
                                3000.0, -1500.0, 3000.0, -1500.0)
    assert r.direcao_xx.Md_tot_kncm == pytest.approx(r.direcao_yy.Md_tot_kncm, rel=1e-12)
    # cada direção é o pilar-padrão isolado, sem o mínimo (verificado pela envoltória)
    iso = P.pilar_padrao_direcao(1500.0, 400.0, 40.0, 1600.0, 30.0, 3000.0, -1500.0, aplicar_minimo=False)
    assert r.direcao_xx.Md_tot_kncm == pytest.approx(iso.Md_tot_kncm, rel=1e-12)
    nomes = [s["secao"] for s in r.secoes]
    assert nomes == ["A (topo)", "intermediária", "B (base)"]
    inter = r.secoes[1]
    assert inter["Mx_kncm"] == pytest.approx(iso.Md_tot_kncm) and inter["My_kncm"] == pytest.approx(iso.Md_tot_kncm)
    direto = F.verificar_fco(SEC_40, C30, ACO, 1500.0, inter["Mx_kncm"], inter["My_kncm"], 80)
    assert inter["razao"] == pytest.approx(direto["razao"], rel=1e-6)
    assert r.envoltoria_minima is not None
    assert r.ok == (r.status == "OK")


def test_158335_extremos_usam_momentos_de_1a_ordem():
    r = VP.pilar_padrao_obliquo(SEC_20x50, C30, ACO, 1400.0, 280.0, 280.0,
                                2000.0, -1000.0, 1500.0, 500.0, aplicar_gama_n=False)
    a, _, b = r.secoes
    assert (a["Mx_kncm"], a["My_kncm"]) == (2000.0, 1500.0)
    assert (b["Mx_kncm"], b["My_kncm"]) == (-1000.0, 500.0)
    # xx: λ = 19,4 < λ1 -> dispensa; intermediária com M1d,A = 2000
    assert r.direcao_xx.dispensa_2a_ordem
    assert r.secoes[1]["Mx_kncm"] == pytest.approx(2000.0)
    # yy: 2ª ordem calculada, logo a envoltória mínima tem 2ª ordem só em yy
    assert not r.direcao_yy.dispensa_2a_ordem
    assert r.envoltoria_minima.direcao_xx is None and r.envoltoria_minima.direcao_yy is not None


def test_158335_gama_n_de_pilar_fino():
    # b = 18 cm: γn = 1,95 − 0,05 × 18 = 1,05 (13.2.3, Tabela 13.1)
    s = F.SecaoRetangular(18.0, 40.0, 3.0, F.armadura_perimetral_retangular(18, 40, 3.0, 2, 3, 16.0))
    r = VP.pilar_padrao_obliquo(s, C30, ACO, 600.0, 250.0, 250.0, 1000.0, 1000.0, 500.0, 500.0)
    assert r.gama_n == pytest.approx(1.05)
    assert r.Nd_kn == pytest.approx(630.0)
    assert r.secoes[0]["Mx_kncm"] == pytest.approx(1050.0)
    assert any("γn = 1,05" in m for m in r.memoria)


def test_158335_nao_verifica_com_momentos_altos():
    r = VP.pilar_padrao_obliquo(SEC_20x50, C30, ACO, 1400.0, 280.0, 280.0,
                                20000.0, 20000.0, 8000.0, 8000.0, verificar_minimo=False)
    assert not r.ok and r.status == "NAO_VERIFICA"
    assert r.envoltoria_minima is None
    assert any("não verificada" in m for m in r.memoria)


def test_158335_lambda_acima_de_90_numa_direcao():
    with pytest.raises(Erro):
        VP.pilar_padrao_obliquo(SEC_20x50, C30, ACO, 1400.0, 280.0, 600.0, 0.0, 0.0, 0.0, 0.0)
