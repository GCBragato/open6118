# Matriz de cobertura da NBR 6118:2026 no open6118

Anexo do [PLANO_IMPLEMENTACAO_NBR6118_2026.md](PLANO_IMPLEMENTACAO_NBR6118_2026.md). Uma linha por item calculável ou conferível da norma, com a situação no código em 18/09/2026 e o pacote do plano que cuida dele.

**Total:** 661 itens — 75 implementados, 58 parciais, 372 ausentes e 156 não computáveis.

**Como ler:**

- **Pág.** é a página do PDF da norma (a impressa + 18).
- **Pacote** vazio quer dizer que não há nada a fazer (item implementado ou não computável); "fora" é item que fica fora do escopo, com o motivo.
- A fórmula transcrita, o que falta e o teste sugerido de cada item estão em `PLANO_IMPLEMENTACAO_NBR6118_2026_ITENS.json`. A fonte da fórmula é sempre a imagem da página da norma.
- Os ids estão em ASCII de propósito: são a chave que liga a matriz, o JSON e o plano.

## Seção 5

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `5.1-requisitos-qualidade` | 5.1 | 30 | Requisitos de qualidade da estrutura (segurança/ruína, serviço, durabilidade) | não computável | baixa | P |  |
| `5.2-requisitos-projeto-documentacao` | 5.2 | 31 | Requisitos de qualidade do projeto, condições impostas e documentação da solução adotada | não computável | baixa | P |  |
| `5.3-atp-procedimento` | 5.3 | 33 | Procedimento de avaliação técnica de projeto (ATP): quando fazer, quem faz, quando pode ser dispensada | não computável | baixa | P |  |
| `5.3-tab5.1-classes-consequencia` | 5.3.2 (Tabela 5.1) | 32 | Tabela 5.1 - Classes de consequência (CC1, CC2, CC3) por caso típico de construção | ausente | média | P | P1 |

## Seção 6

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `6.1-6.2-vida-util-projeto` | 6.1, 6.2.4 | 34 | Exigência de durabilidade e vida útil de projeto de referência | ausente | média | P | P1 |
| `6.3-mecanismos-deterioracao` | 6.3 | 34 | Mecanismos de envelhecimento e deterioração (concreto, armadura, estrutura) | não computável | baixa | P |  |
| `6.4-tab6.1-classes-agressividade` | 6.4 (Tabela 6.1) | 36 | Tabela 6.1 - Classes de agressividade ambiental (CAA I a IV) | ausente | alta | P | P1 |

## Seção 7

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `7.4.2-tab7.1-relacao-ac-classe-concreto` | 7.4.2 (Tabela 7.1) | 38 | Tabela 7.1 - Correspondência entre classe de agressividade e qualidade do concreto (a/c máx. e classe mínima) | parcial | alta | P | P1 |
| `7.4.7.1-cnom-cmin-formula` | 7.4.7.1-7.4.7.3 | 38 | cnom = cmín + Δc, com Δc ≥ 10 mm em obras correntes | parcial | média | P | P1 |
| `7.4.7-tab7.2-cobrimento-nominal` | 7.4.7.2, 7.4.7.6-nota, Tabela 7.2 | 39 | Tabela 7.2 - Cobrimento nominal por CAA, tipo de estrutura e elemento, com reduções admitidas | parcial | alta | P | P1 |
| `7.4.7.4-delta-c-premoldados` | 7.4.7.4 | 38 | Redução de Δc para 5 mm em estruturas pré-moldadas com controle rigoroso (NBR 9062) | ausente | baixa | P | P1 |
| `7.4.7.5-cnom-minimos-barra-feixe-bainha` | 7.4.7.5 | 39 | Cobrimento nominal mínimo em função do diâmetro da barra, feixe e bainha | ausente | média | P | P1 |
| `7.4.7.6-dmax-agregado-cobrimento` | 7.4.7.6 | 39 | Dimensão máxima do agregado graúdo limitada pelo cobrimento nominal | ausente | baixa | P | P1 |
| `7.6-7.8-fissuracao-manutencao-durabilidade` | 7.6, 7.7, 7.8 | 40 | Controle de fissuração para durabilidade (remete a 13.4.2), medidas especiais e manual de manutenção (remete a 25.3) | não computável | baixa | P |  |

## Seção 8

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `8.2.1-classes-concreto-faixa` | 8.2.1 | 41 | Classes de resistência do concreto (grupos I e II, até C90) e faixa mínima com/sem armadura ativa | implementado | alta | P |  |
| `8.2.2-massa-especifica-concreto` | 8.2.2 | 42 | Massa específica do concreto simples e armado | ausente | média | P | P2 |
| `8.2.3-dilatacao-termica-concreto` | 8.2.3 | 42 | Coeficiente de dilatação térmica do concreto | ausente | baixa | P | P2 |
| `8.2.5-fct-conversao-ensaios-indiretos` | 8.2.5 | 42 | fct a partir de ensaios indiretos (fct,sp ou fct,f) | ausente | baixa | P | P2 |
| `8.2.5-fctm-fctkinf-fctksup-fctd` | 8.2.5 | 42 | fct,m, fctk,inf, fctk,sup e fctd em função de fck | implementado | alta | P |  |
| `8.2.6-resistencia-multiaxial` | 8.2.6 | 42 | Resistência do concreto no estado multiaxial de tensões | ausente | baixa | P | P2 |
| `8.2.7-fadiga-concreto-referencia` | 8.2.7 | 43 | Resistência à fadiga do concreto (remete a 11.4.2.3 e 23.5.4) | não computável | baixa | P |  |
| `8.2.8-Eci-Ecs-alphai-idade` | 8.2.8 | 44 | Eci, Ecs, αi e Eci em idade menor que 28 dias | implementado | alta | P |  |
| `8.2.9-poisson-Gc` | 8.2.9 | 45 | Coeficiente de Poisson e módulo de elasticidade transversal Gc | parcial | baixa | P | P2 |
| `8.2.10.1-diagrama-parabola-retangulo` | 8.2.10.1 (Figura 8.2) | 45 | Diagrama tensão-deformação idealizado do concreto na compressão (parábola-retângulo) | implementado | alta | M |  |
| `8.2.10.1-fig8.3-diagrama-nao-linear` | 8.2.10.1 (Figura 8.3) | 46 | Diagrama tensão-deformação para análise não linear (curta duração) | ausente | baixa | M | P2 |
| `8.2.10.2-fig8.4-diagrama-bilinear-tracao` | 8.2.10.2 (Figura 8.4) | 46 | Diagrama tensão-deformação bilinear de tração do concreto não fissurado | ausente | média | P | P2 |
| `8.2.11-tabela8.1` | 8.2.11 | 47 | Tabela 8.1 - valores característicos de φ(t∞,t0) e εcs(t∞,t0) | implementado | alta | M |  |
| `8.3.1-fyk-categoria` | 8.3.1 | 47 | Categorias do aço de armadura passiva e fyk | implementado | alta | P |  |
| `8.3.2-tab8.2-eta1-aderencia` | 8.3.2 (Tabela 8.2) | 48 | Tabela 8.2 - η1 por categoria de aço | implementado | alta | P |  |
| `8.3.3-8.4.2-massa-especifica-aco` | 8.3.3, 8.4.2 | 48 | Massa específica do aço passivo e ativo | ausente | baixa | P | P2 |
| `8.3.4-8.4.3-dilatacao-termica-aco` | 8.3.4, 8.4.3 | 48 | Coeficiente de dilatação térmica do aço passivo e ativo | ausente | baixa | P | P2 |
| `8.3.5-8.4.4-modulo-elasticidade-aco` | 8.3.5, 8.4.4 | 48 | Módulo de elasticidade do aço passivo (Es) e ativo (Ep) | implementado | alta | P |  |
| `8.3.6-fig8.5-diagrama-aco-passivo` | 8.3.6 (Figura 8.5) | 48 | Diagrama tensão-deformação bilinear do aço passivo (tração e compressão) | implementado | alta | P |  |
| `8.3.7-dutilidade-aco-passivo` | 8.3.7 | 49 | Classificação de dutilidade do aço passivo | ausente | baixa | P | P2 |
| `8.3.8-fadiga-aco-passivo-referencia` | 8.3.8 | 49 | Resistência à fadiga do aço passivo (remete a 23.5.5) | não computável | baixa | P |  |
| `8.3.9-soldabilidade-aco` | 8.3.9 | 49 | Soldabilidade do aço e critérios de ensaio da emenda soldada | não computável | baixa | P |  |
| `8.4.1-classificacao-aco-ativo` | 8.4.1 | 49 | Classificação do aço de armadura ativa (fios/cordoalhas, RN/RB) | parcial | média | P | P3 |
| `8.4.5-fig8.6-diagrama-aco-ativo` | 8.4.5 (Figura 8.6) | 50 | Diagrama tensão-deformação simplificado do aço de armadura ativa | parcial | alta | M | P3 |
| `8.4.6-dutilidade-aco-ativo` | 8.4.6 | 50 | Classificação de dutilidade de fios e cordoalhas | ausente | baixa | P | P3 |
| `8.4.7-fadiga-aco-ativo-referencia` | 8.4.7 | 50 | Resistência à fadiga do aço ativo (remete a 23.5.5) | não computável | baixa | P |  |
| `8.4.8-tab8.3-relaxacao-psi1000` | 8.4.8 (Tabela 8.3) | 51 | Tabela 8.3 - ψ1000 por σp0/fptk, tipo de armadura e classe RN/RB | implementado | média | P |  |

## Seção 9

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `9.1-simbologia` | 9.1 | 51 | Simbologia da Seção 9 | não computável | baixa | P |  |
| `9.2.1-disposicoes-gerais` | 9.2.1 | 53 | Disposições gerais de aderência, ancoragem e emendas | não computável | baixa | P |  |
| `9.2.2-niveis-protensao` | 9.2.2 | 53 | Níveis de protensão | não computável | média | P |  |
| `9.3.1-posicao-barra-classificacao` | 9.3.1 | 53 | Classificação boa/má situação de aderência pela posição da barra na concretagem | ausente | média | P | P21 |
| `9.3.2.1-fbd` | 9.3.2.1 | 54 | Resistência de aderência de cálculo — armadura passiva (fbd) | implementado | alta | P |  |
| `9.3.2.1-eta2` | 9.3.2.1 | 54 | Coeficiente η2 (situação de aderência) | implementado | alta | P |  |
| `9.3.2.1-eta3` | 9.3.2.1 | 54 | Coeficiente η3 (diâmetro da barra) | implementado | alta | P |  |
| `9.3.2.2-fbpd` | 9.3.2.2 | 54 | Resistência de aderência de cálculo — armadura ativa pré-tracionada (fbpd) | parcial | média | P | P31 |
| `9.3.2.2-etap1` | 9.3.2.2 | 54 | Coeficiente ηp1 (tipo de fio/cordoalha) | implementado | média | P |  |
| `9.3.2.2-etap2` | 9.3.2.2 | 54 | Coeficiente ηp2 (situação de aderência, armadura ativa) | parcial | baixa | P | P31 |
| `9.3.2.3-fator-escorregamento` | 9.3.2.3 | 54 | Majoração de 1,75 na tensão de aderência para verificação de escorregamento em elementos fletidos | ausente | baixa | P | P21 |
| `9.4.1.1-tipos-ancoragem-aderencia` | 9.4.1.1 | 55 | Tipos de ancoragem por aderência e confinamento | parcial | baixa | P | P21 |
| `9.4.2.1-condicoes-ancoragem-reta` | 9.4.2.1 | 55 | Condições de ancoragem reta (com/sem gancho) por tipo de barra e solicitação | ausente | média | P | P21 |
| `9.4.2.2-barras-transversais-soldadas-ancoragem` | 9.4.2.2 | 55 | Ancoragem por barras transversais soldadas (condições geométricas) | parcial | baixa | P | P21 |
| `9.4.2.3-tab9.1-pino-dobramento-gancho` | 9.4.2.3 (Tabela 9.1) | 56 | Tabela 9.1 — diâmetro do pino de dobramento dos ganchos (D) | implementado | alta | P |  |
| `9.4.2.3-ganchos-comprimento-tipo` | 9.4.2.3 | 56 | Tipos de gancho e comprimento mínimo da ponta reta | ausente | média | P | P21 |
| `9.4.2.3-gancho-solda-transversal` | 9.4.2.3 | 56 | Diâmetro do pino quando há barra soldada transversal ao gancho | ausente | baixa | P | P21 |
| `9.4.2.4-lb-basico` | 9.4.2.4 | 57 | Comprimento de ancoragem básico ℓb | implementado | alta | P |  |
| `9.4.2.5-lb-necessario` | 9.4.2.5 | 57 | Comprimento de ancoragem necessário ℓb,nec | implementado | alta | P |  |
| `9.4.2.6.1-armadura-transversal-ancoragem-phi-menor-32` | 9.4.2.6.1 | 57 | Armadura transversal na ancoragem — φ<32mm | ausente | média | P | P21 |
| `9.4.2.6.2-armadura-transversal-ancoragem-phi-maior-igual-32` | 9.4.2.6.2 | 58 | Armadura transversal na ancoragem — φ≥32mm | ausente | baixa | P | P21 |
| `9.4.3-feixe-diametro-equivalente` | 9.4.3 | 58 | Diâmetro equivalente de feixe de barras (φn) | ausente | média | P | P27 |
| `9.4.3-feixe-regras-ancoragem` | 9.4.3 | 58 | Regras de ancoragem de feixes (φn≤25mm / >25mm / caso construtivo) | ausente | média | M | P27 |
| `9.4.4-tela-soldada-ancoragem` | 9.4.4 | 58 | Ancoragem de telas soldadas por aderência (nº de fios transversais) | ausente | média | P | P27 |
| `9.4.5.1-lbp-basico` | 9.4.5.1 | 59 | Comprimento de ancoragem básico de armadura ativa (ℓbp) | parcial | média | P | P31 |
| `9.4.5.2-lbpt-transferencia` | 9.4.5.2 | 59 | Comprimento de transferência ℓbpt | parcial | média | P | P31 |
| `9.4.5.3-lbpd-necessario` | 9.4.5.3 | 59 | Comprimento de ancoragem necessário de armadura ativa (ℓbpd) | parcial | média | P | P31 |
| `9.4.5.4-armadura-transversal-zona-ancoragem-ativa` | 9.4.5.4 | 60 | Armadura transversal na zona de ancoragem de armadura ativa | não computável | média | P |  |
| `9.4.6-ancoragem-estribos-obrigatoriedade` | 9.4.6 | 60 | Ancoragem de estribos deve ser por gancho ou barra longitudinal soldada | não computável | alta | P |  |
| `9.4.6.1-ganchos-estribos-tipos` | 9.4.6.1 | 60 | Tipos de gancho de estribo e comprimento mínimo da ponta reta | ausente | alta | P | P21 |
| `9.4.6.1-tab9.2-pino-dobramento-estribo` | 9.4.6.1 (Tabela 9.2) | 60 | Tabela 9.2 — diâmetro do pino de dobramento para estribos | implementado | alta | P |  |
| `9.4.6.2-estribo-barra-transversal-soldada` | 9.4.6.2 | 60 | Ancoragem de estribo por barras transversais soldadas | ausente | baixa | P | P21 |
| `9.4.7-dispositivos-mecanicos-ancoragem` | 9.4.7 | 61 | Ancoragem por dispositivos mecânicos — limites de escorregamento e resistência de cálculo | ausente | baixa | P | P27 |
| `9.4.7.1-barra-transversal-unica` | 9.4.7.1 | 61 | Barra transversal única como dispositivo de ancoragem integral | ausente | baixa | P | P27 |
| `9.5.2-traspasse-limite-32mm-feixe-45mm` | 9.5.2 | 62 | Limite de bitola para emenda por traspasse (barra e feixe) | parcial | média | P | P27 |
| `9.5.2.1-mesma-secao-transversal` | 9.5.2.1 | 62 | Critério de 'mesma seção transversal' para emendas e traspasse com diâmetros diferentes | ausente | média | P | P27 |
| `9.5.2.1-tab9.3-proporcao-maxima-emendas` | 9.5.2.1 (Tabela 9.3) | 63 | Tabela 9.3 — proporção máxima de barras tracionadas emendadas por traspasse na mesma seção | ausente | alta | P | P27 |
| `9.5.2.1-tab9.4-alpha0t` | 9.5.2.1 (Tabela 9.4) | 63 | Tabela 9.4 — coeficiente α0t por % de barras emendadas na mesma seção | implementado | alta | P |  |
| `9.5.2.2-l0t-traspasse-tracionado` | 9.5.2.2.1 | 63 | Comprimento de traspasse de barras tracionadas isoladas (ℓ0t) | implementado | alta | P |  |
| `9.5.2.2.2-l0t-distancia-maior-4phi` | 9.5.2.2.2 | 63 | Traspasse com distância livre entre barras >4φ | ausente | média | P | P27 |
| `9.5.2.3-l0c-traspasse-comprimido` | 9.5.2.3 | 63 | Comprimento de traspasse de barras comprimidas isoladas (ℓ0c) | implementado | alta | P |  |
| `9.5.2.4.1-armadura-transversal-emendas-tracionadas` | 9.5.2.4.1 | 64 | Armadura transversal nas emendas por traspasse — barras tracionadas | ausente | média | M | P27 |
| `9.5.2.4.2-armadura-transversal-emendas-comprimidas` | 9.5.2.4.2 | 64 | Armadura transversal nas emendas por traspasse — barras comprimidas | ausente | média | P | P27 |
| `9.5.2.4.3-armadura-transversal-emendas-secundarias` | 9.5.2.4.3 | 64 | Armadura transversal nas emendas de armaduras secundárias | ausente | baixa | P | P27 |
| `9.5.2.5-emenda-traspasse-feixe` | 9.5.2.5 | 64 | Emendas por traspasse em feixes de barras | ausente | baixa | M | P27 |
| `9.5.3-emendas-luvas` | 9.5.3 | 65 | Emendas mecânicas por luvas | ausente | média | P | P27 |
| `9.5.4-emendas-solda` | 9.5.4 | 65 | Emendas por solda — tipos, geometria e resistência | ausente | média | P | P27 |
| `9.6.1.1-forca-media` | 9.6.1.1 | 67 | Força média na armadura de protensão Pt(x) | ausente | média | P | P30 |
| `9.6.1.2.1-sigma-pi-limites` | 9.6.1.2.1 | 67 | Valores-limites de σpi na saída do aparelho de tração | ausente | média | P | P30 |
| `9.6.1.2.2-sigma-p0-termino` | 9.6.1.2.2 | 67 | Verificação de σp0(x) ao término da protensão | ausente | média | P | P30 |
| `9.6.1.2.3-tolerancia-execucao` | 9.6.1.2.3 | 67 | Tolerância de execução - majoração de σpi | ausente | baixa | P | P30 |
| `9.6.1.3-Pk-caracteristico` | 9.6.1.3 | 68 | Valores característicos superior/inferior da força de protensão | ausente | baixa | P | P30 |
| `9.6.1.4-Pd-calculo` | 9.6.1.4 | 68 | Valor de cálculo da força de protensão | ausente | média | P | P30 |
| `9.6.2.1-generalidades-qualitativo` | 9.6.2.1 | 68 | Distância de regularização - critério geral | não computável | baixa | P |  |
| `9.6.2.2-angulo-beta-difusao` | 9.6.2.2 | 68 | Ângulo de difusão da protensão em pós-tração | ausente | média | P | P31 |
| `9.6.2.3-lp-regularizacao` | 9.6.2.3 | 69 | Distância de regularização lp em elementos pré-tracionados | ausente | média | P | P31 |
| `9.6.3.1-generalidades-perdas-qualitativo` | 9.6.3.1 | 69 | Perdas de protensão a prever no projeto | não computável | baixa | P |  |
| `9.6.3.2-perdas-iniciais-qualitativo` | 9.6.3.2 | 69 | Perdas iniciais da força de protensão (pré-tração) | não computável | baixa | P |  |
| `9.6.3.3.1-encurtamento-pretracao` | 9.6.3.3.1 | 70 | Perda imediata por deformação do concreto na pré-tração | implementado | média | P |  |
| `9.6.3.3.2.1-encurtamento-postracao` | 9.6.3.3.2.1 | 70 | Perda por encurtamento do concreto entre grupos de cabos sucessivos (pós-tração) | parcial | média | P | P30 |
| `9.6.3.3.2.2-perda-atrito` | 9.6.3.3.2.2 | 70 | Perda de protensão por atrito cabo-bainha (pós-tração) | implementado | média | P |  |
| `9.6.3.3.2.2-tabela-mu-k` | 9.6.3.3.2.2 | 71 | Coeficientes de atrito μ e de perda por curvatura k | ausente | média | P | P30 |
| `9.6.3.3.2.3-deslizamento-qualitativo` | 9.6.3.3.2.3 | 71 | Perda por deslizamento da armadura e acomodação da ancoragem | não computável | média | P |  |
| `9.6.3.4.2-processo-simplificado` | 9.6.3.4.2 | 71 | Perda progressiva combinada - processo simplificado (fases únicas) | implementado | média | M |  |
| `9.6.3.4.2-deformacoes-aco-concreto` | 9.6.3.4.2 | 72 | Variação de deformação do aço e do concreto entre t0 e t | ausente | baixa | P | P30 |
| `9.6.3.4.3-processo-aproximado-RN` | 9.6.3.4.3 | 73 | Perda progressiva - processo aproximado, aço de relaxação normal (RN) | ausente | média | P | P30 |
| `9.6.3.4.3-processo-aproximado-RB` | 9.6.3.4.3 | 73 | Perda progressiva - processo aproximado, aço de relaxação baixa (RB) | ausente | média | P | P30 |
| `9.6.3.4.4-metodo-geral` | 9.6.3.4.4 | 73 | Método geral de cálculo das perdas progressivas (fases diferentes) | ausente | baixa | G | P43 |
| `9.6.3.4.5-psi-t` | 9.6.3.4.5 | 74 | Coeficiente de relaxação do aço no tempo ψ(t,t0) | implementado | média | P |  |
| `9.6.3.4.5-psi-infinito` | 9.6.3.4.5 | 74 | Relaxação no tempo infinito ψ(t∞, t0) | implementado | média | P |  |
| `9.6.3.4.5-psi-limite-tensao-minima` | 9.6.3.4.5 | 74 | Isenção de relaxação para tensões inferiores a 0,5 fptk | ausente | média | P | P30 |

