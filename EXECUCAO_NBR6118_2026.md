# Execução do plano de implementação da NBR 6118:2026

- **Data:** 19/09/2026
- **Base:** [PLANO_IMPLEMENTACAO_NBR6118_2026.md](PLANO_IMPLEMENTACAO_NBR6118_2026.md), revisto no mesmo dia com as decisões do engenheiro responsável (seção 6 do plano)
- **Norma:** ABNT NBR 6118:2026, 5ª edição. As páginas citadas são as do PDF (a impressa é 18 a menos).
- **Estado:** os 48 pacotes do plano estão no `main`, um commit por pacote. Nada foi publicado no PyPI.

## 1. Resposta curta

1. **A biblioteca cobre 512 dos 519 itens computáveis da norma, 98,7 %.** Antes desta execução eram 75, ou
   14,5 %.
2. **Ficam de fora 7 itens:** o vento, que é da NBR 6123 e entra na biblioteca como esforço já calculado, e
   **6 itens parciais**, listados na seção 5, em que a norma dá uma figura ou um princípio, sem fórmula,
   ângulo ou proporção que permitam fechar a conta.
3. **Os testes passaram de 613 para 3.374**, todos com o valor esperado tirado do texto ou da imagem da
   norma. Nenhum é pulado, nenhum está marcado para falhar.
4. **A biblioteca passou a calcular a estrutura**, e não só a verificar seções: pórtico plano e espacial,
   grelha, treliça plana e espacial, lajes por grelha e por pórtico equivalente, 2ª ordem global e as
   treliças de bielas e tirantes (decisão 1 do plano).
5. **Tamanho:** 54 módulos e 44.874 linhas de Python na biblioteca, com 1.114 funções e classes públicas,
   mais 27.828 linhas de teste.

## 2. Como foi feito

Cada um dos 48 pacotes do plano passou pelo mesmo protocolo, o da seção 9 do plano:

1. **Implementação em cópia isolada.** Um agente recebeu só o texto do pacote, os itens da norma com a
   página e as convenções, e trabalhou num `git worktree` próprio, sem enxergar o trabalho dos outros. A
   fórmula veio da **imagem da página**, não do texto extraído do PDF, que estraga raiz, fração e letra grega.
2. **Três verificações independentes,** cada uma por um agente que não viu a implementação sendo feita: uma
   releu a norma na imagem, outra recalculou tudo com script próprio sem importar a biblioteca, e a terceira
   revisou o diff, as convenções, os acentos e as assinaturas públicas.
3. **Correção e nova conferência,** até as três lentes aprovarem. Em 23 dos 54 pacotes houve pelo menos uma
   volta de correção; em um deles, duas.
4. **Integração no `main`,** um commit por pacote, com o pytest inteiro passando depois de cada merge e o
   item marcado na matriz de cobertura.

Depois dos 48 pacotes vieram **4 rodadas de fechamento** dos itens que tinham ficado parciais, **1
conferência final** da biblioteca inteira em cinco lentes (seção 6) e **2 rodadas de correção** do que ela
apontou. Ao todo foram cerca de 295 rodadas de agente.

**O que a verificação encontrou.** As lentes apontaram, entre outras coisas, um erro de leitura da Figura
20.2 que trocava a linha da armadura (seção 4), a taxa mecânica mínima de viga aceitando aço fora da Tabela
17.3, a esbeltez de lâmina de pilar-parede aceita exatamente no limite de 90, fórmula de material
reimplementada em vez de delegada ao núcleo e mensagens sem acento. Em 93 itens, com 98 registros ao todo,
quem implementou anotou diferença entre a transcrição do plano e a imagem da página, ou uma leitura que a norma
não fecha; valeu a imagem, e cada registro está no JSON do plano, no campo `divergencias_imagem` do item.

## 3. O que entrou, onda por onda

| Onda | Pacotes | Itens | Temas |
|---|---|---|---|
| 1 | P1 a P9 | 88 | durabilidade e cobrimento, materiais, aço de protensão, ações e combinações, segurança, fluência e retração do Anexo A, flecha, estádio II e fissuração |
| 2 | P10 a P26, P44 e P45 | 183 | limites geométricos, classificação, redistribuição, geometria efetiva, cortante e torção completas, lajes, punção, detalhamento de vigas, pilares e lajes, 2ª ordem local, estabilidade global, cálculo de barras e lajes por grelha |
| 3 | P27 a P37, P46 a P48 | 113 | emendas, momento-curvatura e método geral, pilar-parede, protensão completa, regiões especiais, bielas e tirantes, consolos e dentes Gerber, fundações, 2ª ordem global e hiperestático de protensão |
| 4 | P38 a P43 | 59 | fadiga, concreto simples, flexo-torção de perfis abertos e método geral de perdas |

