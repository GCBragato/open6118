"""P6 — Fluência e retração: motor do Anexo A (tempo_concreto_nbr6118.py).

Valores esperados tirados das imagens da NBR 6118:2026 (PDF p. 234 a 240 e
p. 47 para a Tabela 8.1). Quando o esperado depende de conta, a conta está no
comentário do teste.
"""

import dataclasses
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import protendido_nbr6118 as PT  # noqa: E402
import tempo_concreto_nbr6118 as tc  # noqa: E402

Erro = nbr.FaixaNormativaError

# ---------------------------------------------------------------------------
# Tabela A.1 (A.2.3.2, PDF p. 237) — todas as células
# ---------------------------------------------------------------------------
# (ambiente, abatimento representativo, φ1c, 10⁴·ε1s)
CELULAS_A_1 = [
    ("agua", 2.0, 0.6, 1.0), ("agua", 7.0, 0.8, 1.0), ("agua", 12.0, 1.0, 1.0),
    ("muito_umido", 2.0, 1.0, -1.9), ("muito_umido", 7.0, 1.3, -2.5),
    ("muito_umido", 12.0, 1.6, -3.1),
    ("ar_livre", 2.0, 1.5, -3.8), ("ar_livre", 7.0, 2.0, -5.0),
    ("ar_livre", 12.0, 2.5, -6.2),
    ("seco", 2.0, 2.3, -4.7), ("seco", 7.0, 3.0, -6.3), ("seco", 12.0, 3.8, -7.9),
]


@pytest.mark.parametrize("amb, abat, phi1c, eps_1e4", CELULAS_A_1)
def test_tabela_A1_celulas_phi1c_eps1s(amb, abat, phi1c, eps_1e4):
    # Tabela A.1, PDF p. 237. ε1s em ‰ = 10⁴·ε1s / 10.
    assert tc.phi1c_tabela(amb, abat) == pytest.approx(phi1c)
    assert tc.eps1s_tabela_pmil(amb, abat) == pytest.approx(eps_1e4 / 10.0)


@pytest.mark.parametrize("amb, gama", [("agua", 30.0), ("muito_umido", 5.0),
                                       ("ar_livre", 1.5), ("seco", 1.0)])
def test_tabela_A1_celulas_gama(amb, gama):
    # Tabela A.1, coluna γ, PDF p. 237.
    assert tc.gama_tabela(amb) == pytest.approx(gama)


@pytest.mark.parametrize("rotulo, chave", [("Na água", "agua"), ("muito úmido", "muito_umido"),
                                           ("Ao ar livre", "ar_livre"), ("Em ambiente seco", "seco")])
def test_tabela_A1_rotulos_de_ambiente(rotulo, chave):
    assert tc.gama_tabela(rotulo) == tc.gama_tabela(chave)


def test_tabela_A1_ambiente_desconhecido():
    with pytest.raises(ValueError):
        tc.gama_tabela("deserto")


TABELA_AR_LIVRE = (1.5, 2.0, 2.5)


@pytest.mark.parametrize("abat, coluna", [(0.0, 0), (4.0, 0), (4.9, 0), (5.0, 1), (9.0, 1),
                                          (9.9, 1), (10.0, 2), (15.0, 2)])
def test_tabela_A1_faixas_de_abatimento(abat, coluna):
    # Colunas 0–4, 5–9 e 10–15 cm; o vão entre faixas vai para a faixa de baixo.
    assert tc.phi1c_tabela("ar_livre", abat) == TABELA_AR_LIVRE[coluna]



@pytest.mark.parametrize("abat", [-0.1, 15.1, 20.0])
def test_tabela_A1_abatimento_fora_da_tabela_levanta(abat):
    with pytest.raises(Erro):
        tc.phi1c_tabela("seco", abat)
    with pytest.raises(Erro):
        tc.phi1c(70.0, abat)


