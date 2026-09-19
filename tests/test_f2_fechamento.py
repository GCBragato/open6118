"""Testes do F2 -- fechamento da flecha com armadura ativa (17.3.2.1.1 e
17.3.2.1.3) e do ELS de fissuração/descompressão de laje (19.3.2 -> 17.3.3
e 17.3.4).

Valores esperados tirados das imagens das páginas do PDF (SCRATCH/nbr_png):
p146 (17.3.2.1.1, expressão de Branson), p147 (Figura 17.3, rigidez
ponderada), p148 (17.3.2.1.3, flecha em elementos com armaduras ativas),
p150-151 (17.3.4, descompressão e formação de fissuras), p179 (19.3.2) e
p97-99 (Tabela 13.3, deslocamentos-limites). As contas à mão estão nos
comentários de cada teste; as soluções fechadas de flecha (5ql^4/384EI,
Pl^3/48EI, Pl^3/3EI) são resistência dos materiais, e servem para conferir a
integração numérica da curvatura.
"""

import math
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import els_deformacao_nbr6118 as ELS8  # noqa: E402
import els_fissuracao_nbr6118 as ELS9  # noqa: E402
import protendido_nbr6118 as PT  # noqa: E402


def _fctm(fck_mpa: float) -> float:
    """fct,m manual (8.2.5), sem importar o núcleo, só para montar o
    esperado dos testes deste arquivo."""
    if fck_mpa <= 50.0:
        return 0.3 * fck_mpa ** (2.0 / 3.0)
    return 2.12 * math.log(1.0 + 0.1 * (fck_mpa + 8.0))


# ===========================================================================
# 17.3.2.1.1, Figura 17.3 -- rigidez equivalente ponderada (PDF p. 147)
# ===========================================================================
def test_rigidez_ponderada_a1_a2_padrao_0_15():
    """Figura 17.3 (p. 147): (EI)eq = [(EI)1·a1 + (EI)v·av + (EI)2·a2]/l,
    com a1/l = a2/l = 0,15 ("pode-se adotar a1/l e a2/l aproximadamente
    iguais a 0,15"). l = 600 -> a1 = a2 = 90, av = 420.
    Conta: (1e6·90 + 2e6·420 + 3e6·90)/600 = 1,2e9/600 = 2,0e6."""
    ei = ELS8.rigidez_equivalente_ponderada_kncm2(1.0e6, 2.0e6, 3.0e6, 600.0)
    assert ei == pytest.approx(2.0e6, rel=1e-12)


def test_rigidez_ponderada_a1_a2_explicitos():
    """Figura 17.3 (p. 147) com a1 = 100 cm e a2 = 50 cm, l = 600 ->
    av = 450. Conta: (1e6·100 + 2e6·450 + 3e6·50)/600 = 1,15e9/600 =
    1.916.666,667."""
    ei = ELS8.rigidez_equivalente_ponderada_kncm2(
        1.0e6, 2.0e6, 3.0e6, 600.0, a1_cm=100.0, a2_cm=50.0)
    assert ei == pytest.approx(1.15e9 / 600.0, rel=1e-12)


def test_rigidez_ponderada_tres_trechos_iguais():
    """Rigidez igual nos três trechos: a ponderação da Figura 17.3 devolve
    a própria rigidez, qualquer que seja a divisão do vão."""
    for a1, a2 in ((None, None), (0.0, 0.0), (100.0, 200.0)):
        ei = ELS8.rigidez_equivalente_ponderada_kncm2(
            5.0e7, 5.0e7, 5.0e7, 800.0, a1_cm=a1, a2_cm=a2)
        assert ei == pytest.approx(5.0e7, rel=1e-12)


def test_rigidez_ponderada_borda_sem_trecho_negativo():
    """Borda a1 = a2 = 0 (vão biapoiado, sem trecho de momento negativo):
    av = l e o resultado é (EI)eq,v."""
    ei = ELS8.rigidez_equivalente_ponderada_kncm2(
        1.0e6, 2.0e6, 3.0e6, 600.0, a1_cm=0.0, a2_cm=0.0)
    assert ei == pytest.approx(2.0e6, rel=1e-12)


def test_rigidez_ponderada_borda_sem_trecho_positivo():
    """Borda oposta, a1 + a2 = l: av = 0 e só os dois trechos de apoio
    pesam. Conta: (1e6·300 + 3e6·300)/600 = 1,2e9/600 = 2,0e6."""
    ei = ELS8.rigidez_equivalente_ponderada_kncm2(
        1.0e6, 2.0e6, 3.0e6, 600.0, a1_cm=300.0, a2_cm=300.0)
    assert ei == pytest.approx(2.0e6, rel=1e-12)


