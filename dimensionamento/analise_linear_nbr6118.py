"""Análise Linear - Pré e pós-processamento (ABNT NBR 6118:2026, Seção 14).

Módulo do pacote P14 do plano de implementação. Dá um lugar único à geometria
efetiva de elementos lineares (trecho rígido, largura colaborante, vão
efetivo, seção efetiva em mísula) e ao pós-processamento de resultados de uma
análise linear (arredondamento de momentos sobre apoio, correções do modelo
de viga contínua, redução de rigidez à torção em grelha) antes do
dimensionamento propriamente dito. Itens cobertos (páginas do PDF):

    - 14.3.3  Carregamento monotônico (p. 104)
    - 14.6.2.1 Trechos rígidos, Figura 14.1 (p. 108-109)
    - 14.6.2.2 Largura colaborante de vigas T/L, Figura 14.2 (p. 109-110)
    - 14.6.2.2 Largura efetiva com abertura na laje, Figura 14.3 (p. 109)
    - 14.6.2.3 Mísulas e variações bruscas de seção, Figura 14.4 (p. 109-110)
    - 14.6.2.4 Vão efetivo de vigas, Figura 14.5 (p. 110) - movida de
      lajes_nbr6118.py (reexportação lá mantida)
    - 14.6.3   Arredondamento do diagrama de momentos fletores, Figura 14.6
      (p. 111)
    - 14.6.6.1 Correções de momento mínimo em viga contínua e coeficientes de
      engastamento perfeito em apoio extremo, Figura 14.8 (p. 113-114)
    - 14.6.6.2 Redução da rigidez à torção em grelha/pórtico espacial
      (p. 115)
    - 14.6.6.3 Dispensa de alternância de cargas variáveis (p. 115)
    - 14.6.6.4 Critério de diafragma rígido (p. 115)

Convenções: tensões e fck em MPa; geometria em cm; esforços em kN e kN.cm.
Fora da faixa de validade de cada item, as funções levantam
``nucleo_nbr6118.FaixaNormativaError`` (nunca devolvem número calculado com a
fórmula errada). A fonte de cada fórmula é a imagem da página do PDF citada
acima (SCRATCH\\nbr_png\\pNNN.png); onde a norma só traz uma regra gráfica,
sem equação explícita (14.6.2.2 - abertura; 14.6.2.3 - mísula), a docstring
da função correspondente diz isso e declara a escolha feita.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError


# ---------------------------------------------------------------------------
# 14.3.3 - Carregamento monotônico (PDF p. 104)
# ---------------------------------------------------------------------------
def admite_carregamento_monotonico(sigma_c_serv_mpa: float, fck_mpa: float) -> bool:
    """Admite-se carregamento monotônico em vez de cíclico (14.3.3, PDF p. 104).

    Fórmula/regra: sigma_c,serv <= 0,5 * fck (resposta a ciclos de carga e
    descarga em serviço) -> admite-se carregamento monotônico até o
    estado-limite considerado, nas estruturas usuais.

    sigma_c_serv_mpa: tensão de compressão no concreto em serviço, MPa
    (positiva para compressão).
    fck_mpa: resistência característica do concreto, MPa; validada por
    ``nucleo_nbr6118.validar_fck`` (8.2.1: C20 a C90).

    Retorna True quando o carregamento monotônico pode ser admitido; False
    caso contrário (nesse caso a resposta a ciclos de carga/descarga deve ser
    considerada explicitamente).
    """
    fck = nbr.validar_fck(fck_mpa)
    limite = 0.5 * fck
    tolerancia = 1e-9 * max(1.0, abs(limite))
    return sigma_c_serv_mpa <= limite + tolerancia


# ---------------------------------------------------------------------------
# 14.6.2.1 - Trechos rígidos, Figura 14.1 (PDF p. 108-109)
# ---------------------------------------------------------------------------
def trecho_rigido_cm(h_ortogonal_cm: float) -> float:
    """Extensão do trecho rígido no cruzamento de elementos lineares
    (14.6.2.1, Figura 14.1, PDF p. 108-109).

    Fórmula: trecho = 0,3 * h, com h = altura (na direção considerada) do
    elemento que cruza o nó, aplicada a cada lado do cruzamento dos eixos
    (0,3*h1 de um lado, 0,3*h2 do outro, quando os dois elementos que cruzam
    têm alturas diferentes - chame a função uma vez para cada altura).

    h_ortogonal_cm: altura do elemento ortogonal que cruza o nó, na direção
    considerada, cm.

    Faixa: h_ortogonal_cm > 0.
    """
    if h_ortogonal_cm <= 0.0:
        raise FaixaNormativaError(
            f"h_ortogonal_cm = {h_ortogonal_cm:g} cm não é uma altura válida "
            "(14.6.2.1): deve ser positiva."
        )
    return 0.3 * h_ortogonal_cm


# ---------------------------------------------------------------------------
# 14.6.2.2 - Largura colaborante de vigas T/L, Figura 14.2 (PDF p. 109-110)
# ---------------------------------------------------------------------------
def vao_a_para_mesa(L_cm: float, tipo: str = "biapoiada") -> float:
    """Distância 'a' entre pontos de momento fletor nulo (14.6.2.2, PDF p. 109).

    Promovida de viga_servico_nbr6118.py para este módulo (P14); a
    reexportação lá mantida preserva a assinatura pública antiga.

    tipo:
      'biapoiada'   -> a = 1,00 * L
      'continua', 'continua-extrema'      -> a = 0,75 * L (tramo com momento
        em uma só extremidade)
      'continua-intermediaria'            -> a = 0,60 * L (tramo com
        momentos nas duas extremidades)
      'balanco'     -> a = 2,00 * L

    Alternativamente, a norma permite calcular ou conferir 'a' pelo exame
    direto do diagrama de momentos fletores da estrutura; esta função cobre
    apenas a estimativa tabelada.
    """
    t = tipo.lower()
    if t == "biapoiada":
        return L_cm
    if t in ("continua-extrema", "continua"):
        return 0.75 * L_cm
    if t == "continua-intermediaria":
        return 0.6 * L_cm
    if t == "balanco":
        return 2.0 * L_cm
    raise ValueError(f"tipo desconhecido: {tipo}.")


def largura_colaborante_cm(
    bw_cm: float,
    b2_esq_cm: float,
    b2_dir_cm: float,
    a_cm: float,
    borda: bool = False,
    b4_cm: float | None = None,
) -> float:
    """Largura colaborante bf de viga de seção T ou L (14.6.2.2, Figura 14.2,
    PDF p. 109-110).

    bf = bw + b1 + b3, com:
        b1 <= 0,5 * b2_esq_cm  e  b1 <= 0,1 * a_cm   (lado esquerdo, mesa
            contínua com viga vizinha a distância b2_esq_cm)
        b3 <= 0,5 * b2_dir_cm  e  b3 <= 0,1 * a_cm   (lado direito contínuo,
            quando borda=False)
        b3 <= b4_cm            e  b3 <= 0,1 * a_cm   (lado direito de borda -
            face livre, mísula ou abertura -, quando borda=True; b4_cm é o
            limite físico do lado de borda mostrado na metade inferior da
            Figura 14.2)

    bw_cm: largura da nervura (alma) da viga.
    b2_esq_cm: distância entre a face da nervura e a face da viga vizinha
    mais próxima, do lado esquerdo (ou o dobro da distância até a lateral da
    laje contínua, conforme a Figura 14.2).
    b2_dir_cm: idem, do lado direito; ignorado quando borda=True.
    a_cm: distância entre pontos de momento fletor nulo no tramo considerado
    (ver vao_a_para_mesa).
    borda: True quando o lado direito tem condição de borda (face livre,
    mísula ou abertura), caso em que o limite passa a ser b4_cm em vez de
    0,5*b2_dir_cm. Para seção L (mesa de um só lado), use borda=True com
    b4_cm=0,0.
    b4_cm: limite físico do lado de borda (Figura 14.2); obrigatório quando
    borda=True.

    Faixa: a_cm > 0; b2_esq_cm >= 0; b2_dir_cm >= 0 (quando usado); b4_cm >=
    0 (quando usado).
    """
    if a_cm <= 0.0:
        raise FaixaNormativaError(
            f"a_cm = {a_cm:g} cm não é uma distância válida entre pontos de "
            "momento nulo (14.6.2.2): deve ser positiva."
        )
    if b2_esq_cm < 0.0:
        raise FaixaNormativaError(
            f"b2_esq_cm = {b2_esq_cm:g} cm não pode ser negativo (14.6.2.2)."
        )
    b1 = min(0.5 * b2_esq_cm, 0.1 * a_cm)
    if borda:
        if b4_cm is None:
            raise ValueError(
                "b4_cm é obrigatório quando borda=True (14.6.2.2, Figura 14.2)."
            )
        if b4_cm < 0.0:
            raise FaixaNormativaError(
                f"b4_cm = {b4_cm:g} cm não pode ser negativo (14.6.2.2)."
            )
        b3 = min(b4_cm, 0.1 * a_cm)
    else:
        if b2_dir_cm < 0.0:
            raise FaixaNormativaError(
                f"b2_dir_cm = {b2_dir_cm:g} cm não pode ser negativo (14.6.2.2)."
            )
        b3 = min(0.5 * b2_dir_cm, 0.1 * a_cm)
    return bw_cm + b1 + b3


def largura_efetiva_mesa(
    bw_cm: float, b2_l_esq_cm: float, b2_l_dir_cm: float,
    L_cm: float, tipo_vao: str = "biapoiada",
    tipo_secao: str = "T",
) -> dict:
    """Largura colaborante bf para seção T ou L, a partir do vão e do tipo de
    tramo (14.6.2.2, Figura 14.2, PDF p. 109-110).

    Promovida de viga_servico_nbr6118.py para este módulo (P14): mesma
    assinatura e mesmo resultado de antes deste pacote (a reexportação em
    viga_servico_nbr6118.largura_efetiva_mesa preserva quem já chamava a
    função lá); a fórmula em si agora é a de largura_colaborante_cm.

    bw_cm     : largura da nervura.
    b2_l_*_cm : distância livre entre face do pilar/nervura e face da viga
                vizinha (uma para cada lado; para seção L, passar 0,0 do
                lado livre).
    L_cm      : vão da viga.
    tipo_vao  : ver vao_a_para_mesa().
    tipo_secao: 'T' (mesa dos dois lados) ou 'L' (mesa de um só lado - o
                lado direito é tratado como borda, com b4=0).

    Retorna dict com a_cm, b1_cm, b3_cm, bf_cm (mesmas chaves de antes deste
    pacote).
    """
    a = vao_a_para_mesa(L_cm, tipo_vao)
    borda_L = tipo_secao.upper() == "L"
    b1 = min(0.5 * b2_l_esq_cm, 0.1 * a)
    bf = largura_colaborante_cm(
        bw_cm, b2_l_esq_cm, 0.0 if borda_L else b2_l_dir_cm, a,
        borda=borda_L, b4_cm=0.0 if borda_L else None,
    )
    b3 = bf - bw_cm - b1
    return {
        "a_cm": a,
        "b1_cm": b1,
        "b3_cm": b3,
        "bf_cm": bf,
    }


def largura_efetiva_com_abertura(bf_cm: float, bef_geometrico_cm: float) -> float:
    """Largura efetiva bef da mesa colaborante na presença de abertura na
    laje (14.6.2.2, Figura 14.3, PDF p. 109).

    A norma não dá equação explícita aqui - é uma regra gráfica: quando a
    laje tem abertura ou interrupção na região da mesa colaborante, traçam-se
    duas retas (numeradas 1 e 2 na Figura 14.3) a partir dos vértices da
    abertura até a viga, e a largura efetiva bef é lida diretamente no
    desenho, respeitando sempre bef <= bf. Como a norma não fixa o ângulo
    dessas retas nem uma fórmula fechada, esta função não reconstrói a
    geometria da abertura (que depende do desenho de cada caso); ela recebe
    o bef já obtido graficamente (bef_geometrico_cm, pelo desenho da Figura
    14.3 do caso concreto) e apenas aplica o limite normativo bf.

    bf_cm: largura colaborante sem abertura (14.6.2.2, largura_colaborante_cm
    ou largura_efetiva_mesa).
    bef_geometrico_cm: largura efetiva obtida da construção gráfica da
    Figura 14.3 para a abertura em questão.

    Faixa: bf_cm > 0; bef_geometrico_cm >= 0.
    """
    if bf_cm <= 0.0:
        raise FaixaNormativaError(
            f"bf_cm = {bf_cm:g} cm não é uma largura colaborante válida "
            "(14.6.2.2): deve ser positiva."
        )
    if bef_geometrico_cm < 0.0:
        raise FaixaNormativaError(
            f"bef_geometrico_cm = {bef_geometrico_cm:g} cm não pode ser "
            "negativo (14.6.2.2, Figura 14.3)."
        )
    return min(bf_cm, bef_geometrico_cm)


# ---------------------------------------------------------------------------
# 14.6.2.3 - Mísulas e variações bruscas de seção, Figura 14.4 (PDF p. 109-110)
# ---------------------------------------------------------------------------
def secao_efetiva_misula(h_menor_cm: float, h_maior_cm: float) -> float:
    """Altura (ou largura) efetiva em mísula ou variação brusca de seção
    (14.6.2.3, Figura 14.4, PDF p. 109-110).

    A norma também não dá equação aqui (regra gráfica): "só deve ser
    considerada como parte efetiva da seção aquela indicada na Figura 14.4".
    A figura mostra duas transições espelhadas (uma para o caso em que a
    seção aumenta ao longo do vão, outra em que diminui), cada uma com dois
    traçados sobrepostos e legendados 1 e 2 (variação brusca e mísula,
    respectivamente) entre um trecho de seção menor e um de seção maior; em
    ambos os traçados, o mesmo segmento vertical rotulado "hef ou bef" mede,
    na posição da transição, a distância entre o nível do trecho maior e o
    nível do trecho menor - ou seja, o valor de hef (ou bef) coincide com a
    própria altura (ou largura) do trecho de seção CONSTANTE menor que a
    mísula ou a variação brusca liga, nunca com o do trecho maior nem com
    algo intermediário dentro da cunha de transição. Interpretação adotada
    aqui, a favor da segurança e consistente com a leitura da figura nos
    dois sentidos: a dimensão efetiva no trecho de mísula ou variação
    brusca é o MENOR dos dois trechos de seção constante que ela liga - o
    acréscimo de seção dado pela mísula nunca é contado.

    h_menor_cm, h_maior_cm: alturas (ou larguras) dos dois trechos de seção
    constante ligados pela mísula ou variação brusca, com h_menor_cm <=
    h_maior_cm.

    Faixa: h_menor_cm > 0; h_maior_cm > 0; h_menor_cm <= h_maior_cm.
    """
    if h_menor_cm <= 0.0 or h_maior_cm <= 0.0:
        raise FaixaNormativaError(
            "h_menor_cm e h_maior_cm devem ser positivos (14.6.2.3)."
        )
    if h_menor_cm > h_maior_cm:
        raise ValueError(
            "h_menor_cm deve ser <= h_maior_cm (troque a ordem dos argumentos)."
        )
    return h_menor_cm


# ---------------------------------------------------------------------------
# 14.6.2.4 - Vão efetivo, Figura 14.5 (PDF p. 110)
# ---------------------------------------------------------------------------
def vao_efetivo(l0_cm: float, t1_cm: float, t2_cm: float, h_cm: float) -> float:
    """Vão efetivo de viga (ou laje) (14.6.2.4, Figura 14.5, PDF p. 110).

    Promovida de lajes_nbr6118.py para este módulo (P14); a reexportação lá
    mantida preserva a assinatura pública antiga. Fórmula (sem alteração):

        l_ef = l0 + a1 + a2
        a1 = min(t1/2, 0,3*h)
        a2 = min(t2/2, 0,3*h)

    l0_cm: distância livre entre as faces dos apoios.
    t1_cm, t2_cm: largura dos apoios em cada extremidade, na direção do vão.
    h_cm: altura do elemento.
    """
    a1 = min(t1_cm / 2.0, 0.3 * h_cm)
    a2 = min(t2_cm / 2.0, 0.3 * h_cm)
    return l0_cm + a1 + a2


# ---------------------------------------------------------------------------
# 14.6.3 - Arredondamento do diagrama de momentos fletores, Figura 14.6
# (PDF p. 111)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoArredondamentoMomento:
    M_kncm: float
    R1_kn: float
    R2_kn: float
    t_cm: float
    delta_M_kncm: float
    delta_M1_kncm: float
    delta_M2_kncm: float
    M_arredondado_kncm: float
    M_esquerda_kncm: float
    M_direita_kncm: float
    memoria: tuple[str, ...]


def arredondar_momento_apoio(
    M_kncm: float, R1_kn: float, R2_kn: float, t_cm: float,
) -> ResultadoArredondamentoMomento:
    """Arredondamento do diagrama de momentos fletores sobre um apoio (ou
    carga concentrada) de largura t (14.6.3, Figura 14.6, PDF p. 111).

    Caso geral, com reações distintas R1 (borda esquerda do apoio) e R2
    (borda direita):
        DeltaM  = (R2 - R1)/4 * t   (no eixo do apoio)
        DeltaM1 = R1 * t / 4        (na borda esquerda, sob R1)
        DeltaM2 = R2 * t / 4        (na borda direita, sob R2)

    Caso particular de apoio simétrico, com reação única R (R1 = R2 = R): a
    Figura 14.6 dá, separadamente, a redução no eixo do apoio
        DeltaM' = R * t / 8
    que NÃO é o mesmo valor de DeltaM acima (DeltaM se anula quando R1=R2,
    por ser proporcional a R2-R1; DeltaM' é a fórmula própria da norma para
    esse caso degenerado). Esta função usa DeltaM' sempre que R1 == R2
    (dentro de tolerância relativa), e a fórmula geral (DeltaM) nos demais
    casos, para reduzir o momento no eixo do apoio.

    M_kncm: momento fletor de pico no eixo do apoio (ou da carga
    concentrada), calculado tratando o apoio como pontual, kN.cm.
    R1_kn, R2_kn: reações (ou forças) nas bordas esquerda/direita do apoio,
    kN (módulo).
    t_cm: largura do apoio (ou da carga concentrada) na direção do vão, cm.

    Todas as reduções são aplicadas no sentido de aliviar o pico (preservam
    o sinal de M_kncm).
    """
    if t_cm < 0.0:
        raise FaixaNormativaError(f"t_cm = {t_cm:g} cm não pode ser negativo (14.6.3).")
    if R1_kn < 0.0 or R2_kn < 0.0:
        raise FaixaNormativaError("R1_kn e R2_kn devem ser >= 0 (14.6.3, módulo da reação).")

    delta_M = (R2_kn - R1_kn) / 4.0 * t_cm
    delta_M1 = R1_kn * t_cm / 4.0
    delta_M2 = R2_kn * t_cm / 4.0
    simetrico = abs(R1_kn - R2_kn) <= 1e-9 * max(1.0, R1_kn, R2_kn)
    delta_eixo = (R1_kn * t_cm / 8.0) if simetrico else delta_M

    sinal = math.copysign(1.0, M_kncm) if M_kncm != 0.0 else 1.0
    M_arred = M_kncm - sinal * delta_eixo
    M_esq = M_kncm - sinal * delta_M1
    M_dir = M_kncm - sinal * delta_M2

    memoria = (
        f"14.6.3 (Fig. 14.6): M={M_kncm:.2f} kN.cm, R1={R1_kn:.2f} kN, "
        f"R2={R2_kn:.2f} kN, t={t_cm:.2f} cm",
        f"DeltaM1 = R1*t/4 = {delta_M1:.2f} kN.cm -> M na borda esquerda = {M_esq:.2f} kN.cm",
        f"DeltaM2 = R2*t/4 = {delta_M2:.2f} kN.cm -> M na borda direita = {M_dir:.2f} kN.cm",
        (
            f"R1=R2: DeltaM' = R*t/8 = {delta_eixo:.2f} kN.cm (caso simétrico, Fig. 14.6)"
            if simetrico else
            f"DeltaM = (R2-R1)/4*t = {delta_M:.2f} kN.cm (no eixo do apoio)"
        ),
        f"M arredondado no eixo do apoio = {M_arred:.2f} kN.cm",
    )
    return ResultadoArredondamentoMomento(
        M_kncm=M_kncm, R1_kn=R1_kn, R2_kn=R2_kn, t_cm=t_cm,
        delta_M_kncm=delta_M, delta_M1_kncm=delta_M1, delta_M2_kncm=delta_M2,
        M_arredondado_kncm=M_arred, M_esquerda_kncm=M_esq, M_direita_kncm=M_dir,
        memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 14.6.6.1 - Vigas contínuas: momento mínimo e coeficientes de engastamento
# perfeito em apoio extremo, Figura 14.8 (PDF p. 113-114)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoMomentosMinimos:
    """Resultado de momentos_minimos_viga_continua (14.6.6.1 a, b).

    Nota sobre ``ok``: esta função apenas corrige/eleva os momentos quando a
    norma exige um mínimo (nunca rejeita a entrada por si), então ``ok`` é
    sempre True aqui - o campo existe só para seguir a convenção 3.3.4 do
    plano (dataclass de verificação/dimensionamento traz ok, governante e
    memoria); use ``aplica_minimo_negativo`` para saber se o item b) mexeu
    no momento negativo.
    """

    M_positivo_kncm: float
    M_positivo_engastamento_kncm: float
    M_positivo_final_kncm: float
    M_negativo_kncm: float | None
    M_negativo_engastamento_kncm: float | None
    M_negativo_final_kncm: float | None
    aplica_minimo_negativo: bool
    ok: bool
    memoria: tuple[str, ...]


def momentos_minimos_viga_continua(
    M_positivo_kncm: float,
    M_positivo_engastamento_kncm: float,
    M_negativo_kncm: float | None = None,
    M_negativo_engastamento_kncm: float | None = None,
    largura_apoio_cm: float | None = None,
    altura_pilar_cm: float | None = None,
) -> ResultadoMomentosMinimos:
    """Correções de momento mínimo no modelo de viga contínua, simplesmente
    apoiada nos pilares (14.6.6.1 a, b, PDF p. 113).

    a) Não podem ser considerados momentos positivos de vão menores que os
       de engastamento perfeito:
           M+ adotado = max(M_positivo_kncm, M_positivo_engastamento_kncm)
    b) Quando a viga for solidária com o pilar intermediário e a largura do
       apoio, medida na direção do eixo da viga, for maior que 1/4 da altura
       do pilar, não pode ser considerado momento negativo de módulo menor
       que o de engastamento perfeito nesse apoio:
           |M-| adotado = max(|M_negativo_kncm|, |M_negativo_engastamento_kncm|)
           quando largura_apoio_cm > 0,25 * altura_pilar_cm

    M_positivo_kncm: momento positivo de vão obtido do modelo de viga
    contínua simplificada.
    M_positivo_engastamento_kncm: momento positivo de vão que se obteria com
    engastamento perfeito nos apoios internos (p*l^2/24, para carga
    uniforme; o chamador fornece o valor já calculado).
    M_negativo_kncm, M_negativo_engastamento_kncm: idem, para o momento
    negativo no apoio intermediário avaliado (None quando o item b) não se
    aplica a este apoio).
    largura_apoio_cm: largura do apoio na direção do eixo da viga.
    altura_pilar_cm: altura do pilar, na mesma direção.

    O item b) só é avaliado quando M_negativo_kncm, largura_apoio_cm e
    altura_pilar_cm forem todos informados; nesse caso
    M_negativo_engastamento_kncm passa a ser obrigatório.
    """
    M_pos_final = max(M_positivo_kncm, M_positivo_engastamento_kncm)
    memoria = [
        f"14.6.6.1 a): M+ adotado = max({M_positivo_kncm:.2f}, "
        f"{M_positivo_engastamento_kncm:.2f}) = {M_pos_final:.2f} kN.cm",
    ]

    aplica_neg = False
    M_neg_final = M_negativo_kncm
    if (
        M_negativo_kncm is not None
        and largura_apoio_cm is not None
        and altura_pilar_cm is not None
    ):
        limite = 0.25 * altura_pilar_cm
        aplica_neg = largura_apoio_cm > limite + 1e-9 * max(1.0, limite)
        if aplica_neg:
            if M_negativo_engastamento_kncm is None:
                raise ValueError(
                    "M_negativo_engastamento_kncm é obrigatório quando o apoio "
                    "é mais largo que 1/4 da altura do pilar (14.6.6.1 b)."
                )
            sinal = (
                math.copysign(1.0, M_negativo_kncm)
                if M_negativo_kncm != 0.0 else -1.0
            )
            M_neg_final = sinal * max(
                abs(M_negativo_kncm), abs(M_negativo_engastamento_kncm)
            )
            memoria.append(
                f"14.6.6.1 b): largura do apoio ({largura_apoio_cm:.2f} cm) > "
                f"h_pilar/4 ({limite:.2f} cm); |M-| adotado = "
                f"max({abs(M_negativo_kncm):.2f}, "
                f"{abs(M_negativo_engastamento_kncm):.2f}) = "
                f"{abs(M_neg_final):.2f} kN.cm"
            )
        else:
            memoria.append(
                f"14.6.6.1 b): não se aplica (largura do apoio "
                f"{largura_apoio_cm:.2f} cm <= h_pilar/4 = {limite:.2f} cm)."
            )
    else:
        memoria.append(
            "14.6.6.1 b): não avaliado (dados do apoio/pilar não informados)."
        )

    return ResultadoMomentosMinimos(
        M_positivo_kncm=M_positivo_kncm,
        M_positivo_engastamento_kncm=M_positivo_engastamento_kncm,
        M_positivo_final_kncm=M_pos_final,
        M_negativo_kncm=M_negativo_kncm,
        M_negativo_engastamento_kncm=M_negativo_engastamento_kncm,
        M_negativo_final_kncm=M_neg_final,
        aplica_minimo_negativo=aplica_neg,
        ok=True,
        memoria=tuple(memoria),
    )


@dataclass(frozen=True)
class ResultadoCoeficientesEngastamento:
    r_inf: float
    r_sup: float
    r_viga: float
    coef_viga: float
    coef_sup: float
    coef_inf: float
    memoria: tuple[str, ...]


def coeficientes_engastamento_extremo(
    r_inf: float, r_sup: float, r_viga: float,
) -> ResultadoCoeficientesEngastamento:
    """Coeficientes de distribuição do momento de engastamento perfeito num
    apoio extremo viga-pilar (14.6.6.1 c, Figura 14.8, PDF p. 113-114).

    Quando não se faz o cálculo exato da solidariedade viga-pilar, o momento
    fletor no apoio extremo é tomado como o momento de engastamento perfeito
    multiplicado pelos coeficientes:
        na viga:               (r_inf + r_sup) / (r_viga + r_inf + r_sup)
        no tramo sup. do pilar: r_sup / (r_viga + r_inf + r_sup)
        no tramo inf. do pilar: r_inf / (r_viga + r_inf + r_sup)
    com r_i = I_i / l_i (rigidez do elemento i no nó considerado). Pela
    Figura 14.8, l_i é o vão livre total da viga (l_vig) e, para os pilares,
    a METADE do vão livre acima/abaixo do nó (l_sup/2, l_inf/2) - o chamador
    já deve fornecer r_inf e r_sup calculados com essas metades (r_i =
    I_i/l_i, com l_i = l_sup/2 ou l_inf/2).

    r_inf, r_sup: rigidez (I/l) dos tramos inferior e superior do pilar no
    nó considerado.
    r_viga: rigidez (I/l) da viga no nó considerado.

    Nota: por equilíbrio de momentos no nó, coef_viga = coef_sup + coef_inf
    sempre (o momento que entra na viga se reparte integralmente entre os
    dois tramos do pilar).

    Faixa: r_inf, r_sup, r_viga >= 0, com pelo menos um positivo (a soma no
    denominador não pode ser nula).
    """
    if r_inf < 0.0 or r_sup < 0.0 or r_viga < 0.0:
        raise FaixaNormativaError(
            "r_inf, r_sup e r_viga devem ser >= 0 (14.6.6.1 c)."
        )
    soma = r_viga + r_inf + r_sup
    if soma <= 0.0:
        raise FaixaNormativaError(
            "r_viga + r_inf + r_sup deve ser positivo (14.6.6.1 c)."
        )
    coef_viga = (r_inf + r_sup) / soma
    coef_sup = r_sup / soma
    coef_inf = r_inf / soma
    memoria = (
        f"14.6.6.1 c) (Fig. 14.8): r_inf={r_inf:.4g}, r_sup={r_sup:.4g}, "
        f"r_viga={r_viga:.4g}",
        f"coef_viga = (r_inf+r_sup)/soma = {coef_viga:.4f}",
        f"coef_sup  = r_sup/soma = {coef_sup:.4f}",
        f"coef_inf  = r_inf/soma = {coef_inf:.4f}",
    )
    return ResultadoCoeficientesEngastamento(
        r_inf=r_inf, r_sup=r_sup, r_viga=r_viga,
        coef_viga=coef_viga, coef_sup=coef_sup, coef_inf=coef_inf,
        memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 14.6.6.2 - Redução da rigidez à torção em grelha/pórtico espacial
# (PDF p. 115)
# ---------------------------------------------------------------------------
FATOR_RIGIDEZ_TORCAO_GRELHA = 0.15  # 14.6.6.2 - 15% da rigidez elástica


def rigidez_torcao_reduzida(
    GJ_elastico_kncm2: float,
    classe_protensao: int | None = None,
    desprezar_para_elu: bool = False,
) -> float:
    """Rigidez à torção das vigas em modelos de grelha ou pórtico espacial
    (14.6.6.2, PDF p. 115).

    De maneira aproximada, reduz-se a rigidez à torção elástica das vigas
    para simular a fissuração por torção:
        GJ_reduzido = FATOR_RIGIDEZ_TORCAO_GRELHA * GJ_elastico  (=0,15*GJ),
    exceto para elementos estruturais com protensão limitada ou completa
    (classes 2 ou 3), que mantêm GJ_elastico (a redução não se aplica a
    eles).

    Alternativa, só para verificação de estados-limites últimos: pode-se
    considerar rigidez à torção das vigas nula (GJ = 0), de modo a eliminar
    a torção de compatibilidade da análise (ressalvado o indicado em
    17.5.1.2, fora do escopo deste módulo) - use desprezar_para_elu=True.

    GJ_elastico_kncm2: rigidez à torção elástica da viga (G*J), kN.cm2.
    classe_protensao: 2 ou 3 para protensão limitada/completa (mantém
    GJ_elastico); None ou outro valor para concreto armado ou protensão
    parcial, aplica a redução de 15%.
    desprezar_para_elu: True devolve 0,0 (torção de compatibilidade
    desprezada, só para ELU), tendo prioridade sobre classe_protensao.
    """
    if GJ_elastico_kncm2 < 0.0:
        raise FaixaNormativaError(
            f"GJ_elastico_kncm2 = {GJ_elastico_kncm2:g} não pode ser negativo (14.6.6.2)."
        )
    if desprezar_para_elu:
        return 0.0
    if classe_protensao in (2, 3):
        return GJ_elastico_kncm2
    return FATOR_RIGIDEZ_TORCAO_GRELHA * GJ_elastico_kncm2


# ---------------------------------------------------------------------------
# 14.6.6.3 - Dispensa de alternância de cargas variáveis (PDF p. 115)
# ---------------------------------------------------------------------------
def dispensa_alternancia_cargas(q_kn_m2: float, g_kn_m2: float) -> bool:
    """Dispensa da alternância de cargas variáveis em edifícios (14.6.6.3,
    PDF p. 115; a mesma regra vale para lajes, 14.7.1).

    Fórmula/regra: para carga_total = g_kn_m2 + q_kn_m2,
        q_kn_m2 <= 5 kN/m2  E  q_kn_m2 <= 0,5 * carga_total
    dispensam a consideração de alternância de cargas variáveis na análise
    estrutural (limites inclusivos).

    q_kn_m2: carga variável (sobrecarga), kN/m2.
    g_kn_m2: carga permanente, kN/m2 (carga_total = g_kn_m2 + q_kn_m2).

    Faixa: q_kn_m2 >= 0; g_kn_m2 >= 0.
    """
    if q_kn_m2 < 0.0 or g_kn_m2 < 0.0:
        raise FaixaNormativaError(
            "q_kn_m2 e g_kn_m2 devem ser >= 0 (14.6.6.3)."
        )
    carga_total = g_kn_m2 + q_kn_m2
    tol = 1e-9 * max(1.0, carga_total)
    return q_kn_m2 <= 5.0 + 1e-9 and q_kn_m2 <= 0.5 * carga_total + tol


# ---------------------------------------------------------------------------
# 14.6.6.4 - Critério de diafragma rígido (PDF p. 115)
# ---------------------------------------------------------------------------
def laje_diafragma_rigido(
    lado_maior_cm: float, lado_menor_cm: float, tem_abertura_grande: bool = False,
) -> bool:
    """Critério para considerar a laje de um pavimento como diafragma
    (chapa) totalmente rígido em seu plano (14.6.6.4, PDF p. 115).

    Fórmula/regra: a laje pode ser considerada diafragma rígido quando não
    apresentar grandes aberturas E o lado maior do retângulo circunscrito ao
    pavimento em planta não superar em três vezes o lado menor:
        lado_maior_cm / lado_menor_cm <= 3   (limite inclusivo)

    lado_maior_cm, lado_menor_cm: lados do retângulo circunscrito ao
    pavimento em planta, cm (lado_maior_cm >= lado_menor_cm).
    tem_abertura_grande: True quando o pavimento tem grande abertura na
    laje; nesse caso a função sempre devolve False, qualquer que seja a
    razão entre os lados.

    Faixa: lado_menor_cm > 0; lado_maior_cm >= lado_menor_cm.
    """
    if lado_menor_cm <= 0.0:
        raise FaixaNormativaError(
            f"lado_menor_cm = {lado_menor_cm:g} cm deve ser positivo (14.6.6.4)."
        )
    if lado_maior_cm < lado_menor_cm:
        raise ValueError(
            "lado_maior_cm deve ser >= lado_menor_cm (troque a ordem dos argumentos)."
        )
    if tem_abertura_grande:
        return False
    razao = lado_maior_cm / lado_menor_cm
    return razao <= 3.0 + 1e-9