# ---------------------------------------------------------------------------
# Tabela A.1, nota c — colunas 0–4 e 10–15 = ×0,75 e ×1,25 da coluna 5–9
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("amb", ["muito_umido", "ar_livre", "seco"])
def test_tabela_A1_nota_c_reproduz_as_colunas(amb):
    # Ex.: seco, ε1s: 0,75·(−6,3) = −4,725 → −4,7; 1,25·(−6,3) = −7,875 → −7,9.
    # A tabela está arredondada a uma casa: diferença <= 0,05.
    linha = tc.TABELA_A_1[amb]
    for campo in ("phi1c", "eps1s_1e4"):
        baixo, meio, alto = linha[campo]
        assert baixo == pytest.approx(0.75 * meio, abs=0.05 + 1e-9)
        assert alto == pytest.approx(1.25 * meio, abs=0.05 + 1e-9)


def test_tabela_A1_nota_c_nao_vale_na_agua():
    # Na água (U > 90 %) a retração é +1,0 nas três colunas (nota c só para U <= 90 %).
    assert tc.TABELA_A_1["agua"]["eps1s_1e4"] == (1.0, 1.0, 1.0)


# ---------------------------------------------------------------------------
# Tabela A.1, nota a — φ1c = 4,45 − 0,035·U
# ---------------------------------------------------------------------------
def test_nota_a_valores_exatos():
    # U = 90: 4,45 − 3,15 = 1,30 (linha “muito úmido”, 5–9 cm);
    # U = 70: 4,45 − 2,45 = 2,00 (linha “ao ar livre”); U = 40: 4,45 − 1,40 = 3,05.
    assert tc.phi1c(90.0) == pytest.approx(1.30)
    assert tc.phi1c(70.0) == pytest.approx(2.00)
    assert tc.phi1c(40.0) == pytest.approx(3.05)
    # Nota c: 0,75·2,00 = 1,50 e 1,25·2,00 = 2,50.
    assert tc.phi1c(70.0, 3.0) == pytest.approx(1.50)
    assert tc.phi1c(70.0, 12.0) == pytest.approx(2.50)


@pytest.mark.parametrize("amb", ["muito_umido", "ar_livre", "seco"])
@pytest.mark.parametrize("abat", [2.0, 7.0, 12.0])
def test_nota_a_continuidade_com_a_tabela(amb, abat):
    # Maior diferença: seco, 5–9 cm, 3,05 contra 3,0 (arredondamento da tabela).
    U = tc.TABELA_A_1[amb]["U_pct"]
    assert tc.phi1c(U, abat) == pytest.approx(tc.phi1c_tabela(amb, abat), abs=0.05 + 1e-9)


@pytest.mark.parametrize("U", [-0.1, 90.1, 100.0])
def test_nota_a_fora_da_faixa(U):
    with pytest.raises(Erro):
        tc.phi1c(U)


def test_nota_a_bordas_da_faixa():
    assert tc.phi1c(0.0) == pytest.approx(4.45)
    assert tc.phi1c(90.0) == pytest.approx(1.30)


# ---------------------------------------------------------------------------
# Tabela A.1, nota b — 10⁴·ε1s polinomial em U
# ---------------------------------------------------------------------------
def test_nota_b_valores_calculados():
    # U = 40: −8,09 + 2,666667 − 0,700525 − 0,478451 + 0,336481 = −6,265828
    # U = 70: −8,09 + 4,666667 − 2,145359 − 2,564198 + 3,155826 = −4,977064
    # U = 90: −8,09 + 6,000000 − 3,546410 − 5,449856 + 8,623647 = −2,462619
    assert tc.eps1s_1e4(40.0) == pytest.approx(-6.265828, abs=1e-5)
    assert tc.eps1s_1e4(70.0) == pytest.approx(-4.977064, abs=1e-5)
    assert tc.eps1s_1e4(90.0) == pytest.approx(-2.462619, abs=1e-5)
    assert tc.eps1s_pmil(70.0) == pytest.approx(-0.4977064, abs=1e-6)


