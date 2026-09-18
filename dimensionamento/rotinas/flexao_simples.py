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

# Núcleo normativo unico (dimensionamento/nucleo_nbr6118.py). A partir de
# dimensionamento/rotinas/, a pasta pai e' dimensionamento/ (onde o nucleo
# mora); localizado a partir de __file__, independe do diretorio de
# trabalho atual.
_DIMENSIONAMENTO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _DIMENSIONAMENTO_DIR not in sys.path:
    sys.path.append(_DIMENSIONAMENTO_DIR)

import nucleo_nbr6118 as nbr

def calc_a_c_coef_lambda(fck):
    """Retorna a_c e o coeficiente lambda
    Unidades de entrada: MPa

    a_c e' o coeficiente que multiplica fcd no bloco retangular (17.2.2 e,
    8.2.10.1): a tensao do bloco e' alpha_c*etac*fcd, nao so' alpha_c*fcd,
    e por isso a_c aqui e' o produto alpha_c*etac (etac < 1 ja a partir de
    C45). coefLambda = lambda (y = lambda*x). Delega ao nucleo.

    LEG-11: a versao no disco (alteracao local nao commitada) usava
    a_c = 1 para fck <= 50 (regressao de -5% a -8% no As frente ao HEAD).
    A versao do HEAD usava a_c = 0,85 sem etac, ja errada a partir de C45
    (-0,6% a -1,4% em C45/C50, crescendo bastante acima de C50). As duas
    foram substituidas por esta.
    """
    return nbr.alpha_c(fck) * nbr.eta_c(fck), nbr.lambda_retangulo(fck)

def calc_x(d,fcd,Md,largura,a_c,coefLambda):
    """Retorna a altura da linha neutra (x) em metros
    Unidades de entrada: metros, MPa e kN.m"""
    fcd = fcd*cv.convPressao('MPa', 'kPa')
    x = (d-(d**2-2*(Md/(largura*a_c*fcd)))**(1/2))/coefLambda
    return x

def calc_B_x(x,d):
    """Retorna a relação x/d (Bx)
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