def test_rigidez_ponderada_fora_da_faixa():
    """a1 + a2 acima do vão não deixa trecho de momento positivo; vão e
    rigidezes não positivos também são erro."""
    with pytest.raises(ValueError):
        ELS8.rigidez_equivalente_ponderada_kncm2(
            1.0e6, 2.0e6, 3.0e6, 600.0, a1_cm=400.0, a2_cm=300.0)
    with pytest.raises(ValueError):
        ELS8.rigidez_equivalente_ponderada_kncm2(
            1.0e6, 2.0e6, 3.0e6, 600.0, a1_cm=-1.0)
    with pytest.raises(ValueError):
        ELS8.rigidez_equivalente_ponderada_kncm2(1.0e6, 2.0e6, 3.0e6, 0.0)
    with pytest.raises(ValueError):
        ELS8.rigidez_equivalente_ponderada_kncm2(0.0, 2.0e6, 3.0e6, 600.0)


# ===========================================================================
# 17.3.2.1 -- flecha imediata por integração da curvatura (PDF p. 146)
# ===========================================================================
_L_CM = 600.0
_EI_KNCM2 = 1.0e8
_N_EST = 201


def _estacoes(n: int = _N_EST, l_cm: float = _L_CM) -> list[float]:
    return [l_cm * i / (n - 1) for i in range(n)]


def test_flecha_curvatura_biapoiada_carga_uniforme():
    """Viga biapoiada com carga uniforme: a integração da curvatura tem de
    reproduzir 5·q·l^4/(384·EI). q = 0,2 kN/cm, l = 600 cm, EI = 1e8 kN.cm2
    -> 5·0,2·600^4/(384·1e8) = 1,296e11/3,84e10 = 3,375 cm.
    M(x) = q·x·(l − x)/2."""
    q = 0.2
    xs = _estacoes()
    ms = [q * x * (_L_CM - x) / 2.0 for x in xs]
    f = ELS8.flecha_imediata_curvatura_cm(xs, ms, _EI_KNCM2)
    assert f == pytest.approx(3.375, rel=1e-4)


def test_flecha_curvatura_biapoiada_carga_concentrada_meio_do_vao():
    """Viga biapoiada com carga P no meio do vão: P·l^3/(48·EI).
    P = 10 kN, l = 600, EI = 1e8 -> 10·2,16e8/(4,8e9) = 0,45 cm."""
    P = 10.0
    xs = _estacoes()
    ms = [P * x / 2.0 if x <= _L_CM / 2.0 else P * (_L_CM - x) / 2.0 for x in xs]
    f = ELS8.flecha_imediata_curvatura_cm(xs, ms, _EI_KNCM2)
    assert f == pytest.approx(0.45, rel=1e-4)


def test_flecha_curvatura_biapoiada_ponto_diferente_do_meio():
    """Flecha no quarto do vão (x = 150 cm) da biapoiada com carga
    uniforme: f(a) = q·a·(l^3 − 2·l·a^2 + a^3)/(24·EI).
    Conta: 0,2·150·(2,16e8 − 2,7e7 + 3,375e6)/(24·1e8)
         = 30·1,92375e8/2,4e9 = 2,4046875 cm."""
    q = 0.2
    a = 150.0
    xs = _estacoes()
    ms = [q * x * (_L_CM - x) / 2.0 for x in xs]
    f = ELS8.flecha_imediata_curvatura_cm(xs, ms, _EI_KNCM2, x_flecha_cm=a)
    esperado = q * a * (_L_CM ** 3 - 2.0 * _L_CM * a ** 2 + a ** 3) / (24.0 * _EI_KNCM2)
    assert esperado == pytest.approx(2.4046875, rel=1e-12)
    assert f == pytest.approx(esperado, rel=1e-4)


def test_flecha_curvatura_balanco_carga_na_ponta():
    """Balanço engastado em x = 0 com carga P na extremidade livre:
    P·l^3/(3·EI). P = 10, l = 600, EI = 1e8 -> 10·2,16e8/3e8 = 7,2 cm.
    M(x) = −P·(l − x) (momento negativo, fibra superior tracionada)."""
    P = 10.0
    xs = _estacoes()
    ms = [-P * (_L_CM - x) for x in xs]
    f = ELS8.flecha_imediata_curvatura_cm(xs, ms, _EI_KNCM2, esquema="balanco")
    assert f == pytest.approx(7.2, rel=1e-4)


