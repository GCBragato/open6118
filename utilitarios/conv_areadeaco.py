"""
Este módulo simplifica a conversão de áreas de aço.
Métodos disponíveis:
convComprimento(), convForca(), convArea(), convVolume(), convPressao(),
convInercia(), convCargaLinear(), convMomento()
"""

import math
import conv_unidades

def barras_barras(nBar1, phi1, phi2):
    """Converte a quantidade de barras de um diâmetro para outro
    Unidades de entrada: unidades e milímetros"""
    nBar2 = nBar1*phi1**2/phi2**2
    return nBar2

def As_barras(As,phi):
    """Retorna a quantidade de barras necessária para dado As
    Unidades de entrada: cm² e milímetros"""
    nBar = As*400/(math.pi*phi**2)
    return nBar

def barras_As(nBar,phi):
    """Retorna a área de aço de dada quantidade de barras
    Unidades de entrada: unidades e milímetros"""
    As = nBar*math.pi*phi**2/400
    return As

def barras_barras_espacamento(phi1,s1,phi2):
    """Retorna o espaçamento equivalente, dado uma bitola e espaçamentos
    referência e o espaçamento da bitola desejada
    Unidades de entrada: milímetros e centímetros"""
    s2 = 100/(((100/s1)*math.pi*phi1**2/400)/(math.pi*phi2**2/400))
    return s2
    