"""
NBR 6118:2026, pg 32 - Seção 9 Comportamento conjunto dos materiais

Legado: mantido por compatibilidade e corrigido contra a NBR 6118:2026
(auditoria de 18/09/2026, achados ANC-01 a ANC-08); para projetos novos,
use dimensionamento/ancoragem_nbr6118.py.

Métodos disponíveis:
res_ade_pass(),
res_ade_ati(),
diam_pino_dobramento(),
comp_ancor_basico(),
comp_ancor_necessario(),
comp_ancor_basico_ativo(),
comp_transferencia(),
comp_ancor_necessario_ativo(),
diam_pino_dobramento_transversal(),
comp_transpasse_trac(),
comp_transpasse_comp()
"""

import os
import sys
import warnings

# Núcleo normativo único (nucleo_nbr6118.py mora em dimensionamento/, um
# nível acima de secoes_norma/): usa eta1/eta2/eta3/fctd em vez de repetir
# as fórmulas de material aqui.
_DIMENSIONAMENTO_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'dimensionamento'
)
if _DIMENSIONAMENTO_DIR not in sys.path:
    sys.path.insert(0, _DIMENSIONAMENTO_DIR)

import nucleo_nbr6118 as nbr
import ancoragem_nbr6118 as anc  # P31: fachada da ancoragem de armadura ativa

from sec8 import Concreto, Aco_Passivo


def main():
    C25 = Concreto(25)
    CA50 = Aco_Passivo('CA50')
    fbd = res_ade_pass('nervurada','boa',16,C25.fctd)
    fbpd = res_ade_ati('cordoalha','boa',C25.fctd)
    D = diam_pino_dobramento(16,'CA50')
    lb = comp_ancor_basico(16, CA50.fyd, fbd)
    lb_nec = comp_ancor_necessario(1.0, lb, 10, 10, 16)


"""
Seção 9.3 Verificação da aderência, pg 34.
"""


_CATEGORIA_POR_TIPO_BARRA = {'lisa': 'CA-25', 'entalhada': 'CA-60', 'nervurada': 'CA-50'}


def _boa_aderencia(qual_ader):
    """Converte 'boa' ou 'má'/'ma' em booleano (True = boa aderência).

    Aceita 'má' (grafia da norma, 9.3.2.1) e 'ma' (sem acento) para má
    aderência (ANC-06): antes só 'ma' era aceito e 'má' caía no sentinela
    'erro', que o produto seguinte transformava em TypeError.
    """
    chave = str(qual_ader).strip().lower()
    if chave == 'boa':
        return True
    if chave in ('ma', 'má'):
        return False
    raise ValueError(f"qual_ader deve ser 'boa' ou 'má' (ou 'ma'): {qual_ader!r}")


def res_ade_pass(tipo_barra, qual_ader, bitola, fctd, categoria=None):
    """Retorna o valor da Resistência de aderência de cálculo
    da armadura passiva (fbd) em MPa: fbd = eta1*eta2*eta3*fctd (9.3.2.1)

    tipo_barra = 'lisa', 'entalhada' ou 'nervurada'\n
    qual_ader = 'boa' ou 'má' (ou 'ma') aderência\n
    bitola = diâmetro da barra em mm\n
    fctd = Resistência de dimensionamento do concreto à tração direta em MPa\n
    categoria = 'CA-25', 'CA-50' ou 'CA-60' (Tabela 8.2, PDF p. 48): eta1
    depende da categoria do aço, não da superfície da barra (ANC-01; a
    regra antiga, por superfície, era de 2014). Se omitida, é derivada de
    tipo_barra: lisa -> CA-25, entalhada -> CA-60, nervurada -> CA-50. Uma
    barra CA-60 nervurada exige categoria='CA-60' explícito, porque a
    derivação por tipo_barra assume CA-50 para barras nervuradas.
    """
    if categoria is None:
        categoria = _CATEGORIA_POR_TIPO_BARRA.get(tipo_barra)
        if categoria is None:
            raise ValueError(
                f"tipo_barra deve ser 'lisa', 'entalhada' ou 'nervurada': {tipo_barra!r}"
            )

    n1 = nbr.eta1(categoria)
    n2 = nbr.eta2(_boa_aderencia(qual_ader))
    n3 = nbr.eta3(bitola)
    fbd = n1*n2*n3*fctd
    return fbd


