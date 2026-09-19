"""ELS de deformação: rigidez equivalente, flecha e limites — ABNT NBR 6118:2026.

Fecha o fluxo do estado-limite de deformação excessiva para vigas e lajes de
concreto armado: momento de fissuração (17.3.1, PDF p. 145), rigidez
equivalente pelo critério de Branson para a flecha imediata (17.3.2.1.1,
PDF p. 146), o coeficiente de fluência para a flecha diferida (17.3.2.1.2,
PDF p. 147-148), os deslocamentos-limites da Tabela 13.3 (13.3, PDF p. 97-99)
e a verificação conjunta (19.3.1, PDF p. 179, que remete lajes aos mesmos
critérios de 17.3.2).

Este módulo é a versão promovida (mais genérica) de duas funções que já
existiam em ``lajes_nbr6118.py`` (``momento_fissuracao``, restrita a seção
retangular e fct,m; ``alpha_f``, sem t0 ponderado por várias cargas) — ver
Seção 3.2, item 4 do plano de implementação. As funções antigas continuam
funcionando como estavam (não foram tocadas: ver observação no retorno do
pacote P8).

Convenções (iguais às do núcleo, ver ``nucleo_nbr6118.py``):
    - fck e tensões em MPa; geometria em cm; momentos em kN.cm; rigidez em
      kN.cm²; deformação em ‰.
    - Fora da faixa de validade, ``FaixaNormativaError`` (nunca um número
      calculado com a fórmula errada).
    - Mensagens ao usuário em português acentuado; identificadores em ASCII.
"""

from __future__ import annotations

import unicodedata
import warnings
from dataclasses import dataclass
from typing import Sequence

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError
AvisoNBR6118 = nbr.AvisoNBR6118


def _chave_categoria(texto: str) -> str:
    """Normaliza um rótulo de categoria/elemento: minúsculas, sem acento,
    com espaço e hífen virando underscore (mantém a separação de palavras,
    ao contrário de ``nucleo_nbr6118._chave``, para rótulos compostos como
    'movimento_lateral_vento')."""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.strip().lower().replace(" ", "_").replace("-", "_")
    while "__" in t:
        t = t.replace("__", "_")
    return t


# ---------------------------------------------------------------------------
# 17.3.1 — Momento de fissuração Mr (PDF p. 145)
# ---------------------------------------------------------------------------
# alfa (fator de forma geométrica): 1,5 retangular; 1,2 T ou duplo T;
# 1,3 I ou T invertido (chaves normalizadas por nucleo_nbr6118._chave).
ALPHA_FORMA_MR = {
    "retangular": 1.5,
    "t": 1.2,
    "duplot": 1.2,
    "tduplo": 1.2,
    "i": 1.3,
    "tinvertido": 1.3,
}


def _fct_kncm2(fck_mpa: float, resistencia: str) -> float:
    """fct em kN/cm², delegando ao núcleo (nunca reimplementa fct,m/fctk,inf).

    resistencia='fctm' -> fct,m (estado-limite de deformação excessiva, uso
    usual em 17.3.2); resistencia='fctk_inf' -> fctk,inf (estado-limite de
    formação de fissuras, 17.3.1, PDF p. 145)."""
    chave = nbr._chave(resistencia)
    if chave == "fctm":
        return nbr.mpa_para_kncm2(nbr.fct_m(fck_mpa))
    if chave in ("fctkinf", "fctinf"):
        return nbr.mpa_para_kncm2(nbr.fctk_inf(fck_mpa))
    raise ValueError(
        f"resistencia deve ser 'fctm' ou 'fctk_inf' (NBR 6118:2026 17.3.1, "
        f"PDF p. 145); recebido {resistencia!r}."
    )


