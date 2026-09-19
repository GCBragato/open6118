<p align="center">
  <img src="brgt/logo_brgt.png" alt="BRGT Engenharia Estrutural" width="140">
</p>

# open6118

Biblioteca aberta, em Python, para dimensionamento e verificação de concreto armado e protendido pela
**ABNT NBR 6118:2026**.

Ela recebe esforços e geometria e devolve o que a norma pede para aquela seção ou aquele elemento, com a
conta à vista. Serve a quem quer conferir um número fora do programa de projeto, a quem desenvolve a própria
ferramenta de cálculo e a quem ensina e quer mostrar cada passo.

## Situação em 18/09/2026

- **Auditada contra o texto da NBR 6118:2026.** Foram 73 defeitos, 38 deles graves, todos corrigidos e
  confirmados por verificação independente. Detalhes em [AUDITORIA_NBR6118_2026.md](AUDITORIA_NBR6118_2026.md)
  e [CORRECOES_NBR6118_2026.md](CORRECOES_NBR6118_2026.md).
- **613 testes**, com os valores esperados tirados do texto da norma, e não de exemplos de apostila.
- **Concreto de C20 a C90**, com o Grupo II (C55 a C90) calculado de verdade. Fora dessa faixa, a biblioteca
  levanta `FaixaNormativaError` em vez de extrapolar.
- **Cobre 75 dos 505 itens computáveis da norma.** O restante está planejado em 43 pacotes, em
  [PLANO_IMPLEMENTACAO_NBR6118_2026.md](PLANO_IMPLEMENTACAO_NBR6118_2026.md), com a
  [matriz item a item](PLANO_IMPLEMENTACAO_NBR6118_2026_MATRIZ.md).

## O que ela calcula hoje

- Flexão simples, em seção retangular e T, com armadura simples ou dupla; flexão composta normal e oblíqua,
  com um kernel em Python e outro em C++, opcional, que dá o mesmo resultado.
- Pilares pelo pilar-padrão: esbeltez, momento mínimo, excentricidade acidental e 2ª ordem local por
  curvatura ou rigidez aproximada; envoltória mínima de 1ª e 2ª ordem.
- Força cortante, nos modelos I e II, e torção, com a combinação entre as duas.
- Ancoragem passiva, comprimento básico e necessário, e traspasse.
- Lajes: momentos em uma e duas direções, flexão, armadura mínima, γn do balanço e cortante sem armadura
  transversal.
- Viga em serviço: estádio II, decalagem e abertura de fissura.
- Protendido: perdas por atrito, escorregamento, encurtamento, retração, fluência e relaxação, estimativa da
  força e momento resistente.
- Sapatas e blocos sobre estacas, pelos métodos de cálculo das apostilas (bielas, CEB-70 e Blévot), com as
  verificações de biela da norma.

## Como usar

Ainda não se instala pelo pip. Clone o repositório e rode a partir da raiz dele:

```bash
git clone https://github.com/GCBragato/open6118.git
cd open6118
pip install numpy scipy pytest
python -m pytest
```

Um exemplo, uma viga de 20 × 50 cm, com d = 46 cm, aço CA-50 e Md = 14.000 kN·cm, em C30 e em C90:

```python
from dimensionamento import vigas_bastos as vigas

for fck in (30, 90):
    r = vigas.secao_retangular_simples(
        Md_kncm=14000, bw_cm=20, d_cm=46, h_cm=50, fck_mpa=fck, fyk_mpa=500
    )
    print(f"C{fck}: As = {r.As:.2f} cm², As,mín = {r.As_min:.2f} cm², "
          f"x = {r.x:.2f} cm, domínio {r.dominio}")
```

```text
C30: As = 7.79 cm², As,mín = 1.50 cm², x = 11.62 cm, domínio 2
C90: As = 7.39 cm², As,mín = 2.56 cm², x = 6.88 cm, domínio 2
```

Com `fck_mpa=95`, a mesma chamada levanta `FaixaNormativaError`: a norma vai até C90.

O kernel C++ de flexão composta oblíqua (`dimensionamento/rotinas/fco_cpp/`) vem compilado para Windows e
Python 3.13. O padrão é o kernel em Python, que dá o mesmo resultado; para recompilar o C++, use o
`build.bat` da mesma pasta (Visual Studio 2022 Build Tools e pybind11).

## Organização

| Onde | O que tem |
|---|---|
| `dimensionamento/nucleo_nbr6118.py` | o núcleo normativo único: materiais, diagramas, dutilidade, armaduras mínimas, aderência, momento mínimo e cobrimento. Todos os módulos delegam a ele. |
| `dimensionamento/*_bastos.py` | os módulos por elemento: vigas, lajes, pilares, cortante, torção, ancoragem, protendido, sapatas e blocos |
| `dimensionamento/rotinas/` | o kernel de flexão composta oblíqua (Python e C++), o despachante entre os dois e a envoltória mínima de pilar |
| `secoes_norma/` | código legado por seção da norma, hoje delegando ao núcleo |
| `tests/` | os testes; os escritos na auditoria de 2026 citam o item e a página da norma de cada valor esperado |

## O que a biblioteca não faz

1. **Não é programa de projeto.** Não monta modelo nem faz análise estrutural global; verifica seções e
   elementos a partir de esforços dados.
2. **Não substitui o engenheiro responsável.** Todo resultado deve ser conferido à luz da NBR 6118:2026 e das
   demais normas aplicáveis.
3. **Cobre só parte da norma.** O que não está implementado não é verificado; a
   [matriz](PLANO_IMPLEMENTACAO_NBR6118_2026_MATRIZ.md) diz o que está e o que não está.

## Como contribuir

A contribuição mais útil é a mais simples: **se um número não bater com a norma, abra uma
[issue](https://github.com/GCBragato/open6118/issues)** com o caso, o valor que a biblioteca deu e o item da
norma que diz outra coisa.

## Créditos

Os módulos `*_bastos.py` nasceram das apostilas do **Prof. Paulo Sérgio Bastos (UNESP, Bauru)**, que resolvem
passo a passo exemplos de vigas, lajes, pilares, cortante, torção, ancoragem, sapatas, blocos e concreto
protendido. O nome do arquivo é o crédito. As apostilas foram escritas para edições anteriores da norma; onde
a edição de 2026 diverge, vale a norma.

A auditoria, as correções e o plano de 2026 foram feitos com agentes de IA (Claude, da Anthropic), com cada
achado conferido de forma independente: a norma lida na imagem da página, a execução com script próprio e a
revisão. O método está descrito nos relatórios.

## Licença

MIT — ver [LICENCE.txt](LICENCE.txt).

Desenvolvida por Gustavo Bragato, da [BRGT Engenharia Estrutural](https://brgt.com.br).
