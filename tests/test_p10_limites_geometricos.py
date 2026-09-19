"""Testes do P10 — Limites geométricos e coeficiente γn.

Cobre dimensionamento/limites_geometricos_nbr6118.py contra a ABNT
NBR 6118:2026:

  - 13.2.2 (largura mínima de viga e viga-parede), p. 93
  - 13.2.3, Tabela 13.1 (dimensão/área mínima de pilar, γn), p. 93-94
  - 13.2.4.1 (espessuras mínimas de laje maciça a-g; Tabela 13.2, γn de laje
    em balanço), p. 94
  - 13.2.4.2 (mesa e nervura de laje nervurada; classificação a-c), p. 95
  - 13.2.5.1 (dispensa de furo em viga), p. 95-96
  - 13.2.5.2, Figura 13.1 (dispensa de abertura em laje), p. 96
  - 13.2.6 (canalizações embutidas proibidas), p. 96
  - 11.7.1 (remissão ao γn de elementos esbeltos), p. 84
  - 22.2 (γn de consolo e dente Gerber), p. 203

Os valores esperados vêm da imagem de cada página
(SCRATCH\\nbr_png\\pNNN.png), não do JSON do plano.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr                        # noqa: E402
import limites_geometricos_nbr6118 as lim            # noqa: E402
import lajes_nbr6118 as laj                          # noqa: E402
import pilares_nbr6118 as pil                        # noqa: E402


# =============================================================================
# 13.2.2 — Largura mínima de viga e viga-parede (p. 93)
# =============================================================================
def test_largura_minima_viga_comum():
    assert lim.largura_minima_viga_cm() == pytest.approx(12.0)


def test_largura_minima_viga_parede():
    assert lim.largura_minima_viga_cm(viga_parede=True) == pytest.approx(15.0)


def test_largura_minima_excepcional_absoluta_10cm():
    """13.2.2: casos excepcionais reduzem até o mínimo absoluto de 10 cm,
    tanto para viga comum quanto para viga-parede."""
    assert lim.largura_minima_viga_cm(excepcional=True) == pytest.approx(10.0)
    assert lim.largura_minima_viga_cm(viga_parede=True, excepcional=True) == pytest.approx(10.0)


@pytest.mark.parametrize("bw, viga_parede, excepcional, ok_esperado", [
    (12.0, False, False, True),    # bw = mínimo exato -> ok
    (11.9, False, False, False),   # abaixo do mínimo -> falha
    (10.0, False, True, True),     # mínimo absoluto excepcional -> ok
    (9.0, False, True, False),     # abaixo até do mínimo absoluto -> falha
    (15.0, True, False, True),
    (14.9, True, False, False),
])
def test_largura_minima_viga_uso_tipico(bw, viga_parede, excepcional, ok_esperado):
    minimo = lim.largura_minima_viga_cm(viga_parede=viga_parede, excepcional=excepcional)
    ok = bw + 1e-9 >= minimo
    assert ok == ok_esperado


# =============================================================================
# 13.2.3, Tabela 13.1 — γn de pilares e pilares-parede (p. 94)
# =============================================================================
@pytest.mark.parametrize("b_cm, gama_n_esperado", [
    (19.0, 1.00), (18.0, 1.05), (17.0, 1.10), (16.0, 1.15),
    (15.0, 1.20), (14.0, 1.25),
])
def test_tabela_13_1_gama_n_pilar_celula_a_celula(b_cm, gama_n_esperado):
    """Tabela 13.1 (b em cm -> γn), célula a célula, conferida na imagem (p. 94)."""
    assert lim.gama_n_pilar(b_cm) == pytest.approx(gama_n_esperado, abs=1e-9)


def test_gama_n_pilar_ponto_interior_14_5():
    """γn = 1,95 - 0,05*14,5 = 1,225 (fórmula contínua entre os degraus tabelados)."""
    assert lim.gama_n_pilar(14.5) == pytest.approx(1.225, abs=1e-9)


def test_gama_n_pilar_acima_de_19_fica_em_1():
    assert lim.gama_n_pilar(20.0) == pytest.approx(1.0, abs=1e-9)
    assert lim.gama_n_pilar(30.0) == pytest.approx(1.0, abs=1e-9)


def test_gama_n_pilar_abaixo_de_14_levanta_erro():
    """13.2.3: a norma não permite pilar/pilar-parede maciço com b < 14 cm."""
    with pytest.raises(nbr.FaixaNormativaError):
        lim.gama_n_pilar(13.9)


def test_verificar_dimensao_pilar_b19_ok_sem_majoracao():
    r = lim.verificar_dimensao_pilar(b_cm=20.0, Ac_cm2=1000.0)
    assert r.ok is True
    assert r.gama_n == pytest.approx(1.0)


def test_verificar_dimensao_pilar_b16_gama_n_1_15():
    r = lim.verificar_dimensao_pilar(b_cm=16.0, Ac_cm2=1000.0)
    assert r.ok is True
    assert r.gama_n == pytest.approx(1.15, abs=1e-9)


def test_verificar_dimensao_pilar_b13_reprovado():
    r = lim.verificar_dimensao_pilar(b_cm=13.0, Ac_cm2=1000.0)
    assert r.ok is False
    assert r.b_minimo_ok is False


def test_verificar_dimensao_pilar_area_360_exata_ok():
    """13.2.3: área mínima absoluta é 360 cm²; exatamente 360 tem de passar."""
    r = lim.verificar_dimensao_pilar(b_cm=20.0, Ac_cm2=360.0)
    assert r.ok is True
    assert r.area_minima_ok is True


def test_verificar_dimensao_pilar_secao_19x18_reprovada_por_area():
    """19 x 18 cm = 342 cm² < 360 cm²: reprovado por área mínima, mesmo com
    b = 18 cm (dentro da faixa 14-19, permitido com γn)."""
    r = lim.verificar_dimensao_pilar(b_cm=18.0, Ac_cm2=19.0 * 18.0)
    assert r.area_minima_ok is False
    assert r.ok is False
    assert r.gama_n == pytest.approx(1.05, abs=1e-9)  # γn de b=18 calculado mesmo reprovando por área


def test_verificar_dimensao_pilar_area_abaixo_359_9_reprovada():
    r = lim.verificar_dimensao_pilar(b_cm=20.0, Ac_cm2=359.9)
    assert r.ok is False
    assert r.area_minima_ok is False


# =============================================================================
# 13.2.4.1, Tabela 13.2 — γn de laje em balanço (p. 94) — já testada em
# test_lajes_nbr2026.py (LAJ-07); aqui confere só a mudança de casa + reexport.
# =============================================================================
@pytest.mark.parametrize("h_cm, gama_n_esperado", [
    (10.0, 1.45), (19.0, 1.00), (25.0, 1.00),
])
def test_gama_n_laje_balanco_reexportado_de_lajes_nbr6118(h_cm, gama_n_esperado):
    assert lim.gama_n_laje_balanco(h_cm) == pytest.approx(gama_n_esperado, abs=1e-9)
    assert laj.gama_n_laje_balanco is lim.gama_n_laje_balanco


def test_gama_n_laje_balanco_abaixo_de_10_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        lim.gama_n_laje_balanco(9.0)


# =============================================================================
# 11.7.1 — Remissão ao γn de elementos esbeltos críticos (p. 84)
# =============================================================================
def test_gama_n_esbeltos_despacha_pilar():
    assert lim.gama_n_esbeltos("pilar", 16.0) == pytest.approx(lim.gama_n_pilar(16.0))


def test_gama_n_esbeltos_despacha_pilar_parede():
    assert lim.gama_n_esbeltos("pilar-parede", 15.0) == pytest.approx(lim.gama_n_pilar(15.0))


def test_gama_n_esbeltos_despacha_laje_balanco():
    assert lim.gama_n_esbeltos("laje-balanco", 12.0) == pytest.approx(lim.gama_n_laje_balanco(12.0))


def test_gama_n_esbeltos_tipo_desconhecido_levanta_erro():
    with pytest.raises(ValueError):
        lim.gama_n_esbeltos("viga", 16.0)


def test_pilares_aplicar_gama_n_b_menor_que_19_majora_esforco():
    """11.7.1: pilar com b < 19 cm tem o esforço solicitante majorado por γn."""
    esforco_maj, gn = pil.aplicar_gama_n(b_cm=16.0, esforco=1000.0)
    assert gn == pytest.approx(1.15, abs=1e-9)
    assert esforco_maj == pytest.approx(1150.0, abs=1e-6)


def test_pilares_aplicar_gama_n_b19_nao_majora():
    esforco_maj, gn = pil.aplicar_gama_n(b_cm=19.0, esforco=1000.0)
    assert gn == pytest.approx(1.0)
    assert esforco_maj == pytest.approx(1000.0)


def test_pilares_aplicar_gama_n_em_bloco_p10_no_fim_do_arquivo():
    """Achado da verificação (11.7.1-gamma_n-esbeltos-remissao): o que o P10
    acrescenta a um arquivo já existente (pilares_nbr6118.py) tem de seguir
    a convenção usada pelos demais pacotes que tocaram arquivo existente
    (ex.: protendido_nbr6118.py no P3) — bloco próprio no fim do arquivo,
    aberto por um comentário '# === Pn: <tema> ==='."""
    caminho = Path(pil.__file__)
    codigo = caminho.read_text(encoding="utf-8")
    marcador = "# === P10:"
    assert marcador in codigo, "falta o comentário de bloco '# === P10: ...' em pilares_nbr6118.py"
    pos_marcador = codigo.index(marcador)
    pos_funcao = codigo.index("def aplicar_gama_n")
    assert pos_marcador < pos_funcao, "aplicar_gama_n tem de vir depois do marcador de bloco do P10"


# =============================================================================
# 13.2.4.1 a-g — Espessuras mínimas de laje maciça (p. 94)
# =============================================================================
def test_espessura_minima_cobertura_sem_balanco_7cm():
    assert lim.espessura_minima_laje_cm("cobertura") == pytest.approx(7.0)


def test_espessura_minima_piso_sem_balanco_8cm():
    assert lim.espessura_minima_laje_cm("piso") == pytest.approx(8.0)


def test_espessura_minima_balanco_10cm():
    assert lim.espessura_minima_laje_cm("balanco") == pytest.approx(10.0)


def test_espessura_minima_piso_veiculo_leve_e_pesado_degrau_30kn():
    """13.2.4.1 d/e: degrau exato em 30 kN — <=30 dá 10 cm, >30 dá 12 cm."""
    assert lim.espessura_minima_laje_cm("piso_veiculo", peso_veiculo_kn=30.0) == pytest.approx(10.0)
    assert lim.espessura_minima_laje_cm("piso_veiculo", peso_veiculo_kn=30.01) == pytest.approx(12.0)


def test_espessura_minima_piso_veiculo_sem_peso_levanta_erro():
    with pytest.raises(ValueError):
        lim.espessura_minima_laje_cm("piso_veiculo")


def test_espessura_minima_protendida_biapoiada_vao_1000cm():
    """13.2.4.1 f: max(15, l/42); l=1000 cm -> 1000/42 = 23,809... > 15."""
    esperado = 1000.0 / 42.0
    assert lim.espessura_minima_laje_cm(
        "protendida", vao_efetivo_cm=1000.0
    ) == pytest.approx(esperado, abs=1e-3)


def test_espessura_minima_protendida_continua_usa_l_por_50():
    esperado = max(15.0, 1000.0 / 50.0)
    assert lim.espessura_minima_laje_cm(
        "protendida", vao_efetivo_cm=1000.0, continua=True
    ) == pytest.approx(esperado, abs=1e-3)


def test_espessura_minima_protendida_vao_pequeno_usa_piso_absoluto_15cm():
    """Vão pequeno: l/42 < 15 -> prevalece o mínimo absoluto de 15 cm."""
    assert lim.espessura_minima_laje_cm(
        "protendida", vao_efetivo_cm=300.0
    ) == pytest.approx(15.0)


def test_espessura_minima_lisa_16cm():
    assert lim.espessura_minima_laje_cm("lisa") == pytest.approx(16.0)


def test_espessura_minima_cogumelo_fora_capitel_14cm():
    assert lim.espessura_minima_laje_cm("cogumelo") == pytest.approx(14.0)


def test_espessura_minima_categoria_desconhecida_levanta_erro():
    with pytest.raises(ValueError):
        lim.espessura_minima_laje_cm("categoria-inexistente")


def test_espessura_minima_categoria_desconhecida_mensagem_com_cedilha():
    """Achado da verificação (13.2.4.1.1-espessura-min-laje): a mensagem de
    erro para o usuário final tem de escrever 'balanço' com cedilha, como o
    resto da prosa do módulo (docstrings nas linhas 9, 102, 107, 116,
    223-225), e não 'balanco' sem acento."""
    with pytest.raises(ValueError, match="balanço"):
        lim.espessura_minima_laje_cm("categoria-inexistente")


# =============================================================================
# 13.2.4.2 — Espessura mínima de mesa de laje nervurada (p. 95)
# =============================================================================
def test_mesa_nervurada_sem_tubo_l0_75_da_5cm():
    """l0/15 = 75/15 = 5,0 cm (>= 4 cm mínimo absoluto)."""
    assert lim.espessura_minima_mesa_nervurada_cm(l0_cm=75.0) == pytest.approx(5.0)


def test_mesa_nervurada_sem_tubo_l0_pequeno_usa_minimo_absoluto_4cm():
    assert lim.espessura_minima_mesa_nervurada_cm(l0_cm=30.0) == pytest.approx(4.0)


def test_mesa_nervurada_com_tubo_phi_8_menor_que_10_usa_5cm():
    assert lim.espessura_minima_mesa_nervurada_cm(l0_cm=75.0, phi_mm=8.0) == pytest.approx(5.0)


def test_mesa_nervurada_com_tubo_phi_15_sem_cruzamento_5_5cm():
    """φ=15 mm > 10 mm: hf >= 4 + 1,5 = 5,5 cm."""
    assert lim.espessura_minima_mesa_nervurada_cm(
        l0_cm=75.0, phi_mm=15.0, cruzamento=False
    ) == pytest.approx(5.5)


def test_mesa_nervurada_com_tubo_phi_15_com_cruzamento_7cm():
    """φ=15 mm > 10 mm, cruzamento: hf >= 4 + 2*1,5 = 7 cm."""
    assert lim.espessura_minima_mesa_nervurada_cm(
        l0_cm=75.0, phi_mm=15.0, cruzamento=True
    ) == pytest.approx(7.0)


def test_mesa_nervurada_phi_10_exato_usa_regra_menor_igual():
    """φ = 10 mm cai na regra "<= 10 mm" -> mínimo absoluto 5 cm."""
    assert lim.espessura_minima_mesa_nervurada_cm(l0_cm=30.0, phi_mm=10.0) == pytest.approx(5.0)


# =============================================================================
# 13.2.4.2 — Espessura mínima de nervura e armadura de compressão (p. 95)
# =============================================================================
def test_espessura_minima_nervura_5cm():
    assert lim.espessura_minima_nervura_cm() == pytest.approx(5.0)


def test_verificar_nervura_b4_reprovado_por_espessura():
    r = lim.verificar_nervura(b_cm=4.0)
    assert r.espessura_minima_ok is False
    assert r.ok is False


def test_verificar_nervura_b6_com_armadura_compressao_reprovado():
    """b=6 cm >= 5 cm (espessura ok), mas < 8 cm: proíbe armadura de compressão."""
    r = lim.verificar_nervura(b_cm=6.0, As_comp_cm2=0.5)
    assert r.espessura_minima_ok is True
    assert r.armadura_compressao_permitida is False
    assert r.ok is False


def test_verificar_nervura_b9_com_armadura_compressao_ok():
    r = lim.verificar_nervura(b_cm=9.0, As_comp_cm2=0.5)
    assert r.armadura_compressao_permitida is True
    assert r.ok is True


def test_verificar_nervura_b6_sem_armadura_compressao_ok():
    """Sem armadura de compressão, a restrição não se aplica mesmo com b < 8 cm."""
    r = lim.verificar_nervura(b_cm=6.0, As_comp_cm2=0.0)
    assert r.ok is True


def test_verificar_nervura_b8_exato_permite_compressao():
    r = lim.verificar_nervura(b_cm=8.0, As_comp_cm2=0.5)
    assert r.armadura_compressao_permitida is True


# =============================================================================
# 13.2.4.2 a-c — Classificação do espaçamento entre nervuras (p. 95)
# =============================================================================
def test_classificar_espacamento_60_categoria_a_criterio_laje():
    r = lim.classificar_laje_nervurada(espacamento_cm=60.0)
    assert r.categoria == "a"
    assert r.dispensa_flexao_mesa is True
    assert r.cisalhamento_como == "laje"


def test_classificar_espacamento_65_exato_ainda_categoria_a():
    r = lim.classificar_laje_nervurada(espacamento_cm=65.0)
    assert r.categoria == "a"


def test_classificar_espacamento_100_largura_10_categoria_b_sem_excecao():
    r = lim.classificar_laje_nervurada(espacamento_cm=100.0, largura_media_nervura_cm=10.0)
    assert r.categoria == "b"
    assert r.dispensa_flexao_mesa is False
    assert r.cisalhamento_como == "viga"


def test_classificar_espacamento_85_largura_13_excecao_cisalhamento_como_laje():
    """65 < 85 <= 90 e largura média 13 cm > 12 cm: exceção -> cisalhamento como laje."""
    r = lim.classificar_laje_nervurada(espacamento_cm=85.0, largura_media_nervura_cm=13.0)
    assert r.categoria == "b"
    assert r.cisalhamento_como == "laje"


def test_classificar_espacamento_85_largura_12_sem_excecao():
    """Largura média exatamente 12 cm não satisfaz '> 12 cm': sem exceção."""
    r = lim.classificar_laje_nervurada(espacamento_cm=85.0, largura_media_nervura_cm=12.0)
    assert r.cisalhamento_como == "viga"


def test_classificar_espacamento_95_largura_13_sem_excecao_por_espacamento():
    """Espaçamento > 90 cm não entra na exceção mesmo com largura > 12 cm."""
    r = lim.classificar_laje_nervurada(espacamento_cm=95.0, largura_media_nervura_cm=13.0)
    assert r.cisalhamento_como == "viga"


def test_classificar_espacamento_110_exato_ainda_categoria_b():
    r = lim.classificar_laje_nervurada(espacamento_cm=110.0, largura_media_nervura_cm=10.0)
    assert r.categoria == "b"


def test_classificar_espacamento_120_categoria_c_mesa_como_laje_macica():
    r = lim.classificar_laje_nervurada(espacamento_cm=120.0)
    assert r.categoria == "c"
    assert r.mesa_como_laje_macica is True


def test_classificar_laje_nervurada_tem_ok_e_governante():
    """Achado da verificação (13.2.4.2-classificacao-espacamento-nervuras):
    ResultadoClassificacaoNervurada precisa expor ok e governante, como as
    demais dataclasses de resultado do mesmo arquivo (convenção 3.3 item 4)."""
    r_a = lim.classificar_laje_nervurada(espacamento_cm=60.0)
    assert r_a.ok is True
    assert "13.2.4.2 a)" in r_a.governante

    r_b = lim.classificar_laje_nervurada(espacamento_cm=100.0, largura_media_nervura_cm=10.0)
    assert r_b.ok is True
    assert "13.2.4.2 b)" in r_b.governante

    r_c = lim.classificar_laje_nervurada(espacamento_cm=120.0)
    assert r_c.ok is True
    assert "13.2.4.2 c)" in r_c.governante


# =============================================================================
# 13.2.5.1 — Dispensa de verificação de furo em viga (p. 95-96)
# =============================================================================
def test_furo_viga_dispensado_caso_tipico():
    """h=50 cm (2h=100 cm); furo circular d=12 cm a 110 cm do apoio, na zona
    de tração; dist. face = 8 cm, cobrimento 2,5 cm (mín. = 5 cm) -> dispensado."""
    r = lim.dispensa_verificacao_furo_viga(
        h_cm=50.0, dist_furo_apoio_cm=110.0, dist_face_cm=8.0, cobrimento_cm=2.5,
        diametro_furo_cm=12.0, zona_tracao=True,
    )
    assert r.dispensa_verificacao is True


def test_furo_viga_13x13_nao_dispensado_por_dimensao():
    """Furo retangular 13x13 cm > 12x12 cm (item b): não dispensa."""
    r = lim.dispensa_verificacao_furo_viga(
        h_cm=50.0, dist_furo_apoio_cm=110.0, dist_face_cm=8.0, cobrimento_cm=2.5,
        largura_furo_cm=13.0, altura_furo_cm=13.0, zona_tracao=True,
    )
    assert r.dispensa_verificacao is False
    assert "b" not in r.condicoes_atendidas


def test_furo_viga_a_80cm_do_apoio_nao_dispensado_por_distancia():
    """80 cm < 2h = 100 cm: viola o item a) -> não dispensa."""
    r = lim.dispensa_verificacao_furo_viga(
        h_cm=50.0, dist_furo_apoio_cm=80.0, dist_face_cm=8.0, cobrimento_cm=2.5,
        diametro_furo_cm=12.0, zona_tracao=True,
    )
    assert r.dispensa_verificacao is False
    assert "a" not in r.condicoes_atendidas


def test_furo_viga_dist_face_abaixo_do_minimo_reprova_sempre():
    """A distância mínima furo-face (max(5, 2*cobrimento)) é sempre obrigatória."""
    r = lim.dispensa_verificacao_furo_viga(
        h_cm=50.0, dist_furo_apoio_cm=110.0, dist_face_cm=3.0, cobrimento_cm=2.5,
        diametro_furo_cm=12.0, zona_tracao=True,
    )
    assert r.dist_face_ok is False
    assert r.ok is False


def test_furo_viga_sem_dimensao_informada_levanta_erro():
    with pytest.raises(ValueError):
        lim.dispensa_verificacao_furo_viga(
            h_cm=50.0, dist_furo_apoio_cm=110.0, dist_face_cm=8.0, cobrimento_cm=2.5,
        )


# =============================================================================
# 13.2.5.2, Figura 13.1 — Dispensa de abertura em laje (p. 96)
# =============================================================================
def test_abertura_laje_dispensada_caso_tipico():
    """lx=500, ly=600 (lx é o menor vão); ax=ay=40 < lx/10=50; distâncias
    aos apoios >= vão/4 em cada direção; sem outra abertura."""
    r = lim.dispensa_verificacao_abertura_laje(
        lx_cm=500.0, ly_cm=600.0, ax_cm=40.0, ay_cm=40.0,
        dist_face_apoio_x_cm=130.0, dist_face_apoio_y_cm=160.0,
    )
    assert r.dispensa_verificacao is True


def test_abertura_laje_ax_60_nao_dispensado_dimensao_maior_que_lx_10():
    """ax=60 cm >= lx/10=50 cm: viola o item a)."""
    r = lim.dispensa_verificacao_abertura_laje(
        lx_cm=500.0, ly_cm=600.0, ax_cm=60.0, ay_cm=40.0,
        dist_face_apoio_x_cm=130.0, dist_face_apoio_y_cm=160.0,
    )
    assert r.dispensa_verificacao is False
    assert "a" not in r.condicoes_atendidas


def test_abertura_laje_lisa_sempre_exige_verificacao():
    """Laje lisa: mesmo com dimensões e distâncias favoráveis, nunca dispensa."""
    r = lim.dispensa_verificacao_abertura_laje(
        lx_cm=500.0, ly_cm=600.0, ax_cm=10.0, ay_cm=10.0, tipo_laje="lisa",
        dist_face_apoio_x_cm=200.0, dist_face_apoio_y_cm=200.0,
    )
    assert r.dispensa_verificacao is False


def test_abertura_laje_cogumelo_sempre_exige_verificacao():
    r = lim.dispensa_verificacao_abertura_laje(
        lx_cm=500.0, ly_cm=600.0, ax_cm=10.0, ay_cm=10.0, tipo_laje="cogumelo",
    )
    assert r.dispensa_verificacao is False


def test_abertura_laje_lx_maior_que_ly_levanta_erro():
    """lx_cm tem de ser o menor vão (Figura 13.1); fora de ordem, levanta erro
    em vez de adivinhar a que direção cada distância se refere."""
    with pytest.raises(ValueError):
        lim.dispensa_verificacao_abertura_laje(
            lx_cm=600.0, ly_cm=500.0, ax_cm=40.0, ay_cm=40.0,
            dist_face_apoio_x_cm=160.0, dist_face_apoio_y_cm=130.0,
        )


def test_abertura_laje_distancia_entre_aberturas_menor_que_metade_menor_vao():
    """Duas aberturas a 200 cm uma da outra, lx=500 -> lx/2=250: viola c)."""
    r = lim.dispensa_verificacao_abertura_laje(
        lx_cm=500.0, ly_cm=600.0, ax_cm=40.0, ay_cm=40.0,
        dist_face_apoio_x_cm=130.0, dist_face_apoio_y_cm=160.0,
        dist_entre_aberturas_cm=200.0,
    )
    assert r.dispensa_verificacao is False
    assert "c" not in r.condicoes_atendidas


# =============================================================================
# 13.2.6 — Canalizações embutidas: casos proibidos (p. 96)
# =============================================================================
def test_canalizacao_delta_t_20_sem_isolamento_proibido():
    r = lim.canalizacao_embutida_permitida(delta_temperatura_c=20.0)
    assert r.permitido is False
    assert "13.2.6 a)" in r.proibicoes


def test_canalizacao_delta_t_20_com_verificacao_permitido():
    r = lim.canalizacao_embutida_permitida(
        delta_temperatura_c=20.0, isolamento_ou_verificacao=True,
    )
    assert r.permitido is True


def test_canalizacao_delta_t_15_exato_permitido():
    """Degrau exato em 15 °C: |ΔT| = 15 não ultrapassa o limite."""
    r = lim.canalizacao_embutida_permitida(delta_temperatura_c=15.0)
    assert r.permitido is True


def test_canalizacao_pressao_035_proibida():
    r = lim.canalizacao_embutida_permitida(pressao_interna_mpa=0.35)
    assert r.permitido is False
    assert "13.2.6 b)" in r.proibicoes


def test_canalizacao_pressao_03_exata_permitida():
    r = lim.canalizacao_embutida_permitida(pressao_interna_mpa=0.3)
    assert r.permitido is True


def test_canalizacao_em_pilar_sem_dreno_proibida():
    r = lim.canalizacao_embutida_permitida(em_pilar=True, abertura_drenagem=False)
    assert r.permitido is False
    assert "13.2.6 c)" in r.proibicoes


def test_canalizacao_em_pilar_com_dreno_permitida():
    r = lim.canalizacao_embutida_permitida(em_pilar=True, abertura_drenagem=True)
    assert r.permitido is True


def test_canalizacao_embutida_tem_ok_e_governante():
    """Achado da verificação (13.2.6-canalizacoes-embutidas-proibicoes):
    ResultadoCanalizacaoEmbutida precisa expor ok e governante, como as
    demais dataclasses de resultado do módulo (convenção 3.3 item 4)."""
    r_ok = lim.canalizacao_embutida_permitida(pressao_interna_mpa=0.2)
    assert r_ok.ok is True
    assert r_ok.ok == r_ok.permitido
    assert "13.2.6" in r_ok.governante

    r_proibido = lim.canalizacao_embutida_permitida(em_pilar=True, abertura_drenagem=False)
    assert r_proibido.ok is False
    assert r_proibido.ok == r_proibido.permitido
    assert "13.2.6 c)" in r_proibido.governante


# =============================================================================
# 22.2 — γn de consolo e dente Gerber (p. 203)
# =============================================================================
def test_gama_n_consolo_gerber_e_1_2():
    assert lim.gama_n_consolo_gerber() == pytest.approx(1.2)


def test_gama_n_consolo_gerber_majora_momento_de_calculo():
    """Compara o resultado com e sem γn=1,2 aplicado ao momento de cálculo."""
    Md_sem = 1000.0
    Md_com = Md_sem * lim.gama_n_consolo_gerber()
    assert Md_com == pytest.approx(1200.0)
    assert Md_com > Md_sem