## Seção 10

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `10.1-criterios-seguranca` | 10.1 | 74 | Critérios de segurança baseados na ABNT NBR 8681 | não computável | alta | P |  |
| `10.2-classificacao-estados-limites` | 10.2 | 74 | Classificação em estados-limites últimos e de serviço | não computável | alta | P |  |
| `10.3-lista-elu` | 10.3 | 74 | Rol dos estados-limites últimos a verificar (a-h) | parcial | média | M | P5 |
| `10.4-els` | 10.4 | 74 | Estados-limites de serviço (conforto, durabilidade, aparência) | não computável | alta | P |  |

## Seção 11

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `11.2.2-classificacao-acoes` | 11.2.2 | 76 | Classificação das ações (permanentes, variáveis, excepcionais) | ausente | alta | M | P4 |
| `11.3.2.1-peso-proprio` | 11.3.2.1 | 76 | Peso próprio da estrutura (remissão a 8.2.2) | não computável | alta | P |  |
| `11.3.2.2-peso-elementos-fixos` | 11.3.2.2 | 77 | Peso de elementos construtivos fixos e instalações (remissão a NBR 6120) | não computável | alta | P |  |
| `11.3.2.3-empuxos-permanentes` | 11.3.2.3 | 77 | Empuxos permanentes de terra e materiais granulosos não removíveis | não computável | média | P |  |
| `11.3.3.1-retracao-valor-simplificado` | 11.3.3.1 | 77 | Retração do concreto - valor simplificado εcs(t∞,t0) = −15·10⁻⁵ | parcial | média | P | P7 |
| `11.3.3.2-fluencia-deformacao-total` | 11.3.3.2 | 78 | Deformação total do concreto por fluência (processo simplificado) | parcial | média | P | P7 |
| `11.3.3.3-deslocamentos-apoio` | 11.3.3.3 | 78 | Deslocamentos de apoio como ação permanente indireta | não computável | média | P |  |
| `11.3.3.4.1-desaprumo-global` | 11.3.3.4.1 | 79 | Imperfeições geométricas globais - desaprumo (θ1, θa) | ausente | alta | M | P26 |
| `11.3.3.4.1-combinacao-vento-desaprumo` | 11.3.3.4.1 | 79 | Regra de combinação entre vento e desaprumo global (30%) | ausente | alta | M | P26 |
| `11.3.3.4.2-imperfeicao-local` | 11.3.3.4.2 | 80 | Imperfeições geométricas locais (falta de retilineidade / desaprumo do lance de pilar) | implementado | alta | P |  |
| `11.3.3.4.3-m1d-min-uniaxial` | 11.3.3.4.3 | 80 | Momento mínimo de 1a ordem para substituir imperfeições locais (uniaxial) | implementado | alta | P |  |
| `11.3.3.4.3-envoltoria-minima-1a-ordem` | 11.3.3.4.3 | 81 | Envoltória mínima de 1a ordem (flexão composta oblíqua, Figura 11.3) | implementado | alta | G |  |
| `11.3.3.5-protensao-acao` | 11.3.3.5 | 81 | Ação da protensão como ação permanente indireta | parcial | média | G | fora: Os esforços hiperestáticos de protensão exigem a análise da estrutura contínua, que é do TQS. A parcela isostática já existe, e o P30 entrega Pd,t. |
| `11.4.1.1-cargas-utilizacao` | 11.4.1.1 | 81 | Cargas variáveis de utilização (verticais, móveis, impacto, frenagem, força centrífuga) | não computável | alta | P |  |
| `11.4.1.2-acao-vento` | 11.4.1.2 | 82 | Ação do vento (remissão a NBR 6123) | ausente | alta | G | fora: O vento é da NBR 6123. A biblioteca recebe os esforços de vento prontos, combina-os (P4) e os compara com o desaprumo (P26). |
| `11.4.1.3-acao-agua` | 11.4.1.3 | 82 | Ação da água em reservatórios/tanques e água de chuva retida | ausente | baixa | P | P4 |
| `11.4.1.4-acoes-fase-construtiva` | 11.4.1.4 | 82 | Ações variáveis durante a construção (fases construtivas) | não computável | média | P |  |
| `11.4.2.1-temperatura-uniforme` | 11.4.2.1 | 82 | Variação uniforme de temperatura - faixas por dimensão do elemento | ausente | média | P | P4 |
| `11.4.2.2-temperatura-nao-uniforme` | 11.4.2.2 | 83 | Variação não uniforme de temperatura (gradiente entre faces) | ausente | baixa | P | P4 |
| `11.4.2.3-acoes-dinamicas` | 11.4.2.3 | 83 | Ações dinâmicas (choques, vibrações, fadiga - remissão a Seção 23) | não computável | baixa | P |  |
| `11.5-acoes-excepcionais` | 11.5 | 83 | Ações excepcionais (valores por normas específicas) | ausente | baixa | P | P4 |
| `11.6.1.1-valores-caracteristicos-permanentes` | 11.6.1.1 | 83 | Valores característicos de ações permanentes = valores médios | não computável | média | P |  |
| `11.6.1.2-valores-caracteristicos-variaveis` | 11.6.1.2 | 83 | Valores característicos de ações variáveis (25%-35% de probabilidade de ultrapassagem) | não computável | baixa | P |  |
| `11.6.2-valores-representativos` | 11.6.2 | 84 | Valores representativos das ações (característicos, convencionais excepcionais, reduzidos) | ausente | alta | P | P4 |
| `11.6.3-valores-calculo` | 11.6.3 | 84 | Valores de cálculo das ações Fd = γf·Frep | ausente | alta | P | P4 |
| `11.7-gamma_f-decomposicao` | 11.7 | 84 | Decomposição γf = γf1·γf2·γf3 | parcial | alta | P | P4 |
| `11.7.1-gamma_n-esbeltos-remissao` | 11.7.1 | 84 | Remissão ao γn para elementos esbeltos críticos (pilares/pilares-parede/lajes em balanço < 19 cm) | parcial | alta | P | P10 |
| `11.7.1-tabela-11.1-gamma_f` | 11.7.1 | 85 | Tabela 11.1 - Coeficiente γf = γf1·γf3 por tipo de ação e combinação | parcial | alta | P | P4 |
| `11.7.1-tabela-11.2-gamma_f2-psi` | 11.7.1 | 85 | Tabela 11.2 - Valores de γf2 (ψ0, ψ1, ψ2) por tipo de ação variável | ausente | alta | P | P4 |
| `11.7.1-mesmo-gamma-carga-permanente` | 11.7.1 | 86 | Regra: mesmo γf para cargas permanentes de mesma origem em toda a estrutura | não computável | média | P |  |
| `11.7.2-gamma_f-els` | 11.7.2 | 86 | Coeficiente de ponderação das ações para ELS: γf = γf2 | ausente | alta | P | P4 |
| `11.8.2.1-combinacao-ultima-normal` | 11.8.2.1 / 11.8.2.4 (Tabela 11.3) | 87 | Combinação última normal para concreto armado - Fd | ausente | alta | M | P4 |
| `11.8.2.1-perda-equilibrio-corpo-rigido` | 11.8.2.1 (Tabela 11.3) | 87 | Verificação de perda de equilíbrio como corpo rígido (Fsd ≥ Fnd) | ausente | média | M | P5 |
| `11.8.2.1-combinacao-ultima-protendido` | 11.8.2.1 (Tabela 11.3) | 87 | Força de protensão como carregamento externo na combinação última (Pk,máx/Pk,mín) | não computável | média | P |  |
| `11.8.2.2-combinacao-ultima-especial-construcao` | 11.8.2.2 / 11.8.2.4 (Tabela 11.3) | 87 | Combinação última especial ou de construção - Fd | ausente | média | M | P4 |
| `11.8.2.3-combinacao-ultima-excepcional` | 11.8.2.3 / 11.8.2.4 (Tabela 11.3) | 87 | Combinação última excepcional - Fd | ausente | baixa | M | P4 |
| `11.8.3.1-classificacao-combinacoes-servico` | 11.8.3.1 | 88 | Classificação das combinações de serviço (quase permanentes, frequentes, raras) e seu uso | não computável | alta | P |  |
| `11.8.3.2-combinacao-quase-permanente-servico` | 11.8.3.2 (Tabela 11.4) | 89 | Combinação quase permanente de serviço (CQP) - Fd,ser | ausente | alta | P | P4 |
| `11.8.3.2-combinacao-frequente-servico` | 11.8.3.2 (Tabela 11.4) | 89 | Combinação frequente de serviço (CF) - Fd,ser | ausente | alta | P | P4 |
| `11.8.3.2-combinacao-rara-servico` | 11.8.3.2 (Tabela 11.4) | 89 | Combinação rara de serviço (CR) - Fd,ser | ausente | alta | P | P4 |

