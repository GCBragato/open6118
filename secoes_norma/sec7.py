"""
NBR 6118:2026 - Seção 7 Critérios de projeto que visam a durabilidade
(legado: os cobrimentos da Tabela 7.2 vêm de dimensionamento/nucleo_nbr6118.py).
Métodos disponíveis:
CAAPropriedades(), agora uma fachada de uma linha sobre
dimensionamento/durabilidade_nbr6118.py (P1, 19/09/2026): emite
DeprecationWarning e delega a relacao_ac_maxima, classe_concreto_minima e
nucleo_nbr6118.cobrimento_nominal.
"""

import os
import sys
import warnings

_DIMENSIONAMENTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dimensionamento")
if _DIMENSIONAMENTO_DIR not in sys.path:
    sys.path.insert(0, _DIMENSIONAMENTO_DIR)

import nucleo_nbr6118 as nbr
import durabilidade_nbr6118 as dur

def main():
    #Pede ao usuário a Classe de Agressividade Ambiental e o tipo de Concreto
    caa = input("Classe de Agressividade Ambiental (CAI, CAII, CAIII, CAIV): ")
    ct  = input("Tipo de concreto (CA p/ armado ou CP p/ protendido): ")

    #Roda a função para pegar todas as propriedades atreladas à CAA
    resultado = CAAPropriedades(caa, ct)

    #Printa resultados
    print("Relação A/C ≤ " + str(resultado[0]))
    print("Classe concreto ≥ " + str(resultado[1]))
    print("Cobrimento Nominal de Laje = " + str(resultado[2]) + "mm")
    print("Cobrimento Nominal de Vigas e Pilares = " + str(resultado[3]) + "mm")
    print("Cobrimento Nominal de Elementos Estruturais em contato com o solo = " + str(resultado[4]) + "mm")

def CAAPropriedades(caa, ct):
    """Unidades aceitas: mm, cm, m, km e pol

    Obsoleto desde o P1 (19/09/2026): fachada de uma linha sobre
    dimensionamento/durabilidade_nbr6118.py (relacao_ac_maxima,
    classe_concreto_minima) e nucleo_nbr6118.cobrimento_nominal. Prefira
    chamar essas funções diretamente.
    """
    warnings.warn(
        "sec7.CAAPropriedades é legado; use durabilidade_nbr6118.relacao_ac_maxima/"
        "classe_concreto_minima e nucleo_nbr6118.cobrimento_nominal.",
        DeprecationWarning,
        stacklevel=2,
    )
    protendido = (ct == "CP")
    caas = ("CAI", "CAII", "CAIII", "CAIV")
    relacao_a_c_origem = {c: dur.relacao_ac_maxima(c, protendido) for c in caas}
    cClass_origem = {c: f"C{dur.classe_concreto_minima(c, protendido)}" for c in caas}
    # Tabela 7.2 (PDF p. 39) pelo núcleo. LEG-01: viga/pilar em CAA I
    # é 25 mm (estava 22 mm).
    cob_nom_laje_origem = {c: nbr.cobrimento_nominal(c, "laje", protendido) for c in caas}
    cob_nom_vigpil_origem = {c: nbr.cobrimento_nominal(c, "viga", protendido) for c in caas}
    if protendido:
        cob_nom_solo_origem = {c: "-" for c in caas}  # a Tabela 7.2 não dá
    else:
        cob_nom_solo_origem = {c: nbr.cobrimento_nominal(c, "solo") for c in caas}

    #Retorna os dados
    # [0] = Relação Água / Cimento
    # [1] = Classe de Concreto
    # [2] = Cobrimento Nominal de Laje
    # [3] = Cobrimento Nominal de Vigas e Pilares
    # [4] = Cobrimento Nominal de Elementos Estruturais em contato com o solo
    CAAPropriedades_get = [
        relacao_a_c_origem.get(caa, 'erro'),
        cClass_origem.get(caa, 'erro'),
        cob_nom_laje_origem.get(caa, 'erro'),
        cob_nom_vigpil_origem.get(caa, 'erro'),
        cob_nom_solo_origem.get(caa, 'erro')
        ]
    return CAAPropriedades_get

if __name__ == "__main__":
    main()