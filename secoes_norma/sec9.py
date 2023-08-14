"""
NBR 6118:2014, pg 32 - Seção 9 Comportamento conjunto dos materiais
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


def res_ade_pass(tipo_barra,qual_ader,bitola,fctd):
    """Retorna o valor da Resistência de aderência de cálculo
    da armadura passiva (fbd) em MPa

    tipo_barra = 'lisa', 'entalhada' ou 'nervurada'\n
    qual_ader = 'boa' ou 'má' aderência\n
    bitola = diâmetro da barra em mm\n
    fctd = Resistência de dimensionamento do concreto à tração direta em MPa
    """
    
    tipo_barra_origem = {'lisa': 1, 'entalhada': 1.4, 'nervurada': 2.25}
    qual_ader_origem = {'boa': 1, 'ma': 0.7}
    if bitola < 32:
        n3 = 1
    else:
        n3 = (132-bitola)/100
    n1 = tipo_barra_origem.get(tipo_barra, 'erro')
    n2 = qual_ader_origem.get(qual_ader, 'erro')
    fbd = n1*n2*n3*fctd
    return fbd


def res_ade_ati(tipo_fio,qual_ader,fctd):
    """Retorna o valor da Resistência de aderência de cálculo
    da armadura ativa (fbpd) em MPa

    tipo_fio = 'fio', 'cordoalha' (de três e sete fios) ou 'dentado'\n
    qual_ader = 'boa' ou 'má' aderência\n
    fctd = Resistência de dimensionamento do concreto à tração direta em MPa
    calculada na idade de aplicação de protensão para o comprimento de
    transferência ou 28 dias para o comprimento de ancoragem
    """
    
    tipo_fio_origem = {'fio': 1, 'cordoalha': 1.2, 'dentado': 1.4}
    qual_ader_origem = {'boa': 1, 'ma': 0.7}
    n1 = tipo_fio_origem.get(tipo_fio, 'erro')
    n2 = qual_ader_origem.get(qual_ader, 'erro')
    fbpd = n1*n2*fctd
    return fbpd


"""
Seção 9.4 Ancoragem das armaduras, pg 35
"""

def diam_pino_dobramento(bitola,tipo_aco):
    """Retorna valor D que multiplicado ao diâmetro da barra resulta no diâmetro
    do pino de dobramento

    bitola = diâmetro da barra em mm\n
    tipo_aco = 'CA25', 'CA50' ou 'CA60'
    """

    if bitola < 20:
        if tipo_aco == 'CA25':
            D = 4
        elif tipo_aco == 'CA50':
            D = 5
        elif tipo_aco == 'CA60':
            D = 6
    elif bitola >= 20:
        if tipo_aco == 'CA25':
            D = 5
        elif tipo_aco == 'CA50':
            D = 8
    else:
        D = 0

        return D


def comp_ancor_basico(bitola, fyd, fbd):
    """Retorna o comprimento de ancoragem básico em cm

    bitola = diâmetro da barra em mm\n
    fyd = tensão de escoamento de cálculo do aço em MPa\n
    fbd = resistência de aderência de cálculo da armadura passiva em MPa
    """
    
    lb = max((bitola*fyd)/(4*fbd), 25*bitola)

    return lb


def comp_ancor_necessario(alfa, lb, as_calc, as_efet, bitola):
    """Retorna o comprimento de ancoragem necessário em cm

    alfa = 1.0 parra barras sem gancho\n
    alfa = 0.7 para barras tracionadas com gancho, com cobrimento no plano
    normal ao do gancho >= 3 * bitola da barra\n
    alfa = 0.7 quando houver barras transversais soldadas
    alfa = 0.5 quando houver barras transverais soldadas e gancho com cobrimento
    no plano normal ao do gancho >= 3 * bitola da barra\n
    lb = comprimento de ancoragem básico em cm\n
    as_calc = área de aço calculada em cm²\n
    as_efet = área de aço efetiva em cm²
    """

    lb_min = max(0.3*lb, 10*bitola, 10)
    lb_nec = max(alfa*lb*(as_calc/as_efet), lb_min)

    return lb_nec


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
    """

    if tipo == 'isolado':
        mult = (1/4)
    elif tipo == 'grupo':
        mult = (7/36)
    
    lbp = mult*bitola*fpyd/fbpd

    return lbp


def comp_transferencia(lbp, opi, fpyd, tipo):
    """Retorna o comprimento de transferência em cm

    lbp = comprimento de ancoragem básico para armaduras ativas por aderência
    em cm\n
    opi = tensão na armadura ativa imediatamente após a aplicação da protensão
    em MPa\n
    fpyd = tensão de escoamento de cálculo do aço ativo em MPa\n
    tipo = 'isolado' para fios dentados ou lisos ou 'grupo' para cordoalhas de
    três ou sete fios
    """

    if tipo == 'isolado':
        mult = (1/4)
    elif tipo == 'grupo':
        mult = (7/36)
    
    lbpt = mult*lbp*opi/fpyd

    return lbpt


def comp_ancor_necessario_ativo(lbpt, lbp, fpyd, op_inf):
    """Retorna o comprimento de ancoragem necessário para armaduras ativas em cm

    lbpt = comprimento de transferência em cm\n
    lbp = comprimento de ancoragem básico para armaduras ativas por aderência
    em cm\n
    fpyd = tensão de escoamento de cálculo do aço ativo em MPa\n
    op_inf = tensão na armadura ativa após todas as perdas ao longo do tempo em
    MPa
    """

    lbpd = lbpt + lbp*(fpyd-op_inf)/fpyd

    return lbpd


def diam_pino_dobramento_transversal(bitola, tipo_aco):
    """Retorna valor D que multiplicado ao diâmetro da barra resulta no diâmetro
    do pino de dobramento para armaduras transversais

    bitola = diâmetro da barra em mm\n
    tipo_aco = 'CA25', 'CA50' ou 'CA60'
    """

    if bitola <= 10:
        if tipo_aco == 'CA25':
            D = 3
        elif tipo_aco == 'CA50':
            D = 3
        elif tipo_aco == 'CA60':
            D = 3
    elif bitola < 20:
        if tipo_aco == 'CA25':
            D = 4
        elif tipo_aco == 'CA50':
            D = 5
    elif bitola >= 20:
        if tipo_aco == 'CA25':
            D = 5
        elif tipo_aco == 'CA50':
            D = 8
    else:
        D = 0

        return D


"""
Seção 9.5 Emendas das barras, pg 42
"""

def comp_transpasse_trac(porc_emen, lb_nec, lb, bitola):
    """Retorna o comprimento de transpasse para barras tracionadas em cm

    porc_emen = proporção de barras emendadas na mesma seção em %\n
    lb_nec = comprimento de ancoragem necessário em cm\n
    lb = comprimento de ancoragem básico em cm\n
    bitola = diâmetro da barra em mm
    """

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

    l0t_min = max(0.3*alfa0t*lb, 15*bitola, 20)
    l0t = max(alfa0t*lb_nec, l0t_min)

    return l0t


def comp_transpasse_comp(lb_nec, lb, bitola):
    """Retorna o comprimento de transpasse para barras comprimidas em cm

    lb_nec = comprimento de ancoragem necessário em cm\n
    lb = comprimento de ancoragem básico em cm\n
    bitola = diâmetro da barra em mm
    """

    l0c_min = max(0.6*lb, 15*bitola, 20)
    l0c = max(lb_nec, l0c_min)

    return l0c


"""
Seção 9.6 Protensão, pg 47
"""


#todo


if __name__ == "__main__":
    main()