## 4. O que mudou no que já existia

A execução acrescentou muito mais do que mudou, mas há mudanças que afetam quem já usava a biblioteca:

1. **Aço de protensão (P3).** O diagrama passou a ser o da Figura 8.6, com o segundo trecho ascendente até
   fptd, no lugar do patamar (decisão 2 do plano). O momento resistente de seção protendida sobe de 2 % a 3 %.
   Com `diagrama="patamar"` o cálculo volta ao de antes.
2. **γg configurável (P4).** `nucleo_nbr6118.GAMA_G` é lido na hora da chamada, e a memória de cálculo
   registra o valor usado (decisão 3).
3. **Cortante de laje (P15).** `lajes_nbr6118.cortante_resistente_laje` passou a delegar à função de
   cortante, que tem o termo da força normal. O resultado muda quando há força normal, e com tração o valor
   de antes ficava contra a segurança (decisão 6).
4. **Taxa mecânica mínima de viga (P12).** `omega_min` passou a recusar aço e γ diferentes dos que a Tabela
   17.3 pressupõe, em vez de devolver um número errado em silêncio. Com CA-50 e os γ padrão nada muda.
5. **Figura 20.2, distribuição de armadura em laje sem vigas (C2).** A cota de 15 cm da faixa interna
   pertence à linha das barras superiores, e não à das inferiores. Três valores mudaram: as barras superiores
   ganharam o piso de 15 cm, as inferiores contínuas perderam a cota que não era delas, e o corte do restante
   passou a ser 0,125ℓ sem piso.
6. **Pilar-parede (C1).** A esbeltez de lâmina igual a 90 passou a ser recusada, como manda 15.9.3.
7. **Cobrimento (P1).** `cobrimento_nominal` passou a expor cmín e Δc e a aceitar redução por classe
   superior, face revestida e pré-moldado. Com os padrões, os números são os mesmos de antes.
8. **Legado.** `secoes_norma/sec7` e `sec9` viraram fachadas sobre os módulos novos, com aviso de função
   obsoleta e os mesmos números.
9. **Erro de faixa.** Onde a norma não define, as funções levantam `FaixaNormativaError` (subclasse de
   `ValueError`), em vez de `ValueError` cru ou de um número extrapolado.

Cada pacote registrou as suas mudanças de comportamento na mensagem do commit; são 101 ao todo.

## 5. O que ficou parcial, e por quê

Cada linha tem o número do item da norma, que é também o id usado na triagem desses pontos.

| Id | Item | O que falta | Por quê |
|---|---|---|---|
| 11.4.1.2 | vento | o cálculo das forças de vento | é da NBR 6123, outra norma; a biblioteca recebe as forças prontas, combina com as demais ações e compara com o desaprumo |
| 14.6.2.2 | abertura na mesa colaborante | a largura efetiva a partir das coordenadas da abertura | a Figura 14.3 é regra gráfica, sem o ângulo da reta inclinada; a função recebe o bef medido no desenho e aplica o limite normativo |
| 14.6.2.3 | mísulas | a altura efetiva ponto a ponto dentro da cunha | a Figura 14.4 não dá comprimento nem inclinação da cunha; a função devolve o piso garantido, que é o trecho menor |
| 19.5.3.4 | contorno C″ da punção | o perímetro reduzido do arranjo de conectores em cruz | a Figura 19.8 ilustra o arranjo sem dar a regra numérica do trecho reto e do raio |
| 22.5.1.3 | modelo de cálculo do consolo | o modelo de atrito-cisalhamento, para consolo muito curto | a norma cita o modelo sem coeficiente de atrito nem expressão; o modelo de biela e tirante está completo |
| 22.5.2.3 | modelo de cálculo do dente Gerber | a treliça própria do dente | a norma manda seguir os princípios do consolo "com as correções necessárias", sem dar a posição dos nós; a biblioteca usa o modelo do consolo com o braço e a distância ajustados ao dente |
| 22.7.3 | bloco sobre estacas em três dimensões | a análise de sólido | a norma aceita a treliça espacial de bielas e tirantes como alternativa, e a biblioteca faz a treliça; o sólido em elementos finitos ficou fora pela decisão 1 |

## 6. A conferência final

Cinco lentes independentes olharam a biblioteca pronta:

1. **Registro contra código:** os 662 itens do plano, as 976 funções citadas e os 1.870 testes citados foram
   cruzados com o código e com a coleta do pytest. Nenhuma função declarada está faltando. Os 55 módulos
   importam sem ciclo, e o exemplo do README reproduz a saída documentada.
