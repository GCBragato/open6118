# -*- coding: utf-8 -*-
"""Testes do P18 — Detalhamento de lajes (ABNT NBR 6118:2026, Seção 20).

Cada teste cita o item da norma e a página do PDF (a impressa é PDF - 18).
Fonte das fórmulas: SCRATCH\\nbr_png\\p192.png, p194.png, p196.png, p197.png.
"""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dimensionamento"))

import pytest

import detalhamento_lajes_nbr6118 as dl
import nucleo_nbr6118 as nbr


TOL = 1e-9


# ---------------------------------------------------------------------------
# 20.1 — phi_max_laje_mm (PDF p. 192): phi_max = h/8
# ---------------------------------------------------------------------------
def test_phi_max_laje_h10():
    # h=10cm -> phi_max = 10/8 = 1,25 cm = 12,5 mm (teste sugerido do plano)
    assert dl.phi_max_laje_mm(10.0) == pytest.approx(12.5, abs=TOL)


def test_phi_max_laje_h20():
    # h=20cm -> phi_max = 20/8 = 2,5 cm = 25 mm (teste sugerido do plano)
    assert dl.phi_max_laje_mm(20.0) == pytest.approx(25.0, abs=TOL)


def test_phi_max_laje_ponto_interior():
    # h=16cm -> phi_max = 16/8 = 2,0 cm = 20 mm
    assert dl.phi_max_laje_mm(16.0) == pytest.approx(20.0, abs=TOL)


def test_phi_max_laje_h_invalido():
    with pytest.raises(ValueError):
        dl.phi_max_laje_mm(0.0)
    with pytest.raises(ValueError):
        dl.phi_max_laje_mm(-5.0)


# ---------------------------------------------------------------------------
# 20.1 — espacamento_max_principal_cm (PDF p. 192):
# s_max = min(2h, 20cm); se phi >= 20mm, s_max = 15*phi (substitui a regra)
# ---------------------------------------------------------------------------
def test_espacamento_max_principal_h15_governa_20cm():
    # h=15cm -> 2h=30cm > 20cm, logo s_max=20cm (teste sugerido do plano)
    assert dl.espacamento_max_principal_cm(15.0, 0.0) == pytest.approx(20.0, abs=TOL)


def test_espacamento_max_principal_h_pequeno_governa_2h():
    # h=3cm -> 2h=6cm < 20cm, logo s_max=6cm (a outra borda do min())
    assert dl.espacamento_max_principal_cm(3.0, 0.0) == pytest.approx(6.0, abs=TOL)


def test_espacamento_max_principal_phi25_relaxa_15phi():
    # phi=25mm (>=20mm) -> 15*2,5cm=37,5cm (teste sugerido do plano)
    assert dl.espacamento_max_principal_cm(100.0, 25.0) == pytest.approx(37.5, abs=TOL)


def test_espacamento_max_principal_phi_no_limite_20mm():
    # phi=20mm exatamente (fronteira >=20mm): 15*2,0cm=30cm
    assert dl.espacamento_max_principal_cm(100.0, 20.0) == pytest.approx(30.0, abs=TOL)


def test_espacamento_max_principal_phi_logo_abaixo_20mm():
    # phi=19,9mm (< 20mm): regra normal, h=100cm -> min(200,20)=20cm
    assert dl.espacamento_max_principal_cm(100.0, 19.9) == pytest.approx(20.0, abs=TOL)


def test_espacamento_max_principal_h_invalido():
    with pytest.raises(ValueError):
        dl.espacamento_max_principal_cm(0.0, 10.0)
    with pytest.raises(ValueError):
        dl.espacamento_max_principal_cm(15.0, -1.0)


# ---------------------------------------------------------------------------
# 20.1 — prolongamento_positivo_apoio_cm (PDF p. 192):
# minimo 4 cm alem do eixo teorico do apoio; usar o maior com a ancoragem (Secao 9)
# ---------------------------------------------------------------------------
def test_prolongamento_positivo_apoio_minimo_absoluto():
    # sem lb,nec informado -> prevalece o minimo absoluto de 4 cm
    assert dl.prolongamento_positivo_apoio_cm() == pytest.approx(4.0, abs=TOL)
    assert dl.prolongamento_positivo_apoio_cm(0.0) == pytest.approx(4.0, abs=TOL)