def test_flecha_curvatura_ei_por_estacao_igual_ao_escalar():
    """EI dado por estação, todas iguais, tem de dar o mesmo que o EI
    escalar; e dobrar a rigidez tem de dividir a flecha por dois (a
    integração é linear em 1/EI)."""
    q = 0.2
    xs = _estacoes()
    ms = [q * x * (_L_CM - x) / 2.0 for x in xs]
    f_escalar = ELS8.flecha_imediata_curvatura_cm(xs, ms, _EI_KNCM2)
    f_lista = ELS8.flecha_imediata_curvatura_cm(xs, ms, [_EI_KNCM2] * len(xs))
    f_dobro = ELS8.flecha_imediata_curvatura_cm(xs, ms, 2.0 * _EI_KNCM2)
    assert f_lista == pytest.approx(f_escalar, rel=1e-12)
    assert f_dobro == pytest.approx(f_escalar / 2.0, rel=1e-12)


def test_flecha_curvatura_ei_variavel_confere_com_trapezio_a_mao():
    """Rigidez variável ao longo do vão (Estádio I nos terços de apoio e
    Estádio II no terço central, 17.3.2.1): o resultado tem de bater com a
    regra do trapézio refeita à mão neste teste, sem usar a biblioteca."""
    q = 0.2
    xs = _estacoes(61)
    ms = [q * x * (_L_CM - x) / 2.0 for x in xs]
    eis = [_EI_KNCM2 if (x < _L_CM / 3.0 or x > 2.0 * _L_CM / 3.0)
           else 0.4 * _EI_KNCM2 for x in xs]
    # m(x) da carga virtual unitária no meio do vão: x/2 até o meio e
    # (l − x)/2 depois (viga biapoiada).
    mv = [x / 2.0 if x <= _L_CM / 2.0 else (_L_CM - x) / 2.0 for x in xs]
    g = [ms[i] * mv[i] / eis[i] for i in range(len(xs))]
    esperado = sum((g[i] + g[i - 1]) * (xs[i] - xs[i - 1]) / 2.0
                   for i in range(1, len(xs)))
    f = ELS8.flecha_imediata_curvatura_cm(xs, ms, eis)
    assert f == pytest.approx(esperado, rel=1e-12)


def test_flecha_curvatura_erros_de_entrada():
    """Entradas impossíveis levantam ValueError: menos de três estações, x
    não crescente, tamanhos diferentes, EI não positivo, esquema
    desconhecido e ponto fora do vão."""
    xs = _estacoes(11)
    ms = [0.1 * x * (_L_CM - x) / 2.0 for x in xs]
    with pytest.raises(ValueError):
        ELS8.flecha_imediata_curvatura_cm([0.0, 1.0], [0.0, 0.0], _EI_KNCM2)
    with pytest.raises(ValueError):
        ELS8.flecha_imediata_curvatura_cm([0.0, 2.0, 1.0], [0.0, 1.0, 0.0], _EI_KNCM2)
    with pytest.raises(ValueError):
        ELS8.flecha_imediata_curvatura_cm(xs, ms[:-1], _EI_KNCM2)
    with pytest.raises(ValueError):
        ELS8.flecha_imediata_curvatura_cm(xs, ms, 0.0)
    with pytest.raises(ValueError):
        ELS8.flecha_imediata_curvatura_cm(xs, ms, [_EI_KNCM2] * (len(xs) - 1))
    with pytest.raises(ValueError):
        ELS8.flecha_imediata_curvatura_cm(xs, ms, _EI_KNCM2, esquema="engastada")
    with pytest.raises(ValueError):
        ELS8.flecha_imediata_curvatura_cm(xs, ms, _EI_KNCM2, x_flecha_cm=700.0)