def momento_fissuracao_kncm(
    Ic_cm4: float, yt_cm: float, fck_mpa: float,
    forma: str = "retangular", resistencia: str = "fctm",
) -> float:
    """Momento de fissuração Mr, NBR 6118:2026 17.3.1 (PDF p. 145).

    Mr = alfa * fct * Ic / yt

    alfa = 1,5 (retangular); 1,2 (T ou duplo T); 1,3 (I ou T invertido).
    fct = fctk,inf (estado-limite de formação de fissuras) ou fct,m
    (estado-limite de deformação excessiva — o uso usual em 17.3.2, e o
    default aqui, igual ao que ``lajes_nbr6118.momento_fissuracao`` sempre
    fez).

    Ic_cm4 e yt_cm vêm da geometria bruta real da seção (retangular, T, I ou
    qualquer poligonal — quem chama calcula Ic e yt; esta função não impõe
    seção retangular como a antiga ``lajes_nbr6118.momento_fissuracao``
    fazia). yt_cm é a distância do centroide à fibra mais tracionada.

    Retorna Mr em kN.cm. Levanta ``ValueError`` se Ic_cm4 ou yt_cm não forem
    positivos, ou se `forma`/`resistencia` não forem reconhecidos.
    """
    chave_forma = nbr._chave(forma)
    if chave_forma not in ALPHA_FORMA_MR:
        raise ValueError(
            f"forma deve ser 'retangular', 'T', 'duplo_T', 'I' ou "
            f"'T_invertido' (NBR 6118:2026 17.3.1, PDF p. 145); recebido "
            f"{forma!r}."
        )
    if Ic_cm4 <= 0 or yt_cm <= 0:
        raise ValueError("Ic_cm4 e yt_cm devem ser positivos.")
    alfa = ALPHA_FORMA_MR[chave_forma]
    fct = _fct_kncm2(fck_mpa, resistencia)
    return alfa * fct * Ic_cm4 / yt_cm


# ---------------------------------------------------------------------------
# 17.3.2.1.1 — Rigidez equivalente (Branson) para flecha imediata (PDF p. 146)
# ---------------------------------------------------------------------------
def rigidez_equivalente_kncm2(
    Ecs_kncm2: float, Ic_cm4: float, III_cm4: float,
    Mr_kncm: float, Ma_kncm: float, barras_lisas: bool = False,
) -> float:
    """Rigidez equivalente (EI)eq,t0 para a flecha imediata de vigas de
    concreto armado, NBR 6118:2026 17.3.2.1.1 (PDF p. 146).

    (EI)eq,t0 = Ecs*{(Mr/Ma)^3 * Ic + [1 - (Mr/Ma)^3] * III} <= Ecs*Ic

    Ic_cm4: momento de inércia da seção bruta de concreto.
    III_cm4: momento de inércia da seção fissurada no Estádio II, calculado
    com alfa_e = Es/Ecs (``viga_servico_nbr6118.I_II_retangular`` ou
    ``I_II_secao_T``).
    Mr_kncm: momento de fissuração (``momento_fissuracao_kncm``).
    Ma_kncm: momento fletor na seção crítica do vão considerado, para a
    combinação de ações avaliada nessa avaliação (o máximo no vão para vigas
    biapoiadas/contínuas, ou o momento no apoio para balanços).
    barras_lisas: reduz Mr à metade antes do cálculo — a norma manda reduzir
    o valor de Mr à metade quando a armadura é de barras lisas (17.3.2.1.1,
    PDF p. 146); default False reproduz o comportamento usual (barras de
    alta aderência).

    Ambos Mr_kncm e Ma_kncm entram em módulo (sinal não importa aqui).
    Ma_kncm = 0 (seção sem momento fletor) devolve Ecs*Ic (seção não
    fissurada). Retorna (EI)eq em kN.cm².
    """
    if Ecs_kncm2 <= 0 or Ic_cm4 <= 0:
        raise ValueError("Ecs_kncm2 e Ic_cm4 devem ser positivos.")
    if III_cm4 < 0:
        raise ValueError("III_cm4 não pode ser negativo.")
    Ecs_Ic = Ecs_kncm2 * Ic_cm4
    Mr = abs(Mr_kncm) * (0.5 if barras_lisas else 1.0)
    Ma = abs(Ma_kncm)
    if Ma < 1e-9:
        return Ecs_Ic
    razao3 = (Mr / Ma) ** 3
    ei = Ecs_kncm2 * (razao3 * Ic_cm4 + (1.0 - razao3) * III_cm4)
    return min(ei, Ecs_Ic)


