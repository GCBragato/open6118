import math
import conv_datas

def main():
    print("Digite e pressione Enter.")
    meses = int(
        input("Idade desejada para o cálculo de fluência em meses: ")
        )
    a_f = multiplicador_flecha_diferida(0, meses)
    print("Multiplicar a flecha imediata por 1 + " + str(a_f))

def multiplicador_flecha_diferida(p_linha, meses):
    """
    Seção 17.3.2.1.2 Cálculo da flecha diferida no tempo para vigas
    de concreto armado, Página 126. Aqui calculamos o valor de αf, o
    multiplicador da flecha imediata.
    
    Dados de entrada: As comprimido [%] e idade da flecha diferida [meses].
    """

    #Função para o cálculo de delta_xi
    def calc_xi(t): return 0.68*(0.996**t)*t**0.32

    """Para o cálcuilo de xi_t0, consideraremos a
    aplicação de carga de longa duração em 1 mês"""
    xi_t0 = calc_xi(0.47)
    if meses >= 70:
        xi_t = 2
    else:
        xi_t = calc_xi(meses)
    delta_xi = xi_t-xi_t0

    a_f = delta_xi / (1+50*p_linha)

    return a_f

def As_min_long_vigas(fck):
    """
    17.3.5.2.1 Armadura de tração, Página 130 Tabela para área de aço
    mínima, expresso em % da área da seção.
    
    Dados de entrada = fck [MPa].
    """

    valores_p_min ={
        20: 0.15, 25: 0.15, 30: 0.15, 35: 0.164, 40: 0.179, 45: 0.194,
        50: 0.208, 55: 0.211, 60: 0.219, 65: 0.226, 70: 0.233,
        75: 0.239, 80: 0.245, 85: 0.251, 90: 0.256
        }
    p_min = valores_p_min.get(fck, 'erro')
    return p_min

#17.4 Elementos lineares sujeitos à força cortante - Estado-limite último

def As_min_trans_vigas(fct_m,fyk,bw,alfa):
    """
    17.4.1.1.1 Condições gerais, página 133. Cálculo de Asw/s
    mínimo.
    
    Dados de entrada = fct_m e fyk [MPa].
    """

    #Fórmula deduzida
    Asw_s_min = 0.2*fct_m*bw*math.sin(math.radians(alfa))/fyk
    return Asw_s_min

def VRd2(fck,fcd,bw,d,modelo,elemento):
    """17.4.2.2 Modelo de cálculo 1, página 135 e 17.4.2.2 Modelo de
    cálculo 2, página 137. Cálculo da resistência a compressão diagonal
    do concreto para verificações.
    
    Dados de entrada: fck [MPa], fcd [MPa], bw [m], d [m], modelo [1 ou 2],
    elemento [tracionado ou flsimples_fltracao]
    """

    if modelo == 1:
        VRd2 = 0.27*(1-fck/250)*fcd*bw*d


if __name__ == "__main__":
    main()