# ===========================================================================
# 17.3.2.1.3 -- fluxo completo da flecha de elemento protendido (PDF p. 148)
# ===========================================================================
# Viga de referência dos testes: Ecs = 3000 kN/cm2, seção retangular
# b = 30 cm e h = 40 cm -> Ic = 30·40^3/12 = 160.000 cm4, Ac = 1.200 cm2,
# W = Ic/yt = 160.000/20 = 8.000 cm3 (W/Ac = 6,6667 cm); seção fissurada
# III = 60.000 cm4; P = 500 kN, ep = 10 cm, Mr sem protensão = 1.500 kN.cm,
# l = 600 cm. Ecs·Ic = 3000·160.000 = 4,8e8 kN.cm2.
_ECS = 3000.0
_IC = 30.0 * 40.0 ** 3 / 12.0
_III = 60000.0
_AC = 1200.0
_W = 8000.0
_P = 500.0
_EP = 10.0
_MR_SEM_P = 1500.0
_MR_P = _MR_SEM_P + _P * (_EP + _W / _AC)   # 1500 + 500·16,6667 = 9.833,33


def _momentos_uniformes(q_kncm: float, n: int = 101) -> tuple[list[float], list[float]]:
    xs = _estacoes(n)
    return xs, [q_kncm * x * (_L_CM - x) / 2.0 for x in xs]


def test_flecha_protendido_fluxo_nao_fissurado():
    """17.3.2.1.3 (p. 148): "é suficiente considerar (EI)eq = Ecs·Ic, desde
    que não seja ultrapassado o estado-limite de formação de fissuras".
    Mr,p = 1500 + 500·(10 + 8000/1200) = 9.833,33 kN.cm; com q = 0,20
    kN/cm no total, Ma = q·l^2/8 = 0,2·360000/8 = 9.000 kN.cm < Mr,p ->
    (EI)eq = 3000·160000 = 4,8e8 kN.cm2.
    Flechas imediatas (5·q·l^4/384EI): permanente q = 0,15 ->
    5·0,15·1,296e11/(384·4,8e8) = 9,72e10/1,8432e11 = 0,52734375 cm;
    variável q = 0,05 -> 0,17578125 cm. Com phi = 2: f_total =
    0,17578125 + 0,52734375·3 = 1,7578125 cm. Limite l/250 = 2,4 cm
    (Tabela 13.3, p. 97) -> ok."""
    xs, mp = _momentos_uniformes(0.15)
    _, mv = _momentos_uniformes(0.05)
    r = PT.verificar_flecha_protendido(
        xs, mp, mv, _ECS, _IC, _III, _MR_SEM_P, _P, _EP, _AC, _W,
        phi=2.0, categoria="aceitabilidade_visual")
    assert r.Mr_protendido_kncm == pytest.approx(_MR_P, rel=1e-12)
    assert r.Ma_kncm == pytest.approx(9000.0, rel=1e-12)
    assert r.fissurado is False
    assert r.EI_eq_kncm2 == pytest.approx(_ECS * _IC, rel=1e-12)
    assert r.f_imediata_permanente_cm == pytest.approx(0.52734375, rel=1e-4)
    assert r.f_imediata_variavel_cm == pytest.approx(0.17578125, rel=1e-4)
    assert r.f_total_cm == pytest.approx(1.7578125, rel=1e-4)
    assert r.f_diferida_cm == pytest.approx(2.0 * 0.52734375, rel=1e-4)
    assert r.vao_limite_cm == pytest.approx(600.0, rel=1e-12)
    assert r.limite_cm == pytest.approx(2.4, rel=1e-12)
    assert r.ok is True
    assert any("17.3.2.1.3" in linha for linha in r.memoria)


def test_flecha_protendido_fluxo_fissurado_usa_branson():
    """Ultrapassado o estado-limite de formação de fissuras, 17.3.2.1.3
    manda aplicar a expressão completa de 17.3.2.1.1 (p. 146) com Mr da
    seção protendida. q total = 0,60 kN/cm -> Ma = 0,6·360000/8 = 27.000
    kN.cm > Mr,p = 9.833,33.
    (Mr/Ma)^3 = (9833,3333/27000)^3 = 0,36419753^3 = 0,0483071;
    (EI)eq = 3000·(0,0483071·160000 + 0,9516929·60000)
           = 3000·(7729,1 + 57101,6) = 1,9449e8 kN.cm2 (< Ecs·Ic = 4,8e8)."""
    xs, mp = _momentos_uniformes(0.60)
    # Com a seção fissurada e phi = 1, a flecha total passa de l/250; o
    # aviso é esperado e não é o objeto deste teste.
    with pytest.warns(nbr.AvisoNBR6118):
        r = PT.verificar_flecha_protendido(
            xs, mp, None, _ECS, _IC, _III, _MR_SEM_P, _P, _EP, _AC, _W,
            phi=1.0, categoria="aceitabilidade_visual")
    razao3 = (_MR_P / 27000.0) ** 3
    ei_esperado = _ECS * (razao3 * _IC + (1.0 - razao3) * _III)
    assert razao3 == pytest.approx(0.0483071, rel=1e-5)
    assert ei_esperado == pytest.approx(1.9449e8, rel=1e-4)
    assert r.fissurado is True
    assert r.EI_eq_kncm2 == pytest.approx(ei_esperado, rel=1e-12)
    assert r.EI_eq_kncm2 < _ECS * _IC
    # Sem parcela variável: f_total = f_permanente·(1 + phi) = 2·f_imediata.
    assert r.f_imediata_variavel_cm == pytest.approx(0.0, abs=1e-12)
    assert r.f_total_cm == pytest.approx(2.0 * r.f_imediata_permanente_cm, rel=1e-12)