# ---------------------------------------------------------------------------
# 17.3.2.1.2 — Flecha diferida: xi(t), t0 ponderado e alfa_f (PDF p. 147-148)
# ---------------------------------------------------------------------------
def xi_fluencia(t_meses: float) -> float:
    """Coeficiente ξ(t) em função do tempo, NBR 6118:2026 17.3.2.1.2 e
    Tabela 17.1 (PDF p. 147-148).

    xi(t) = 0,68 * (0,996^t) * t^0,32,  para t <= 70 meses;
    xi(t) = 2,                          para t > 70 meses.

    Conferido célula a célula contra a Tabela 17.1: t = 0, 0.5, 1, 2, 3, 4,
    5, 10, 20, 40 e >= 70 meses. t_meses < 0 levanta ``FaixaNormativaError``
    (idade não pode ser negativa).
    """
    t = float(t_meses)
    if t < 0:
        raise FaixaNormativaError(
            "t_meses não pode ser negativo (NBR 6118:2026 Tabela 17.1, "
            "PDF p. 148)."
        )
    if t > 70.0:
        return 2.0
    return 0.68 * (0.996 ** t) * (t ** 0.32)


def t0_ponderado(cargas: Sequence[tuple[float, float]]) -> float:
    """t0 ponderado por várias parcelas de carga de longa duração aplicadas
    em idades diferentes, NBR 6118:2026 17.3.2.1.2 (PDF p. 148).

    t0 = (Σ Pi·t0i) / (Σ Pi)

    cargas: sequência de pares (Pi, t0i_meses); Pi representa as parcelas de
    carga e t0i a idade, em meses, em que cada parcela foi aplicada.
    """
    pares = list(cargas)
    if not pares:
        raise ValueError("cargas não pode ser vazio (17.3.2.1.2, PDF p. 148).")
    soma_p = sum(p for p, _ in pares)
    if abs(soma_p) < 1e-12:
        raise ValueError("A soma das parcelas de carga (ΣPi) não pode ser zero.")
    return sum(p * t0i for p, t0i in pares) / soma_p


def alpha_f(
    t_meses: float,
    t0_meses: float | Sequence[tuple[float, float]] = 1.0,
    rho_linha: float = 0.0,
) -> float:
    """Coeficiente de fluência para a flecha diferida, NBR 6118:2026
    17.3.2.1.2 (PDF p. 147).

    alfa_f = Δξ / (1 + 50·ρ'),  Δξ = ξ(t) - ξ(t0),  ρ' = As'/(b·d)

    t0_meses aceita um único valor (idade, em meses, de aplicação da carga
    de longa duração) ou uma sequência de pares (Pi, t0i_meses) quando há
    parcelas de carga aplicadas em idades diferentes — nesse caso o t0
    ponderado é calculado por ``t0_ponderado`` (mesma página).

    Versão promovida de ``lajes_nbr6118.alpha_f`` (que só aceitava t0 único);
    a antiga continua funcionando sem alteração.
    """
    if rho_linha < 0:
        raise ValueError("rho_linha não pode ser negativo.")
    if isinstance(t0_meses, (int, float)):
        t0 = float(t0_meses)
    else:
        t0 = t0_ponderado(t0_meses)
    return (xi_fluencia(t_meses) - xi_fluencia(t0)) / (1.0 + 50.0 * rho_linha)


