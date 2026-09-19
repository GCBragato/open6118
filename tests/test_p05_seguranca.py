"""Testes do P5 — Verificação de segurança e coeficientes de resistência
(NBR 6118:2026, 10.3, 11.8.2.1/Tabela 11.3, 12.4, 12.4.1, 12.4.2 e 12.5.2).

Os valores esperados saem da norma (página do PDF indicada em cada teste). As
contas à mão estão nos comentários.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import acoes_nbr6118 as ac  # noqa: E402
import seguranca_nbr6118 as seg  # noqa: E402


# ---------------------------------------------------------------------------
# 10.3 — Estados-limites últimos a verificar (p. 74-75)
# ---------------------------------------------------------------------------
def test_estados_limites_ultimos_tem_as_oito_letras_a_h():
    assert set(seg.ESTADOS_LIMITES_ULTIMOS) == set("abcdefgh")


def test_estados_limites_ultimos_textos_conforme_10_3():
    e = seg.ESTADOS_LIMITES_ULTIMOS
    assert e["a"] == "Perda do equilíbrio da estrutura, admitida como corpo rígido."
    assert "2ª ordem" in e["c"]
    assert "Seção 23" in e["d"]
    assert e["e"] == "Estado-limite último de colapso progressivo."
    assert "NBR 15200" in e["f"]
    assert "NBR 15421" in e["g"]
    assert "casos especiais" in e["h"]


def test_checklist_elu_marca_os_verificados():
    linhas = seg.checklist_elu({"a", "b"})
    assert linhas[0].startswith("Estados-limites últimos a verificar")
    marcados = {l.split(")")[0].strip()[-1]: l.startswith("  [x]") for l in linhas[1:]}
    assert marcados["a"] is True
    assert marcados["b"] is True
    assert marcados["c"] is False
    assert marcados["h"] is False
    assert len(linhas) == 1 + 8


def test_checklist_elu_aceita_maiuscula_e_espaco():
    linhas = seg.checklist_elu({" A ", "H"})
    assert any(l.startswith("  [x] a)") for l in linhas)
    assert any(l.startswith("  [x] h)") for l in linhas)


def test_checklist_elu_letra_desconhecida_levanta():
    with pytest.raises(ValueError):
        seg.checklist_elu({"i"})
    with pytest.raises(ValueError):
        seg.checklist_elu({"1"})


# ---------------------------------------------------------------------------
# 12.5.2 — Condição geral de segurança Rd >= Sd (p. 92)
# ---------------------------------------------------------------------------
def test_rd_igual_sd_passa():
    r = seg.verificar_seguranca(100.0, 100.0, rotulo="Md x MRd")
    assert r.ok is True
    assert r.Rd == 100.0 and r.Sd == 100.0
    assert r.item == "12.5.2"


def test_rd_igual_sd_vezes_1_menos_1e_6_nao_passa():
    # Enunciado do brief: "Rd = Sd·(1 − 1e-6) não passa" -> Rd é MENOR que Sd.
    Sd = 100.0
    Rd = Sd * (1 - 1e-6)
    r = seg.verificar_seguranca(Rd, Sd)
    assert r.ok is False
    assert Rd < Sd


def test_tolerancia_1e_9_nos_dois_lados():
    Sd = 100.0
    r_ok = seg.verificar_seguranca(Sd - 0.5e-9, Sd)
    assert r_ok.ok is True
    r_nok = seg.verificar_seguranca(Sd - 2e-9, Sd)
    assert r_nok.ok is False


def test_rd_maior_que_sd_passa():
    r = seg.verificar_seguranca(150.0, 100.0)
    assert r.ok is True


def test_memoria_cita_item_e_rotulo():
    r = seg.verificar_seguranca(10.0, 5.0, rotulo="Vsd x VRd2", item="17.4.2.2")
    assert any("17.4.2.2" in l for l in r.memoria)
    assert any("Vsd x VRd2" in l for l in r.memoria)


# ---------------------------------------------------------------------------
# 11.8.2.1, Tabela 11.3 — Perda de equilíbrio como corpo rígido (p. 87-88)
# ---------------------------------------------------------------------------
def test_fsd_equilibrio_normal_gama_favoravel_e_1():
    # Fsd = gama_gs*Gsk + Rd = 1,0*200 + 30 = 230
    assert seg.fsd_equilibrio(Gsk=200.0, Rd=30.0) == pytest.approx(230.0)


def test_fsd_equilibrio_sem_rd():
    assert seg.fsd_equilibrio(Gsk=80.0) == pytest.approx(80.0)


def test_fnd_equilibrio_normal():
    # Fnd = gama_gn*Gnk + gama_q*Qnk - gama_qs*Qs_min
    #     = 1,4*50 + 1,4*40 - 1,0*10 = 70 + 56 - 10 = 116
    Fnd = seg.fnd_equilibrio(Gnk=50.0, Qnk=40.0, Qs_min=10.0)
    assert Fnd == pytest.approx(1.4 * 50.0 + 1.4 * 40.0 - 1.0 * 10.0)
    assert Fnd == pytest.approx(116.0)


def test_fnd_equilibrio_sem_qs_min():
    assert seg.fnd_equilibrio(Gnk=50.0, Qnk=40.0) == pytest.approx(1.4 * 50.0 + 1.4 * 40.0)


def test_fnd_equilibrio_gama_g_reduzido_pela_nota_a(monkeypatch):
    monkeypatch.setattr(nbr, "GAMA_G", 1.3)
    Fnd = seg.fnd_equilibrio(Gnk=50.0, Qnk=40.0)
    assert Fnd == pytest.approx(1.3 * 50.0 + 1.4 * 40.0)


def test_fnd_equilibrio_combinacao_especial():
    # Tabela 11.1: especial/construção -> permanente D = 1,3; variável G = 1,2.
    Fnd = seg.fnd_equilibrio(Gnk=50.0, Qnk=40.0, combinacao="especial")
    assert Fnd == pytest.approx(1.3 * 50.0 + 1.2 * 40.0)


def test_fnd_equilibrio_combinacao_excepcional():
    # Tabela 11.1: excepcional -> permanente D = 1,2; variável G = 1,0.
    Fnd = seg.fnd_equilibrio(Gnk=50.0, Qnk=40.0, combinacao="excepcional")
    assert Fnd == pytest.approx(1.2 * 50.0 + 1.0 * 40.0)


def test_fnd_equilibrio_gama_explicito_sobrepoe_tabela():
    Fnd = seg.fnd_equilibrio(Gnk=50.0, Qnk=40.0, gama_gn=1.1, gama_q=1.2, gama_qs=0.5, Qs_min=10.0)
    assert Fnd == pytest.approx(1.1 * 50.0 + 1.2 * 40.0 - 0.5 * 10.0)


def test_verificar_equilibrio_corpo_rigido_passa_quando_fsd_maior_igual_fnd():
    r = seg.verificar_equilibrio_corpo_rigido(230.0, 116.0)
    assert r.ok is True
    assert r.item == "11.8.2.1"


def test_verificar_equilibrio_corpo_rigido_nao_passa():
    r = seg.verificar_equilibrio_corpo_rigido(100.0, 116.0)
    assert r.ok is False


def test_sapata_excentrica_sob_vento_fsd_maior_igual_fnd():
    # Sapata excêntrica sob vento: peso próprio + do solo estabiliza o
    # tombamento; o vento (variável instabilizante principal) e o peso menos
    # favorável instabilizam.
    Gsk = 500.0    # peso próprio + solo sobre a sapata, estabilizante (kN)
    Gnk = 20.0     # parcela permanente instabilizante (kN)
    Qnk = 80.0     # vento reduzido a Qnk = Q1k (sem outras variáveis), kN
    Fsd = seg.fsd_equilibrio(Gsk=Gsk)                       # 1,0*500 = 500
    Fnd = seg.fnd_equilibrio(Gnk=Gnk, Qnk=Qnk)              # 1,4*20 + 1,4*80 = 140
    assert Fsd == pytest.approx(500.0)
    assert Fnd == pytest.approx(140.0)
    r = seg.verificar_equilibrio_corpo_rigido(Fsd, Fnd)
    assert r.ok is True


# ---------------------------------------------------------------------------
# 12.4 — Decomposição gama_m = gama_m1*gama_m2*gama_m3 (p. 91)
# ---------------------------------------------------------------------------
def test_gama_m_composto():
    assert nbr.gama_m_composto(1.1, 1.2, 1.3) == pytest.approx(1.1 * 1.2 * 1.3)


def test_gama_m_composto_negativo_levanta():
    with pytest.raises(ValueError):
        nbr.gama_m_composto(-1.0, 1.0, 1.0)
    with pytest.raises(ValueError):
        nbr.gama_m_composto(1.0, -1.0, 1.0)
    with pytest.raises(ValueError):
        nbr.gama_m_composto(1.0, 1.0, -1.0)


def test_gama_m_els_e_1():
    assert nbr.GAMA_M_ELS == 1.0


# ---------------------------------------------------------------------------
# 12.4.1 — Tabela 12.1 e os três fatores de 1,1 (p. 91)
# ---------------------------------------------------------------------------
def test_tabela_12_1_valores_base():
    assert nbr.GAMAS_TABELA_12_1["normal"] == (1.4, 1.15)
    assert nbr.GAMAS_TABELA_12_1["especial"] == (1.2, 1.15)
    assert nbr.GAMAS_TABELA_12_1["construcao"] == (1.2, 1.15)
    assert nbr.GAMAS_TABELA_12_1["excepcional"] == (1.2, 1.0)


@pytest.mark.parametrize("comb,esperado", [
    ("normal", 1.4), ("especial", 1.2), ("construcao", 1.2), ("excepcional", 1.2),
])
def test_gama_c_ajustado_sem_flag_reproduz_tabela_12_1(comb, esperado):
    assert nbr.gama_c_ajustado(comb) == pytest.approx(esperado)


def test_gama_c_ajustado_execucao_desfavoravel_multiplica_por_1_1():
    # 12.4.1: gamma_c * 1,1 -> 1,4 * 1,1 = 1,54
    assert nbr.gama_c_ajustado("normal", execucao_desfavoravel=True) == pytest.approx(1.4 * 1.1)
    assert nbr.gama_c_ajustado("normal", execucao_desfavoravel=True) == pytest.approx(1.54)


def test_gama_c_ajustado_testemunho_extraido_divide_por_1_1():
    # 12.4.1: gamma_c / 1,1 -> 1,4 / 1,1 = 1,272727...
    assert nbr.gama_c_ajustado("normal", testemunho_extraido=True) == pytest.approx(1.4 / 1.1)


def test_gama_c_ajustado_nao_aceita_as_duas_flags_juntas():
    with pytest.raises(ValueError):
        nbr.gama_c_ajustado("normal", execucao_desfavoravel=True, testemunho_extraido=True)


def test_gama_s_ajustado_sem_flag_reproduz_tabela_12_1():
    assert nbr.gama_s_ajustado("normal") == pytest.approx(1.15)
    assert nbr.gama_s_ajustado("excepcional") == pytest.approx(1.0)


def test_gama_s_ajustado_ca25_sem_controle_multiplica_por_1_1():
    # 12.4.1: gamma_s * 1,1 -> 1,15 * 1,1 = 1,265
    assert nbr.gama_s_ajustado("normal", ca25_sem_controle=True) == pytest.approx(1.15 * 1.1)
    assert nbr.gama_s_ajustado("normal", ca25_sem_controle=True) == pytest.approx(1.265)


def test_gama_c_e_gama_s_ajustado_combinacao_desconhecida_levanta():
    with pytest.raises(ValueError):
        nbr.gama_c_ajustado("invalida")
    with pytest.raises(ValueError):
        nbr.gama_s_ajustado("invalida")
