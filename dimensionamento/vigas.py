"""
Seguindo o livro: CARVALHO, Roberto Chust; FILHO, Jasson Rodrigues
de Figueiredo.Cálculo e Detalhamento de Estruturas Usuais de Concreto
Armado: Segundo a NBR 6118:2014. 4ª Edição. São Carlos: EDUFSCar 2021.
Implementarei todo o dimensionamento de uma viga, de acordo com os
exercícios do capítulo 4, página 201, exemplo 1.
"""

import os
import sys
pathUtilitarios = os.getcwd() + "\\utilitarios"
sys.path.append(pathUtilitarios)
pathSecoes_Norma = os.getcwd() + "\\secoes_norma"
sys.path.append(pathSecoes_Norma)

import conv_unidades as cv
import sec8 as s8

class Viga(s8.Concreto, s8.Aco_Passivo):
    def __init__(self,
    fck,
    largura,
    altura,
    cobrimento,
    Mk,
    Vk,
    Nk,
    a_E = 1,
    t = 28,
    cimento='CPIII',
    y_c = 1.4,
    catAco = 'CA50',
    superficie = 'nervurada',
    y_s = 1.15,
    y_f = 1.4,
    mult_dAproximado = 0.9):

        """Uma viga, suas propriedades e funções. Insira fck em MPa,
        esforços em kN e m, e dimensões em cm.

        Propriedades:

        """

        self.fck = fck
        self.largura = largura*cv.convComprimento('cm', 'm')
        self.altura = altura*cv.convComprimento('cm', 'm')
        self.cobrimento = cobrimento*cv.convComprimento('cm', 'm')
        self.Mk = Mk
        self.Vk = Vk
        self.Nk = Nk
        self.a_E = a_E
        self.t = t
        self.cimento = cimento
        self.y_c = y_c
        self.catAco = catAco
        self.superficie = superficie
        self.y_s = y_s
        self.y_f = y_f
        self.mult_dAproximado = mult_dAproximado

        #Atribuir esforços de dimensionamento [MPa]
        self.Md = self.Mk*self.y_c
        self.Vd = self.Vk*self.y_c
        self.Nd = self.Nk*self.y_c

        #Atribuir valores usados em Concreto com métodos herdados [MPa]
        self.fck_j = self.fck_j_F()
        self.fct_m = self.fct_m_F()
        self.fctk_inf = self.fctk_inf_F()
        self.fctk_sup = self.fctk_sup_F()
        self.E_ci = self.E_ci_F()
        self.E_cs = self.E_cs_F()
        self.fcd = self.fcd_F()

        #Atribuir valores usados em Aco_Passivo com métodos herdados [MPa]
        self.fyk = self.fyk_F()
        self.fyd = self.fyd_F()

        #Atribuir outros valores que serão utilizados no dimensionamento
        self.dAproximado = self.altura*self.mult_dAproximado #[m]

        if self.fck <= 50:
            self.coefLambda = 0.8
            self.a_c = 0.85
        elif self.fck <= 90:
            self.coefLambda = 0.8-(self.fck-50)/400
            self.a_c = 0.85*(1-(self.fck-50)/200)

    def calc_x(self):
        """Retorna altura da linha (x) neutra em metros"""

        d = self.dAproximado
        fcd = self.fcd*cv.convPressao('MPa', 'kPa')

        x = (d-(d**2-2*(self.Md/(self.largura*self.a_c*fcd)))**(1/2))/self.coefLambda

        return x

    def calc_B_x(self):
        """Retorna a relação x/d (Bx) e o estádio da seção"""
        B_x = self.calc_x()/self.dAproximado
        return B_x

    def calc_As(self):
        """Retorna a área de aço necessária para a viga em m²"""
        fyd = self.fyd*cv.convPressao('MPa', 'kPa')
        As = self.Md/((self.dAproximado-0.5*self.coefLambda*self.calc_x())*fyd)
        return As

#Testes
minhaViga = Viga(25,14,30,2.5,10,0,0)
print(minhaViga.calc_x()*cv.convComprimento('m', 'cm'))
print(minhaViga.dAproximado*cv.convComprimento('m', 'cm'))
print(minhaViga.calc_B_x())
print(minhaViga.calc_As()*cv.convArea('m2', 'cm2'))
print(minhaViga.fyd)