def test_prolongamento_positivo_apoio_governado_pela_ancoragem():
    # lb,nec = 6 cm > 4 cm -> prevalece a ancoragem da Secao 9
    assert dl.prolongamento_positivo_apoio_cm(6.0) == pytest.approx(6.0, abs=TOL)


def test_prolongamento_positivo_apoio_fronteira_igual():
    # lb,nec = 4 cm (fronteira exata): os dois lados dao o mesmo resultado
    assert dl.prolongamento_positivo_apoio_cm(4.0) == pytest.approx(4.0, abs=TOL)


def test_prolongamento_positivo_apoio_lb_negativo():
    with pytest.raises(ValueError):
        dl.prolongamento_positivo_apoio_cm(-1.0)


# ---------------------------------------------------------------------------
# 20.1 — As_secundaria_min_cm2_por_m e espacamento_max_secundaria_cm (PDF p. 192):
# As,sec >= 0,20*As,principal; s_max = 33 cm
# ---------------------------------------------------------------------------
def test_As_secundaria_min():
    # As_principal=5 cm2/m -> As,sec_min=1,0 cm2/m (teste sugerido do plano)
    assert dl.As_secundaria_min_cm2_por_m(5.0) == pytest.approx(1.0, abs=TOL)


def test_As_secundaria_min_outro_ponto():
    # As_principal=8 cm2/m -> 0,20*8=1,6 cm2/m
    assert dl.As_secundaria_min_cm2_por_m(8.0) == pytest.approx(1.6, abs=TOL)


def test_As_secundaria_min_invalido():
    with pytest.raises(ValueError):
        dl.As_secundaria_min_cm2_por_m(0.0)


def test_espacamento_max_secundaria():
    assert dl.espacamento_max_secundaria_cm() == pytest.approx(33.0, abs=TOL)


# ---------------------------------------------------------------------------
# 20.1 — espacamento_max_estribo_nervura_cm (PDF p. 192): s_max = 20 cm
# ---------------------------------------------------------------------------
def test_espacamento_max_estribo_nervura():
    assert dl.espacamento_max_estribo_nervura_cm() == pytest.approx(20.0, abs=TOL)


# ---------------------------------------------------------------------------
# 20.3.1 — distribuicao_faixas_laje_lisa (Figura 20.2, PDF p. 194)
# ---------------------------------------------------------------------------
def test_distribuicao_faixas_l600_fracao_governa():
    # l=600cm -> 0,35l=210cm; 0,25l=150cm; 0,125l=75cm (>15cm, governa a
    # fracao) - teste sugerido do plano
    d = dl.distribuicao_faixas_laje_lisa(600.0)
    assert d.faixa_ext_sup_50pct_min_cm == pytest.approx(210.0, abs=TOL)
    assert d.faixa_ext_sup_restante_min_cm == pytest.approx(150.0, abs=TOL)
    assert d.faixa_int_sup_100pct_min_cm == pytest.approx(150.0, abs=TOL)
    assert d.faixa_ext_inf_100pct_min_cm == pytest.approx(15.0, abs=TOL)
    # faixa interna, barras inferiores (33%): sem cota de extensao minima
    # nesta linha da Figura 20.2 (conferencia C2, ver docstring da funcao)
    assert d.faixa_int_inf_33pct_min_cm == pytest.approx(0.0, abs=TOL)
    assert d.faixa_ext_inf_colapso_prog_max_cm == pytest.approx(75.0, abs=TOL)
    assert d.faixa_int_inf_restante_max_cm == pytest.approx(75.0, abs=TOL)
    assert d.soma_percentuais_ok is True


def test_distribuicao_faixas_l100_minimo_absoluto_governa():
    # l=100cm -> 0,125l=12,5cm < 15cm, deve prevalecer o minimo absoluto de
    # 15cm apenas na linha (faixa externa) onde a cota >= 15cm de fato
    # coexiste com o corte <= 0,125l - teste sugerido do plano, ajustado
    # pela conferencia C2 (ver docstring de distribuicao_faixas_laje_lisa)
    d = dl.distribuicao_faixas_laje_lisa(100.0)
    assert d.faixa_ext_inf_colapso_prog_max_cm == pytest.approx(15.0, abs=TOL)
    # faixa interna, restante (67% das inferiores): sem piso de 15cm nesta
    # linha - o corte e so 0,125*100 = 12,5cm
    assert d.faixa_int_inf_restante_max_cm == pytest.approx(12.5, abs=TOL)
    # e as fracoes de 0,35l/0,25l continuam validas nesse vao pequeno
    assert d.faixa_ext_sup_50pct_min_cm == pytest.approx(35.0, abs=TOL)
    assert d.faixa_ext_sup_restante_min_cm == pytest.approx(25.0, abs=TOL)
    assert d.faixa_int_sup_100pct_min_cm == pytest.approx(25.0, abs=TOL)


