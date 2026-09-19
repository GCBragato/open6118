"""Testes do P14 — Pré e pós-processamento da análise linear.

Cobre dimensionamento/analise_linear_nbr6118.py contra a ABNT NBR 6118:2026:

  - 14.3.3   Carregamento monotônico, p. 104
  - 14.6.2.1 Trechos rígidos, Figura 14.1, p. 108-109
  - 14.6.2.2 Largura colaborante T/L, Figura 14.2, p. 109-110
  - 14.6.2.2 Largura efetiva com abertura, Figura 14.3, p. 109
  - 14.6.2.3 Mísulas e variações bruscas de seção, Figura 14.4, p. 109-110
  - 14.6.2.4 Vão efetivo, Figura 14.5, p. 110
  - 14.6.3   Arredondamento do diagrama de momentos, Figura 14.6, p. 111
  - 14.6.6.1 Momento mínimo em viga contínua e coeficientes de
    engastamento perfeito, Figura 14.8, p. 113-114
  - 14.6.6.2 Redução da rigidez à torção em grelha, p. 115
  - 14.6.6.3 Dispensa de alternância de cargas, p. 115
  - 14.6.6.4 Diafragma rígido, p. 115

Os valores esperados vêm da imagem de cada página (SCRATCH\\nbr_png\\pNNN.png),
não do JSON do plano.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import analise_linear_nbr6118 as al        # noqa: E402
import lajes_nbr6118 as laj                # noqa: E402
import nucleo_nbr6118 as nbr               # noqa: E402
import viga_servico_nbr6118 as vserv       # noqa: E402


def _aprox(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


def test_modulo_tem_mensagens_ao_usuario_acentuadas():
    """Checagem mecanica (convencao 3.3.5 do plano / regra global do
    Gustavo): o modulo do P14 precisa ter acentuacao real em texto para o
    usuario (docstrings, comentarios, mensagens de erro, memoria de
    calculo). Antes da correcao deste pacote, o arquivo inteiro (696 linhas)
    era ASCII puro - esta contagem batia em 0."""
    import analise_linear_nbr6118 as modulo

    fonte = Path(modulo.__file__).read_text(encoding="utf-8")
    acentos = "áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ"
    n_acentos = sum(fonte.count(c) for c in acentos)
    assert n_acentos > 100, (
        f"modulo com apenas {n_acentos} caracteres acentuados; "
        "texto ao usuario deve estar em portugues acentuado."
    )


# =============================================================================
# 14.3.3 — Carregamento monotonico (p. 104)
# =============================================================================
def test_admite_carregamento_monotonico_limite_inclusivo():
    """sigma_c,serv = 0,5*fck deve passar (limite inclusivo); 0,501*fck reprova."""
    fck = 30.0
    assert al.admite_carregamento_monotonico(0.5 * fck, fck) is True
    assert al.admite_carregamento_monotonico(0.501 * fck, fck) is False


def test_admite_carregamento_monotonico_fck_invalido():
    with pytest.raises(nbr.FaixaNormativaError):
        al.admite_carregamento_monotonico(5.0, 10.0)  # fck < 20 MPa


# =============================================================================
# 14.6.2.1 — Trechos rigidos, Figura 14.1 (p. 108-109)
# =============================================================================
def test_trecho_rigido_h60():
    """h=60 cm -> trecho rígido de 0,3*60=18 cm para cada lado (Figura 14.1)."""
    assert _aprox(al.trecho_rigido_cm(60.0), 18.0)


def test_trecho_rigido_invalido():
    with pytest.raises(nbr.FaixaNormativaError):
        al.trecho_rigido_cm(0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        al.trecho_rigido_cm(-10.0)


def test_trecho_rigido_mensagem_de_erro_tem_acentuacao():
    """Mensagem ao usuario em portugues acentuado (convencao 3.3.5 do plano):
    'nao' e 'valida' sem acento e regressao, nao mensagem correta."""
    with pytest.raises(nbr.FaixaNormativaError, match="não é uma altura válida"):
        al.trecho_rigido_cm(-10.0)


# =============================================================================
# 14.6.2.2 — Largura colaborante T/L, Figura 14.2 (p. 109-110)
# =============================================================================
def test_largura_colaborante_governado_por_meio_b2():
    """b2_esq=100, b2_dir=100, a=2000 (grande): 0,5*b2=50 < 0,1*a=200 -> b1=b3=50.
    bf = bw + 50 + 50."""
    bf = al.largura_colaborante_cm(20.0, 100.0, 100.0, 2000.0)
    assert _aprox(bf, 20.0 + 50.0 + 50.0)


def test_largura_colaborante_governado_por_01a():
    """b2_esq=b2_dir=1000 (grande), a=500: 0,1*a=50 < 0,5*b2=500 -> b1=b3=50."""
    bf = al.largura_colaborante_cm(20.0, 1000.0, 1000.0, 500.0)
    assert _aprox(bf, 20.0 + 50.0 + 50.0)


def test_largura_colaborante_no_limite_b1_igual_b2_metade():
    """b1 = 0,5*b2 no limite exato (b1 = 0,1*a também, ambos iguais = fronteira)."""
    # 0,5*b2 = 0,1*a -> b2 = 0,2*a. a=300 -> b2=60 -> b1=30.
    bf = al.largura_colaborante_cm(20.0, 60.0, 60.0, 300.0)
    assert _aprox(bf, 20.0 + 30.0 + 30.0)


def test_largura_colaborante_caso_de_borda_com_b4():
    """Figura 14.2, caso de borda: b3 <= b4 (em vez de 0,5*b2_dir).
    bw=20, b2_esq=200 (a=1000 -> b1=min(100,100)=100), borda com b4=15
    (< 0,1*a=100) -> b3=15. bf = 20+100+15=135."""
    bf = al.largura_colaborante_cm(
        20.0, 200.0, 0.0, 1000.0, borda=True, b4_cm=15.0,
    )
    assert _aprox(bf, 20.0 + 100.0 + 15.0)


def test_largura_colaborante_borda_governado_por_01a():
    """Caso de borda com b4 grande: b3 limitado por 0,1*a, não por b4."""
    bf = al.largura_colaborante_cm(
        20.0, 200.0, 0.0, 1000.0, borda=True, b4_cm=1000.0,
    )
    # b1 = min(100,100) = 100; b3 = min(1000, 100) = 100
    assert _aprox(bf, 20.0 + 100.0 + 100.0)


def test_largura_colaborante_borda_sem_b4_levanta_erro():
    with pytest.raises(ValueError):
        al.largura_colaborante_cm(20.0, 200.0, 0.0, 1000.0, borda=True)


def test_largura_colaborante_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        al.largura_colaborante_cm(20.0, 100.0, 100.0, 0.0)  # a_cm <= 0
    with pytest.raises(nbr.FaixaNormativaError):
        al.largura_colaborante_cm(20.0, -1.0, 100.0, 500.0)  # b2_esq < 0
    with pytest.raises(nbr.FaixaNormativaError):
        al.largura_colaborante_cm(20.0, 100.0, -1.0, 500.0)  # b2_dir < 0
    with pytest.raises(nbr.FaixaNormativaError):
        al.largura_colaborante_cm(20.0, 100.0, 0.0, 500.0, borda=True, b4_cm=-1.0)


def test_largura_colaborante_mensagens_de_erro_tem_acentuacao():
    """Mensagem ao usuario em portugues acentuado (convencao 3.3.5 do plano)."""
    with pytest.raises(nbr.FaixaNormativaError, match="não é uma distância válida"):
        al.largura_colaborante_cm(20.0, 100.0, 100.0, 0.0)
    with pytest.raises(ValueError, match="é obrigatório"):
        al.largura_colaborante_cm(20.0, 200.0, 0.0, 1000.0, borda=True)


def test_largura_efetiva_mesa_T_biapoiada_reproduz_comportamento_anterior():
    """Mesmo caso que já existia em viga_servico_nbr6118 antes do P14: viga T
    biapoiada L=500 cm, bw=20 cm, b2_l_esq=b2_l_dir=300 cm.
    a = 500; b1 = b3 = min(0.5*300, 0.10*500) = min(150, 50) = 50.
    bf = 50 + 20 + 50 = 120 cm."""
    r = al.largura_efetiva_mesa(
        bw_cm=20.0, b2_l_esq_cm=300.0, b2_l_dir_cm=300.0,
        L_cm=500.0, tipo_vao="biapoiada", tipo_secao="T",
    )
    assert _aprox(r["a_cm"], 500.0)
    assert _aprox(r["b1_cm"], 50.0)
    assert _aprox(r["b3_cm"], 50.0)
    assert _aprox(r["bf_cm"], 120.0)


def test_largura_efetiva_mesa_L_continua_reproduz_comportamento_anterior():
    """Viga L (extremidade), L=600, bw=20, b2_l=80 (só um lado).
    a=0.75*600=450. b1=min(0.5*80,0.10*450)=min(40,45)=40. bf=40+20=60."""
    r = al.largura_efetiva_mesa(
        bw_cm=20.0, b2_l_esq_cm=80.0, b2_l_dir_cm=0.0,
        L_cm=600.0, tipo_vao="continua-extrema", tipo_secao="L",
    )
    assert _aprox(r["a_cm"], 450.0)
    assert _aprox(r["b1_cm"], 40.0)
    assert _aprox(r["b3_cm"], 0.0)
    assert _aprox(r["bf_cm"], 60.0)


def test_largura_efetiva_mesa_facade_em_viga_servico():
    """viga_servico_nbr6118.largura_efetiva_mesa é uma reexportação direta
    (viga_servico_nbr6118.largura_efetiva_mesa = _analise_linear.largura_
    efetiva_mesa) - este teste verifica apenas o roteamento do alias (que
    quem chama pelo módulo antigo chega na mesma função), não a fórmula em
    si: sendo o mesmo objeto de função, os dois lados não podem divergir
    silenciosamente. A fórmula em si é coberta pelos testes de
    largura_colaborante_cm e dos demais casos de largura_efetiva_mesa acima."""
    r1 = vserv.largura_efetiva_mesa(20.0, 300.0, 300.0, 500.0, "biapoiada", "T")
    r2 = al.largura_efetiva_mesa(20.0, 300.0, 300.0, 500.0, "biapoiada", "T")
    assert r1 == r2
    assert vserv.largura_efetiva_mesa is al.largura_efetiva_mesa


def test_largura_efetiva_com_abertura():
    """bef <= bf sempre (14.6.2.2, Figura 14.3)."""
    assert _aprox(al.largura_efetiva_com_abertura(120.0, 80.0), 80.0)
    assert _aprox(al.largura_efetiva_com_abertura(120.0, 150.0), 120.0)  # clip em bf
    assert _aprox(al.largura_efetiva_com_abertura(120.0, 120.0), 120.0)


def test_largura_efetiva_com_abertura_invalida():
    with pytest.raises(nbr.FaixaNormativaError):
        al.largura_efetiva_com_abertura(0.0, 10.0)
    with pytest.raises(nbr.FaixaNormativaError):
        al.largura_efetiva_com_abertura(120.0, -1.0)


# =============================================================================
# 14.6.2.3 — Mísulas e variações bruscas de seção, Figura 14.4 (p. 109-110)
# =============================================================================
def test_secao_efetiva_misula_usa_o_menor():
    assert _aprox(al.secao_efetiva_misula(30.0, 50.0), 30.0)
    assert _aprox(al.secao_efetiva_misula(40.0, 40.0), 40.0)  # sem variação


def test_secao_efetiva_misula_invalida():
    with pytest.raises(nbr.FaixaNormativaError):
        al.secao_efetiva_misula(0.0, 50.0)
    with pytest.raises(ValueError):
        al.secao_efetiva_misula(50.0, 30.0)  # ordem trocada


# =============================================================================
# 14.6.2.4 — Vão efetivo, Figura 14.5 (p. 110)
# =============================================================================
def test_vao_efetivo_apostila_580_20_20_10():
    """l0=580, t1=t2=20, h=10 -> a1=a2=min(10,3)=3 -> l_ef=586."""
    assert _aprox(al.vao_efetivo(580.0, 20.0, 20.0, 10.0), 586.0)


def test_vao_efetivo_governado_pela_metade_do_apoio():
    """t1/2 < 0,3h -> a1 = t1/2. l0=400, t1=10 (a1=5), t2=200 (a2=min(100,30)=30), h=100.
    l_ef = 400+5+30=435."""
    assert _aprox(al.vao_efetivo(400.0, 10.0, 200.0, 100.0), 435.0)


def test_vao_efetivo_facade_em_lajes():
    assert _aprox(laj.vao_efetivo(580.0, 20.0, 20.0, 10.0), 586.0)


# =============================================================================
# 14.6.3 — Arredondamento do diagrama de momentos, Figura 14.6 (p. 111)
# =============================================================================
def test_arredondamento_caso_geral_reacoes_distintas():
    """M=1000 kN.cm, R1=50 kN, R2=70 kN, t=40 cm (Figura 14.6):
    DeltaM1 = 50*40/4 = 500; DeltaM2 = 70*40/4 = 700;
    DeltaM = (70-50)/4*40 = 200."""
    r = al.arredondar_momento_apoio(1000.0, 50.0, 70.0, 40.0)
    assert _aprox(r.delta_M1_kncm, 500.0)
    assert _aprox(r.delta_M2_kncm, 700.0)
    assert _aprox(r.delta_M_kncm, 200.0)
    assert _aprox(r.M_esquerda_kncm, 1000.0 - 500.0)
    assert _aprox(r.M_direita_kncm, 1000.0 - 700.0)
    assert _aprox(r.M_arredondado_kncm, 1000.0 - 200.0)


def test_arredondamento_caso_simetrico_R1_igual_R2():
    """Caso simétrico R1=R2=R=60 kN, t=30 cm (Figura 14.6):
    DeltaM1=DeltaM2=R*t/4=450; DeltaM (fórmula geral) = 0;
    redução no eixo do apoio usa DeltaM'=R*t/8=225, não 0."""
    r = al.arredondar_momento_apoio(2000.0, 60.0, 60.0, 30.0)
    assert _aprox(r.delta_M1_kncm, 450.0)
    assert _aprox(r.delta_M2_kncm, 450.0)
    assert _aprox(r.delta_M_kncm, 0.0)
    assert _aprox(r.M_arredondado_kncm, 2000.0 - 225.0)