def flecha_total(
    f_imediata_qp_cm: float, alpha_f: float,
    f_imediata_comb_adotada_cm: float | None = None,
) -> float:
    """Flecha total, NBR 6118:2026 17.3.2.1.2 (PDF p. 148) e 13.3, Notas 3,
    5 e 6 (PDF p. 99).

    Caso usual (Nota 5: "para determinação da flecha de longa duração,
    adotar a combinação quase permanente"; e a norma, em 17.3.2.1.2, diz
    isso de forma direta: "o valor da flecha total deve ser obtido
    multiplicando a flecha imediata por (1 + alfa_f)"):

        f_total = f_imediata,qp * (1 + alfa_f)

    Caso geral (Nota 3: "o deslocamento total deve ser obtido a partir da
    combinação das ações características ponderadas pelos coeficientes
    definidos na Seção 11"; Nota 6: "deslocamento total é o deslocamento
    considerando todas as ações da combinação adotada pelo projetista para
    esta verificação, acrescido dos efeitos de longa duração"), quando a
    combinação adotada para o deslocamento total não é a quase permanente,
    informe a flecha imediata sob essa combinação em
    f_imediata_comb_adotada_cm; o efeito de longa duração continua vindo da
    quase permanente (Nota 5):

        f_total = f_imediata,comb_adotada + f_imediata,qp * alfa_f
    """
    f_qp = float(f_imediata_qp_cm)
    f_adotada = f_qp if f_imediata_comb_adotada_cm is None else float(f_imediata_comb_adotada_cm)
    return f_adotada + f_qp * float(alpha_f)


# ---------------------------------------------------------------------------
# 13.3, NOTA 1 e NOTA 2 — Vão equivalente (PDF p. 99)
# ---------------------------------------------------------------------------
def vao_equivalente(
    elemento: str, l_cm: float, vao_menor_cm: float | None = None,
) -> float:
    """Vão equivalente para o deslocamento-limite, NBR 6118:2026 13.3,
    NOTA 1 e NOTA 2 (PDF p. 99).

    elemento='balanco': NOTA 1 — vão equivalente = 2 * l_cm, com l_cm sendo
        o comprimento do balanço.
    elemento='laje': NOTA 2 — para elementos de superfície, o valor l é o
        menor vão; l_cm já deve ser esse menor vão (a função devolve sem
        alteração — documenta a regra).
    elemento='laje_parede': NOTA 2, exceção — verificação de parede ou
        divisória sobre laje: interessa a direção na qual a parede se
        desenvolve (l_cm), limitada a duas vezes o menor vão da laje
        (vao_menor_cm, obrigatório neste caso):

            vao_eq = min(l_cm, 2 * vao_menor_cm)
    """
    chave = _chave_categoria(elemento)
    if chave == "balanco":
        return 2.0 * float(l_cm)
    if chave == "laje":
        return float(l_cm)
    if chave in ("laje_parede", "parede_em_laje", "parede"):
        if vao_menor_cm is None:
            raise ValueError(
                "vao_menor_cm é obrigatório para elemento='laje_parede' "
                "(NBR 6118:2026 13.3, NOTA 2, PDF p. 99)."
            )
        return min(float(l_cm), 2.0 * float(vao_menor_cm))
    raise ValueError(
        f"elemento deve ser 'balanco', 'laje' ou 'laje_parede'; recebido "
        f"{elemento!r}."
    )