def test_flecha_protendido_fluxo_phi_zero():
    """phi = 0 (sem fluência): 17.3.2.1.3 dá f_total = f_imediata, e a
    flecha diferida é nula."""
    xs, mp = _momentos_uniformes(0.15)
    _, mv = _momentos_uniformes(0.05)
    r = PT.verificar_flecha_protendido(
        xs, mp, mv, _ECS, _IC, _III, _MR_SEM_P, _P, _EP, _AC, _W,
        phi=0.0, categoria="aceitabilidade_visual")
    assert r.f_total_cm == pytest.approx(r.f_imediata_cm, rel=1e-12)
    assert r.f_diferida_cm == pytest.approx(0.0, abs=1e-12)


def test_flecha_protendido_fluxo_acima_do_limite_avisa():
    """Flecha total acima do limite da Tabela 13.3: ok = False e
    AvisoNBR6118. Categoria 'alvenaria' (p. 98): min(l/500, 10 mm) =
    min(1,2 cm, 1,0 cm) = 1,0 cm, abaixo da flecha total de 1,0547 cm do
    caso não fissurado."""
    xs, mp = _momentos_uniformes(0.15)
    _, mv = _momentos_uniformes(0.05)
    with pytest.warns(nbr.AvisoNBR6118):
        r = PT.verificar_flecha_protendido(
            xs, mp, mv, _ECS, _IC, _III, _MR_SEM_P, _P, _EP, _AC, _W,
            phi=2.0, categoria="alvenaria")
    assert r.limite_cm == pytest.approx(1.0, rel=1e-12)
    assert r.ok is False
    assert "acima do limite" in r.governante


def test_flecha_protendido_fluxo_categoria_sem_limite_numerico():
    """Tabela 13.3, 'Elementos que suportam equipamentos sensíveis'
    (p. 98): o limite é a recomendação do fabricante, sem número -> a
    verificação devolve limite None e ok None."""
    xs, mp = _momentos_uniformes(0.15)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        r = PT.verificar_flecha_protendido(
            xs, mp, None, _ECS, _IC, _III, _MR_SEM_P, _P, _EP, _AC, _W,
            phi=2.0, categoria="equipamento_sensivel")
    assert r.limite_cm is None
    assert r.ok is None


def test_flecha_protendido_fluxo_balanco_vao_equivalente_e_ma_no_apoio():
    """Balanço: 17.3.2.1.1 (p. 146) toma Ma como o momento no apoio, e a
    Tabela 13.3, NOTA 1 (p. 99) manda usar vão equivalente = 2·l. Balanço
    de 200 cm com carga uniforme q = 0,10 kN/cm: M(x) = −q·(l − x)^2/2,
    Ma = |M(0)| = 0,1·200^2/2 = 2.000 kN.cm; vão-limite = 400 cm."""
    l_bal = 200.0
    q = 0.10
    xs = [l_bal * i / 40.0 for i in range(41)]
    mp = [-q * (l_bal - x) ** 2 / 2.0 for x in xs]
    r = PT.verificar_flecha_protendido(
        xs, mp, None, _ECS, _IC, _III, _MR_SEM_P, _P, _EP, _AC, _W,
        phi=1.0, categoria="aceitabilidade_visual", esquema="balanco")
    assert r.Ma_kncm == pytest.approx(2000.0, rel=1e-12)
    assert r.vao_limite_cm == pytest.approx(400.0, rel=1e-12)
    assert r.limite_cm == pytest.approx(400.0 / 250.0, rel=1e-12)
    # q·l^4/(8·EI) = 0,1·1,6e9/(8·4,8e8) = 1,6e8/3,84e9 = 0,0416667 cm.
    assert r.f_imediata_permanente_cm == pytest.approx(1.6e8 / 3.84e9, rel=1e-3)