@pytest.mark.parametrize("amb", ["muito_umido", "ar_livre", "seco"])
@pytest.mark.parametrize("abat", [2.0, 7.0, 12.0])
def test_nota_b_continuidade_com_a_tabela(amb, abat):
    # Coluna 5–9: diferença <= 0,05 (maior: U = 90, −2,463 contra −2,5).
    # Colunas 0–4 e 10–15: a tabela arredonda 0,75 e 1,25 vezes a coluna 5–9,
    # então a folga cresce para 1,25·0,05 + 0,01 = 0,0725
    # (maior: ar livre, 0,75·(−4,977) = −3,733 contra −3,8).
    U = tc.TABELA_A_1[amb]["U_pct"]
    tol = 0.05 + 1e-9 if abat == 7.0 else 0.0725
    assert tc.eps1s_1e4(U, abat) == pytest.approx(
        10.0 * tc.eps1s_tabela_pmil(amb, abat), abs=tol)


@pytest.mark.parametrize("U", [39.9, 90.1, 20.0])
def test_nota_b_fora_da_faixa(U):
    with pytest.raises(Erro):
        tc.eps1s_1e4(U)


# ---------------------------------------------------------------------------
# Tabela A.1, nota d — γ = 1 + exp(−7,8 + 0,1·U)
# ---------------------------------------------------------------------------
def test_nota_d_valores():
    # U = 40: 1 + e^−3,8 = 1,022371; U = 70: 1 + e^−0,8 = 1,449329;
    # U = 90: 1 + e^1,2 = 4,320117 (a tabela dá 5,0 para “muito úmido”).
    assert tc.gama_umidade(40.0) == pytest.approx(1.022371, abs=1e-6)
    assert tc.gama_umidade(70.0) == pytest.approx(1.449329, abs=1e-6)
    assert tc.gama_umidade(90.0) == pytest.approx(4.320117, abs=1e-6)
    assert tc.gama_umidade(0.0) == pytest.approx(1.0 + math.exp(-7.8))


def test_nota_d_fora_da_faixa():
    with pytest.raises(Erro):
        tc.gama_umidade(90.1)


# ---------------------------------------------------------------------------
# Tabela A.2 e idade fictícia (A.2.4.1, PDF p. 239)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cimento, alfa_flu", [
    ("CP III", 1.0), ("CP IV", 1.0), ("CP I", 2.0), ("CP I-S", 2.0), ("CP II-E", 2.0),
    ("CP II-F", 2.0), ("CP II-Z", 2.0), ("CP V-ARI", 3.0), ("CP V-ARI RS", 3.0),
    ("lento", 1.0), ("normal", 2.0), ("rapido", 3.0),
])
def test_tabela_A2_todas_as_celulas(cimento, alfa_flu):
    assert tc.alfa_cimento(cimento, "fluencia") == alfa_flu
    assert tc.alfa_cimento(cimento, "retração") == 1.0


def test_tabela_A2_entradas_invalidas():
    with pytest.raises(ValueError):
        tc.alfa_cimento("CP VI")
    with pytest.raises(ValueError):
        tc.alfa_cimento("CPII", "dilatacao")


def test_idade_ficticia_20C_constante():
    # (20 + 10)/30 = 1: t = α·tef. CP II na fluência: 2·28 = 56; na retração: 28.
    assert tc.idade_ficticia_dias([(20.0, 28.0)], "CPII") == pytest.approx(56.0)
    assert tc.idade_ficticia_dias([(20.0, 28.0)], "CPII", "retracao") == pytest.approx(28.0)


def test_idade_ficticia_historico_variavel():
    # CP III (α = 1): (5 + 10)/30·10 + (20 + 10)/30·18 + (35 + 10)/30·2 = 5 + 18 + 3 = 26.
    hist = [(5.0, 10.0), (20.0, 18.0), (35.0, 2.0)]
    assert tc.idade_ficticia_dias(hist, "CP III") == pytest.approx(26.0)
    # CP V-ARI (α = 3) na fluência: 3·26 = 78.
    assert tc.idade_ficticia_dias(hist, "CP V-ARI") == pytest.approx(78.0)