def test_distribuicao_faixas_fronteira_0125l_igual_15cm():
    # 0,125*l = 15cm exatamente quando l = 120cm: os dois criterios coincidem
    # (faixa externa, unica linha onde essas duas cotas compartilham celula)
    d = dl.distribuicao_faixas_laje_lisa(120.0)
    assert d.faixa_ext_inf_colapso_prog_max_cm == pytest.approx(15.0, abs=TOL)
    # na faixa interna essa fronteira nao existe (a linha das inferiores
    # nao tem piso de 15cm): o corte e so 0,125*120 = 15cm por coincidencia
    # aritmetica, nao por combinacao de cotas
    assert d.faixa_int_inf_restante_max_cm == pytest.approx(15.0, abs=TOL)


# As demais fronteiras de ">= 15 cm" x ">= 0,25 l" na faixa interna (e a
# evidencia visual da arbitragem C2) estao em tests/test_c2_figura_20_2.py.


def test_distribuicao_faixas_soma_percentuais_100_por_cento():
    # Aceite do pacote: soma das fracoes de cada linha da Figura 20.2 = 100%
    # (50% + 50% "restante"; 100%; 33% + 67% "restante")
    faixa_ext_sup = 50 + 50
    faixa_int_sup = 100
    faixa_int_inf = 33 + 67
    assert faixa_ext_sup == 100
    assert faixa_int_sup == 100
    assert faixa_int_inf == 100
    d = dl.distribuicao_faixas_laje_lisa(500.0)
    assert d.soma_percentuais_ok is True


def test_distribuicao_faixas_l_invalido():
    with pytest.raises(ValueError):
        dl.distribuicao_faixas_laje_lisa(0.0)


# ---------------------------------------------------------------------------
# 20.3.1 — barras_continuas_apoio_min (PDF p. 194):
# n_barras >= 2 e fyd*As,ccp >= 1,5*FSd (19.5.4, recebido como parametro)
# ---------------------------------------------------------------------------
def test_barras_continuas_apoio_ok():
    # fyd=500/1,15=434,78 MPa -> 43,478 kN/cm2; As_ccp=4cm2 ->
    # capacidade=173,9 kN >= 1,5*100=150 kN; n=2 -> ok
    r = dl.barras_continuas_apoio_min(
        n_barras_continuas=2, FSd_kn=100.0, fyd_mpa=nbr.fyd(500.0), As_ccp_cm2=4.0,
    )
    assert r.ok is True
    assert r.n_min == 2
    assert r.capacidade_kn == pytest.approx(nbr.mpa_para_kncm2(nbr.fyd(500.0)) * 4.0, rel=1e-9)
    assert r.capacidade_min_kn == pytest.approx(150.0, abs=TOL)


def test_barras_continuas_apoio_numero_insuficiente():
    # apenas 1 barra continua: reprovado por 20.3.1, mesmo com As,ccp ampla
    r = dl.barras_continuas_apoio_min(
        n_barras_continuas=1, FSd_kn=100.0, fyd_mpa=500.0, As_ccp_cm2=10.0,
    )
    assert r.ok is False
    assert "20.3.1" in r.governante


def test_barras_continuas_apoio_ccp_insuficiente():
    # n=2 (ok), mas As,ccp pequena: fyd*As,ccp=100*2=200*0,1=... reprovado por 19.5.4
    r = dl.barras_continuas_apoio_min(
        n_barras_continuas=2, FSd_kn=100.0, fyd_mpa=500.0, As_ccp_cm2=2.0,
    )
    capacidade = nbr.mpa_para_kncm2(500.0) * 2.0  # 50*2=100 kN
    assert capacidade == pytest.approx(100.0, abs=TOL)
    assert capacidade < 1.5 * 100.0
    assert r.ok is False
    assert "19.5.4" in r.governante