## Seção 12

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `12.2-resistencia-caracteristica-conceito` | 12.2 | 90 | Conceito de resistência característica (fk,inf com 5% de não superação) | não computável | média | P |  |
| `12.3.1-resistencia-calculo-generica` | 12.3.1 | 90 | Resistência de cálculo genérica fd = fk/γm | implementado | alta | P |  |
| `12.3.2-tensoes-resistentes-calculo` | 12.3.2 | 90 | Tensões resistentes de cálculo σRd, τRd (definição conceitual) | não computável | média | P |  |
| `12.3.3-fcd-28dias` | 12.3.3-a | 90 | Resistência de cálculo do concreto para verificação em j ≥ 28 dias | implementado | alta | P |  |
| `12.3.3-fcd-antes-28dias` | 12.3.3-b | 90 | Resistência de cálculo do concreto para verificação em j < 28 dias (β1, s por cimento) | implementado | alta | P |  |
| `12.4-gamma_m-decomposicao` | 12.4 | 91 | Decomposição γm = γm1·γm2·γm3 | parcial | baixa | P | P5 |
| `12.4.1-tabela-12.1-gamma_c_gamma_s` | 12.4.1 | 91 | Tabela 12.1 - Valores de γc e γs por tipo de combinação | implementado | alta | P |  |
| `12.4.1-gamma_c-condicoes-desfavoraveis` | 12.4.1 | 91 | Majoração de γc por 1,1 em condições desfavoráveis de execução | ausente | baixa | P | P5 |
| `12.4.1-gamma_c-testemunhos-extraidos` | 12.4.1 | 91 | Redução de γc dividindo por 1,1 no caso de testemunhos extraídos | ausente | baixa | P | P5 |
| `12.4.1-gamma_s-ca25-sem-controle` | 12.4.1 | 91 | Majoração de γs por 1,1 para CA-25 sem controle de qualidade da NBR 7480 | ausente | baixa | P | P5 |
| `12.4.2-gamma_m-els-unitario` | 12.4.2 | 92 | Coeficiente de ponderação das resistências no ELS: γm = 1,0 | implementado | média | P |  |
| `12.5.1-condicoes-construtivas-seguranca` | 12.5.1 | 92 | Condições construtivas de segurança (detalhamento, controle de materiais, execução) | não computável | média | P |  |
| `12.5.2-Rd-Sd` | 12.5.2 | 92 | Condição analítica de segurança Rd ≥ Sd | implementado | média | P |  |
| `12.5.3-esforcos-resistentes-calculo` | 12.5.3 | 92 | Esforços resistentes de cálculo (remissão a 12.3.1 e Seções 17/19/23) | não computável | média | P |  |
| `12.5.4-esforcos-solicitantes-calculo` | 12.5.4 | 92 | Esforços solicitantes de cálculo (remissão a Seção 14, análise estrutural) | não computável | média | P |  |

## Seção 13

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `13.2.2-largura-min-viga` | 13.2.2 | 93 | Largura mínima de viga e viga-parede | ausente | alta | P | P10 |
| `13.2.3-dim-min-pilar` | 13.2.3 | 93 | Dimensão mínima e área mínima de pilar/pilar-parede | ausente | alta | P | P10 |
| `13.2.3-gama_n` | 13.2.3, Tabela 13.1 | 94 | Coeficiente adicional γn para pilares e pilares-parede (Tabela 13.1) | ausente | alta | P | P10 |
| `13.2.4.1-espessura-min-laje` | 13.2.4.1 | 94 | Espessuras mínimas de lajes maciças (lista a-g) | ausente | alta | M | P10 |
| `13.2.4.1-tab13.2-gama_n-laje-balanco` | 13.2.4.1, Tabela 13.2 | 94 | Tabela 13.2 - Coeficiente adicional γn para lajes em balanço (fórmula linear em função de h) | implementado | média | P | P10 |
| `13.2.4.2-espessura-min-mesa-nervurada` | 13.2.4.2 | 95 | Espessura mínima da mesa de laje nervurada | ausente | alta | P | P10 |
| `13.2.4.2-espessura-min-nervura` | 13.2.4.2 | 95 | Espessura mínima de nervura e restrição à armadura de compressão | ausente | alta | P | P10 |
| `13.2.4.2-classificacao-espacamento-nervuras` | 13.2.4.2 a-c | 95 | Classificação do espaçamento entre nervuras e regra de verificação aplicável | ausente | alta | P | P10 |
| `13.2.4.3-lajes-pre-moldadas` | 13.2.4.3 | 95 | Remissão a normas de lajes pré-moldadas e alveolares protendidas | não computável | média | P |  |
| `13.2.5-furos-aberturas-intro` | 13.2.5 | 95 | Princípio geral de furos e aberturas em elementos estruturais | não computável | média | P |  |
| `13.2.5.1-furo-viga-largura-dispensa` | 13.2.5.1 | 95 | Condições para dispensa de verificação de furo transversal em viga (direção da largura) | ausente | média | M | P10 |
| `13.2.5.2-abertura-laje-dispensa` | 13.2.5.2, Figura 13.1 | 96 | Dimensões-limites para aberturas em lajes com dispensa de verificação | ausente | média | M | P10 |
| `13.2.6-canalizacoes-embutidas-proibicoes` | 13.2.6 | 96 | Casos proibidos de canalização embutida | ausente | baixa | P | P10 |
| `13.3-tab13.3-aceitabilidade-sensorial` | 13.3, Tabela 13.3 | 97 | Deslocamento-limite por aceitabilidade sensorial (visual e vibração) | ausente | alta | P | P8 |
| `13.3-tab13.3-efeitos-estruturais-servico` | 13.3, Tabela 13.3 | 98 | Deslocamento-limite por efeitos estruturais em serviço (drenagem, planicidade, equipamentos sensíveis) | ausente | alta | P | P8 |
| `13.3-tab13.3-elementos-nao-estruturais-paredes` | 13.3, Tabela 13.3, notas c-e | 98 | Deslocamento-limite para paredes, divisórias e movimento lateral do edifício | ausente | alta | P | P8 |
| `13.3-tab13.3-forros-pontes-rolantes` | 13.3, Tabela 13.3 | 98 | Deslocamento-limite para forros e pontes rolantes | ausente | baixa | P | P8 |
| `13.3-tab13.3-efeitos-elementos-estruturais` | 13.3, Tabela 13.3 | 99 | Efeitos em elementos estruturais - deslocamentos incorporados ao modelo | não computável | média | P |  |
| `13.3-notas-vao-equivalente-balanco` | 13.3, NOTA 1 e NOTA 2 | 99 | Regra do vão equivalente para deslocamento-limite em balanços e placas | ausente | média | P | P8 |
| `13.3-nota3-combinacao-deslocamento` | 13.3, NOTA 3, NOTA 5, NOTA 6 | 99 | Combinação de ações para deslocamento total e flecha diferida | parcial | alta | M | P8 |
| `13.4.1-fissuracao-intro` | 13.4.1 | 99 | Princípio geral do controle de fissuração | não computável | média | P |  |
| `13.4.2-outras-causas-fissuracao` | 13.4.2 (paragrafo introdutorio) | 100 | Outras causas de fissuração (retração plástica, térmica, reações químicas internas) | não computável | baixa | P |  |
| `13.4.2-tab13.4-wk-max-caa` | 13.4.2, Tabela 13.4 | 100 | Abertura máxima wk pela classe de agressividade e tipo de concreto/protensão (Tabela 13.4) | parcial | alta | M | P1 |
| `13.4.3-aceitabilidade-sensorial-fissura` | 13.4.3 | 101 | Controle de fissuração por aceitabilidade sensorial e utilização | não computável | média | P |  |

## Seção 14

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `14.2.1-objetivo-analise` | 14.2.1 | 102 | Objetivo da análise estrutural | não computável | baixa | P |  |
| `14.2.2-premissas-modelo` | 14.2.2 | 102 | Premissas do modelo estrutural (adequação, discretização, interação solo-estrutura) | não computável | baixa | P |  |
| `14.2.3-14.2.4-aplicacao-resultados` | 14.2.3/14.2.4 | 103 | Aplicação dos resultados de modelos lineares e não lineares (regra geral de dimensionamento) | não computável | baixa | P |  |
| `14.3.1-ordem-equilibrio` | 14.3.1 | 103 | Escolha entre teoria de 1a e 2a ordem para as equações de equilíbrio | não computável | média | P |  |
| `14.3.2-compatibilidade` | 14.3.2 | 104 | Condições de compatibilidade e dutilidade quando não verificadas | não computável | baixa | P |  |
| `14.3.3-tensao-max-ciclica` | 14.3.3 | 104 | Limite de tensão de compressão em serviço para admitir carregamento monotônico | ausente | baixa | P | P14 |
| `14.4.1-classif-elemento-linear` | 14.4.1 | 104 | Critério de classificação de elemento linear (barra) por proporção geométrica | ausente | baixa | P | P11 |
| `14.4.1.1-14.4.1.4-classif-funcional` | 14.4.1.1 a 14.4.1.4 | 104 | Classificação funcional dos elementos lineares (viga, pilar, tirante, arco) | não computável | baixa | P |  |
| `14.4.2.1-placa-espessa` | 14.4.2.1 | 104 | Critério de placa espessa (espessura maior que 1/3 do vão) | ausente | média | P | P11 |
| `14.4.2.2-viga-parede-classif` | 14.4.2.2 | 105 | Critério de classificação de viga-parede (chapa com vão menor que 3x a maior dimensão da seção) | ausente | média | P | P11 |
| `14.4.2.3-cascas-definicao` | 14.4.2.3 | 105 | Definição de casca (elemento de superfície não plana) | não computável | baixa | P |  |
| `14.4.2.4-pilar-parede-classif` | 14.4.2.4 | 105 | Critério de classificação de pilar-parede (menor dimensão menor que 1/5 da maior, na seção transversal) | ausente | média | P | P11 |
| `14.5.1-metodos-generalidades` | 14.5.1 | 105 | Generalidades sobre os métodos de análise estrutural (14.5.2 a 14.5.6) | não computável | baixa | P |  |
| `14.5.2-analise-linear` | 14.5.2 | 105 | Análise linear - hipóteses (comportamento elástico-linear, seção bruta, Ecs) | não computável | baixa | P |  |
| `14.5.3-analise-redistrib-geral` | 14.5.3 | 106 | Análise linear com redistribuição - condições gerais | não computável | média | P |  |
| `14.5.4-analise-plastica-restricoes` | 14.5.4 | 106 | Restrições ao uso de análise plástica em estruturas reticuladas | ausente | média | P | P11 |
| `14.5.5-analise-nao-linear-geral` | 14.5.5 | 106 | Análise não linear - condições gerais (geometria e armaduras completas, equilíbrio/compatibilidade/dutilidade) | não computável | baixa | P |  |
| `14.5.6-modelos-fisicos` | 14.5.6 | 106 | Análise por modelos físicos (ensaios) - condições e margens de segurança | não computável | baixa | P |  |
| `14.6.1-hipoteses-elementos-lineares` | 14.6.1 | 107 | Hipóteses básicas para estruturas de elementos lineares (seção plana, eixo, comprimento entre apoios) | não computável | baixa | P |  |
| `14.6.2.1-trecho-rigido` | 14.6.2.1 | 108 | Extensão do trecho rígido no cruzamento de elementos lineares (Figura 14.1) | ausente | alta | P | P14 |
| `14.6.2.2-vao-a-mesa` | 14.6.2.2 | 108 | Distância a entre pontos de momento fletor nulo (para largura colaborante) | implementado | alta | P |  |
| `14.6.2.2-largura-colaborante` | 14.6.2.2 | 109 | Largura colaborante bf de viga T/L (limites b1, b3 conforme Figura 14.2) | parcial | alta | M | P14 |
| `14.6.2.2-largura-efetiva-abertura` | 14.6.2.2 | 109 | Largura efetiva bef da mesa colaborante na presença de abertura na laje (Figura 14.3) | ausente | média | M | P14 |
| `14.6.2.3-misulas-secao-efetiva` | 14.6.2.3 | 109 | Seção efetiva em mísulas e variações bruscas de seção (Figura 14.4) | ausente | alta | M | P14 |
| `14.6.2.4-vao-efetivo-viga` | 14.6.2.4 | 110 | Vão efetivo de vigas (lef = l0 + a1 + a2) | implementado | alta | P |  |
| `14.6.3-arredondamento-momentos` | 14.6.3 | 111 | Arredondamento do diagrama de momentos fletores sobre apoios/cargas concentradas (Figura 14.6) | ausente | alta | P | P14 |
| `14.6.4.1-rigidez-vigas-pilares` | 14.6.4.1 | 111 | Valores de rigidez para análise linear (Ecs, momento de inércia bruto; flechas com fissuração/fluência) | não computável | média | P |  |
| `14.6.4.2-restricoes-redistribuicao` | 14.6.4.2 | 111 | Restrições à redistribuição em pilares, elementos comprimidos e consolos | não computável | média | P |  |
| `14.6.4.3-xd-dutilidade` | 14.6.4.3 | 112 | Limite de x/d para dutilidade sem redistribuição (0,45 / 0,35) | implementado | alta | P |  |
| `14.6.4.3-xd-redistribuicao` | 14.6.4.3 | 112 | Limite de x/d quando há redistribuição de momento (função do coeficiente δ) | ausente | alta | P | P13 |
| `14.6.4.3-delta-min` | 14.6.4.3 | 112 | Limite mínimo do coeficiente de redistribuição (δ ≥ 0,75) | ausente | alta | P | P13 |
| `14.6.4.4-rotacao-plastica` | 14.6.4.4 | 112 | Capacidade de rotação plástica admissível (Figura 14.7) e fator de correção a/d | ausente | média | G | P13 |
| `14.6.4.4-dispensa-verificacao-rotacao` | 14.6.4.4 | 113 | Dispensa da verificação explícita de rotação plástica (x/d ≤ 0,25 / 0,15) | ausente | média | P | P13 |
| `14.6.5-analise-nao-linear-elementos-lineares` | 14.6.5 | 113 | Análise não linear de elementos lineares - aplicabilidade a ELU e ELS | não computável | baixa | P |  |
| `14.6.6.1-vigas-continuas-momento-minimo` | 14.6.6.1 | 113 | Correções de momento mínimo no modelo de viga contínua simplesmente apoiada nos pilares | ausente | alta | M | P14 |
| `14.6.6.1-coeficientes-engastamento-apoio-extremo` | 14.6.6.1 | 114 | Coeficientes de momento de engastamento perfeito nos apoios extremos (rigidez de pilares/viga, Figura 14.8) | ausente | alta | M | P14 |
| `14.6.6.2-reducao-rigidez-torcao-grelha` | 14.6.6.2 | 115 | Redução da rigidez à torção das vigas em modelos de grelha/pórtico espacial (15% da rigidez elástica) | ausente | alta | P | P14 |
| `14.6.6.3-dispensa-alternancia-cargas` | 14.6.6.3 | 115 | Dispensa de alternância de cargas variáveis em edifícios (q ≤ 5 kN/m² e ≤ 50% da carga total) | ausente | alta | P | P14 |
| `14.6.6.4-diafragma-rigido` | 14.6.6.4 | 115 | Critério para considerar a laje como diafragma rígido em seu plano | ausente | alta | P | P14 |
| `14.7.1-hipoteses-placas` | 14.7.1 | 115 | Hipóteses básicas de estruturas de placas (seção plana em faixas estreitas, plano médio) | não computável | baixa | P |  |
| `14.7.2.2-vao-efetivo-laje` | 14.7.2.2 | 116 | Vão efetivo de lajes/placas (mesma fórmula lef = l0+a1+a2 de 14.6.2.4) | implementado | alta | P |  |
| `14.7.3-poisson-placas` | 14.7.3 | 116 | Coeficiente de Poisson para análise elástica de placas (ν = 0,2) | ausente | baixa | P | P2 |
| `14.7.3.1-rigidez-estadio-I-placas` | 14.7.3.1 | 116 | Rigidez do Estadio I para verificação de flecha em placas (momento fletor menor que o de fissuração) | não computável | média | P |  |
| `14.7.3.2-redistribuicao-lajes` | 14.7.3.2 | 116 | Limites de x/d para redistribuição de momentos em placas (mesmas fórmulas de 14.6.4.3) | ausente | alta | P | P13 |
| `14.7.4-xd-limite-plastico-laje` | 14.7.4 | 116 | Limite de x/d para dispensa de verificação de rotação na análise plástica de lajes (charneiras) | ausente | média | P | P13 |
| `14.7.4-razao-momentos-borda-vao` | 14.7.4 | 116 | Razão mínima entre momentos de borda e de vão na análise plástica de lajes retangulares (1,5:1) | ausente | média | P | P13 |
| `14.7.5-analise-nao-linear-placas` | 14.7.5 | 117 | Análise não linear de placas - aplicabilidade a ELU e ELS | não computável | baixa | P |  |
| `14.7.6.1-reacoes-apoio-charneiras` | 14.7.6.1 | 117 | Reações de apoio de lajes maciças retangulares pelo método das charneiras plásticas (triângulos/trapézios) | parcial | alta | G | P17 |
| `14.7.6.2-compatibilizacao-momentos` | 14.7.6.2 | 117 | Compatibilização de momentos negativos entre lajes vizinhas | parcial | alta | P | P17 |
| `14.7.7-lajes-nervuradas-grelha-vigas` | 14.7.7 | 117 | Cálculo da laje nervurada como grelha de vigas quando as hipóteses de laje maciça não se aplicam | ausente | alta | G | fora: Modelar a laje nervurada como grelha é análise estrutural, feita no TQS. Os limites que tornam isso obrigatório estão no P10. |
| `14.7.7-lajes-nervuradas-unidirecionais` | 14.7.7 | 118 | Lajes nervuradas unidirecionais: cálculo na direção das nervuras, com rigidez transversal e à torção desprezadas | não computável | alta | P |  |
| `14.7.8-analise-numerica-lajes-lisas` | 14.7.8 | 118 | Exigência de procedimento numérico para análise de lajes lisas e lajes-cogumelo | não computável | alta | P |  |
| `14.7.8-portico-equivalente` | 14.7.8 | 118 | Processo elástico aproximado (pórticos múltiplos com redistribuição) para lajes lisas/cogumelo com pilares em filas regulares | ausente | alta | G | fora: Montar e resolver o pórtico múltiplo é análise estrutural, feita no TQS. A repartição dos momentos entre faixas está no P17. |
| `14.7.8-faixas-distribuicao-momento` | 14.7.8 | 118 | Distribuição percentual dos momentos do pórtico equivalente entre faixas internas e externas (Figura 14.9) | ausente | alta | P | P17 |
| `14.8.1-vigas-parede-pilares-parede-analise` | 14.8.1 | 119 | Método de análise de vigas-parede e pilares-parede (linear/não linear; representação como elemento linear equivalente) | não computável | média | P |  |
| `14.8.2-blocos-analise` | 14.8.2 | 119 | Método de análise de blocos de fundação (linear, plástica ou não linear) | não computável | média | P |  |

