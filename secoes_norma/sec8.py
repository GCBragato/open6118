"""
NBR 6118:2014, pg 21 - Seção 8 Propriedades dos materiais
Métodos disponíveis:

"""

"""
Seção 8.2 Concreto, pg 22.
Todas as propriedades do concreto serão computadas em uma classe.
"""

import os
pathConvUnid = os.getcwd() + "\\utilitarios"
print(pathConvUnid)
import sys
sys.path.append(pathConvUnid)

import conv_unidades as cv
import math

class Concreto:
    """Propriedades do Concreto. Insira fck em MPa, t em dias e cimento
    em CPI, CPII, CPIII, CPIV ou CPV

    Propriedades padrões de norma:
    Peso próprio = .pp (kN/m³),
    Coeficiente de Dilatação Térmica = .cDilTermica (/°C)

    Funções disponíveis:
    .fct_m() (MPa), .fctk_inf() (MPa), .fctk_sup() (MPa), .E_ci() (MPa), 
    .E_cs() (MPa)
    """
    def __init__(self, fck, a_E=1, t=28, cimento='CPIII'):

        self.pp = 25
        self.cDilTermica = 10e-5
        self.fck = fck
        self.a_E = a_E
        self.t = t
        self.cimento = cimento

    def fck_j(self):
        s_dic = {
            'CPI': 0.25,
            'CPII': 0.25,
            'CPIII': 0.38,
            'CPIV': 0.38,
            'CPV-ARI': 0.2
            }
        s = s_dic.get(self.cimento)
        B1 = math.e**(s*(1-((28/self.t)**(1/2))))
        fck_j = B1*self.fck
        return fck_j

    def fct_m(self):
        """Retorna ftct_m em MPa"""
        if self.fck_j() <= 7:
            fct_m = 0
            return fct_m
        if self.fck <= 50:
            fct_m = 0.3*self.fck_j()**(2/3)
        elif self.fck <= 90:
            fct_m = 2.12*math.log(1+0.11*self.fck_j())
        return fct_m
    
    def fctk_inf(self):
        """Retorna ftct_inf em MPa"""
        if self.fck_j() <= 7:
            fctk_inf = 0
        else:
            fctk_inf = 0.7*self.fct_m()
        return fctk_inf

    def fctk_sup(self):
        """Retorna fctk_sup em MPa"""
        if self.fck_j() <= 7:
            fctk_sup = 0
        else:
            fctk_sup = 1.3*self.fct_m()
        return fctk_sup

    def E_ci(self):
        """Retorna E_ci em MPa"""
        if self.fck <= 50:
            E_ci = ((self.fck_j()/self.fck)**(0.5))*self.a_E*5600*self.fck_j()**(1/2)
        elif self.fck <= 90:
            E_ci = ((self.fck_j()/self.fck)**(0.3))*21.5*1000*self.a_E*((self.fck_j()/10)+1.25)**(1/3)
        return E_ci

    def E_cs(self):
        """Retorna E_cs em MPa"""
        a_i = min(0.8+0.2*(self.fck_j()/80), 1)
        E_cs = a_i*self.E_ci()
        return E_cs








C25 = Concreto(25)
print(C25.fck_j())
print(C25.E_ci())
print(C25.E_cs())
print(C25.fct_m())
print(C25.fctk_inf())
print(C25.fctk_sup())