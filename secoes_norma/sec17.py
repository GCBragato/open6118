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
    multiplicador da flecha imediata. Dados de entrada = armadura
    comprimida (%) e idade para cálculo da flecha diferida (meses).
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

def armadura_minima_vigas(fck):
    """
    17.3.5.2.1 Armadura de tração, Página 130 Tabela para área de aço
    mínima, expresso em % da área da seção. Dados de entrada = fck (MPa).
    """

    valores_p_min ={
        20: 0.15, 25: 0.15, 30: 0.15, 35: 0.164, 40: 0.179, 45: 0.194,
        50: 0.208, 55: 0.211, 60: 0.219, 65: 0.226, 70: 0.233,
        75: 0.239, 80: 0.245, 85: 0.251, 90: 0.256
        }
    p_min = valores_p_min.get(fck, 'erro')
    return p_min

if __name__ == "__main__":
    main()