## Seção 15

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `15.2-conceitos-2a-ordem` | 15.2 | 120 | Conceitos fundamentais de instabilidade e efeitos de 2ª ordem | não computável | alta | P |  |
| `15.3-principio-nao-linearidade` | 15.3 | 120 | Princípio básico de cálculo com efeitos de 2ª ordem | não computável | alta | P |  |
| `15.3-combinacao-sdtot` | 15.3 | 121 | Formulação de segurança da combinação para 2ª ordem (Sd,tot) | parcial | média | P | P4 |
| `15.3.1-rigidez-secante-ei-sec` | 15.3.1 | 121 | Rigidez secante (EI)sec pela relação momento-curvatura (Figura 15.1) | implementado | média | G |  |
| `15.3.1-kappa-sec-adimensional` | 15.3.1 | 122 | Rigidez secante adimensional κsec | ausente | baixa | P | P25 |
| `15.3.2-envoltoria-minima-2a-ordem` | 15.3.2 | 122 | Envoltória mínima com 2ª ordem (Figura 15.2) | parcial | alta | M | P25 |
| `15.4.1-efeitos-globais-locais-localizados` | 15.4.1 | 122 | Definições de efeitos globais, locais e localizados de 2ª ordem | não computável | alta | P |  |
| `15.4.2-classificacao-nos-fixos-moveis` | 15.4.2 | 123 | Classificação da estrutura em nós fixos ou nós móveis | ausente | alta | P | P26 |
| `15.4.3-contraventamento` | 15.4.3 | 123 | Subestruturas de contraventamento e elementos contraventados | não computável | média | P |  |
| `15.4.4-elementos-isolados` | 15.4.4 | 124 | O que é considerado elemento isolado para análise local | não computável | média | P |  |
| `15.5.1-majoracao-ecs-analise-global` | 15.5.1 | 124 | Majoração de 10% do módulo de deformação secante na análise de estabilidade global | ausente | média | P | P26 |
| `15.5.2-parametro-instabilidade-alfa` | 15.5.2 | 124 | Parâmetro de instabilidade α | ausente | alta | P | P26 |
| `15.5.2-alfa1-limite` | 15.5.2 | 124 | Valor-limite α1 do parâmetro de instabilidade | ausente | alta | P | P26 |
| `15.5.2-rigidez-pilar-equivalente` | 15.5.2 | 125 | Rigidez EcsIc de um pilar equivalente (para α e γz) | ausente | alta | G | P26 |
| `15.5.3-coeficiente-gama-z` | 15.5.3 | 125 | Coeficiente γz de avaliação dos esforços globais de 2ª ordem | ausente | alta | P | P26 |
| `15.6-comprimento-equivalente-nos-fixos` | 15.6 | 125 | Comprimento equivalente ℓe do pilar em estrutura de nós fixos | ausente | alta | P | P25 |
| `15.7.2-processo-aproximado-095-gamaz` | 15.7.2 | 126 | Processo aproximado de majoração das ações horizontais por 0,95 γz | ausente | alta | M | P26 |
| `15.7.3-rigidez-aproximada-analise-global` | 15.7.3 | 126 | Rigidezes aproximadas para consideração da não linearidade física na análise global | ausente | alta | P | P26 |
| `15.7.4-efeitos-locais-em-nos-moveis` | 15.7.4 | 127 | Encadeamento dos esforços globais de 2ª ordem para a análise local em nós móveis | ausente | alta | M | P25 |
| `15.8.1-limite-esbeltez-200` | 15.8.1 | 127 | Limite geral de esbeltez para elementos isolados (λ ≤ 200) | ausente | alta | P | P25 |
| `15.8.1-n1-majoracao-lambda140` | 15.8.1 | 127 | Coeficiente adicional γn1 para esbeltez > 140 | parcial | alta | P | P25 |
| `15.8.2-lambda-esbeltez-basico` | 15.8.2 | 127 | Índice de esbeltez λ = ℓe/i | parcial | média | P | P25 |
| `15.8.2-lambda1-limite-esbeltez` | 15.8.2 | 128 | Esbeltez-limite λ1 para dispensa dos efeitos locais de 2ª ordem | implementado | alta | P |  |
| `15.8.2-alfa-b` | 15.8.2 | 128 | Coeficiente αb (forma do diagrama de momentos de 1ª ordem) | implementado | alta | M |  |
| `15.8.3.1-escolha-metodo-fluencia-obrigatoria` | 15.8.3.1 | 129 | Escolha entre método geral e métodos aproximados; obrigatoriedade da fluência para λ>90 | não computável | alta | P |  |
| `15.8.3.2-metodo-geral` | 15.8.3.2 | 129 | Método geral (análise não linear de 2ª ordem por discretização) | ausente | alta | G | P28 |
| `15.8.3.3.2-md-tot-curvatura-aprox` | 15.8.3.3.2 | 129 | Método do pilar-padrão com curvatura aproximada | implementado | alta | M |  |
| `15.8.3.3.3-md-tot-rigidez-kappa-aprox` | 15.8.3.3.3 | 130 | Método do pilar-padrão com rigidez κ aproximada | implementado | alta | M |  |
| `15.8.3.3.4-metodo-diagramas-mn1r` | 15.8.3.3.4 | 130 | Método do pilar-padrão acoplado a diagramas M, N, 1/r | ausente | média | G | P28 |
| `15.8.3.3.5-pilar-padrao-flexao-obliqua` | 15.8.3.3.5 | 131 | Método do pilar-padrão para flexão composta oblíqua (duas direções simultâneas) | ausente | alta | G | P25 |
| `15.8.4-fluencia-ecc` | 15.8.4 | 131 | Excentricidade adicional de fluência ecc para pilares esbeltos (λ>90) | ausente | média | M | P25 |
| `15.9.1-pilar-parede-generalidades` | 15.9.1 | 131 | Condição para pilar-parede ser tratado como elemento linear | não computável | média | P |  |
| `15.9.2-esbeltez-lamina-pilar-parede` | 15.9.2 | 132 | Esbeltez λi de cada lâmina do pilar-parede e dispensa dos efeitos localizados | ausente | média | P | P29 |
| `15.9.2-comprimento-equivalente-lamina` | 15.9.2 | 132 | Comprimento equivalente ℓe de lâmina de pilar-parede por vinculação (Figura 15.4) | ausente | média | M | P29 |
| `15.9.3-faixas-verticais-pilar-parede` | 15.9.3 | 133 | Decomposição do pilar-parede em faixas verticais para efeito localizado de 2ª ordem | ausente | média | M | P29 |
| `15.10-instabilidade-lateral-vigas` | 15.10 | 134 | Verificação aproximada de instabilidade lateral (flambagem lateral) de vigas | ausente | baixa | P | P12 |

## Seção 16

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `16.1-objetivo` | 16.1 | 134 | Objetivo do dimensionamento, verificação e detalhamento | não computável | baixa | P |  |
| `16.2.1-generalidades` | 16.2.1 | 135 | Princípios gerais (generalidades) | não computável | baixa | P |  |
| `16.2.2-visao-global-local` | 16.2.2 | 135 | Visão global e local do projeto | não computável | baixa | P |  |
| `16.2.3-seguranca-elu` | 16.2.3 | 135 | Segurança em relação aos ELU e exigência de dutilidade | não computável | baixa | P |  |
| `16.2.4-seguranca-els` | 16.2.4 | 136 | Segurança em relação aos ELS (desempenho em serviço) | não computável | baixa | P |  |
| `16.3-criterios-projeto` | 16.3 | 136 | Organização dos critérios de projeto por seção (17 a 24) | não computável | baixa | P |  |
| `16.4-durabilidade` | 16.4 | 137 | Durabilidade como condição para a segurança ao longo da vida útil | não computável | baixa | P |  |
| `16.5-cargas-ciclicas` | 16.5 | 137 | Efeitos de cargas cíclicas significativas (pontes, vigas de rolamento) | não computável | baixa | P |  |

