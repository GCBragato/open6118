"""Testes do T3 — Ajustes decididos na triagem de 21/09/2026.

Não muda o status de nenhum item da matriz do plano; cobre dois ajustes
pontuais:

  1. Armadura de pele: área total por face, em cm2 (17.3.5.2.3, PDF p. 153),
     em ``dimensionamento/vigas_nbr6118.armadura_pele_total_cm2_por_face``.
  2. γqs na perda de equilíbrio (Tabela 11.3, PDF p. 87-88): a docstring de
     ``dimensionamento/seguranca_nbr6118.fnd_equilibrio`` foi corrigida (sem
     mudar o valor padrão nem a assinatura); este teste documenta o sentido
     do coeficiente.

Os valores esperados vêm da imagem da página (SCRATCH\\nbr_png\\pNNN.png).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import seguranca_nbr6118 as seg             # noqa: E402
import vigas_nbr6118 as vig                 # noqa: E402


# ---------------------------------------------------------------------------
# 1. Armadura de pele — área total por face (17.3.5.2.3, PDF p. 153)
# ---------------------------------------------------------------------------
def test_pele_total_viga_20x80_da_1_6_cm2_por_face():
    # Ac,alma = 20 * 80 = 1600 cm2; 0,10% * 1600 = 1,6 cm2 por face.
    # Teto: 5 cm2/m * (80/100 m) = 4,0 cm2 -> não governa.
    assert vig.armadura_pele_total_cm2_por_face(bw_cm=20.0, h_alma_cm=80.0) == \
        pytest.approx(1.6)


def test_pele_total_e_a_taxa_por_metro_sao_a_mesma_grandeza_distribuida():
    # 1,6 cm2 distribuídos em 0,80 m de altura de alma equivalem a
    # 1,6 / 0,80 = 2,0 cm2/m, que é o que a taxa por metro (função antiga)
    # devolve para a mesma viga (17.3.5.2.3, PDF p. 153).
    total = vig.armadura_pele_total_cm2_por_face(bw_cm=20.0, h_alma_cm=80.0)
    taxa = vig.armadura_pele_cm2_por_face(bw_cm=20.0, h_cm=80.0)
    assert total / (80.0 / 100.0) == pytest.approx(taxa)


def test_pele_total_viga_larga_teto_governa():
    # bw = 80 cm, h_alma = 100 cm: Ac,alma = 8000 cm2; 0,10% * 8000 = 8,0 cm2,
    # mas o teto de 5 cm2/m * 1,0 m = 5,0 cm2 é menor -> governa o teto
    # (17.3.5.2.3, PDF p. 153: "não sendo necessária uma armadura superior a
    # 5 cm2/m por face").
    assert vig.armadura_pele_total_cm2_por_face(bw_cm=80.0, h_alma_cm=100.0) == \
        pytest.approx(5.0)


def test_pele_total_h_60_cm_e_a_fronteira_da_dispensa():
    # "Em vigas com altura igual ou inferior a 60 cm, pode ser dispensada..."
    # (17.3.5.2.3, PDF p. 153): h_alma = 60 cm ainda está dispensado (0,0);
    # h_alma = 60,01 cm já exige armadura de pele.
    assert vig.armadura_pele_total_cm2_por_face(bw_cm=20.0, h_alma_cm=60.0) == 0.0
    assert vig.armadura_pele_total_cm2_por_face(bw_cm=20.0, h_alma_cm=60.01) > 0.0


def test_pele_total_viga_t_usa_altura_total_na_dispensa():
    # Viga T: alma abaixo da mesa com 50 cm (<= 60 cm), mas altura TOTAL da
    # viga de 80 cm (> 60 cm). A dispensa de 17.3.5.2.3 (PDF p. 153) é pela
    # altura da viga, não da alma ("Em vigas com altura igual ou inferior a
    # 60 cm, pode ser dispensada..."), então NÃO pode ser dispensada aqui.
    # Antes da correção, a função testava a dispensa sobre h_alma_cm (50 cm)
    # e devolvia 0,0 indevidamente — a favor da insegurança.
    resultado = vig.armadura_pele_total_cm2_por_face(
        bw_cm=20.0, h_alma_cm=50.0, h_total_cm=80.0
    )
    assert resultado > 0.0
    # Ac,alma = 20 * 50 = 1000 cm2; 0,10% * 1000 = 1,0 cm2 por face
    # (teto: 5 cm2/m * 0,50 m = 2,5 cm2 -> não governa).
    assert resultado == pytest.approx(1.0)


def test_pele_total_viga_t_com_altura_total_baixa_ainda_dispensa():
    # Mesma viga T, mas com altura total <= 60 cm: a dispensa se aplica.
    assert vig.armadura_pele_total_cm2_por_face(
        bw_cm=20.0, h_alma_cm=50.0, h_total_cm=60.0
    ) == 0.0


def test_pele_total_sem_h_total_cm_assume_secao_retangular():
    # Compatibilidade: sem informar h_total_cm, o comportamento antigo
    # (seção retangular, onde h_alma_cm == altura total) se mantém.
    assert vig.armadura_pele_total_cm2_por_face(bw_cm=20.0, h_alma_cm=60.0) == 0.0


def test_pele_total_funcao_antiga_continua_igual():
    # A função antiga (taxa por metro) precisa continuar devolvendo o que
    # devolvia antes do T3 — outros módulos e testes dependem dela.
    assert vig.armadura_pele_cm2_por_face(bw_cm=20.0, h_cm=60.0) == 0.0
    assert vig.armadura_pele_cm2_por_face(bw_cm=50.0, h_cm=100.0) == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# 2. γqs na perda de equilíbrio (Tabela 11.3, PDF p. 87-88) — sentido do
#    coeficiente, sem mudar o padrão (gama_qs = 1,0)
# ---------------------------------------------------------------------------
def test_gama_qs_padrao_continua_1_0():
    import inspect
    assinatura = inspect.signature(seg.fnd_equilibrio)
    assert assinatura.parameters["gama_qs"].default == 1.0


def test_gama_qs_menor_da_fnd_maior_lado_favoravel_a_seguranca():
    # Fnd = γgn*Gnk + γq*Qnk - γqs*Qs,mín: quanto menor γqs, menos Qs,mín é
    # subtraído, e maior fica Fnd (a ação instabilizante de cálculo) — o
    # lado a favor da segurança na verificação de perda de equilíbrio
    # (Rd = Fsd >= Sd = Fnd). O padrão γqs = 1,0 é o lado MENOS conservador
    # (Qs,mín entra inteiro a favor do equilíbrio).
    fnd_padrao = seg.fnd_equilibrio(
        Gnk=100.0, Qnk=50.0, Qs_min=20.0, gama_gn=1.4, gama_q=1.4, gama_qs=1.0,
    )
    fnd_qs_reduzido = seg.fnd_equilibrio(
        Gnk=100.0, Qnk=50.0, Qs_min=20.0, gama_gn=1.4, gama_q=1.4, gama_qs=0.9,
    )
    assert fnd_qs_reduzido > fnd_padrao


def test_gama_qs_zero_nao_reduz_fnd_nenhum_caso_extremo_confere_a_formula():
    # Com Qs_min = 0 (nenhuma ação estabilizante mínima), γqs não influencia
    # o resultado — confere que o termo é mesmo subtrativo e isolado.
    fnd_a = seg.fnd_equilibrio(
        Gnk=100.0, Qnk=50.0, Qs_min=0.0, gama_gn=1.4, gama_q=1.4, gama_qs=1.0,
    )
    fnd_b = seg.fnd_equilibrio(
        Gnk=100.0, Qnk=50.0, Qs_min=0.0, gama_gn=1.4, gama_q=1.4, gama_qs=0.5,
    )
    assert fnd_a == pytest.approx(fnd_b)