_TIPO_FIO_P31 = {'fio': 'fio liso', 'cordoalha': 'cordoalha', 'dentado': 'fio dentado'}


def res_ade_ati(tipo_fio,qual_ader,fctd):
    """Retorna o valor da Resistência de aderência de cálculo
    da armadura ativa (fbpd) em MPa

    tipo_fio = 'fio', 'cordoalha' (de três e sete fios) ou 'dentado'\n
    qual_ader = 'boa' ou 'má' (ou 'ma') aderência\n
    fctd = Resistência de dimensionamento do concreto à tração direta em MPa
    calculada na idade de aplicação de protensão para o comprimento de
    transferência ou 28 dias para o comprimento de ancoragem

    P31 (19/09/2026): fachada sobre dimensionamento/ancoragem_nbr6118.py
    (nbr.eta_p1 e anc.eta_p2, 9.3.2.2) -- ver eta_p2 lá, exposta em separado
    para ser auditável.
    """
    warnings.warn(
        "sec9.res_ade_ati é legado; use nucleo_nbr6118.eta_p1 e "
        "ancoragem_nbr6118.eta_p2 (ou ancoragem_nbr6118.fbpd_mpa, quando "
        "fctd ainda não estiver calculado).",
        DeprecationWarning,
        stacklevel=2,
    )
    if tipo_fio not in _TIPO_FIO_P31:
        raise ValueError(
            f"tipo_fio inválido: {tipo_fio!r}. Use 'fio', 'cordoalha' ou 'dentado'."
        )
    n1 = nbr.eta_p1(_TIPO_FIO_P31[tipo_fio])
    n2 = anc.eta_p2(_boa_aderencia(qual_ader))
    return n1*n2*fctd


"""
Seção 9.4 Ancoragem das armaduras, pg 35
"""

_PINO_DOBRAMENTO_TAB_9_1 = {
    # (faixa_bitola, tipo_aco) -> D/bitola (Tabela 9.1, PDF p. 57)
    ('<20', 'CA25'): 4, ('<20', 'CA50'): 5, ('<20', 'CA60'): 6,
    ('>=20', 'CA25'): 5, ('>=20', 'CA50'): 8,   # CA-60 >= 20 mm: sem valor na tabela
}


def diam_pino_dobramento(bitola, tipo_aco):
    """Retorna valor D que multiplicado ao diâmetro da barra resulta no diâmetro
    do pino de dobramento (Tabela 9.1)

    bitola = diâmetro da barra em mm\n
    tipo_aco = 'CA25', 'CA50' ou 'CA60'
    """
    faixa = '<20' if bitola < 20 else '>=20'
    D = _PINO_DOBRAMENTO_TAB_9_1.get((faixa, tipo_aco))
    if D is None:
        raise ValueError(
            f"Tabela 9.1 não dá o pino de dobramento para {tipo_aco} com "
            f"bitola {bitola} mm (faixa {faixa} mm)."
        )
    return D


def comp_ancor_basico(bitola, fyd, fbd):
    """Retorna o comprimento de ancoragem básico em cm (9.4.2.4)

    bitola = diâmetro da barra em mm\n
    fyd = tensão de escoamento de cálculo do aço em MPa\n
    fbd = resistência de aderência de cálculo da armadura passiva em MPa

    lb = (bitola/4)*(fyd/fbd) >= 25*bitola: com bitola em mm e fyd, fbd em
    MPa, o resultado sai em mm; convertido para cm (ANC-02 — antes o valor
    ficava em mm com rótulo de cm, dez vezes maior que o devido).
    """
    lb_mm = max((bitola*fyd)/(4*fbd), 25*bitola)

    return lb_mm/10