def test_flecha_protendido_fluxo_erros_de_entrada():
    """Diagramas de tamanho diferente do de x e esquema desconhecido
    levantam ValueError."""
    xs, mp = _momentos_uniformes(0.15)
    with pytest.raises(ValueError):
        PT.verificar_flecha_protendido(
            xs, mp[:-1], None, _ECS, _IC, _III, _MR_SEM_P, _P, _EP, _AC, _W,
            phi=1.0, categoria="aceitabilidade_visual")
    with pytest.raises(ValueError):
        PT.verificar_flecha_protendido(
            xs, mp, None, _ECS, _IC, _III, _MR_SEM_P, _P, _EP, _AC, _W,
            phi=1.0, categoria="aceitabilidade_visual", esquema="engastada")


# ===========================================================================
# 19.3.2 (p. 179) -> 17.3.4 (p. 150-151): descompressão em faixa de laje
# ===========================================================================
# Faixa de laje de referência: b = 100 cm, h = 20 cm -> Ac = 2.000 cm2,
# W = 100·20^2/6 = 6.666,667 cm3. P = 300 kN, ep = 5 cm.
# sigma_base = −P/Ac − P·ep/W + M/W = −0,15 − 0,225 + M/6666,667 (kN/cm2).
_B_LAJE = 100.0
_H_LAJE = 20.0
_AC_LAJE = 2000.0
_W_LAJE = 100.0 * 20.0 ** 2 / 6.0
_P_LAJE = 300.0
_EP_LAJE = 5.0
_M_DESCOMPRESSAO = _P_LAJE * (_EP_LAJE + _W_LAJE / _AC_LAJE)  # 2.500 kN.cm


def test_descompressao_laje_els_d_no_degrau():
    """17.3.4 (p. 150-151): ELS-D tem tensão-limite de tração nula. No
    momento que zera a tensão na base, M = P·(ep + W/Ac) =
    300·(5 + 3,3333) = 2.500 kN.cm, a igualdade passa."""
    assert _M_DESCOMPRESSAO == pytest.approx(2500.0, rel=1e-12)
    r = ELS9.verificar_descompressao_laje(
        _P_LAJE, _EP_LAJE, _M_DESCOMPRESSAO, _B_LAJE, _H_LAJE, estado="ELS-D")
    assert r.sigma_base_kncm2 == pytest.approx(0.0, abs=1e-12)
    assert r.limite_kncm2 == pytest.approx(0.0, abs=1e-12)
    assert r.ok is True


def test_descompressao_laje_els_d_dos_dois_lados_do_degrau():
    """Um passo abaixo e um passo acima do momento de descompressão:
    M = 2.400 -> sigma_base = −0,015 kN/cm2 (toda a seção comprimida), ok;
    M = 2.600 -> sigma_base = +0,015 kN/cm2 (0,15 MPa de tração), não ok."""
    r_ok = ELS9.verificar_descompressao_laje(
        _P_LAJE, _EP_LAJE, 2400.0, _B_LAJE, _H_LAJE, estado="ELS-D")
    r_nao = ELS9.verificar_descompressao_laje(
        _P_LAJE, _EP_LAJE, 2600.0, _B_LAJE, _H_LAJE, estado="ELS-D")
    assert r_ok.sigma_base_kncm2 == pytest.approx(-0.015, rel=1e-9)
    assert r_ok.sigma_tracao_max_kncm2 == pytest.approx(0.0, abs=1e-12)
    assert r_ok.ok is True
    assert r_nao.sigma_base_kncm2 == pytest.approx(0.015, rel=1e-9)
    assert r_nao.ok is False