def test_arredondamento_preserva_sinal_negativo():
    """M negativo (momento de apoio, hogging): a redução alivia o módulo."""
    r = al.arredondar_momento_apoio(-1000.0, 50.0, 70.0, 40.0)
    assert _aprox(r.M_arredondado_kncm, -1000.0 + 200.0)


def test_arredondamento_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        al.arredondar_momento_apoio(1000.0, 50.0, 70.0, -1.0)
    with pytest.raises(nbr.FaixaNormativaError):
        al.arredondar_momento_apoio(1000.0, -1.0, 70.0, 40.0)


# =============================================================================
# 14.6.6.1 — Momento mínimo em viga contínua, item a) e b) (p. 113)
# =============================================================================
def test_momento_minimo_positivo_engastamento_perfeito():
    """Viga biengastada de referência: p=10 kN/cm, l=1000 cm ->
    M_eng_vao = p*l^2/24, M_eng_apoio = p*l^2/12 (biengastada com carga
    uniforme). Modelo simplificado (viga isolada apoiada) dá M+ = p*l^2/8,
    que já é maior que p*l^2/24 -> M+ final = M+ isolado (não muda)."""
    p, l = 10.0, 1000.0
    M_pos_isolada = p * l ** 2 / 8.0
    M_pos_engastamento = p * l ** 2 / 24.0
    r = al.momentos_minimos_viga_continua(M_pos_isolada, M_pos_engastamento)
    assert _aprox(r.M_positivo_final_kncm, M_pos_isolada)


