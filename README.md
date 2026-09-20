<p align="center">
  <img src="brgt/logo_brgt.png" alt="BRGT Engenharia Estrutural" width="140">
</p>

# open6118

Biblioteca aberta, em Python, para dimensionamento e verificação de concreto armado e protendido pela
**ABNT NBR 6118:2026**.

Ela recebe esforços e geometria e devolve o que a norma pede para aquela seção ou aquele elemento, com a
conta à vista. Serve a quem quer conferir um número fora do programa de projeto, a quem desenvolve a própria
ferramenta de cálculo e a quem ensina e quer mostrar cada passo.

## Situação em 19/09/2026

- **Cobre 512 dos 519 itens computáveis da norma, 98,7 %.** O relatório da execução, com o método, o que
  mudou e o que ficou de fora, está em [EXECUCAO_NBR6118_2026.md](EXECUCAO_NBR6118_2026.md); a cobertura item
  a item, em [PLANO_IMPLEMENTACAO_NBR6118_2026_MATRIZ.md](PLANO_IMPLEMENTACAO_NBR6118_2026_MATRIZ.md).
- **3.374 testes**, com os valores esperados tirados do texto ou da imagem da norma, e não de exemplos de
  apostila.
- **Auditada antes contra o texto da norma.** Foram 73 defeitos, 38 deles graves, todos corrigidos e
  confirmados por verificação independente: [AUDITORIA_NBR6118_2026.md](AUDITORIA_NBR6118_2026.md) e
  [CORRECOES_NBR6118_2026.md](CORRECOES_NBR6118_2026.md).
- **Concreto de C20 a C90**, com o Grupo II (C55 a C90) calculado de verdade. Fora dessa faixa, e onde a
  norma não define o caso, a biblioteca levanta `FaixaNormativaError` em vez de extrapolar.
- **Fora da cobertura:** o vento, que é da NBR 6123, e seis itens em que a norma dá só uma figura ou um
  princípio, sem fórmula fechada. Estão listados no relatório da execução.
- Cada verificação devolve, junto com o número, a **memória de cálculo** com o item da norma, a fórmula e os
  valores usados.

## O que ela calcula hoje

**Esforços e análise**

- Ações e combinações: as Tabelas 11.1 a 11.4, com γg configurável, e as combinações última e de serviço.
- Estruturas de barras: pórtico plano e espacial, grelha e treliça plana e espacial, com recalque de apoio,
  alternância de cargas e deformação por cisalhamento.
- Lajes nervuradas e lisas por grelha e por pórtico equivalente; reações e compatibilização de momentos.
- Estabilidade global: α, γz, imperfeições globais e 2ª ordem global por análise não linear.
- Pós-processamento da análise linear: vão efetivo, largura colaborante, trecho rígido, arredondamento do
  diagrama e redistribuição com reequilíbrio.

**Elementos e seções**

- Flexão simples e composta, normal e oblíqua, com um kernel em Python e outro em C++, opcional, que dá o
  mesmo resultado; domínios, momento-curvatura e método geral.
- Pilares: pilar-padrão por curvatura, por rigidez e com diagramas M-N-1/r, fluência, envoltória mínima e
  pilar-parede.
- Cortante nos modelos I e II, torção e a combinação entre elas.
- Lajes: flexão, armaduras mínimas, cortante e **punção**, com armadura, casos especiais e colapso progressivo.
- Vigas e lajes em serviço: estádio II, fissuração, flecha imediata e diferida, e os limites da Tabela 13.3.
- Protendido: força, limites, todas as perdas, ato da protensão, ELS de tensões, ancoragem ativa,
  hiperestático de protensão e detalhamento de laje protendida.
- Fundações: sapatas e blocos, pelos métodos clássicos e por treliça espacial de bielas e tirantes.
- Regiões e elementos especiais: bielas e tirantes, vigas-parede, consolos, dentes Gerber, furos e aberturas.
- Fadiga, concreto simples e flexo-torção de perfis abertos.
- Detalhamento: ancoragem, ganchos, emendas, feixes, telas, e as regras de viga, pilar e laje.
- Durabilidade: classe de agressividade, relação água/cimento, cobrimento e abertura de fissura admissível.

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
from dimensionamento import vigas_nbr6118 as vigas

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
| `dimensionamento/nucleo_nbr6118.py` | o núcleo normativo único: materiais, diagramas, dutilidade, armaduras mínimas, aderência, momento mínimo, cobrimento e os coeficientes de ponderação. Todos os módulos delegam a ele. |
| `dimensionamento/*_nbr6118.py` | os 40 módulos por tema: ações, análise de barras, vigas, lajes, pilares, cortante, torção, punção, ancoragem, emendas, protendido, fundações, bielas e tirantes, consolos, fadiga, concreto simples, durabilidade, ELS e detalhamento |
| `dimensionamento/rotinas/` | o kernel de flexão composta oblíqua (Python e C++), o despachante entre os dois e a envoltória mínima de pilar |
| `secoes_norma/` | código legado por seção da norma, hoje delegando ao núcleo |
| `tests/` | os testes; os escritos na auditoria de 2026 citam o item e a página da norma de cada valor esperado |

## O que a biblioteca não faz

1. **Não é programa de projeto.** Não desenha, não detalha e não monta o modelo por você: quem chama a
   biblioteca monta o modelo de barras e lê o resultado. Elementos finitos de placa e de sólido ficam fora;
   laje lisa entra como grelha equivalente, e bloco e sapata como treliça espacial, como a norma permite.
2. **Não substitui o engenheiro responsável.** Todo resultado deve ser conferido à luz da NBR 6118:2026 e das
   demais normas aplicáveis.
3. **Não cobre a norma inteira.** Faltam o vento, que é de outra norma, e seis itens que a norma só
   descreve com figura; a [matriz](PLANO_IMPLEMENTACAO_NBR6118_2026_MATRIZ.md) diz item a item o que está e o
   que não está.
4. **A comparação com um programa comercial de projeto precisa ser refeita.** A que existia é anterior às
   correções de 18/09.

## Como contribuir

A contribuição mais útil é a mais simples: **se um número não bater com a norma, abra uma
[issue](https://github.com/GCBragato/open6118/issues)** com o caso, o valor que a biblioteca deu e o item da
norma que diz outra coisa.

## Créditos

Os módulos por elemento nasceram das apostilas do **Prof. Paulo Sérgio Bastos (UNESP, Bauru)**, que resolvem
passo a passo exemplos de vigas, lajes, pilares, cortante, torção, ancoragem, sapatas, blocos e concreto
protendido. Até 19/09/2026 eles se chamavam `*_bastos.py`; hoje se chamam `*_nbr6118.py`, e o crédito está aqui
e no cabeçalho de cada módulo. As apostilas foram escritas para edições anteriores da norma; onde a edição de
2026 diverge, vale a norma.

A auditoria, as correções e o plano de 2026 foram feitos com agentes de IA (Claude, da Anthropic), com cada
achado conferido de forma independente: a norma lida na imagem da página, a execução com script próprio e a
revisão. O método está descrito nos relatórios.

## Licença

MIT — ver [LICENCE.txt](LICENCE.txt).

Desenvolvida por Gustavo Bragato, da [BRGT Engenharia Estrutural](https://brgt.com.br).
