"""Secao 17 (legado) - Elementos lineares: flecha diferida e forca cortante.

LEGADO (auditoria NBR 6118:2026, ver REPO\\AUDITORIA_NBR6118_2026.md): nenhum
outro módulo do repositório importa secoes_norma/sec17.py hoje. Para cortante
em vigas, use dimensionamento/cortante_nbr6118.py (Vc, Vsw, VRd2 completos,
com unidades em cm); para armadura mínima, dimensionamento/nucleo_nbr6118.py
(``rho_min_flexao``/``As_min_flexao_retangular``). O ``VRd2`` abaixo ganhou
o ``return`` que faltava e o modelo de cálculo II, mas segue simples
(não calcula Vc/Vsw) — prefira cortante_nbr6118.py em código novo.
"""

import math
import os
import sys

# utilitarios/ (conv_datas) e dimensionamento/ (nucleo_nbr6118), localizados
# a partir de __file__: sem isto, "import conv_datas" falhava sempre que o
# diretorio de trabalho nao fosse a raiz do repositorio (o modulo nunca
# chegou a ser importavel de forma robusta).
_REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("utilitarios", "dimensionamento"):
    _p = os.path.join(_REPO_DIR, _sub)
    if _p not in sys.path:
        sys.path.append(_p)

import conv_datas
import nucleo_nbr6118 as nbr

def main():
    print("Digite e pressione Enter.")
    meses = int(
        input("Idade desejada para o cálculo de fluência em meses: ")
        )
    a_f = multiplicador_flecha_diferida(0, meses)
    print("Multiplicar a flecha imediata por 1 + " + str(a_f))

def multiplicador_flecha_diferida(p_linha, meses, t0_meses=1):
    """
    Seção 17.3.2.1.2 Cálculo da flecha diferida no tempo para vigas
    de concreto armado, Página 129 (PDF). Aqui calculamos o valor de αf, o
    multiplicador da flecha imediata.

    Dados de entrada: As'/(bw*d) comprimido [fração, não %] e idade da
    flecha diferida [meses]. ``t0_meses`` é a idade de aplicação da carga
    de longa duração (t0 em meses); a norma não fixa esse valor, é dado de
    projeto (17.3.2.1.2).

    LEG-09: a versão antiga usava t0 = 0,47 mês, fixo e sem relação com o
    comentário do próprio código (que já dizia "1 mês"). Agora t0 é
    parâmetro, com padrão de 1 mês.
    """

    #Função para o cálculo de xi(t) - Tabela 17.1 / 17.3.2.1.2 (PDF p. 129)
    def calc_xi(t):
        if t > 70:
            return 2.0
        return 0.68*(0.996**t)*t**0.32

    xi_t0 = calc_xi(t0_meses)
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

def VRd2(fck, fcd, bw, d, modelo, elemento, theta_graus=45.0, alfa_graus=90.0):
    """17.4.2.2 Modelo de cálculo I, página 138 (PDF) e 17.4.2.3 Modelo de
    cálculo II, página 140 (PDF). Força cortante resistente de cálculo
    relativa à ruína das bielas comprimidas de concreto (verificação
    VSd <= VRd2).

    Dados de entrada: fck [MPa], fcd [MPa], bw [m], d [m], modelo [1 ou 2].
    ``elemento`` [tracionado ou flsimples_fltracao] é aceito por
    compatibilidade, mas não é usado aqui: ele influencia Vc (parcela
    complementar à treliça), que esta função não calcula — só a
    verificação da biela (VRd2). ``theta_graus`` (30 a 45°) é a inclinação
    das bielas, só para o modelo II; ``alfa_graus`` é a inclinação dos
    estribos (90° = vertical, padrão).

    LEG-10: a versão antiga não tinha ``return`` no ramo do modelo 1
    (sempre devolvia None) e não implementava o modelo 2. bw e d em
    metros e fcd em MPa (= MN/m²): fcd*bw*d sai em MN, por isso o fator
    1000 no final, para chegar em kN. Para uso novo, com Vc/Vsw e
    unidades em cm, prefira dimensionamento/cortante_nbr6118.py
    (modelo_calculo_I / modelo_calculo_II), que já está corrigido.
    """
    alfa_v2 = 1.0 - fck/250.0

    if modelo == 1:
        return 0.27*alfa_v2*fcd*bw*d*1000.0

    if modelo == 2:
        if not (30.0 <= theta_graus <= 45.0):
            raise ValueError(
                "theta deve estar entre 30 e 45 graus (17.4.2.3, PDF p. 140)."
            )
        theta_rad = math.radians(theta_graus)
        cotg_theta = 0.0 if abs(theta_graus - 90.0) < 1e-9 else 1.0/math.tan(theta_rad)
        cotg_alfa = 0.0 if abs(alfa_graus - 90.0) < 1e-9 else 1.0/math.tan(math.radians(alfa_graus))
        return (0.54*alfa_v2*fcd*bw*d*math.sin(theta_rad)**2
                * (cotg_alfa + cotg_theta) * 1000.0)

    raise ValueError("modelo deve ser 1 ou 2 (17.4.2.2 / 17.4.2.3).")


if __name__ == "__main__":
    main()