def test_momento_minimo_positivo_e_elevado_quando_menor_que_engastamento():
    """Quando o M+ do modelo simplificado vem menor que o de engastamento
    perfeito, a norma proíbe adotá-lo: M+ final = M+ engastamento."""
    r = al.momentos_minimos_viga_continua(
        M_positivo_kncm=300.0, M_positivo_engastamento_kncm=500.0,
    )
    assert _aprox(r.M_positivo_final_kncm, 500.0)


def test_momento_minimo_negativo_aplica_quando_apoio_largo():
    """Apoio (40 cm) > h_pilar/4 (30 cm, h_pilar=120) -> |M-| final =
    max(|M- adotado|, |M- engastamento|)."""
    r = al.momentos_minimos_viga_continua(
        M_positivo_kncm=500.0, M_positivo_engastamento_kncm=400.0,
        M_negativo_kncm=-600.0, M_negativo_engastamento_kncm=-800.0,
        largura_apoio_cm=40.0, altura_pilar_cm=120.0,
    )
    assert r.aplica_minimo_negativo is True
    assert _aprox(r.M_negativo_final_kncm, -800.0)


def test_momento_minimo_negativo_nao_aplica_quando_apoio_estreito():
    """Apoio (20 cm) <= h_pilar/4 (30 cm, h_pilar=120) -> não mexe no M-
    adotado, mesmo que seja menor em módulo que o de engastamento."""
    r = al.momentos_minimos_viga_continua(
        M_positivo_kncm=500.0, M_positivo_engastamento_kncm=400.0,
        M_negativo_kncm=-600.0, M_negativo_engastamento_kncm=-800.0,
        largura_apoio_cm=20.0, altura_pilar_cm=120.0,
    )
    assert r.aplica_minimo_negativo is False
    assert _aprox(r.M_negativo_final_kncm, -600.0)