## Seção 17

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `17.1-simbologia` | 17.1 | 137 | Simbologia específica da Seção 17 | não computável | baixa | P |  |
| `17.1-omega-min` | 17.1 | 140 | Taxa mecânica mínima de armadura de flexão (wmin) | ausente | baixa | P | P12 |
| `17.2.1-introducao-envoltoria` | 17.2.1 | 140 | Envoltória de esforços resistentes (NRd,MRd) sobre (NSd,MSd) | não computável | alta | P |  |
| `17.2.2ab-hipoteses-planas-aderencia` | 17.2.2 | 140 | Hipóteses de seções planas e aderência perfeita (a, b) | não computável | alta | P |  |
| `17.2.2c-delta-sigma-p-nao-aderente` | 17.2.2 c) | 140 | Acréscimo de tensão em armadura ativa não aderente (Dsp) | ausente | média | P | P32 |
| `17.2.2d-tracao-desprezada-elu` | 17.2.2 d) | 141 | Tensão de tração no concreto desprezada no ELU | não computável | alta | P |  |
| `17.2.2e-lambda-alfac-tensao-retangulo` | 17.2.2 e) | 141 | Bloco retangular equivalente: λ, αc e tensão constante | implementado | alta | P |  |
| `17.2.2f-tensao-armaduras-diagramas` | 17.2.2 f) | 141 | Tensão nas armaduras pelos diagramas tensão-deformação (8.3.6/8.4.5) | não computável | alta | P |  |
| `17.2.2g-limites-dominios` | 17.2.2 g) | 142 | Limites de linha neutra entre domínios e deformações da Figura 17.1 | implementado | alta | P |  |
| `17.2.2g-classificacao-dominio` | 17.2.2 g) | 142 | Classificação explícita do domínio de deformação (reta a, 1 a 5, 4a, reta b) | parcial | média | M | P28 |
| `17.2.3-dutilidade-vigas` | 17.2.3 | 142 | Dutilidade em vigas: limite de x/d (remete a 14.6.4.3) | parcial | alta | P | P12 |
| `17.2.4.1-forcas-concentradas-10pct-h` | 17.2.4.1 | 143 | Concentração das forças de armadura no centroide (critério 10% h) | ausente | baixa | P | P12 |
| `17.2.4.1-armaduras-laterais-vigas` | 17.2.4.1 | 143 | Armaduras laterais de vigas podem entrar no cálculo dos esforços resistentes | não computável | média | P |  |
| `17.2.4.2.1-protensao-hiperestatica-pre-alongamento` | 17.2.4.2.1 | 143 | Protensão no ELU: só hiperestáticos e pré-alongamento com perdas | não computável | média | P |  |
| `17.2.4.3.1-fckj-especificado` | 17.2.4.3.1 | 143 | Especificação de fckj no projeto para o ato da protensão | não computável | baixa | P |  |
| `17.2.4.3.1-coeficientes-ato-protensao` | 17.2.4.3.1-b | 143 | Coeficientes de ponderação para o ELU no ato da protensão | ausente | média | P | P32 |
| `17.2.4.3.2-tensao-max-compressao` | 17.2.4.3.2-a | 144 | Tensão máxima de compressão no concreto no ato da protensão | ausente | média | P | P32 |
| `17.2.4.3.2-tensao-max-tracao` | 17.2.4.3.2-b | 144 | Tensão máxima de tração no concreto no ato da protensão | ausente | média | P | P32 |
| `17.2.4.3.2-armadura-tracao-estadio2` | 17.2.4.3.2-c | 144 | Armadura de tração no Estadio II para o ato da protensão | ausente | média | M | P32 |
| `17.2.4.4.1-limites-tensao-compressao-els` | 17.2.4.4.1 | 144 | Limites de tensão de compressão no concreto em serviço (protensão completa/limitada) | ausente | média | P | P32 |
| `17.2.4.4.2-limite-tensao-tracao-els` | 17.2.4.4.2 | 144 | Limite de tensão de tração no concreto (ELS-F / ELS-D) | parcial | média | M | P32 |
| `17.2.5-interacao-flexao-obliqua` | 17.2.5 | 145 | Processo aproximado de interação para flexão composta oblíqua | implementado | alta | P |  |
| `17.3.1-momento-fissuracao` | 17.3.1 | 145 | Momento de fissuração Mr | parcial | alta | M | P8 |
| `17.3.2.1.1-flecha-imediata-rigidez-equivalente` | 17.3.2.1.1 | 146 | Rigidez equivalente (EI)eq para flecha imediata (Branson) | ausente | alta | M | P8 |
| `17.3.2.1.2-flecha-diferida-alphaf-xi` | 17.3.2.1.2 | 147 | Coeficiente de fluência para flecha diferida (αf e ξ(t)) | parcial | alta | P | P8 |
| `17.3.2.1.3-flecha-armaduras-ativas` | 17.3.2.1.3 | 148 | Flecha em elementos com armaduras ativas | ausente | média | M | P32 |
| `17.3.3.2-abertura-fissura-wk` | 17.3.3.2 | 149 | Abertura característica de fissuras wk (Eq. 86 / Eq. 87) | implementado | alta | P |  |
| `17.3.3.2-area-envolvimento-acri` | 17.3.3.2 | 149 | Geometria da área de envolvimento Acri (Figura 17.4) | ausente | média | M | P9 |
| `17.3.3.3-tabela-17.2-controle-sem-wk` | 17.3.3.3 | 150 | Tabela 17.2 -- controle da fissuração sem verificar wk | ausente | média | P | P9 |
| `17.3.4-descompressao-formacao-fissuras` | 17.3.4 | 150 | Estados-limites de descompressão e de formação de fissuras (verificação direta) | parcial | média | M | P32 |
| `17.3.5.1-principios-basicos-as-min-max` | 17.3.5.1 | 151 | Princípios básicos das armaduras mínimas e máximas | não computável | alta | P |  |
| `17.3.5.2.1-md-min-as-min-vigas` | 17.3.5.2.1 | 151 | Momento mínimo e armadura mínima de tração em vigas | implementado | alta | P |  |
| `17.3.5.2.2-as-min-deformacao-imposta` | 17.3.5.2.2 | 152 | Armadura mínima de tração sob deformações impostas (estanqueidade/estética) | ausente | baixa | M | P9 |
| `17.3.5.2.3-armadura-pele` | 17.3.5.2.3 | 153 | Armadura de pele em vigas | ausente | alta | P | P12 |
| `17.3.5.2.4-as-max-tracao-compressao-vigas` | 17.3.5.2.4 | 153 | Soma máxima das armaduras de tração e compressão em vigas | ausente | alta | P | P12 |
| `17.3.5.3.1-as-min-pilar` | 17.3.5.3.1 | 153 | Armadura longitudinal mínima de pilares | implementado | alta | P |  |
| `17.3.5.3.2-as-max-pilar` | 17.3.5.3.2 | 153 | Armadura longitudinal máxima de pilares | implementado | alta | P |  |
| `17.4.1.1.1-asw-min` | 17.4.1.1.1 | 154 | Armadura transversal mínima (taxa geométrica) | implementado | alta | P |  |
| `17.4.1.1.2-excecoes-asw-min` | 17.4.1.1.2 | 154 | Exceções à armadura transversal mínima | ausente | média | P | P15 |
| `17.4.1.1.3-limite-barras-dobradas` | 17.4.1.1.3 | 155 | Limite de 60% para barras dobradas na Asw | ausente | baixa | P | P15 |
| `17.4.1.1.4-barras-soldadas` | 17.4.1.1.4 | 155 | Barras verticais soldadas combinadas com estribos | não computável | baixa | P |  |
| `17.4.1.1.5-alfa-estribo` | 17.4.1.1.5 | 155 | Faixa de inclinação da armadura transversal | implementado | alta | P |  |
| `17.4.1.1.6-espacamento-dependencia` | 17.4.1.1.6 | 155 | Espaçamentos máximos/mínimos da armadura transversal (remete a Seção 18) | não computável | alta | P |  |
| `17.4.1.2.1-reducao-vsd-apoio` | 17.4.1.2.1 | 155 | Redução de VSd para cargas próximas ao apoio | ausente | alta | M | P15 |
| `17.4.1.2.2-protensao-tangencial` | 17.4.1.2.2 | 155 | Efeito tangencial da protensão em VSd e condição de armadura longitudinal | ausente | média | P | P15 |
| `17.4.1.2.3-altura-variavel` | 17.4.1.2.3 | 155 | Força cortante resistida pela alma em elementos de altura variável | ausente | média | M | P15 |
| `17.4.2.1-condicao-dupla` | 17.4.2.1 | 156 | Condição dupla de resistência (VRd2 e VRd3) | parcial | alta | P | P15 |
| `17.4.2.2-VRd2-modeloI` | 17.4.2.2 a) | 156 | VRd2 - Modelo de cálculo I (θ = 45°) | implementado | alta | P |  |
| `17.4.2.2-Vc-Vsw-modeloI` | 17.4.2.2 b) | 157 | Vc e Vsw - Modelo de cálculo I (todos os casos de Vc) | parcial | alta | M | P15 |
| `17.4-M0-momento-descompressao` | 17.4.2.2 b) [M0] | 157 | M0 - momento que anula a tensão de compressão na borda tracionada | ausente | média | M | P15 |
| `17.4.2.2-decalagem-forca` | 17.4.2.2 c) | 158 | Decalagem do diagrama de força no banzo tracionado - Modelo I | implementado | alta | M |  |
| `17.4.2.2-Fsd-cor-alternativa` | 17.4.2.2 c) [alternativa] | 158 | Força de tração decalada por fórmula direta (alternativa a aℓ) | ausente | baixa | P | P15 |
| `17.4.2.3-VRd2-modeloII` | 17.4.2.3 a) | 158 | VRd2 - Modelo de cálculo II (θ variável de 30° a 45°) | implementado | alta | P |  |
| `17.4.2.3-Vc-Vsw-modeloII` | 17.4.2.3 b) | 159 | Vc1 e Vsw - Modelo de cálculo II (todos os casos) | parcial | alta | M | P15 |
| `17.4.2.3-decalagem-modeloII` | 17.4.2.3 c) | 159 | Decalagem do diagrama de força no banzo tracionado - Modelo II | implementado | alta | M |  |
| `17.5.1.1-modelo-trelica-espacial` | 17.5.1.1 | 159 | Modelo resistente de treliça espacial para torcao uniforme | implementado | média | P |  |
| `17.5.1.2-taxa-min-torcao` | 17.5.1.2 | 160 | Taxas geométricas mínimas de torção (longitudinal e transversal) | implementado | média | P |  |
| `17.5.1.2-dispensa-torcao-compatibilidade` | 17.5.1.2 | 160 | Dispensa de armadura de torção de compatibilidade | ausente | média | P | P16 |
| `17.5.1.2-limite-Vsd-adaptacao-plastica` | 17.5.1.2 | 160 | Limite de VSd para adaptação plástica em trecho curto de torção | ausente | baixa | P | P16 |
| `17.5.1.3-condicao-tripla-torcao` | 17.5.1.3 | 160 | Condição tripla de resistência à torção pura | parcial | média | P | P16 |
| `17.5.1.4.1-secao-vazada-equivalente` | 17.5.1.4.1 | 160 | Geometria da seção vazada equivalente (seção poligonal convexa cheia) | implementado | média | M |  |
| `17.5.1.4.2-secao-composta-retangulos` | 17.5.1.4.2 | 161 | Distribuição do momento de torção entre retângulos de uma seção composta | ausente | média | M | P16 |
| `17.5.1.4.3-secoes-vazadas-reais` | 17.5.1.4.3 | 161 | Espessura de parede em seções vazadas reais (caixão, celular) | ausente | baixa | P | P16 |
| `17.5.1.5-TRd2-torcao` | 17.5.1.5 | 161 | TRd2 - resistência das diagonais comprimidas de concreto à torção | implementado | média | P |  |
| `17.5.1.6.a-TRd3-estribos` | 17.5.1.6 a) | 162 | TRd3 - resistência dos estribos de torção | implementado | média | P |  |
| `17.5.1.6.b-TRd4-longitudinal` | 17.5.1.6 b) | 162 | TRd4 - resistência das barras longitudinais de torção | implementado | média | P |  |
| `17.5.1.6-arranjo-armadura-torcao` | 17.5.1.6 | 162 | Regras de arranjo da armadura longitudinal de torção | ausente | baixa | P | P16 |
| `17.5.2.1-17.5.2.2-perfis-abertos-generalidades` | 17.5.2.1/17.5.2.2 | 162 | Torção em perfis abertos de parede fina - generalidades e rigidezes reduzidas | ausente | baixa | M | P42 |
| `17.5.2.3-rigidez-flexo-torcao` | 17.5.2.3 | 163 | Coeficiente de mola (rigidez) à flexo-torção de perfil com paredes opostas | ausente | baixa | G | P42 |
| `17.5.2.4-resistencia-flexo-torcao` | 17.5.2.4 | 163 | Resistência à flexo-torção a partir da resistência à flexão das paredes | ausente | baixa | M | P42 |
| `17.6-fissuracao-inclinada-alma` | 17.6 | 164 | Limite de espaçamento da armadura transversal para fissuração inclinada da alma | ausente | baixa | P | P15 |
| `17.7.1.1-flexao-torcao-generalidades` | 17.7.1.1 | 164 | Verificação separada de torção e flexão com complementos obrigatórios | não computável | média | P |  |
| `17.7.1.2-soma-armadura-longitudinal` | 17.7.1.2 | 164 | Soma da armadura longitudinal de torção com a de flexão (zona tracionada) | ausente | alta | P | P16 |
| `17.7.1.3-reducao-torcao-banzo-comprimido` | 17.7.1.3 | 164 | Redução da armadura longitudinal de torção no banzo comprimido por flexão | não computável | baixa | P |  |
| `17.7.1.4-tensao-principal-banzo-comprimido` | 17.7.1.4 | 164 | Tensão principal de compressão no banzo comprimido sob flexão+torção | ausente | baixa | M | P16 |
| `17.7.2.1-theta-coincidente` | 17.7.2.1 | 165 | Ângulo θ coincidente para cortante e torção combinados | não computável | média | P |  |
| `17.7.2.2-interacao-V-T-biela` | 17.7.2.2 | 165 | Interação VSd/VRd2 + TSd/TRd2 ≤ 1 (compressão diagonal combinada) | implementado | alta | P |  |
| `17.7.2.3-soma-armaduras-transversais-VT` | 17.7.2.3 | 165 | Soma das armaduras transversais calculadas separadamente para V e T | ausente | média | P | P16 |

## Seção 18

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `18.1-simbologia` | 18.1 | 165 | Simbologia específica da Seção 18 | não computável | baixa | P |  |
| `18.2.1-arranjo-armaduras` | 18.2.1 | 166 | Arranjo geral das armaduras (execução e adensamento) | não computável | baixa | P |  |
| `18.2.2-diametro-curvatura-barra-longitudinal` | 18.2.2 | 166 | Diâmetro interno mínimo de curvatura de barra longitudinal dobrada (força cortante ou nó de pórtico) | ausente | média | P | P22 |
| `18.2.2-fissuracao-plano-dobra` | 18.2.2 | 166 | Necessidade de armadura transversal ou diâmetro maior quando há risco de fissuração no plano da barra dobrada | não computável | baixa | P |  |
| `18.2.3-mudanca-direcao-armaduras` | 18.2.3 | 166 | Mudança de direção de barras tracionadas (retificação, cobrimento insuficiente) | não computável | baixa | P |  |
| `18.2.4-protecao-flambagem-barras` | 18.2.4 | 167 | Proteção contra flambagem das barras longitudinais junto à superfície (limite de 20·φt sem estribo suplementar) | ausente | média | M | P23 |
| `18.3.1-generalidades-esbeltez-viga-x-viga-parede` | 18.3.1 | 167 | Classificação viga comum x viga-parede pela relação vão/altura (l/h) | ausente | média | P | P11 |
| `18.3.2.1-as-min-flexao-viga-remissao` | 18.3.2.1 | 168 | Quantidade mínima de armadura longitudinal de flexão em vigas (remissão a 17.3.5) | implementado | alta | P |  |
| `18.3.2.2-espacamento-longitudinal-vigas` | 18.3.2.2 | 168 | Espaçamento mínimo livre entre barras longitudinais de vigas (horizontal ah e vertical av) | ausente | alta | P | P22 |
| `18.3.2.3.1-cobertura-diagrama-decalagem` | 18.3.2.3.1 | 168 | Cobertura do diagrama de força de tração solicitante pelo resistente (pontos A/B, decalagem al) - Figura 18.3 | parcial | alta | G | P22 |
| `18.3.2.3.1-caso-ponto-A-na-face-apoio` | 18.3.2.3.1 | 169 | Caso especial: ponto A na face do apoio ou além dela, com Fsd decrescente em direção ao apoio | ausente | média | M | P22 |
| `18.3.2.3.2-barras-nas-mesas` | 18.3.2.3.2 | 169 | Comprimento adicional para barras alojadas nas mesas/lajes que compõem a armadura da viga T | ausente | média | P | P22 |
| `18.3.2.4-armadura-tracao-apoio-condicoes` | 18.3.2.4 | 169 | Envoltória de condições para armadura de tração junto aos apoios (a,b,c,d) | não computável | alta | P |  |
| `18.3.2.4-b-forca-tracao-apoio-extremo` | 18.3.2.4-b | 169 | Força de tração de cálculo Fsd para ancorar a diagonal de compressão em apoio extremo | ausente | alta | P | P22 |
| `18.3.2.4-c-fracao-as-vao` | 18.3.2.4-c | 170 | Armadura mínima de apoio por prolongamento de fração da armadura do vão | ausente | alta | P | P22 |
| `18.3.2.4-d-apoio-extremo-momento-negativo` | 18.3.2.4-d | 170 | Apoio extremo com momento negativo: armadura pelo dimensionamento, ancorada conforme 18.3.2.4.1 | não computável | média | P |  |
| `18.3.2.4.1-ancoragem-apoio` | 18.3.2.4.1 | 170 | Comprimento mínimo de ancoragem da armadura de tração a partir da face do apoio | parcial | alta | M | P22 |
| `18.3.3.1-generalidades-armadura-transversal-cortante` | 18.3.3.1 | 170 | Tipos de armadura transversal para força cortante (estribos, barras dobradas, telas soldadas), remissão a 17.4 | não computável | alta | P |  |
| `18.3.3.2-diametro-min-max-estribo` | 18.3.3.2 | 170 | Diâmetro mínimo e máximo da barra de estribo para força cortante | ausente | alta | P | P23 |
| `18.3.3.2-barras-amarracao-canto-estribo` | 18.3.3.2 | 171 | Diâmetro mínimo de barra de amarração/canto quando não há barra longitudinal calculada no canto do estribo | ausente | média | P | P23 |
| `18.3.3.2-espacamento-longitudinal-max-estribos` | 18.3.3.2 | 171 | Espaçamento longitudinal máximo entre estribos (smáx) em função de Vd/VRd2 | ausente | alta | P | P23 |
| `18.3.3.2-espacamento-transversal-max-ramos` | 18.3.3.2 | 171 | Espaçamento transversal máximo entre ramos sucessivos de estribo (st,máx) em função de Vd/VRd2 | ausente | alta | P | P23 |
| `18.3.3.2-emenda-traspasse-estribo` | 18.3.3.2 | 171 | Restrição à emenda por traspasse de estribos (só tela ou barra de alta aderência) | ausente | baixa | P | P23 |
| `18.3.3.3.1-ancoragem-barra-dobrada-cortante` | 18.3.3.3.1 | 171 | Ancoragem de barras dobradas resistentes à força cortante (trecho reto ≥ lb,nec) | implementado | média | P |  |
| `18.3.3.3.2-espacamento-barras-dobradas` | 18.3.3.3.2 | 171 | Espaçamento longitudinal máximo entre barras dobradas resistentes a cortante | ausente | baixa | P | P23 |
| `18.3.4-armadura-torcao-generalidades-remissao` | 18.3.4 | 171 | Armadura de torção: estribos fechados + longitudinais, remissão a 17.5 e efetividade dentro da parede fictícia | não computável | média | P |  |
| `18.3.4-estribo-torcao-135-graus-fechado` | 18.3.4 | 171 | Estribo de torção fechado em todo o contorno, com ganchos a 135 graus, reaproveitando regras de 18.3.3.2 | ausente | média | P | P23 |
| `18.3.4-espacamento-longitudinal-barras-torcao` | 18.3.4 | 172 | Espaçamento máximo das barras longitudinais de torção ao longo do perímetro interno dos estribos (350mm) | ausente | média | P | P23 |
| `18.3.4-relacao-deltaAsl-deltau` | 18.3.4 | 172 | Relação DeltaAsl/Deltau constante ao longo do perímetro | parcial | baixa | M | P23 |
| `18.3.4-barra-cada-vertice-poligonal` | 18.3.4 | 172 | Pelo menos uma barra longitudinal em cada vértice de estribo poligonal de torção | ausente | baixa | P | P23 |
| `18.3.5-armadura-pele` | 18.3.5 | 172 | Espaçamento máximo da armadura de pele (afastamento ≤ d/3 e 20 cm) | ausente | alta | P | P12 |
| `18.3.6-armadura-suspensao-percentuais` | 18.3.6 | 172 | Armadura de suspensão em vigas não penduradas: percentuais e extensão na viga de apoio e na viga apoiada | ausente | média | M | P23 |
| `18.3.6-fator-reducao-vigas-face-superior-coincidente` | 18.3.6 | 172 | Fator de redução da carga de suspensão para vigas não penduradas com faces superiores coincidentes | ausente | baixa | P | P23 |
| `18.3.6-definicao-viga-pendurada` | 18.3.6 | 172 | Classificação viga pendurada x não pendurada | ausente | baixa | P | P23 |
| `18.3.7-armadura-ligacao-mesa-alma` | 18.3.7 | 173 | Armadura mínima de ligação mesa-alma ou talão-alma (1,5 cm2/m) | ausente | média | P | P23 |
| `18.4.1-introducao-pilar-x-pilar-parede` | 18.4.1 | 173 | Classificação pilar comum x pilar-parede pela razão entre dimensões da seção (maior ≤ 5 vezes a menor) | ausente | alta | P | P11 |
| `18.4.2.1-diametro-min-max-barra-longitudinal-pilar` | 18.4.2.1 | 173 | Diâmetro mínimo e máximo da barra longitudinal de pilar | ausente | alta | P | P24 |
| `18.4.2.1-taxa-armadura-pilar-remissao` | 18.4.2.1 | 173 | Taxa geométrica de armadura longitudinal de pilar (remissão a 17.3.5.3) | implementado | alta | P |  |
| `18.4.2.2-distribuicao-transversal-vertices-pilar` | 18.4.2.2 | 173 | Número mínimo de barras por geometria de pilar (1 por vértice; mínimo 6 em seção circular) | ausente | alta | P | P24 |
| `18.4.2.2-espacamento-min-barras-pilar` | 18.4.2.2 | 173 | Espaçamento mínimo livre entre barras longitudinais de pilar (fora da região de emenda) | ausente | alta | P | P24 |
| `18.4.2.2-espacamento-max-eixos-pilar` | 18.4.2.2 | 174 | Espaçamento máximo entre eixos das barras longitudinais de pilar (2x a menor dimensão, limitado a 400mm) | ausente | alta | P | P24 |
| `18.4.3-diametro-min-estribo-pilar` | 18.4.3 | 174 | Diâmetro mínimo do estribo de pilar (5mm ou 1/4 do diâmetro da barra/feixe longitudinal) | ausente | alta | P | P24 |
| `18.4.3-espacamento-max-estribo-pilar-basico` | 18.4.3 | 174 | Espaçamento longitudinal máximo básico entre estribos de pilar (200mm; menor dimensão; 24phi CA-25/12phi CA-50) | ausente | alta | P | P24 |
| `18.4.3-espacamento-max-estribo-pilar-phi-reduzido` | 18.4.3 | 174 | Limite adicional de espaçamento quando φt < φℓ/4 (fórmula com fyk) | ausente | média | P | P24 |
| `18.4.3-nota-dutilidade-concreto-alta-resistencia` | 18.4.3 (NOTA) | 174 | Recomendação de redução de 50% no espaçamento de estribos para concretos C55 a C90 (dutilidade) | ausente | média | P | P24 |
| `18.5-pilar-parede-esforcos-transversais-remissao-secao15` | 18.5 | 174 | Pilar-parede: exigência adicional de considerar 1a e 2a ordem transversal (Seção 15), inclusive 2a ordem localizada | não computável | média | P |  |
| `18.5-armadura-transversal-pilar-parede-25pct` | 18.5 | 174 | Armadura transversal mínima de pilar-parede (25% da longitudinal por metro de face, se flexão de placa não for calculada) | ausente | média | P | P29 |
| `18.6.1.1-tracado-qualitativo` | 18.6.1.1 | 175 | Traçado admissível dos cabos de protensão | não computável | baixa | P |  |
| `18.6.1.1-FSd-apoio-intermediario` | 18.6.1.1 | 175 | Força de tração da armadura em apoios intermediários | ausente | média | P | P22 |
| `18.6.1.2-raio-minimo-curvatura` | 18.6.1.2 | 175 | Raio mínimo de curvatura dos cabos de protensão | ausente | média | P | P31 |
| `18.6.1.3-curvatura-ancoragens-qualitativo` | 18.6.1.3 | 175 | Curvatura nas proximidades das ancoragens | não computável | baixa | P |  |
| `18.6.1.4-fixacao-execucao-qualitativo` | 18.6.1.4 | 175 | Fixação da armadura de protensão durante a execução | não computável | baixa | P |  |
| `18.6.1.5-extremidade-reta-minima` | 18.6.1.5 | 175 | Comprimento mínimo dos trechos retos nas extremidades dos cabos | ausente | média | P | P31 |
| `18.6.1.6-prolongamento-extremidade-qualitativo` | 18.6.1.6 | 176 | Prolongamento de extremidade dos cabos | não computável | baixa | P |  |
| `18.6.1.7-emendas-qualitativo` | 18.6.1.7 | 176 | Emendas da armadura de protensão | não computável | baixa | P |  |
| `18.6.1.8-ancoragens-remissao` | 18.6.1.8 | 176 | Ancoragens de protensão - remissão a 9.4.7 | não computável | baixa | P |  |
| `18.6.2.1.1-bainha-metalica-aderente-qualitativo` | 18.6.2.1.1 | 176 | Bainhas para protensão interna com armadura aderente | não computável | baixa | P |  |
| `18.6.2.1.2-bainha-plastica-nao-aderente-qualitativo` | 18.6.2.1.2 | 176 | Bainhas para protensão interna com armadura não aderente | não computável | baixa | P |  |
| `18.6.2.1.3-bainha-protensao-externa-qualitativo` | 18.6.2.1.3 | 176 | Bainhas para protensão externa | não computável | baixa | P |  |
| `18.6.2.2-agrupamento-cabos` | 18.6.2.2 | 176 | Regras de agrupamento de cabos em bainhas (pós-tração) | ausente | média | P | P31 |
| `18.6.2.3-tabela18.1-espacamento-postracao` | 18.6.2.3 | 177 | Tabela 18.1 - Espaçamentos mínimos entre bainhas (pós-tração) | ausente | média | P | P31 |
| `18.6.2.3-tabela18.2-espacamento-pretracao` | 18.6.2.3 | 177 | Tabela 18.2 - Espaçamentos mínimos entre fios/cordoalhas (pré-tração) | ausente | média | P | P31 |