def comp_ancor_necessario(alfa, lb, as_calc, as_efet, bitola):
    """Retorna o comprimento de ancoragem necessário em cm (9.4.2.5)

    alfa = 1.0 parra barras sem gancho\n
    alfa = 0.7 para barras tracionadas com gancho, com cobrimento no plano
    normal ao do gancho >= 3 * bitola da barra\n
    alfa = 0.7 quando houver barras transversais soldadas
    alfa = 0.5 quando houver barras transverais soldadas e gancho com cobrimento
    no plano normal ao do gancho >= 3 * bitola da barra\n
    lb = comprimento de ancoragem básico em cm\n
    as_calc = área de aço calculada em cm²\n
    as_efet = área de aço efetiva em cm²

    lb_min = máx(0,3*lb, 10*bitola, 100 mm), tudo em cm. Com bitola em mm,
    "10*bitola" em cm é só "bitola" (10*bitola/10); o piso de 100 mm é 10 cm
    (ANC-02 — antes "10*bitola" ficava sem converter e o piso aparecia como
    "10", uma casa decimal abaixo dos 100 mm da norma).
    """

    lb_min = max(0.3*lb, bitola, 10.0)
    lb_nec = max(alfa*lb*(as_calc/as_efet), lb_min)

    return lb_nec


_TIPO_ISOLADO_GRUPO_P31 = {'isolado': 'fio liso', 'grupo': 'cordoalha'}


def comp_ancor_basico_ativo(bitola, fpyd, fbpd, tipo):
    """Retorna o comprimento de ancoragem básico para armaduras ativas por
    aderência em cm

    bitola = diâmetro da barra em mm\n
    fpyd = tensão de escoamento de cálculo do aço ativo em MPa\n
    fbpd = resistência de aderência de cálculo da armadura ativa calculada
    considerando a idade do concreto na data da protensão para o cálculo do
    comprimento de transferência e 28 dias para o cálculo do comprimento
    de ancoragem em MPa\n
    tipo = 'isolado' para fios isolados ou 'grupo' para cordoalhas de três ou
    sete fios

    P31 (19/09/2026): fachada sobre ancoragem_nbr6118.lbp_cm (9.4.5.1).
    'isolado' e 'grupo' viram 'fio liso' e 'cordoalha' lá (mesmo
    multiplicador de fios lisos ou dentados; ver TIPOS_ARMADURA_ATIVA_ADERENCIA).
    """
    warnings.warn(
        "sec9.comp_ancor_basico_ativo é legado; use "
        "ancoragem_nbr6118.lbp_cm.",
        DeprecationWarning,
        stacklevel=2,
    )
    if tipo not in _TIPO_ISOLADO_GRUPO_P31:
        raise ValueError(f"tipo inválido: {tipo!r}. Use 'isolado' ou 'grupo'.")
    return anc.lbp_cm(bitola, fpyd, fbpd, _TIPO_ISOLADO_GRUPO_P31[tipo])


def comp_transferencia(lbp, opi, fpyd, tipo, liberacao_gradual=True):
    """Retorna o comprimento de transferência em cm (9.4.5.2)

    lbp = comprimento de ancoragem básico para armaduras ativas por aderência
    em cm\n
    opi = tensão na armadura ativa imediatamente após a aplicação da protensão
    em MPa\n
    fpyd = tensão de escoamento de cálculo do aço ativo em MPa\n
    tipo = 'isolado' para fios dentados ou lisos ou 'grupo' para cordoalhas de
    três ou sete fios\n
    liberacao_gradual = True (padrão) quando a liberação do dispositivo de
    tração, no ato da protensão, é gradual; False (liberação súbita)
    multiplica o resultado por 1,25 (9.4.5.2 b)

    P31 (19/09/2026): fachada sobre ancoragem_nbr6118.lbpt_cm (9.4.5.2).
    """
    warnings.warn(
        "sec9.comp_transferencia é legado; use ancoragem_nbr6118.lbpt_cm.",
        DeprecationWarning,
        stacklevel=2,
    )
    if tipo not in _TIPO_ISOLADO_GRUPO_P31:
        raise ValueError(f"tipo deve ser 'isolado' ou 'grupo': {tipo!r}")
    return anc.lbpt_cm(lbp, opi, fpyd, _TIPO_ISOLADO_GRUPO_P31[tipo],
                       liberacao_gradual)


def comp_ancor_necessario_ativo(lbpt, lbp, fpyd, op_inf):
    """Retorna o comprimento de ancoragem necessário para armaduras ativas em cm

    lbpt = comprimento de transferência em cm\n
    lbp = comprimento de ancoragem básico para armaduras ativas por aderência
    em cm\n
    fpyd = tensão de escoamento de cálculo do aço ativo em MPa\n
    op_inf = tensão na armadura ativa após todas as perdas ao longo do tempo em
    MPa

    P31 (19/09/2026): fachada sobre ancoragem_nbr6118.lbpd_cm (9.4.5.3).
    """
    warnings.warn(
        "sec9.comp_ancor_necessario_ativo é legado; use "
        "ancoragem_nbr6118.lbpd_cm.",
        DeprecationWarning,
        stacklevel=2,
    )
    return anc.lbpd_cm(lbpt, lbp, fpyd, op_inf)