def test_momento_minimo_negativo_no_limite_exato_nao_aplica():
    """largura_apoio == h_pilar/4 exatamente: não é "maior que", então não
    aplica (limite exato do lado que não aplica, 14.6.6.1 b)."""
    r = al.momentos_minimos_viga_continua(
        M_positivo_kncm=500.0, M_positivo_engastamento_kncm=400.0,
        M_negativo_kncm=-600.0, M_negativo_engastamento_kncm=-800.0,
        largura_apoio_cm=30.0, altura_pilar_cm=120.0,
    )
    assert r.aplica_minimo_negativo is False


# =============================================================================
# 14.6.6.1 — Coeficientes de engastamento perfeito, Figura 14.8 (p. 113-114)
# =============================================================================
def test_coeficientes_engastamento_soma_viga_igual_soma_pilares():
    """Por equilíbrio, coef_viga = coef_sup + coef_inf sempre."""
    r = al.coeficientes_engastamento_extremo(r_inf=2.0, r_sup=3.0, r_viga=5.0)
    assert _aprox(r.coef_viga, r.coef_sup + r.coef_inf)
    soma = 2.0 + 3.0 + 5.0
    assert _aprox(r.coef_viga, (2.0 + 3.0) / soma)
    assert _aprox(r.coef_sup, 3.0 / soma)
    assert _aprox(r.coef_inf, 2.0 / soma)


