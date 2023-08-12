"""
NBR 6118:2014, pg 21 - Seção 8 Propriedades dos materiais
Classes disponíveis:
Concreto e Aco_Passivo
"""

"""
Seção 8.2 Concreto, pg 22.
Todas as propriedades do concreto serão computadas em uma classe.
"""

import os
pathConvUnid = os.getcwd() + "\\utilitarios"
import sys
sys.path.append(pathConvUnid)

import conv_unidades as cv
import conv_areadeaco as ca
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
    o_c_de_E_c() [o/oo (por mil)]
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
        self.fctd = self.fctk_inf/y_c
        self.n,self.Eps_c2,self.Eps_cu = self.Eps_c2_Eps_cu_n()

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
        if self.fck_j <= 7:
            fct_m = 0
            return fct_m
        if self.fck <= 50:
            fct_m = 0.3*self.fck_j**(2/3)
        elif self.fck <= 90:
            fct_m = 2.12*math.log(1+0.11*self.fck_j)
        return fct_m
    
    def fctk_inf_F(self):
        """Retorna ftct_inf em MPa"""
        if self.fck_j <= 7:
            fctk_inf = 0
        else:
            fctk_inf = 0.7*self.fct_m
        return fctk_inf

    def fctk_sup_F(self):
        """Retorna fctk_sup em MPa"""
        if self.fck_j <= 7:
            fctk_sup = 0
        else:
            fctk_sup = 1.3*self.fct_m
        return fctk_sup

    def E_ci_F(self):
        """Retorna E_ci em MPa"""
        if self.fck <= 50:
            E_ci = ((self.fck_j/self.fck)**(0.5))*self.a_E*5600*self.fck_j**(1/2)
        elif self.fck <= 90:
            E_ci = ((self.fck_j/self.fck)**(0.3))*21.5*1000*self.a_E*((self.fck_j/10)+1.25)**(1/3)
        return E_ci

    def E_cs_F(self):
        """Retorna E_cs em MPa"""
        a_i = min(0.8+0.2*(self.fck_j/80), 1)
        E_cs = a_i*self.E_ci
        return E_cs

    def fcd_F(self):
        """Retorna fcd em MPa"""
        return self.fck/self.y_c

    def fctd_F(self):
        """Retorna fctd em MPa"""
        return self.fctk_inf/self.y_c

    def Eps_c2_Eps_cu_n(self):
        """Retorna Eps_c2, Eps_cu em o/oo (por mil) e n"""
        if self.fck <= 50:
            n = 2
            Eps_c2 = 2.0
            Eps_cu = 3.5
        elif self.fck <= 90:
            n = 1.4+23.4*math.pow((90-self.fck)/100, 4)
            Eps_c2 = 2.0+0.085*math.pow(self.fck-50, 0.53)
            Eps_cu = 2.6+35*math.pow((90-self.fck)/100, 4)
        return n, Eps_c2, Eps_cu

    def o_c_de_Eps_c(self,Eps_c,tipo='b'):
        """Retorna a tensão o_c para o Diagrama tensão-deformação
        idealizado. Insira Eps_c em o/oo (por mil)
        
        Tipo 'a' = retorna o_c para fck\n
        Tipo 'b' = retorna o_c para 0.85*fcd
        """

        if tipo == 'a':
            if Eps_c < self.Eps_c2:
                o_c = self.fck*(1-(1-(Eps_c/self.Eps_c2))**self.n)
            elif Eps_c <= self.Eps_cu:
                o_c = self.fck
            else:
                o_c = 0
        elif tipo == 'b':
            if Eps_c < self.Eps_c2:
                o_c = 0.85*self.fcd*(1-(1-(Eps_c/self.Eps_c2))**self.n)
            elif Eps_c <= self.Eps_cu:
                o_c = self.fcd
            else:
                o_c = 0

        return o_c

class Aco_Passivo:
    """Propriedades do Aço Passico. Insira categoria como CA25, CA50 ou
    CA60 e superficie como lisa, entalhada ou nervurada

    Propriedades:
    Peso próprio = .pp [kN/m³],
    Coeficiente de Dilatação Térmica = .cDilTermica [/°C],
    .Es [MPa], .n_1, .fyk [MPa], .fyd [MPa], .Eps_su [o/oo]
    .Eps_fyk [o/oo], .Eps_fyd [o/oo]
    """
    def __init__(self, catAco = 'CA50', superficie = 'nervurada', y_s = 1.15):
        self.catAco = catAco
        self.superficie = superficie
        self.y_s = y_s
        self.pp = 78.5
        self.cDilTermica = 10e-5
        self.Es = 210000
        self.n_1 = self.n_1_F()
        self.fyk = self.fyk_F()
        self.fyd = self.fyd_F()
        self.Eps_su = 10
        self.Eps_fyk = self.Eps_fyk_F()
        self.Eps_fyd = self.Eps_fyd_F()

    def n_1_F(self):
        """Retorna aderencia da superfície da barra"""
        aderencia_dic = {'lisa': 1, 'entalhada': 1.4, 'nervurada': 2.25}
        return aderencia_dic.get(self.superficie)

    def fyk_F(self):
        """Retorna tensão de escoamento característica em MPa"""
        fyk_dic = {'CA25': 250, 'CA50': 500, 'CA60': 600}
        return fyk_dic.get(self.catAco)

    def fyd_F(self):
        """Retorna tensão de escoamento de dimensionamento em MPa"""
        return self.fyk/self.y_s

    def Eps_fyk_F(self):
        """Retorna deformação em o/oo para tensão característica"""
        return self.fyk*1000/self.Es

    def Eps_fyd_F(self):
        """Retorna deformação em o/oo para tensão de dimensionamento"""
        return self.fyd*1000/self.Es

    def o_s_de_Eps_s(self,Eps_s,tipo='b'):
        """Retorna tensão [MPa] para deformação inserida [o/oo]
        
        Tipo 'a' = retorna o_s para fyk\n
        Tipo 'b' = retorna o_s para fyd
        """
        if tipo == 'a':
            if Eps_s < self.Eps_fyk:
                o_s = Eps_s*self.Es*0.001
            elif Eps_s <= self.Eps_su:
                o_s = self.fyk
            else:
                o_s = 0
        if tipo =='b':
            if Eps_s < self.Eps_fyd:
                o_s = Eps_s*self.Es*0.001
            elif Eps_s <= self.Eps_su:
                o_s = self.fyd
            else:
                o_s = 0
        return o_s

#C = Concreto(30)
#print(C.o_c_de_Eps_c(3.5,'a'))

A = Aco_Passivo()
# #print(teste)
# #print(A.fyk)
#print(A.Eps_fyd)
# print(0.003/(A.Eps_fyd/1000+0.003))
#print('T1 = ',A.o_s_de_Eps_s(10))
#print('T2 = ',A.o_s_de_Eps_s(0.82595)*cv.convPressao('MPa','tf/cm2')*ca.barras_As(1,8))
#print('T2 = ',A.o_s_de_Eps_s(2.21203)*cv.convPressao('MPa','tf/cm2')*ca.barras_As(1,8))

#C = Concreto(30)
#print(C.E_ci)
#print('C = ',C.o_c_de_Eps_c(3.5))
#print(C.Eps_c2)
#print(C.Eps_cu)
#print(C.n)
#print(C.fcd)

# #Média ponderada para as seções:
# ABloco = 60*14 #cm²
# AConcreto = 16*14 #cm²
# fdBloco = 3.2
# fdConcreto = 21.4
# fdMédio = (ABloco*fdBloco+AConcreto*fdConcreto)/(ABloco+AConcreto)
# print(fdMédio)
