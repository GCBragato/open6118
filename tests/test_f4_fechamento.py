"""Testes do F4 — Modelos de cálculo: consolo, dente Gerber e bloco em três
dimensões.

Fechamento dos três itens que os pacotes P36 e P48 deixaram parciais, contra a
ABNT NBR 6118:2026 (páginas do PDF; a impressa é 18 a menos):

  - 22.5.1.2 Comportamento estrutural do consolo, p. 207 (com a Figura 22.4)
  - 22.5.1.3 Modelo de cálculo do consolo, p. 208
  - 22.5.2.2 Comportamento do dente Gerber, p. 210 (com a Figura 22.6)
  - 22.5.2.3 Modelo de cálculo do dente Gerber, p. 210
  - 22.7.2   Comportamento estrutural do bloco sobre estacas, p. 213
  - 22.7.3   Modelo de cálculo do bloco sobre estacas, p. 213
  - 22.3.1 e 22.3.2 (faixa de inclinação e tensões de biela e nó), p. 204

Os três itens são de procedimento: a norma não tabela resultado. Os valores
esperados vêm (a) do texto literal, quando há limite — a difusão 1:2 de
22.5.1.2 c), a faixa 0,57 <= tan(theta) <= 2 de 22.3.1, a faixa de 1,2·phi de
22.7.2.1 a) —, (b) da estática fechada do modelo, com a conta no comentário de
cada teste, e (c) da conferência contra o que a biblioteca já calculava por
outro caminho (a conta de braço de alavanca do P36, o método das bielas do
P37).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import bielas_tirantes_nbr6118 as bt        # noqa: E402
import consolos_nbr6118 as cons             # noqa: E402
import nucleo_nbr6118 as nbr                # noqa: E402

FYD_KNCM2 = nbr.mpa_para_kncm2(nbr.fyd())   # CA-50: 500/1,15 = 434,78 MPa


# =============================================================================
# 22.5.1.3 — Braço de alavanca adotado e inclinação da biela (PDF p. 208)
# =============================================================================
def test_braco_alavanca_adotado_padrao_e_informado():
    # sem z_cm: a aproximação do módulo, z = 0,85*d (22.5.1.3 não dá z)
    assert cons.braco_alavanca_adotado_cm(40.0) == pytest.approx(34.0)
    # com z_cm: vale o valor do projetista
    assert cons.braco_alavanca_adotado_cm(40.0, 30.0) == pytest.approx(30.0)
    # z = d é o limite aceito
    assert cons.braco_alavanca_adotado_cm(40.0, 40.0) == pytest.approx(40.0)


def test_braco_alavanca_adotado_fora_da_faixa_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        cons.braco_alavanca_adotado_cm(40.0, 40.1)      # z > d
    with pytest.raises(nbr.FaixaNormativaError):
        cons.braco_alavanca_adotado_cm(40.0, 0.0)       # z <= 0
    with pytest.raises(nbr.FaixaNormativaError):
        cons.braco_alavanca_adotado_cm(0.0)             # d <= 0


def test_inclinacao_biela_consolo_nos_dois_lados_do_limite_superior():
    # 22.3.1 (p. 204): tan(theta) <= 2. Com z = 0,85*d, tan = 0,85*d/a, e o
    # limite cai em a = 0,425*d. Com d = 40: a = 17 cm dá tan = 2 exatamente.
    assert cons.inclinacao_biela_consolo(17.0, 40.0).tan_theta == pytest.approx(2.0)
    assert cons.inclinacao_biela_consolo(17.0, 40.0).ok is True
    # a = 16 cm -> tan = 34/16 = 2,125 > 2 -> fora da faixa
    r = cons.inclinacao_biela_consolo(16.0, 40.0)
    assert r.tan_theta == pytest.approx(2.125)
    assert r.ok is False


def test_inclinacao_biela_consolo_nos_dois_lados_do_limite_inferior():
    # 22.3.1: tan(theta) >= 0,57. Com z = 0,85*d o limite cai em a = 1,4912*d;
    # é um consolo que 22.5.1.1 já classificaria como viga em balanço (a > d),
    # mas a função de inclinação é geométrica e cobre o caso.
    # d = 40 -> z = 34; a = 34/0,57 = 59,6491 cm dá tan = 0,57 exatamente.
    a_limite = 34.0 / 0.57
    assert cons.inclinacao_biela_consolo(a_limite, 40.0).ok is True
    # a = 65 cm -> tan = 34/65 = 0,5231 < 0,57 -> fora da faixa
    r = cons.inclinacao_biela_consolo(65.0, 40.0)
    assert r.tan_theta == pytest.approx(34.0 / 65.0)
    assert r.ok is False


def test_inclinacao_biela_consolo_faixa_interior_e_z_informado():
    # consolo curto típico, a/d = 0,625: tan = 34/25 = 1,36, no meio da faixa
    assert cons.inclinacao_biela_consolo(25.0, 40.0).tan_theta == pytest.approx(1.36)
    # com z informado, tan = z/a
    assert cons.inclinacao_biela_consolo(25.0, 40.0, 30.0).tan_theta == \
        pytest.approx(30.0 / 25.0)


# =============================================================================
# 22.5.1.2 c) com 22.3.2 — Compressão na biela do consolo (PDF p. 207 e 204)
# =============================================================================
def test_verificar_biela_consolo_exemplo_a_mao():
    # Consolo do exemplo do P36 já amplificado pelo gama_n de 22.2:
    # Fd,amp = 240 kN, a = 25, d = 40, b = 20, h = 45, a0 = 15 cm, C30.
    #
    # z = 0,85*40 = 34 cm; L = raiz(25^2 + 34^2) = raiz(1781) = 42,2019 cm;
    # sen(theta) = 34/42,2019 = 0,805651.
    # Rcd = Fd*L/z = 240*42,2019/34 = 297,8957 kN.
    # 22.5.1.2 c): difusão 1:2 em d' = h - d = 5 cm -> largura do nó
    #   = a0 + d' = 15 + 5 = 20 cm.
    # h,biela = 20*0,805651 = 16,1130 cm; b,biela = b = 20 cm;
    #   área = 322,2604 cm2.
    # sigma = 297,8957/322,2604 = 0,924394 kN/cm2.
    # 22.3.2: nó CCT -> fcd3 = 0,72*alpha_v2*fcd = 0,72*0,88*(30/1,4)/10
    #   = 1,357714 kN/cm2 -> sigma/fcd3 = 0,680846 <= 1 -> ok.
    r = cons.verificar_biela_consolo(240.0, 25.0, 40.0, 20.0, 45.0, 15.0, 30.0)
    assert r.z_cm == pytest.approx(34.0)
    assert r.L_biela_cm == pytest.approx(math.sqrt(1781.0))
    assert r.sen_theta == pytest.approx(34.0 / math.sqrt(1781.0))
    assert r.tan_theta == pytest.approx(34.0 / 25.0)
    assert r.Rcd_kn == pytest.approx(297.8957, abs=1e-3)
    assert r.profundidade_difusao_cm == pytest.approx(5.0)
    assert r.largura_no_cm == pytest.approx(20.0)
    assert r.h_biela_cm == pytest.approx(16.1130, abs=1e-3)
    assert r.b_biela_cm == pytest.approx(20.0)
    assert r.area_biela_cm2 == pytest.approx(322.2604, abs=1e-3)
    assert r.sigma_kncm2 == pytest.approx(0.924394, abs=1e-5)
    assert r.tipo_no == "CCT"
    assert r.fcd_no_kncm2 == pytest.approx(bt.fcd3_kncm2(30.0))
    assert r.razao == pytest.approx(0.680846, abs=1e-5)
    assert r.ok is True
    assert r.governante == "22.5.1.2"


def test_verificar_biela_consolo_tipo_ccc_usa_fcd1():
    # 22.3.2: no nó de ligação com o pilar só confluem bielas -> CCC -> fcd1
    r = cons.verificar_biela_consolo(240.0, 25.0, 40.0, 20.0, 45.0, 15.0, 30.0,
                                     tipo="CCC")
    assert r.fcd_no_kncm2 == pytest.approx(bt.fcd1_kncm2(30.0))
    # mesma tensão, razão menor (fcd1 > fcd3)
    assert r.sigma_kncm2 == pytest.approx(0.924394, abs=1e-5)
    assert r.razao < 0.680846


def test_verificar_biela_consolo_tipo_desconhecido_levanta_value_error():
    with pytest.raises(ValueError):
        cons.verificar_biela_consolo(240.0, 25.0, 40.0, 20.0, 45.0, 15.0, 30.0,
                                     tipo="XXX")


def test_verificar_biela_consolo_b0_limita_a_largura_transversal():
    # com b0 = 10 cm e d' = 5 cm, a difusão 1:2 dá 10 + 5 = 15 cm < b = 20 cm
    r = cons.verificar_biela_consolo(240.0, 25.0, 40.0, 20.0, 45.0, 15.0, 30.0,
                                     b0_cm=10.0)
    assert r.b_biela_cm == pytest.approx(15.0)
    # b0 grande: a largura do consolo é que manda
    r2 = cons.verificar_biela_consolo(240.0, 25.0, 40.0, 20.0, 45.0, 15.0, 30.0,
                                      b0_cm=40.0)
    assert r2.b_biela_cm == pytest.approx(20.0)


def test_verificar_biela_consolo_reprova_com_placa_pequena():
    # a0 = 3 cm -> largura do nó = 8 cm; h,biela = 8*0,805651 = 6,4452 cm;
    # área = 128,9042 cm2; sigma = 297,8957/128,9042 = 2,3110 kN/cm2 > fcd3.
    r = cons.verificar_biela_consolo(240.0, 25.0, 40.0, 20.0, 45.0, 3.0, 30.0)
    assert r.sigma_kncm2 == pytest.approx(2.3110, abs=1e-3)
    assert r.razao > 1.0
    assert r.ok is False


def test_verificar_biela_consolo_h_menor_ou_igual_a_d_levanta_erro():
    # sem d' = h - d não há difusão de 22.5.1.2 c) a considerar
    with pytest.raises(nbr.FaixaNormativaError):
        cons.verificar_biela_consolo(240.0, 25.0, 40.0, 20.0, 40.0, 15.0, 30.0)
    with pytest.raises(nbr.FaixaNormativaError):
        cons.verificar_biela_consolo(240.0, 25.0, 40.0, 20.0, 45.0, 0.0, 30.0)


def test_verificar_biela_consolo_inclinacao_fora_da_faixa_reprova():
    # a = 16 cm -> tan = 2,125 > 2 (22.3.1): mesmo com a compressão folgada,
    # o modelo de biela-tirante não vale
    r = cons.verificar_biela_consolo(50.0, 16.0, 40.0, 30.0, 45.0, 20.0, 30.0)
    assert r.razao < 1.0
    assert r.inclinacao.ok is False
    assert r.ok is False


# =============================================================================
# 22.5.1.3 com 22.3.1 — Treliça do consolo (PDF p. 208 e 203)
# =============================================================================
def test_modelo_biela_tirante_consolo_reproduz_a_conta_de_braco_de_alavanca():
    # Mesmo consolo: Fd,amp = 240 kN, Hd,amp = 36 kN, a = 25, d = 40 -> z = 34.
    # Rsd = 240*25/34 + 36 = 212,4706 kN (22.5.1.3);
    # Rcd = -240*raiz(25^2+34^2)/34 = -297,8957 kN.
    Fd, Hd, a, d = 240.0, 36.0, 25.0, 40.0
    z = 34.0
    t = cons.modelo_biela_tirante_consolo(Fd, Hd, a, d)
    assert t.grau_estatico() == 0        # 3 barras + 3 graus - 2*3 nós
    r = t.resolver()
    assert r.N_kn("A-C") == pytest.approx(Fd * a / z + Hd)
    assert r.N_kn("A-C") == pytest.approx(
        cons.Rsd_tirante_consolo_kn(Fd, Hd, a, z))
    assert r.barras["A-C"].tipo == "tirante"
    assert r.N_kn("C-B") == pytest.approx(-Fd * math.hypot(a, z) / z)
    assert r.barras["C-B"].tipo == "biela"
    # a barra da face do pilar fecha a contagem de 22.3.1 e sai nula
    assert r.N_kn("A-B") == pytest.approx(0.0)
    assert r.nulas == ("A-B",)
    # 22.3.1: inclinação da biela em relação ao eixo do tirante
    assert r.barras["C-B"].tan_theta == pytest.approx(z / a)


def test_modelo_biela_tirante_consolo_sem_forca_horizontal():
    # Hd = 0 -> Rsd = Fd*a/z, sem a parcela somada direto (22.5.1.3)
    r = cons.modelo_biela_tirante_consolo(200.0, 0.0, 20.0, 40.0).resolver()
    assert r.N_kn("A-C") == pytest.approx(200.0 * 20.0 / 34.0)


def test_modelo_biela_tirante_consolo_com_z_informado():
    # z do projetista no lugar de 0,85*d (22.5.1.3 não dá z)
    r = cons.modelo_biela_tirante_consolo(200.0, 0.0, 20.0, 40.0,
                                          z_cm=30.0).resolver()
    assert r.N_kn("A-C") == pytest.approx(200.0 * 20.0 / 30.0)


# =============================================================================
# 22.5.1.3 — dimensionar_consolo com as verificações fechadas (PDF p. 208)
# =============================================================================
def test_dimensionar_consolo_com_a0_verifica_a_biela_e_leva_ao_ok():
    # Fd = 200 kN, gama_n = 1,2 -> Fd,amp = 240 kN; a0 = 15 cm.
    # A biela é a do teste a mão acima: razão 0,6808 -> ok.
    r = cons.dimensionar_consolo(200.0, 30.0, 25.0, 40.0, 20.0, 45.0, 30.0,
                                 500.0, a0_cm=15.0)
    assert r.biela is not None
    assert r.biela.tipo_no == "CCT"
    assert r.biela.razao == pytest.approx(0.680846, abs=1e-5)
    assert r.biela.Fd_kn == pytest.approx(240.0)   # já amplificado por gama_n
    assert r.ok is True
    assert r.governante == "22.5.1.3"


def test_dimensionar_consolo_com_a0_pequeno_reprova_pela_biela():
    r = cons.dimensionar_consolo(200.0, 30.0, 25.0, 40.0, 20.0, 45.0, 30.0,
                                 500.0, a0_cm=3.0)
    assert r.biela.ok is False
    assert r.ok is False
    assert r.governante == "22.5.1.2"


def test_dimensionar_consolo_sem_a0_nao_verifica_a_biela():
    # sem a largura da placa não há como aplicar 22.5.1.2 c): biela fica None,
    # mas a inclinação de 22.3.1 é conferida de qualquer jeito
    r = cons.dimensionar_consolo(200.0, 30.0, 25.0, 40.0, 20.0, 45.0, 30.0)
    assert r.biela is None
    assert r.inclinacao_biela is not None
    assert r.inclinacao_biela.tan_theta == pytest.approx(34.0 / 25.0)
    assert r.ok is True
    assert any("não foi verificada" in linha for linha in r.memoria)


def test_dimensionar_consolo_muito_curto_reprova_pela_inclinacao_22_3_1():
    # a = 15, d = 40 -> a/d = 0,375 (consolo muito curto) e tan = 34/15 =
    # 2,2667 > 2: fora da faixa de 22.3.1. É a faixa em que 22.5.1.3 manda
    # usar atrito-cisalhamento, que a biblioteca não implementa.
    r = cons.dimensionar_consolo(5.0, 0.0, 15.0, 40.0, 25.0, 50.0, 25.0, 500.0)
    assert r.classificacao == "muito_curto"
    assert r.inclinacao_biela.tan_theta == pytest.approx(34.0 / 15.0)
    assert r.ok is False
    assert r.governante == "22.3.1"


def test_dimensionar_consolo_z_informado_substitui_a_aproximacao():
    # z = 30 cm no lugar de 0,85*40 = 34 -> Rsd = 240*25/30 + 36 = 236 kN
    r = cons.dimensionar_consolo(200.0, 30.0, 25.0, 40.0, 20.0, 45.0, 30.0,
                                 500.0, z_cm=30.0)
    assert r.z_cm == pytest.approx(30.0)
    assert r.Rsd_kn == pytest.approx(240.0 * 25.0 / 30.0 + 36.0)
    assert any("informado pelo projetista" in linha for linha in r.memoria)


def test_dimensionar_consolo_modelo_atrito_explica_a_ausencia_de_coeficiente():
    # 22.5.1.3 cita o modelo atrito-cisalhamento sem nenhum coeficiente de
    # atrito; a biblioteca recusa em vez de inventar constante sem fonte.
    with pytest.raises(NotImplementedError) as exc:
        cons.dimensionar_consolo(100.0, 0.0, 20.0, 40.0, 25.0, 50.0, 25.0,
                                 500.0, modelo="atrito")
    assert "coeficientes de atrito" in str(exc.value)


# =============================================================================
# 22.5.2.3 com 22.5.2.2 — Dente Gerber (PDF p. 210)
# =============================================================================
def test_dente_gerber_com_a0_verifica_a_biela_e_soma_a_suspensao():
    Fd, Hd, a, d, b, h, fck = 200.0, 30.0, 25.0, 40.0, 20.0, 45.0, 30.0
    g = cons.dimensionar_dente_gerber(Fd, Hd, a, d, b, h, fck, 500.0,
                                      a0_cm=15.0)
    assert g.consolo.biela is not None
    assert g.consolo.biela.razao == pytest.approx(0.680846, abs=1e-5)
    # 22.5.2.4.2: As,susp = Fd,amp/fyd, com Fd,amp = 200*1,2 = 240 kN
    assert g.As_suspensao_dente_cm2 == pytest.approx(240.0 / FYD_KNCM2)
    assert g.ok is True
    assert g.governante == "22.5.2.3"


def test_dente_gerber_biela_mais_inclinada_quando_a_suspensao_esta_perto():
    # 22.5.2.2 a): a biela do dente é mais inclinada porque procura apoio na
    # armadura de suspensão. No modelo, isso é a menor distância a até a linha
    # da suspensão: tan(theta) = z/a cresce quando a diminui.
    longe = cons.dimensionar_dente_gerber(200.0, 0.0, 30.0, 40.0, 20.0, 45.0, 30.0)
    perto = cons.dimensionar_dente_gerber(200.0, 0.0, 20.0, 40.0, 20.0, 45.0, 30.0)
    assert perto.consolo.inclinacao_biela.tan_theta > \
        longe.consolo.inclinacao_biela.tan_theta
    assert perto.consolo.inclinacao_biela.tan_theta == pytest.approx(34.0 / 20.0)
    # e o tirante alivia, porque o braço até a suspensão é menor
    assert perto.consolo.Rsd_kn < longe.consolo.Rsd_kn


def test_dente_gerber_inclinacao_fora_de_22_3_1_reprova():
    # a = 15, d = 40 -> tan = 2,2667 > 2: o modelo biela-tirante não cobre
    g = cons.dimensionar_dente_gerber(200.0, 0.0, 15.0, 40.0, 20.0, 45.0, 30.0)
    assert g.ok is False
    assert g.governante == "22.3.1"


def test_dente_gerber_z_informado_muda_o_tirante_e_nao_a_suspensao():
    # 22.5.2.4.2: a suspensão é dimensionada para Fd, não depende de z
    base = cons.dimensionar_dente_gerber(200.0, 0.0, 25.0, 40.0, 20.0, 45.0, 30.0)
    z30 = cons.dimensionar_dente_gerber(200.0, 0.0, 25.0, 40.0, 20.0, 45.0, 30.0,
                                        z_cm=30.0)
    assert z30.consolo.z_cm == pytest.approx(30.0)
    assert z30.consolo.Rsd_kn > base.consolo.Rsd_kn
    assert z30.As_suspensao_dente_cm2 == pytest.approx(
        base.As_suspensao_dente_cm2)


def test_dente_gerber_memoria_cita_as_tres_diferencas_de_22_5_2_2():
    g = cons.dimensionar_dente_gerber(200.0, 0.0, 25.0, 40.0, 20.0, 45.0, 30.0)
    texto = "\n".join(g.memoria)
    assert "22.5.2.2 a)" in texto
    assert "22.5.2.2 b)" in texto
    assert "22.5.2.4.2" in texto


# =============================================================================
# 22.7.2.1 a) — Faixa do tirante do bloco (PDF p. 213)
# =============================================================================
def test_largura_faixa_tirante_bloco():
    # 22.7.2.1 a): "faixas de largura igual a 1,2 vez seu diâmetro"
    assert bt.largura_faixa_tirante_bloco_cm(30.0) == pytest.approx(36.0)
    assert bt.largura_faixa_tirante_bloco_cm(25.0) == pytest.approx(30.0)
    with pytest.raises(nbr.FaixaNormativaError):
        bt.largura_faixa_tirante_bloco_cm(0.0)


# =============================================================================
# 22.7.3 — Topologia automática de tirantes do bloco (PDF p. 213)
# =============================================================================
@pytest.mark.parametrize("n", [3, 4, 5, 6, 7, 8])
def test_topologia_tirantes_bloco_tem_2n_menos_3_tirantes(n):
    # 22.3.1 no modo autoequilibrado: m + 6 = 3*(n+1), com n bielas ->
    # número de tirantes = 2n - 3.
    pos = [(100.0 * math.cos(2 * math.pi * i / n),
            100.0 * math.sin(2 * math.pi * i / n)) for i in range(n)]
    pares = bt.topologia_tirantes_bloco(pos, 100.0)
    assert len(pares) == 2 * n - 3
    assert len(set(tuple(sorted(p)) for p in pares)) == 2 * n - 3


def test_topologia_tirantes_bloco_prefere_as_ligacoes_mais_curtas():
    # 4 estacas em losango de raio 100 mais uma central: as 4 ligações
    # centro-estaca (100 cm) são mais curtas que os lados do perímetro
    # (141,42 cm), e entram primeiro; faltam 3 para chegar a 2*5-3 = 7.
    pos = [(100.0, 0.0), (0.0, 100.0), (-100.0, 0.0), (0.0, -100.0), (0.0, 0.0)]
    pares = bt.topologia_tirantes_bloco(pos, 100.0)
    assert len(pares) == 7
    assert set(tuple(sorted(p)) for p in pares[:4]) == \
        {(0, 4), (1, 4), (2, 4), (3, 4)}


def test_topologia_tirantes_bloco_erros():
    with pytest.raises(ValueError):
        bt.topologia_tirantes_bloco([(0.0, 0.0), (100.0, 0.0)], 100.0)
    with pytest.raises(nbr.FaixaNormativaError):
        bt.topologia_tirantes_bloco([(0.0, 0.0), (100.0, 0.0), (0.0, 100.0)], 0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        bt.topologia_tirantes_bloco([(0.0, 0.0), (100.0, 0.0), (0.0, 100.0)],
                                    100.0, ap_cm=-1.0)


def test_bloco_5_estacas_topologia_automatica_resolve():
    # 4 estacas em losango de raio R = 100 mais uma central; d = 100;
    # Nd = 2000 -> 400 kN em cada estaca.
    # Cada biela periférica leva 400 na vertical e produz empuxo radial
    # H = 400*100/100 = 400 kN, que o tirante radial até a estaca central
    # absorve inteiro (ele aponta exatamente para o centro): T = 400 kN.
    # Os tirantes do perímetro saem nulos, e a biela central é vertical.
    pos = [(100.0, 0.0), (0.0, 100.0), (-100.0, 0.0), (0.0, -100.0), (0.0, 0.0)]
    t = bt.modelo_bloco_estacas(pos, 2000.0, 100.0)
    assert t.grau_estatico() == 0
    r = t.resolver()
    for k in range(4):
        assert r.N_kn(("tirante", min(k, 4), max(k, 4))) == pytest.approx(400.0)
        assert r.N_kn(("biela", k)) == pytest.approx(
            -400.0 * math.hypot(100.0, 100.0) / 100.0)
    assert r.N_kn(("biela", 4)) == pytest.approx(-400.0)
    assert r.barras[("biela", 4)].tan_theta == math.inf
    assert len(r.nulas) == 3        # os 3 tirantes de perímetro escolhidos


def test_bloco_6_estacas_hexagono_tirantes_do_perimetro():
    # 6 estacas num hexágono regular de raio R = 100, d = 100, Nd = 1200
    # -> 200 kN em cada estaca; empuxo radial H = 200*100/100 = 200 kN.
    # No vértice, o ângulo interno do hexágono é 120 graus e o raio o divide
    # ao meio: cada um dos dois tirantes do perímetro faz 60 graus com o raio,
    # logo 2*T*cos(60) = T = H -> T = 200 kN. As 3 diagonais curtas escolhidas
    # para fechar a isostaticidade saem nulas.
    R, d, Nd = 100.0, 100.0, 1200.0
    pos = [(R * math.cos(i * math.pi / 3), R * math.sin(i * math.pi / 3))
           for i in range(6)]
    t = bt.modelo_bloco_estacas(pos, Nd, d)
    assert t.grau_estatico() == 0
    r = t.resolver()
    lados = [b for b in r.barras.values()
             if b.id[0] == "tirante" and b.L_cm == pytest.approx(R)]
    assert len(lados) == 6
    for b in lados:
        assert b.N_kn == pytest.approx(200.0)
    assert len(r.nulas) == 3
    for bid in r.nulas:
        assert r.barras[bid].L_cm == pytest.approx(R * math.sqrt(3.0))


# =============================================================================
# 22.7.3 — Força horizontal no topo do bloco (PDF p. 213)
# =============================================================================
def test_bloco_forca_horizontal_avisa_interacao_solo_estrutura():
    # 22.7.3: "Sempre que houver forças horizontais significativas ou forte
    # assimetria, o modelo deve contemplar a interação solo-estrutura."
    pos = [(-100.0, 0.0), (100.0, 0.0)]
    with pytest.warns(nbr.AvisoNBR6118, match="interação solo-estrutura"):
        bt.modelo_bloco_estacas(pos, 1000.0, 100.0, Hx_kn=100.0)
    # avisar=False silencia
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        bt.modelo_bloco_estacas(pos, 1000.0, 100.0, Hx_kn=100.0, avisar=False)


def test_bloco_2_estacas_com_forca_horizontal():
    # Nd = 1000, e = 200 (estacas a +-100), d = 100, Hx = 100 kN.
    # Vertical: R = Nd/2 +- Hx*d*x/Sx, com Sx = 2*100^2 = 20000 ->
    #   R = 500 +- 100*100*100/20000 = 500 +- 50.
    # Horizontal: -Hx/2 = -50 kN em cada estaca.
    # No nó da estaca 1 (x = +100): Nz = 550 -> biela = -550*raiz(2) e
    #   empuxo horizontal 550; equilíbrio em x: 550 - T - 50 = 0 -> T = 500,
    #   o mesmo tirante de Nd*e/(4d) = 500 kN do caso sem força horizontal
    #   (com duas estacas a parcela da força horizontal se cancela).
    Nd, d, Hx = 1000.0, 100.0, 100.0
    pos = [(-100.0, 0.0), (100.0, 0.0)]
    t = bt.modelo_bloco_estacas(pos, Nd, d, Hx_kn=Hx, avisar=False)
    assert t.espacial is True       # com força horizontal o modelo é espacial
    assert t.grau_estatico() == 0
    r = t.resolver()
    assert r.N_kn(("tirante", 0, 1)) == pytest.approx(500.0)
    assert r.N_kn(("biela", 0)) == pytest.approx(-450.0 * math.sqrt(2.0))
    assert r.N_kn(("biela", 1)) == pytest.approx(-550.0 * math.sqrt(2.0))
    # sem força horizontal, as duas bielas são iguais
    r0 = bt.modelo_bloco_estacas(pos, Nd, d).resolver()
    assert r0.N_kn(("biela", 0)) == pytest.approx(r0.N_kn(("biela", 1)))


def test_bloco_forca_horizontal_com_excentricidade_cruzada_fica_autoequilibrado():
    # Força horizontal em x com excentricidade em y (e vice-versa) produz
    # torção em torno do eixo vertical: a distribuição acrescenta a parcela
    # polar, e a treliça continua autoequilibrada (22.3.1) -- se não
    # estivesse, resolver levantaria TrelicaNaoAutoequilibradaError.
    s = 100.0
    pos = [(-s, -s), (s, -s), (s, s), (-s, s)]
    t = bt.modelo_bloco_estacas(pos, 1600.0, 100.0, ex_cm=10.0, ey_cm=-20.0,
                                Hx_kn=80.0, Hy_kn=-40.0, avisar=False)
    r = t.resolver()
    assert r.autoequilibrado is True
    # equilíbrio vertical: a soma das reações é a força do pilar
    assert sum(float(f[2]) for no, f in t.forcas.items() if no != "P") == \
        pytest.approx(1600.0)
    assert sum(float(f[0]) for no, f in t.forcas.items()) == pytest.approx(0.0)
    assert sum(float(f[1]) for no, f in t.forcas.items()) == pytest.approx(0.0)


def test_bloco_sem_forca_horizontal_nao_muda_nada():
    # regressão: Hx = Hy = 0 reproduz exatamente o modelo do P48
    Nd, e, ap, d = 1000.0, 200.0, 40.0, 90.0
    pos = [(-e / 2.0, 0.0), (e / 2.0, 0.0)]
    t = bt.modelo_bloco_estacas(pos, Nd, d, ap_cm=ap, Hx_kn=0.0, Hy_kn=0.0)
    assert t.espacial is False
    r = t.resolver()
    assert r.N_kn(("tirante", 0, 1)) == pytest.approx(
        Nd * (2.0 * e - ap) / (8.0 * d))


# =============================================================================
# 22.7.3 com 21.2 — Fendilhamento na região de contato pilar-bloco (p. 213)
# =============================================================================
def test_fendilhamento_pilar_bloco_exemplo_a_mao():
    # Pilar 40 x 40 cm sobre bloco 200 x 200 cm, Nd = 2000 kN, C30, sem
    # excentricidade. Prisma simétrico: a' = b' = 200 cm.
    # Tx = 0,25*2000*(1 - 40/200) = 500*0,8 = 400 kN, a a'/2 = 100 cm da face.
    # As = 400/43,4783 = 9,2 cm2 (22.3.3).
    # Esmagamento: sigma = 2000/(40*40) = 1,25 kN/cm2; nó CCC -> fcd1 =
    #   0,85*0,88*(30/1,4)/10 = 1,602857 kN/cm2 -> razão 0,7799 -> ok.
    r = bt.fendilhamento_pilar_bloco(2000.0, 40.0, 40.0, 200.0, 200.0, 30.0,
                                     fyd_kncm2=FYD_KNCM2)
    assert r.T_x_kn == pytest.approx(400.0)
    assert r.T_y_kn == pytest.approx(400.0)
    assert r.x_tirante_x_cm == pytest.approx(100.0)
    assert r.x_tirante_y_cm == pytest.approx(100.0)
    assert r.As_x_cm2 == pytest.approx(400.0 / FYD_KNCM2)
    assert r.As_x_cm2 == pytest.approx(9.2, abs=1e-2)
    assert r.sigma_contato_kncm2 == pytest.approx(1.25)
    assert r.no_contato.tipo == "CCC"
    assert r.no_contato.fcd_no_kncm2 == pytest.approx(bt.fcd1_kncm2(30.0))
    assert r.no_contato.razao == pytest.approx(1.25 / bt.fcd1_kncm2(30.0))
    assert r.ok is True
    assert r.governante == "22.7.3"


def test_fendilhamento_pilar_bloco_sem_fyd_nao_dimensiona():
    r = bt.fendilhamento_pilar_bloco(2000.0, 40.0, 40.0, 200.0, 200.0, 30.0)
    assert r.As_x_cm2 is None and r.As_y_cm2 is None
    assert r.T_x_kn == pytest.approx(400.0)


def test_fendilhamento_pilar_bloco_excentricidade_reduz_o_prisma():
    # ex = 20 cm -> a' = 200 - 2*20 = 160 cm;
    # Tx = 0,25*2000*(1 - 40/160) = 500*0,75 = 375 kN, a 80 cm da face.
    r = bt.fendilhamento_pilar_bloco(2000.0, 40.0, 40.0, 200.0, 200.0, 30.0,
                                     ex_cm=20.0)
    assert r.T_x_kn == pytest.approx(375.0)
    assert r.x_tirante_x_cm == pytest.approx(80.0)
    # a direção y não muda
    assert r.T_y_kn == pytest.approx(400.0)


def test_fendilhamento_pilar_bloco_reprova_o_esmagamento():
    # pilar 20 x 20 cm com Nd = 2000 kN: sigma = 5 kN/cm2 > fcd1 = 1,6029
    r = bt.fendilhamento_pilar_bloco(2000.0, 20.0, 20.0, 200.0, 200.0, 30.0)
    assert r.sigma_contato_kncm2 == pytest.approx(5.0)
    assert r.no_contato.ok is False
    assert r.ok is False


def test_fendilhamento_pilar_bloco_erros():
    with pytest.raises(nbr.FaixaNormativaError):
        bt.fendilhamento_pilar_bloco(0.0, 40.0, 40.0, 200.0, 200.0, 30.0)
    with pytest.raises(nbr.FaixaNormativaError):
        bt.fendilhamento_pilar_bloco(2000.0, 0.0, 40.0, 200.0, 200.0, 30.0)
    # pilar não cabe no prisma simétrico do bloco
    with pytest.raises(nbr.FaixaNormativaError):
        bt.fendilhamento_pilar_bloco(2000.0, 200.0, 40.0, 200.0, 200.0, 30.0)