def test_idade_ficticia_limites():
    # T = −9,9 °C ainda contribui: (0,1/30)·30 = 0,1 dia com α = 1.
    assert tc.idade_ficticia_dias([(-9.9, 30.0)], "CPIV") == pytest.approx(0.1)
    with pytest.raises(Erro):
        tc.idade_ficticia_dias([(-10.0, 30.0)], "CPIV")
    with pytest.raises(ValueError):
        tc.idade_ficticia_dias([], "CPIV")
    with pytest.raises(ValueError):
        tc.idade_ficticia_dias([(20.0, -1.0)], "CPIV")


# ---------------------------------------------------------------------------
# Espessura fictícia (A.2.4.2, PDF p. 240) e a promoção de h_ficticia_cm
# ---------------------------------------------------------------------------
def test_espessura_ficticia():
    # Viga 30×60 com 150 cm de perímetro exposto: 2·1 800/150 = 24 cm.
    assert tc.espessura_ficticia_cm(1800.0, 150.0) == pytest.approx(24.0)
    # Ponderada: ao ar livre (tabela) 1,5·24 = 36 cm; U = 70 % (nota d) 1,449329·24.
    assert tc.espessura_ficticia_ponderada_cm(1800.0, 150.0, ambiente="ar_livre") == pytest.approx(36.0)
    assert tc.espessura_ficticia_ponderada_cm(1800.0, 150.0, U_pct=70.0) == pytest.approx(
        1.449329 * 24.0, abs=1e-4)


def test_espessura_ficticia_entradas_invalidas():
    with pytest.raises(ValueError):
        tc.espessura_ficticia_cm(0.0, 150.0)
    with pytest.raises(ValueError):
        tc.espessura_ficticia_ponderada_cm(1800.0, 150.0)  # nem U nem ambiente
    with pytest.raises(ValueError):
        tc.espessura_ficticia_ponderada_cm(1800.0, 150.0, U_pct=70.0, ambiente="seco")


def test_h_ficticia_do_protendido_delega():
    assert PT.h_ficticia_cm(1800.0, 150.0) == pytest.approx(24.0)
    assert PT.h_ficticia_cm(1800.0, 150.0, gama_humid=1.5) == pytest.approx(36.0)


# ---------------------------------------------------------------------------
# φ2c e ε2s (h em cm) — A.2.2.3, PDF p. 235, e A.2.3.2, PDF p. 237
# ---------------------------------------------------------------------------
def test_phi2c():
    # h = 20 cm: 62/40 = 1,55; h → 0: 42/20 = 2,1; h grande → 1.
    assert tc.phi2c(20.0) == pytest.approx(1.55)
    assert tc.phi2c(1e-9) == pytest.approx(2.1)
    assert tc.phi2c(1e9) == pytest.approx(1.0, abs=1e-6)
    with pytest.raises(Erro):
        tc.phi2c(0.0)


def test_eps2s():
    # h = 20 cm: 73/80,8 = 0,903465; h → 0: 33/20,8; h grande → 2/3.
    assert tc.eps2s(20.0) == pytest.approx(73.0 / 80.8)
    assert tc.eps2s(1e-9) == pytest.approx(33.0 / 20.8)
    assert tc.eps2s(1e9) == pytest.approx(2.0 / 3.0, abs=1e-6)
    with pytest.raises(Erro):
        tc.eps2s(-1.0)


# ---------------------------------------------------------------------------
# βf(t) e βs(t) (h em m) — A.2.2.3, PDF p. 235, e A.2.3.2, PDF p. 238
# ---------------------------------------------------------------------------
def test_beta_f_calculo_a_mao_h_20cm():
    # h = 0,20 m: A = 0,336 − 14 + 117,6 + 113 = 216,936
    # B = 6,144 − 122,4 + 646,8 − 23 = 507,544
    # C = −1,6 + 0,52 + 218 + 183 = 399,92
    # D = 60,632 − 1 276,64 + 7 068,6 + 1 931 = 7 783,592
    # βf(100) = (10 000 + 21 693,6 + 507,544)/(10 000 + 39 992 + 7 783,592) = 0,557349
    assert tc.beta_f(100.0, 20.0) == pytest.approx(0.557349, abs=1e-6)