def test_coeficientes_engastamento_pilares_muito_mais_rigidos_tende_a_engastamento_perfeito():
    """Pilares (r_inf=r_sup=R) muito mais rígidos que a viga: coef_viga ->
    1,0 (tendência ao engastamento perfeito na viga); os dois coeficientes
    de pilar tendem, cada um, a 0,5 (dividem entre si quase todo o momento,
    já que coef_sup+coef_inf=coef_viga->1)."""
    r = al.coeficientes_engastamento_extremo(r_inf=1.0e6, r_sup=1.0e6, r_viga=1.0)
    assert r.coef_viga > 0.9999
    assert _aprox(r.coef_sup, 0.5, 1e-3)
    assert _aprox(r.coef_inf, 0.5, 1e-3)


def test_coeficientes_engastamento_viga_muito_mais_rigida_tende_a_zero():
    """Viga muito mais rígida que os pilares: coef_viga -> 0 (o apoio se
    comporta como articulado para a viga, quase não há engastamento)."""
    r = al.coeficientes_engastamento_extremo(r_inf=1.0, r_sup=1.0, r_viga=1.0e6)
    assert r.coef_viga < 1e-3


def test_coeficientes_engastamento_invalidos():
    with pytest.raises(nbr.FaixaNormativaError):
        al.coeficientes_engastamento_extremo(-1.0, 1.0, 1.0)
    with pytest.raises(nbr.FaixaNormativaError):
        al.coeficientes_engastamento_extremo(0.0, 0.0, 0.0)


