"""
NBR 6118:2014, pg 21 - Seção 8 Propriedades dos materiais\n
Classes disponíveis:\n
Concreto e Aco_Passivo

LEGADO (auditoria NBR 6118:2026, ver REPO\\AUDITORIA_NBR6118_2026.md): este
módulo só é usado por dimensionamento/vigas.py (script de estudo do
Gustavo) e é importado por secoes_norma/sec9.py (também legado, não
editado aqui). Os cálculos de material agora delegam a
dimensionamento/nucleo_nbr6118.py, fonte única testada contra a norma
(tests/test_nucleo_nbr6118.py). Para código novo, prefira o núcleo
diretamente ou os módulos dimensionamento/*_bastos.py (ex.:
ancoragem_bastos.py no lugar de sec9.py, cortante_bastos.py no lugar da
verificação de cortante do legado).
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

# Núcleo normativo unico (dimensionamento/nucleo_nbr6118.py), localizado a
# partir de __file__ (independe do diretorio de trabalho atual).
_DIMENSIONAMENTO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dimensionamento"
)
if _DIMENSIONAMENTO_DIR not in sys.path:
    sys.path.append(_DIMENSIONAMENTO_DIR)

import nucleo_nbr6118 as nbr

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
        """Retorna fckj em MPa (12.3.3, PDF p. 90-91). Delega ao núcleo.

        LEG-02: a versão antiga só olhava o cimento para o coeficiente s de
        β1; a norma manda s = 0,20 também para todo concreto C60 ou
        superior, qualquer que seja o cimento (fckj −16,5 % em C70/CPIV
        antes da correção). Valida 20 <= fck <= 90 aqui mesmo (é a primeira
        conta do __init__), em vez do antigo UnboundLocalError para
        fck > 90 dentro de Eps_c2_Eps_cu_n.
        """
        return nbr.fckj(self.fck, self.t, self.cimento)

    def fct_m_F(self):
        """Retorna fct_m em MPa (8.2.5, PDF p. 42-43). Delega ao núcleo.

        LEG-04 (= ANC-09): a fórmula antiga era 2,12·ln(1 + 0,11·fckj), da
        NBR 6118:2014; a de 2023/2026 é 2,12·ln[1 + 0,1·(fckj + 8)]. Usa
        fckj (não fck) porque já é assim que o legado calculava (correto
        para fckj >= 7 MPa, 8.2.5); mantém o retorno 0 abaixo disso, que a
        norma não define e o módulo sempre tratou como concreto verde.
        """
        if self.fck_j <= 7:
            return 0.0
        return nbr.fct_m_idade(self.fck_j)

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
        """Retorna E_ci em MPa (8.2.8, PDF p. 44). Delega ao núcleo.

        LEG-05: a versão antiga aplicava o efeito da idade duas vezes —
        usava fckj tanto no fator (fckj/fck)^expoente quanto dentro da
        fórmula-base de 28 dias (que deve usar sempre fck). Eci(t) do
        núcleo já calcula Eci(28) com fck e só depois aplica o fator da
        idade; com t = 28 (fckj = fck) o fator vira 1 e o resultado é
        idêntico ao de sempre.
        """
        return nbr.Eci_idade(self.fck, self.fck_j, self.a_E)

    def E_cs_F(self):
        """Retorna E_cs em MPa (8.2.8). Delega o αi ao núcleo.

        LEG-06: αi usava fckj em vez de fck (−2,7 % aos 7 dias); a norma
        define αi só em função de fck (idade de projeto), aplicado sobre o
        Eci(t) já ajustado pela idade.
        """
        return nbr.alpha_i(self.fck) * self.E_ci

    def fcd_F(self):
        """Retorna fcd em MPa (12.3.3 b, PDF p. 90). Delega ao núcleo.

        LEG-03: a versão antiga sempre usava fck/γc, mesmo com t < 28 dias;
        a norma manda fcd = fckj/γc nesse caso (fcd +46 % aos 7 dias antes
        da correção, contra a segurança).
        """
        return nbr.fcd(self.fck, self.y_c, self.t, self.cimento)

    def fctd_F(self):
        """Retorna fctd em MPa"""
        return self.fctk_inf/self.y_c

    def Eps_c2_Eps_cu_n(self):
        """Retorna n, Eps_c2, Eps_cu em o/oo (por mil) (8.2.10.1, PDF p. 45).

        Já batia com a norma; passa a delegar ao núcleo para ter fonte
        única (mesmo critério do resto do módulo).
        """
        return nbr.n_parabola(self.fck), nbr.eps_c2(self.fck), nbr.eps_cu(self.fck)

    def o_c_de_Eps_c(self,Eps_c,tipo='b'):
        """Retorna a tensão o_c para o Diagrama tensão-deformação
        idealizado. Insira Eps_c em o/oo (por mil)

        Tipo 'a' = retorna o_c para fck (didático, sem âncora normativa
        própria — mantido sem alteração)\n
        Tipo 'b' = retorna o_c para 0,85*ηc*fcd (Fig. 8.2, 8.2.10.1).
        Delega ao núcleo.

        LEG-07: faltava o fator ηc no trecho parabólico (C60: +14,5 %,
        contra a segurança, já a partir de C45).
        LEG-07b: o patamar (εc2 <= εc <= εcu) devolvia fcd puro em vez de
        0,85*ηc*fcd — um salto de +17,6 % logo na entrada do patamar,
        para qualquer fck.
        """

        if tipo == 'a':
            if Eps_c < self.Eps_c2:
                o_c = self.fck*(1-(1-(Eps_c/self.Eps_c2))**self.n)
            elif Eps_c <= self.Eps_cu:
                o_c = self.fck
            else:
                o_c = 0
            return o_c

        # tipo == 'b': além de Eps_cu a norma não define o diagrama; este
        # método (uso didático/legado) devolve 0, como sempre devolveu.
        if Eps_c > self.Eps_cu:
            return 0.0
        return nbr.sigma_c(Eps_c, self.fck, self.y_c)

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
        """Retorna η1 (Tabela 8.2, PDF p. 48). Delega ao núcleo.

        LEG-08: a versão antiga calculava η1 pela superfície da barra
        (lisa/entalhada/nervurada, regra de 2014); a Tabela 8.2 de
        2023/2026 define η1 pela CATEGORIA do aço: CA-25 = 1,00,
        CA-50 = 2,25, CA-60 = 1,00 (o parâmetro ``superficie`` continua
        aceito, por compatibilidade, mas não influencia mais η1 — mesmo
        padrão do ANC-01 em ancoragem_bastos.py).
        """
        return nbr.eta1(self.catAco)

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
#print(A.fyk)
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