def test_barras_continuas_apoio_fronteira_capacidade_exata():
    # fyd*As,ccp = 1,5*FSd exatamente -> ok (>=)
    # fyd=500 MPa=50 kN/cm2; As_ccp=3cm2 -> capacidade=150kN; FSd=100kN -> 1,5*100=150kN
    r = dl.barras_continuas_apoio_min(
        n_barras_continuas=2, FSd_kn=100.0, fyd_mpa=500.0, As_ccp_cm2=3.0,
    )
    assert r.capacidade_kn == pytest.approx(150.0, abs=TOL)
    assert r.ok is True


# ---------------------------------------------------------------------------
# 20.3.1 — penetracao_capitel_cm (PDF p. 194): L >= max(30cm, 24*phi)
# ---------------------------------------------------------------------------
def test_penetracao_capitel_fracao_governa():
    # phi=20mm -> 24*2cm=48cm > 30cm, L_min=48cm (teste sugerido do plano)
    assert dl.penetracao_capitel_cm(20.0) == pytest.approx(48.0, abs=TOL)


def test_penetracao_capitel_minimo_absoluto_governa():
    # phi=10mm -> 24*1cm=24cm < 30cm, L_min=30cm (teste sugerido do plano)
    assert dl.penetracao_capitel_cm(10.0) == pytest.approx(30.0, abs=TOL)


def test_penetracao_capitel_fronteira_30cm():
    # 24*phi=30cm exatamente quando phi=12,5mm
    assert dl.penetracao_capitel_cm(12.5) == pytest.approx(30.0, abs=TOL)


def test_penetracao_capitel_invalido():
    with pytest.raises(ValueError):
        dl.penetracao_capitel_cm(0.0)


# ---------------------------------------------------------------------------
# 20.5.1 — ancoragem_tela_apoio_cm (PDF p. 196): l_anc = max(10*phi, 10cm)
# ---------------------------------------------------------------------------
def test_ancoragem_tela_apoio_minimo_absoluto_governa():
    # phi=6mm -> 10*0,6cm=6cm < 10cm, l_anc=10cm (teste sugerido do plano)
    assert dl.ancoragem_tela_apoio_cm(6.0) == pytest.approx(10.0, abs=TOL)


def test_ancoragem_tela_apoio_fracao_governa():
    # phi=12mm -> 10*1,2cm=12cm > 10cm, l_anc=12cm (teste sugerido do plano)
    assert dl.ancoragem_tela_apoio_cm(12.0) == pytest.approx(12.0, abs=TOL)


def test_ancoragem_tela_apoio_fronteira_10cm():
    # 10*phi=10cm exatamente quando phi=10mm
    assert dl.ancoragem_tela_apoio_cm(10.0) == pytest.approx(10.0, abs=TOL)


def test_ancoragem_tela_apoio_invalido():
    with pytest.raises(ValueError):
        dl.ancoragem_tela_apoio_cm(0.0)


# ---------------------------------------------------------------------------
# 20.5.2 — emenda_tela_malhas (PDF p. 196): tabela de duas celulas
# ---------------------------------------------------------------------------
def test_emenda_tela_malhas_principal():
    assert dl.emenda_tela_malhas("principal") == {"malhas": 2, "fios": 3}


def test_emenda_tela_malhas_secundaria():
    assert dl.emenda_tela_malhas("secundaria") == {"malhas": 1, "fios": 2}


def test_emenda_tela_malhas_secundaria_acentuada_e_maiuscula():
    # normalizacao de acento/maiuscula na chave de entrada
    assert dl.emenda_tela_malhas("Secundária") == {"malhas": 1, "fios": 2}
    assert dl.emenda_tela_malhas("PRINCIPAL") == {"malhas": 2, "fios": 3}


def test_emenda_tela_malhas_tipo_invalido():
    # a norma nao define esse caso -> erro, nunca numero
    with pytest.raises(ValueError):
        dl.emenda_tela_malhas("terciaria")


