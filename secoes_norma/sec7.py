"""
NBR 6118:2014, pg 17 - Seção 7 Critérios de projeto que visam a durabilidade
Métodos disponíveis:
CAAPropriedades(),
"""

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
        cob_nom_laje_origem  =  {"CAI": 20, "CAII": 25, "CAIII": 35, "CAIV": 45}
        cob_nom_vigpil_origem  = {"CAI": 22, "CAII": 30, "CAIII": 40, "CAIV": 50}
        cob_nom_solo_origem  = {"CAI": 30, "CAII": 30, "CAIII": 40, "CAIV": 50}

    if ct == "CP": #Para Concreto Protendido, base de dados é:
        relacao_a_c_origem = {"CAI": 0.6, "CAII": 0.55, "CAIII": 0.5, "CAIV": 0.45}
        cClass_origem = {"CAI": "C25", "CAII": "C30", "CAIII": "C35", "CAIV": "C40"}
        cob_nom_laje_origem  = {"CAI": 25, "CAII": 30, "CAIII": 40, "CAIV": 50}
        cob_nom_vigpil_origem  = {"CAI": 30, "CAII": 35, "CAIII": 45, "CAIV": 55}
        cob_nom_solo_origem  = {"CAI": "-", "CAII": "-", "CAIII": "-", "CAIV": "-"}

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