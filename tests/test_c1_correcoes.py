"""Testes do C1 -- Correções da conferência final: convenções e duplicação.

Não é um pacote da norma: cobre as correções apontadas pela conferência final
da biblioteca (ver SCRATCH/exec/pacotes/C1.md). Cada bloco de teste corresponde
a um item do C1. O item 5 (pilar-parede, λi = 90) tem os testes ajustados/
acrescentados diretamente em tests/test_p29_pilar_parede.py, onde já morava o
teste que embutia o comportamento errado.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import ancoragem_nbr6118 as anc  # noqa: E402
import blocos_nbr6118 as blo  # noqa: E402
import els_deformacao_nbr6118 as elsd  # noqa: E402
import els_fissuracao_nbr6118 as elsf  # noqa: E402
import lajes_nbr6118 as lj  # noqa: E402
import nucleo_nbr6118 as nbr  # noqa: E402
import protendido_nbr6118 as PT  # noqa: E402
import sapatas_nbr6118 as sap  # noqa: E402
import viga_servico_nbr6118 as vserv  # noqa: E402
import vigas_nbr6118 as vig  # noqa: E402
from rotinas import flexao_composta_obliqua as fco  # noqa: E402


# ---------------------------------------------------------------------------
# C1.1 -- Erro de faixa/positividade com o tipo errado: padronizar para
# FaixaNormativaError (subclasse de ValueError, nada quebra para quem pega
# ValueError). Erro de uso (parâmetro obrigatório faltando, combinação
# incoerente, lista vazia/tamanho errado) continua ValueError -- não é faixa
# normativa.
# ---------------------------------------------------------------------------

# --- els_deformacao_nbr6118.py -----------------------------------------
def test_c1_1_els_deformacao_forma_desconhecida_levanta_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.momento_fissuracao_kncm(Ic_cm4=1.0e5, yt_cm=20.0, fck_mpa=30.0, forma="hexagonal")


def test_c1_1_els_deformacao_resistencia_desconhecida_levanta_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        elsd._fct_kncm2(30.0, "fctk_sup")


def test_c1_1_els_deformacao_geometria_nao_positiva_levanta_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.momento_fissuracao_kncm(Ic_cm4=0.0, yt_cm=20.0, fck_mpa=30.0)
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.rigidez_equivalente_kncm2(Ecs_kncm2=-1.0, Ic_cm4=1.0e5, III_cm4=5.0e4,
                                        Mr_kncm=100.0, Ma_kncm=200.0)
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.rigidez_equivalente_kncm2(Ecs_kncm2=3000.0, Ic_cm4=1.0e5, III_cm4=-1.0,
                                        Mr_kncm=100.0, Ma_kncm=200.0)


def test_c1_1_els_deformacao_rho_linha_negativo_levanta_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.alpha_f(t_meses=70.0, t0_meses=1.0, rho_linha=-0.01)


def test_c1_1_els_deformacao_elemento_e_categoria_desconhecidos_levantam_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.vao_equivalente(elemento="cobertura", l_cm=500.0)
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.deslocamento_limite(categoria="categoria_inexistente", vao_cm=500.0)


def test_c1_1_els_deformacao_rigidez_ponderada_vao_e_ei_nao_positivos_levanta_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.rigidez_equivalente_ponderada_kncm2(
            EI_eq1_kncm2=1.0, EI_eqv_kncm2=1.0, EI_eq2_kncm2=1.0, vao_cm=0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.rigidez_equivalente_ponderada_kncm2(
            EI_eq1_kncm2=0.0, EI_eqv_kncm2=1.0, EI_eq2_kncm2=1.0, vao_cm=500.0)
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.rigidez_equivalente_ponderada_kncm2(
            EI_eq1_kncm2=1.0, EI_eqv_kncm2=1.0, EI_eq2_kncm2=1.0, vao_cm=500.0,
            a1_cm=-1.0)
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.rigidez_equivalente_ponderada_kncm2(
            EI_eq1_kncm2=1.0, EI_eqv_kncm2=1.0, EI_eq2_kncm2=1.0, vao_cm=500.0,
            a1_cm=300.0, a2_cm=300.0)


def test_c1_1_els_deformacao_curvatura_ei_esquema_e_ponto_fora_levantam_faixa():
    xs = [0.0, 250.0, 500.0]
    ms = [0.0, 1000.0, 0.0]
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.flecha_imediata_curvatura_cm(xs, ms, EI_kncm2=0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.flecha_imediata_curvatura_cm(xs, ms, EI_kncm2=1.0e9, esquema="engastada")
    with pytest.raises(nbr.FaixaNormativaError):
        elsd.flecha_imediata_curvatura_cm(xs, ms, EI_kncm2=1.0e9, x_flecha_cm=600.0)


def test_c1_1_els_deformacao_erro_de_uso_continua_valueerror():
    """Combinação incoerente / lista vazia / shape errado: continuam
    ValueError puro (não é faixa normativa)."""
    with pytest.raises(ValueError):
        elsd.t0_ponderado([])  # lista vazia
    with pytest.raises(ValueError):
        elsd.deslocamento_limite(categoria="movimento_lateral_vento", vao_cm=500.0)  # falta H/Hi
    with pytest.raises(ValueError):
        elsd.flecha_imediata_curvatura_cm([0.0, 1.0, 2.0], [0.0, 1.0], EI_kncm2=1.0)  # tamanho errado
    # e não são, por engano, FaixaNormativaError:
    with pytest.raises(ValueError) as exc_info:
        elsd.t0_ponderado([])
    assert not isinstance(exc_info.value, nbr.FaixaNormativaError)


# --- protendido_nbr6118.py ------------------------------------------------
def test_c1_1_protendido_tipo_e_relaxacao_desconhecidos_levantam_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        PT.psi_1000(tipo="cabo_magico", relaxacao="RN", sigma_pi_sobre_fptk=0.7)
    with pytest.raises(nbr.FaixaNormativaError):
        PT.psi_1000(tipo="fio", relaxacao="RX", sigma_pi_sobre_fptk=0.7)
    with pytest.raises(nbr.FaixaNormativaError):
        PT.psi_1000(tipo="fio", relaxacao="RN", sigma_pi_sobre_fptk=2.0)  # fora da Tabela 8.3


def test_c1_1_protendido_n_cabos_e_perfil_desconhecido_levantam_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        PT.perda_encurtamento_cabos_restantes_kncm2(
            n_cabos=0, sigma_cpog_kncm2=1.0, fck_mpa=30.0)
    with pytest.raises(nbr.FaixaNormativaError):
        PT.omega_perfil(perfil="hexagonal", mu=0.2, k_per_m=0.01)


def test_c1_1_protendido_categoria_e_diametro_nao_tabelados_levantam_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        PT.propriedades_cordoalha(diam_mm=12.7, categoria="CP-999")
    with pytest.raises(nbr.FaixaNormativaError):
        PT.propriedades_cordoalha(diam_mm=999.0, categoria="CP-190 RB")
    with pytest.raises(nbr.FaixaNormativaError):
        PT.propriedades_fio(diam_mm=999.0)
    with pytest.raises(nbr.FaixaNormativaError):
        PT.propriedades_fio(diam_mm=6.0, categoria="CP-999")


def test_c1_1_protendido_contato_e_aco_desconhecidos_levantam_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        PT.coeficientes_atrito("contato_inexistente")
    with pytest.raises(nbr.FaixaNormativaError):
        PT.perda_progressiva_aproximada_pct(
            aco="XX", phi_inf=1.0, sigma_c_p0g_mpa=1.0, eps_cs_permil=0.1, fck_mpa=30.0)


def test_c1_1_protendido_excentricidade_fora_do_trecho_levanta_faixa():
    trecho = PT.TrechoCabo(barra=1, L_cm=100.0, e_i_cm=0.0, e_j_cm=0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        trecho.excentricidade_cm(150.0)
    with pytest.raises(nbr.FaixaNormativaError):
        PT.TrechoCabo(barra=1, L_cm=0.0, e_i_cm=0.0, e_j_cm=0.0)


def test_c1_1_protendido_sistema_desconhecido_levanta_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        PT.gama_p_ato_protensao("sistema_inexistente")


def test_c1_1_protendido_tipo_barra_combinacao_e_estado_limite_desconhecidos_levantam_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        PT.limite_compressao_servico_mpa(30.0, combinacao="combinacao_inexistente")
    with pytest.raises(nbr.FaixaNormativaError):
        PT.limite_tracao_servico_mpa(30.0, estado_limite="ELS-X")


def test_c1_1_protendido_estado_desconhecido_e_geometria_nao_positiva_levantam_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        PT.verificar_descompressao_fissuracao(
            P_kn=0.0, ep_cm=0.0, M_kncm=0.0, Ac_cm2=1000.0, Wb_cm3=1.0e4,
            Wt_cm3=1.0e4, estado="ELS-X")
    with pytest.raises(nbr.FaixaNormativaError):
        PT.rho_p_armadura_ativa(Ap_cm2=5.0, bc_cm=0.0, dp_cm=50.0)
    with pytest.raises(nbr.FaixaNormativaError):
        PT.delta_sigma_p_nao_aderente(fck_mpa=30.0, rho_p=0.0, vao_dp=30.0)
    with pytest.raises(nbr.FaixaNormativaError):
        PT.delta_sigma_p_nao_aderente(fck_mpa=30.0, rho_p=0.01, vao_dp=30.0, gama_s=0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        PT.momento_fissuracao_protendido_kncm(
            Mr_sem_protensao_kncm=1000.0, P_kn=500.0, ep_cm=20.0, Ac_cm2=0.0, W_cm3=1.0)
    with pytest.raises(nbr.FaixaNormativaError):
        PT.flecha_total_protendido(f_imediata_permanente_cm=1.0, phi=-0.1)


def test_c1_1_protendido_esquema_desconhecido_levanta_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        PT.verificar_flecha_protendido(
            x_cm=[0.0, 100.0], M_permanente_kncm=[0.0, 0.0], M_variavel_kncm=None,
            Ecs_kncm2=3000.0, Ic_cm4=1.0e5, III_cm4=5.0e4,
            Mr_sem_protensao_kncm=100.0, P_kn=0.0, ep_cm=0.0, Ac_cm2=100.0,
            W_cm3=100.0, phi=1.0, categoria="alvenaria", esquema="esquema_invalido",
        )


def test_c1_1_protendido_erro_de_uso_continua_valueerror():
    """Combinação/lista incoerente: continua ValueError puro."""
    with pytest.raises(ValueError):
        PT._forcas_por_trecho_p47(2, (100.0,))  # tamanho errado
    with pytest.raises(ValueError):
        PT.propriedades_fio(diam_mm=6.0)  # ambíguo (2 categorias), sem informar qual
    with pytest.raises(ValueError):
        PT.PerfilCabo(trechos=())  # lista vazia
    with pytest.raises(ValueError) as exc_info:
        PT.PerfilCabo(trechos=())
    assert not isinstance(exc_info.value, nbr.FaixaNormativaError)


# --- els_fissuracao_nbr6118.py --------------------------------------------
def test_c1_1_els_fissuracao_estadio_desconhecido_levanta_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        elsf.tensoes_servico(None, None, None, N_kn=0.0, Mx_kncm=0.0, estadio="III")


def test_c1_1_els_fissuracao_sigma_nao_positiva_levanta_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        elsf.controle_fissuracao_sem_wk(sigma_si_mpa=-10.0)
    with pytest.raises(nbr.FaixaNormativaError):
        elsf.As_min_deformacao_imposta(k=0.5, kc=1.0, fctef_mpa=2.0, Act_cm2=500.0, sigma_s_mpa=0.0)


def test_c1_1_els_fissuracao_geometria_nao_positiva_levanta_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        elsf.verificar_descompressao_laje(
            P_kn=100.0, ep_cm=5.0, M_kncm=1000.0, b_cm=0.0, h_cm=20.0, estado="ELS-D")


def test_c1_1_els_fissuracao_caso_kc_desconhecido_levanta_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        elsf.kc_deformacao_imposta(caso="caso_qualquer")


def test_c1_1_els_fissuracao_altura_zona_tracionada_negativa_levanta_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        elsf.kc_deformacao_imposta(caso="interpolado", altura_zona_tracionada_cm=-1.0, h_cm=50.0)


# ---------------------------------------------------------------------------
# C1.2 -- viga_servico_nbr6118: Eci_mpa/Ecs_mpa/alpha_e delegam ao núcleo
# (nucleo_nbr6118.Eci/Ecs/alpha_i/alpha_E) em vez de repetir a fórmula de
# 8.2.8 com as constantes escritas à mão.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck", [20.0, 25.0, 30.0, 40.0, 50.0, 60.0, 70.0, 90.0])
def test_c1_2_Eci_Ecs_delegam_ao_nucleo(fck):
    assert vserv.Eci_mpa(fck) == pytest.approx(nbr.Eci(fck, nbr.alpha_E("granito")))
    assert vserv.Ecs_mpa(fck) == pytest.approx(nbr.Ecs(fck, nbr.alpha_E("granito")))
    assert vserv.Eci_mpa(fck, "basalto") == pytest.approx(nbr.Eci(fck, nbr.alpha_E("basalto")))
    assert vserv.Ecs_mpa(fck, "calcario") == pytest.approx(nbr.Ecs(fck, nbr.alpha_E("calcario")))


@pytest.mark.parametrize("fck", [20.0, 30.0, 50.0, 70.0])
def test_c1_2_alpha_e_continua_es_sobre_ecs(fck):
    esperado = vserv.E_S_MPA / nbr.Ecs(fck, nbr.alpha_E("granito"))
    assert vserv.alpha_e(fck, "granito") == pytest.approx(esperado)


def test_c1_2_valores_batem_com_a_formula_antiga_c20_a_c90():
    """Conferido de C20 a C90 (mesma faixa citada no achado): o número não
    muda, só a implementação -- fórmula antiga escrita à mão comparada com a
    delegação nova."""
    for fck in (20.0, 30.0, 40.0, 50.0, 55.0, 70.0, 90.0):
        if fck <= 50.0:
            eci_antigo = 5600.0 * math.sqrt(fck)  # alpha_E=1,0 (granito)
        else:
            eci_antigo = 21500.0 * (fck / 10.0 + 1.25) ** (1.0 / 3.0)
        alpha_i_antigo = min(1.0, 0.8 + 0.2 * fck / 80.0)
        ecs_antigo = alpha_i_antigo * eci_antigo
        assert vserv.Eci_mpa(fck) == pytest.approx(eci_antigo, rel=1e-12)
        assert vserv.Ecs_mpa(fck) == pytest.approx(ecs_antigo, rel=1e-12)


def test_c1_2_agregado_desconhecido_agora_levanta():
    """Mudança de comportamento aceita (mesmo padrão já usado em
    protendido_nbr6118.Eci_mpa, achado PRO-01): delegar ao núcleo troca o
    fallback silencioso (alpha_E=1,0) por erro explícito."""
    with pytest.raises(ValueError):
        vserv.Eci_mpa(30.0, "agregado-inexistente")
    with pytest.raises(ValueError):
        vserv.Ecs_mpa(30.0, "agregado-inexistente")


def test_c1_2_alpha_E_local_nao_foi_tocado():
    """A função local alpha_E (lookup direto, fora do escopo do achado) segue
    permissiva com agregado desconhecido -- ainda usada por
    els_fissuracao_nbr6118 (vserv.alpha_E)."""
    assert vserv.alpha_E("agregado-inexistente") == 1.0


# ---------------------------------------------------------------------------
# C1.3 -- GAMA_C e GAMA_S lidos do núcleo (nucleo_nbr6118.GAMA_C/GAMA_S), não
# mais literais redeclarados.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("modulo", [vig, lj, anc, vserv, sap, blo, PT])
def test_c1_3_gama_c_e_gama_s_vem_do_nucleo(modulo):
    assert modulo.GAMA_C == nbr.GAMA_C
    assert modulo.GAMA_S == nbr.GAMA_S
    assert modulo.GAMA_C == pytest.approx(1.4)
    assert modulo.GAMA_S == pytest.approx(1.15)


# ---------------------------------------------------------------------------
# C1.4 -- lajes_nbr6118.fyd_kncm2 delega a nucleo_nbr6118.fyd em vez de
# calcular fyk/gama_s*0,1 à mão.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fyk,gama_s", [(500.0, 1.15), (600.0, 1.15), (500.0, 1.0)])
def test_c1_4_fyd_kncm2_delega_ao_nucleo(fyk, gama_s):
    esperado = nbr.mpa_para_kncm2(nbr.fyd(fyk, gama_s))
    assert lj.fyd_kncm2(fyk, gama_s) == pytest.approx(esperado)


def test_c1_4_fyd_kncm2_valor_da_norma_fyk_500():
    # fyd = 500/1,15 = 434,7826... MPa = 43,47826... kN/cm2
    assert lj.fyd_kncm2(500.0) == pytest.approx(43.47826, abs=1e-4)


# ---------------------------------------------------------------------------
# C1.6 -- achado rejeitado: o pico do diagrama CURVO parábola-retângulo
# (ALPHA_C) continua fixo em 0,85, não vira nbr.alpha_c(fck) (que é reduzido
# acima de C50 e vale só para o retângulo equivalente, 17.2.2 e), PDF p. 141).
# Teste de regressão para não ser "corrigido" de novo no futuro.
# ---------------------------------------------------------------------------
def test_c1_6_alpha_c_da_parabola_continua_fixo_em_085():
    assert fco.ALPHA_C == pytest.approx(0.85)


def test_c1_6_alpha_c_reduzido_do_nucleo_nao_se_aplica_ao_pico_da_parabola():
    # nbr.alpha_c(fck) reduz acima de C50 (17.2.2 e) -- vale só para o
    # retangulo equivalente, nao para o pico do diagrama curvo.
    assert nbr.alpha_c(70.0) < 0.85
    curva = fco.CurvaCParabolaRetangulo(
        fcd_kncm2=3.0, eps_c2_pmilh=2.0, eps_cu_pmilh=2.6, n_parabola=1.4, eta_c=0.855)
    assert curva.alpha_c == pytest.approx(0.85)