# ---------------------------------------------------------------------------
# 13.3, Tabela 13.3 — Deslocamentos-limites (PDF p. 97-99)
# ---------------------------------------------------------------------------
TABELA_13_3 = {
    "aceitabilidadevisual": dict(
        tipo="Aceitabilidade sensorial", razao="Visual",
        exemplo="Deslocamentos visíveis em elementos estruturais",
        considerar="Total", regra="l/250", pagina=97),
    "aceitabilidadevibracao": dict(
        tipo="Aceitabilidade sensorial", razao="Outro",
        exemplo="Vibrações sentidas no piso",
        considerar="Devido a cargas variáveis de utilização",
        regra="l/350", pagina=97),
    "drenagem": dict(
        tipo="Efeitos estruturais em serviço",
        razao="Superfícies que devem drenar água",
        exemplo="Coberturas e varandas", considerar="Total",
        regra="l/250 (nota a)", pagina=98),
    "planicidadetotal": dict(
        tipo="Efeitos estruturais em serviço",
        razao="Pavimentos que devem permanecer planos",
        exemplo="Ginásios e pistas de boliche", considerar="Total",
        regra="l/350 + contraflecha, com desvio isolado da contraflecha "
              "<= l/350 (nota b)",
        pagina=98),
    "planicidadeapospiso": dict(
        tipo="Efeitos estruturais em serviço",
        razao="Pavimentos que devem permanecer planos",
        exemplo="Ginásios e pistas de boliche",
        considerar="Ocorrido após a construção do piso",
        regra="l/600", pagina=98),
    "equipamentosensivel": dict(
        tipo="Efeitos estruturais em serviço",
        razao="Elementos que suportam equipamentos sensíveis",
        exemplo="Laboratórios",
        considerar="Ocorrido após nivelamento do equipamento",
        regra="De acordo com recomendação do fabricante do equipamento",
        pagina=98),
    "alvenaria": dict(
        tipo="Efeitos em elementos não estruturais - Paredes",
        razao="Alvenaria, caixilhos e revestimentos",
        exemplo="Alvenaria, caixilhos e revestimentos",
        considerar="Após a construção da parede",
        regra="min(l/500, 10 mm) (nota c)", pagina=98),
    "divisorialeve": dict(
        tipo="Efeitos em elementos não estruturais - Paredes",
        razao="Divisórias leves e caixilhos telescópicos",
        exemplo="Divisórias leves e caixilhos telescópicos",
        considerar="Ocorrido após a instalação da divisória",
        regra="min(l/250, 25 mm) (nota c)", pagina=98),
    "movimentolateralvento": dict(
        tipo="Efeitos em elementos não estruturais - Paredes",
        razao="Movimento lateral de edifícios",
        exemplo="Movimento lateral de edifícios",
        considerar="Provocado pela ação do vento, combinação frequente "
                   "(psi1 = 0,30)",
        regra="H/1700 (deslocamento lateral total) e Hi/850 entre "
              "pavimentos (notas d, e)",
        pagina=98),
    "movimentotermicovertical": dict(
        tipo="Efeitos em elementos não estruturais - Paredes",
        razao="Movimentos térmicos verticais",
        exemplo="Movimentos térmicos verticais",
        considerar="Provocado por diferença de temperatura",
        regra="min(l/400, 15 mm) (nota f)", pagina=98),
    "forrotermicohorizontal": dict(
        tipo="Efeitos em elementos não estruturais - Forros",
        razao="Movimentos térmicos horizontais", exemplo="Forros",
        considerar="Provocado por diferença de temperatura",
        regra="Hi/500", pagina=98),
    "forrorevestimentocolado": dict(
        tipo="Efeitos em elementos não estruturais - Forros",
        razao="Revestimentos colados", exemplo="Forros",
        considerar="Ocorrido após a construção do forro",
        regra="l/350", pagina=98),
    "forrorevestimentopendurado": dict(
        tipo="Efeitos em elementos não estruturais - Forros",
        razao="Revestimentos pendurados ou com juntas", exemplo="Forros",
        considerar="Deslocamento ocorrido após a construção do forro",
        regra="l/175", pagina=98),
    "ponterolante": dict(
        tipo="Efeitos em elementos não estruturais - Pontes rolantes",
        razao="Desalinhamento de trilhos", exemplo="Pontes rolantes",
        considerar="Deslocamento provocado pelas ações decorrentes da "
                   "frenação",
        regra="H/400", pagina=98),
}


