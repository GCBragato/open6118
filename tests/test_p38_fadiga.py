"""Testes do P38 -- Fadiga da armadura, curvas S-N e vibração (NBR 6118:2026,
Seção 23: 23.3, 23.5.1, 23.5.5, 23.6).

Valores esperados tirados das imagens das páginas do PDF (SCRATCH/nbr_png):
p215-p216 (23.3, Tabela 23.1); p217 (23.5.1, Palmgren-Miner); p220-p221
(23.5.5, Tabela 23.2, notas d e e); p222 (Tabela 23.3, Figura 23.2);
p223 (relevo de nervura r/h e 23.6). As contas à mão estão nos comentários.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import fadiga_nbr6118 as F  # noqa: E402
import nucleo_nbr6118 as nbr  # noqa: E402


# ===========================================================================
# 23.3 -- Tabela 23.1 e verificação de vibrações excessivas (PDF p. 215-216)
# ===========================================================================
def test_231_tabela_fcrit_todos_os_valores():
    """Tabela 23.1, os 5 usos (PDF p. 216)."""
    assert F.fcrit_tabela_23_1("ginasio_academia") == 8.0
    assert F.fcrit_tabela_23_1("sala_danca_concerto_sem_cadeira_fixa") == 7.0
    assert F.fcrit_tabela_23_1("passarela_pedestres_ciclistas") == 4.5
    assert F.fcrit_tabela_23_1("escritorio") == 4.0
    assert F.fcrit_tabela_23_1("sala_concerto_com_cadeira_fixa") == 3.5


def test_231_fcrit_uso_desconhecido_leva_a_valueerror():
    with pytest.raises(ValueError):
        F.fcrit_tabela_23_1("fabrica")


def test_233_fn_maior_que_1_2_fcrit_passa():
    """23.3: fn > 1,2 fcrit -- escritório, fcrit=4,0 -> limite=4,8; fn=5,0 ok."""
    r = F.verificar_vibracao(5.0, uso="escritorio")
    assert r.fcrit_hz == 4.0
    assert r.limite_hz == pytest.approx(4.8)
    assert r.ok is True


def test_233_fn_menor_que_1_2_fcrit_reprova():
    """fn=4,5 < 1,2 x 4,0 = 4,8 -> reprova."""
    r = F.verificar_vibracao(4.5, uso="escritorio")
    assert r.ok is False


def test_233_fronteira_1_2_fcrit_exata_nao_passa():
    """A norma pede fn > 1,2 fcrit (desigualdade estrita); fn = limite exato não passa."""
    r = F.verificar_vibracao(4.8, fcrit_hz=4.0)
    assert r.ok is False


def test_233_piso_absoluto_3hz_reprova_mesmo_com_fcrit_baixo():
    """Em nenhum caso fn < 3 Hz, mesmo que fn > 1,2 fcrit (fcrit=2,0 -> limite=2,4;
    fn=2,9 > 2,4 mas < 3,0 Hz -> reprova pelo piso)."""
    r = F.verificar_vibracao(2.9, fcrit_hz=2.0)
    assert r.limite_hz == pytest.approx(2.4)
    assert 2.9 > r.limite_hz
    assert r.ok is False
    assert "piso" in r.governante


def test_233_sem_uso_nem_fcrit_leva_a_valueerror():
    with pytest.raises(ValueError):
        F.verificar_vibracao(5.0)


# ===========================================================================
# 23.5.1 -- Faixa de aplicabilidade (PDF p. 216-217)
# ===========================================================================
def test_2351_faixa_aplicabilidade_fronteiras_ok():
    assert F.faixa_aplicabilidade(20_000) == 20_000.0
    assert F.faixa_aplicabilidade(2_000_000) == 2_000_000.0
    assert F.faixa_aplicabilidade(500_000) == 500_000.0


def test_2351_abaixo_de_20000_fora_do_campo():
    """n=19 999 -> fadiga de alta intensidade, fora do campo de aplicação (23.5.1)."""
    with pytest.raises(nbr.FaixaNormativaError):
        F.faixa_aplicabilidade(19_999)


def test_2351_acima_de_2_milhoes_fora_do_campo():
    """n=2 000 001 -> fora do campo coberto, precisa de análise especial (23.5.1)."""
    with pytest.raises(nbr.FaixaNormativaError):
        F.faixa_aplicabilidade(2_000_001)


# ===========================================================================
# 23.5.1 -- Palmgren-Miner, soma(n_i/N_i) <= 1 (PDF p. 217)
# ===========================================================================
def test_palmgren_miner_um_patamar_no_limite():
    """n_i = N_i -> soma = 1,0 (limite, ainda ok pela tolerância de verificar_seguranca)."""
    r = F.palmgren_miner([(1.0e6, 1.0e6)])
    assert r.dano_total == pytest.approx(1.0)
    assert r.ok is True


def test_palmgren_miner_dois_patamares_metade_do_dano_cada():
    """Dois patamares com metade do dano cada -> soma = 0,5 + 0,5 = 1,0."""
    r = F.palmgren_miner([(5.0e5, 1.0e6), (5.0e5, 1.0e6)])
    assert r.parcelas == pytest.approx((0.5, 0.5))
    assert r.dano_total == pytest.approx(1.0)
    assert r.ok is True


def test_palmgren_miner_acima_de_1_reprova():
    r = F.palmgren_miner([(1.5e6, 1.0e6)])
    assert r.dano_total == pytest.approx(1.5)
    assert r.ok is False


def test_palmgren_miner_espectro_vazio_leva_a_valueerror():
    with pytest.raises(ValueError):
        F.palmgren_miner([])


def test_palmgren_miner_N_i_zero_leva_a_valueerror():
    with pytest.raises(ValueError):
        F.palmgren_miner([(1.0, 0.0)])


# ===========================================================================
# 23.5.5 -- Tabela 23.2, armadura passiva CA-50 (PDF p. 220), célula a célula
# ===========================================================================
_PHIS = (10.0, 12.5, 16.0, 20.0, 22.0, 25.0, 32.0, 40.0)

_BARRA_RETA = (190.0, 190.0, 190.0, 185.0, 180.0, 175.0, 165.0, 150.0)


@pytest.mark.parametrize("phi,esperado", list(zip(_PHIS, _BARRA_RETA)))
def test_tabela232_barra_reta_todas_as_celulas(phi, esperado):
    """Barras retas ou dobradas com D >= 25*phi, Tipo T1 (PDF p. 220)."""
    assert F.delta_fsd_fad("barra_reta", phi) == pytest.approx(esperado)


_ESTRIBO_8PHI = (105.0, 105.0, 105.0, 105.0, 100.0, 95.0, 90.0, 85.0)


@pytest.mark.parametrize("phi,esperado", list(zip(_PHIS, _ESTRIBO_8PHI)))
def test_tabela232_estribo_dmin_8phi_todas_as_celulas(phi, esperado):
    """Dmin = 8*phi, phi >= 20 mm, Tipo T1 (PDF p. 220)."""
    assert F.delta_fsd_fad("estribo_dmin_8phi", phi) == pytest.approx(esperado)


def test_tabela232_estribo_dmin_5phi_celulas_definidas():
    """Dmin = 5*phi, phi < 20 mm -- só phi=10; 12,5; 16 definidos (90 MPa)."""
    assert F.delta_fsd_fad("estribo_dmin_5phi", 10.0) == pytest.approx(90.0)
    assert F.delta_fsd_fad("estribo_dmin_5phi", 12.5) == pytest.approx(90.0)
    assert F.delta_fsd_fad("estribo_dmin_5phi", 16.0) == pytest.approx(90.0)


@pytest.mark.parametrize("phi", (20.0, 22.0, 25.0, 32.0, 40.0))
def test_tabela232_estribo_dmin_5phi_celulas_traco_levantam_erro(phi):
    """phi >= 20 mm: célula '-' (fora da faixa de Dmin=5*phi) -- a norma não define."""
    with pytest.raises(nbr.FaixaNormativaError):
        F.delta_fsd_fad("estribo_dmin_5phi", phi)


def test_tabela232_estribo_dmin_3phi_celula_definida():
    """Dmin = 3*phi, phi <= 10 mm -- só phi=10 definido (85 MPa)."""
    assert F.delta_fsd_fad("estribo_dmin_3phi", 10.0) == pytest.approx(85.0)


@pytest.mark.parametrize("phi", (12.5, 16.0, 20.0, 22.0, 25.0, 32.0, 40.0))
def test_tabela232_estribo_dmin_3phi_celulas_traco_levantam_erro(phi):
    with pytest.raises(nbr.FaixaNormativaError):
        F.delta_fsd_fad("estribo_dmin_3phi", phi)


@pytest.mark.parametrize("phi", _PHIS)
def test_tabela232_marinho_classe_iv_todas_as_celulas(phi):
    """Ambiente marinho, Classe IV: 110 MPa para todo phi, Tipo T4 (PDF p. 220)."""
    assert F.delta_fsd_fad("marinho_classe_iv", phi) == pytest.approx(110.0)


@pytest.mark.parametrize("phi", _PHIS)
def test_tabela232_soldada_ou_conector_mecanico_todas_as_celulas(phi):
    """Barras soldadas/conectores mecânicos: 85 MPa para todo phi, Tipo T4 (PDF p. 221)."""
    assert F.delta_fsd_fad("soldada_ou_conector_mecanico", phi) == pytest.approx(85.0)


def test_tabela232_armadura_ativa_todos_os_casos():
    """Armadura ativa CP-190RB/CP-210RB (PDF p. 221): phi_mm não usado."""
    assert F.delta_fsd_fad("ativa_pretracao_reta") == pytest.approx(150.0)
    assert F.delta_fsd_fad("ativa_postracao_cabo_bainha_plastica") == pytest.approx(140.0)
    assert F.delta_fsd_fad("ativa_postracao_cabo_bainha_metalica") == pytest.approx(110.0)
    assert F.delta_fsd_fad("ativa_dispositivo_emenda") == pytest.approx(70.0)


def test_tabela232_caso_desconhecido_leva_a_valueerror():
    with pytest.raises(ValueError):
        F.delta_fsd_fad("caso_inexistente", 10.0)


def test_tabela232_phi_fora_da_grade_levanta_erro_faixa():
    """phi=15 mm não está na grade tabelada (sem interpolação, 3.3-7)."""
    with pytest.raises(nbr.FaixaNormativaError):
        F.delta_fsd_fad("barra_reta", 15.0)


def test_tabela232_phi_obrigatorio_para_caso_passivo():
    with pytest.raises(ValueError):
        F.delta_fsd_fad("barra_reta")


# ===========================================================================
# 23.5.5, nota d -- fator redutor do pino de dobramento (PDF p. 221)
# ===========================================================================
def test_notad_xi_em_D_igual_25phi_reproduz_barra_reta():
    """D = 25*phi -> xi = 0,35 + 0,026*25 = 1,0 -- fronteira exata com a barra reta
    (a nota e/consistência da Tabela 23.2: a barra dobrada com D=25*phi tem a
    mesma resistência da barra reta correspondente)."""
    xi = F.fator_redutor_pino_dobramento(25.0 * 10.0, 10.0)
    assert xi == pytest.approx(0.35 + 0.026 * 25.0)
    assert xi == pytest.approx(1.0)


def test_notad_xi_D_8phi_e_D_5phi():
    assert F.fator_redutor_pino_dobramento(8.0 * 10.0, 10.0) == pytest.approx(0.35 + 0.026 * 8.0)
    assert F.fator_redutor_pino_dobramento(5.0 * 10.0, 10.0) == pytest.approx(0.35 + 0.026 * 5.0)


def test_notad_phi_zero_ou_negativo_levanta_erro():
    with pytest.raises(ValueError):
        F.fator_redutor_pino_dobramento(80.0, 0.0)


# ===========================================================================
# 23.5.5 -- Tabela 23.3, tipos da curva S-N (PDF p. 222), todas as células
# ===========================================================================
_TABELA_23_3_ESPERADA = {
    "T1": (1.0e6, 5, 9),
    "T2": (1.0e6, 3, 7),
    "T3": (1.0e6, 3, 5),
    "T4": (1.0e7, 3, 5),
    "T5": (1.0e6, 5, 5),
    "T6": (1.0e6, 5, 7),
    "T7": (1.0e6, 5, 10),
}


@pytest.mark.parametrize("tipo,esperado", list(_TABELA_23_3_ESPERADA.items()))
def test_tabela233_todas_as_linhas(tipo, esperado):
    par = F.TABELA_23_3[tipo]
    assert (par["N_estrela"], par["k1"], par["k2"]) == esperado


# ===========================================================================
# 23.5.5 -- curva S-N (Figura 23.2, PDF p. 222)
# ===========================================================================
@pytest.mark.parametrize("tipo", list(F.TABELA_23_3))
def test_curva_sn_reproduz_valor_tabelado_em_2e6_ciclos(tipo):
    """N = 2x10^6 -> reproduz exatamente Delta_fsd,fad,min (consistência)."""
    assert F.curva_SN(123.0, tipo, 2.0e6) == pytest.approx(123.0)


@pytest.mark.parametrize("tipo", list(F.TABELA_23_3))
def test_curva_sn_continua_em_N_estrela(tipo):
    """N = N* -> os ramos k1 e k2 coincidem no mesmo valor (continuidade)."""
    n_estrela = F.TABELA_23_3[tipo]["N_estrela"]
    valor = F.curva_SN(150.0, tipo, n_estrela)
    # avalia os dois ramos manualmente a partir da mesma constante da âncora
    # e confere que batem exatamente no ponto de transição
    assert valor > 0.0
    # continuidade: um n levemente abaixo e um levemente acima de N* dão
    # valores muito próximos de 'valor' (a função é contínua em N*)
    abaixo = F.curva_SN(150.0, tipo, n_estrela * (1.0 - 1e-9))
    acima = F.curva_SN(150.0, tipo, n_estrela * (1.0 + 1e-9))
    assert abaixo == pytest.approx(valor, rel=1e-6)
    assert acima == pytest.approx(valor, rel=1e-6)


def test_curva_sn_decresce_com_o_numero_de_ciclos():
    """Resistência à fadiga cai com mais ciclos (forma da Figura 23.2)."""
    v_baixo = F.curva_SN(190.0, "T1", 1.0e5)
    v_alto = F.curva_SN(190.0, "T1", 1.0e7)
    assert v_baixo > v_alto


def test_curva_sn_tipo_desconhecido_leva_a_valueerror():
    with pytest.raises(ValueError):
        F.curva_SN(150.0, "T9", 2.0e6)


def test_curva_sn_n_ciclos_nao_positivo_leva_a_valueerror():
    with pytest.raises(ValueError):
        F.curva_SN(150.0, "T1", 0.0)


# ===========================================================================
# 23.5.5, nota e -- teto da barra reta na curva S-N (PDF p. 221-222)
# ===========================================================================
def test_notae_teto_da_barra_reta_ativa_abaixo_do_cruzamento():
    """phi=10: marinho_classe_iv (T4, 110 MPa) x barra_reta (T1, 190 MPa).
    Em N=10 000 ciclos a curva T4 extrapolada (643,3 MPa) supera a da barra
    reta (515,5 MPa) -- o teto da nota e (p. 222: 'em nenhum caso... maior
    que a da barra reta') tem de prevalecer, então o valor usado é o da
    barra reta."""
    n = 10_000.0
    bruto_t4 = F.curva_SN(110.0, "T4", n)
    teto_t1 = F.curva_SN(190.0, "T1", n)
    assert bruto_t4 > teto_t1          # confirma que o teto é mesmo necessário aqui
    usado = F.delta_fsd_fad("marinho_classe_iv", 10.0, n_ciclos=n)
    assert usado == pytest.approx(teto_t1)
    assert usado == pytest.approx(F.delta_fsd_fad("barra_reta", 10.0, n_ciclos=n))


def test_notae_teto_nao_ativa_acima_do_cruzamento():
    """Em N=100 000 ciclos a curva T4 (298,6 MPa) já fica abaixo da barra
    reta (325,2 MPa): o valor usado é o próprio, sem o teto."""
    n = 100_000.0
    bruto_t4 = F.curva_SN(110.0, "T4", n)
    teto_t1 = F.curva_SN(190.0, "T1", n)
    assert bruto_t4 < teto_t1
    usado = F.delta_fsd_fad("marinho_classe_iv", 10.0, n_ciclos=n)
    assert usado == pytest.approx(bruto_t4)


def test_notae_barra_reta_nao_tem_teto_proprio():
    """O próprio caso 'barra_reta' não aplica o teto sobre si mesmo."""
    n = 10_000.0
    direto = F.curva_SN(190.0, "T1", n)
    assert F.delta_fsd_fad("barra_reta", 10.0, n_ciclos=n) == pytest.approx(direto)


# ===========================================================================
# 23.5.5 -- relevo de nervura, r/h < 0,5 (PDF p. 223)
# ===========================================================================
def test_relevo_r_h_abaixo_de_0_5_usa_tabela_direto():
    assert F.fator_relevo(0.4) == 1.0
    assert F.fator_relevo(0.0) == 1.0


def test_relevo_r_h_igual_ou_acima_de_0_5_aplica_reducao_de_30_por_cento():
    assert F.fator_relevo(0.5) == pytest.approx(0.70)
    assert F.fator_relevo(0.6) == pytest.approx(0.70)


# ===========================================================================
# 23.5.5 -- verificar_fadiga_armadura, gama_f x Delta_sigma_Ss <= Delta_fsd,fad
# ===========================================================================
def test_verificacao_fadiga_no_limite_exato_passa():
    """Delta_sigma_Ss = Delta_fsd,fad exato -> caso limite, aprovado."""
    r = F.verificar_fadiga_armadura(190.0, "barra_reta", phi_mm=10.0)
    assert r.delta_fsd_fad_mpa == pytest.approx(190.0)
    assert r.ok is True


def test_verificacao_fadiga_acima_do_limite_reprova():
    r = F.verificar_fadiga_armadura(190.5, "barra_reta", phi_mm=10.0)
    assert r.ok is False


def test_verificacao_fadiga_aplica_reducao_de_relevo():
    """Com r/h=0,6 (sem ensaio), o limite efetivo cai 30%: 190*0,7=133 MPa."""
    r = F.verificar_fadiga_armadura(150.0, "barra_reta", phi_mm=10.0, r_h=0.6)
    assert r.delta_fsd_fad_mpa == pytest.approx(190.0 * 0.70)
    assert r.ok is False   # 150 > 133


def test_verificacao_fadiga_gama_f_diferente_de_1():
    """gama_f=1,2: 1,2*150=180 <= 190 -> ainda ok; 1,2*160=192 > 190 -> reprova."""
    ok = F.verificar_fadiga_armadura(150.0, "barra_reta", phi_mm=10.0, gama_f=1.2)
    reprova = F.verificar_fadiga_armadura(160.0, "barra_reta", phi_mm=10.0, gama_f=1.2)
    assert ok.ok is True
    assert reprova.ok is False


# ===========================================================================
# 23.6 -- Deformação progressiva cíclica (PDF p. 223)
# ===========================================================================
def test_deformacao_progressiva_n_igual_1():
    """n=1 -> fator = 1,5 - 0,5*exp(-0,05) = 1,0244 (conta da própria norma)."""
    fator_esperado = 1.5 - 0.5 * math.exp(-0.05)
    assert fator_esperado == pytest.approx(1.0244, abs=1e-4)
    assert F.deformacao_progressiva(2.0, 1) == pytest.approx(2.0 * fator_esperado)


def test_deformacao_progressiva_cresce_e_tende_a_1_5_a1():
    """Quando n cresce, o fator tende assintoticamente a 1,5 (nunca ultrapassa)."""
    a1 = 3.0
    fator_1 = F.deformacao_progressiva(a1, 1) / a1
    fator_grande = F.deformacao_progressiva(a1, 1.0e10) / a1
    assert fator_1 < fator_grande < 1.5
    assert fator_grande == pytest.approx(1.5, abs=1e-3)


def test_deformacao_progressiva_n_menor_que_1_levanta_erro():
    with pytest.raises(ValueError):
        F.deformacao_progressiva(1.0, 0.5)


# ===========================================================================
# Correção da verificação independente (volta 1) -- acentuação obrigatória
# ===========================================================================
def test_modulo_usa_acentuacao_em_portugues_e_nao_ascii_puro():
    """O módulo fadiga_nbr6118.py (docstrings, comentários e mensagens de
    erro) tem de usar acentuação em português, como o resto do núcleo
    (nucleo_nbr6118.py, seguranca_nbr6118.py) e como pede a convenção 5 do
    BRIEF_IMPLEMENTACAO.md. Antes da correção, o arquivo inteiro era ASCII
    puro (0 caracteres não-ASCII em 573 linhas); este teste falha nesse
    caso e passa quando o texto para o usuário volta a ter acento."""
    caminho = Path(__file__).resolve().parents[1] / "dimensionamento" / "fadiga_nbr6118.py"
    fonte = caminho.read_text(encoding="utf-8")
    nao_ascii = sum(1 for c in fonte if ord(c) > 127)
    assert nao_ascii > 100, (
        f"fadiga_nbr6118.py tem só {nao_ascii} caracteres não-ASCII; "
        "docstrings, comentários e mensagens de erro devem usar acentuação "
        "em português (BRIEF_IMPLEMENTACAO.md, convenção 5)."
    )
    # Mensagens de erro (texto que chega ao engenheiro que usa a biblioteca)
    # precisam de acento, não da forma crua ('nao', 'excecao' etc.).
    with pytest.raises(nbr.FaixaNormativaError) as exc_faixa:
        F.faixa_aplicabilidade(19_999)
    assert "não" in str(exc_faixa.value)
    with pytest.raises(nbr.FaixaNormativaError) as exc_tabela:
        F.delta_fsd_fad("estribo_dmin_5phi", 20.0)
    assert "não" in str(exc_tabela.value)
