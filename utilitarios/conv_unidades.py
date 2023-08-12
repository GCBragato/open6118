"""
Este módulo converte unidades comumente usadas na NBR 6118.\n
Métodos disponíveis:
convComprimento(), convForca(), convArea(), convVolume(), convPressao(),
convInercia(), convCargaLinear(), convMomento()
"""

"""
Dicionários de unidades base
"""
#Comprimento
comprimento = {
    'mm' : 1000.0,
    'cm' : 100.0,
    'm' : 1.0,
    'km' : 0.001,
    'pol' : 39.3701
    }

#Força
forca = {
    'N' : 10000.0,
    'kN' : 10.0,
    'MN' : 0.01,
    'GN' : 0.00001,
    'gf' : 1000000.0,
    'kgf' : 1000.0,
    'tf' : 1.0
    }

def convComprimento(de, para):
    """Unidades aceitas: mm, cm, m, km e pol"""
    multiplicador = comprimento.get(para) / comprimento.get(de)
    return multiplicador

def convForca(de, para):
    """Unidades aceitas: N, kN, MN, GN, gf, kgf e tf"""
    multiplicador = forca.get(para) / forca.get(de)
    return multiplicador

def convArea(de, para):
    """Unidades aceitas: mm2, cm2, m2, km2 e pol2. Atenção ao 2 não
    expoente!
    """
    mm2 = comprimento.get('mm')**2
    cm2 = comprimento.get('cm')**2
    m2 = comprimento.get('m')**2
    km2 = comprimento.get('km')**2
    pol2 = comprimento.get('pol')**2

    indice = {
        'mm2' : mm2,
        'cm2' : cm2,
        'm2' : m2,
        'km2' : km2,
        'pol2' : pol2
    }

    multiplicador = indice.get(para) / indice.get(de)
    return multiplicador

def convVolume(de, para):
    """Unidades aceitas: mm3, cm3, m3, km3 e pol3. Atenção ao 3 não
    expoente!
    """
    mm3 = comprimento.get('mm')**3
    cm3 = comprimento.get('cm')**3
    m3 = comprimento.get('m')**3
    km3 = comprimento.get('km')**3
    pol3 = comprimento.get('pol')**3

    indice = {
        'mm3' : mm3,
        'cm3' : cm3,
        'm3' : m3,
        'km3' : km3,
        'pol3' : pol3
    }

    multiplicador = indice.get(para) / indice.get(de)
    return multiplicador

def convPressao(de, para):
    """Unidades aceitas: Separar com "/" (exemplo: tf/m2)
    Para Força: N, kN, MN, GN, gf, kgf e tf
    Para Área: mm2, cm2, m2, km2 e pol2. Atenção ao 2 não expoente!
    Pressão Direta: Pa, kPa, MPa e GPa
    """
    
    #1a Parte: Substituir Pa por N/m²
    de = de.replace("Pa", "N/m2")
    para = para.replace("Pa", "N/m2")

    #2a Parte: Separar por "/"
    deMatriz = de.split('/')
    paraMatriz = para.split('/')

    #3a Parte: converter a força
    multForca = convForca(deMatriz[0], paraMatriz[0])

    #4a Parte: converter a área
    multArea = convArea(deMatriz[1], paraMatriz[1])

    #5a Parte: juntar as conversões
    multiplicador = multForca / multArea
    return multiplicador

def convPesoProprio(de, para):
    """Unidades aceitas: Separar com "/" (exemplo: tf/m3)
    Para Força: N, kN, MN, GN, gf, kgf e tf
    Para Volume: mm3, cm3, m3, km3 e pol3. Atenção ao 3 não expoente!
    """

    #1a Parte: Separar por "/"
    deMatriz = de.split('/')
    paraMatriz = para.split('/')

    #2a Parte: converter a força
    multForca = convForca(deMatriz[0], paraMatriz[0])

    #3a Parte: converter o volume
    multVolume = convVolume(deMatriz[1], paraMatriz[1])

    #4a Parte: juntar as conversões
    multiplicador = multForca / multVolume
    return multiplicador


def convInercia(de, para):
    """Unidades aceitas: mm4, cm4, m4, km4 e pol4. Atenção ao 4 não
    expoente!
    """
    mm4 = comprimento.get('mm')**4
    cm4 = comprimento.get('cm')**4
    m4 = comprimento.get('m')**4
    km4 = comprimento.get('km')**4
    pol4 = comprimento.get('pol')**4

    indice = {
        'mm4' : mm4,
        'cm4' : cm4,
        'm4' : m4,
        'km4' : km4,
        'pol4' : pol4
    }

    multiplicador = indice.get(para) / indice.get(de)
    return multiplicador

def convCargaLinear(de, para):
    """Unidades aceitas: Separar com "/" (exemplo: tf/m)
    Para Força: N, kN, MN, GN, gf, kgf e tf
    Para Comprimento: mm, cm, m, km e pol
    """

    #1a Parte: Separar por "/"
    deMatriz = de.split('/')
    paraMatriz = para.split('/')

    #2a Parte: converter a força
    multForca = convForca(deMatriz[0], paraMatriz[0])
    
    #3a Parte: converter o comprimento
    multComprimento = convComprimento(deMatriz[1], paraMatriz[1])

    #4a Parte: juntar as conversões
    multiplicador = multForca / multComprimento
    return multiplicador

def convMomento(de, para):
    """Unidades aceitas: Separar com "." (exemplo: tf.m)
    Para Força: N, kN, MN, GN, gf, kgf e tf
    Para Comprimento: mm, cm, m, km e pol
    """

    #1a Parte: Separar por "/"
    deMatriz = de.split('.')
    paraMatriz = para.split('.')

    #2a Parte: converter a força
    multForca = convForca(deMatriz[0], paraMatriz[0])
    
    #3a Parte: converter o comprimento
    multComprimento = convComprimento(deMatriz[1], paraMatriz[1])

    #4a Parte: juntar as conversões
    multiplicador = multForca * multComprimento
    return multiplicador

#print(6*convPesoProprio('kgf/cm3', 'tf/m3'))
#print(6000*(.1*.1))
#print(93636*convCargaLinear('kN/m','tf/m'))
#print(2.5*convPressao('kgf/cm2','tf/m2'))
#print(convMomento('tf.cm','tf.m'))