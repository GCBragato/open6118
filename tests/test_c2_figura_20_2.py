# -*- coding: utf-8 -*-
"""Pacote C2 — arbitragem: a que linha pertence a cota ">= 15 cm" da Figura
20.2 (20.3.1, PDF p. 194), na faixa interna (regiao central) da laje sem
vigas.

Nao e um pacote da norma: e a conferencia final de uma divergencia de
leitura de imagem, apontada depois da implementacao original do P18
(``dimensionamento/detalhamento_lajes_nbr6118.py``,
``distribuicao_faixas_laje_lisa``).

Evidencia (ampliacao em 700 dpi de ``SCRATCH\\nbr_png\\p194.png`` /
PDF p. 194, texto das posicoes (x, y) obtido diretamente do PDF com
PyMuPDF, ``page.get_text("dict")``, coordenadas em pontos):

- Faixa externa, linha "Barras inferiores" (100%): a cota ">= 15 cm" (y
  323,6-334,0) e as duas chamadas "<= 0,125 l" da armadura contra colapso
  progressivo (y 326,1-336,5) caem as tres dentro da MESMA linha da tabela
  (rotulo "Barras" y 329,3-355,7 / "inferiores" y 324,1-360,9 / valor "100"
  y 335,3-345,7). As duas cotas de fato compartilham a celula.
- Faixa interna, linha "Barras superiores" (100%): a cota ">= 15 cm" (y
  392,3-402,7) cai dentro da linha rotulada "Barras" (y 372,9-399,3) /
  "superiores" (y 365,1-407,2) / valor "100" (y 381,0-391,4) — junto da
  cota ">= 0,25 l" dessa mesma linha (y 363,1-373,5).
- Faixa interna, linha "Barras inferiores" (33% / Restante): rotulada
  "Barras" (y 416,8-443,2) / "inferiores" (y 411,6-448,5) / valores "33"
  (y 418,3-428,7) e "Restante" (y 433,9-444,3). As unicas cotas dentro
  dessa faixa de y sao as duas chamadas "<= 0,125 l" do corte do restante
  (y 425,3-435,7) — NAO ha nenhuma cota ">= 15 cm" nessa faixa de y.

Ou seja: na faixa interna, ">= 15 cm" pertence a linha das barras
SUPERIORES (100%), nao a das barras inferiores (33%), ao contrario da
leitura original do P18. Na faixa externa a leitura original ja estava
certa (as duas cotas realmente compartilham a linha das inferiores).

Mudanca de comportamento em ``distribuicao_faixas_laje_lisa``:

- ``faixa_int_sup_100pct_min_cm``: antes ``0,25*l`` (sem piso); agora
  ``max(0,25*l, 15)`` — a linha das barras superiores da faixa interna
  ganha o piso de 15 cm que a figura de fato lhe atribui.
- ``faixa_int_inf_33pct_min_cm``: antes ``15.0`` fixo; agora ``0.0`` — a
  linha das barras inferiores (33%) nao tem cota de extensao minima em cm
  na figura (e continua, sem corte, ate o proximo apoio).
- ``faixa_int_inf_restante_max_cm``: antes ``max(15, 0,125*l)``; agora so
  ``0,125*l`` — o piso de 15 cm so se justificava pela leitura (incorreta)
  de que a cota ">= 15 cm" estava nessa linha; sem essa cota ali, nao ha
  piso absoluto a combinar com o corte.

``faixa_ext_inf_100pct_min_cm`` e ``faixa_ext_inf_colapso_prog_max_cm``
(faixa externa) nao mudam: a leitura original ja estava certa para elas.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dimensionamento"))

import pytest

import detalhamento_lajes_nbr6118 as dl


TOL = 1e-9


def test_faixa_interna_superiores_ganha_piso_15cm_vao_pequeno():
    # l=40cm -> 0,25l=10cm < 15cm: a linha das barras superiores da faixa
    # interna (100%) tem cota >= 15cm na mesma celula da figura, logo
    # prevalece o piso de 15cm (20.3.1, Fig. 20.2, PDF p. 194).
    d = dl.distribuicao_faixas_laje_lisa(40.0)
    assert d.faixa_int_sup_100pct_min_cm == pytest.approx(15.0, abs=TOL)


def test_faixa_interna_superiores_fracao_governa_vao_grande():
    # l=600cm -> 0,25*600=150cm > 15cm: a fracao de vao governa, como ja
    # valia antes da correcao (o piso de 15cm so aparece para vaos
    # pequenos, nao muda o resultado usual de projeto).
    d = dl.distribuicao_faixas_laje_lisa(600.0)
    assert d.faixa_int_sup_100pct_min_cm == pytest.approx(150.0, abs=TOL)


def test_faixa_interna_superiores_fronteira_025l_igual_15cm():
    # 0,25*l = 15cm exatamente quando l = 60cm: fronteira entre a fracao de
    # vao e o piso absoluto, nas duas cotas que compartilham a linha das
    # barras superiores (faixa interna).
    d_fronteira = dl.distribuicao_faixas_laje_lisa(60.0)
    assert d_fronteira.faixa_int_sup_100pct_min_cm == pytest.approx(15.0, abs=TOL)
    # um pouco abaixo: 0,25*59,9 = 14,975cm < 15cm -> prevalece o piso de 15cm
    d_abaixo = dl.distribuicao_faixas_laje_lisa(59.9)
    assert d_abaixo.faixa_int_sup_100pct_min_cm == pytest.approx(15.0, abs=TOL)
    # um pouco acima: 0,25*60,1 = 15,025cm > 15cm -> prevalece a fracao de vao
    d_acima = dl.distribuicao_faixas_laje_lisa(60.1)
    assert d_acima.faixa_int_sup_100pct_min_cm == pytest.approx(15.025, abs=TOL)


def test_faixa_interna_inferiores_33pct_sem_cota_minima_em_cm():
    # a linha das barras inferiores (33%) da faixa interna nao tem cota de
    # extensao minima na Figura 20.2: a cota >= 15cm pertence a linha das
    # barras superiores (100%), nao a esta.
    for l in (40.0, 60.0, 100.0, 600.0):
        d = dl.distribuicao_faixas_laje_lisa(l)
        assert d.faixa_int_inf_33pct_min_cm == pytest.approx(0.0, abs=TOL)


def test_faixa_interna_inferiores_restante_sem_piso_15cm():
    # o corte do restante (67%) das barras inferiores, na faixa interna, e
    # so 0,125*l: sem o piso absoluto de 15cm (que a leitura original
    # aplicava por engano, por acreditar que a cota >= 15cm estava nesta
    # linha). l=100cm -> 0,125*100 = 12,5cm < 15cm, e o valor devolvido e
    # 12,5cm, nao 15cm.
    d = dl.distribuicao_faixas_laje_lisa(100.0)
    assert d.faixa_int_inf_restante_max_cm == pytest.approx(12.5, abs=TOL)


def test_faixa_externa_inferiores_leitura_original_mantida():
    # na faixa externa, a cota >= 15cm e as chamadas <= 0,125l da armadura
    # contra colapso progressivo de fato compartilham a mesma linha
    # (Barras inferiores, 100%) - a leitura original ja estava certa aqui,
    # e o comportamento nao muda com a correcao da faixa interna.
    d_grande = dl.distribuicao_faixas_laje_lisa(600.0)
    assert d_grande.faixa_ext_inf_100pct_min_cm == pytest.approx(15.0, abs=TOL)
    assert d_grande.faixa_ext_inf_colapso_prog_max_cm == pytest.approx(75.0, abs=TOL)

    d_pequeno = dl.distribuicao_faixas_laje_lisa(100.0)
    # 0,125*100=12,5cm < 15cm -> prevalece o minimo absoluto de 15cm (as
    # duas cotas realmente compartilham a linha, na faixa externa)
    assert d_pequeno.faixa_ext_inf_colapso_prog_max_cm == pytest.approx(15.0, abs=TOL)
