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

    Propriedades:
    Peso próprio = .pp [kN/m³],
    Coeficiente de Dilatação Térmica = .cDilTermica [/°C],
    .fck_j [MPa], .fct_m [MPa], .fctk_inf [MPa], .fctk_sup [MPa],
    .E_ci [MPa], .E_cs [MPa], .fcd [MPa]

    Funções disponíveis:
    tensaoDeformacao_Compressao() [o/oo (por mil)]
    """
    def __init__(self, fck, a_E=1, t=28, cimento='CPIII', y_c = 1.4):

        self.pp = 25
        self.cDilTermica = 10e-5
        self.fck = fck
        self.a_E = a_E
        self.t = t
        self.cimento = cimento
        self.y_c = y_c
        self.fck_j = self.fck_j_F()
        self.fct_m = self.fct_m_F()
        self.fctk_inf = self.fctk_inf_F()
        self.fctk_sup = self.fctk_sup_F()
        self.E_ci = self.E_ci_F()
        self.E_cs = self.E_cs_F()
        self.fcd = self.fcd_F()

    def fck_j_F(self):
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

    def fct_m_F(self):
        """Retorna ftct_m em MPa"""
        if self.fck_j() <= 7:
            fct_m = 0
            return fct_m
        if self.fck <= 50:
            fct_m = 0.3*self.fck_j()**(2/3)
        elif self.fck <= 90:
            fct_m = 2.12*math.log(1+0.11*self.fck_j())
        return fct_m
    
    def fctk_inf_F(self):
        """Retorna ftct_inf em MPa"""
        if self.fck_j() <= 7:
            fctk_inf = 0
        else:
            fctk_inf = 0.7*self.fct_m()
        return fctk_inf

    def fctk_sup_F(self):
        """Retorna fctk_sup em MPa"""
        if self.fck_j() <= 7:
            fctk_sup = 0
        else:
            fctk_sup = 1.3*self.fct_m()
        return fctk_sup

    def E_ci_F(self):
        """Retorna E_ci em MPa"""
        if self.fck <= 50:
            E_ci = ((self.fck_j()/self.fck)**(0.5))*self.a_E*5600*self.fck_j()**(1/2)
        elif self.fck <= 90:
            E_ci = ((self.fck_j()/self.fck)**(0.3))*21.5*1000*self.a_E*((self.fck_j()/10)+1.25)**(1/3)
        return E_ci

    def E_cs_F(self):
        """Retorna E_cs em MPa"""
        a_i = min(0.8+0.2*(self.fck_j()/80), 1)
        E_cs = a_i*self.E_ci()
        return E_cs

    def fcd_F(self):
        """Retorna fcd em MPa"""
        return self.fck/self.y_c

    def tensaoDeformacao_Compressao(self,E_c,tipo='a'):
        """Retorna a tensão o_c para o Diagrama tensão-deformação
        idealizado. Insira E_c em o/oo (por mil)
        
        Tipo 'a' = retorna o_c para fck\n
        Tipo 'b' = retorna o_c para 0.85*fcd
        """
        if self.fck <= 50:
            n = 2
            E_c2 = 2.0
            E_cu = 3.5
        elif self.fck <= 90:
            n = 1.4+23.4*math.pow((90-self.fck)/100, 4)
            E_c2 = 2.0+0.085*math.pow(self.fck-50, 0.53)
            E_cu = 2.6+35*math.pow((90-self.fck)/100, 4)

        if tipo == 'a':
            o_c = self.fck*(1-(1-(E_c/E_c2))**n)
        elif tipo == 'b':
            o_c = 0.85*self.fcd()*(1-(1-(E_c/E_c2))**n)

        return o_c

class Aco_Passivo:

    def __init__(self, categoria = 'CA50', superficie = 'nervurada', y_s = 1.15):
        self.categoria = categoria
        self.superficie = superficie
        self.y_s = y_s
        self.pp = 78.5
        self.cDilTermica = 10e-5
        self.Es = 210000
        self.n_1 = self.n_1_F()
        self.fyk = self.fyk_F()
        self.fyd = self.fyd_F()

    def n_1_F(self):
        aderencia_dic = {'lisa': 1, 'entalhada': 1.4, 'nervurada': 2.25}
        return aderencia_dic.get(self.superficie)

    def fyk_F(self):
        fyk_dic = {'CA25': 250, 'CA50': 500, 'CA60': 600}
        return fyk_dic.get(self.categoria)

    def fyd_F(self):
        return self.fyk/self.y_s