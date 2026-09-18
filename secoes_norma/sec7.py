"""
NBR 6118:2026 - Seção 7 Critérios de projeto que visam a durabilidade
(legado: os cobrimentos da Tabela 7.2 vêm de dimensionamento/nucleo_nbr6118.py).
Métodos disponíveis:
CAAPropriedades(),
"""

import os
import sys

_DIMENSIONAMENTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dimensionamento")
if _DIMENSIONAMENTO_DIR not in sys.path:
    sys.path.insert(0, _DIMENSIONAMENTO_DIR)

import nucleo_nbr6118 as nbr

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
    """Unidades aceitas: mm, cm, m, km e pol"""
    if ct == "CA": #Para Concreto Armado, base de dados é:
        relacao_a_c_origem ={"CAI": 0.65, "CAII": 0.6, "CAIII": 0.55, "CAIV": 0.45}
        cClass_origem = {"CAI": "C20", "CAII": "C25", "CAIII": "C30", "CAIV": "C40"}
        # Tabela 7.2 (PDF p. 39) pelo núcleo. LEG-01: viga/pilar em CAA I
        # é 25 mm (estava 22 mm).
        cob_nom_laje_origem = {c: nbr.cobrimento_nominal(c, "laje") for c in ("CAI", "CAII", "CAIII", "CAIV")}
        cob_nom_vigpil_origem = {c: nbr.cobrimento_nominal(c, "viga") for c in ("CAI", "CAII", "CAIII", "CAIV")}
        cob_nom_solo_origem = {c: nbr.cobrimento_nominal(c, "solo") for c in ("CAI", "CAII", "CAIII", "CAIV")}

    if ct == "CP": #Para Concreto Protendido, base de dados é:
        relacao_a_c_origem = {"CAI": 0.6, "CAII": 0.55, "CAIII": 0.5, "CAIV": 0.45}
        cClass_origem = {"CAI": "C25", "CAII": "C30", "CAIII": "C35", "CAIV": "C40"}
        cob_nom_laje_origem = {c: nbr.cobrimento_nominal(c, "laje", True) for c in ("CAI", "CAII", "CAIII", "CAIV")}
        cob_nom_vigpil_origem = {c: nbr.cobrimento_nominal(c, "viga", True) for c in ("CAI", "CAII", "CAIII", "CAIV")}
        cob_nom_solo_origem = {"CAI": "-", "CAII": "-", "CAIII": "-", "CAIV": "-"}  # a Tabela 7.2 não dá

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