## Seção 19

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `19.1-simbologia` | 19.1 | 178 | Simbologia específica da seção 19 (lajes) | não computável | baixa | P |  |
| `19.2-principios-elu` | 19.2 | 179 | Princípios do ELU de lajes (flexão e forças normais) | parcial | alta | P | P17 |
| `19.3.1-els-deformacao` | 19.3.1 | 179 | ELS de deformação de lajes remete a 17.3.2 | parcial | alta | M | P8 |
| `19.3.2-els-fissuracao` | 19.3.2 | 179 | ELS de fissuração/descompressão em lajes remete a 17.3.3 e 17.3.4 | parcial | alta | M | P9 |
| `19.3.3.1-principios-as-max-min` | 19.3.3.1 | 179 | Princípios básicos de armaduras máximas e mínimas de laje | implementado | alta | P |  |
| `19.3.3.2-extensao-armadura-negativa-borda` | 19.3.3.2 | 179 | Extensão mínima da armadura negativa de borda sem continuidade | ausente | alta | P | P17 |
| `19.3.3.2-tab19.1-as-min` | 19.3.3.2 / Tabela 19.1 | 180 | Tabela 19.1 - valores mínimos para armaduras passivas aderentes de laje | parcial | alta | M | P17 |
| `19.3.3.2-as-min-laje-lisa-nao-aderente` | 19.3.3.2 | 180 | Armadura negativa mínima em laje lisa/cogumelo com armadura ativa não aderente | ausente | média | P | P17 |
| `19.3.3.3-as-max` | 19.3.3.3 | 181 | Armadura máxima de flexão de laje remete a 17.3.5.2 | ausente | alta | P | P12 |
| `19.4.1-vrd1` | 19.4.1 | 181 | Força cortante resistente de laje sem armadura transversal (VRd1) | parcial | alta | M | P15 |
| `19.4.1-decalagem-al-15d` | 19.4.1 | 182 | Deslocamento da lei de decalagem em lajes (al=1,5d) | ausente | média | P | P15 |
| `19.4.2-modelo-cortante-laje` | 19.4.2 | 182 | Lajes com armadura para força cortante aplicam os critérios de 17.4.2 | implementado | alta | P |  |
| `19.4.2-fywd-max-laje` | 19.4.2 | 182 | Limite de tensão no estribo de laje por espessura (fywd reduzido) | ausente | alta | P | P15 |
| `19.5.1-modelo-calculo-puncao` | 19.5.1 | 182 | Modelo de cálculo de punção: superfícies críticas C, C' e C'' | ausente | alta | M | P19 |
| `19.5.2.1-tsd-pilar-interno-simetrico` | 19.5.2.1 | 183 | Tensão solicitante de punção em pilar interno com carregamento simétrico | ausente | alta | P | P19 |
| `19.5.2.2-tsd-pilar-interno-momento` | 19.5.2.2 | 184 | Tensão solicitante de punção em pilar interno com efeito de momento | ausente | alta | M | P19 |
| `19.5.2.2-tabela19.2-K` | 19.5.2.2 / Tabela 19.2 | 184 | Tabela 19.2 - coeficiente K | ausente | alta | P | P19 |
| `19.5.2.2-wp-retangular` | 19.5.2.2 | 184 | Wp do perímetro crítico - pilar retangular | ausente | alta | P | P19 |
| `19.5.2.2-wp-circular` | 19.5.2.2 | 184 | Wp do perímetro crítico - pilar circular | ausente | média | P | P19 |
| `19.5.2.2-wp-integral-generico` | 19.5.2.2 | 184 | Wp por integração numérica do perímetro crítico (forma qualquer) | ausente | baixa | M | P20 |
| `19.5.2.3-pilar-borda-sem-momento-paralelo` | 19.5.2.3 a) | 185 | tSd em pilar de borda sem momento paralelo à borda livre | ausente | alta | M | P19 |
| `19.5.2.3-pilar-borda-com-momento-paralelo` | 19.5.2.3 b) | 185 | tSd em pilar de borda com momento paralelo à borda livre | ausente | alta | M | P19 |
| `19.5.2.4-pilar-canto` | 19.5.2.4 | 186 | Verificação de punção em pilar de canto | ausente | alta | M | P19 |
| `19.5.2.5-capitel` | 19.5.2.5 | 187 | Verificação de punção com capitel (contornos C1' e C2') | ausente | média | M | P20 |
| `19.5.2.6-contorno-reentrancia` | 19.5.2.6 | 187 | Perímetro crítico em contorno C com reentrâncias | ausente | baixa | M | P20 |
| `19.5.2.6-contorno-abertura` | 19.5.2.6 | 187 | Perímetro crítico junto a abertura na laje | ausente | alta | M | P20 |
| `19.5.2.7-interacao-normal-tangencial` | 19.5.2.7 | 188 | Dispensa de verificação da interação entre flexão e punção | não computável | alta | P |  |
| `19.5.3.1-trd2-compressao-diagonal` | 19.5.3.1 | 188 | Tensão resistente de compressão diagonal do concreto no contorno C (punção) | ausente | alta | P | P19 |
| `19.5.3.2-trd1-sem-armadura` | 19.5.3.2 | 188 | Tensão resistente na superfície crítica C' sem armadura de punção | ausente | alta | M | P19 |
| `19.5.3.3-trd3-com-armadura` | 19.5.3.3 | 189 | Tensão resistente na superfície crítica C' com armadura de punção | ausente | alta | M | P19 |
| `19.5.3.4-superficie-c2linha` | 19.5.3.4 | 190 | Definição geométrica da superfície crítica C'' e disposição da armadura de punção | ausente | alta | M | P20 |
| `19.5.3.5-armadura-puncao-obrigatoria` | 19.5.3.5 | 191 | Armadura de punção obrigatória por robustez (estabilidade global) | ausente | alta | P | P20 |
| `19.5.4-colapso-progressivo` | 19.5.4 | 191 | Armadura de flexão inferior contra colapso progressivo na ligação laje-pilar | ausente | alta | P | P20 |
| `19.5.5-puncao-protendido` | 19.5.5 | 191 | Tensão solicitante efetiva de punção em laje protendida (efeito favorável dos cabos inclinados) | ausente | média | M | P20 |

## Seção 20

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `20.1-diametro-max-barra` | 20.1 | 192 | Diâmetro máximo de barra de flexão em laje | ausente | alta | P | P18 |
| `20.1-espacamento-max-principal` | 20.1 | 192 | Espaçamento máximo da armadura principal de flexão em laje | ausente | alta | P | P18 |
| `20.1-sem-escalonamento-armadura-positiva` | 20.1 | 192 | Vedação de escalonamento da armadura positiva e prolongamento mínimo no apoio | ausente | alta | P | P18 |
| `20.1-armadura-secundaria-positiva` | 20.1 | 192 | Armadura secundária positiva mínima e espaçamento máximo | ausente | alta | P | P18 |
| `20.1-estribo-nervurada-espacamento` | 20.1 | 192 | Espaçamento máximo de estribos em nervuras de laje nervurada | ausente | média | P | P18 |
| `20.2-bordas-aberturas` | 20.2 | 193 | Armadura em bordas livres e aberturas de lajes maciças | não computável | média | P |  |
| `20.3.1-fig20.2-distribuicao-faixas` | 20.3.1 | 194 | Distribuição de armadura em lajes sem vigas por faixas (Figura 20.2) | ausente | alta | M | P18 |
| `20.3.1-barras-continuas-apoio` | 20.3.1 | 194 | Mínimo de barras inferiores contínuas sobre os apoios | ausente | alta | P | P18 |
| `20.3.1-capitel-penetracao-minima` | 20.3.1 | 194 | Penetração mínima de barras inferiores interrompidas em capitel | ausente | média | P | P18 |
| `20.3.2.1-espacamento-max-cabos` | 20.3.2.1 | 194 | Espaçamento máximo entre cordoalhas/cabos para faixa protendida | ausente | média | P | P33 |
| `20.3.2.1-tensao-compressao-media-minima` | 20.3.2.1 | 194 | Tensão de compressão média mínima na seção com cabo/feixe | ausente | média | P | P33 |
| `20.3.2.2-largura-max-faixa-externa` | 20.3.2.2 | 195 | Largura máxima da porção de laje para cabos em faixa externa de apoio | ausente | média | P | P33 |
| `20.3.2.3-espacamento-min-cabos` | 20.3.2.3 | 195 | Espaçamento mínimo entre cabos/feixes ou entre cabo e armadura passiva | ausente | média | P | P33 |
| `20.3.2.4-cobrimento-min-cabo-abertura` | 20.3.2.4 | 195 | Cobrimento mínimo de cabos junto à face de abertura em laje | ausente | média | P | P33 |
| `20.3.2.5-desvio-max-inclinacao` | 20.3.2.5 | 195 | Inclinação máxima do desvio em planta de cabo/feixe | ausente | média | P | P33 |
| `20.3.2.5-distancia-min-cabos-curva` | 20.3.2.5 | 195 | Distância mínima entre cabos na região central da curva de desvio | ausente | média | P | P33 |
| `20.3.2.6-cabos-atravessando-pilar` | 20.3.2.6 | 196 | Número mínimo de cabos atravessando a armadura do pilar por direção | ausente | média | P | P33 |
| `20.3.2.6-barras-apoio-laje-lisa-protendida` | 20.3.2.6 | 196 | Armadura passiva mínima sobre apoios de laje lisa/cogumelo protendida | ausente | média | M | P33 |
| `20.3.2.6-max-cabos-feixe-monocordoalha` | 20.3.2.6 | 196 | Número máximo de monocordoalhas não aderentes em feixe | ausente | média | P | P33 |
| `20.4-diametro-max-estribo-puncao` | 20.4 | 196 | Diâmetro máximo do estribo de armadura de punção | ausente | alta | P | P20 |
| `20.4-contato-mecanico-canto-estribo` | 20.4 | 196 | Contato mecânico e diâmetro mínimo da barra longitudinal no canto do estribo de punção | ausente | média | P | P20 |
| `20.4-studs-desempenho-ensaio` | 20.4 | 196 | Preferência por studs e exigência de desempenho comprovado por ensaio | não computável | média | P |  |
| `20.5.1-ancoragem-tela-soldada-apoio` | 20.5.1 | 196 | Comprimento de ancoragem de tela soldada nervurada no apoio sobre viga | ausente | média | P | P18 |
| `20.5.2-emenda-tela-tabela-malhas-fios` | 20.5.2 | 196 | Emenda de armaduras em tela soldada nervurada por sobreposição de malhas/fios | ausente | baixa | P | P18 |
| `20.5.2-emenda-tela-retangular-reducao` | 20.5.2 | 196 | Redução de emenda em telas retangulares (L ou T) na maior dimensão | não computável | baixa | P |  |
| `20.6-armadura-inferior-laje-balanco` | 20.6 | 197 | Armadura inferior de segurança em laje em balanço (marquise) | ausente | alta | P | P18 |