def test_descompressao_laje_els_f_limite_de_17_2_4_4_2():
    """ELS-F (17.3.4 com o limite de 17.2.4.4.2, p. 144): tensão-limite =
    0,7·alpha·fct,m, alpha = 1,5 na seção retangular da faixa de laje.
    fck = 35 -> fct,m = 0,3·35^(2/3) = 3,20996 MPa; limite = 1,05·3,20996 =
    3,37046 MPa = 0,337046 kN/cm2.
    M que leva a base exatamente ao limite:
    M = W·(limite + 0,375) = 6666,667·0,712046 = 4.746,97 kN.cm."""
    limite_kncm2 = 1.5 * 0.7 * _fctm(35.0) / 10.0
    assert limite_kncm2 * 10.0 == pytest.approx(3.370459, rel=1e-5)
    m_limite = _W_LAJE * (limite_kncm2 + 0.375)
    r_ok = ELS9.verificar_descompressao_laje(
        _P_LAJE, _EP_LAJE, m_limite, _B_LAJE, _H_LAJE,
        estado="ELS-F", fck_mpa=35.0)
    assert r_ok.limite_kncm2 == pytest.approx(limite_kncm2, rel=1e-12)
    assert r_ok.sigma_tracao_max_kncm2 == pytest.approx(limite_kncm2, rel=1e-9)
    assert r_ok.ok is True
    r_nao = ELS9.verificar_descompressao_laje(
        _P_LAJE, _EP_LAJE, m_limite * 1.01, _B_LAJE, _H_LAJE,
        estado="ELS-F", fck_mpa=35.0)
    assert r_nao.ok is False


def test_descompressao_laje_erros_de_entrada():
    """Faixa com dimensão não positiva, ELS-F sem fck e estado-limite
    desconhecido são erro."""
    with pytest.raises(ValueError):
        ELS9.verificar_descompressao_laje(
            _P_LAJE, _EP_LAJE, 2500.0, 0.0, _H_LAJE)
    with pytest.raises(ValueError):
        ELS9.verificar_descompressao_laje(
            _P_LAJE, _EP_LAJE, 2500.0, _B_LAJE, _H_LAJE, estado="ELS-F")
    with pytest.raises(ValueError):
        ELS9.verificar_descompressao_laje(
            _P_LAJE, _EP_LAJE, 2500.0, _B_LAJE, _H_LAJE, estado="ELS-X")


def test_descompressao_laje_equivale_a_verificacao_de_viga():
    """19.3.2 (p. 179) remete aos critérios de viga: a verificação da faixa
    de laje tem de dar exatamente o mesmo que
    protendido_nbr6118.verificar_descompressao_fissuracao com Ac = b·h e
    Wb = Wt = b·h^2/6."""
    r_laje = ELS9.verificar_descompressao_laje(
        _P_LAJE, _EP_LAJE, 3000.0, _B_LAJE, _H_LAJE,
        estado="ELS-F", fck_mpa=35.0)
    r_viga = PT.verificar_descompressao_fissuracao(
        P_kn=_P_LAJE, ep_cm=_EP_LAJE, M_kncm=3000.0, Ac_cm2=_AC_LAJE,
        Wb_cm3=_W_LAJE, Wt_cm3=_W_LAJE, estado="ELS-F", fck_mpa=35.0)
    assert r_laje == r_viga


# ===========================================================================
# 19.3.2 (p. 179) -- ponto de entrada único, com o critério da Tabela 13.4
# ===========================================================================
def test_els_laje_nivel_1_usa_abertura_de_fissura():
    """Tabela 13.4: protendido nível 1 (protensão parcial), pós-tração,
    CAA I -> wk,máx = 0,2 mm na combinação frequente. O critério é o de
    17.3.3, e o resultado tem de ser o mesmo de wk_verificacao."""
    r = ELS9.verificar_els_laje_protendida(
        caa="I", b_cm=_B_LAJE, h_cm=_H_LAJE, fck_mpa=35.0,
        nivel_protensao=1, tipo_protensao="pós-tração",
        phi_mm=10.0, sigma_si_kncm2=20.0, Acr_cm2=150.0, As_cm2=3.0)
    esperado = ELS9.wk_verificacao(
        phi_mm=10.0, sigma_si_kncm2=20.0, Acr_cm2=150.0, As_cm2=3.0,
        fck_mpa=35.0, caa="I", tipo_concreto="protendido",
        nivel_protensao=1, tipo_protensao="pós-tração")
    assert r.criterio.startswith("17.3.3")
    assert r.wk_max_mm == pytest.approx(0.2, rel=1e-12)
    assert "frequente" in r.exigencia_tabela_13_4
    assert r.fissuracao == esperado
    assert r.els_f is None and r.els_d is None
    assert r.ok is bool(esperado.ok)