def deslocamento_limite(
    categoria: str, vao_cm: float | None = None,
    H_cm: float | None = None, Hi_cm: float | None = None,
    contraflecha_cm: float = 0.0,
) -> tuple[float | None, str]:
    """Deslocamento-limite da Tabela 13.3, NBR 6118:2026 13.3 (PDF p. 97-99).

    categoria (aceita com ou sem underscore/acento — ver as chaves, já
    normalizadas, de TABELA_13_3): 'aceitabilidade_visual',
    'aceitabilidade_vibracao', 'drenagem', 'planicidade_total',
    'planicidade_apos_piso', 'equipamento_sensivel', 'alvenaria',
    'divisoria_leve', 'movimento_lateral_vento', 'movimento_termico_vertical',
    'forro_termico_horizontal', 'forro_revestimento_colado',
    'forro_revestimento_pendurado', 'ponte_rolante'.

    vao_cm segue a Nota 1 (balanços) e a Nota 2 (placas) — ver
    ``vao_equivalente``.

    Devolve (limite_cm, descricao):
      - 'equipamento_sensivel' não tem número definido pela norma: devolve
        (None, texto explicando que vale a recomendação do fabricante);
      - 'movimento_lateral_vento' exige exatamente um entre H_cm
        (deslocamento lateral total do edifício, H/1700) e Hi_cm
        (deslocamento entre pavimentos vizinhos, Hi/850 — nota e);
      - 'ponte_rolante' exige H_cm (H/400); 'forro_termico_horizontal' exige
        Hi_cm (Hi/500);
      - as demais categorias exigem vao_cm; 'planicidade_total' soma
        contraflecha_cm (default 0 — nota b: a atuação isolada da
        contraflecha não pode ocasionar desvio maior que l/350; violar
        essa restrição levanta ``FaixaNormativaError``).
    """
    chave = nbr._chave(categoria)
    if chave not in TABELA_13_3:
        raise ValueError(
            f"categoria desconhecida: {categoria!r}. Use uma das chaves de "
            f"TABELA_13_3 (ex.: 'aceitabilidade_visual', 'alvenaria', "
            f"'movimento_lateral_vento', ...)."
        )
    info = TABELA_13_3[chave]
    descricao = (
        f"{info['tipo']} - {info['razao']} ({info['exemplo']}): "
        f"deslocamento a considerar = {info['considerar']}; "
        f"limite = {info['regra']} (Tabela 13.3, PDF p. {info['pagina']})."
    )

    if chave == "equipamentosensivel":
        return None, descricao

    if chave == "movimentolateralvento":
        if (H_cm is None) == (Hi_cm is None):
            raise ValueError(
                "categoria='movimento_lateral_vento' exige exatamente um "
                "entre H_cm (deslocamento lateral total, H/1700) e Hi_cm "
                "(entre pavimentos vizinhos, Hi/850)."
            )
        if H_cm is not None:
            return float(H_cm) / 1700.0, descricao
        return float(Hi_cm) / 850.0, descricao

    if chave == "ponterolante":
        if H_cm is None:
            raise ValueError("categoria='ponte_rolante' exige H_cm (H/400).")
        return float(H_cm) / 400.0, descricao

    if chave == "forrotermicohorizontal":
        if Hi_cm is None:
            raise ValueError(
                "categoria='forro_termico_horizontal' exige Hi_cm (Hi/500)."
            )
        return float(Hi_cm) / 500.0, descricao

    # Demais categorias usam vao_cm.
    if vao_cm is None:
        raise ValueError(f"categoria={categoria!r} exige vao_cm.")
    l_cm = float(vao_cm)
    if chave in ("aceitabilidadevisual", "drenagem"):
        return l_cm / 250.0, descricao
    if chave == "aceitabilidadevibracao":
        return l_cm / 350.0, descricao
    if chave == "planicidadetotal":
        contraflecha = float(contraflecha_cm)
        limite_contraflecha = l_cm / 350.0
        if contraflecha > limite_contraflecha + 1e-9:
            raise FaixaNormativaError(
                f"contraflecha_cm={contraflecha:g} excede l/350="
                f"{limite_contraflecha:.4f} cm: a NBR 6118:2026 13.3, Tabela "
                f"13.3, NOTA b (PDF p. 99) proíbe que a atuação isolada da "
                f"contraflecha ocasione desvio do plano maior que l/350."
            )
        return l_cm / 350.0 + contraflecha, descricao
    if chave == "planicidadeapospiso":
        return l_cm / 600.0, descricao
    if chave == "alvenaria":
        return min(l_cm / 500.0, 1.0), descricao
    if chave == "divisorialeve":
        return min(l_cm / 250.0, 2.5), descricao
    if chave == "movimentotermicovertical":
        return min(l_cm / 400.0, 1.5), descricao
    if chave == "forrorevestimentocolado":
        return l_cm / 350.0, descricao
    if chave == "forrorevestimentopendurado":
        return l_cm / 175.0, descricao
    raise AssertionError(f"categoria {chave!r} sem regra implementada.")  # inalcançável


