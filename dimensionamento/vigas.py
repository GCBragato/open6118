"""
Seguindo o livro: CARVALHO, Roberto Chust; FILHO, Jasson Rodrigues
de Figueiredo.Cálculo e Detalhamento de Estruturas Usuais de Concreto
Armado: Segundo a NBR 6118:2014. 4ª Edição. São Carlos: EDUFSCar 2021.
Implementarei todo o dimensionamento de uma viga, de acordo com os
exercícios do capítulo 4, página 201, exemplo 1.
"""

"""
Primeiro implementar os básicos: cobrimento, módulo de elasticidade,
conversão de unidades etc.
"""

import os
pathConvUnid = os.getcwd() + "\\utilitarios"
print(pathConvUnid)
import sys
sys.path.append(pathConvUnid)

import conv_unidades as cv

print('2.5 tf/m³ para 1 kN/m³ = ' + str(2.5 * cv.convPesoProprio('tf/m3', 'kN/m3')))