2. **Duplicação e coerência:** procurou fórmula de material reimplementada, coeficiente escrito à mão e a
   mesma grandeza calculada em dois módulos. O que achou virou a rodada C1.
3. **Texto para o usuário:** varreu 114 arquivos atrás de mensagem, aviso e memória de cálculo sem acento.
4. **Amostra na norma, duas listas de 13 itens de alto risco** (tabelas grandes, figuras digitalizadas,
   degraus), reconferidos na imagem da página. Um deles achou o erro da Figura 20.2.

**Um achado foi rejeitado, com evidência.** A lente de duplicação afirmou que o kernel de flexão deveria usar
o αc reduzido no pico do diagrama parábola-retângulo. O item 17.2.2 e), na p. 141, diz o contrário: o
diagrama curvo tem pico 0,85·ηc·fcd, e o αc reduzido vale só para o retângulo equivalente. Usar o αc ali
contaria a redução duas vezes. O código está certo e ganhou um comentário citando o item, para não ser
"corrigido" no futuro.

## 7. O que ainda depende do engenheiro

Numerados de D1 a D7 (e D7.1 a D7.4), que são os ids usados na triagem desses pontos.

- **D1. Comparar de novo com o programa de projeto.** A comparação que existia foi medida antes das correções
  de 18/09 e não vale mais. É a verificação cruzada que falta. O script `tests/compare_tqs_pilar.py` lê o
  relatório de pilares do programa (`Pilar.xml`).
- **D2. γqs na perda de equilíbrio como corpo rígido (11.8.2.1).** A edição de 2026 não dá valor para o
  multiplicador de Qs,mín em Fnd = γgn·Gnk + γq·Qnk − γqs·Qs,mín. Foi adotado 1,0, exposto como parâmetro. Com
  1,0 a ação variável estabilizante entra inteira a favor do equilíbrio, que é o lado menos conservador.
- **D3. Catálogo de fios de protensão (8.4.1).** Os valores vieram de catálogo de referência, não da ABNT NBR
  7482. Vale conferir antes de usar em projeto.
- **D4. Armadura de pele (17.3.5.2.3).** A função devolve a taxa em cm² por metro de altura da alma
  (0,10 %·bw·100). Distribuída na altura, dá o mesmo que a área total 0,10 %·bw·h por face; muda só a forma de
  apresentar.
- **D5. Figura 14.7, rotação plástica (14.6.4.4).** A curva foi digitalizada da imagem, com tolerância
  declarada de ±3 mrad.
- **D6. Integral de fluência com tensão variável (A.2.5).** A imagem da p. 240 traz α·φ(τ,t0)/Eci dentro da
  integral, o que contradiz o princípio da superposição: o acréscimo de tensão aplicado em τ deveria fluir até
  t com φ(t,τ). A biblioteca segue a letra da norma por padrão (`integrando='impresso'`) e oferece a
  superposição como opção explícita (`integrando='superposicao'`), registrada na memória de cálculo. É
  provável erro de impressão na norma; vale confirmar qual das duas usar.
- **D7. Leituras declaradas na docstring.** Onde a norma não fecha o caso, a escolha está escrita na função:
  - **D7.1.** No φa do Anexo A (A.2.2.3), fc(t∞) é a resistência final, o limite de β1, e não fc aos 28 dias.
  - **D7.2.** No kc interpolado da armadura mínima sob deformação imposta (17.3.5.2.2), kc cresce de 0 a 0,4
    com a altura da zona tracionada.
  - **D7.3.** Nas barras transversais soldadas (9.4.6.2 a), vale φt1 > 0,7·φt, estrito, como no texto (a
    figura sugere "maior ou igual").
  - **D7.4.** No teto de Vc do Modelo II (17.4.2.3), vale "≤ 2·Vc1", como no Modelo I (o texto do Modelo II
    escreve "<").

## 8. Limites que continuam valendo

1. **Não é programa de projeto.** Não desenha, não detalha e não monta o modelo por você: o modelo de barras
   é montado por quem chama a biblioteca.
2. **Não substitui o engenheiro responsável.** Todo resultado deve ser conferido à luz da norma.
3. **Elementos finitos de placa e de sólido ficam fora** (decisão 1). Laje lisa entra como grelha
   equivalente, e bloco e sapata como treliça espacial, que a norma aceita.
4. **Cobertura não é garantia de acerto em todo caso.** Cada item foi conferido por três lentes, mas a
   biblioteca é nova: o uso em projeto real é o próximo filtro.