def test_beta_s_calculo_a_mao_h_20cm():
    # h = 0,20 m, t/100 = 1: B = 0,928 − 11,28 + 44 − 4,8 = 28,848
    # C = 0,02 − 1,76 + 40,7 = 38,96; D = −0,6 + 23,4 + 99,2 − 6,8 = 115,2
    # E = −0,2704 + 0,704 + 23,36 − 7,8 + 0,8 = 16,7936
    # βs(100) = (1 + 40 + 28,848)/(1 + 38,96 + 115,2 + 16,7936) = 0,406203
    assert tc.beta_s(100.0, 20.0) == pytest.approx(0.406203, abs=1e-6)


def test_cruzado_h_em_cm_contra_h_em_m():
    # Falha se h entrar em m onde é cm, ou em cm onde é m.
    # φ2c e ε2s usam h = 20 (cm): 1,55 e 0,9035; com h = 0,2 dariam 2,089 e 1,58.
    assert tc.phi2c(20.0) == pytest.approx(1.55)
    assert tc.eps2s(20.0) == pytest.approx(0.903465, abs=1e-6)
    # βf e βs com h_pond_cm = 20 usam h = 0,2 m; se usassem h = 20 (travado em
    # 1,6 m) dariam o mesmo valor que h_pond_cm = 160.
    assert tc.beta_f(100.0, 20.0) != pytest.approx(tc.beta_f(100.0, 160.0), abs=0.01)
    assert tc.beta_s(100.0, 20.0) != pytest.approx(tc.beta_s(100.0, 160.0), abs=0.01)
    assert tc.beta_f(100.0, 20.0) == pytest.approx(0.557349, abs=1e-6)


def test_beta_f_beta_s_trava_h_nos_extremos():
    # h < 0,05 m adota 0,05 m; h > 1,6 m adota 1,6 m (só trava o argumento).
    for f in (tc.beta_f, tc.beta_s):
        assert f(50.0, 1.0) == f(50.0, 5.0)
        assert f(50.0, 500.0) == f(50.0, 160.0)
        assert f(50.0, 5.0001) == pytest.approx(f(50.0, 5.0), abs=1e-4)
        assert f(50.0, 159.999) == pytest.approx(f(50.0, 160.0), abs=1e-4)


def test_beta_f_beta_s_faixa_de_t():
    for f in (tc.beta_f, tc.beta_s):
        f(3.0, 20.0)
        with pytest.raises(Erro):
            f(2.99, 20.0)
        assert f(math.inf, 20.0) == 1.0


@pytest.mark.parametrize("h_cm", [5.0, 10.0, 20.0, 40.0, 80.0, 160.0])
def test_figura_A2_todas_as_curvas_partem_de_0_13(h_cm):
    # Figura A.2 (PDF p. 236): em t = 3 dias as curvas partem juntas de ≈ 0,13.
    assert tc.beta_f(3.0, h_cm) == pytest.approx(0.13, abs=0.01)


@pytest.mark.parametrize("t, h_cm, lido", [
    (1000.0, 5.0, 0.92), (1000.0, 160.0, 0.61), (10000.0, 5.0, 0.98), (10000.0, 160.0, 0.93),
])
def test_figura_A2_leitura_grafica(t, h_cm, lido):
    # Leitura gráfica da Figura A.2: tolerância larga.
    assert tc.beta_f(t, h_cm) == pytest.approx(lido, abs=0.03)


