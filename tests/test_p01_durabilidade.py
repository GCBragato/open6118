"""Testes do P1 — Durabilidade, cobrimento e abertura de fissura admissível.

Cobre dimensionamento/durabilidade_nbr6118.py e o bloco P1 de
dimensionamento/nucleo_nbr6118.py, contra a ABNT NBR 6118:2026:

  - 5.3.2, Tabela 5.1 (classes de consequência), p. 32-33
  - 6.1, 6.2.4 (vida útil de projeto), p. 34
  - 6.4, Tabela 6.1 (classes de agressividade ambiental), p. 36
  - 7.4.2, Tabela 7.1 (qualidade do concreto), p. 38
  - 7.4.7.1-7.4.7.6, Tabela 7.2 (cobrimento nominal), p. 38-39
  - 13.4.2, Tabela 13.4 (wk,máx), p. 100-101

Os valores esperados vêm da imagem de cada página (SCRATCH\\nbr_png\\pNNN.png),
não do JSON do plano nem de apostila.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr        # noqa: E402
import durabilidade_nbr6118 as dur  # noqa: E402


# =============================================================================
# 5.3.2, Tabela 5.1 — Classes de consequência (p. 32-33)
# =============================================================================
def test_cc_texto_livre_pavimentos():
    """Exemplos do brief do pacote (SCRATCH\\exec\\pacotes\\P1.md)."""
    assert dur.classe_consequencia("Prédio residencial de 6 pavimentos") == "CC3"
    assert dur.classe_consequencia("Prédio residencial de 4 pavimentos") == "CC2"
    assert dur.classe_consequencia("casa térrea unifamiliar") == "CC1"


@pytest.mark.parametrize("tipo_obra", [
    "hospital regional", "escola municipal", "ponte estaiada", "silo de grãos",
    "estádio municipal", "shopping center", "aeroporto internacional",
])
def test_cc3_casos_tipicos_por_palavra_chave(tipo_obra):
    """Tabela 5.1, coluna CC3: casos típicos nomeados, independem de tamanho."""
    assert dur.classe_consequencia(tipo_obra) == "CC3"


def test_cc3_criterios_estruturais():
    assert dur.classe_consequencia(protendida=True) == "CC3"
    assert dur.classe_consequencia(subsolo=True) == "CC3"
    assert dur.classe_consequencia(reforma_elimina_pilar=True) == "CC3"
    assert dur.classe_consequencia(pavimentos_habitaveis=6) == "CC3"  # >5, multifamiliar


def test_cc3_cc2_muro_de_contencao_degrau_2_5m():
    """Tabela 5.1: CC2 até 2,5 m de altura de empuxo; CC3 acima."""
    assert dur.classe_consequencia(altura_muro_m=2.5) == "CC2"
    assert dur.classe_consequencia(altura_muro_m=2.51) == "CC3"


def test_cc3_balanco_degrau_3m():
    """Tabela 5.1: CC3 só acima de 3 m de balanço; <=3 m cai nos outros critérios."""
    assert dur.classe_consequencia(balanco_m=3.0, pavimentos_habitaveis=3) == "CC2"
    assert dur.classe_consequencia(balanco_m=3.01, pavimentos_habitaveis=3) == "CC3"


def test_cc2_cc3_reforma_acrescimo_degrau_5pct():
    """Tabela 5.1: CC2 com acréscimo <=5% sem eliminar pilar; CC3 acima."""
    assert dur.classe_consequencia(reforma_elimina_pilar=False, acrescimo_carga_pct=5.0) == "CC2"
    assert dur.classe_consequencia(reforma_elimina_pilar=False, acrescimo_carga_pct=5.01) == "CC3"


def test_cc2_multifamiliar_ate_5_pavimentos():
    assert dur.classe_consequencia(pavimentos_habitaveis=5) == "CC2"
    assert dur.classe_consequencia(pavimentos_habitaveis=1) == "CC2"


def test_cc1_unifamiliar_e_agricola():
    assert dur.classe_consequencia(unifamiliar=True, pavimentos_habitaveis=2) == "CC1"
    assert dur.classe_consequencia(unifamiliar=True, pavimentos_habitaveis=1) == "CC1"
    assert dur.classe_consequencia(agricola_nao_ocupado=True) == "CC1"


def test_cc_duvida_vira_cc3_item_5_3_3():
    """5.3.3: em caso de dúvida sobre a classe, adotar CC3 para análise."""
    assert dur.classe_consequencia() == "CC3"
    assert dur.classe_consequencia(unifamiliar=True, pavimentos_habitaveis=3) == "CC3"


# =============================================================================
# 6.1, 6.2.4 — Vida útil de projeto (p. 34)
# =============================================================================
def test_vida_util_projeto_50_anos():
    assert dur.VIDA_UTIL_PROJETO_ANOS == 50


# =============================================================================
# 6.4, Tabela 6.1 — Classes de agressividade ambiental (p. 36)
# =============================================================================
@pytest.mark.parametrize("ambiente, esperado", [
    ("rural", "I"),
    ("submerso", "I"),
    ("urbano", "II"),
    ("marinho", "III"),
    ("industrial", "III"),
    ("industrial quimico", "IV"),
    ("respingos de mare", "IV"),
])
def test_tabela_6_1_todas_as_celulas(ambiente, esperado):
    assert dur.classe_agressividade(ambiente) == esperado


def test_tabela_6_1_nota_a_ambiente_interno_ou_revestido():
    """Nota a: microclima interno/face revestida admite uma classe mais branda."""
    assert dur.classe_agressividade("urbano", revestido=True) == "I"
    assert dur.classe_agressividade("marinho", revestido=True) == "II"
    assert dur.classe_agressividade("industrial", revestido=True) == "II"
    assert dur.classe_agressividade("industrial quimico", revestido=True) == "III"


def test_tabela_6_1_nota_b_clima_seco():
    """Nota b: clima seco (UR<=65%) admite uma classe mais branda (não vale para todos)."""
    assert dur.classe_agressividade("urbano", microclima_seco=True) == "I"
    assert dur.classe_agressividade("industrial", microclima_seco=True) == "II"


def test_tabela_6_1_notas_nao_acumulam():
    """As duas notas juntas não reduzem duas classes de uma vez."""
    assert dur.classe_agressividade("industrial", revestido=True, microclima_seco=True) == "II"


def test_tabela_6_1_nota_nao_aplicavel_levanta_erro():
    with pytest.raises(ValueError):
        dur.classe_agressividade("marinho", microclima_seco=True)       # nota b não existe p/ marinho
    with pytest.raises(ValueError):
        dur.classe_agressividade("industrial quimico", microclima_seco=True)  # idem, IV
    with pytest.raises(ValueError):
        dur.classe_agressividade("respingos de mare", revestido=True)   # sem notas
    with pytest.raises(ValueError):
        dur.classe_agressividade("rural", revestido=True)               # já é a mínima


def test_tabela_6_1_ambiente_desconhecido():
    with pytest.raises(ValueError):
        dur.classe_agressividade("lunar")


# =============================================================================
# 7.4.2, Tabela 7.1 — Qualidade do concreto (p. 38)
# =============================================================================
@pytest.mark.parametrize("caa, ac_ca, classe_ca, ac_cp, classe_cp", [
    ("I", 0.65, 20, 0.60, 25),
    ("II", 0.60, 25, 0.55, 30),
    ("III", 0.55, 30, 0.50, 35),
    ("IV", 0.45, 40, 0.45, 40),
])
def test_tabela_7_1_todas_as_celulas(caa, ac_ca, classe_ca, ac_cp, classe_cp):
    assert dur.relacao_ac_maxima(caa, protendido=False) == pytest.approx(ac_ca)
    assert dur.classe_concreto_minima(caa, protendido=False) == classe_ca
    assert dur.relacao_ac_maxima(caa, protendido=True) == pytest.approx(ac_cp)
    assert dur.classe_concreto_minima(caa, protendido=True) == classe_cp


def test_tabela_7_1_caa_aceita_variantes():
    assert dur.relacao_ac_maxima("CAA III") == pytest.approx(0.55)
    assert dur.classe_concreto_minima("CAIII") == 30


# =============================================================================
# 7.4.7.1-7.4.7.3 — cnom = cmín + Δc (p. 38)
# =============================================================================
def test_cmin_cnom_caa_ii_laje():
    """Item do pacote: cnom(CAA II, laje) = 25 mm = cmín + 10; cmín = 15 mm."""
    assert nbr.cobrimento_minimo_mm("II", "laje") == pytest.approx(15.0)
    assert nbr.cobrimento_nominal("II", "laje") == pytest.approx(25.0)


def test_cnom_delta_c_10mm_e_argumento_explicito():
    assert nbr.cobrimento_nominal("II", "laje", delta_c_mm=10.0) == pytest.approx(25.0)
    # cmin=15mm (independente de Delta_c); com Delta_c=12mm, cnom=15+12=27mm
    assert nbr.cobrimento_nominal("II", "laje", delta_c_mm=12.0) == pytest.approx(27.0)


# =============================================================================
# 7.4.7, Tabela 7.2 — cobrimento nominal, todas as células (p. 39)
# =============================================================================
@pytest.mark.parametrize("elemento, protendido, esperado", [
    ("laje", False, (20, 25, 35, 45)),
    ("viga", False, (25, 30, 40, 50)),
    ("pilar", False, (25, 30, 40, 50)),
    ("solo", False, (30, 30, 40, 50)),
    ("laje", True, (25, 30, 40, 50)),
    ("viga", True, (30, 35, 45, 55)),
    ("pilar", True, (30, 35, 45, 55)),
])
def test_tabela_7_2_todas_as_celulas(elemento, protendido, esperado):
    for caa, valor in zip(("I", "II", "III", "IV"), esperado):
        assert nbr.cobrimento_nominal(caa, elemento, protendido) == pytest.approx(valor)


def test_tabela_7_2_nota_d_pilar_solo():
    assert nbr.cobrimento_nominal("I", "pilar solo") == pytest.approx(45.0)
    assert nbr.cobrimento_nominal("II", "pilar solo") == pytest.approx(45.0)
    assert nbr.cobrimento_nominal("III", "pilar solo") == pytest.approx(45.0)
    assert nbr.cobrimento_nominal("IV", "pilar solo") == pytest.approx(50.0)


# =============================================================================
# 7.4.7.4 — Δc = 5 mm em pré-moldados com controle rigoroso (NBR 9062, p. 38)
# =============================================================================
def test_delta_c_5mm_premoldados_reduz_5mm_o_cnom_da_tabela():
    """Item do pacote: cnom reduzido = cnom(Tabela 7.2) - 5 mm."""
    cnom_tabela = nbr.cobrimento_nominal("III", "viga")             # 40, Δc=10
    cnom_reduzido = nbr.cobrimento_nominal("III", "viga", delta_c_mm=5.0)
    assert cnom_reduzido == pytest.approx(cnom_tabela - 5.0)
    assert cnom_reduzido == pytest.approx(35.0)


# =============================================================================
# Redução por classe de concreto superior (nota após a Tabela 7.2, p. 39)
# =============================================================================
def test_reducao_5mm_classe_de_concreto_superior():
    cnom_tabela = nbr.cobrimento_nominal("II", "laje")               # 25
    cnom_reduzido = nbr.cobrimento_nominal("II", "laje", reducao_classe_superior=True)
    assert cnom_reduzido == pytest.approx(cnom_tabela - 5.0)


def test_reducao_classe_superior_nao_atinge_piso_de_pilar_solo():
    """A nota d (cnom >= 45 mm) é um mínimo absoluto: não sofre a redução."""
    assert nbr.cobrimento_nominal("I", "pilar solo", reducao_classe_superior=True) == pytest.approx(45.0)


# =============================================================================
# Nota b da Tabela 7.2 — face revestida, cnom >= 15 mm (p. 39)
# =============================================================================
def test_face_revestida_laje_e_viga_cnom_15mm():
    assert nbr.cobrimento_nominal("IV", "laje", face_revestida=True) == pytest.approx(15.0)
    assert nbr.cobrimento_nominal("I", "viga", face_revestida=True) == pytest.approx(15.0)


def test_face_revestida_nao_vale_para_pilar_solo_ou_protendido():
    with pytest.raises(ValueError):
        nbr.cobrimento_nominal("II", "pilar", face_revestida=True)
    with pytest.raises(ValueError):
        nbr.cobrimento_nominal("II", "solo", face_revestida=True)
    with pytest.raises(ValueError):
        nbr.cobrimento_nominal("II", "laje", protendido=True, face_revestida=True)


# =============================================================================
# Nota c da Tabela 7.2 — superfície exposta a ambiente quimicamente agressivo
# =============================================================================
def test_superficie_exposta_agressiva_forca_caa_iv():
    for elemento, protendido in (("laje", False), ("viga", False), ("laje", True)):
        for caa in ("I", "II", "III"):
            assert nbr.cobrimento_nominal(caa, elemento, protendido, superficie_exposta_agressiva=True) \
                == pytest.approx(nbr.cobrimento_nominal("IV", elemento, protendido))


# =============================================================================
# Entradas inválidas de cobrimento_nominal seguem levantando ValueError
# (aceite: assinatura antiga preservada)
# =============================================================================
def test_cobrimento_nominal_entradas_invalidas_continuam_levantando():
    with pytest.raises(ValueError):
        nbr.cobrimento_nominal("V", "laje")
    with pytest.raises(ValueError):
        nbr.cobrimento_nominal("I", "solo", protendido=True)
    with pytest.raises(ValueError):
        nbr.cobrimento_nominal("I", "parede")


# =============================================================================
# 7.4.7.5 — cnom mínimo por barra, feixe e bainha (p. 39)
# =============================================================================
def test_phi_feixe_formula_phi_vezes_raiz_n():
    """Item do pacote: feixe de 3 barras de 20 mm -> phi_feixe = 20*sqrt(3) = 34,6 mm."""
    assert dur.phi_feixe_mm(20.0, 3) == pytest.approx(20.0 * 3 ** 0.5)
    assert dur.phi_feixe_mm(20.0, 3) == pytest.approx(34.64, abs=0.01)


def test_phi_feixe_exige_ao_menos_2_barras():
    with pytest.raises(ValueError):
        dur.phi_feixe_mm(20.0, 1)


def test_verificar_cobrimento_so_barra_ok():
    r = dur.verificar_cobrimento(cnom_mm=25.0, phi_mm=20.0)
    assert r.ok is True
    assert r.governante == "barra (7.4.7.5 d)"
    assert r.phi_feixe_mm is None and r.phi_bainha_mm is None
    assert len(r.memoria) >= 2


def test_verificar_cobrimento_barra_maior_que_cnom_levanta_aviso():
    """Testes e aceite do pacote: phi de barra/feixe maior que cnom levanta aviso."""
    with pytest.warns(dur.AvisoNBR6118):
        r = dur.verificar_cobrimento(cnom_mm=15.0, phi_mm=20.0)
    assert r.ok is False
    assert r.governante == "barra (7.4.7.5 d)"


def test_verificar_cobrimento_feixe_maior_que_cnom_levanta_aviso():
    """phi de feixe (3 barras de 20 mm, phi_feixe=34,6mm) maior que cnom levanta aviso."""
    feixe = dur.phi_feixe_mm(20.0, 3)
    with pytest.warns(dur.AvisoNBR6118):
        r = dur.verificar_cobrimento(cnom_mm=30.0, phi_mm=20.0, phi_feixe_mm=feixe)
    assert r.ok is False
    assert r.governante == "feixe (7.4.7.5 e)"
    # cnom suficiente não levanta aviso
    with warnings.catch_warnings():
        warnings.simplefilter("error", dur.AvisoNBR6118)
        r_ok = dur.verificar_cobrimento(cnom_mm=35.0, phi_mm=20.0, phi_feixe_mm=feixe)
    assert r_ok.ok is True


def test_verificar_cobrimento_bainha_metade_do_diametro():
    """f) cnom >= 0,5*phi_bainha: bainha de 80mm exige cnom >= 40mm."""
    r_ok = dur.verificar_cobrimento(cnom_mm=40.0, phi_mm=10.0, phi_bainha_mm=80.0)
    assert r_ok.ok is True
    assert r_ok.minimo_bainha_mm == pytest.approx(40.0)
    with pytest.warns(dur.AvisoNBR6118):
        r_falha = dur.verificar_cobrimento(cnom_mm=39.0, phi_mm=10.0, phi_bainha_mm=80.0)
    assert r_falha.ok is False
    assert r_falha.governante == "bainha (7.4.7.5 f)"


def test_verificar_cobrimento_memoria_usa_nao_ok_com_acento():
    """Texto para o usuario final (memoria de calculo) tem de usar "nao ok"
    com acento, nunca "nao ok" sem acento -- ver convencao 5 do brief.

    Cobre os tres pontos da funcao que geram esse texto: barra, feixe e
    bainha, cada um forcado a reprovar para acionar o ramo "else" da
    f-string.
    """
    with pytest.warns(dur.AvisoNBR6118):
        r_barra = dur.verificar_cobrimento(cnom_mm=15.0, phi_mm=20.0)
    assert "não ok" in r_barra.memoria[0]
    assert "nao ok" not in r_barra.memoria[0]

    feixe = dur.phi_feixe_mm(20.0, 3)
    with pytest.warns(dur.AvisoNBR6118):
        r_feixe = dur.verificar_cobrimento(cnom_mm=30.0, phi_mm=20.0, phi_feixe_mm=feixe)
    assert any("não ok" in linha for linha in r_feixe.memoria)
    assert not any("nao ok" in linha for linha in r_feixe.memoria)

    with pytest.warns(dur.AvisoNBR6118):
        r_bainha = dur.verificar_cobrimento(cnom_mm=39.0, phi_mm=10.0, phi_bainha_mm=80.0)
    assert any("não ok" in linha for linha in r_bainha.memoria)
    assert not any("nao ok" in linha for linha in r_bainha.memoria)


# =============================================================================
# 7.4.7.6 — dmáx <= 1,2*cnom (p. 39)
# =============================================================================
def test_dmax_agregado_item_do_pacote():
    """Item do pacote: cnom=30mm -> dmax admissível = 36mm."""
    assert dur.dmax_agregado_mm(30.0) == pytest.approx(36.0)


@pytest.mark.parametrize("cnom, dmax", [(20.0, 24.0), (25.0, 30.0), (50.0, 60.0)])
def test_dmax_agregado_proporcional(cnom, dmax):
    assert dur.dmax_agregado_mm(cnom) == pytest.approx(dmax)


# =============================================================================
# 13.4.2, Tabela 13.4 — wk,máx (p. 100-101)
# =============================================================================
def test_wk_max_concreto_simples_nao_exige():
    assert nbr.wk_max_mm("simples", "II") == (None, "-")


@pytest.mark.parametrize("caa, esperado", [
    ("I", 0.4), ("II", 0.3), ("III", 0.3), ("IV", 0.2),
])
def test_wk_max_concreto_armado_todas_as_celulas(caa, esperado):
    """Item do pacote: armado CAA II -> wk_max=0,3, comb=frequente."""
    wk, comb = nbr.wk_max_mm("armado", caa)
    assert wk == pytest.approx(esperado)
    assert comb == "frequente"


def test_wk_max_protendido_nivel1_faixas_de_caa():
    """Item do pacote: protendido nível 1 pós-tração CAA II -> wk_max=0,2."""
    assert nbr.wk_max_mm("protendido", "I", 1, "pre-tracao") == (pytest.approx(0.2), "frequente")
    assert nbr.wk_max_mm("protendido", "I", 1, "pos-tracao") == (pytest.approx(0.2), "frequente")
    assert nbr.wk_max_mm("protendido", "II", 1, "pos-tracao") == (pytest.approx(0.2), "frequente")
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.wk_max_mm("protendido", "II", 1, "pre-tracao")     # pré só CAA I
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.wk_max_mm("protendido", "III", 1, "pos-tracao")    # pós só CAA I e II


def test_wk_max_protendido_nivel2_duas_verificacoes():
    for caa in ("I", "II"):
        wk, comb = nbr.wk_max_mm("protendido", caa, 2, "pre-tracao")
        assert wk is None
        assert "ELS-F" in comb and "frequente" in comb
        assert "ELS-D" in comb and "quase-permanente" in comb
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.wk_max_mm("protendido", "III", 2, "pre-tracao")    # pré só CAA I e II
    for caa in ("I", "II", "III", "IV"):
        wk, comb = nbr.wk_max_mm("protendido", caa, 2, "pos-tracao")
        assert wk is None
        assert "ELS-F" in comb and "ELS-D" in comb


def test_wk_max_protendido_nivel3_duas_verificacoes_qualquer_caa():
    """Item do pacote: nível 3, pré-tração, qualquer CAA -> ELS-F(rara)/ELS-D(frequente)."""
    for tp in ("pre-tracao", "pos-tracao"):
        for caa in ("I", "II", "III", "IV"):
            wk, comb = nbr.wk_max_mm("protendido", caa, 3, tp)
            assert wk is None
            assert "ELS-F" in comb and "rara" in comb
            assert "ELS-D" in comb and "frequente" in comb


def test_wk_max_mm_entradas_invalidas():
    with pytest.raises(ValueError):
        nbr.wk_max_mm("madeira", "I")
    with pytest.raises(ValueError):
        nbr.wk_max_mm("protendido", "I", nivel_protensao=4, tipo_protensao="pre-tracao")
    with pytest.raises(ValueError):
        nbr.wk_max_mm("protendido", "I", nivel_protensao=1, tipo_protensao="mista")
    with pytest.raises(ValueError):
        nbr.wk_max_mm("armado", "V")


# =============================================================================
# viga_servico_nbr6118.abertura_fissura_wk aceita caa= (mantendo wk_max_mm
# explícito como alternativa)
# =============================================================================
def test_abertura_fissura_wk_aceita_caa():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))
    import viga_servico_nbr6118 as vs   # noqa: E402

    # sem caa: comportamento antigo, wk_max_mm explicito (default 0.30)
    r_antigo = vs.abertura_fissura_wk(
        phi_mm=16.0, sigma_si_kncm2=20.0, Acr_cm2=800.0, As_cm2=8.0, fck_mpa=30.0,
    )
    assert r_antigo.wk_max_mm == pytest.approx(0.30)

    # com caa: busca o limite na Tabela 13.4 (armado, CAA II -> 0,3mm)
    r_caa = vs.abertura_fissura_wk(
        phi_mm=16.0, sigma_si_kncm2=20.0, Acr_cm2=800.0, As_cm2=8.0, fck_mpa=30.0,
        caa="II",
    )
    assert r_caa.wk_max_mm == pytest.approx(0.3)
    assert r_caa.wk_mm == pytest.approx(r_antigo.wk_mm)   # o wk calculado não muda, só o limite


def test_abertura_fissura_wk_caa_protendido_nivel_sem_wk_max_levanta_erro():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))
    import viga_servico_nbr6118 as vs   # noqa: E402

    with pytest.raises(ValueError):
        vs.abertura_fissura_wk(
            phi_mm=16.0, sigma_si_kncm2=20.0, Acr_cm2=800.0, As_cm2=8.0, fck_mpa=30.0,
            caa="II", tipo_concreto="protendido", nivel_protensao=2, tipo_protensao="pre-tracao",
        )


# =============================================================================
# Legado: secoes_norma/sec7.CAAPropriedades vira fachada com DeprecationWarning
# =============================================================================
def test_sec7_caapropriedades_emite_deprecation_e_mantem_numeros():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "secoes_norma"))
    import sec7   # noqa: E402

    with pytest.warns(DeprecationWarning):
        resultado = sec7.CAAPropriedades("CAI", "CA")
    assert resultado[0] == pytest.approx(0.65)
    assert resultado[1] == "C20"
    assert resultado[2] == 20      # laje
    assert resultado[3] == 25      # viga/pilar (LEG-01)
    assert resultado[4] == 30      # solo


def test_sec7_caapropriedades_protendido_sem_cobrimento_de_solo():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "secoes_norma"))
    import sec7   # noqa: E402

    with pytest.warns(DeprecationWarning):
        resultado = sec7.CAAPropriedades("CAII", "CP")
    assert resultado[0] == pytest.approx(0.55)
    assert resultado[1] == "C30"
    assert resultado[4] == "-"


# =============================================================================
# AvisoNBR6118 mudou de casa para o núcleo (P1)
# =============================================================================
def test_avisonbr6118_mora_no_nucleo_e_e_reexportado():
    assert dur.AvisoNBR6118 is nbr.AvisoNBR6118
    assert issubclass(nbr.AvisoNBR6118, UserWarning)