_PINO_DOBRAMENTO_TAB_9_2 = {
    # (faixa_bitola, tipo_aco) -> D/bitola (Tabela 9.2, PDF p. 60)
    ('<=10', 'CA25'): 3, ('<=10', 'CA50'): 3, ('<=10', 'CA60'): 3,
    ('10-20', 'CA25'): 4, ('10-20', 'CA50'): 5,   # CA-60: sem valor na tabela
    ('>=20', 'CA25'): 5, ('>=20', 'CA50'): 8,     # CA-60: sem valor na tabela
}


def diam_pino_dobramento_transversal(bitola, tipo_aco):
    """Retorna valor D que multiplicado ao diâmetro da barra resulta no diâmetro
    do pino de dobramento para armaduras transversais (Tabela 9.2)

    bitola = diâmetro da barra em mm\n
    tipo_aco = 'CA25', 'CA50' ou 'CA60'
    """
    if bitola <= 10:
        faixa = '<=10'
    elif bitola < 20:
        faixa = '10-20'
    else:
        faixa = '>=20'

    D = _PINO_DOBRAMENTO_TAB_9_2.get((faixa, tipo_aco))
    if D is None:
        raise ValueError(
            f"Tabela 9.2 não dá o pino de dobramento de estribos para "
            f"{tipo_aco} com bitola {bitola} mm (faixa {faixa} mm)."
        )
    return D


"""
Seção 9.5 Emendas das barras, pg 42
"""

def comp_transpasse_trac(porc_emen, lb_nec, lb, bitola):
    """Retorna o comprimento de transpasse para barras tracionadas em cm
    (9.5.2.2.1)

    porc_emen = proporção de barras emendadas na mesma seção em %\n
    lb_nec = comprimento de ancoragem necessário em cm\n
    lb = comprimento de ancoragem básico em cm\n
    bitola = diâmetro da barra em mm

    l0t_min = máx(0,3*alfa0t*lb, 15*bitola, 200 mm), tudo em cm. Com bitola
    em mm, "15*bitola" em cm é 1,5*bitola (ANC-03 — antes usava 15*bitola
    sem converter, o que misturava escalas na mesma comparação com o piso
    de 200 mm). Emenda por traspasse não é permitida para bitola > 32 mm
    (9.5.2, ANC-08).
    """
    if bitola > 32:
        raise ValueError(
            "Emenda por traspasse não é permitida para bitola > 32 mm (9.5.2)."
        )

    if porc_emen <= 20:
        alfa0t = 1.2
    elif porc_emen <= 25:
        alfa0t = 1.4
    elif porc_emen <= 33:
        alfa0t = 1.6
    elif porc_emen <= 50:
        alfa0t = 1.8
    elif porc_emen > 50:
        alfa0t = 2.0

    l0t_min = max(0.3*alfa0t*lb, 1.5*bitola, 20.0)
    l0t = max(alfa0t*lb_nec, l0t_min)

    return l0t


def comp_transpasse_comp(lb_nec, lb, bitola):
    """Retorna o comprimento de transpasse para barras comprimidas em cm
    (9.5.2.3)

    lb_nec = comprimento de ancoragem necessário em cm\n
    lb = comprimento de ancoragem básico em cm\n
    bitola = diâmetro da barra em mm

    l0c_min = máx(0,6*lb, 15*bitola, 200 mm), tudo em cm — mesma conversão
    de bitola do comp_transpasse_trac (ANC-03). Emenda por traspasse não é
    permitida para bitola > 32 mm (9.5.2, ANC-08).
    """
    if bitola > 32:
        raise ValueError(
            "Emenda por traspasse não é permitida para bitola > 32 mm (9.5.2)."
        )

    l0c_min = max(0.6*lb, 1.5*bitola, 20.0)
    l0c = max(lb_nec, l0c_min)

    return l0c


"""
Seção 9.6 Protensão, pg 47
"""


#todo


if __name__ == "__main__":
    main()