## Seção 21

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `21.1-definicao-regiao-especial` | 21.1 | 197 | Definição de regiões especiais e elementos especiais | não computável | média | P |  |
| `21.2.1-FRd-esmagamento-area-reduzida` | 21.2.1 | 197 | Resistência de cálculo ao esmagamento sob carga em área reduzida | ausente | média | P | P34 |
| `21.2.1-proporcao-lados-ac0` | 21.2.1 | 197 | Proporção máxima entre lados de área reduzida retangular | ausente | média | P | P34 |
| `21.2.1-ressalvas-qualitativas` | 21.2.1 | 198 | Ressalvas de aplicação da fórmula de esmagamento em área reduzida | não computável | média | P |  |
| `21.2.2-articulacao-concreto` | 21.2.2 | 198 | Geometria e inclinação limite de articulação de concreto (núcleo reduzido) | ausente | baixa | M | P34 |
| `21.2.3-intro-protensao-modelo-3d` | 21.2.3 | 199 | Modelagem da região de introdução da protensão | não computável | média | G |  |
| `21.2.4-cargas-superficie-chumbadores` | 21.2.4 | 199 | Verificação de cargas de insertos e chumbadores na superfície do concreto | não computável | baixa | P |  |
| `21.3.1-generalidades-furos-aberturas` | 21.3.1 | 200 | Generalidades sobre furos e aberturas em elementos estruturais | não computável | alta | P |  |
| `21.3.2-classificacao-abertura-viga-parede` | 21.3.2 | 200 | Classificação de abertura em parede/viga-parede como normal ou prejudicial | não computável | média | M |  |
| `21.3.3-diametro-max-furo-viga` | 21.3.3 | 200 | Diâmetro máximo de furo vertical em viga | ausente | alta | P | P34 |
| `21.3.3-distancia-min-furo-face` | 21.3.3 | 200 | Distância mínima do furo à face da viga | ausente | alta | P | P34 |
| `21.3.3-secao-remanescente-furo-viga` | 21.3.3 | 200 | Verificação da seção remanescente da viga na região do furo | ausente | alta | M | P34 |
| `21.3.3-conjunto-furos-alinhados` | 21.3.3 | 200 | Distância mínima entre furos alinhados e estribo por intervalo | ausente | média | P | P34 |
| `21.3.3-torcao-ajuste-limites` | 21.3.3 | 201 | Ajuste dos limites de furo em vigas submetidas à torção | não computável | baixa | P |  |
| `21.3.4a-secao-remanescente-abertura-laje` | 21.3.4 | 201 | Verificação da seção remanescente de laje com abertura no ELU | ausente | alta | M | P34 |
| `21.3.4b-armadura-reforco-abertura-laje` | 21.3.4 | 201 | Armadura de reforço equivalente à armadura interrompida por abertura em laje | ausente | alta | P | P34 |
| `21.3.4c-puncao-abertura-proxima-pilar` | 21.3.4 | 201 | Equilíbrio de forças cortantes em laje lisa/cogumelo com abertura próxima a pilar | ausente | alta | G | P20 |
| `21.4-nos-porticos-ligacoes-paredes` | 21.4 | 201 | Nós de pórticos e ligações entre paredes | não computável | média | P |  |
| `21.5-ligacoes-pre-moldados` | 21.5 | 201 | Ligações de elementos estruturais pré-moldados | não computável | baixa | P |  |
| `21.6-juntas-concretagem-armadura-costura` | 21.6 | 201 | Armadura de costura em juntas de concretagem sem aderência/rugosidade garantidas | não computável | média | P |  |

## Seção 22

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `22.2-limite-regiao-bd` | 22.2 | 202 | Limite convencional entre regiões B e D | não computável | baixa | P |  |
| `22.2-gamma-n-consolo-gerber` | 22.2 | 203 | Coeficiente adicional γn para consolos e dentes Gerber | ausente | alta | P | P10 |
| `22.3.1-procedimento-bielas-tirantes` | 22.3.1 | 203 | Procedimento geral do método de bielas e tirantes | ausente | média | G | fora: Idealizar a treliça de uma região D é modelagem do engenheiro. A biblioteca verifica bielas, nós e tirantes a partir das forças dadas (P35). |
| `22.3.1-limite-inclinacao-biela` | 22.3.1 | 204 | Faixa de inclinação admissível das bielas inclinadas | ausente | média | P | P35 |
| `22.3.2-fcd1` | 22.3.2 | 204 | Resistência de cálculo da biela/nó CCC (fcd1) | implementado | alta | P |  |
| `22.3.2-fcd2` | 22.3.2 | 204 | Resistência de cálculo da biela/nó CTT ou TTT (fcd2) | ausente | média | P | P35 |
| `22.3.2-fcd3` | 22.3.2 | 204 | Resistência de cálculo da biela/nó CCT (fcd3) | implementado | alta | P |  |
| `22.3.3-as-tirante` | 22.3.3 | 204 | Área de aço de um tirante genérico do modelo biela-tirante | ausente | alta | P | P35 |
| `22.4.1-classificacao-viga-parede` | 22.4.1 | 204 | Classificação de viga como viga-parede | ausente | média | P | P11 |
| `22.4.2-comportamento-viga-parede` | 22.4.2 | 204 | Comportamento estrutural das vigas-parede | não computável | média | P |  |
| `22.4.3-modelo-calculo-viga-parede` | 22.4.3 | 205 | Modelos de cálculo para viga-parede no ELU | ausente | média | G | fora: Exige MEF ou uma treliça montada caso a caso. As armaduras e verificações de 22.4.4 estão no P35. |
| `22.4.4.1-as-viga-parede-continua` | 22.4.4.1 | 205 | Distribuição da armadura negativa em viga-parede contínua (3 faixas) | ausente | média | M | P35 |
| `22.4.4.1-armadura-horizontal-minima-viga-parede` | 22.4.4.1 | 205 | Armadura horizontal mínima de viga-parede | ausente | média | P | P35 |
| `22.4.4.2-ancoragem-flexao-positiva-viga-parede` | 22.4.4.2 | 205 | Ancoragem da armadura de flexão positiva nos apoios de viga-parede | não computável | média | P |  |
| `22.4.4.3-armadura-vertical-minima-viga-parede` | 22.4.4.3 | 206 | Armadura vertical mínima de viga-parede | ausente | média | P | P35 |
| `22.4.4.3-verificacao-suspensao-carga-inferior` | 22.4.4.3 | 206 | Armadura vertical de suspensão em viga-parede com carregamento inferior | ausente | média | P | P35 |
| `22.5.1.1-classificacao-consolo` | 22.5.1.1 | 206 | Classificação de consolo (curto / muito curto / viga em balanço) | ausente | alta | P | P36 |
| `22.5.1.2-limite-inclinacao-biela-consolo` | 22.5.1.2 | 207 | Inclinação máxima da abertura de carga na biela do consolo | ausente | alta | P | P36 |
| `22.5.1.2-limite-taxa-tirante-ductil` | 22.5.1.2 | 207 | Limitação superior da taxa de armadura do tirante do consolo | não computável | média | P |  |
| `22.5.1.3-modelo-calculo-consolo` | 22.5.1.3 | 208 | Modelo de cálculo do consolo (biela-tirante ou atrito-cisalhamento) | ausente | alta | G | P36 |
| `22.5.1.4.1-as-min-tirante-consolo` | 22.5.1.4.1 | 208 | Armadura mínima do tirante do consolo | ausente | alta | P | P36 |
| `22.5.1.4.1-restricao-gancho-vertical-consolo` | 22.5.1.4.1 | 208 | Restrição ao uso de gancho vertical na extremidade do tirante do consolo | ausente | média | P | P36 |
| `22.5.1.4.3-armadura-costura-consolo` | 22.5.1.4.3 | 209 | Armadura de costura mínima do consolo | ausente | alta | P | P36 |
| `22.5.1.4.4-armadura-suspensao-consolo` | 22.5.1.4.4 | 209 | Armadura de suspensão do consolo para carga indireta | ausente | média | P | P36 |
| `22.5.2.1-classificacao-dente-gerber` | 22.5.2.1 | 210 | Conceituação do dente Gerber | não computável | média | P |  |
| `22.5.2.2-comportamento-dente-gerber` | 22.5.2.2 | 210 | Comportamento estrutural do dente Gerber frente ao consolo | não computável | média | P |  |
| `22.5.2.3-modelo-calculo-dente-gerber` | 22.5.2.3 | 210 | Modelo de cálculo do dente Gerber | ausente | média | G | P36 |
| `22.5.2.4.2-as-suspensao-dente-gerber` | 22.5.2.4.2 | 211 | Armadura de suspensão do dente Gerber | ausente | média | P | P36 |
| `22.5.2.4.3-ancoragem-armadura-principal-gerber` | 22.5.2.4.3 | 211 | Ancoragem da armadura principal (tirante) do dente Gerber | não computável | baixa | P |  |
| `22.5.2.4.4-ancoragem-inferior-viga-gerber` | 22.5.2.4.4 | 211 | Ancoragem da armadura inferior da viga no trecho de suspensão do dente Gerber | não computável | baixa | P |  |
| `22.5.2.4.5-casos-especiais-gerber` | 22.5.2.4.5 | 211 | Casos especiais de suspensão no dente Gerber (barras dobradas, protensão) | não computável | baixa | P |  |
| `22.6.1-sapata-rigida-flexivel` | 22.6.1 | 211 | Classificação de sapata rígida x flexível | implementado | alta | P |  |
| `22.6.1-hipotese-distribuicao-plana` | 22.6.1 | 211 | Validade da hipótese de distribuição plana de tensões no contato sapata-solo | parcial | média | P | P37 |
| `22.6.2.2-cisalhamento-compressao-diagonal-sapata-rigida` | 22.6.2.2 | 212 | Verificação ao cisalhamento de sapata rígida por compressão diagonal (superfície C) | implementado | alta | P |  |
| `22.6.2.3-sapata-flexivel-puncao` | 22.6.2.3 | 212 | Sapata flexível: verificação ao cisalhamento por punção | ausente | alta | G | P20 |
| `22.6.3-modelo-calculo-sapata` | 22.6.3 | 212 | Modelo de cálculo tridimensional (ou bielas-tirantes 3D) para sapatas | ausente | média | G | fora: O modelo 3D linear ou de bielas e tirantes é análise estrutural. O método simplificado de sapatas é completado no P37. |
| `22.6.4.1.1-armadura-flexao-sapata-detalhamento` | 22.6.4.1.1 | 212 | Detalhamento da armadura de flexão de sapata rígida | ausente | alta | P | P37 |
| `22.6.4.1.1-fendilhamento-barra-25mm` | 22.6.4.1.1 | 213 | Verificação de fendilhamento horizontal para barras de flexão com diâmetro ≥ 25 mm | ausente | média | M | P37 |
| `22.6.4.1.2-armadura-arranque-pilar-sapata` | 22.6.4.1.2 | 213 | Altura da sapata suficiente para ancoragem da armadura de arranque do pilar | ausente | alta | P | P37 |
| `22.6.4.1.3-sapata-flexivel-remissao-lajes-puncao` | 22.6.4.1.3 | 213 | Sapata flexível: remissão aos requisitos de lajes e punção | não computável | média | P |  |
| `22.7.1-classificacao-bloco-rigido-flexivel` | 22.7.1 | 213 | Classificação de bloco sobre estacas rígido x flexível | ausente | alta | P | P37 |
| `22.7.2.1-a-faixa-armadura-estacas` | 22.7.2.1 | 213 | Faixa de concentração das trações sobre o eixo das estacas | ausente | alta | P | P37 |
| `22.7.2.2-bloco-flexivel-comportamento` | 22.7.2.2 | 213 | Comportamento estrutural do bloco flexível | não computável | média | P |  |
| `22.7.3-modelo-calculo-bloco` | 22.7.3 | 213 | Modelo de cálculo tridimensional (ou bielas-tirantes 3D) para blocos sobre estacas | ausente | média | G | fora: O modelo 3D é análise estrutural. O método das bielas (Blévot) é completado no P37. |
| `22.7.4.1.1-armadura-flexao-bloco-85pct` | 22.7.4.1.1 | 214 | Concentração mínima de 85% da armadura de flexão nas faixas das estacas | ausente | alta | M | P37 |
| `22.7.4.1.1-estacas-tracionadas-ancoragem` | 22.7.4.1.1 | 214 | Ancoragem da armadura de estacas tracionadas no bloco | ausente | média | M | P37 |
| `22.7.4.1.2-armadura-distribuicao-bloco-20pct` | 22.7.4.1.2 | 214 | Armadura de distribuição (malha positiva adicional) do bloco rígido | parcial | média | P | P37 |
| `22.7.4.1.3-armadura-suspensao-bloco-condicional` | 22.7.4.1.3 | 215 | Condição de exigência da armadura de suspensão no bloco | parcial | média | M | P37 |
| `22.7.4.1.4-armadura-arranque-pilar-bloco` | 22.7.4.1.4 | 215 | Altura do bloco suficiente para ancoragem da armadura de arranque do pilar | ausente | alta | P | P37 |
| `22.7.4.1.5-armadura-lateral-superior-obrigatoria` | 22.7.4.1.5 | 215 | Obrigatoriedade de armadura lateral e superior em blocos com estacas em linha única | parcial | média | M | P37 |
| `22.7.4.2-bloco-flexivel-remissao-lajes-puncao` | 22.7.4.2 | 215 | Bloco flexível: remissão aos requisitos de lajes e punção | não computável | média | P |  |