# =============================================================================
# 14.6.6.2 — Redução da rigidez à torção em grelha (p. 115)
# =============================================================================
def test_fator_rigidez_torcao_grelha_e_015():
    assert al.FATOR_RIGIDEZ_TORCAO_GRELHA == 0.15


def test_rigidez_torcao_reduzida_concreto_armado():
    assert _aprox(al.rigidez_torcao_reduzida(1000.0), 150.0)


@pytest.mark.parametrize("classe", [2, 3])
def test_rigidez_torcao_reduzida_nao_se_aplica_a_protensao_limitada_completa(classe):
    """Classes 2 e 3 (protensão limitada/completa) mantêm GJ elástico."""
    assert _aprox(al.rigidez_torcao_reduzida(1000.0, classe_protensao=classe), 1000.0)


def test_rigidez_torcao_reduzida_classe_1_reduz_normalmente():
    assert _aprox(al.rigidez_torcao_reduzida(1000.0, classe_protensao=1), 150.0)


def test_rigidez_torcao_elu_desprezada():
    assert al.rigidez_torcao_reduzida(1000.0, desprezar_para_elu=True) == 0.0
    # desprezar_para_elu tem prioridade mesmo com classe 2/3:
    assert al.rigidez_torcao_reduzida(
        1000.0, classe_protensao=3, desprezar_para_elu=True,
    ) == 0.0


def test_rigidez_torcao_reduzida_negativa_invalida():
    with pytest.raises(nbr.FaixaNormativaError):
        al.rigidez_torcao_reduzida(-1.0)


# =============================================================================
# 14.6.6.3 — Dispensa de alternância de cargas (p. 115)
# =============================================================================
def test_dispensa_alternancia_limite_5_kn_m2_inclusivo():
    """q=5 kN/m2 exatos, com g suficiente para não violar os 50%, deve passar."""
    assert al.dispensa_alternancia_cargas(q_kn_m2=5.0, g_kn_m2=5.0) is True  # q=50% de 10
    assert al.dispensa_alternancia_cargas(q_kn_m2=5.01, g_kn_m2=100.0) is False


def test_dispensa_alternancia_limite_50_por_cento_inclusivo():
    """q = 50% exatos da carga total deve passar; 50,1% deve reprovar."""
    # q=4, g=4 -> total=8, q/total=50% exato.
    assert al.dispensa_alternancia_cargas(q_kn_m2=4.0, g_kn_m2=4.0) is True
    # q=4, g=3.984 -> total=7.984, q/total=50,1%.
    assert al.dispensa_alternancia_cargas(q_kn_m2=4.0, g_kn_m2=3.984) is False


def test_dispensa_alternancia_reprova_por_qualquer_um_dos_dois_criterios():
    """Cada critério reprova sozinho, mesmo que o outro passe."""
    # q=6 > 5 kN/m2, mas q/total = 6/26 = 23% (<=50%): reprova por causa do
    # primeiro critério isolado.
    assert al.dispensa_alternancia_cargas(q_kn_m2=6.0, g_kn_m2=20.0) is False
    # q=4 <= 5 kN/m2, mas g=0 -> q/total = 100% (>50%): reprova por causa do
    # segundo critério isolado.
    assert al.dispensa_alternancia_cargas(q_kn_m2=4.0, g_kn_m2=0.0) is False


def test_dispensa_alternancia_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        al.dispensa_alternancia_cargas(-1.0, 5.0)


# =============================================================================
# 14.6.6.4 — Diafragma rígido (p. 115)
# =============================================================================
def test_diafragma_rigido_no_limite_3_inclusivo():
    assert al.laje_diafragma_rigido(300.0, 100.0) is True   # razao = 3,0 exata
    assert al.laje_diafragma_rigido(300.01, 100.0) is False  # razao > 3,0


def test_diafragma_rigido_com_abertura_grande_sempre_falso():
    assert al.laje_diafragma_rigido(150.0, 100.0, tem_abertura_grande=True) is False


def test_diafragma_rigido_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        al.laje_diafragma_rigido(100.0, 0.0)
    with pytest.raises(ValueError):
        al.laje_diafragma_rigido(50.0, 100.0)  # lado_maior < lado_menor