# ---------------------------------------------------------------------------
# 19.3.1 — Verificação conjunta, usada por vigas e por lajes (PDF p. 179)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoFlecha:
    f_imediata_cm: float
    alpha_f: float
    f_diferida_cm: float
    f_total_cm: float
    categoria: str
    limite_cm: float | None
    descricao_limite: str
    ok: bool | None
    governante: str
    memoria: tuple[str, ...]


def verificar_flecha(
    f_imediata_qp_cm: float, categoria: str,
    t_meses: float = 70.0,
    t0_meses: float | Sequence[tuple[float, float]] = 1.0,
    rho_linha: float = 0.0,
    vao_cm: float | None = None,
    H_cm: float | None = None, Hi_cm: float | None = None,
    contraflecha_cm: float = 0.0,
    f_imediata_comb_adotada_cm: float | None = None,
) -> ResultadoFlecha:
    """Verifica a flecha de uma viga ou de uma laje contra a Tabela 13.3,
    reunindo 17.3.2 (flecha imediata e diferida) e 13.3 (limites).

    Usada tanto por vigas quanto por lajes: NBR 6118:2026 19.3.1 (PDF p. 179)
    manda usar, para a flecha de lajes, "os critérios dados em 17.3.2,
    considerando a possibilidade de fissuração (Estádio II)" — exatamente o
    que esta função e ``rigidez_equivalente_kncm2`` fazem.

    f_imediata_qp_cm: flecha imediata sob a combinação quase permanente
    (11.8.3.2, P4), já calculada pelo chamador — por exemplo com
    ``lajes_nbr6118.flecha_imediata_duas_direcoes`` para lajes armadas em
    duas direções, ou por integração da curvatura ao longo do vão para
    vigas — usando a rigidez de ``rigidez_equivalente_kncm2`` (Estádio I ou
    II conforme Ma vs Mr).
    Demais parâmetros: ver ``alpha_f``, ``deslocamento_limite`` e
    ``flecha_total``.

    Emite ``AvisoNBR6118`` quando a flecha total excede o limite.
    """
    af = alpha_f(t_meses, t0_meses, rho_linha)
    f_total = flecha_total(f_imediata_qp_cm, af, f_imediata_comb_adotada_cm)
    f_base = (f_imediata_qp_cm if f_imediata_comb_adotada_cm is None
              else f_imediata_comb_adotada_cm)
    f_diferida = f_total - f_base

    limite, descricao = deslocamento_limite(
        categoria, vao_cm=vao_cm, H_cm=H_cm, Hi_cm=Hi_cm,
        contraflecha_cm=contraflecha_cm,
    )

    memoria = [
        f"alfa_f = {af:.4f} (t = {t_meses:g} meses; 17.3.2.1.2, PDF p. 147).",
        f"f_imediata,qp = {float(f_imediata_qp_cm):.4f} cm.",
        f"f_total = {f_total:.4f} cm (17.3.2.1.2 e 13.3, Notas 3, 5 e 6).",
        descricao,
    ]

    if limite is None:
        ok = None
        governante = "sem limite numérico (recomendação do fabricante)"
        memoria.append(
            "Sem limite numérico definido pela norma para esta categoria; "
            "conferir a recomendação do fabricante do equipamento."
        )
    else:
        ok = f_total <= limite + 1e-9
        governante = categoria
        memoria.append(
            f"f_total {'<=' if ok else '>'} limite: {f_total:.4f} cm "
            f"{'<=' if ok else '>'} {limite:.4f} cm -> "
            f"{'ok' if ok else 'não ok'}."
        )
        if not ok:
            warnings.warn(
                f"Flecha total {f_total:.3f} cm excede o limite de "
                f"{limite:.3f} cm da Tabela 13.3 ({categoria}).",
                AvisoNBR6118,
                stacklevel=2,
            )

    return ResultadoFlecha(
        f_imediata_cm=float(f_imediata_qp_cm),
        alpha_f=af,
        f_diferida_cm=f_diferida,
        f_total_cm=f_total,
        categoria=categoria,
        limite_cm=limite,
        descricao_limite=descricao,
        ok=ok,
        governante=governante,
        memoria=tuple(memoria),
    )
