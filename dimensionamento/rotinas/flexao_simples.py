"""
Funções utilizadas no dimensionamento de peças a flexão simples.
Métodos disponíveis:
calc_a_c_coef_lambda(fck [MPa]): (1)=a_c,(2)=coefLambda
calc_x(d [m],fcd [MPa],Md [kN.m],largura [cm],a_c,coefLambda): x[m]
calc_B_x(x [m],d [m]): B_x
calc_As(fyd [MPa],Md [kN.m],d [m],coefLambda,x [m]):
"""

import os
import sys
pathUtilitarios = os.getcwd() + "\\utilitarios"
sys.path.append(pathUtilitarios)

import conv_unidades as cv

def calc_a_c_coef_lambda(fck):
    """Retorna a_c e o coeficiente lamba
    Unidades de entrada: MPa"""
    if fck <= 50:
        a_c = 0.85
        coefLambda = 0.8
    elif fck <= 90:
        a_c = 0.85*(1-(fck-50)/200)
        coefLambda = 0.8-(fck-50)/400
    return a_c, coefLambda

def calc_x(d,fcd,Md,largura,a_c,coefLambda):
    """Retorna a altura da linha neutra (x) em metros
    Unidades de entrada: metros, MPa e kN.m"""
    fcd = fcd*cv.convPressao('MPa', 'kPa')
    x = (d-(d**2-2*(Md/(largura*a_c*fcd)))**(1/2))/coefLambda
    return x

def calc_B_x(x,d):
    """Retorna a relação x/d (Bx) e o estádio da seção
    Unidades de entrada: metros"""
    B_x = x/d
    return B_x

def calc_As(fyd,Md,d,coefLambda,x):
    """Retorna a área de aço necessária para a viga em m²
    Unidades de entrada: metros, MPa e kN.m"""
    fyd = fyd*cv.convPressao('MPa', 'kPa')
    As = Md/((d-0.5*coefLambda*x)*fyd)
    return As

def calc_x_de_As(As,fyd,largura,fcd,a_c,coefLambda):
    """Retorna a altura da linha neutra (x) em metros, dado As
    Unidades de entrada: m², metros e MPa"""
    fyd = fyd*cv.convPressao('MPa', 'kPa')
    fcd = fcd*cv.convPressao('MPa', 'kPa')
    x = As*fyd/(a_c*largura*fcd*coefLambda)
    return x

def calc_MRd(fyd,As,largura,fcd,d,a_c,coefLambda):
    """Retorna o momento resistente para a a viga em kN.m, dado o As
    Unidades de entrada: m², metros, MPa e kN.m"""
    x = calc_x_de_As(As,fyd,largura,fcd,a_c,coefLambda)
    fyd = fyd*cv.convPressao('MPa', 'kPa')
    MRd = As*fyd*(d-0.5*coefLambda*x)
    return MRd