@pytest.mark.parametrize("t, h_cm, lido", [
    (3.0, 5.0, 0.22), (3.0, 10.0, 0.11), (3.0, 160.0, 0.0),
    (1000.0, 5.0, 0.97), (10000.0, 160.0, 0.88),
])
def test_figura_A3_leitura_grafica(t, h_cm, lido):
    # Leitura gráfica da Figura A.3 (PDF p. 238): tolerância larga.
    assert tc.beta_s(t, h_cm) == pytest.approx(lido, abs=0.03)


# ---------------------------------------------------------------------------
# βd e φa — A.2.2.3, PDF p. 234-235
# ---------------------------------------------------------------------------
def test_beta_d():
    assert tc.beta_d(30.0, 30.0) == pytest.approx(20.0 / 70.0)  # t = t0
    assert tc.beta_d(60.0, 30.0) == pytest.approx(0.5)          # 50/100
    assert tc.beta_d(math.inf, 30.0) == 1.0
    with pytest.raises(Erro):
        tc.beta_d(29.0, 30.0)


def test_razao_fc_usa_o_crescimento_de_12_3():
    # fc(t0)/fc(t∞) = β1(t0)/exp(s) = exp(−s·√(28/t0)).
    # CP II, t0 = 28: exp(−0,25) = 0,778801; t0 = 7: exp(−0,25·2) = 0,606531.
    assert tc.fc_t0_sobre_fc_tinf(28.0, "CPII", 30.0) == pytest.approx(0.778801, abs=1e-6)
    assert tc.fc_t0_sobre_fc_tinf(7.0, "CPII", 30.0) == pytest.approx(0.606531, abs=1e-6)
    # Coerente com o núcleo (fckj/fck = β1 para t < 28 dias).
    assert tc.fc_t0_sobre_fc_tinf(7.0, "CPII", 30.0) == pytest.approx(
        nbr.fckj(30.0, 7.0, "CPII") / 30.0 / math.exp(0.25))


def test_phi_a():
    # C30, t0 = 28, CP II: 0,8·(1 − 0,778801) = 0,176959.
    assert tc.phi_a(30.0, 28.0) == pytest.approx(0.176959, abs=1e-6)
    # C60 (s = 0,20 para C60 ou mais): 1,4·(1 − e^−0,2) = 0,253777.
    assert tc.phi_a(60.0, 28.0) == pytest.approx(0.253777, abs=1e-6)
    # Degrau de classe: C45 com 0,8 e C50 com 1,4 (razão fixada em 0,5).
    assert tc.phi_a(45.0, 28.0, razao_fc=0.5) == pytest.approx(0.4)
    assert tc.phi_a(50.0, 28.0, razao_fc=0.5) == pytest.approx(0.7)
    # t0 = t∞: razão 1 → φa = 0; t0 muito grande tende a 0.
    assert tc.phi_a(30.0, 28.0, razao_fc=1.0) == 0.0
    # t0 = 1e14: 0,8·[1 − exp(−0,25·√(28/1e14))] = 0,8·0,25·5,29e−7 ≈ 1,06e−7.
    assert tc.phi_a(30.0, 1e14) == pytest.approx(0.0, abs=1e-6)


def test_phi_a_fora_da_faixa():
    with pytest.raises(Erro):
        tc.phi_a(19.0, 28.0)
    with pytest.raises(Erro):
        tc.phi_a(30.0, 28.0, razao_fc=1.1)
    with pytest.raises(Erro):
        tc.phi_a(30.0, 0.0)


def test_phi_f_inf():
    # C20–C45: φ1c·φ2c = 2,0·1,55 = 3,1; C50–C90: 0,45·3,1 = 1,395.
    assert tc.phi_f_inf(45.0, 2.0, 1.55) == pytest.approx(3.1)
    assert tc.phi_f_inf(50.0, 2.0, 1.55) == pytest.approx(1.395)
    assert tc.phi_f_inf(90.0, 2.0, 1.55) == pytest.approx(1.395)
    with pytest.raises(Erro):
        tc.phi_f_inf(95.0, 2.0, 1.55)