def test_els_laje_concreto_armado_usa_wk_da_tabela_13_4():
    """Laje de concreto armado, CAA II: a Tabela 13.4 dá wk,máx = 0,3 mm
    (combinação frequente), e 19.3.2 (p. 179) manda usar os critérios de
    17.3.3 — os mesmos de viga, com a largura da faixa de laje."""
    r = ELS9.verificar_els_laje_protendida(
        caa="II", b_cm=_B_LAJE, h_cm=_H_LAJE, fck_mpa=30.0,
        tipo_concreto="armado",
        phi_mm=10.0, sigma_si_kncm2=20.0, Acr_cm2=150.0, As_cm2=3.0)
    assert r.criterio.startswith("17.3.3")
    assert r.wk_max_mm == pytest.approx(0.3, rel=1e-12)
    assert r.fissuracao is not None


def test_els_laje_nivel_2_usa_els_f_e_els_d():
    """Tabela 13.4: protendido nível 2 (protensão limitada), pós-tração,
    CAA II -> sem wk,máx; a exigência são ELS-F (combinação frequente) e
    ELS-D (combinação quase-permanente), as duas por 17.3.4 (p. 150-151).
    Com M(ELS-F) = 3.000 e M(ELS-D) = 2.400 kN.cm na faixa de referência:
    ELS-F -> sigma_base = 0,075 kN/cm2 < 0,337046 -> ok;
    ELS-D -> sigma_base = −0,015 kN/cm2 (comprimida) -> ok."""
    r = ELS9.verificar_els_laje_protendida(
        caa="II", b_cm=_B_LAJE, h_cm=_H_LAJE, fck_mpa=35.0,
        nivel_protensao=2, tipo_protensao="pós-tração",
        P_kn=_P_LAJE, ep_cm=_EP_LAJE,
        M_els_f_kncm=3000.0, M_els_d_kncm=2400.0)
    assert r.criterio.startswith("17.3.4")
    assert r.wk_max_mm is None
    assert "ELS-F" in r.exigencia_tabela_13_4 and "ELS-D" in r.exigencia_tabela_13_4
    assert r.els_f.sigma_base_kncm2 == pytest.approx(0.075, rel=1e-9)
    assert r.els_d.sigma_base_kncm2 == pytest.approx(-0.015, rel=1e-9)
    assert r.ok is True
    assert r.governante == "ELS-F e ELS-D atendidos"


def test_els_laje_nivel_3_combinacoes_rara_e_frequente():
    """Tabela 13.4: protendido nível 3 (protensão completa) -> ELS-F na
    combinação rara e ELS-D na frequente. Com M(ELS-D) = 2.600 kN.cm a
    seção tem tração e o ELS-D não passa."""
    r = ELS9.verificar_els_laje_protendida(
        caa="III", b_cm=_B_LAJE, h_cm=_H_LAJE, fck_mpa=35.0,
        nivel_protensao=3, tipo_protensao="pré-tração",
        P_kn=_P_LAJE, ep_cm=_EP_LAJE,
        M_els_f_kncm=3000.0, M_els_d_kncm=2600.0)
    assert "rara" in r.exigencia_tabela_13_4
    assert r.els_f.ok is True
    assert r.els_d.ok is False
    assert r.ok is False
    assert r.governante == "ELS-D não atendido"


def test_els_laje_caa_fora_da_tabela_13_4():
    """Tabela 13.4 não dá nível 1 com pré-tração fora da CAA I: o núcleo
    levanta FaixaNormativaError, e a fachada de laje não inventa valor."""
    with pytest.raises(nbr.FaixaNormativaError):
        ELS9.verificar_els_laje_protendida(
            caa="II", b_cm=_B_LAJE, h_cm=_H_LAJE, fck_mpa=35.0,
            nivel_protensao=1, tipo_protensao="pré-tração",
            phi_mm=10.0, sigma_si_kncm2=20.0, Acr_cm2=150.0, As_cm2=3.0)


def test_els_laje_faltando_dados_de_cada_criterio():
    """Cada critério exige os seus insumos: o de 17.3.3 exige phi, sigma_si,
    Acri e As; o de 17.3.4 exige P e os momentos das duas combinações."""
    with pytest.raises(ValueError) as e1:
        ELS9.verificar_els_laje_protendida(
            caa="I", b_cm=_B_LAJE, h_cm=_H_LAJE, fck_mpa=35.0,
            nivel_protensao=1, tipo_protensao="pós-tração")
    assert "phi_mm" in str(e1.value)
    with pytest.raises(ValueError) as e2:
        ELS9.verificar_els_laje_protendida(
            caa="II", b_cm=_B_LAJE, h_cm=_H_LAJE, fck_mpa=35.0,
            nivel_protensao=2, tipo_protensao="pós-tração", P_kn=_P_LAJE)
    assert "M_els_f_kncm" in str(e2.value)
