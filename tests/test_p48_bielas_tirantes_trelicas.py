"""Testes do P48 — Bielas e tirantes: treliças e modelos de cálculo.

Cobre o bloco P48 de dimensionamento/bielas_tirantes_nbr6118.py contra a
ABNT NBR 6118:2026 (páginas do PDF; a impressa é 18 a menos):

  - 21.2.3 Região de introdução da protensão, p. 199
  - 22.2   Limite convencional entre as regiões B e D, p. 202
  - 22.3.1 Procedimento para aplicação do método, p. 203-204
  - 22.4.3 Modelos de cálculo de viga-parede, p. 205
  - 22.6.3 Modelo de cálculo de sapata, p. 212
  - 22.7.3 Modelo de cálculo de bloco sobre estacas, p. 213

Os itens deste pacote são de procedimento: a norma não tabela resultado de
treliça. Os valores esperados vêm (a) do texto literal do item, quando há
limite (22.2: distância h); (b) da estática fechada da treliça, com a conta
no comentário de cada teste; e (c) das referências da literatura declaradas
na docstring de cada modelo, conferidas contra o que a biblioteca já
calculava por outro caminho (método das bielas de blocos e de sapatas).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import bielas_tirantes_nbr6118 as bt        # noqa: E402
import blocos_nbr6118 as bloc               # noqa: E402
import nucleo_nbr6118 as nbr                # noqa: E402
import sapatas_nbr6118 as sap               # noqa: E402

FYD_KNCM2 = nbr.mpa_para_kncm2(nbr.fyd())   # CA-50: 500/1,15 = 434,78 MPa


# =============================================================================
# 22.2 — Limite convencional entre as regiões B e D (PDF p. 202)
# =============================================================================
def test_extensao_regiao_d_um_e_dois_lados():
    # 22.2, p. 202: "o limite entre as regiões B e D pode ser considerado
    # localizado a uma distância h ... da seção efetiva da descontinuidade".
    # Figura 22.1 b3 (introdução de força concentrada na extremidade): h de
    # um lado; Figura 22.1 b2 (carga concentrada no vão): 2h, h de cada lado.
    assert bt.extensao_regiao_d_cm(60.0) == pytest.approx(60.0)
    assert bt.extensao_regiao_d_cm(60.0, n_lados=1) == pytest.approx(60.0)
    assert bt.extensao_regiao_d_cm(60.0, n_lados=2) == pytest.approx(120.0)
    # mudança de seção (Figura 22.1 a1): cada lado com o seu h
    assert bt.extensao_regiao_d_cm(40.0) + bt.extensao_regiao_d_cm(90.0) == \
        pytest.approx(130.0)


def test_extensao_regiao_d_fora_da_faixa():
    with pytest.raises(bt.FaixaNormativaError):
        bt.extensao_regiao_d_cm(0.0)
    with pytest.raises(bt.FaixaNormativaError):
        bt.extensao_regiao_d_cm(-10.0)
    with pytest.raises(ValueError):
        bt.extensao_regiao_d_cm(60.0, n_lados=3)


def test_classificar_regiao_bd_nos_dois_lados_do_degrau():
    # o degrau de 22.2 está exatamente em x = h
    h = 70.0
    assert bt.classificar_regiao_bd(0.0, h) == "D"
    assert bt.classificar_regiao_bd(h - 1e-6, h) == "D"
    assert bt.classificar_regiao_bd(h, h) == "D"
    assert bt.classificar_regiao_bd(h + 1e-3, h) == "B"
    assert bt.classificar_regiao_bd(3.0 * h, h) == "B"
    with pytest.raises(bt.FaixaNormativaError):
        bt.classificar_regiao_bd(-1.0, h)
    with pytest.raises(bt.FaixaNormativaError):
        bt.classificar_regiao_bd(10.0, 0.0)


# =============================================================================
# 22.3.1 — Treliça idealizada de bielas, tirantes e nós (PDF p. 203-204)
# =============================================================================
def _trelica_tres_barras(P: float = 60.0) -> bt.TrelicaBT:
    """A(0,0) e B(400,0) apoiados, C(200,150) carregado com P para baixo.
    sen(theta) = 150/250 = 0,6; tg(theta) = 150/200 = 0,75."""
    t = bt.TrelicaBT("treliça de conferência", espacial=False)
    t.no("A", 0.0, 0.0).no("B", 400.0, 0.0).no("C", 200.0, 150.0)
    t.barra("AB", "A", "B").barra("AC", "A", "C").barra("CB", "C", "B")
    t.apoio("A", "ux", "uy").apoio("B", "uy")
    t.forca("C", Fy_kn=-P)
    return t


def test_trelica_bt_classifica_biela_e_tirante():
    # nó C: 2*N*sen(theta) = P -> N = -60/(2*0,6) = -50 kN (compressão)
    # nó A: N_AB = -N_AC*cos(theta) = 50*0,8 = 40 kN? Não: pelo momento,
    # N_AB = (P/2)/tg(theta) = 30/0,75 = 40 kN (tração)
    r = _trelica_tres_barras(60.0).resolver()
    assert r.N_kn("AC") == pytest.approx(-50.0)
    assert r.N_kn("CB") == pytest.approx(-50.0)
    assert r.N_kn("AB") == pytest.approx(40.0)
    assert r.bielas == ("AC", "CB")
    assert r.tirantes == ("AB",)
    assert r.nulas == ()
    assert r.barras["AC"].tipo == "biela"
    assert r.barras["AB"].tipo == "tirante"
    # reações: 30 kN em cada apoio
    assert r.reacoes["A"]["uy"] == pytest.approx(30.0)
    assert r.reacoes["B"]["uy"] == pytest.approx(30.0)
    assert r.governante == "22.3.1"
    assert any("isostática" in m for m in r.memoria)


def test_trelica_bt_inclinacao_e_comprimento():
    r = _trelica_tres_barras().resolver()
    # tg(theta) das bielas em relação ao eixo x (armadura longitudinal)
    assert r.barras["AC"].tan_theta == pytest.approx(0.75)
    assert r.barras["CB"].tan_theta == pytest.approx(0.75)
    assert r.barras["AB"].tan_theta == pytest.approx(0.0)
    assert r.barras["AC"].L_cm == pytest.approx(250.0)
    # eixo longitudinal vertical: a inclinação inverte (tg = 200/150)
    r2 = _trelica_tres_barras().resolver(eixo_longitudinal=(0.0, 1.0, 0.0))
    assert r2.barras["AC"].tan_theta == pytest.approx(200.0 / 150.0)
    assert r2.barras["AB"].tan_theta == math.inf


def test_trelica_bt_hipostatica_recusada():
    # 2 barras + 3 apoios - 2*3 nós = -1 -> mecanismo
    t = bt.TrelicaBT("sem banzo inferior")
    t.no("A", 0.0, 0.0).no("B", 400.0, 0.0).no("C", 200.0, 150.0)
    t.barra("AC", "A", "C").barra("CB", "C", "B")
    t.apoio("A", "ux", "uy").apoio("B", "uy")
    t.forca("C", Fy_kn=-60.0)
    assert t.grau_estatico() == -1
    with pytest.raises(bt.TrelicaNaoIsostaticaError) as exc:
        t.resolver()
    msg = str(exc.value)
    assert "isostática" in msg and "hipostática" in msg and "-1" in msg


def test_trelica_bt_hiperestatica_recusada():
    # 3 barras + 4 apoios - 2*3 nós = +1 -> redundância
    t = _trelica_tres_barras()
    t.apoio("B", "ux")
    assert t.grau_estatico() == 1
    with pytest.raises(bt.TrelicaNaoIsostaticaError) as exc:
        t.resolver()
    assert "hiperestática" in str(exc.value)


def test_trelica_bt_forma_critica_recusada():
    # contagem fecha (3 barras + 3 apoios - 2*3 nós = 0), mas os três nós
    # são colineares: matriz singular
    t = bt.TrelicaBT("forma crítica")
    t.no("A", 0.0, 0.0).no("B", 200.0, 0.0).no("C", 400.0, 0.0)
    t.barra("AB", "A", "B").barra("BC", "B", "C").barra("AC", "A", "C")
    t.apoio("A", "ux", "uy").apoio("C", "uy")
    t.forca("B", Fy_kn=-10.0)
    assert t.grau_estatico() == 0
    with pytest.raises(bt.TrelicaNaoIsostaticaError) as exc:
        t.resolver()
    assert "forma crítica" in str(exc.value)


def test_trelica_bt_autoequilibrada():
    # mesma treliça, agora com as reações de apoio (30 kN em cada) entrando
    # como força nodal, que é a forma literal de 22.3.1
    t = bt.TrelicaBT("autoequilibrada")
    t.no("A", 0.0, 0.0).no("B", 400.0, 0.0).no("C", 200.0, 150.0)
    t.barra("AB", "A", "B").barra("AC", "A", "C").barra("CB", "C", "B")
    t.forca("C", Fy_kn=-60.0).forca("A", Fy_kn=30.0).forca("B", Fy_kn=30.0)
    assert t.grau_estatico() == 0    # 3 barras + 3 corpo rígido - 2*3 nós
    r = t.resolver()
    assert r.autoequilibrado is True
    assert r.N_kn("AC") == pytest.approx(-50.0)
    assert r.N_kn("AB") == pytest.approx(40.0)
    assert r.reacoes == {}


def test_trelica_bt_nao_autoequilibrada_recusada():
    t = bt.TrelicaBT("sem reações")
    t.no("A", 0.0, 0.0).no("B", 400.0, 0.0).no("C", 200.0, 150.0)
    t.barra("AB", "A", "B").barra("AC", "A", "C").barra("CB", "C", "B")
    t.forca("C", Fy_kn=-60.0)
    with pytest.raises(bt.TrelicaNaoAutoequilibradaError) as exc:
        t.resolver()
    assert "autoequilibrado" in str(exc.value)


def test_trelica_bt_erros_de_montagem():
    t = bt.TrelicaBT("erros")
    t.no("A", 0.0, 0.0).no("B", 100.0, 0.0)
    with pytest.raises(ValueError):
        t.no("A", 5.0, 5.0)                 # nó repetido
    with pytest.raises(ValueError):
        t.no("Z", 0.0, 0.0, 10.0)           # z em treliça plana
    with pytest.raises(ValueError):
        t.barra("x", "A", "Q")              # nó inexistente
    with pytest.raises(ValueError):
        t.barra("x", "A", "A")              # nós iguais
    with pytest.raises(ValueError):
        t.apoio("A", "rz")                  # grau de rotação não existe
    with pytest.raises(ValueError):
        t.forca("A", Fz_kn=10.0)            # z em treliça plana


def test_verificar_inclinacoes_bielas_nos_dois_lados_da_faixa():
    # 22.3.1, p. 204: 0,57 <= tg(theta) <= 2 nas bielas inclinadas.
    # Treliça A(0,0)-B(2a,0)-C(a, a*tg) com tg escolhida em cada caso.
    def _res(tg: float):
        a = 200.0
        t = bt.TrelicaBT(f"tg={tg}")
        t.no("A", 0.0, 0.0).no("B", 2 * a, 0.0).no("C", a, a * tg)
        t.barra("AB", "A", "B").barra("AC", "A", "C").barra("CB", "C", "B")
        t.apoio("A", "ux", "uy").apoio("B", "uy")
        t.forca("C", Fy_kn=-100.0)
        return bt.verificar_inclinacoes_bielas(t.resolver())

    assert _res(0.57).ok is True                 # borda inferior
    assert _res(2.00).ok is True                 # borda superior
    assert _res(1.20).ok is True                 # ponto interior
    fora = _res(0.50)
    assert fora.ok is False and set(fora.fora_da_faixa) == {"AC", "CB"}
    assert _res(2.50).ok is False
    # o tirante horizontal do banzo não entra na conferência
    assert "AB" not in _res(1.20).tan_theta


def test_dimensionar_tirantes_usa_22_3_3():
    r = _trelica_tres_barras(60.0).resolver()
    As = bt.dimensionar_tirantes_cm2(r, FYD_KNCM2)
    # 22.3.3: As = FSd/fyd = 40/43,478 = 0,920 cm2
    assert set(As) == {"AB"}
    assert As["AB"] == pytest.approx(40.0 / FYD_KNCM2)
    assert As["AB"] == pytest.approx(bt.As_tirante_cm2(40.0, FYD_KNCM2))


# =============================================================================
# 22.4.3 — Modelos de cálculo de viga-parede (PDF p. 205)
# =============================================================================
def test_braco_alavanca_viga_parede_biapoiada():
    # z = 0,60*l para l/h < 1; z = 0,20*(l + 2h) para 1 <= l/h <= 2
    assert bt.braco_alavanca_viga_parede_cm(240.0, 400.0) == pytest.approx(144.0)
    # l/h = 1: as duas expressões coincidem (0,6*l = 0,2*3l)
    assert bt.braco_alavanca_viga_parede_cm(300.0, 300.0) == pytest.approx(180.0)
    # ponto interior l/h = 1,5: 0,2*(450 + 600) = 210
    assert bt.braco_alavanca_viga_parede_cm(450.0, 300.0) == pytest.approx(210.0)
    # borda superior l/h = 2: 0,2*(600 + 600) = 240
    assert bt.braco_alavanca_viga_parede_cm(600.0, 300.0) == pytest.approx(240.0)
    with pytest.raises(bt.FaixaNormativaError):
        bt.braco_alavanca_viga_parede_cm(601.0, 300.0)


def test_braco_alavanca_viga_parede_continua():
    # z = 0,50*l para l/h < 1; z = 0,20*(l + 1,5h) para 1 <= l/h <= 2,5
    assert bt.braco_alavanca_viga_parede_cm(240.0, 400.0, continua=True) == \
        pytest.approx(120.0)
    # l/h = 1: 0,5*l = 0,2*2,5l
    assert bt.braco_alavanca_viga_parede_cm(300.0, 300.0, continua=True) == \
        pytest.approx(150.0)
    # ponto interior l/h = 4/3: 0,2*(400 + 450) = 170
    assert bt.braco_alavanca_viga_parede_cm(400.0, 300.0, continua=True) == \
        pytest.approx(170.0)
    # borda superior l/h = 2,5: 0,2*(750 + 450) = 240
    assert bt.braco_alavanca_viga_parede_cm(750.0, 300.0, continua=True) == \
        pytest.approx(240.0)
    with pytest.raises(bt.FaixaNormativaError):
        bt.braco_alavanca_viga_parede_cm(751.0, 300.0, continua=True)
    with pytest.raises(bt.FaixaNormativaError):
        bt.braco_alavanca_viga_parede_cm(-1.0, 300.0)


def test_modelo_viga_parede_biapoiada_carga_concentrada():
    # l = 400, h = 300 -> l/h = 4/3 e z = 0,2*(400 + 600) = 200 cm.
    # T = P*l/(4z) = 200*400/800 = 100 kN; biela: sen(theta) = z/L com
    # L = sqrt(200^2 + 200^2) -> C = -(P/2)/sen(theta) = -100*sqrt(2)
    l, h, P = 400.0, 300.0, 200.0
    z = bt.braco_alavanca_viga_parede_cm(l, h)
    assert z == pytest.approx(200.0)
    r = bt.modelo_viga_parede_biapoiada(l, h, P_kn=P).resolver()
    assert r.N_kn("A-B") == pytest.approx(P * l / (4.0 * z))
    assert r.N_kn("A-C") == pytest.approx(-100.0 * math.sqrt(2.0))
    assert r.N_kn("C-B") == pytest.approx(-100.0 * math.sqrt(2.0))
    assert r.tirantes == ("A-B",)
    assert r.reacoes["A"]["uy"] == pytest.approx(P / 2.0)


def test_modelo_viga_parede_biapoiada_carga_uniforme():
    # Q = q*l = 100 kN/m * 4 m = 400 kN; resultante de cada metade (200 kN)
    # concentrada no quarto de vão. T = Q*l/(8z) = 400*400/1600 = 100 kN,
    # que é o momento de vão q*l^2/8 dividido por z.
    l, h, q = 400.0, 300.0, 100.0
    z = bt.braco_alavanca_viga_parede_cm(l, h)
    Q = q * l / 100.0
    r = bt.modelo_viga_parede_biapoiada(l, h, q_kn_m=q).resolver()
    assert r.N_kn("A-C") == pytest.approx(Q * l / (8.0 * z))
    assert r.N_kn("C-B") == pytest.approx(Q * l / (8.0 * z))
    assert r.N_kn("T1-T2") == pytest.approx(-Q * l / (8.0 * z))
    # as diagonais T1-C e C-T2 existem só para fechar a isostaticidade
    assert set(r.nulas) == {"T1-C", "C-T2"}
    assert r.reacoes["A"]["uy"] == pytest.approx(Q / 2.0)


def test_modelo_viga_parede_biapoiada_entradas_invalidas():
    with pytest.raises(ValueError):
        bt.modelo_viga_parede_biapoiada(400.0, 300.0)
    with pytest.raises(ValueError):
        bt.modelo_viga_parede_biapoiada(400.0, 300.0, P_kn=10.0, q_kn_m=10.0)
    with pytest.raises(bt.FaixaNormativaError):
        bt.modelo_viga_parede_biapoiada(400.0, 300.0, P_kn=10.0, z_cm=400.0)


def test_modelo_viga_parede_continua_dois_vaos():
    # l = 400, h = 300 -> z = 0,2*(400 + 450) = 170 cm.
    # Q = q*l = 400 kN por vão; R_int = 1,25*Q = 500 kN (valor elástico de
    # dois vãos iguais); R_ext = (2*400 - 500)/2 = 150 kN.
    # Tirante de vão: R_ext*(l/2)/z = 150*200/170 = 176,47 kN.
    # Tirante negativo sobre o apoio: (Q - 2*R_ext)*(l/2)/z = 100*200/170.
    l, h, q = 400.0, 300.0, 100.0
    z = bt.braco_alavanca_viga_parede_cm(l, h, continua=True)
    Q = q * l / 100.0
    R_int = 1.25 * Q
    R_ext = (2.0 * Q - R_int) / 2.0
    r = bt.modelo_viga_parede_continua(l, h, q_kn_m=q).resolver()
    assert r.N_kn("A-C") == pytest.approx(R_ext * (l / 2.0) / z)
    assert r.N_kn("C-E") == pytest.approx(R_ext * (l / 2.0) / z)
    assert r.N_kn("T1-T2") == pytest.approx((Q - 2.0 * R_ext) * (l / 2.0) / z)
    assert "T1-T2" in r.tirantes          # banzo superior tracionado
    assert "A-T1" in r.bielas
    assert r.reacoes["A"]["uy"] == pytest.approx(R_ext)


def test_modelo_viga_parede_continua_reacao_informada():
    # 22.3.1 exige reação de análise prévia: informada, ela governa
    l, h, P = 400.0, 300.0, 300.0
    z = 250.0
    R_int = 800.0
    R_ext = (2.0 * P - R_int) / 2.0       # = -100 kN (apoio tracionado)
    r = bt.modelo_viga_parede_continua(l, h, P_kn=P, z_cm=z,
                                       R_interno_kn=R_int).resolver()
    assert r.reacoes["A"]["uy"] == pytest.approx(R_ext)
    assert r.N_kn("A-C") == pytest.approx(R_ext * (l / 2.0) / z)
    with pytest.raises(ValueError):
        bt.modelo_viga_parede_continua(l, h)


def test_verificar_apoio_viga_parede_nos_dois_lados_do_limite():
    # 22.4.3: verificação indireta da biela pela tensão vertical no apoio,
    # conforme 22.3.2. C30, nó CCT -> fcd3 = 0,72*alpha_v2*fcd.
    fck, b, la = 30.0, 20.0, 40.0
    fcd3 = bt.fcd3_kncm2(fck)
    R_lim = fcd3 * b * la
    ok = bt.verificar_apoio_viga_parede(R_lim * 0.999, b, la, fck)
    assert ok.ok is True and ok.governante == "22.4.3"
    assert ok.sigma_kncm2 == pytest.approx(R_lim * 0.999 / (b * la))
    reprova = bt.verificar_apoio_viga_parede(R_lim * 1.001, b, la, fck)
    assert reprova.ok is False
    # nó CCC usa fcd1, que é maior
    ccc = bt.verificar_apoio_viga_parede(R_lim * 1.001, b, la, fck, tipo="CCC")
    assert ccc.ok is True and ccc.fcd_no_kncm2 == pytest.approx(bt.fcd1_kncm2(fck))
    with pytest.raises(bt.FaixaNormativaError):
        bt.verificar_apoio_viga_parede(100.0, 0.0, la, fck)


# =============================================================================
# 22.7.3 — Modelo tridimensional de bloco sobre estacas (PDF p. 213)
# =============================================================================
def test_bloco_2_estacas_bate_com_metodo_das_bielas():
    # Aceite do pacote: mesma força no tirante do método das bielas que já
    # existe. Blévot: T = Nd*(2e - ap)/(8d); e = 200, ap = 40, d = 90,
    # Nd = 1000 -> T = 1000*360/720 = 500 kN.
    Nd, e, ap, d = 1000.0, 200.0, 40.0, 90.0
    t = bt.modelo_bloco_estacas([(-e / 2.0, 0.0), (e / 2.0, 0.0)], Nd, d, ap_cm=ap)
    r = t.resolver()
    T = r.N_kn(("tirante", 0, 1))
    assert T == pytest.approx(Nd * (2.0 * e - ap) / (8.0 * d))
    assert T == pytest.approx(500.0)
    # e a armadura de blocos_nbr6118 é 1,15*T/fyd (majoração de Blévot)
    assert bloc.As_principal_2_estacas(Nd, e, ap, d) == \
        pytest.approx(1.15 * T / FYD_KNCM2)
    # bielas: cada uma leva Nd/2 na vertical
    L = math.hypot(e / 2.0 - ap / 4.0, d)
    assert r.N_kn(("biela", 0)) == pytest.approx(-(Nd / 2.0) * L / d)
    assert r.barras[("biela", 0)].tipo == "biela"
    # tg(theta) da biela em relação ao eixo x (armadura do tirante)
    assert r.barras[("biela", 0)].tan_theta == pytest.approx(d / (e / 2.0 - ap / 4.0))
    assert t.espacial is False     # duas estacas alinhadas: treliça plana


def test_bloco_2_estacas_sem_recuo_do_pilar():
    # ap = 0: a biela parte do eixo do pilar e T = Nd*e/(4d)
    Nd, e, d = 800.0, 160.0, 80.0
    r = bt.modelo_bloco_estacas([(-e / 2.0, 0.0), (e / 2.0, 0.0)], Nd, d).resolver()
    assert r.N_kn(("tirante", 0, 1)) == pytest.approx(Nd * e / (4.0 * d))


def test_bloco_3_estacas_trelica_espacial():
    # 3 estacas em triângulo equilátero de circunraio R (ap = 0).
    # Cada biela leva Nd/3 na vertical -> empuxo radial H = (Nd/3)*R/d.
    # No vértice, os dois tirantes do perímetro fazem 30 graus com o raio:
    # 2*T*cos(30) = H -> T = H/sqrt(3).
    Nd, R, d = 1200.0, 115.4700538, 100.0
    pos = [(R * math.cos(a), R * math.sin(a))
           for a in (math.pi / 2, math.pi / 2 + 2 * math.pi / 3,
                     math.pi / 2 + 4 * math.pi / 3)]
    t = bt.modelo_bloco_estacas(pos, Nd, d)
    assert t.espacial is True
    assert t.grau_estatico() == 0       # 3 bielas + 3 tirantes + 6 - 3*4
    r = t.resolver()
    H = (Nd / 3.0) * R / d
    T = H / math.sqrt(3.0)
    for par in ((0, 1), (0, 2), (1, 2)):
        assert r.N_kn(("tirante",) + par) == pytest.approx(T)
    assert r.N_kn(("biela", 0)) == pytest.approx(-(Nd / 3.0) * math.hypot(R, d) / d)


def test_bloco_4_estacas_tirantes_do_perimetro():
    # 4 estacas em quadrado de meio-espaçamento s, pilar quadrado ap.
    # Nó do modelo recuado de ap/4 em cada componente: r = s - ap/4.
    # Cada biela leva Nd/4; o empuxo horizontal (Nd/4)*(r,r)/d se equilibra
    # com os dois tirantes do lado: T = Nd*r/(4d).
    Nd, s, ap, d = 1600.0, 100.0, 40.0, 100.0
    rr = s - ap / 4.0
    t = bt.modelo_bloco_estacas([(-s, -s), (s, -s), (s, s), (-s, s)], Nd, d,
                                ap_cm=ap)
    assert t.grau_estatico() == 0       # 4 bielas + 5 tirantes + 6 - 3*5
    r = t.resolver()
    lados = [b for b in r.barras.values()
             if b.tipo == "tirante" and b.L_cm == pytest.approx(2.0 * rr)]
    assert len(lados) == 4
    for b in lados:
        assert b.N_kn == pytest.approx(Nd * rr / (4.0 * d))
    # a diagonal, que existe só para fechar a isostaticidade, sai nula
    assert len(r.nulas) == 1
    assert r.barras[r.nulas[0]].L_cm == pytest.approx(2.0 * rr * math.sqrt(2.0))


def test_bloco_reacoes_informadas_e_erros():
    Nd, e, d = 1000.0, 200.0, 100.0
    pos = [(-e / 2.0, 0.0), (e / 2.0, 0.0)]
    # reações que não equilibram a força do pilar
    with pytest.raises(bt.TrelicaNaoAutoequilibradaError):
        bt.modelo_bloco_estacas(pos, Nd, d, reacoes_estacas_kn=[400.0, 400.0]).resolver()
    # reações informadas corretas: mesma resposta do padrão
    r = bt.modelo_bloco_estacas(pos, Nd, d,
                                reacoes_estacas_kn=[500.0, 500.0]).resolver()
    assert r.N_kn(("tirante", 0, 1)) == pytest.approx(Nd * e / (4.0 * d))
    with pytest.raises(ValueError):
        bt.modelo_bloco_estacas(pos, Nd, d, reacoes_estacas_kn=[500.0])
    with pytest.raises(ValueError):
        bt.modelo_bloco_estacas([(0.0, 0.0)], Nd, d)
    with pytest.raises(bt.FaixaNormativaError):
        bt.modelo_bloco_estacas(pos, Nd, 0.0)


def test_bloco_5_estacas_exige_topologia_isostatica():
    # F4 (fechamento de 22.7.3): sem tirantes informados, o reticulado passou
    # a ser escolhido por topologia_tirantes_bloco e já fecha a isostaticidade
    # de 22.3.1 (antes do F4 este caso levantava TrelicaNaoIsostaticaError,
    # porque só havia perímetro). A contagem é 5 bielas + 2*5-3 = 7 tirantes
    # + 6 graus de corpo rígido - 3*6 nós = 0.
    pos = [(100.0, 0.0), (0.0, 100.0), (-100.0, 0.0), (0.0, -100.0), (0.0, 0.0)]
    t = bt.modelo_bloco_estacas(pos, 2000.0, 100.0)
    assert t.grau_estatico() == 0
    assert sum(1 for b in t.barras if b[0] == "tirante") == 7
    t.resolver()
    # com a topologia informada pelo projetista, a contagem também fecha
    t2 = bt.modelo_bloco_estacas(
        pos, 2000.0, 100.0,
        tirantes=[(0, 1), (1, 2), (2, 3), (3, 0), (4, 0), (4, 1), (4, 2)])
    assert t2.grau_estatico() == 0      # 5 bielas + 7 tirantes + 6 - 3*6
    r = t2.resolver()
    # a estaca central fica sob o pilar: biela vertical, sem empuxo
    assert r.barras[("biela", 4)].tan_theta == math.inf
    # o equilíbrio vertical devolve a reação de cada estaca (2000/5 = 400)
    assert sum(1 for b in r.barras.values() if b.tipo == "biela") == 5


# =============================================================================
# 22.6.3 — Modelo tridimensional de sapata (PDF p. 212)
# =============================================================================
def _tirantes_por_direcao(trelica, resultado):
    tx = ty = 0.0
    for b in resultado.barras.values():
        if not b.id[0] == "tirante":
            continue
        pi, pj = trelica.nos[b.no_i], trelica.nos[b.no_j]
        if abs(pi[1] - pj[1]) < 1e-9:
            tx += b.N_kn
        elif abs(pi[0] - pj[0]) < 1e-9:
            ty += b.N_kn
    return tx, ty


def test_modelo_sapata_centrada_bate_com_metodo_das_bielas():
    # a soma dos dois tirantes paralelos a x é Nd*(a - ap)/(8d), que é o
    # tracao_base_bielas de sapatas_nbr6118; idem em y com b e bp.
    a, b, ap, bp, d, Nd = 240.0, 180.0, 40.0, 30.0, 60.0, 1200.0
    t = bt.modelo_sapata(a, b, ap, bp, d, Nd)
    r = t.resolver()
    tx, ty = _tirantes_por_direcao(t, r)
    assert tx == pytest.approx(sap.tracao_base_bielas(Nd, a, ap, d))
    assert ty == pytest.approx(sap.tracao_base_bielas(Nd, b, bp, d))
    assert tx == pytest.approx(Nd * (a - ap) / (8.0 * d))
    assert ty == pytest.approx(Nd * (b - bp) / (8.0 * d))
    assert len(r.bielas) == 4
    assert len(r.nulas) == 1            # a diagonal de fechamento


def test_modelo_sapata_excentrica():
    # ex = 20 cm: as reações dos quadrantes saem da distribuição linear de
    # sapata rígida sobre os nós do modelo, em x = +-(a - ap)/4 = +-50 cm.
    # R = Nd/4 +- Nd*ex*x/Sx, Sx = 4*50^2 = 10000 -> 420 e 180 kN.
    a, b, ap, bp, d, Nd, ex = 240.0, 180.0, 40.0, 30.0, 60.0, 1200.0, 20.0
    t = bt.modelo_sapata(a, b, ap, bp, d, Nd, ex_cm=ex)
    r = t.resolver()
    assert r.autoequilibrado is True    # as reações entram como força nodal
    forcas = sorted(round(float(F[2]), 6) for F in t.forcas.values())
    assert forcas[0] == pytest.approx(-Nd)
    assert forcas[1:] == [pytest.approx(180.0), pytest.approx(180.0),
                          pytest.approx(420.0), pytest.approx(420.0)]
    # a direção y não muda: soma dos tirantes paralelos a y continua a mesma
    _, ty = _tirantes_por_direcao(t, r)
    assert ty == pytest.approx(Nd * (b - bp) / (8.0 * d))


def test_modelo_sapata_pilar_nao_cabe():
    with pytest.raises(bt.FaixaNormativaError):
        bt.modelo_sapata(100.0, 100.0, 120.0, 40.0, 50.0, 500.0)
    with pytest.raises(bt.FaixaNormativaError):
        bt.modelo_sapata(0.0, 100.0, 20.0, 40.0, 50.0, 500.0)


# =============================================================================
# 21.2.3 — Região de introdução da protensão (PDF p. 199)
# =============================================================================
def test_prisma_simetrico_e_posicao_do_tirante():
    assert bt.prisma_simetrico_cm(80.0) == pytest.approx(80.0)
    assert bt.prisma_simetrico_cm(80.0, 10.0) == pytest.approx(60.0)
    assert bt.prisma_simetrico_cm(80.0, -10.0) == pytest.approx(60.0)
    assert bt.posicao_fendilhamento_cm(80.0) == pytest.approx(40.0)
    assert bt.posicao_fendilhamento_cm(80.0, 10.0) == pytest.approx(30.0)
    with pytest.raises(bt.FaixaNormativaError):
        bt.prisma_simetrico_cm(80.0, 40.0)
    with pytest.raises(bt.FaixaNormativaError):
        bt.prisma_simetrico_cm(0.0)


def test_forca_fendilhamento_expressao_fechada():
    # T = 0,25*P*(1 - a/h'), do prisma simétrico (Guyon; Schlaich & Schäfer;
    # AASHTO LRFD 5.9.5.6.5a). P = 1000 kN, h = 80 cm.
    P, h = 1000.0, 80.0
    # borda inferior da faixa: a -> 0 dá T -> 0,25*P
    assert bt.forca_fendilhamento_kn(P, 1e-9, h) == pytest.approx(250.0, abs=1e-6)
    # ponto interior a = 20 cm: 0,25*1000*(1 - 0,25) = 187,5 kN
    assert bt.forca_fendilhamento_kn(P, 20.0, h) == pytest.approx(187.5)
    # borda superior: a -> h' dá T -> 0
    assert bt.forca_fendilhamento_kn(P, h - 1e-9, h) == pytest.approx(0.0, abs=1e-6)
    # excêntrica: h' = 80 - 2*10 = 60 -> 0,25*1000*(1 - 20/60) = 166,67 kN
    assert bt.forca_fendilhamento_kn(P, 20.0, h, e_cm=10.0) == \
        pytest.approx(1000.0 / 6.0)
    with pytest.raises(bt.FaixaNormativaError):
        bt.forca_fendilhamento_kn(P, h, h)
    with pytest.raises(bt.FaixaNormativaError):
        bt.forca_fendilhamento_kn(P, 0.0, h)


def test_modelo_zona_ancoragem_equilibrio_do_no():
    # a treliça do prisma simétrico tem de fechar o nó: a biela leva P/2 na
    # horizontal e T na vertical, com tg(theta) = ((h'-a)/4)/(h'/2).
    P, a, h = 1000.0, 20.0, 80.0
    r = bt.modelo_zona_ancoragem(P, a, h)
    assert r.T_fendilhamento_kn == pytest.approx(bt.forca_fendilhamento_kn(P, a, h))
    assert r.T_fendilhamento_kn == pytest.approx(187.5)
    assert r.x_tirante_cm == pytest.approx(40.0)
    assert r.h_prisma_cm == pytest.approx(80.0)
    assert r.tan_theta == pytest.approx(((h - a) / 4.0) / (h / 2.0))
    # componentes da biela: L = sqrt(40^2 + 15^2) = 42,720
    L = math.hypot(h / 2.0, (h - a) / 4.0)
    assert r.C_biela_kn == pytest.approx(-(P / 2.0) * L / (h / 2.0))
    cos = (h / 2.0) / L
    sen = ((h - a) / 4.0) / L
    assert abs(r.C_biela_kn) * cos == pytest.approx(P / 2.0)
    assert abs(r.C_biela_kn) * sen == pytest.approx(r.T_fendilhamento_kn)
    assert r.governante == "21.2.3"


def test_modelo_zona_ancoragem_armadura_e_esmagamento():
    # 22.3.3: As = T/fyd; 22.3.2: nó CCT sob a placa de ancoragem.
    P, a, h, fck = 900.0, 25.0, 100.0, 40.0
    area = 600.0
    r = bt.modelo_zona_ancoragem(P, a, h, fck_mpa=fck, area_ancoragem_cm2=area,
                                 fyd_kncm2=FYD_KNCM2)
    T = 0.25 * P * (1.0 - a / h)
    assert r.T_fendilhamento_kn == pytest.approx(T)
    assert r.As_tirante_cm2 == pytest.approx(T / FYD_KNCM2)
    assert r.sigma_ancoragem_kncm2 == pytest.approx(P / area)
    assert r.no_ancoragem.fcd_no_kncm2 == pytest.approx(bt.fcd3_kncm2(fck))
    assert r.ok is (P / area <= bt.fcd3_kncm2(fck))
    # sem fck e sem área: só o tirante
    s = bt.modelo_zona_ancoragem(P, a, h)
    assert s.no_ancoragem is None and s.sigma_ancoragem_kncm2 is None
    assert s.As_tirante_cm2 is None and s.ok is True
    with pytest.raises(bt.FaixaNormativaError):
        bt.modelo_zona_ancoragem(-1.0, a, h)
    with pytest.raises(bt.FaixaNormativaError):
        bt.modelo_zona_ancoragem(P, a, h, area_ancoragem_cm2=0.0)


def test_zona_ancoragem_regiao_d_coincide_com_22_2():
    # a extensão do prisma simétrico concêntrico é a própria região D de 22.2
    h = 90.0
    assert bt.prisma_simetrico_cm(h) == pytest.approx(bt.extensao_regiao_d_cm(h))
    assert bt.classificar_regiao_bd(bt.posicao_fendilhamento_cm(h), h) == "D"