# ---------------------------------------------------------------------------
# 20.6 — As_inferior_balanco (PDF p. 197):
# armadura inferior dimensionada para Mg isolado, com o minimo de 17.3.5.2.1
# ---------------------------------------------------------------------------
def test_As_inferior_balanco_governado_pelo_minimo():
    # g=5kN/m2, vao=150cm: Mg=5*1,5^2/2=5,625 kN.m/m=562,5 kN.cm/m
    # bw=100cm, h=15cm, d=12cm, fck=25MPa -> As de flexao = 1,092 cm2/m
    # (fcd=25/1,4=17,857MPa; tensao=0,85*1*17,857=15,179MPa=1,5179kN/cm2;
    # lambda=0,8; a=1,5179*100*0,64/2=48,57; b=-1,5179*100*0,8*12=-1457,2;
    # c=562,5; x=(1457,2-sqrt(1457,2^2-4*48,57*562,5))/(2*48,57)=8,046cm;
    # As=562,5/(43,478*(12-0,5*0,8*8,046))=1,092cm2/m)
    # As,min (17.3.5.2.1, W0=100*15^2/6=3750cm3;fctk,sup=1,3*fct,m;
    # Md,min=0,8*3750*fctk,sup) = 2,25 cm2/m -> governa o minimo absoluto
    r = dl.As_inferior_balanco(
        g_kn_m2=5.0, vao_balanco_cm=150.0, d_cm=12.0, h_cm=15.0, fck_mpa=25.0,
    )
    assert r.Mg_kncm == pytest.approx(562.5, abs=TOL)
    assert r.As_cm2 == pytest.approx(2.25, abs=1e-6)
    assert r.As_min_cm2 == pytest.approx(2.25, abs=1e-6)
    assert "17.3.5.2.1" in r.governante


def test_As_inferior_balanco_governado_pela_flexao():
    # vao e carga maiores: a flexao passa a governar sobre o minimo absoluto
    # g=8kN/m2, vao=200cm -> Mg=8*2^2/2=16kN.m/m=1600kN.cm/m
    r = dl.As_inferior_balanco(
        g_kn_m2=8.0, vao_balanco_cm=200.0, d_cm=12.0, h_cm=15.0, fck_mpa=25.0,
    )
    assert r.Mg_kncm == pytest.approx(1600.0, abs=TOL)
    assert r.As_min_cm2 == pytest.approx(2.25, abs=1e-6)
    assert r.As_cm2 > r.As_min_cm2
    assert r.As_cm2 == pytest.approx(3.187966, rel=1e-5)
    assert "20.6" in r.governante


def test_As_inferior_balanco_secao_insuficiente():
    # vao muito grande para a secao: discriminante negativo -> erro, nunca numero
    with pytest.raises(ValueError):
        dl.As_inferior_balanco(
            g_kn_m2=50.0, vao_balanco_cm=600.0, d_cm=8.0, h_cm=10.0, fck_mpa=20.0,
        )


def test_As_inferior_balanco_entradas_invalidas():
    with pytest.raises(ValueError):
        dl.As_inferior_balanco(
            g_kn_m2=5.0, vao_balanco_cm=0.0, d_cm=12.0, h_cm=15.0, fck_mpa=25.0,
        )
    with pytest.raises(ValueError):
        dl.As_inferior_balanco(
            g_kn_m2=-1.0, vao_balanco_cm=150.0, d_cm=12.0, h_cm=15.0, fck_mpa=25.0,
        )