# ---------------------------------------------------------------------------
# φ(t,t0) completo — A.2.2.3
# ---------------------------------------------------------------------------
def test_phi_em_t_igual_t0():
    # t = t0: some a parcela φf; φ = φa + 0,4·20/70.
    r = tc.coeficiente_fluencia(30.0, 30.0, 30.0, 20.0, U_pct=70.0)
    assert r.phi == pytest.approx(r.phi_a + 0.4 * 20.0 / 70.0)
    assert r.beta_f_t == r.beta_f_t0


def test_phi_caso_a_mao():
    # Ao ar livre (tabela): γ = 1,5; hfic = 20 → h = 30 cm; φ1c = 2,0;
    # φ2c = 72/50 = 1,44; C30: φf∞ = 2,88. t0 = 28, CP II: φa = 0,176959.
    # h = 0,3 m: A = 1,134 − 31,5 + 176,4 + 113 = 259,034;
    # B = 20,736 − 275,4 + 970,2 − 23 = 692,536; C = −5,4 + 1,17 + 327 + 183 = 505,77;
    # D = 204,633 − 2 872,44 + 10 602,9 + 1 931 = 9 866,093.
    # βf(28) = (784 + 7 252,952 + 692,536)/(784 + 14 161,56 + 9 866,093) = 0,351830
    # φ(∞,28) = 0,176959 + 2,88·(1 − 0,351830) + 0,4 = 2,443688
    r = tc.coeficiente_fluencia(math.inf, 28.0, 30.0, 20.0, ambiente="ar_livre")
    assert r.h_pond_cm == pytest.approx(30.0)
    assert r.phi_2c == pytest.approx(1.44)
    assert r.beta_f_t0 == pytest.approx(0.351830, abs=1e-6)
    assert r.phi == pytest.approx(2.443688, abs=1e-5)
    assert tc.phi(math.inf, 28.0, 30.0, 20.0, ambiente="ar_livre") == r.phi


def test_phi_resultado_e_memoria():
    r = tc.coeficiente_fluencia(1000.0, 28.0, 30.0, 20.0, U_pct=70.0)
    assert dataclasses.is_dataclass(r)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.phi = 0.0  # type: ignore[misc]
    texto = "\n".join(r.memoria)
    assert "A.2.2.3" in texto and "φ(t,t0)" in texto
    assert all(isinstance(linha, str) for linha in r.memoria)


def test_phi_entradas_invalidas():
    with pytest.raises(Erro):
        tc.coeficiente_fluencia(100.0, 2.0, 30.0, 20.0, U_pct=70.0)   # t0 < 3
    with pytest.raises(Erro):
        tc.coeficiente_fluencia(20.0, 28.0, 30.0, 20.0, U_pct=70.0)   # t < t0
    with pytest.raises(ValueError):
        tc.coeficiente_fluencia(100.0, 28.0, 30.0, 20.0)              # sem U nem ambiente


TAB_8_1_CASOS = [
    (t0, U, i, hfic)
    for t0 in (5.0, 30.0, 60.0)
    for U in (40.0, 55.0, 75.0, 90.0)
    for i, hfic in enumerate((20.0, 60.0))
]


@pytest.mark.parametrize("t0, U, i, hfic", TAB_8_1_CASOS)
def test_phi_inf_contra_tabela_8_1(t0, U, i, hfic):
    # 8.2.11 diz que o Anexo A é a versão mais precisa da Tabela 8.1 (PDF p. 47).
    # Comparação de ordem de grandeza: U e 2Ac/u da tabela, abatimento 5–9 cm,
    # t0 fictício = t0 da tabela. C50–C90 (C60, s = 0,20) fica a 0,1 em todas
    # as células; C20–C45 (C30) fica a 0,25.
    esperado_1 = nbr.TABELA_8_1_PHI["C20-C45"][t0][U][i]
    esperado_2 = nbr.TABELA_8_1_PHI["C50-C90"][t0][U][i]
    assert tc.phi(math.inf, t0, 30.0, hfic, U_pct=U) == pytest.approx(esperado_1, abs=0.25)
    assert tc.phi(math.inf, t0, 60.0, hfic, U_pct=U) == pytest.approx(esperado_2, abs=0.10)


