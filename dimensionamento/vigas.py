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
pathSecoes_Norma = os.getcwd() + "\\dimensionamento\\rotinas"
sys.path.append(pathSecoes_Norma)

import conv_unidades as cv
import sec8 as s8
import flexao_simples as fs
import conv_areadeaco as cAs
import math

class Viga():
    def __init__(self, largura, altura, cobrimento,  mult_dAproximado = 0.9):
        """Uma viga, suas propriedades e funções.
        Unidades de entrada: MPa, kN, metros e MPa"""

        self.largura = largura
        self.altura = altura
        self.cobrimento = cobrimento
        self.mult_dAproximado = mult_dAproximado
        self.dAproximado = self.altura*self.mult_dAproximado #[m]

class EsforcosSolicitantesViga():
    def __init__(self, Mk=0, Vk=0, Nk=0, y_f=1.4):
        """Esforços comumente utilizados para o dimensionamento de
        uma viga de concreto armado."""
        self.Mk = Mk
        self.Vk = Vk
        self.Nk = Nk
        self.Md = Mk*y_f
        self.Vd = Vk*y_f
        self.Nd = Nk*y_f

def dim_flexao_simples(mk,altura_input):

    ##################################################################
    #                       INSERIR DADOS AQUI                       #
    ##################################################################

    fck_input = 40
    largura_input = 200*cv.convComprimento('cm','m')
    altura_input = altura_input*cv.convComprimento('cm','m')
    cobrimento_input = 2.5*cv.convComprimento('cm','m')
    Mk_input = mk*cv.convMomento('tf.m', 'kN.m')
    Vk_input = 0
    Nk_input = 0
    y_f = 1.4
    y_c = 1.4

    C = s8.Concreto(fck_input,t=28,y_c=y_c,a_E=0.8,cimento='CPIV')
    A = s8.Aco_Passivo('CA50')
    V = Viga(largura_input,altura_input,cobrimento_input)
    S = EsforcosSolicitantesViga(Mk_input,Vk_input,Nk_input,y_f=y_f)

    a_c, coefLambda = fs.calc_a_c_coef_lambda(C.fck)

    x = fs.calc_x(V.dAproximado,C.fcd,S.Md,V.largura,a_c,coefLambda)
    #print('x = ',x*cv.convComprimento('m', 'cm'),'cm')
    B_x = fs.calc_B_x(x, V.dAproximado)
    As = fs.calc_As(A.fyd,S.Md,V.dAproximado,coefLambda,x)

    #print('x = ',x*cv.convComprimento('m', 'cm'),'cm')
    #print('B_x = ' + str(B_x))
    #print('As =', round(As*cv.convArea('m2', 'cm2'),2),'cm²')
    #barra = 6.3
    #print(math.ceil(cAs.As_barras(As*cv.convArea('m2','cm2'),barra)),f'Barras de {barra} mm')
    return As

def MRd_da_As():

    #Input
    fck_input = 25
    largura_input = 14*cv.convComprimento('cm','m')
    altura_input = 54*cv.convComprimento('cm','m')
    cobrimento_input = 2.5*cv.convComprimento('cm','m')
    As_input=cAs.barras_As(2,10)*cv.convArea('cm2','m2')

    C = s8.Concreto(fck_input)
    A = s8.Aco_Passivo()
    V = Viga(largura_input,altura_input,cobrimento_input)

    a_c, coefLambda = fs.calc_a_c_coef_lambda(C.fck)

    MRd = fs.calc_MRd(A.fyd,As_input,largura_input,C.fcd,V.dAproximado,a_c,coefLambda)*cv.convMomento('kN.m','tf.m')
    print('MRk = '+str(MRd/1.4))
    return MRd

def main():
    # Vão = a 0.05 a 10 de 0.05m
    '''
    vaos = [x/100+0.05 for x in range(0, 1000, 5)]
    my_vao = 0.0
    for vao in vaos:
        if vao < 0.8:
            c_by_lj = 0
            area_pp = (vao*(vao/2)/2)
        else:
            c_by_lj = 1.828-1.4624/vao
            area_pp = (vao+(vao-0.8)/2)*0.4
        c_by_pp = area_pp*2.4*0.14/vao
        c_tot = c_by_lj + c_by_pp
        momento = c_tot*vao**2/8
        As = dim_flexao_simples(momento)
        #print(f'Vão = {vao}m, As = {As:.2f}m²')
        nbarras = 2
        barra = 8
        # Área da barra
        As_max = cAs.barras_As(nbarras,barra)*cv.convArea('cm2','m2')
        #print(f'Vão = {vao}m, As = {As*cv.convArea("m2","cm2"):.2f}cm²')
        #print('As_max =', As_max*cv.convArea('m2','cm2'),'cm²')
        if As < As_max:
            my_vao = vao
        else:
            break
    print(f'Vão = {my_vao:.2f}m')'''
    for altura in range(50,69,1):
        print(f'altura = {altura}cm')
        As = dim_flexao_simples(203.4,altura)*cv.convArea('m2','cm2')
        print(f'As = {As:.6f}cm²')

if __name__ == "__main__":
    main()