# ---------------------------------------------------------------------------
# Correcoes da verificacao independente (volta 1)
# ---------------------------------------------------------------------------
# 1) Convencao do plano (secao 3.3.3): fora da faixa de validade, as funcoes
#    devem levantar FaixaNormativaError (nao ValueError puro), inclusive para
#    a celula/caso que a norma nao define. Antes da correcao, _positivo e
#    _nao_negativo (usadas por quase todas as funcoes do modulo) levantavam
#    builtins.ValueError puro, e o mesmo valia para o raise direto em
#    emenda_tela_malhas e para o "secao insuficiente" de As_inferior_balanco:
#    estes testes falhavam antes da correcao (type(exc) era ValueError, nao
#    FaixaNormativaError, apesar de pytest.raises(ValueError) aceitar os dois
#    por FaixaNormativaError ser subclasse).
def test_entrada_invalida_levanta_faixa_normativa_error_positivo():
    with pytest.raises(nbr.FaixaNormativaError):
        dl.phi_max_laje_mm(-5.0)
    with pytest.raises(nbr.FaixaNormativaError):
        dl.penetracao_capitel_cm(0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        dl.ancoragem_tela_apoio_cm(-1.0)
    with pytest.raises(nbr.FaixaNormativaError):
        dl.As_secundaria_min_cm2_por_m(0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        dl.distribuicao_faixas_laje_lisa(-10.0)


def test_entrada_invalida_levanta_faixa_normativa_error_nao_negativo():
    with pytest.raises(nbr.FaixaNormativaError):
        dl.prolongamento_positivo_apoio_cm(-1.0)
    with pytest.raises(nbr.FaixaNormativaError):
        dl.barras_continuas_apoio_min(
            n_barras_continuas=2, FSd_kn=-1.0, fyd_mpa=500.0, As_ccp_cm2=4.0,
        )


def test_emenda_tela_malhas_tipo_invalido_e_faixa_normativa_error():
    # a norma nao define esse caso -> FaixaNormativaError, nunca numero
    with pytest.raises(nbr.FaixaNormativaError):
        dl.emenda_tela_malhas("terciaria")


def test_As_inferior_balanco_secao_insuficiente_e_faixa_normativa_error():
    with pytest.raises(nbr.FaixaNormativaError):
        dl.As_inferior_balanco(
            g_kn_m2=50.0, vao_balanco_cm=600.0, d_cm=8.0, h_cm=10.0, fck_mpa=20.0,
        )


# 2) Figura 20.2 (PDF p. 194): no apoio EXTERNO a figura desenha "Eixo de
#    apoio externo" separado de "Face de apoio", e as cotas >= 0,35l /
#    >= 0,25l / >= 15 cm partem da face (so o traco da armadura comeca no
#    eixo); so no apoio INTERNO (unica linha tracejada) a cota coincide com
#    o eixo. Antes da correcao, o docstring do modulo e da funcao/dataclass
#    afirmava que TODAS as extensoes eram medidas a partir do eixo, o que e
#    incorreto para o apoio externo (risco de deslocar a armadura ao
#    transferir a memoria para o desenho). Este teste falharia antes da
#    correcao, pois o docstring nao mencionava "face" nenhuma vez.
def test_distribuicao_faixas_docstring_distingue_eixo_e_face_do_apoio():
    doc_funcao = dl.distribuicao_faixas_laje_lisa.__doc__
    doc_dataclass = dl.DistribuicaoFaixasLajeLisa.__doc__
    assert "face" in doc_funcao.lower()
    assert "eixo de apoio externo" in doc_funcao.lower() or "apoio externo" in doc_funcao.lower()
    assert "apoio interno" in doc_funcao.lower()
    assert "face" in doc_dataclass.lower()


# 3) Acentuacao obrigatoria em texto para o usuario final (memoria de calculo
#    e governante). Antes da correcao, estas strings saiam sem acento
#    ("continuas", "numero minimo", "acoes", "majoracao").
def test_distribuicao_faixas_memoria_acentuada():
    r = dl.distribuicao_faixas_laje_lisa(600.0)
    memoria_completa = " ".join(r.memoria)
    assert "contínuas" in memoria_completa
    assert "continuas" not in memoria_completa


def test_barras_continuas_apoio_governante_e_memoria_acentuados():
    r = dl.barras_continuas_apoio_min(
        n_barras_continuas=1, FSd_kn=100.0, fyd_mpa=500.0, As_ccp_cm2=10.0,
    )
    assert r.governante == "20.3.1 número mínimo de barras contínuas não atendido"
    memoria_completa = " ".join(r.memoria)
    assert "contínua" in memoria_completa
    assert "mínimo" in memoria_completa


def test_As_inferior_balanco_governante_e_memoria_acentuados():
    r = dl.As_inferior_balanco(
        g_kn_m2=8.0, vao_balanco_cm=200.0, d_cm=12.0, h_cm=15.0, fck_mpa=25.0,
    )
    assert r.governante == "20.6 momento das ações permanentes isoladas"
    memoria_completa = " ".join(r.memoria)
    assert "ações" in memoria_completa
    assert "majoração" in memoria_completa
    assert "acoes" not in memoria_completa
    assert "majoracao" not in memoria_completa
