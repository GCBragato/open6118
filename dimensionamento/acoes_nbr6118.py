"""Ações e combinações de ações — ABNT NBR 6118:2026, Seção 11 e 15.3.1.

Modelo de dados de ação (11.2.2), coeficientes de ponderação (11.7, Tabelas
11.1 e 11.2), valores representativos e de cálculo (11.6.2 e 11.6.3),
combinações últimas (11.8.2, Tabela 11.3), combinações de serviço (11.8.3,
Tabela 11.4), a formulação de segurança da 2ª ordem (15.3.1), a ação da água
(11.4.1.3) e as variações de temperatura (11.4.2).

Norma: ABNT NBR 6118:2026. As páginas citadas são as do PDF (a página impressa
é 18 a menos).

Unidades: a combinação não converte unidade. ``Fk`` é o valor característico
da ação ou do efeito dela (força em kN, momento em kN·cm, tensão...), e ``Fd``
sai na mesma unidade. Todas as ações de uma combinação têm de estar na mesma
unidade e se referir ao mesmo efeito (o mesmo esforço na mesma seção), com
sinal.

Parâmetro configurável: o γg das ações permanentes diretas na combinação
normal é ``nucleo_nbr6118.GAMA_G`` (padrão 1,4), lido na hora da chamada. Quando
a obra se enquadrar na nota a da Tabela 11.1 (ações permanentes de pequena
variabilidade, critério da NBR 8681), o script muda no começo::

    import nucleo_nbr6118 as nbr
    nbr.GAMA_G = 1.3

As funções também aceitam ``gama_g`` explícito, e a memória de cálculo registra
o valor usado.

Favorável e desfavorável: cada ação tem o campo ``favoravel``. Com ``None`` (o
padrão), a combinação decide pelo sinal do valor característico e pelo
``sentido`` pedido: com ``sentido='max'`` a ação de ``Fk`` negativo é
favorável; com ``sentido='min'``, a de ``Fk`` positivo. A ação permanente
favorável usa ``Fk_inf`` quando ele existe (valor característico inferior,
11.6.1.1; para a protensão, Pk,mín da Tabela 11.3). A ação variável favorável
não entra na combinação: a Tabela 11.1 só dá coeficiente de ação variável
desfavorável, e a NBR 8681 manda considerar a ação variável só quando ela é
desfavorável.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

try:
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError

# ---------------------------------------------------------------------------
# 11.2.2 — Classificação das ações (PDF p. 76)
# ---------------------------------------------------------------------------
NATUREZAS = (
    "permanente_direta",
    "permanente_indireta",
    "variavel_direta",
    "variavel_indireta",
    "excepcional",
)

# Coluna da Tabela 11.1 que cada natureza pode usar.
TIPOS_POR_NATUREZA = {
    "permanente_direta": ("permanente",),
    "permanente_indireta": ("protensao", "recalque_retracao"),
    "variavel_direta": ("variavel",),
    "variavel_indireta": ("temperatura",),
    "excepcional": ("excepcional",),
}

_ALIAS_NATUREZA = {
    "permanentedireta": "permanente_direta",
    "permanenteindireta": "permanente_indireta",
    "variaveldireta": "variavel_direta",
    "variavelindireta": "variavel_indireta",
    "excepcional": "excepcional",
}

_ALIAS_TIPO = {
    "permanente": "permanente", "g": "permanente",
    "variavel": "variavel", "q": "variavel",
    "temperatura": "temperatura", "t": "temperatura",
    "protensao": "protensao", "p": "protensao",
    "recalqueretracao": "recalque_retracao", "recalque": "recalque_retracao",
    "retracao": "recalque_retracao", "fluencia": "recalque_retracao",
    "recalquedeapoioeretracao": "recalque_retracao",
    "excepcional": "excepcional",
}

# ---------------------------------------------------------------------------
# 11.7.1 — Tabela 11.1: coeficiente γf = γf1·γf3 (PDF p. 85)
# D = desfavorável, F = favorável, G = cargas variáveis em geral, T = temperatura.
# ---------------------------------------------------------------------------
TABELA_11_1 = {
    "normal": {
        "permanente": {"D": 1.4, "F": 1.0},          # D = 1,4 com a nota a
        "variavel": {"G": 1.4, "T": 1.2},
        "protensao": {"D": 1.2, "F": 0.9},
        "recalque_retracao": {"D": 1.2, "F": 0.0},
    },
    "especial_construcao": {
        "permanente": {"D": 1.3, "F": 1.0},
        "variavel": {"G": 1.2, "T": 1.0},
        "protensao": {"D": 1.2, "F": 0.9},
        "recalque_retracao": {"D": 1.2, "F": 0.0},
    },
    "excepcional": {
        "permanente": {"D": 1.2, "F": 1.0},
        "variavel": {"G": 1.0, "T": 0.0},
        "protensao": {"D": 1.2, "F": 0.9},
        "recalque_retracao": {"D": 0.0, "F": 0.0},
    },
}

GAMA_G_NOTA_A_MIN = 1.3   # Tabela 11.1, nota a: γg pode ser reduzido para 1,3

_ALIAS_COMBINACAO_ULTIMA = {
    "normal": "normal", "normais": "normal",
    "especial": "especial_construcao", "especiais": "especial_construcao",
    "construcao": "especial_construcao", "deconstrucao": "especial_construcao",
    "especialconstrucao": "especial_construcao",
    "especialoudeconstrucao": "especial_construcao",
    "especiaisoudeconstrucao": "especial_construcao",
    "excepcional": "excepcional", "excepcionais": "excepcional",
}

# ---------------------------------------------------------------------------
# 11.7.1 — Tabela 11.2: valores do coeficiente γf2 = (ψ0, ψ1, ψ2) (PDF p. 85)
# ---------------------------------------------------------------------------
TABELA_11_2_PSI = {
    # Cargas de utilização de edificações
    "sem_predominancia": (0.5, 0.4, 0.3),                   # nota b
    "com_predominancia": (0.7, 0.6, 0.4),                   # nota c
    "biblioteca_arquivo_oficina_garagem": (0.8, 0.7, 0.6),
    # Pressão dinâmica do vento nas estruturas em geral
    "vento": (0.6, 0.3, 0.0),
    # Variações uniformes de temperatura em relação à média anual local
    "temperatura": (0.6, 0.5, 0.3),
}

_ALIAS_PSI = {
    "sempredominancia": "sem_predominancia", "residencial": "sem_predominancia",
    "hospedagem": "sem_predominancia", "acessorestrito": "sem_predominancia",
    "compredominancia": "com_predominancia", "comercial": "com_predominancia",
    "escritorio": "com_predominancia", "escritorios": "com_predominancia",
    "loja": "com_predominancia", "lojas": "com_predominancia",
    "estacaodepassageiros": "com_predominancia",
    "edificiopublico": "com_predominancia", "edificiospublicos": "com_predominancia",
    "acessopublico": "com_predominancia",
    "bibliotecaarquivooficinagaragem": "biblioteca_arquivo_oficina_garagem",
    "biblioteca": "biblioteca_arquivo_oficina_garagem",
    "arquivo": "biblioteca_arquivo_oficina_garagem",
    "arquivos": "biblioteca_arquivo_oficina_garagem",
    "oficina": "biblioteca_arquivo_oficina_garagem",
    "oficinas": "biblioteca_arquivo_oficina_garagem",
    "garagem": "biblioteca_arquivo_oficina_garagem",
    "garagens": "biblioteca_arquivo_oficina_garagem",
    "vento": "vento",
    "temperatura": "temperatura",
}

# ---------------------------------------------------------------------------
# 11.7 — Decomposição γf = γf1·γf2·γf3 (PDF p. 84) e 15.3.1 (PDF p. 121)
# ---------------------------------------------------------------------------
# A norma não tabela γf1 e γf2·γf3 em separado: a Tabela 11.1 dá o produto
# γf1·γf3, a Tabela 11.2 dá γf2 e 15.3.1 fixa γf3 = 1,1.
GAMA_F3 = nbr.GAMA_F3          # 15.3.1 — γf3 = 1,1
GAMA_F2_PRINCIPAL = 1.0        # 11.6.2 a) — a ação principal entra com o valor característico

# 11.4.1.3 — ação da água (PDF p. 82)
GAMA_F_AGUA = 1.2              # γf = γf3 = 1,2

# 11.4.2 — temperatura (PDF p. 82-83)
TEMPERATURA_UNIFORME_ATE_50CM_C = (10.0, 15.0)     # 11.4.2.1 a)
TEMPERATURA_UNIFORME_ACIMA_70CM_C = (5.0, 10.0)    # 11.4.2.1 b)
DIMENSAO_LIMITE_INFERIOR_CM = 50.0
DIMENSAO_LIMITE_SUPERIOR_CM = 70.0
GRADIENTE_TERMICO_MIN_C = 5.0                      # 11.4.2.2

_TOL = 1e-9


def _fmt(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


def _normalizar(valor: str, aliases: dict, o_que: str, opcoes: Iterable[str]) -> str:
    chave = nbr._chave(valor)
    if chave not in aliases:
        raise ValueError(f"{o_que} desconhecido(a): {valor!r}. Use {', '.join(repr(o) for o in opcoes)}.")
    return aliases[chave]


def _psi_de(categoria) -> tuple[float, float, float]:
    """(ψ0, ψ1, ψ2) de uma categoria da Tabela 11.2 ou de uma tupla explícita."""
    if isinstance(categoria, str):
        return TABELA_11_2_PSI[_normalizar(categoria, _ALIAS_PSI, "Categoria de ψ",
                                           TABELA_11_2_PSI)]
    try:
        valores = tuple(float(v) for v in categoria)
    except TypeError:
        raise ValueError(
            f"categoria_psi inválida: {categoria!r}. Use uma categoria da Tabela 11.2 "
            "ou a tupla (ψ0, ψ1, ψ2).") from None
    if len(valores) != 3:
        raise ValueError("categoria_psi explícita tem de ser a tupla (ψ0, ψ1, ψ2).")
    if any(not (0.0 <= v <= 1.0) for v in valores):
        raise FaixaNormativaError(
            f"ψ = {valores} fora do intervalo de 0 a 1 dos fatores de redução.")
    return valores


# ---------------------------------------------------------------------------
# Modelo de dados — 11.2.2 (PDF p. 76), 11.5 (PDF p. 83), 11.6 (PDF p. 83-84)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Acao:
    """Ação classificada conforme 11.2.2 (NBR 6118:2026, p. 76) e a NBR 8681.

    Campos:
        nome: rótulo da ação na memória de cálculo.
        natureza: 'permanente_direta', 'permanente_indireta', 'variavel_direta',
            'variavel_indireta' ou 'excepcional' (11.2.2 e 11.5).
        tipo: coluna da Tabela 11.1 — 'permanente' (g), 'variavel' (q, cargas
            em geral G), 'temperatura' (T), 'protensao' (p),
            'recalque_retracao' (recalques de apoio, retração e fluência) ou
            'excepcional'. Tem de ser compatível com a natureza.
        Fk: valor característico (11.6.1), ou o valor convencional
            excepcional arbitrado (11.6.2 b) para a ação excepcional. Na
            protensão é Pk,máx (Tabela 11.3).
        Fk_inf: valor característico inferior da ação permanente, usado
            quando ela é favorável (11.6.1.1); na protensão, Pk,mín. Sem ele,
            usa-se Fk.
        categoria_psi: categoria da Tabela 11.2 ('sem_predominancia',
            'com_predominancia', 'biblioteca_arquivo_oficina_garagem',
            'vento', 'temperatura') ou a tupla explícita (ψ0, ψ1, ψ2).
            Obrigatória na ação variável, exceto na temperatura, que assume
            'temperatura'.
        favoravel: None decide pelo sinal na combinação; True ou False fixa.
        gama_f_desfavoravel: γf imposto à ação desfavorável no ELU, no lugar
            da Tabela 11.1 (a água de 11.4.1.3 usa 1,2; a nota a da Tabela
            11.1 manda ponderar as demais permanentes pela NBR 8681 quando
            γg = 1,3).
    """

    nome: str
    natureza: str
    tipo: str
    Fk: float
    Fk_inf: float | None = None
    categoria_psi: object = None
    favoravel: bool | None = None
    gama_f_desfavoravel: float | None = None

    def __post_init__(self):
        natureza = _normalizar(self.natureza, _ALIAS_NATUREZA, "Natureza de ação", NATUREZAS)
        tipo = _normalizar(self.tipo, _ALIAS_TIPO, "Tipo de ação",
                           ("permanente", "variavel", "temperatura", "protensao",
                            "recalque_retracao", "excepcional"))
        if tipo not in TIPOS_POR_NATUREZA[natureza]:
            raise ValueError(
                f"Ação {self.nome!r}: tipo {tipo!r} incompatível com a natureza {natureza!r} "
                f"(use {', '.join(repr(t) for t in TIPOS_POR_NATUREZA[natureza])}).")
        object.__setattr__(self, "natureza", natureza)
        object.__setattr__(self, "tipo", tipo)
        object.__setattr__(self, "Fk", float(self.Fk))
        if self.Fk_inf is not None:
            if not natureza.startswith("permanente"):
                raise ValueError(
                    f"Ação {self.nome!r}: Fk_inf só se aplica a ação permanente (11.6.1.1).")
            object.__setattr__(self, "Fk_inf", float(self.Fk_inf))
        categoria = self.categoria_psi
        if natureza.startswith("variavel"):
            if categoria is None:
                if tipo == "temperatura":
                    categoria = "temperatura"
                else:
                    raise ValueError(
                        f"Ação variável {self.nome!r} sem categoria_psi: informe a categoria "
                        "da Tabela 11.2 ou a tupla (ψ0, ψ1, ψ2).")
            _psi_de(categoria)   # valida já na criação
            object.__setattr__(self, "categoria_psi", categoria)
        if self.gama_f_desfavoravel is not None:
            g = float(self.gama_f_desfavoravel)
            if g < 0.0:
                raise ValueError(f"Ação {self.nome!r}: γf negativo ({g:g}).")
            object.__setattr__(self, "gama_f_desfavoravel", g)

    @property
    def permanente(self) -> bool:
        return self.natureza.startswith("permanente")

    @property
    def variavel(self) -> bool:
        return self.natureza.startswith("variavel")

    @property
    def excepcional(self) -> bool:
        return self.natureza == "excepcional"

    @property
    def psi(self) -> tuple[float, float, float]:
        """(ψ0, ψ1, ψ2) da ação variável (Tabela 11.2)."""
        if not self.variavel:
            raise FaixaNormativaError(
                f"Ação {self.nome!r} não é variável: a Tabela 11.2 só dá ψ para ação variável.")
        return _psi_de(self.categoria_psi)


def classificar_acao(acao: Acao) -> str:
    """Classificação da ação conforme 11.2.2 (p. 76): 'permanente', 'variavel' ou 'excepcional'."""
    if acao.permanente:
        return "permanente"
    if acao.variavel:
        return "variavel"
    return "excepcional"


# ---------------------------------------------------------------------------
# 11.7.1 — Tabelas 11.1 e 11.2 (PDF p. 85)
# ---------------------------------------------------------------------------
def normalizar_combinacao_ultima(combinacao: str) -> str:
    """'normal', 'especial_construcao' ou 'excepcional' (linhas da Tabela 11.1)."""
    return _normalizar(combinacao, _ALIAS_COMBINACAO_ULTIMA, "Combinação última",
                       ("normal", "especial", "construcao", "excepcional"))


def gama_g_configurado(gama_g: float | None = None) -> float:
    """γg das ações permanentes diretas desfavoráveis na combinação normal (Tabela 11.1, nota a).

    Sem argumento, lê ``nucleo_nbr6118.GAMA_G`` na hora da chamada (padrão 1,4).
    A nota a permite reduzir para 1,3 nas ações permanentes de pequena
    variabilidade; a biblioteca não decide se a obra se enquadra (o critério é
    da NBR 8681). Fora de 1,3 a 1,4 levanta ``FaixaNormativaError``. PDF p. 85.
    """
    g = float(nbr.GAMA_G if gama_g is None else gama_g)
    if not (GAMA_G_NOTA_A_MIN - _TOL <= g <= TABELA_11_1["normal"]["permanente"]["D"] + _TOL):
        raise FaixaNormativaError(
            f"γg = {_fmt(g)} fora da Tabela 11.1: o valor é 1,4, reduzido até 1,3 pela nota a.")
    return g


def gama_f_tabela_11_1(combinacao: str, coluna: str, sub: str,
                       gama_g: float | None = None) -> float:
    """Célula da Tabela 11.1 (γf = γf1·γf3), NBR 6118:2026, 11.7.1, p. 85.

    combinacao: 'normal', 'especial'/'construcao' ou 'excepcional'.
    coluna: 'permanente', 'variavel', 'protensao' ou 'recalque_retracao'.
    sub: 'D' ou 'F' (desfavorável e favorável) nas permanentes, na protensão e
    nos recalques; 'G' (cargas em geral) ou 'T' (temperatura) nas variáveis.
    Na célula normal × permanente × D devolve o γg configurado (nota a).
    """
    linha = TABELA_11_1[normalizar_combinacao_ultima(combinacao)]
    col = _normalizar(coluna, {**_ALIAS_TIPO, "temperatura": "variavel", "t": "variavel"},
                      "Coluna da Tabela 11.1", tuple(TABELA_11_1["normal"]))
    if col not in linha:
        raise ValueError(f"A Tabela 11.1 não tem a coluna {coluna!r}.")
    s = str(sub).strip().upper()
    if s not in linha[col]:
        raise ValueError(
            f"A coluna {col!r} da Tabela 11.1 tem as subcolunas {', '.join(linha[col])}, não {sub!r}.")
    if linha is TABELA_11_1["normal"] and col == "permanente" and s == "D":
        return gama_g_configurado(gama_g)
    return linha[col][s]


def gama_f(acao: Acao, combinacao: str, favoravel: bool,
           gama_g: float | None = None) -> float:
    """Coeficiente γf = γf1·γf3 da ação na combinação última (Tabela 11.1, p. 85).

    - permanente direta: coluna g (D ou F); na combinação normal, D = γg de
      ``nucleo_nbr6118.GAMA_G`` (1,4, ou 1,3 pela nota a) ou do argumento;
    - protensão: coluna p (D ou F);
    - recalque de apoio, retração e fluência: coluna de recalques (D ou F);
    - variável direta: coluna G; temperatura: coluna T. A ação variável
      favorável devolve 0 (não entra na combinação; ver a docstring do módulo);
    - excepcional: 1,0 na combinação excepcional (Fq1exc entra com o valor
      representativo, Tabela 11.3); em outra combinação levanta
      ``FaixaNormativaError``;
    - com ``acao.gama_f_desfavoravel`` (água, 11.4.1.3), a ação desfavorável
      usa esse valor em qualquer combinação última.
    """
    comb = normalizar_combinacao_ultima(combinacao)
    if acao.excepcional:
        if comb != "excepcional":
            raise FaixaNormativaError(
                f"A ação excepcional {acao.nome!r} só entra na combinação última excepcional "
                "(11.8.2.3, Tabela 11.3).")
        return 1.0
    if not favoravel and acao.gama_f_desfavoravel is not None:
        return acao.gama_f_desfavoravel
    if acao.variavel:
        if favoravel:
            return 0.0
        return TABELA_11_1[comb]["variavel"]["T" if acao.tipo == "temperatura" else "G"]
    return gama_f_tabela_11_1(comb, acao.tipo, "F" if favoravel else "D", gama_g)


def psi(categoria) -> tuple[float, float, float]:
    """(ψ0, ψ1, ψ2) da Tabela 11.2 (γf2), NBR 6118:2026, 11.7.1, p. 85.

    Categorias: 'sem_predominancia' (residencial, hospedagem, acesso restrito —
    nota b), 'com_predominancia' (comercial, escritórios, lojas, estações,
    edifícios públicos, acesso público — nota c),
    'biblioteca_arquivo_oficina_garagem', 'vento' e 'temperatura'. Aceita os
    apelidos entre parênteses e a tupla explícita (ψ0, ψ1, ψ2). Para ψ1 de
    pontes e fadiga, ver a Seção 23 (nota a).
    """
    return _psi_de(categoria)


def gama_f_composto(gama_f1: float, gama_f2: float, gama_f3: float) -> float:
    """γf = γf1·γf2·γf3 (11.7, p. 84)."""
    for nome, v in (("γf1", gama_f1), ("γf2", gama_f2), ("γf3", gama_f3)):
        if v < 0.0:
            raise ValueError(f"{nome} negativo ({v:g}).")
    return float(gama_f1) * float(gama_f2) * float(gama_f3)


def gama_f1(gama_f1_f3: float, gama_f3: float | None = None) -> float:
    """γf1 = (γf1·γf3)/γf3, com γf1·γf3 da Tabela 11.1 e γf3 = 1,1 de 15.3.1 (p. 84 e 121)."""
    g3 = float(GAMA_F3 if gama_f3 is None else gama_f3)
    if g3 <= 0.0:
        raise ValueError(f"γf3 tem de ser positivo ({g3:g}).")
    return float(gama_f1_f3) / g3


def gama_f_els(tipo: str, categoria=None) -> float:
    """γf = γf2 no ELS (11.7.2, p. 86): 1 na rara, ψ1 na frequente, ψ2 na quase permanente.

    ``categoria`` é a categoria da Tabela 11.2 (ou a tupla (ψ0, ψ1, ψ2)),
    obrigatória na frequente e na quase permanente.
    """
    t = _normalizar_servico(tipo)
    if t == "rara":
        return 1.0
    if categoria is None:
        raise ValueError(f"Combinação {t}: informe a categoria da Tabela 11.2 para obter ψ.")
    p0, p1, p2 = _psi_de(categoria)
    return p1 if t == "frequente" else p2


# ---------------------------------------------------------------------------
# 11.6.2 e 11.6.3 — valores representativos e de cálculo (PDF p. 84)
# ---------------------------------------------------------------------------
_ALIAS_REPRESENTATIVO = {
    "caracteristico": "caracteristico", "fk": "caracteristico",
    "caracteristicoinferior": "caracteristico_inferior",
    "excepcional": "excepcional", "convencionalexcepcional": "excepcional",
    "combinacao": "combinacao", "psi0": "combinacao", "reduzidodecombinacao": "combinacao",
    "frequente": "frequente", "psi1": "frequente",
    "quasepermanente": "quase_permanente", "psi2": "quase_permanente",
}


def valor_representativo(acao: Acao, tipo: str = "caracteristico") -> float:
    """Valor representativo da ação (11.6.2, p. 84).

    tipo:
        'caracteristico' — Fk (11.6.2 a);
        'caracteristico_inferior' — Fk,inf da ação permanente (11.6.1.1),
            ou Fk se ele não foi dado;
        'excepcional' — valor convencional excepcional arbitrado (11.6.2 b),
            só para ação excepcional;
        'combinacao' — ψ0·Fk (ELU, ação que acompanha a principal);
        'frequente' — ψ1·Fk (ELS);
        'quase_permanente' — ψ2·Fk (ELS).
    Os valores reduzidos só existem para ação variável; nos demais casos
    levanta ``FaixaNormativaError``.
    """
    t = _normalizar(tipo, _ALIAS_REPRESENTATIVO, "Valor representativo",
                    ("caracteristico", "caracteristico_inferior", "excepcional",
                     "combinacao", "frequente", "quase_permanente"))
    if t == "caracteristico":
        return acao.Fk
    if t == "caracteristico_inferior":
        if not acao.permanente:
            raise FaixaNormativaError(
                f"Ação {acao.nome!r}: o valor característico inferior é da ação permanente (11.6.1.1).")
        return acao.Fk if acao.Fk_inf is None else acao.Fk_inf
    if t == "excepcional":
        if not acao.excepcional:
            raise FaixaNormativaError(
                f"Ação {acao.nome!r} não é excepcional: o valor convencional excepcional "
                "é só da ação excepcional (11.6.2 b).")
        return acao.Fk
    if not acao.variavel:
        raise FaixaNormativaError(
            f"Ação {acao.nome!r}: a norma define valores reduzidos (ψ0, ψ1, ψ2) só para "
            "ação variável (11.6.2 c).")
    p0, p1, p2 = acao.psi
    return {"combinacao": p0, "frequente": p1, "quase_permanente": p2}[t] * acao.Fk


def valor_calculo(F: float, gama: float) -> float:
    """Fd = γf·Frep (11.6.3, p. 84). γf não pode ser negativo."""
    if gama < 0.0:
        raise ValueError(f"γf negativo ({gama:g}).")
    return float(gama) * float(F)


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Parcela:
    """Uma parcela da combinação: valor = gama·psi·F."""

    nome: str
    natureza: str
    papel: str            # 'permanente', 'principal', 'secundaria', 'excepcional', 'excluida'
    favoravel: bool
    gama: float
    psi: float
    F: float              # valor característico usado (Fk ou Fk_inf)
    valor: float


@dataclass(frozen=True)
class ResultadoCombinacao:
    """Resultado de uma combinação de ações (Tabelas 11.3 e 11.4).

    ``Fd`` é o valor governante (o maior com ``sentido='max'``, o menor com
    ``'min'``); ``principal`` é a ação principal dele e ``governante`` repete
    esse nome para o memorial. ``alternativas`` guarda (principal, Fd) de
    cada combinação varrida. ``gama_g`` é o γg aplicado às permanentes diretas
    desfavoráveis (1,0 no ELS).

    Não há campo ``ok``: a combinação de ações só calcula o valor de cálculo
    Fd, não compara nada com limite, então não existe passa/não passa. A
    verificação fica com quem usa Fd (convenção 3.3 do plano, que vale para
    resultados de verificação e dimensionamento).
    """

    estado: str           # 'ELU' ou 'ELS'
    tipo: str
    sentido: str
    Fd: float
    principal: str
    gama_g: float
    parcelas: tuple[Parcela, ...]
    alternativas: tuple[tuple[str, float], ...]
    governante: str
    memoria: tuple[str, ...]


@dataclass(frozen=True)
class ResultadoSdTot:
    """Formulação de segurança da 2ª ordem, Sd,tot = γf3·S(F) (15.3.1).

    Sem campo ``ok`` pelo mesmo motivo de ``ResultadoCombinacao``: Sd,tot é
    um esforço solicitante, e a comparação com a capacidade resistente é da
    Seção 17.
    """

    F: float              # carga majorada de γf/γf3, a aplicar na análise de 2ª ordem
    S_F: float            # efeito S(F) devolvido pela análise
    gama_f3: float
    Sd_tot: float
    principal: str
    alternativas: tuple[tuple[str, float], ...]
    governante: str
    memoria: tuple[str, ...]


# ---------------------------------------------------------------------------
# Motor comum das combinações
# ---------------------------------------------------------------------------
_SENTIDOS = ("max", "min")


def _validar_sentido(sentido: str) -> str:
    s = str(sentido).strip().lower()
    if s not in _SENTIDOS:
        raise ValueError(f"sentido tem de ser 'max' ou 'min', não {sentido!r}.")
    return s


def _eh_favoravel(acao: Acao, sentido: str) -> bool:
    if acao.favoravel is not None:
        return bool(acao.favoravel)
    return acao.Fk < 0.0 if sentido == "max" else acao.Fk > 0.0


def _rotulo_natureza(acao: Acao) -> str:
    return {
        "permanente_direta": "permanente direta",
        "permanente_indireta": "permanente indireta",
        "variavel_direta": "variável direta",
        "variavel_indireta": "variável indireta",
        "excepcional": "excepcional",
    }[acao.natureza]


def _achar_principal(acoes: Sequence[Acao], principal) -> Acao:
    if isinstance(principal, Acao):
        for a in acoes:
            if a is principal:
                return a
        for a in acoes:
            if a == principal:
                return a
        raise ValueError(f"A ação principal {principal.nome!r} não está na lista de ações.")
    achadas = [a for a in acoes if a.nome == principal]
    if not achadas:
        raise ValueError(f"Não há ação chamada {principal!r} na lista.")
    if len(achadas) > 1:
        raise ValueError(f"Há mais de uma ação chamada {principal!r}; passe o objeto Acao.")
    return achadas[0]


def _validar_acoes(acoes) -> tuple[Acao, ...]:
    acoes = tuple(acoes)
    if not acoes:
        raise ValueError("A combinação precisa de pelo menos uma ação.")
    for a in acoes:
        if not isinstance(a, Acao):
            raise TypeError(f"Esperava Acao, recebeu {type(a).__name__}.")
    return acoes


def _parcela(acao, papel, favoravel, gama, psi_, F):
    return Parcela(acao.nome, acao.natureza, papel, favoravel, gama, psi_, F, gama * psi_ * F)


def _linha_parcela(p: Parcela) -> str:
    estado = "favorável" if p.favoravel else "desfavorável"
    if p.papel == "excluida":
        return f"  {p.nome} ({estado}): não entra na combinação."
    papel = {"permanente": "permanente", "principal": "variável principal",
             "secundaria": "variável secundária", "excepcional": "excepcional"}[p.papel]
    termos = [_fmt(p.gama)]
    if p.psi != 1.0:
        termos.append(_fmt(p.psi))
    termos.append(_fmt(p.F))
    return f"  {p.nome} ({papel}, {estado}): {' × '.join(termos)} = {_fmt(p.valor)}"


def _combinar_elu(acoes, comb, principal, sentido, gama_g, psi2_nota_b):
    parcelas = []
    for a in acoes:
        fav = _eh_favoravel(a, sentido)
        if a.permanente:
            F = a.Fk_inf if (fav and a.Fk_inf is not None) else a.Fk
            parcelas.append(_parcela(a, "permanente", fav, gama_f(a, comb, fav, gama_g), 1.0, F))
        elif a.excepcional:
            if comb == "excepcional" and a is principal:
                parcelas.append(_parcela(a, "excepcional", fav, 1.0, 1.0, a.Fk))
            else:
                parcelas.append(_parcela(a, "excluida", fav, 0.0, 0.0, a.Fk))
        else:  # variável
            if fav:
                parcelas.append(_parcela(a, "excluida", fav, 0.0, 0.0, a.Fk))
                continue
            g = gama_f(a, comb, False, gama_g)
            if a is principal and comb != "excepcional":
                parcelas.append(_parcela(a, "principal", fav, g, 1.0, a.Fk))
            else:
                p0, _, p2 = a.psi
                reduz = p2 if (psi2_nota_b and a.natureza == "variavel_direta") else p0
                parcelas.append(_parcela(a, "secundaria", fav, g, reduz, a.Fk))
    return sum(p.valor for p in parcelas), tuple(parcelas)


def _escolher(alternativas, sentido):
    chave = (lambda it: it[1]) if sentido == "max" else (lambda it: -it[1])
    return max(alternativas, key=chave)


# ---------------------------------------------------------------------------
# 11.8.2 — Combinações últimas, Tabela 11.3 (PDF p. 86-88)
# ---------------------------------------------------------------------------
_FORMULA_ELU = {
    "normal": "Fd = γg·Fgk + γεg·Fεgk + γq·(Fq1k + Σψ0j·Fqjk) + γεq·ψ0ε·Fεqk",
    "especial_construcao": "Fd = γg·Fgk + γεg·Fεgk + γq·(Fq1k + Σψ0j·Fqjk) + γεq·ψ0ε·Fεqk",
    "excepcional": "Fd = γg·Fgk + γεg·Fεgk + Fq1exc + γq·Σψ0j·Fqjk + γεq·ψ0ε·Fεqk",
}
_TITULO_ELU = {
    "normal": "Combinação última normal — NBR 6118:2026, 11.8.2.1 e Tabela 11.3 (p. 87).",
    "especial_construcao": ("Combinação última especial ou de construção — NBR 6118:2026, "
                            "11.8.2.2 e Tabela 11.3 (p. 87)."),
    "excepcional": "Combinação última excepcional — NBR 6118:2026, 11.5, 11.8.2.3 e Tabela 11.3 (p. 87).",
}


def combinacao_ultima(acoes: Iterable[Acao], tipo: str = "normal", principal=None,
                      sentido: str = "max", gama_g: float | None = None,
                      psi2_nota_b: bool = False) -> ResultadoCombinacao:
    """Combinação última de ações, 11.8.2.1 a 11.8.2.3 e Tabela 11.3 (p. 87-88).

    Normal e especial ou de construção:
        Fd = γg·Fgk + γεg·Fεgk + γq·(Fq1k + Σψ0j·Fqjk) + γεq·ψ0ε·Fεqk
    Excepcional:
        Fd = γg·Fgk + γεg·Fεgk + Fq1exc + γq·Σψ0j·Fqjk + γεq·ψ0ε·Fεqk
    com γ da Tabela 11.1 (linha da combinação) e ψ da Tabela 11.2.

    tipo: 'normal', 'especial', 'construcao' ou 'excepcional'.
    principal: nome ou objeto da ação principal — ação variável direta nas
        combinações normal e especial (a Tabela 11.3 escolhe Fq1k entre as
        variáveis diretas; a temperatura entra sempre reduzida por ψ0ε) e
        ação excepcional na excepcional. Com None, a função varre todas as
        candidatas desfavoráveis e devolve a que governa.
    sentido: 'max' procura o maior Fd; 'min', o menor (ver favorável e
        desfavorável na docstring do módulo).
    gama_g: γg das permanentes diretas na combinação normal; None lê
        ``nucleo_nbr6118.GAMA_G`` (padrão 1,4; 1,3 pela nota a).
    psi2_nota_b: nota b da Tabela 11.3 — nas combinações especial, de
        construção e excepcional, troca ψ0j por ψ2j das variáveis diretas
        (Fq1k ou Fq1exc de duração muito curta, como sismo e incêndio).

    A ação excepcional (11.5) tem o valor definido por norma específica e
    entra só na combinação excepcional, uma de cada vez. A combinação de perda
    de equilíbrio como corpo rígido e a protensão como carregamento externo
    (Tabela 11.3, concreto protendido) usam o mesmo motor: a protensão é uma
    ação 'permanente_indireta' de tipo 'protensao', com Fk = Pk,máx e
    Fk_inf = Pk,mín.
    """
    acoes = _validar_acoes(acoes)
    comb = normalizar_combinacao_ultima(tipo)
    sentido = _validar_sentido(sentido)
    if psi2_nota_b and comb == "normal":
        raise ValueError("A nota b da Tabela 11.3 (ψ0j → ψ2j) não se aplica à combinação normal.")
    g_g = gama_g_configurado(gama_g)

    if comb == "excepcional":
        candidatas = [a for a in acoes if a.excepcional and not _eh_favoravel(a, sentido)]
    else:
        candidatas = [a for a in acoes if a.natureza == "variavel_direta"
                      and not _eh_favoravel(a, sentido)]
    if principal is not None:
        p = _achar_principal(acoes, principal)
        if comb == "excepcional" and not p.excepcional:
            raise FaixaNormativaError(
                f"Na combinação excepcional a ação principal é a excepcional (Fq1exc); "
                f"{p.nome!r} não é.")
        if comb != "excepcional" and p.natureza != "variavel_direta":
            raise FaixaNormativaError(
                f"A Tabela 11.3 toma Fq1k entre as ações variáveis diretas; {p.nome!r} é "
                f"{_rotulo_natureza(p)}.")
        candidatas = [p]
    if not candidatas:
        candidatas = [None]

    avaliadas = []
    for c in candidatas:
        Fd, parcelas = _combinar_elu(acoes, comb, c, sentido, g_g, psi2_nota_b)
        avaliadas.append((c, Fd, parcelas))
    alternativas = tuple(("" if c is None else c.nome, Fd) for c, Fd, _ in avaliadas)
    c_gov, Fd_gov, parcelas_gov = _escolher(avaliadas, sentido)
    nome_gov = "" if c_gov is None else c_gov.nome

    mem = [_TITULO_ELU[comb], _FORMULA_ELU[comb]]
    if comb == "normal":
        origem = "argumento gama_g" if gama_g is not None else "nucleo_nbr6118.GAMA_G"
        mem.append(f"γg = {_fmt(g_g)} ({origem}; Tabela 11.1, p. 85, nota a).")
    else:
        mem.append(f"Coeficientes da linha {'especiais ou de construção' if comb != 'excepcional' else 'excepcionais'} "
                   "da Tabela 11.1 (p. 85).")
    if psi2_nota_b:
        mem.append("Nota b da Tabela 11.3: ψ0j substituído por ψ2j nas variáveis diretas.")
    mem.append(f"Sentido: {'maior' if sentido == 'max' else 'menor'} valor de Fd.")
    mem.extend(_linha_parcela(p) for p in parcelas_gov)
    rot = f" (principal: {nome_gov})" if nome_gov else ""
    mem.append(f"Fd = {_fmt(Fd_gov)}{rot}.")
    if len(avaliadas) > 1:
        mem.append("Varredura da ação principal: "
                   + "; ".join(f"{n} → {_fmt(v)}" for n, v in alternativas)
                   + f"; governa {nome_gov}.")
    return ResultadoCombinacao("ELU", comb, sentido, Fd_gov, nome_gov, g_g, parcelas_gov,
                               alternativas, nome_gov, tuple(mem))


# ---------------------------------------------------------------------------
# 11.8.3 — Combinações de serviço, Tabela 11.4 (PDF p. 89)
# ---------------------------------------------------------------------------
_ALIAS_SERVICO = {
    "quasepermanente": "quase_permanente", "cqp": "quase_permanente",
    "frequente": "frequente", "cf": "frequente",
    "rara": "rara", "cr": "rara",
}
_FORMULA_ELS = {
    "quase_permanente": "Fd,ser = ΣFgi,k + Σψ2j·Fqj,k",
    "frequente": "Fd,ser = ΣFgik + ψ1·Fq1k + Σψ2j·Fqjk",
    "rara": "Fd,ser = ΣFgik + Fq1k + Σψ1j·Fqjk",
}
_TITULO_ELS = {
    "quase_permanente": "Combinação quase permanente de serviço (CQP) — NBR 6118:2026, 11.8.3.2 e Tabela 11.4 (p. 89).",
    "frequente": "Combinação frequente de serviço (CF) — NBR 6118:2026, 11.8.3.2 e Tabela 11.4 (p. 89).",
    "rara": "Combinação rara de serviço (CR) — NBR 6118:2026, 11.8.3.2 e Tabela 11.4 (p. 89).",
}


def _normalizar_servico(tipo: str) -> str:
    return _normalizar(tipo, _ALIAS_SERVICO, "Combinação de serviço",
                       ("quase_permanente", "frequente", "rara"))


def _combinar_els(acoes, tipo, principal, sentido):
    parcelas = []
    for a in acoes:
        fav = _eh_favoravel(a, sentido)
        if a.permanente:
            parcelas.append(_parcela(a, "permanente", fav, 1.0, 1.0, a.Fk))
        elif a.excepcional or fav:
            parcelas.append(_parcela(a, "excluida", fav, 0.0, 0.0, a.Fk))
        else:
            _, p1, p2 = a.psi
            if tipo == "quase_permanente":
                parcelas.append(_parcela(a, "secundaria", fav, 1.0, p2, a.Fk))
            elif a is principal:
                parcelas.append(_parcela(a, "principal", fav, 1.0,
                                         p1 if tipo == "frequente" else GAMA_F2_PRINCIPAL,
                                         a.Fk))
            else:
                parcelas.append(_parcela(a, "secundaria", fav, 1.0,
                                         p2 if tipo == "frequente" else p1, a.Fk))
    return sum(p.valor for p in parcelas), tuple(parcelas)


def combinacao_servico(acoes: Iterable[Acao], tipo: str = "quase_permanente",
                       principal=None, sentido: str = "max") -> ResultadoCombinacao:
    """Combinação de serviço, 11.8.3.2 e Tabela 11.4 (p. 89).

    Quase permanente (CQP): Fd,ser = ΣFgi,k + Σψ2j·Fqj,k
    Frequente (CF):         Fd,ser = ΣFgik + ψ1·Fq1k + Σψ2j·Fqjk
    Rara (CR):              Fd,ser = ΣFgik + Fq1k + Σψ1j·Fqjk

    γf = γf2 (11.7.2): as permanentes entram com o valor característico Fk
    (γ = 1), e as variáveis com o γf2 da combinação. A ação principal é uma
    variável direta (Fq1k, Tabela 11.4); com ``principal=None`` a função varre
    as candidatas desfavoráveis e devolve a que governa. Na CQP não há
    principal. A ação excepcional não entra, e a variável favorável também não.
    """
    acoes = _validar_acoes(acoes)
    t = _normalizar_servico(tipo)
    sentido = _validar_sentido(sentido)
    if t == "quase_permanente":
        if principal is not None:
            raise ValueError("A combinação quase permanente não tem ação principal (Tabela 11.4).")
        candidatas = [None]
    else:
        candidatas = [a for a in acoes if a.natureza == "variavel_direta"
                      and not _eh_favoravel(a, sentido)]
        if principal is not None:
            p = _achar_principal(acoes, principal)
            if p.natureza != "variavel_direta":
                raise FaixaNormativaError(
                    f"A Tabela 11.4 toma Fq1k entre as ações variáveis diretas; {p.nome!r} é "
                    f"{_rotulo_natureza(p)}.")
            candidatas = [p]
        if not candidatas:
            candidatas = [None]

    avaliadas = []
    for c in candidatas:
        Fd, parcelas = _combinar_els(acoes, t, c, sentido)
        avaliadas.append((c, Fd, parcelas))
    alternativas = tuple(("" if c is None else c.nome, Fd) for c, Fd, _ in avaliadas)
    c_gov, Fd_gov, parcelas_gov = _escolher(avaliadas, sentido)
    nome_gov = "" if c_gov is None else c_gov.nome

    mem = [_TITULO_ELS[t], _FORMULA_ELS[t],
           "γf = γf2 (11.7.2, p. 86); permanentes com γ = 1.",
           f"Sentido: {'maior' if sentido == 'max' else 'menor'} valor de Fd,ser."]
    mem.extend(_linha_parcela(p) for p in parcelas_gov)
    rot = f" (principal: {nome_gov})" if nome_gov else ""
    mem.append(f"Fd,ser = {_fmt(Fd_gov)}{rot}.")
    if len(avaliadas) > 1:
        mem.append("Varredura da ação principal: "
                   + "; ".join(f"{n} → {_fmt(v)}" for n, v in alternativas)
                   + f"; governa {nome_gov}.")
    return ResultadoCombinacao("ELS", t, sentido, Fd_gov, nome_gov, 1.0, parcelas_gov,
                               alternativas, nome_gov, tuple(mem))


# ---------------------------------------------------------------------------
# 15.3.1 — Formulação de segurança da 2ª ordem (PDF p. 121)
# ---------------------------------------------------------------------------
def sd_tot_2a_ordem(S_de_F: float, gama_f3: float | None = None) -> float:
    """Sd,tot = γf3·S(F), com γf3 = 1,1 (15.3.1, p. 121).

    ``S_de_F`` é o efeito de 2ª ordem calculado com as cargas majoradas de
    γf/γf3.
    """
    g3 = float(GAMA_F3 if gama_f3 is None else gama_f3)
    if g3 <= 0.0:
        raise ValueError(f"γf3 tem de ser positivo ({g3:g}).")
    return g3 * float(S_de_F)


def combinacao_2a_ordem_sdtot(acoes: Iterable[Acao], principal=None,
                              S: Callable[[float], float] | None = None,
                              gama_g: float | None = None,
                              gama_f3: float | None = None,
                              sentido: str = "max") -> ResultadoSdTot:
    """Formulação de segurança da 2ª ordem, 15.3.1 (p. 121).

        Sd,tot = γf3·S(F)
        F = (γf/γf3)·Fgk + (γf/γf3)·(Fq1k + Σψ0j·Fqjk),   γf3 = 1,1

    F é a combinação última normal (11.8.2.1, com γf da Tabela 11.1 e ψ0 da
    Tabela 11.2) dividida por γf3. A divisão é linear, então F = Fd/γf3 é
    exatamente Σ(γf,i/γf3)·ψi·Fik termo a termo, cada ação com o próprio γf,
    sejam eles iguais ou não. A equação de 15.3.1 escreve só Fgk e Fq, mas o
    parágrafo seguinte (p. 121) manda tirar "a combinação de ações e os
    coeficientes γf e ψ0" da Seção 11; por isso as indiretas (protensão,
    retração, recalque, temperatura) entram como na combinação normal da
    Tabela 11.3, com γεg e γεq·ψ0ε. ``S`` é a análise de 2ª ordem (função do
    valor F no efeito S(F)); sem ela, S é a identidade (análise linear), e
    Sd,tot coincide com o Fd da combinação normal. Com ``principal=None``, a
    função varre as variáveis diretas e devolve a de maior Sd,tot (menor com
    ``sentido='min'``).
    """
    acoes = _validar_acoes(acoes)
    sentido = _validar_sentido(sentido)
    g3 = float(GAMA_F3 if gama_f3 is None else gama_f3)
    if g3 <= 0.0:
        raise ValueError(f"γf3 tem de ser positivo ({g3:g}).")
    analise = S if S is not None else (lambda F: F)
    if principal is not None:
        nomes = [principal]
    else:
        nomes = [a for a in acoes if a.natureza == "variavel_direta"
                 and not _eh_favoravel(a, sentido)] or [None]
    avaliadas = []
    for n in nomes:
        r = combinacao_ultima(acoes, "normal", principal=n, sentido=sentido, gama_g=gama_g)
        F = r.Fd / g3
        S_F = float(analise(F))
        avaliadas.append((r, F, S_F, sd_tot_2a_ordem(S_F, g3)))
    alternativas = tuple((r.principal, sd) for r, _, _, sd in avaliadas)
    chave = (lambda it: it[3]) if sentido == "max" else (lambda it: -it[3])
    r, F, S_F, sd = max(avaliadas, key=chave)
    mem = ["Formulação de segurança da 2ª ordem — NBR 6118:2026, 15.3.1 (p. 121).",
           "Sd,tot = γf3·S(F); F = (γf/γf3)·Fgk + (γf/γf3)·(Fq1k + Σψ0j·Fqjk).",
           f"γf3 = {_fmt(g3)}."]
    mem.extend(r.memoria)
    mem.append(f"F = Fd/γf3 = {_fmt(r.Fd)}/{_fmt(g3)} = {_fmt(F)}.")
    mem.append(f"S(F) = {_fmt(S_F)} ({'análise fornecida' if S is not None else 'S linear'}).")
    mem.append(f"Sd,tot = {_fmt(g3)} × {_fmt(S_F)} = {_fmt(sd)}.")
    if len(avaliadas) > 1:
        mem.append("Varredura da ação principal: "
                   + "; ".join(f"{n} → {_fmt(v)}" for n, v in alternativas)
                   + f"; governa {r.principal}.")
    return ResultadoSdTot(F, S_F, g3, sd, r.principal, alternativas, r.principal, tuple(mem))


# ---------------------------------------------------------------------------
# 11.4.1.3 — Ação da água (PDF p. 82)
# ---------------------------------------------------------------------------
def acao_agua(nome: str, Fk: float, permanente: bool = True, categoria_psi=None,
              Fk_inf: float | None = None) -> Acao:
    """Ação da água em reservatório, tanque ou decantador, ou água de chuva retida (11.4.1.3, p. 82).

    O nível d'água é o máximo compatível com o sistema de extravasão (ou, para
    água de chuva retida, a lâmina do nível de drenagem efetivamente garantido
    pela construção); ``Fk`` é o efeito desse nível, calculado pelo usuário.
    No ELU a água desfavorável leva só γf = γf3 = 1,2, em qualquer combinação
    última. Favorável, segue a Tabela 11.1 (1,0 como permanente; fora da
    combinação como variável). A água pode ser permanente ou variável
    (11.2.2); como variável, ``categoria_psi`` é obrigatória — a Tabela 11.2
    não tem linha para água, e a tupla (ψ0, ψ1, ψ2) vem da NBR 8681.
    """
    if permanente:
        return Acao(nome, "permanente_direta", "permanente", Fk, Fk_inf=Fk_inf,
                    gama_f_desfavoravel=GAMA_F_AGUA)
    if categoria_psi is None:
        raise ValueError(
            "Água como ação variável: informe categoria_psi (a Tabela 11.2 não tem linha para água).")
    return Acao(nome, "variavel_direta", "variavel", Fk, categoria_psi=categoria_psi,
                gama_f_desfavoravel=GAMA_F_AGUA)


# ---------------------------------------------------------------------------
# 11.4.2.1 — Variação uniforme de temperatura (PDF p. 82-83)
# ---------------------------------------------------------------------------
def variacao_temperatura_uniforme(menor_dim_cm: float,
                                  macico_ou_oco_fechado: bool = True) -> tuple[float, float]:
    """Faixa da oscilação uniforme de temperatura em torno da média, °C (11.4.2.1, p. 82-83).

    a) menor dimensão ≤ 50 cm: 10 °C a 15 °C;
    b) elemento maciço ou oco com os vazios inteiramente fechados e menor
       dimensão > 70 cm: 5 °C a 10 °C;
    c) entre 50 cm e 70 cm: interpolação linear entre as duas faixas (a norma
       admite).
    Devolve (ΔT mínimo, ΔT máximo). Quando o elemento não é maciço nem oco
    fechado, a alínea b não se aplica, e a função mantém 10 °C a 15 °C (a
    favor da segurança; a norma não dá outro valor).
    """
    h = float(menor_dim_cm)
    if h <= 0.0:
        raise FaixaNormativaError(f"Menor dimensão = {_fmt(h)} cm: tem de ser positiva.")
    a_lo, a_hi = TEMPERATURA_UNIFORME_ATE_50CM_C
    b_lo, b_hi = TEMPERATURA_UNIFORME_ACIMA_70CM_C
    if h <= DIMENSAO_LIMITE_INFERIOR_CM or not macico_ou_oco_fechado:
        return (a_lo, a_hi)
    if h >= DIMENSAO_LIMITE_SUPERIOR_CM:
        return (b_lo, b_hi)
    t = (h - DIMENSAO_LIMITE_INFERIOR_CM) / (DIMENSAO_LIMITE_SUPERIOR_CM - DIMENSAO_LIMITE_INFERIOR_CM)
    return (a_lo + t * (b_lo - a_lo), a_hi + t * (b_hi - a_hi))


def variacao_temperatura_adotada_c(menor_dim_cm: float, t_media_verao_c: float,
                                   t_media_inverno_c: float,
                                   macico_ou_oco_fechado: bool = True) -> float:
    """Oscilação uniforme adotada, °C: 50 % da diferença entre as médias de verão e inverno (11.4.2.1, p. 83).

    ΔT = 0,5·|Tverão − Tinverno|, limitado à faixa de
    ``variacao_temperatura_uniforme`` (a norma usa o critério para escolher
    um valor entre os dois limites).
    """
    lo, hi = variacao_temperatura_uniforme(menor_dim_cm, macico_ou_oco_fechado)
    dt = 0.5 * abs(float(t_media_verao_c) - float(t_media_inverno_c))
    return min(max(dt, lo), hi)


# ---------------------------------------------------------------------------
# 11.4.2.2 — Variação não uniforme de temperatura (PDF p. 83)
# ---------------------------------------------------------------------------
def diferenca_temperatura_faces_c(delta_t_c: float | None = None) -> float:
    """Diferença de temperatura entre as faces a adotar, °C (11.4.2.2, p. 83).

    Na falta de dados mais precisos, a variação é linear entre as faces, e a
    diferença entre uma face e outra não pode ser inferior a 5 °C. Devolve
    max(|ΔT|, 5 °C); sem ΔT, devolve o mínimo de 5 °C.
    """
    if delta_t_c is None:
        return GRADIENTE_TERMICO_MIN_C
    return max(abs(float(delta_t_c)), GRADIENTE_TERMICO_MIN_C)


def temperatura_linear_c(t_face_1_c: float, t_face_2_c: float, y_cm: float,
                         h_cm: float) -> float:
    """Temperatura na fibra y da variação linear entre faces, °C (11.4.2.2, p. 83).

    T(y) = T1 + (T2 − T1)·y/h, com y medido da face 1 (0 ≤ y ≤ h). Levanta
    ``FaixaNormativaError`` se |T2 − T1| < 5 °C, o mínimo da norma.
    """
    t1, t2, y, h = float(t_face_1_c), float(t_face_2_c), float(y_cm), float(h_cm)
    if h <= 0.0:
        raise FaixaNormativaError(f"h = {_fmt(h)} cm: tem de ser positivo.")
    if not (0.0 <= y <= h):
        raise FaixaNormativaError(f"y = {_fmt(y)} cm fora da seção (0 a {_fmt(h)} cm).")
    if abs(t2 - t1) < GRADIENTE_TERMICO_MIN_C - _TOL:
        raise FaixaNormativaError(
            f"Diferença entre faces = {_fmt(abs(t2 - t1))} °C, inferior ao mínimo de "
            f"{_fmt(GRADIENTE_TERMICO_MIN_C)} °C de 11.4.2.2.")
    return t1 + (t2 - t1) * y / h