# ---------------------------------------------------------------------------
# Retração — A.2.3.2, PDF p. 236-238
# ---------------------------------------------------------------------------
def test_eps_cs_inf():
    # εcs∞ = ε1s·ε2s: ao ar livre, 5–9 cm, h = 20 cm: −0,50·0,903465 = −0,451733 ‰.
    assert tc.eps_cs_inf_pmil(-0.5, tc.eps2s(20.0)) == pytest.approx(-0.451733, abs=1e-6)


def test_retracao_t_igual_t0_e_nula():
    assert tc.eps_cs_pmil(30.0, 30.0, 20.0, U_pct=70.0) == 0.0


def test_retracao_caso_a_mao():
    # Ao ar livre (tabela): γ = 1,5, h = 30 cm; ε1s = −0,50 ‰;
    # ε2s = 93/110,8 = 0,839350; εcs∞ = −0,419675 ‰.
    # βs(∞) = 1; εcs(∞, t0) = εcs∞·(1 − βs(t0)).
    r = tc.retracao(math.inf, 28.0, 20.0, ambiente="ar_livre")
    assert r.eps_2s == pytest.approx(93.0 / 110.8)
    assert r.eps_cs_inf_pmil == pytest.approx(-0.5 * 93.0 / 110.8)
    assert r.eps_cs_pmil == pytest.approx(r.eps_cs_inf_pmil * (1.0 - tc.beta_s(28.0, 30.0)))
    assert "A.2.3.2" in "\n".join(r.memoria)


def test_retracao_na_agua_e_inchamento():
    assert tc.eps_cs_pmil(math.inf, 7.0, 20.0, ambiente="agua") > 0.0


@pytest.mark.parametrize("t0, U, i, hfic", TAB_8_1_CASOS)
def test_eps_cs_inf_contra_tabela_8_1(t0, U, i, hfic):
    # Com t0 fictício = t0 da tabela (α = 1 na retração), o Anexo A reproduz
    # εcs(t∞,t0) da Tabela 8.1 a 0,025 ‰ em todas as células (a maior
    # diferença é U = 90 %, 2Ac/u = 60: −0,17 contra −0,15).
    esperado = nbr.TABELA_8_1_EPS_CS[t0][U][i]
    assert tc.eps_cs_pmil(math.inf, t0, hfic, U_pct=U) == pytest.approx(esperado, abs=0.025)


def test_retracao_entradas_invalidas():
    with pytest.raises(Erro):
        tc.retracao(100.0, 28.0, 20.0, U_pct=30.0)   # nota b só de 40 % a 90 %
    with pytest.raises(Erro):
        tc.retracao(100.0, 1.0, 20.0, U_pct=70.0)    # t0 < 3


# ---------------------------------------------------------------------------
# Promoção da Tabela 8.1 para o núcleo (reexportação no protendido)
# ---------------------------------------------------------------------------
def test_tabela_8_1_promovida_com_reexportacao():
    assert PT.phi_eps_cs_NBR is nbr.phi_eps_cs_NBR
    assert PT.TABELA_8_1_PHI is nbr.TABELA_8_1_PHI
    assert PT.TABELA_8_1_EPS_CS is nbr.TABELA_8_1_EPS_CS
    assert nbr.phi_eps_cs_NBR(75.0, 20.0, 30.0, 30.0) == pytest.approx((2.2, -0.33))


def test_tabela_8_1_fora_da_faixa_levanta_faixa_normativa():
    with pytest.raises(Erro):
        nbr.phi_eps_cs_NBR(75.0, 20.0, to_dias=61.0)
    with pytest.raises(Erro):
        nbr.phi_eps_cs_NBR(95.0, 20.0)