## Seção 23

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `23.3-freq-natural-vs-critica` | 23.3 | 215 | Verificação de vibrações excessivas (fn > 1,2 fcrit) | ausente | baixa | P | P38 |
| `23.3-tab23.1-fcrit` | 23.3 Tabela 23.1 | 216 | Tabela 23.1 - Frequência crítica para vibrações verticais por tipo de uso | ausente | baixa | P | P38 |
| `23.4-ressonancia-amplificacao` | 23.4 | 216 | ELU por ressonância ou amplificação dinâmica | não computável | baixa | P |  |
| `23.5.1-limite-20000-ciclos` | 23.5.1 | 216 | Limite inferior de aplicabilidade da fadiga (20 000 ciclos) e superior de abrangência (2 000 000 ciclos) | ausente | baixa | P | P38 |
| `23.5.1-palmgren-miner` | 23.5.1 | 217 | Regra de Palmgren-Miner (dano acumulado de fadiga) | ausente | média | M | P38 |
| `23.5.2-combinacao-frequente-fadiga` | 23.5.2 | 217 | Combinação frequente de ações para verificação de fadiga | parcial | média | P | P39 |
| `23.5.2-psi1-fadiga-tabela` | 23.5.2 | 217 | Fator de redução ψ1 para verificação de fadiga por tipo de obra/peça | ausente | baixa | P | P39 |
| `23.5.5-fator-reducao-ciclos-menor` | 23.5.2 | 217 | Aumento da resistência à fadiga para pontes rolantes de operação pouco frequente (número de ciclos << 2e6) | ausente | baixa | M | P39 |
| `23.5.3-modelo-I-vc-reduzido-fadiga` | 23.5.3 | 218 | Redução da contribuição do concreto Vc no Modelo de Cálculo I para verificação de fadiga por cortante | ausente | média | P | P39 |
| `23.5.3-modelo-II-theta-corrigido-fadiga` | 23.5.3 | 218 | Correção do ângulo das bielas (θcor) no Modelo de Cálculo II para verificação de fadiga por cortante | ausente | média | P | P39 |
| `23.5.3-alfa-e-relacao-modulos` | 23.5.3 | 218 | Relação entre módulos de deformação aço/concreto (αe) para cálculo elástico de tensões na fadiga | ausente | média | P | P9 |
| `23.5.3-eta-s-fator-aderencia` | 23.5.3 | 218 | Fator ηs de correção de tensão no aço por diferença de aderência entre armadura ativa e passiva | ausente | baixa | P | P39 |
| `23.5.3-phi-eq-feixe` | 23.5.3 | 218 | Diâmetro equivalente de feixe de cordoalhas/fios de protensão (φeq) | ausente | baixa | P | P39 |
| `23.5.3-xi-relacao-aderencia` | 23.5.3 | 219 | Valores de ξ (relação de aderência aço de protensão / aço passivo) por tipo de aço e processo de protensão | ausente | baixa | P | P39 |
| `23.5.3-reducao-vc-fundamentacao` | 23.5.3 | 219 | Justificativa/critério da redução de 50% da resistência à tração do concreto sob carga cíclica (base do fator 0,5 em Vc) | não computável | baixa | P |  |
| `23.5.4.1-fadiga-concreto-compressao` | 23.5.4.1 | 219 | Verificação da fadiga do concreto em compressão | ausente | média | M | P39 |
| `23.5.4.1-eta-c-grad` | 23.5.4.1 | 219 | Fator de gradiente de tensões de compressão ηc,grad | ausente | média | P | P39 |
| `23.5.4.2-fadiga-concreto-tracao` | 23.5.4.2 | 220 | Verificação da fadiga do concreto em tração | ausente | média | P | P39 |
| `23.5.5-verificacao-fadiga-armadura` | 23.5.5 | 220 | Verificação da fadiga da armadura (passiva ou ativa) | ausente | média | M | P38 |
| `23.5.5-tab23.2-delta-fsd-fad` | 23.5.5 Tabela 23.2 | 220 | Tabela 23.2 - Variação de tensão admissível à fadiga (Δfsd,fad,mín) para 2·10⁶ ciclos, por tipo de barra/detalhe e diâmetro | ausente | média | M | P38 |
| `23.5.5-nota-e-barra-reta-limite` | 23.5.5 nota e | 221 | Limite superior da curva S-N pela resistência da barra reta correspondente | ausente | baixa | P | P38 |
| `23.5.5-fator-redutor-pino-dobramento` | 23.5.5 nota d | 221 | Fator redutor ξ em função do diâmetro do pino de dobramento (para barras dobradas/estribos, base dos valores da Tabela 23.2) | ausente | baixa | P | P38 |
| `23.5.5-tab23.3-tipos-curva` | 23.5.5 Tabela 23.3 | 222 | Tabela 23.3 - Parâmetros das curvas S-N (Tipo, N*, k1, k2) | ausente | média | P | P38 |
| `23.5.5-curva-SN-armadura` | 23.5.5 | 222 | Curva S-N da armadura (resistência à fadiga N para uma amplitude de tensão qualquer, fora dos 2·10⁶ ciclos de referência) | ausente | média | M | P38 |
| `23.5.5-relevo-nervura-r-h` | 23.5.5 | 223 | Condição geométrica de nervura para a Tabela 23.2 ser aplicável (relação raio/altura da saliência) | ausente | baixa | P | P38 |
| `23.6-deformacao-progressiva-ciclica` | 23.6 | 223 | Estimativa do aumento progressivo de deformação (flecha) sob n ciclos de carga | ausente | baixa | P | P38 |
| `23.6-fissuracao-agravada-ciclica` | 23.6 | 223 | ELS de fissuração sob ações cíclicas (aparecimento/agravamento de fissuras) | não computável | baixa | P |  |

## Seção 24

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `24.2-condicoes-uso` | 24.2 | 224 | Condições básicas de aplicabilidade do concreto simples | ausente | baixa | P | P40 |
| `24.2-proibicao-sismo-dutilidade` | 24.2 | 224 | Proibição de concreto simples em sismo, explosão ou onde dutilidade for relevante | não computável | baixa | P |  |
| `24.3-classe-concreto` | 24.3 | 224 | Faixa de classes de concreto permitida em concreto simples | ausente | baixa | P | P40 |
| `24.4-junta-dilatacao-espacamento` | 24.4 | 224 | Espaçamento máximo de juntas de dilatação em concreto simples | ausente | baixa | P | P40 |
| `24.4-distancia-armadura-junta` | 24.4 | 224 | Distância mínima da armadura de distribuição até a junta | ausente | baixa | P | P40 |
| `24.4-qualitativo` | 24.4 | 224 | Interrupções de concretagem e contraventamento em concreto simples | não computável | baixa | P |  |
| `24.5.1-generalidades` | 24.5.1 | 225 | Método dos estados-limites e coeficientes de ponderação do concreto armado para concreto simples | não computável | baixa | P |  |
| `24.5.2.1-fctd-simples` | 24.5.2.1 | 225 | Resistência de cálculo à tração do concreto simples (γc = 1,68) | parcial | média | P | P40 |
| `24.5.2.2-tensoes-resistentes-fibra-extrema` | 24.5.2.2 | 225 | Tensões resistentes de cálculo nas fibras extremas (compressão e tração) | ausente | média | P | P40 |
| `24.5.2.3-tau-wRd-flexao` | 24.5.2.3 | 225 | Tensão de cisalhamento resistente de cálculo em peças lineares de concreto simples | ausente | média | P | P40 |
| `24.5.2.4-6-tau-Rd-limitado` | 24.5.2.4/24.5.2.5/24.5.2.6 | 225 | Tensão de cisalhamento resistente de cálculo em lajes, torção simples e punção de concreto simples | ausente | baixa | P | P40 |
| `24.5.3-altura-concreto-contra-solo` | 24.5.3 | 226 | Redução de altura útil para concreto simples lançado contra o solo | ausente | média | P | P40 |
| `24.5.3-qualitativo` | 24.5.3 | 226 | Critérios de dimensionamento como concreto simples (armadura de distribuição, As menor que o mínimo, durabilidade) | não computável | baixa | P |  |
| `24.5.4.1-limites-deformacao-extrema` | 24.5.4.1 | 226 | Limites de deformação nas fibras extremas do concreto simples à flexão | ausente | média | P | P40 |
| `24.5.4.2-limites-deformacao-media` | 24.5.4.2 | 227 | Limites de deformação média a 0,43h da fibra extrema | ausente | baixa | P | P40 |
| `24.5.4.3-tensoes-resistentes-flexao-simplificada` | 24.5.4.3 | 227 | Tensões resistentes de cálculo simplificadas para flexão (região tracionada e comprimida) | ausente | média | M | P40 |
| `24.5.5.1-tau-wd-secao-retangular` | 24.5.5.1 | 227 | Tensão de cisalhamento atuante em seção retangular de concreto simples | ausente | média | P | P40 |
| `24.5.5.2-3-secao-critica-lajes` | 24.5.5.2/24.5.5.3 | 227 | Seção crítica para cisalhamento e regra especial de lajes (sem redução no apoio) | ausente | baixa | P | P40 |
| `24.5.6-torcao-cisalhamento-interacao` | 24.5.6 | 227 | Verificação de torção e interação torção-cortante em concreto simples | ausente | baixa | P | P40 |
| `24.5.7.2-secao-comprimida-excentrica` | 24.5.7.2 | 228 | Cálculo simplificado de seção comprimida excêntrica de concreto simples (ponto virtual G1 e área eficaz triangular) | ausente | média | G | P41 |
| `24.5.7.3-secao-comprimida-cortante` | 24.5.7.3 | 229 | Verificação combinada de seção a compressão inclinada (normal + cortante) em concreto simples | ausente | baixa | M | P41 |
| `24.5.8-estabilidade-global` | 24.5.8 | 229 | Verificação de estabilidade global em estrutura de concreto simples | não computável | baixa | P |  |
| `24.6.1-NRd-pilar-parede` | 24.6.1 | 229 | Força normal resistente de pilar-parede de concreto simples (fórmula de esbeltez) | ausente | média | P | P41 |
| `24.6.1-comprimento-horizontal-carga` | 24.6.1 | 229 | Comprimento horizontal efetivo do pilar-parede por carga concentrada | ausente | baixa | P | P41 |
| `24.6.1-espessura-minima` | 24.6.1 | 229 | Espessura mínima do pilar-parede de concreto simples | ausente | média | P | P41 |
| `24.6.1-abertura-armadura-minima` | 24.6.1 | 230 | Armadura mínima ao redor de aberturas (portas/janelas) em pilar-parede de concreto simples | ausente | baixa | P | P41 |
| `24.6.1-qualitativo` | 24.6.1 | 230 | Estabilidade global do conjunto e junção entre painéis de pilar-parede | não computável | baixa | P |  |
| `24.6.2-proibicao-bloco-estaca` | 24.6.2 | 230 | Proibição de concreto simples em blocos sobre estacas | ausente | média | P | P41 |
| `24.6.2-area-base-tensao-admissivel` | 24.6.2 | 230 | Área da base de bloco de fundação de concreto simples a partir da tensão admissível do solo | parcial | média | P | P41 |
| `24.6.2-espessura-bloco` | 24.6.2 | 230 | Espessura mínima média de bloco de fundação de concreto simples | ausente | média | P | P41 |
| `24.6.2-momento-secao-critica` | 24.6.2 | 230 | Momento fletor majorado na seção crítica de bloco de concreto simples | ausente | média | M | P41 |
| `24.6.2-cortante-limite` | 24.6.2 | 230 | Força cortante majorada limite na seção crítica de bloco de concreto simples | ausente | média | P | P41 |
| `24.6.3-remissao-pilar-parede` | 24.6.3 | 230 | Cálculo de pilares de concreto simples pelo mesmo método dos pilares-parede | ausente | média | P | P41 |
| `24.6.3-nucleo-central-inercia` | 24.6.3 | 230 | Carga dentro do núcleo central de inércia (pilares sem ações laterais) e verificação com ações laterais (sem tração no concreto) | ausente | média | G | P41 |
| `24.6.3-dimensao-minima` | 24.6.3 | 230 | Dimensão mínima de pilar de concreto simples | ausente | média | P | P41 |
| `24.6.4-sem-tracao` | 24.6.4 | 230 | Ausência de tração em qualquer seção de arco de concreto simples no ELU | ausente | baixa | M | P41 |
| `24.6.4-majoracao-2a-ordem` | 24.6.4 | 230 | Majoração máxima de momento fletor por efeitos de 2ª ordem em arcos de concreto simples | ausente | baixa | P | P41 |

## Seção 25

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `25.1-aceitacao-projeto` | 25.1 | 230 | Aceitação do projeto pelo contratante | não computável | baixa | P |  |
| `25.2-recebimento-materiais` | 25.2 | 231 | Recebimento do concreto e do aço conforme normas complementares | não computável | baixa | P |  |
| `25.3-manual-uso-manutencao` | 25.3 | 231 | Manual de utilização, inspeção e manutenção da estrutura | não computável | baixa | P |  |

## Anexo A

| Id | Item | Pág. | O que é | Situação | Prior. | Compl. | Pacote |
|---|---|---|---|---|---|---|---|
| `A.2.1-eps-imediata` | A.2.1 | 232 | Deformação imediata do concreto por ocasião do carregamento | ausente | média | P | P7 |
| `A.2.2.2-hipoteses` | A.2.2.2 | 233 | Hipóteses de cálculo da fluência (a a f) | não computável | baixa | P |  |
| `A.2.2.3-phi-a` | A.2.2.3 | 234 | Coeficiente de deformação rápida φa | ausente | alta | P | P6 |
| `A.2.2.3-phi-t-t0` | A.2.2.3 | 234 | Coeficiente de fluência φ(t,t0) - procedimento completo | ausente | alta | G | P6 |
| `A.2.2.3-eps-cc` | A.2.2.3 | 234 | Deformação por fluência εcc(t,t0) | ausente | alta | P | P7 |
| `A.2.2.3-phi2c` | A.2.2.3 (A.2.4) | 235 | Coeficiente φ2c (função da espessura fictícia) | ausente | alta | P | P6 |
| `A.2.2.3-phi-f-inf` | A.2.2.3 | 235 | Valor final do coeficiente de deformação lenta irreversível φf∞ | ausente | alta | P | P6 |
| `A.2.2.3-beta-d` | A.2.2.3 | 235 | Coeficiente βd(t) - evolução da deformação lenta reversível | ausente | alta | P | P6 |
| `A.2.2.3-beta-f` | A.2.2.3 | 235 | Coeficiente βf(t) - evolução da deformação lenta irreversível (curva racional em t) | ausente | alta | M | P6 |
| `A.2.3.1-hipoteses` | A.2.3.1 | 236 | Hipóteses básicas da retração (a a c) | não computável | baixa | P |  |
| `A.2.3.2-eps-cs-inf` | A.2.3.2 | 236 | Valor final da retração εcs∞ | ausente | alta | P | P6 |
| `A.2.3.2-eps-cs-t-t0` | A.2.3.2 | 236 | Retração entre os instantes t0 e t | ausente | alta | P | P6 |
| `A.2.3.2-eps2s` | A.2.3.2 | 237 | Coeficiente ε2s (função da espessura fictícia) da retração | ausente | alta | P | P6 |
| `tabelaA.1-principal` | A.2.3.2 (Tabela A.1) | 237 | Tabela A.1 - φ1c, 10⁴·ε1s e γ por ambiente/umidade/abatimento | ausente | alta | P | P6 |
| `tabelaA.1-phi1c-continuo` | A.2.3.2 (Tabela A.1, nota a) | 237 | φ1c contínuo em função da umidade U (nota a da Tabela A.1) | ausente | alta | P | P6 |
| `tabelaA.1-eps1s-continuo` | A.2.3.2 (Tabela A.1, nota b) | 237 | 10⁴·ε1s contínuo em função da umidade U (nota b da Tabela A.1) | ausente | alta | P | P6 |
| `tabelaA.1-ajuste-abatimento` | A.2.3.2 (Tabela A.1, nota c) | 237 | Ajuste de ±25 % de φ1c e ε1s por faixa de abatimento (nota c da Tabela A.1) | ausente | alta | P | P6 |
| `tabelaA.1-gamma` | A.2.3.2 (Tabela A.1, nota d) | 237 | γ contínuo em função da umidade U (nota d da Tabela A.1) | ausente | alta | P | P6 |
| `A.2.3.2-beta-s` | A.2.3.2 | 238 | Coeficiente βs(t) - evolução da retração no tempo (curva racional em t/100) | ausente | alta | M | P6 |
| `tabelaA.2-alpha-idade` | A.2.4.1 (Tabela A.2) | 239 | Tabela A.2 - α por tipo de cimento (para a idade fictícia) | ausente | alta | P | P6 |
| `A.2.4.1-idade-ficticia` | A.2.4.1 | 239 | Idade fictícia do concreto t | ausente | alta | M | P6 |
| `A.2.4.2-hfic` | A.2.4.2 | 240 | Espessura fictícia da peça hfic | implementado | alta | P |  |
| `A.2.5-formula-integral` | A.2.5 | 240 | Deformação total do concreto - forma integral (caso geral, tensão variável) | ausente | baixa | G | P43 |
| `A.2.5-formula-simplificada` | A.2.5 | 240 | Deformação total do concreto - forma prática simplificada (φ como função única) | ausente | média | M | P7 |
| `A.2.5-alfa-decisao` | A.2.5 | 240 | Escolha do coeficiente α (0,5 ou 0,8) na fórmula simplificada de εc(t) | ausente | média | P | P7 |
| `A.2.5-qualitativo-fundacao-deformavel` | A.2.5 | 241 | Alerta - fundações deformáveis e elementos sem deformação lenta (tirantes metálicos) | não computável | baixa | P |  |
| `A.3.1-eps-s` | A.3.1 | 241 | Deformação da armadura sob tensão constante (fluência/relaxação do aço) | parcial | média | P | P7 |
| `A.3.2-eps-s-impedida` | A.3.2 | 241 | Deformação total da armadura quando a fluência livre é impedida | ausente | média | M | P7 |
