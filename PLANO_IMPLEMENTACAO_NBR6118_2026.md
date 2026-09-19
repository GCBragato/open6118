# Plano de implementação do restante da NBR 6118:2026 no open6118

*18/09/2026 — plano, não implementação. Nada no código foi alterado para escrevê-lo; os arquivos novos são só este plano e os dois anexos.*

*Revisto em 19/09/2026 com as seis decisões do Gustavo (seção 6). A principal: a análise estrutural que a 6118 prescreve entrou no plano, com cálculo próprio de barras (pacotes P44 a P48).*

## 1. Resposta curta

1. **O que o plano cobre.** A norma inteira, das seções 5 a 25 mais o Anexo A, mapeada em 662 itens. Desses, 143 não são computáveis (texto de princípio, remissão a outra norma, recomendação de projeto) e ficam fora por natureza. Sobram **519 itens computáveis**:
   - **75 implementados** (o código de hoje, já auditado e corrigido);
   - **58 parciais** (a função existe, mas falta um ramo, uma tabela inteira ou a validação);
   - **386 ausentes**.
2. **Como está dividido.** Os 444 itens parciais ou ausentes estão distribuídos assim:
   - **443 em 48 pacotes**, cada um coeso (um módulo ou um tema) e do tamanho de uma rodada de agente, de 2 a 18 itens;
   - **1 fora do escopo:** o vento, que é da NBR 6123. A biblioteca recebe os esforços de vento prontos e os combina.
3. **Uma preparação e quatro ondas.**
   - **Preparação:** renomear os módulos `*_bastos.py` para `*_nbr6118.py` (decisão 4). Neste plano, os nomes de módulo já estão na forma nova.
   - **Onda 1, fundação (P1 a P9):** durabilidade, materiais, ações e combinações, fluência e retração, ELS base. Quase tudo o que vem depois consome isso.
   - **Onda 2, uso corrente em edifícios (P10 a P26, P44 e P45):** limites geométricos, cortante e torção completos, lajes, **punção** (a maior lacuna: não existe punção de laje; só a de sapata rígida), detalhamento de vigas e pilares, 2ª ordem de pilares, estabilidade global e o **cálculo próprio de estruturas de barras** (pórtico, grelha e treliça), com as lajes nervuradas e lisas por grelha e por pórtico equivalente.
   - **Onda 3, prioridade média (P27 a P37 e P46 a P48):** emendas, protensão completa, bielas e tirantes, consolos, fundações, regiões especiais, pilar-parede, o crescimento do kernel, a 2ª ordem global por análise não linear, os esforços hiperestáticos de protensão e os modelos de bielas e tirantes de viga-parede, sapata e bloco.
   - **Onda 4, prioridade baixa (P38 a P43):** fadiga, concreto simples, perfis abertos e o método geral de perdas.
4. **Por que essa ordem.** Punção, flecha e detalhamento são o que o escritório mais usa, mas dependem de ações combinadas (P4), de fluência (P6), do estádio II (P9) e do wk,máx pela classe de agressividade (P1). Fazer a base primeiro evita que cada pacote de uso corrente reimplemente um pedaço dela, que foi exatamente o problema que a auditoria encontrou (11 cópias de fct,m). O cálculo de barras (P44) vem logo depois das combinações, porque é delas que saem os casos de carga.
5. **Tamanho.** São cerca de 410 a 460 funções novas ou estendidas e, numa estimativa, uns 1 400 a 1 700 testes novos. Na execução: 48 rodadas de implementação, cada uma seguida de 3 verificações independentes. Com as ondas 1 e 2 em paralelo onde não há dependência, o grosso (ondas 1 e 2, 28 pacotes) cabe em 7 levas de agentes (seção 5).
6. **O que mudou em 19/09/2026.** Com a análise estrutural no escopo, 21 itens entraram em pacotes: os 7 que estavam fora por serem análise, 13 que estavam como não computáveis só porque a biblioteca não calculava estrutura, e 1 item que o mapa não tinha (15.7.1). Eles formam os pacotes P44 a P48.

## 2. Onde o código está hoje

A tabela já reflete a revisão de 19/09/2026: os 13 itens de análise que eram não computáveis aparecem como ausentes.

| Seção | Impl. | Parcial | Ausente | Não comp. |
|---|---|---|---|---|
| 5 Segurança e ATP | 0 | 0 | 1 | 3 |
| 6 Durabilidade | 0 | 0 | 2 | 1 |
| 7 Critérios de durabilidade | 0 | 3 | 3 | 1 |
| 8 Materiais | 10 | 3 | 10 | 4 |
| 9 Aderência, ancoragem, protensão | 16 | 9 | 37 | 9 |
| 10 Estados-limites | 0 | 1 | 0 | 3 |
| 11 Ações | 3 | 6 | 21 | 10 |
| 12 Resistências | 6 | 1 | 3 | 5 |
| 13 Limites | 1 | 2 | 15 | 6 |
| 14 Análise estrutural | 4 | 3 | 34 | 15 |
| 15 Instabilidade e 2ª ordem | 5 | 4 | 21 | 7 |
| 16 Princípios de projeto | 0 | 0 | 0 | 8 |
| 17 Dimensionamento (lineares) | 20 | 10 | 35 | 13 |
| 18 Detalhamento (lineares) | 3 | 3 | 38 | 18 |
| 19 Lajes | 2 | 5 | 25 | 2 |
| 20 Detalhamento de lajes | 0 | 0 | 23 | 3 |
| 21 Regiões especiais | 0 | 0 | 11 | 9 |
| 22 Elementos especiais | 4 | 4 | 32 | 11 |
| 23 Fadiga e vibração | 0 | 1 | 23 | 3 |
| 24 Concreto simples | 0 | 2 | 29 | 6 |
| 25 Interfaces | 0 | 0 | 0 | 3 |
| Anexo A | 1 | 1 | 23 | 3 |


**Leitura.**

1. O que existe é o **cálculo de esforço resistente de seção**: flexão (inclusive oblíqua, com backend C++), cortante, torção, ancoragem passiva, pilar-padrão até λ = 90, perdas de protensão e fundações pelos métodos de apostila. Essa parte foi auditada hoje e está correta.
2. O que falta é quase tudo **em volta** da seção: de onde vêm os esforços de cálculo (a seção 11 inteira, sem nenhum objeto "ação", e a própria análise que produz os esforços), o que se faz depois (detalhamento: a seção 20 inteira e 38 dos 44 itens da 18) e os estados-limites de serviço além do wk (flecha de viga, limites da Tabela 13.3, estádio II genérico).
3. Há **três buracos grandes de elemento**: punção em laje (19.5, nenhuma linha), consolos, dentes Gerber e vigas-parede (22.4 e 22.5, nenhuma linha) e concreto simples (seção 24 inteira).
4. A seção 14 é a da análise estrutural. Até 18/09 ela ficava com o TQS; com a decisão 1, a biblioteca ganha um cálculo próprio de barras (P44 a P48), e 8 itens dela que eram não computáveis passaram a ter o que calcular. Os 15 que continuam não computáveis são princípios e hipóteses gerais.
5. Várias fórmulas já prontas moram no lugar errado e precisam **mudar de casa antes de ganhar consumidores**:
   - a Tabela 8.1 (φ e εcs) está em `protendido_nbr6118.py`, mas serve a flecha e a pilar;
   - `alpha_f` e `momento_fissuracao` estão em `lajes_nbr6118.py`, mas servem a vigas;
   - `vao_efetivo` também está em `lajes_nbr6118.py`, e serve a vigas;
   - a ancoragem de armadura ativa só existe no legado `secoes_norma/sec9.py`;
   - `GAMA_F = 1,4` está redefinido em 5 arquivos (vigas, lajes, cortante, sapatas e blocos).

## 3. Arquitetura e convenções para o código novo

### 3.1 Fronteira do escopo: a biblioteca calcula estruturas de barras

**Decidido em 19/09/2026 (decisão 1):** o que a 6118 prescreve como análise estrutural entra no plano, com cálculo próprio em Python e só com barras.

- **Entra:**
  - pórtico plano e espacial, grelha e treliça 2D e 3D, pelo método dos deslocamentos (P44);
  - laje nervurada e laje lisa por grelha e por pórtico equivalente (P45);
  - redistribuição com reequilíbrio e 2ª ordem global por análise não linear, com as rigidezes de 15.7.3 (P46);
  - esforços hiperestáticos de protensão (P47);
  - bielas e tirantes: as treliças de regiões D, viga-parede, sapata e bloco (P48).
  - e, como já estava, a análise não linear de uma barra isolada (método geral de pilar, 15.8.3.2), no P28.
- **Continua valendo** tudo o que recebe o resultado de uma análise: γz e α (P26), a verificação de redistribuição (P13), o arredondamento do diagrama sobre apoios e os mínimos de viga contínua (P14), a repartição do pórtico equivalente entre faixas (P17) e o desaprumo global contra o vento (P26). Cada uma dessas funções aceita tanto o número vindo de um programa externo, como o TQS, quanto o modelo da própria biblioteca.
- **Fica de fora:**
  - elementos finitos de placa e de sólido. A laje lisa entra como grelha equivalente, que a 14.7.8 aceita, e o bloco e a sapata como treliça 3D de bielas e tirantes, que a 22.6.3 e a 22.7.3 aceitam;
  - o vento (NBR 6123). A biblioteca recebe os esforços de vento, combina-os (P4) e os compara com o desaprumo (P26).
- **Como se confere o que a norma não tabela:** a análise não tem valor esperado na norma. Os testes usam solução fechada (viga contínua, pórtico simples, treliça isostática, placa de Timoshenko para a grelha) e conferem o equilíbrio em todo resultado. O verificador de execução refaz cada caso com solução analítica própria. A comparação com o TQS serve de conferência cruzada, não de referência.
- Em cada função que recebe resultado de análise, a docstring diz de onde o número pode vir: do modelo da biblioteca ou de um programa externo, por exemplo "ΔMtot,d: da análise linear do pórtico com as rigidezes de 15.7.3 (P46, ou o relatório de γz do TQS)".

### 3.2 Organização dos módulos

1. **Nome por tema da norma, com sufixo `_nbr6118`:** `acoes_nbr6118.py`, `puncao_nbr6118.py`, `detalhamento_vigas_nbr6118.py` e assim por diante. Nada de apostila no nome de módulo novo.
2. **Os `*_bastos.py` são renomeados para `*_nbr6118.py` antes da onda 1** (decisão 4), sem fachada no nome antigo: quem importa o nome antigo troca o import. As assinaturas das funções não mudam, só o nome do módulo. O crédito às apostilas do Prof. Paulo Sérgio Bastos passa para a docstring de cada módulo e para o README. Daqui em diante, este plano usa os nomes novos:

   | Hoje | Depois da preparação |
   |---|---|
   | `vigas_bastos.py` | `vigas_nbr6118.py` |
   | `lajes_bastos.py` | `lajes_nbr6118.py` |
   | `pilares_bastos.py` | `pilares_nbr6118.py` |
   | `cortante_bastos.py` | `cortante_nbr6118.py` |
   | `torcao_bastos.py` | `torcao_nbr6118.py` |
   | `ancoragem_bastos.py` | `ancoragem_nbr6118.py` |
   | `protendido_bastos.py` | `protendido_nbr6118.py` |
   | `sapatas_bastos.py` | `sapatas_nbr6118.py` |
   | `blocos_bastos.py` | `blocos_nbr6118.py` |
   | `viga_servico_bastos.py` | `viga_servico_nbr6118.py` |
3. **Núcleo único.** O que for grandeza de material ou parâmetro geral vai para `nucleo_nbr6118.py`:
   - o que entra: massa específica, ν, dilatação, a Tabela 8.1 (promovida de `protendido_bastos`), `GAMA_F`, a Tabela 13.4 e a normalização única de CAA;
   - o arquivo tem ~620 linhas; se passar de ~1 200, divide-se em `nucleo_nbr6118/` (pacote) com reexportação, sem mudar import.
4. **Promover antes de consumir.** Função no lugar errado muda de casa no pacote que primeiro precisar dela, com reexportação no lugar antigo:
   - `alpha_f` e `momento_fissuracao` vão para `els_deformacao_nbr6118` (P8);
   - `vao_efetivo` vai para `analise_linear_nbr6118` (P14);
   - a ancoragem ativa vai para `ancoragem_bastos` (P31).
5. **Legado `secoes_norma/`:** não recebe nada novo. Cada pacote que cobre um item que também existe no legado transforma a função legada em fachada de uma linha sobre a nova, com `DeprecationWarning`. Na correção de hoje o legado foi consertado e passou a delegar ao núcleo; aposentá-lo de vez (decisão 5 da auditoria) continua em aberto e não bloqueia nenhum pacote.

### 3.3 Convenções de código (as do núcleo, obrigatórias)

1. **Unidades no nome.**
   - Os sufixos são `_mpa`, `_kncm2`, `_kn`, `_kncm`, `_cm`, `_mm`, `_cm2`, `_cm2_por_m`, `_pmil` (‰) e `_dias`.
   - Os padrões de entrada são: tensão e fck em MPa; seção em cm; diâmetro em mm; esforço em kN e kN·cm; deformação em ‰.
   - Quando a norma dá a fórmula em outra unidade, a conversão fica **dentro** da função e é citada na docstring. O caso crítico é o h do Anexo A: em cm em φ2c e ε2s, em m em βf e βs (P6).
2. **Docstring:** a primeira linha diz o que calcula e o item. Depois vêm a fórmula (conferida na imagem da página), as unidades e a faixa de validade, com a página do PDF, como no núcleo.
3. **Faixa de validade:** fora dela, levantar `FaixaNormativaError`, nunca devolver número. Célula "–" de tabela (Tabela 9.2 com CA-60 e φ ≥ 20 mm, Tabela 23.2) também levanta erro, com a mensagem dizendo que a norma não define.
4. **Resultados:**
   - função de fórmula devolve `float`;
   - verificação e dimensionamento devolvem `@dataclass(frozen=True)` no padrão de `ResultadoCortante`, com os valores, os limites, `ok: bool`, `governante: str` e `memoria: list[str]`;
   - `memoria` traz as linhas legíveis da memória de cálculo, com item da norma, fórmula e números. Isso atende o memorial de cálculo e é barato de gerar na hora.
5. **Mensagens ao usuário em português acentuado:** erro, aviso e memória. Identificador em ASCII. Aviso via `AvisoNBR6118` (já existe no kernel), movido para o núcleo.
6. **Tolerância de comparação:** `Rd >= Sd` com tolerância relativa de 1e-9, numa função única `verificar_seguranca` (P5), no lugar de cada módulo decidir entre `>` e `>=`.
7. **Tabelas como dado:** `dict` ou tupla no topo do módulo, com o nome da tabela (`TABELA_11_2_PSI`). A interpolação é explícita (`interp=True/False`) e segue o texto da norma; a função de consulta cita se interpola.
8. **Assinaturas públicas existentes não quebram.** Parâmetro novo entra no fim, com padrão que reproduz o comportamento atual. A exceção é a troca de nome dos módulos (decisão 4) e a Figura 8.6 como padrão (decisão 2), que mudam de propósito.
9. **Parâmetros configuráveis no começo do script.** Coeficiente que o engenheiro pode ter de mudar por projeto fica num bloco "Parâmetros configuráveis" no topo do núcleo, com o valor padrão da norma. O primeiro é o γg (decisão 3): `GAMA_G = 1.4`, e 1,3 quando a obra se enquadrar na nota a da Tabela 11.1. As funções leem o valor na hora da chamada, não no import, e aceitam também o valor explícito por argumento. O script do usuário muda no começo (`nucleo.GAMA_G = 1.3`), e a memória de cálculo registra o valor usado.

### 3.4 Kernel de flexão oblíqua: onde cresce e em qual linguagem

**Recomendação: crescer em Python. O C++ fica só com o que já faz**, o ELU de seção com armadura passiva e curva padrão, onde a paridade foi medida em 1 800 casos.

| Capacidade | Onde | Por quê |
|---|---|---|
| Rótulo de domínio (reta a, 1 a 5, 4a, reta b) | Python, P28 | Pós-processamento de uma deformada já achada; custo desprezível |
| Tensões em serviço, estádios I e II, seção poligonal | Python, P9 | Já existe `_esforcos_internos_els` e `solver_els`; falta expor a função pública |
| Diagrama M-N-1/r e método geral de pilar | Python, P28 | Chamado dezenas de vezes por pilar, não milhares; `ei_secante` já faz o essencial |
| Figura 8.6 com ramo inclinado | Python, P3 | O C++ não modela armadura ativa; o dispatcher já cai para o Python com cabos |
| Domínio 1 e flexo-tração no ELU | Já coberto pelo solver de planos de deformação | Só falta o rótulo e o teste de tração pura |
| Cálculo de barras (P44 a P48) | Python, com numpy e scipy.sparse | Roda uma vez por modelo e por caso; o custo está na solução do sistema esparso, que o scipy já faz em código compilado |

- **Quando portar para C++:** só se um uso medido ficar lento. O caso provável é a envoltória de pilar-parede com muitas faixas (P29).
- **Regra para o dispatcher:** caso sem paridade medida vai para o Python com `AvisoNBR6118`, como hoje.

### 3.5 Testes

1. **Valor esperado tirado da norma:** tabela, exemplo numérico, caso-limite de fórmula (x/d na fronteira, l/h = 2,0 exato, degrau de faixa). Nunca de apostila sem conferir.
2. **Cada tabela é testada em todas as células**, e cada fórmula nas duas bordas da faixa e num ponto interior.
3. **Um arquivo por pacote**, `tests/test_<modulo>.py`. O teste cita o item e a página.
4. **Cálculo à mão:** quando o valor esperado depende de cálculo, o verificador de execução refaz com script próprio, sem importar a biblioteca.

## 4. Pacotes

Formato: objetivo; itens (id do mapa · item da norma · página do PDF); o que criar; depende de; testes e aceite; tamanho e onda. Os pacotes P44 a P48, da análise estrutural, vêm depois do P43 porque entraram na revisão de 19/09/2026; a onda de cada um está na seção 5. Tamanho P é até 8 funções, M de 9 a 16, G acima de 16 ou com algoritmo iterativo.

### P1 — Durabilidade, cobrimento e abertura de fissura admissível

- **Objetivo:** Fechar o fluxo ambiente → CAA → a/c, classe mínima, cobrimento e wk,máx num lugar só, com uma normalização única de CAA.
- **Onda 1**, prioridade alta. Módulo: dimensionamento/durabilidade_nbr6118.py + nucleo_nbr6118.py.
- **Itens (10):**
  - `5.3-tab5.1-classes-consequencia` · 5.3.2 (Tabela 5.1) · p. 32
  - `6.1-6.2-vida-util-projeto` · 6.1, 6.2.4 · p. 34
  - `6.4-tab6.1-classes-agressividade` · 6.4 (Tabela 6.1) · p. 36
  - `7.4.2-tab7.1-relacao-ac-classe-concreto` · 7.4.2 (Tabela 7.1) · p. 38
  - `7.4.7.1-cnom-cmin-formula` · 7.4.7.1-7.4.7.3 · p. 38
  - `7.4.7.4-delta-c-premoldados` · 7.4.7.4 · p. 38
  - `7.4.7.5-cnom-minimos-barra-feixe-bainha` · 7.4.7.5 · p. 39
  - `7.4.7.6-dmax-agregado-cobrimento` · 7.4.7.6 · p. 39
  - `7.4.7-tab7.2-cobrimento-nominal` · 7.4.7.2, 7.4.7.6-nota, Tabela 7.2 · p. 39
  - `13.4.2-tab13.4-wk-max-caa` · 13.4.2, Tabela 13.4 · p. 100-101
- **O que criar:**
  - `durabilidade_nbr6118.py`: `classe_consequencia(tipo_obra) -> str` (Tabela 5.1); `VIDA_UTIL_PROJETO_ANOS = 50` (6.2.4); `TABELA_6_1` e `classe_agressividade(ambiente, microclima_seco=False, revestido=False) -> str` com as notas a/b/c.
  - `relacao_ac_maxima(caa, protendido) -> float` e `classe_concreto_minima(caa, protendido) -> int` (Tabela 7.1), substituindo `sec7.CAAPropriedades` por fachada.
  - No núcleo: `normalizar_caa(caa) -> str` único (usado por `cobrimento_nominal`); `cobrimento_minimo_mm(...)` e `cobrimento_nominal(..., delta_c_mm=10, reducao_classe_superior=False, face_revestida=False)` expondo cmín e Δc (7.4.7.1-7.4.7.4, Tabela 7.2 com notas).
  - `verificar_cobrimento(cnom_mm, phi_mm, phi_feixe_mm=None, phi_bainha_mm=None) -> ResultadoCobrimento` (7.4.7.5) e `dmax_agregado_mm(cnom_mm)` (7.4.7.6).
  - No núcleo: `wk_max_mm(tipo_concreto, caa, nivel_protensao=None) -> tuple[float|None, str]` (Tabela 13.4: wk e combinação a usar). `viga_servico_nbr6118.abertura_fissura_wk` passa a aceitar `caa=` e busca o limite ali, mantendo `wk_max_mm` explícito como alternativa.
- **Depende de:** Nenhum.
- **Testes e aceite:** Todas as células das Tabelas 6.1, 7.1, 7.2 e 13.4 (p. 36, 38, 39 e 100); cnom com Δc = 5 mm; φ de feixe maior que cnom levanta aviso. Aceite: `cobrimento_nominal` antigo dá os mesmos números com os padrões.
- **Tamanho:** M (12 a 14 funções).

### P2 — Propriedades complementares dos materiais

- **Objetivo:** Completar as grandezas de material que faltam no núcleo, para peso próprio, temperatura, estádio I e análise não linear.
- **Onda 1**, prioridade média. Módulo: dimensionamento/nucleo_nbr6118.py.
- **Itens (11):**
  - `8.2.2-massa-especifica-concreto` · 8.2.2 · p. 42
  - `8.2.3-dilatacao-termica-concreto` · 8.2.3 · p. 42
  - `8.2.5-fct-conversao-ensaios-indiretos` · 8.2.5 · p. 42
  - `8.2.6-resistencia-multiaxial` · 8.2.6 · p. 42
  - `8.2.9-poisson-Gc` · 8.2.9 · p. 45
  - `8.2.10.1-fig8.3-diagrama-nao-linear` · 8.2.10.1 (Figura 8.3) · p. 46
  - `8.2.10.2-fig8.4-diagrama-bilinear-tracao` · 8.2.10.2 (Figura 8.4) · p. 46
  - `8.3.3-8.4.2-massa-especifica-aco` · 8.3.3, 8.4.2 · p. 48
  - `8.3.4-8.4.3-dilatacao-termica-aco` · 8.3.4, 8.4.3 · p. 48
  - `8.3.7-dutilidade-aco-passivo` · 8.3.7 · p. 49
  - `14.7.3-poisson-placas` · 14.7.3 · p. 116
- **O que criar:**
  - Constantes: `MASSA_ESPECIFICA_CONCRETO_SIMPLES/ARMADO_KG_M3` (8.2.2), `ALFA_TERMICO_CONCRETO` (8.2.3), `ALFA_TERMICO_ACO` com faixas de temperatura (8.3.4, 8.4.3), `MASSA_ESPECIFICA_ACO_KG_M3` (8.3.3, 8.4.2), `POISSON_CONCRETO = 0.2` (8.2.9, também 14.7.3).
  - `fct_de_ensaio(fct_sp_mpa=None, fct_f_mpa=None) -> float` (8.2.5).
  - `verificar_tensao_multiaxial(sigma1, sigma2, sigma3, fck_mpa) -> Resultado` (8.2.6).
  - `sigma_c_nao_linear(eps_c_pmil, fcm_mpa, Eci_mpa) -> float` (Figura 8.3) e `sigma_ct(eps_ct_pmil, fck_mpa) -> float` bilinear de tração (Figura 8.4).
  - `dutilidade_aco_passivo(categoria) -> str` (8.3.7).
- **Depende de:** Nenhum.
- **Testes e aceite:** Valores literais do texto (p. 42 a 49); Figura 8.3 contínua em εc1 e com pico em fcm; Figura 8.4 com os dois trechos conferidos na imagem (p. 46).
- **Tamanho:** M (12 funções e constantes).

### P3 — Aço de protensão: catálogo e diagrama da Figura 8.6

- **Objetivo:** Dar ao aço de protensão o catálogo completo (fios e cordoalhas, RN e RB) e o diagrama da Figura 8.6 com o segundo trecho ascendente até fptd em εpu, como padrão (decisão 2).
- **Onda 1**, prioridade alta. Módulo: dimensionamento/nucleo_nbr6118.py + rotinas/flexao_composta_obliqua.py + protendido_nbr6118.py.
- **Itens (3):**
  - `8.4.1-classificacao-aco-ativo` · 8.4.1 · p. 49
  - `8.4.5-fig8.6-diagrama-aco-ativo` · 8.4.5 (Figura 8.6) · p. 50
  - `8.4.6-dutilidade-aco-ativo` · 8.4.6 · p. 50
- **O que criar:**
  - No núcleo: `sigma_p(eps_p_pmil, fpyk_mpa, fptk_mpa, Ep_mpa=EP_MPA, eps_pu_pmil=35.0, gama_s=GAMA_S, diagrama='nbr_fig_8_6'|'patamar') -> float`, com a Figura 8.6 como padrão.
  - No kernel: `CurvaApBilinear(..., ramo_inclinado=True)`: reta de (εpyd, fpyd) a (εpu, fptd); com `False`, o patamar de hoje. O padrão passa a ser a Figura 8.6 (decisão 2), e o achado FCO-17 da auditoria deixa de ser escolha documentada.
  - `protendido_nbr6118`: `TABELA_ACOS_ATIVOS` (fios e cordoalhas, RN/RB, NBR 7482/7483) e `dutilidade_aco_ativo(eps_uk, minimo)` (8.4.6).
- **Depende de:** Nenhum. O dispatcher já manda casos com cabos para o Python; confirmar.
- **Testes e aceite:** Pontos (εpyd, fpyd) e (εpu, fptd) exatos para CP-190 RB; monotonia; MRd de seção protendida com ramo inclinado ≥ MRd com patamar. Aceite: só mudam os testes de seção protendida no ELU, e o parecer lista cada um com o valor antes e depois (a expectativa é de 2 % a 3 % a mais no MRd); com `diagrama='patamar'`, eles voltam aos números de hoje.
- **Tamanho:** P (5 a 6 funções).

### P4 — Ações e combinações

- **Objetivo:** Criar o modelo de dados de ação e as combinações das Tabelas 11.3 e 11.4, que hoje o engenheiro faz à mão antes de chamar cada rotina.
- **Onda 1**, prioridade alta. Módulo: dimensionamento/acoes_nbr6118.py.
- **Itens (18):**
  - `11.2.2-classificacao-acoes` · 11.2.2 · p. 76
  - `11.6.2-valores-representativos` · 11.6.2 · p. 84
  - `11.6.3-valores-calculo` · 11.6.3 · p. 84
  - `11.7-gamma_f-decomposicao` · 11.7 · p. 84
  - `11.7.1-tabela-11.1-gamma_f` · 11.7.1 · p. 85
  - `11.7.1-tabela-11.2-gamma_f2-psi` · 11.7.1 · p. 85
  - `11.7.2-gamma_f-els` · 11.7.2 · p. 86
  - `11.8.2.1-combinacao-ultima-normal` · 11.8.2.1 / 11.8.2.4 (Tabela 11.3) · p. 87
  - `11.8.2.2-combinacao-ultima-especial-construcao` · 11.8.2.2 / 11.8.2.4 (Tabela 11.3) · p. 87
  - `11.8.2.3-combinacao-ultima-excepcional` · 11.8.2.3 / 11.8.2.4 (Tabela 11.3) · p. 87
  - `11.5-acoes-excepcionais` · 11.5 · p. 83
  - `11.8.3.2-combinacao-quase-permanente-servico` · 11.8.3.2 (Tabela 11.4) · p. 89
  - `11.8.3.2-combinacao-frequente-servico` · 11.8.3.2 (Tabela 11.4) · p. 89
  - `11.8.3.2-combinacao-rara-servico` · 11.8.3.2 (Tabela 11.4) · p. 89
  - `11.4.1.3-acao-agua` · 11.4.1.3 · p. 82
  - `11.4.2.1-temperatura-uniforme` · 11.4.2.1 · p. 82
  - `11.4.2.2-temperatura-nao-uniforme` · 11.4.2.2 · p. 83
  - `15.3-combinacao-sdtot` · 15.3 · p. 121
- **O que criar:**
  - `acoes_nbr6118.py`: `@dataclass Acao(nome, natureza, tipo, Fk, Fk_inf=None, categoria_psi=None)`, com natureza permanente direta/indireta, variável direta/indireta ou excepcional (11.2.2).
  - `TABELA_11_1` (combinação × ação × D/F) e `gama_f(acao, combinacao, favoravel, gama_g=None)`; o γg das permanentes vem de `nucleo.GAMA_G`, padrão 1,4, configurável no começo do script quando a obra se enquadrar na nota a (γg = 1,3; o critério é da NBR 8681) (decisão 3); `GAMA_F1/F2/F3` nomeados (11.7).
  - `TABELA_11_2_PSI` e `psi(categoria) -> (psi0, psi1, psi2)`; `valor_representativo(acao, tipo)` (11.6.2); `valor_calculo(F, gama)` (11.6.3).
  - `combinacao_ultima(acoes, tipo='normal'|'especial'|'construcao'|'excepcional', principal=None) -> ResultadoCombinacao` (11.8.2.1 a 11.8.2.3, Tabela 11.3), com varredura automática da variável principal quando `principal=None`.
  - `combinacao_servico(acoes, tipo='quase_permanente'|'frequente'|'rara')` (11.8.3.2, Tabela 11.4); `gama_f_els(tipo)` (11.7.2).
  - `combinacao_2a_ordem_sdtot(...)` com γf3 (15.3); `acao_agua(...)` com γf = 1,2 (11.4.1.3); `variacao_temperatura_uniforme(menor_dim_cm)` e `GRADIENTE_TERMICO_MIN_C = 5` (11.4.2).
  - No núcleo, no bloco de parâmetros configuráveis (3.3, item 9): `GAMA_F = 1.4` e `GAMA_G = 1.4`; os 5 módulos que redefinem `GAMA_F` passam a lê-lo de lá.
- **Depende de:** Nenhum.
- **Testes e aceite:** Todas as células das Tabelas 11.1 e 11.2 (p. 85); combinação normal de um caso com 2 variáveis montada à mão; as três de serviço; a interpolação de temperatura entre 50 e 70 cm; `nucleo.GAMA_G = 1.3` no começo do script muda a combinação, e a memória registra o valor usado.
- **Tamanho:** G (18 a 20 funções), o maior da onda 1.

### P5 — Verificação de segurança e coeficientes de resistência

- **Objetivo:** Dar um lugar único para Rd ≥ Sd, para o equilíbrio de corpo rígido e para os ajustes de γc e γs.
- **Onda 1**, prioridade média. Módulo: dimensionamento/seguranca_nbr6118.py + nucleo_nbr6118.py.
- **Itens (6):**
  - `10.3-lista-elu` · 10.3 · p. 74
  - `11.8.2.1-perda-equilibrio-corpo-rigido` · 11.8.2.1 (Tabela 11.3) · p. 87
  - `12.4-gamma_m-decomposicao` · 12.4 · p. 91
  - `12.4.1-gamma_c-condicoes-desfavoraveis` · 12.4.1 · p. 91
  - `12.4.1-gamma_c-testemunhos-extraidos` · 12.4.1 · p. 91
  - `12.4.1-gamma_s-ca25-sem-controle` · 12.4.1 · p. 91
- **O que criar:**
  - `seguranca_nbr6118.py`: `verificar_seguranca(Rd, Sd, rotulo, item) -> ResultadoSeguranca` (12.5.2, tolerância 1e-9); `verificar_equilibrio_corpo_rigido(F_estabilizante, F_desestabilizante)` com os γ próprios da Tabela 11.3 (11.8.2.1).
  - `ESTADOS_LIMITES_ULTIMOS` (10.3, a a h) e `checklist_elu(verificados: set) -> list[str]` para memória de cálculo.
  - No núcleo: `gama_c_ajustado(combinacao, execucao_desfavoravel=False, testemunho_extraido=False)` e `gama_s_ajustado(combinacao, ca25_sem_controle=False)` (12.4.1); `GAMA_M_ELS = 1.0` (12.4.2) e a decomposição γm1·γm2·γm3 documentada (12.4).
- **Depende de:** P4 (γ do equilíbrio).
- **Testes e aceite:** Os três fatores de 1,1 (p. 91); Rd = Sd passa, Rd = Sd·(1 − 1e-6) não passa.
- **Tamanho:** P (6 a 7 funções).

### P6 — Fluência e retração: motor do Anexo A

- **Objetivo:** Implementar o Anexo A (fluência e retração com precisão), que serve à flecha diferida, ao pilar esbelto e às perdas de protensão.
- **Onda 1**, prioridade alta. Módulo: dimensionamento/tempo_concreto_nbr6118.py.
- **Itens (17):**
  - `A.2.2.3-phi-a` · A.2.2.3 · p. 234
  - `A.2.2.3-phi2c` · A.2.2.3 (A.2.4) · p. 235
  - `A.2.2.3-phi-f-inf` · A.2.2.3 · p. 235
  - `A.2.2.3-beta-d` · A.2.2.3 · p. 235
  - `A.2.2.3-beta-f` · A.2.2.3 · p. 235
  - `A.2.2.3-phi-t-t0` · A.2.2.3 · p. 234
  - `A.2.3.2-eps2s` · A.2.3.2 · p. 237
  - `A.2.3.2-eps-cs-inf` · A.2.3.2 · p. 236
  - `A.2.3.2-beta-s` · A.2.3.2 · p. 238
  - `A.2.3.2-eps-cs-t-t0` · A.2.3.2 · p. 236
  - `tabelaA.1-principal` · A.2.3.2 (Tabela A.1) · p. 237
  - `tabelaA.1-phi1c-continuo` · A.2.3.2 (Tabela A.1, nota a) · p. 237
  - `tabelaA.1-eps1s-continuo` · A.2.3.2 (Tabela A.1, nota b) · p. 237
  - `tabelaA.1-ajuste-abatimento` · A.2.3.2 (Tabela A.1, nota c) · p. 237
  - `tabelaA.1-gamma` · A.2.3.2 (Tabela A.1, nota d) · p. 237
  - `tabelaA.2-alpha-idade` · A.2.4.1 (Tabela A.2) · p. 239
  - `A.2.4.1-idade-ficticia` · A.2.4.1 · p. 239
- **O que criar:**
  - `tempo_concreto_nbr6118.py`: `TABELA_A_1` e `phi1c(U, abatimento_cm)`, `eps1s(U, abatimento_cm)`, `gama_umidade(U)` com as notas a a d (Tabela A.1).
  - `TABELA_A_2_ALFA` e `idade_ficticia_dias(historico=[(T_C, dias)], cimento)` (A.2.4.1).
  - `espessura_ficticia_ponderada_cm(Ac_cm2, uar_cm, U)` (A.2.4.2, promovendo `h_ficticia_cm`).
  - `phi_a(fck, t0)`, `phi2c(h_cm)`, `phi_f_inf(...)` (0,45 no C50 a C90), `beta_f(t, h_cm)` (converte para m dentro), `beta_d(t, t0)`, `phi(t, t0, ...)` (A.2.2.3).
  - `eps2s(h_cm)`, `eps_cs_inf(...)`, `beta_s(t, h_cm)`, `eps_cs(t, t0, ...)` (A.2.3.2).
  - Promover `phi_eps_cs_NBR` e a Tabela 8.1 de `protendido_nbr6118` para o núcleo, com reexportação.
- **Depende de:** Nenhum (usa `nucleo.fckj`).
- **Testes e aceite:** Células da Tabela A.1 (p. 237) e da Tabela A.2 (p. 239); continuidade das fórmulas da nota a/b com a tabela em U = 40, 70 e 90 %; um caso completo φ(∞, t0) comparado com a Tabela 8.1 (a ordem de grandeza deve bater); teste cruzado que falha se h entrar em m onde é cm.
- **Tamanho:** G (17 a 19 funções).

### P7 — Deformações diferidas do concreto e da armadura

- **Objetivo:** Montar as deformações diferidas do concreto e da armadura sobre o motor do P6, incluindo os atalhos da seção 11.
- **Onda 1**, prioridade média. Módulo: dimensionamento/tempo_concreto_nbr6118.py.
- **Itens (8):**
  - `A.2.1-eps-imediata` · A.2.1 · p. 232
  - `A.2.2.3-eps-cc` · A.2.2.3 · p. 234
  - `A.2.5-formula-simplificada` · A.2.5 · p. 240
  - `A.2.5-alfa-decisao` · A.2.5 · p. 240
  - `A.3.1-eps-s` · A.3.1 · p. 241
  - `A.3.2-eps-s-impedida` · A.3.2 · p. 241
  - `11.3.3.1-retracao-valor-simplificado` · 11.3.3.1 · p. 77
  - `11.3.3.2-fluencia-deformacao-total` · 11.3.3.2 · p. 78
- **O que criar:**
  - `eps_c_imediata(sigma_c_mpa, Eci_t0_mpa)` (A.2.1); `eps_cc(sigma_c, Eci, phi)` (A.2.2.3).
  - `eps_c_total_simplificada(sigma_c_t0, delta_sigma_c, phi, eps_cs, Ec_t0, Eci, alfa=None)` e `alfa_envelhecimento(caso)` (0,5 ou 0,8; A.2.5).
  - `eps_s_fluencia(sigma_s_t0, Es, chi, fptk=None)` com a regra de 0,5·fptk (A.3.1); `eps_s_impedida(...)` (A.3.2).
  - `retracao_simplificada()` = −15·10⁻⁵ com as condições de validade (11.3.3.1); `deformacao_total_fluencia_simplificada(...)` (11.3.3.2).
- **Depende de:** P6.
- **Testes e aceite:** Casos numéricos montados à mão; a condição UR ≥ 75 % e 10 a 100 cm levanta aviso fora da faixa.
- **Tamanho:** P (8 funções).

### P8 — ELS de deformação: rigidez equivalente, flecha e limites

- **Objetivo:** Ter a flecha de viga e de laje pela norma (Mr genérico, Branson, αf) e compará-la com os limites da Tabela 13.3.
- **Onda 1**, prioridade alta. Módulo: dimensionamento/els_deformacao_nbr6118.py.
- **Itens (10):**
  - `17.3.1-momento-fissuracao` · 17.3.1 · p. 145
  - `17.3.2.1.1-flecha-imediata-rigidez-equivalente` · 17.3.2.1.1 · p. 146
  - `17.3.2.1.2-flecha-diferida-alphaf-xi` · 17.3.2.1.2 · p. 147
  - `19.3.1-els-deformacao` · 19.3.1 · p. 179
  - `13.3-tab13.3-aceitabilidade-sensorial` · 13.3, Tabela 13.3 · p. 97
  - `13.3-tab13.3-efeitos-estruturais-servico` · 13.3, Tabela 13.3 · p. 98
  - `13.3-tab13.3-elementos-nao-estruturais-paredes` · 13.3, Tabela 13.3, notas c-e · p. 98
  - `13.3-tab13.3-forros-pontes-rolantes` · 13.3, Tabela 13.3 · p. 98
  - `13.3-notas-vao-equivalente-balanco` · 13.3, NOTA 1 e NOTA 2 da Tabela 13.3 · p. 99
  - `13.3-nota3-combinacao-deslocamento` · 13.3, NOTA 3, NOTA 5, NOTA 6 · p. 99
- **O que criar:**
  - `els_deformacao_nbr6118.py`: `momento_fissuracao_kncm(Ic_cm4, yt_cm, fck_mpa, forma='retangular'|'T'|'I', resistencia='fctm'|'fctk_inf')` (17.3.1), promovendo a de `lajes_nbr6118`.
  - `rigidez_equivalente(Ecs, Ic, III, Mr, Ma) -> kN·cm²` (17.3.2.1.1); `alpha_f(t_meses, t0_meses, rho_linha)` com t0 ponderado por várias cargas (17.3.2.1.2), promovendo a de `lajes_nbr6118`.
  - `flecha_total(f_imediata_qp, alpha_f)` usando a combinação quase permanente do P4 (13.3 notas 3, 5 e 6).
  - `TABELA_13_3` e `deslocamento_limite(categoria, vao_cm=None, H_cm=None, Hi_cm=None) -> (limite_cm, descricao)`, devolvendo None e o texto na linha de equipamentos sensíveis; `vao_equivalente(elemento, l_cm)` (notas 1 e 2).
  - `verificar_flecha(...) -> ResultadoFlecha`, usado por vigas e por lajes (19.3.1).
- **Depende de:** P4. Opcionalmente, P6 para φ preciso.
- **Testes e aceite:** Todas as linhas da Tabela 13.3 (p. 97-99); Branson nos extremos Ma = Mr (dá EcsIc) e Ma ≫ Mr (tende a EcsIII); ξ(t) contra a Tabela 17.1 (p. 147).
- **Tamanho:** M (12 a 14 funções).

### P9 — Tensões em serviço (estádio II) e fissuração

- **Objetivo:** Expor as tensões de serviço no estádio II para seção genérica e fechar a fissuração (Acri, Tabela 17.2, deformação imposta), que servem a vigas, lajes, protensão e fadiga.
- **Onda 1**, prioridade alta. Módulo: dimensionamento/els_fissuracao_nbr6118.py + rotinas/flexao_composta_obliqua.py.
- **Itens (5):**
  - `23.5.3-alfa-e-relacao-modulos` · 23.5.3 · p. 218
  - `17.3.3.2-area-envolvimento-acri` · 17.3.3.2 · p. 149
  - `17.3.3.3-tabela-17.2-controle-sem-wk` · 17.3.3.3 · p. 150
  - `19.3.2-els-fissuracao` · 19.3.2 · p. 179
  - `17.3.5.2.2-as-min-deformacao-imposta` · 17.3.5.2.2 · p. 152
- **O que criar:**
  - `els_fissuracao_nbr6118.py`: `tensoes_servico(secao, N_kn, Mx_kncm, My_kncm, alpha_e=None, estadio='II') -> ResultadoTensoes` (σc máx, σs por barra, x), sobre o `_esforcos_internos_els` do kernel; `alpha_e_fadiga()` = Es/Ecs ou 10 (23.5.3).
  - `area_envolvimento_acri(barras, secao, cobrimento_cm) -> list[cm²]` (Figura 17.4, 7,5φ).
  - `TABELA_17_2` e `controle_fissuracao_sem_wk(sigma_s_mpa, phi_mm, s_cm, tipo)` (17.3.3.3).
  - `wk_verificacao(...)` que junta σs, Acri e `wk_max_mm` (P1), valendo para laje (19.3.2).
  - `As_min_deformacao_imposta(...)` (17.3.5.2.2).
- **Depende de:** P1 (wk,máx), P4 (combinação frequente).
- **Testes e aceite:** Estádio II de seção retangular contra fórmula fechada (x da equação do 2º grau); seção T contra `viga_servico_nbr6118.I_II_secao_T`; todas as células da Tabela 17.2 (p. 150).
- **Tamanho:** M (9 a 11 funções).

### P10 — Limites geométricos e coeficiente γn

- **Objetivo:** Aplicar os limites geométricos da seção 13.2 e o γn onde a norma pede, com uma fórmula de γn só.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/limites_geometricos_nbr6118.py.
- **Itens (12):**
  - `13.2.2-largura-min-viga` · 13.2.2 · p. 93
  - `13.2.3-dim-min-pilar` · 13.2.3 · p. 93
  - `13.2.3-gama_n` · 13.2.3, Tabela 13.1 · p. 94
  - `13.2.4.1-espessura-min-laje` · 13.2.4.1 · p. 94
  - `13.2.4.2-espessura-min-mesa-nervurada` · 13.2.4.2 · p. 95
  - `13.2.4.2-espessura-min-nervura` · 13.2.4.2 · p. 95
  - `13.2.4.2-classificacao-espacamento-nervuras` · 13.2.4.2 a-c · p. 95
  - `13.2.5.1-furo-viga-largura-dispensa` · 13.2.5.1 · p. 95
  - `13.2.5.2-abertura-laje-dispensa` · 13.2.5.2, Figura 13.1 · p. 96
  - `13.2.6-canalizacoes-embutidas-proibicoes` · 13.2.6 · p. 96
  - `11.7.1-gamma_n-esbeltos-remissao` · 11.7.1 · p. 84
  - `22.2-gamma-n-consolo-gerber` · 22.2 · p. 203
- **O que criar:**
  - `limites_geometricos_nbr6118.py`: `largura_minima_viga_cm(viga_parede=False, excepcional=False)` (13.2.2); `verificar_dimensao_pilar(b_cm, Ac_cm2)` e `gama_n_pilar(b_cm)` (13.2.3, Tabela 13.1); `gama_n_laje_balanco` movida de `lajes_nbr6118.py` para cá, com reexportação. A Tabela 13.2 (13.2.4.1) já está implementada e testada; só muda de casa. A expressão γn = 1,95 − 0,05·h tem a mesma forma da Tabela 13.1 dos pilares (com b), então as duas usam uma função interna só.
  - `espessura_minima_laje_cm(categoria)` (13.2.4.1, a a g, com `peso_veiculo_kn` explícito); `espessura_minima_mesa_nervurada_cm(...)`, `espessura_minima_nervura_cm(...)`, `classificar_laje_nervurada(espacamento_cm, ...)` (13.2.4.2).
  - `dispensa_verificacao_furo_viga(...)` (13.2.5.1); `dispensa_verificacao_abertura_laje(...)` (13.2.5.2); `canalizacao_embutida_permitida(...)` (13.2.6).
  - `gama_n_consolo_gerber()` (22.2) e a aplicação de γn em `pilares_nbr6118` quando b < 19 cm (11.7.1).
- **Depende de:** Nenhum.
- **Testes e aceite:** Tabela 13.1 célula a célula (p. 94); b = 19 dá γn = 1,0 e b = 14 dá 1,25; espessuras a a g de 13.2.4.1; área de 360 cm² exata.
- **Tamanho:** M (12 a 14 funções).

### P11 — Classificação de elementos

- **Objetivo:** Classificar o elemento antes de escolher o método: linear ou de superfície, viga ou viga-parede, pilar ou pilar-parede, placa espessa, análise plástica permitida.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/classificacao_elementos_nbr6118.py.
- **Itens (8):**
  - `14.4.1-classif-elemento-linear` · 14.4.1 · p. 104
  - `14.4.2.1-placa-espessa` · 14.4.2.1 · p. 104
  - `14.4.2.2-viga-parede-classif` · 14.4.2.2 · p. 105
  - `14.4.2.4-pilar-parede-classif` · 14.4.2.4 · p. 105
  - `14.5.4-analise-plastica-restricoes` · 14.5.4 · p. 106
  - `18.3.1-generalidades-esbeltez-viga-x-viga-parede` · 18.3.1 · p. 167
  - `18.4.1-introducao-pilar-x-pilar-parede` · 18.4.1 · p. 173
  - `22.4.1-classificacao-viga-parede` · 22.4.1 · p. 204
- **O que criar:**
  - `classificacao_elementos_nbr6118.py`: `eh_elemento_linear(l_cm, h_max_cm)` (14.4.1); `eh_placa_espessa(h_cm, vao_cm)` (14.4.2.1); `eh_pilar_parede(b_cm, h_cm)` (14.4.2.4 e 18.4.1).
  - `eh_viga_parede(l_cm, h_cm, continua)` com as duas regras: 14.4.2.2 (vão < 3·h) e 18.3.1/22.4.1 (l/h < 2 biapoiada, < 3 contínua). Devolve qual critério governou.
  - `analise_plastica_permitida(segunda_ordem_global, dutilidade_ok)` (14.5.4).
- **Depende de:** Nenhum.
- **Testes e aceite:** Casos-limite exatos: l/h = 2,0 e 3,0; razão 5:1 no pilar; h = vão/3.
- **Tamanho:** P (6 funções).

### P12 — Vigas: armaduras mínima, máxima e de pele; instabilidade lateral

- **Objetivo:** Completar os limites de armadura de viga que faltam (pele, As + A′s ≤ 4 %, ωmín, x/d) e a instabilidade lateral.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/vigas_nbr6118.py (extensão).
- **Itens (8):**
  - `17.1-omega-min` · 17.1 · p. 140
  - `17.2.3-dutilidade-vigas` · 17.2.3 · p. 142
  - `17.3.5.2.3-armadura-pele` · 17.3.5.2.3 · p. 153
  - `17.3.5.2.4-as-max-tracao-compressao-vigas` · 17.3.5.2.4 · p. 153
  - `18.3.5-armadura-pele` · 18.3.5 · p. 172
  - `19.3.3.3-as-max` · 19.3.3.3 · p. 181
  - `17.2.4.1-forcas-concentradas-10pct-h` · 17.2.4.1 · p. 143
  - `15.10-instabilidade-lateral-vigas` · 15.10 · p. 134
- **O que criar:**
  - `omega_min(fck_mpa, fyk_mpa)` (17.1).
  - `armadura_pele_cm2_por_face(bw_cm, h_cm)` e `espacamento_max_pele_cm(d_cm)` (17.3.5.2.3 e 18.3.5); aviso de que `blocos_nbr6118.Asp_pele_face` é outra regra.
  - `verificar_As_max_viga(As, As_linha, Ac)` (17.3.5.2.4), valendo também para laje (19.3.3.3); `vigas_nbr6118` passa a chamar os dois e a verificar x/d contra `xd_limite_dutilidade` (17.2.3).
  - `agrupamento_barras_permitido(dist_cm, h_cm)` (17.2.4.1, 10 % de h).
  - `TABELA_15_1` e `verificar_instabilidade_lateral(b_cm, h_cm, l0_cm, tipo)` (15.10).
- **Depende de:** Nenhum.
- **Testes e aceite:** 4 % exato; pele com h = 60 cm (limite de aplicação); todas as células da Tabela 15.1 (p. 134).
- **Tamanho:** P (7 a 8 funções).

### P13 — Redistribuição de momentos e dutilidade

- **Objetivo:** Verificar redistribuição de momentos e rótula plástica em vigas e lajes.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/redistribuicao_nbr6118.py.
- **Itens (7):**
  - `14.6.4.3-xd-redistribuicao` · 14.6.4.3 · p. 112
  - `14.6.4.3-delta-min` · 14.6.4.3 · p. 112
  - `14.7.3.2-redistribuicao-lajes` · 14.7.3.2 · p. 116
  - `14.6.4.4-rotacao-plastica` · 14.6.4.4 · p. 112
  - `14.6.4.4-dispensa-verificacao-rotacao` · 14.6.4.4 · p. 113
  - `14.7.4-xd-limite-plastico-laje` · 14.7.4 · p. 116
  - `14.7.4-razao-momentos-borda-vao` · 14.7.4 · p. 116
- **O que criar:**
  - `redistribuicao_nbr6118.py`: `xd_limite_redistribuicao(delta, fck_mpa)` e `delta_minimo()` (14.6.4.3, repetido em 14.7.3.2).
  - `rotacao_plastica_admissivel_mrad(xd, fck_mpa, aco, a_d)` com a Figura 14.7 digitalizada e o fator de a/d (14.6.4.4).
  - `dispensa_verificacao_rotacao(xd, fck_mpa)` (14.6.4.4 e 14.7.4); `verificar_razao_momentos_borda_vao(M_borda, M_vao)` (14.7.4).
- **Depende de:** Nenhum (usa `nucleo.xd_limite_dutilidade`).
- **Testes e aceite:** δ = 1 reproduz o limite sem redistribuição; δ = 0,75 no limite; pontos lidos da Figura 14.7 (p. 112) com tolerância declarada. **Conferir na imagem a extensão do radical do fator a/d antes de codificar** (o mapeador registrou baixa confiança).
- **Tamanho:** P (6 a 7 funções; a digitalização da figura é o trabalho maior).

### P14 — Pré e pós-processamento da análise linear

- **Objetivo:** Pós-processar os resultados da análise linear (do P44 ou de programa externo) antes do dimensionamento e dar um lugar único à geometria efetiva. O trecho rígido, a largura colaborante e a rigidez à torção daqui entram no modelo do P44.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/analise_linear_nbr6118.py.
- **Itens (11):**
  - `14.3.3-tensao-max-ciclica` · 14.3.3 · p. 104
  - `14.6.2.1-trecho-rigido` · 14.6.2.1 · p. 108
  - `14.6.2.2-largura-colaborante` · 14.6.2.2 · p. 109
  - `14.6.2.2-largura-efetiva-abertura` · 14.6.2.2 (Figura 14.3) · p. 109
  - `14.6.2.3-misulas-secao-efetiva` · 14.6.2.3 · p. 109
  - `14.6.3-arredondamento-momentos` · 14.6.3 · p. 111
  - `14.6.6.1-vigas-continuas-momento-minimo` · 14.6.6.1 · p. 113
  - `14.6.6.1-coeficientes-engastamento-apoio-extremo` · 14.6.6.1 (Figura 14.8) · p. 114
  - `14.6.6.2-reducao-rigidez-torcao-grelha` · 14.6.6.2 · p. 115
  - `14.6.6.3-dispensa-alternancia-cargas` · 14.6.6.3 · p. 115
  - `14.6.6.4-diafragma-rigido` · 14.6.6.4 · p. 115
- **O que criar:**
  - `analise_linear_nbr6118.py`: `trecho_rigido_cm(h_ortogonal_cm)` (14.6.2.1); `largura_colaborante_cm(bw, b2_esq, b2_dir, a, borda=False, b4=None)` com o caso de borda (14.6.2.2), promovendo `viga_servico_nbr6118.largura_efetiva_mesa` (com reexportação); `largura_efetiva_com_abertura(...)` (Figura 14.3); `secao_efetiva_misula(...)` (14.6.2.3).
  - `vao_efetivo` movida de `lajes_nbr6118`, com reexportação.
  - `arredondar_momento_apoio(M, R1, R2, t_cm)` (14.6.3, Figura 14.6).
  - `momentos_minimos_viga_continua(...)` e `coeficientes_engastamento_extremo(r_inf, r_sup, r_viga)` (14.6.6.1).
  - `FATOR_RIGIDEZ_TORCAO_GRELHA = 0.15` e `rigidez_torcao_reduzida(...)` (14.6.6.2).
  - `dispensa_alternancia_cargas(q, g)` (14.6.6.3); `laje_diafragma_rigido(...)` (14.6.6.4); `admite_carregamento_monotonico(sigma_c_mpa, fck_mpa)` (14.3.3).
- **Depende de:** Nenhum.
- **Testes e aceite:** Exemplos numéricos da Figura 14.6 e 14.8 montados à mão; b1 = 0,5·b2 e a/10 no limite; laje com lados no limite do diafragma.
- **Tamanho:** M (12 a 13 funções).

### P15 — Força cortante completa (vigas e lajes)

- **Objetivo:** Fechar a cortante: os três ramos de Vc (tração, flexão, flexo-compressão com M0), o modo verificação, a redução junto ao apoio e as regras de laje.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/cortante_nbr6118.py (extensão).
- **Itens (14):**
  - `17.4.1.1.2-excecoes-asw-min` · 17.4.1.1.2 · p. 154
  - `17.4.1.1.3-limite-barras-dobradas` · 17.4.1.1.3 · p. 155
  - `17.4.1.2.1-reducao-vsd-apoio` · 17.4.1.2.1 · p. 155
  - `17.4.1.2.2-protensao-tangencial` · 17.4.1.2.2 · p. 155
  - `17.4.1.2.3-altura-variavel` · 17.4.1.2.3 · p. 155
  - `17.4.2.1-condicao-dupla` · 17.4.2.1 · p. 156
  - `17.4.2.2-Vc-Vsw-modeloI` · 17.4.2.2 b) · p. 157
  - `17.4-M0-momento-descompressao` · 17.4.2.2 b) [M0] · p. 157
  - `17.4.2.2-Fsd-cor-alternativa` · 17.4.2.2 c) [alternativa] · p. 158
  - `17.4.2.3-Vc-Vsw-modeloII` · 17.4.2.3 b) · p. 159
  - `17.6-fissuracao-inclinada-alma` · 17.6 · p. 164
  - `19.4.1-vrd1` · 19.4.1 · p. 181
  - `19.4.1-decalagem-al-15d` · 19.4.1 · p. 182
  - `19.4.2-fywd-max-laje` · 19.4.2 · p. 182
- **O que criar:**
  - `cortante_nbr6118`: `M0_kncm(Pd_kn, ep_cm, Nsd_kn, W1_cm3, Ac_cm2)` com γf = 1,0 e γp = 0,9 locais (17.4.2.2 b).
  - `modelo_calculo_I/II(..., Nsd_kn=0, M0_kncm=None, MSd_max_kncm=None)`: Vc = 0 com linha neutra fora da seção, Vc0 (ou Vc1) em flexão simples, e Vc0·(1 + M0/MSd,máx) ≤ 2·Vc0 em flexo-compressão.
  - `verificar_cortante(Asw_cm2_por_m, ...) -> ResultadoCortante`, com VRd2 e VRd3 no modo verificação (17.4.2.1).
  - `VSd_reduzido_apoio(...)` (17.4.1.2.1); `verificar_protensao_tangencial(...)` (17.4.1.2.2); `VSd_red_altura_variavel(...)` (17.4.1.2.3).
  - `regime_asw_minima(bw, d, ...)` (17.4.1.1.2); `verificar_limite_barras_dobradas(Vsw_dobradas, Vsw_total)` (17.4.1.1.3); `FSd_cor(...)` (17.4.2.2 c, alternativa); `S_MAX_FISSURACAO_ALMA_CM = 15` (17.6).
  - Lajes: `fywd_max_laje_mpa(h_cm)` interpolando de 250 a 435 MPa (19.4.2); `AL_LAJE = 1.5·d` (19.4.1); `lajes_nbr6118.cortante_resistente_laje` delega a `laje_sem_armadura` (decisão 6).
- **Depende de:** P4 (γ), P30 é opcional (Pd e ep chegam como número).
- **Testes e aceite:** Os três ramos de Vc nas fronteiras; Vc limitado a 2·Vc0; fywd em h = 15 e 35 cm e no meio; laje com σcp de tração dá VRd1 menor que antes.
- **Tamanho:** G (16 a 18 funções).

### P16 — Torção completa e combinação com flexão e cortante

- **Objetivo:** Completar a torção (seção composta, vazada real, modo verificação) e juntar flexão, cortante e torção como a viga real pede.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/torcao_nbr6118.py (extensão) + combinacao_esforcos_nbr6118.py.
- **Itens (9):**
  - `17.5.1.2-dispensa-torcao-compatibilidade` · 17.5.1.2 · p. 160
  - `17.5.1.2-limite-Vsd-adaptacao-plastica` · 17.5.1.2 · p. 160
  - `17.5.1.3-condicao-tripla-torcao` · 17.5.1.3 · p. 160
  - `17.5.1.4.2-secao-composta-retangulos` · 17.5.1.4.2 · p. 161
  - `17.5.1.4.3-secoes-vazadas-reais` · 17.5.1.4.3 · p. 161
  - `17.5.1.6-arranjo-armadura-torcao` · 17.5.1.6 · p. 162
  - `17.7.1.2-soma-armadura-longitudinal` · 17.7.1.2 · p. 164
  - `17.7.1.4-tensao-principal-banzo-comprimido` · 17.7.1.4 · p. 164
  - `17.7.2.3-soma-armaduras-transversais-VT` · 17.7.2.3 · p. 165
- **O que criar:**
  - `torcao_nbr6118`: `repartir_torcao_secao_composta(retangulos, TSd)` por a³·b (17.5.1.4.2); `espessura_parede_vazada_real(...)` (17.5.1.4.3); `verificar_torcao(Asw, Asl, ...)` com TRd2, TRd3 e TRd4 (17.5.1.3).
  - `torcao_compatibilidade_dispensavel(...)` e `verificar_trecho_curto(l_cm, h_cm, VSd, VRd2)` (17.5.1.2); `distribuir_armadura_longitudinal_torcao(...)` (17.5.1.6).
  - `combinacao_esforcos_nbr6118.py`: `As_longitudinal_total(As_flexao_por_face, Asl_torcao_por_face)` (17.7.1.2); `Asw_total(Asw_V, Asw_T)` (17.7.2.3); `tensao_principal_banzo_comprimido(...)` com τTd = Td/(2·Ae·he) (17.7.1.4).
- **Depende de:** P15 (modo verificação e VRd2).
- **Testes e aceite:** Seção T decomposta à mão; teste do caso A/u < 2c1 que a auditoria deixou sem cobertura; soma de Asw contra os dois módulos separados.
- **Tamanho:** M (10 a 11 funções).

### P17 — Lajes: flexão, armaduras mínimas e momentos

- **Objetivo:** Completar a flexão de lajes: Tabela 19.1 inteira, reações por charneiras em qualquer vinculação, compatibilização com as duas regras e a repartição em faixas de laje lisa.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/lajes_nbr6118.py (extensão).
- **Itens (7):**
  - `19.2-principios-elu` · 19.2 · p. 179
  - `19.3.3.2-tab19.1-as-min` · 19.3.3.2 / Tabela 19.1 · p. 180
  - `19.3.3.2-as-min-laje-lisa-nao-aderente` · 19.3.3.2 · p. 180
  - `19.3.3.2-extensao-armadura-negativa-borda` · 19.3.3.2 · p. 179
  - `14.7.6.1-reacoes-apoio-charneiras` · 14.7.6.1 · p. 117
  - `14.7.6.2-compatibilizacao-momentos` · 14.7.6.2 · p. 117
  - `14.7.8-faixas-distribuicao-momento` · 14.7.8 · p. 118
- **O que criar:**
  - `lajes_nbr6118`: `TABELA_19_1` e `rho_min_laje(tipo_armadura, situacao_ativa)` (5 × 3 células); `As_min_laje_lisa_nao_aderente(h, l)` (19.3.3.2); `extensao_negativa_borda_cm(l_menor)`.
  - `reacoes_charneiras(lx, ly, vinculos)` com ângulos de 45°, 60° e 90° (14.7.6.1), cobrindo o que a tabela de Bares não cobre.
  - `compat_momento_negativo(..., regra='maior'|'media_08')` (14.7.6.2).
  - `repartir_momentos_faixas(M_portico, tipo)` com os percentuais da Figura 14.9 (14.7.8).
  - Aviso de desvio de 15° entre armadura e tensões principais (19.2).
- **Depende de:** Nenhum.
- **Testes e aceite:** Todas as células da Tabela 19.1 (p. 180); reações por charneiras contra Bares nas 5 vinculações já tabeladas; soma dos percentuais de faixa = 100 %.
- **Tamanho:** M (9 a 10 funções).

### P18 — Detalhamento de lajes

- **Objetivo:** Detalhamento de lajes de concreto armado (20.1, 20.3.1, 20.5, 20.6).
- **Onda 2**, prioridade alta. Módulo: dimensionamento/detalhamento_lajes_nbr6118.py.
- **Itens (11):**
  - `20.1-diametro-max-barra` · 20.1 · p. 192
  - `20.1-espacamento-max-principal` · 20.1 · p. 192
  - `20.1-sem-escalonamento-armadura-positiva` · 20.1 · p. 192
  - `20.1-armadura-secundaria-positiva` · 20.1 · p. 192
  - `20.1-estribo-nervurada-espacamento` · 20.1 · p. 192
  - `20.3.1-fig20.2-distribuicao-faixas` · 20.3.1 · p. 194
  - `20.3.1-barras-continuas-apoio` · 20.3.1 · p. 194
  - `20.3.1-capitel-penetracao-minima` · 20.3.1 · p. 194
  - `20.5.1-ancoragem-tela-soldada-apoio` · 20.5.1 · p. 196
  - `20.5.2-emenda-tela-tabela-malhas-fios` · 20.5.2 · p. 196
  - `20.6-armadura-inferior-laje-balanco` · 20.6 · p. 197
- **O que criar:**
  - `detalhamento_lajes_nbr6118.py`: `phi_max_laje_mm(h_cm)`; `espacamento_max_principal_cm(h_cm, phi_mm)`; `As_secundaria_min(As_principal)` e `espacamento_max_secundaria_cm()`; `prolongamento_positivo_apoio(...)`; `espacamento_max_estribo_nervura_cm(...)` (20.1).
  - `distribuicao_faixas_laje_lisa(...)` pela Figura 20.2 (ler na imagem, p. 194); `barras_continuas_apoio_min(...)`; `penetracao_capitel_cm(...)` (20.3.1).
  - `ancoragem_tela_apoio_cm(...)` e `emenda_tela_malhas(...)` (20.5).
  - `As_inferior_balanco(g_kn_m2, ...)` (20.6).
- **Depende de:** P21 (ancoragem), P19 (colapso progressivo, para a verificação conjunta de 20.3.1).
- **Testes e aceite:** Limites literais de 20.1; percentuais da Figura 20.2 lidos na imagem; soma das frações = 100 %.
- **Tamanho:** M (12 funções).

### P19 — Punção: solicitação e resistência

- **Objetivo:** Criar a punção de laje: tensão solicitante em pilar interno, de borda e de canto, e as três resistências (C, C′ com e sem armadura).
- **Onda 2**, prioridade alta. Módulo: dimensionamento/puncao_nbr6118.py.
- **Itens (12):**
  - `19.5.1-modelo-calculo-puncao` · 19.5.1 · p. 182
  - `19.5.2.1-tsd-pilar-interno-simetrico` · 19.5.2.1 · p. 183
  - `19.5.2.2-tsd-pilar-interno-momento` · 19.5.2.2 · p. 184
  - `19.5.2.2-tabela19.2-K` · 19.5.2.2 / Tabela 19.2 · p. 184
  - `19.5.2.2-wp-retangular` · 19.5.2.2 · p. 184
  - `19.5.2.2-wp-circular` · 19.5.2.2 · p. 184
  - `19.5.2.3-pilar-borda-sem-momento-paralelo` · 19.5.2.3 a) · p. 185
  - `19.5.2.3-pilar-borda-com-momento-paralelo` · 19.5.2.3 b) · p. 185
  - `19.5.2.4-pilar-canto` · 19.5.2.4 · p. 186
  - `19.5.3.1-trd2-compressao-diagonal` · 19.5.3.1 · p. 188
  - `19.5.3.2-trd1-sem-armadura` · 19.5.3.2 · p. 188
  - `19.5.3.3-trd3-com-armadura` · 19.5.3.3 · p. 189
- **O que criar:**
  - `puncao_nbr6118.py`: `perimetro_critico(c1, c2, d, tipo='interno'|'borda'|'canto', contorno='C'|'Cl')` e `u_estrela(...)`.
  - `TABELA_19_2_K` e `K(c1_c2)`. A Tabela 19.2 só dá C1/C2 = 0,5, 1,0, 2,0 e 3,0 e não diz como tratar os valores intermediários: a função interpola linearmente (prática corrente) e diz isso na docstring e na memória, com a opção `interpolar=False`, que usa o K do degrau superior (a favor da segurança); fora de 0,5 a 3,0 levanta `FaixaNormativaError`; `Wp_retangular(c1, c2, d)`, `Wp_circular(D, d)`.
  - `tau_Sd(FSd, u, d, MSd=0, K=None, Wp=None, tipo=...)` com os ramos de 19.5.2.1 a 19.5.2.4.
  - `tau_Rd2(fck)` (reusa `nucleo.alpha_v2`), `tau_Rd1(fck, rho, d, sigma_cp)` e `tau_Rd3(..., Asw, sr, fywd)` (19.5.3), com comentário sobre o 0,13 × 0,10 que não se reduzem um ao outro.
  - `verificar_puncao(...) -> ResultadoPuncao` (C, C′ e C″, status de cada uma e memória).
- **Depende de:** P15 (`fywd_max_laje_mpa`).
- **Testes e aceite:** Casos de pilar interno, borda e canto montados à mão; Tabela 19.2 em todas as células (p. 184); fronteira C1/C2 = 0,5 e 3,0; ke ≤ 2.
- **Tamanho:** G (14 a 16 funções).

### P20 — Punção: casos especiais, robustez e detalhamento

- **Objetivo:** Completar a punção: forma genérica, capitel, reentrância e abertura, disposição até C″, armadura obrigatória, colapso progressivo, laje protendida e sapata flexível.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/puncao_nbr6118.py.
- **Itens (12):**
  - `19.5.2.2-wp-integral-generico` · 19.5.2.2 · p. 184
  - `19.5.2.5-capitel` · 19.5.2.5 · p. 187
  - `19.5.2.6-contorno-reentrancia` · 19.5.2.6 · p. 187
  - `19.5.2.6-contorno-abertura` · 19.5.2.6 · p. 187
  - `19.5.3.4-superficie-c2linha` · 19.5.3.4 · p. 190
  - `19.5.3.5-armadura-puncao-obrigatoria` · 19.5.3.5 · p. 191
  - `19.5.4-colapso-progressivo` · 19.5.4 · p. 191
  - `19.5.5-puncao-protendido` · 19.5.5 · p. 191
  - `20.4-diametro-max-estribo-puncao` · 20.4 · p. 196
  - `20.4-contato-mecanico-canto-estribo` · 20.4 · p. 196
  - `21.3.4c-puncao-abertura-proxima-pilar` · 21.3.4 · p. 201
  - `22.6.2.3-sapata-flexivel-puncao` · 22.6.2.3 · p. 212
- **O que criar:**
  - `Wp_generico(poligono, d)` por integração (19.5.2.2); `contornos_capitel(...)` (19.5.2.5); `perimetro_com_reentrancia(...)` e `perimetro_com_abertura(...)` (19.5.2.6, 8d).
  - `disposicao_armadura_puncao(...)` até C″ (19.5.3.4); `armadura_puncao_obrigatoria(...)` (19.5.3.5); `As_colapso_progressivo(FSd, fyd)` (19.5.4); `tau_Sd_efetivo_protendido(...)` (19.5.5).
  - `phi_max_estribo_puncao_mm(h)` e `verificar_contato_canto(...)` (20.4); `puncao_abertura_proxima_pilar(...)` (21.3.4 c).
  - `sapatas_nbr6118`: verificação de punção de sapata flexível, com a redução pela reação do solo, chamando este módulo (22.6.2.3).
- **Depende de:** P19.
- **Testes e aceite:** Wp genérico reproduz os fechados de P19 para retângulo e círculo; abertura a 8d exatos; sapata flexível contra caso montado à mão.
- **Tamanho:** G (13 a 14 funções).

### P21 — Ancoragem passiva, ganchos e estribos

- **Objetivo:** Completar a ancoragem passiva: classificação de aderência, ganchos (comprimento, pino, validação), armadura transversal na ancoragem e estribos.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/ancoragem_nbr6118.py (extensão).
- **Itens (11):**
  - `9.3.1-posicao-barra-classificacao` · 9.3.1 · p. 53
  - `9.3.2.3-fator-escorregamento` · 9.3.2.3 · p. 54
  - `9.4.1.1-tipos-ancoragem-aderencia` · 9.4.1.1 · p. 55
  - `9.4.2.1-condicoes-ancoragem-reta` · 9.4.2.1 · p. 55
  - `9.4.2.2-barras-transversais-soldadas-ancoragem` · 9.4.2.2 · p. 55
  - `9.4.2.3-ganchos-comprimento-tipo` · 9.4.2.3 · p. 56
  - `9.4.2.3-gancho-solda-transversal` · 9.4.2.3 · p. 56
  - `9.4.2.6.1-armadura-transversal-ancoragem-phi-menor-32` · 9.4.2.6.1 · p. 57
  - `9.4.2.6.2-armadura-transversal-ancoragem-phi-maior-igual-32` · 9.4.2.6.2 · p. 58
  - `9.4.6.1-ganchos-estribos-tipos` · 9.4.6.1 · p. 60
  - `9.4.6.2-estribo-barra-transversal-soldada` · 9.4.6.2 · p. 60
- **O que criar:**
  - `ancoragem_nbr6118`: `situacao_aderencia(inclinacao_graus, h_cm, y_cm)` (9.3.1); `FATOR_ESCORREGAMENTO = 1.75` e `fbd_escorregamento(...)` (9.3.2.3).
  - `dispensa_confinamento(cobrimento, espacamento, phi)` (9.4.1.1); `validar_uso_gancho(tipo_barra, solicitacao, phi)` (9.4.2.1); `verificar_barra_transversal_soldada(...)` (9.4.2.2).
  - `diametro_pino_gancho(phi, aco)` trazida do legado, e `comprimento_gancho(phi, tipo)` com ponta reta de 2φ, 4φ ou 8φ (9.4.2.3); `pino_com_solda_transversal(...)`.
  - `Ast_ancoragem(...)` para φ < 32 e φ ≥ 32 mm (9.4.2.6).
  - `TABELA_9_2` e `diametro_pino_estribo(phi_t, aco)`, trazidos do legado (`sec9.diam_pino_dobramento_transversal`, que já levanta erro na célula "–"), como a Tabela 9.1; `ponta_reta_estribo_cm(phi_t, tipo)` com mínimos de 5 e 7 cm; `ancoragem_estribo_barra_soldada(...)` (9.4.6).
- **Depende de:** Nenhum.
- **Testes e aceite:** Tabelas 9.1 e 9.2 inteiras (p. 56 e 60); φ = 20 mm na fronteira; CA-60 com φ ≥ 20 levanta erro. Conferir `alpha_0t` em 30 e 40 % (risco 6).
- **Tamanho:** M (13 a 14 funções).

### P22 — Detalhamento de vigas: armadura longitudinal

- **Objetivo:** Detalhar a armadura longitudinal de viga: espaçamentos, cobertura do diagrama decalado, corte de barras e ancoragem nos apoios.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/detalhamento_vigas_nbr6118.py.
- **Itens (9):**
  - `18.2.2-diametro-curvatura-barra-longitudinal` · 18.2.2 · p. 166
  - `18.3.2.2-espacamento-longitudinal-vigas` · 18.3.2.2 · p. 168
  - `18.3.2.3.1-cobertura-diagrama-decalagem` · 18.3.2.3.1 · p. 168
  - `18.3.2.3.1-caso-ponto-A-na-face-apoio` · 18.3.2.3.1 · p. 169
  - `18.3.2.3.2-barras-nas-mesas` · 18.3.2.3.2 · p. 169
  - `18.3.2.4-b-forca-tracao-apoio-extremo` · 18.3.2.4-b · p. 169
  - `18.3.2.4-c-fracao-as-vao` · 18.3.2.4-c · p. 170
  - `18.3.2.4.1-ancoragem-apoio` · 18.3.2.4.1 · p. 170
  - `18.6.1.1-FSd-apoio-intermediario` · 18.6.1.1 · p. 175
- **O que criar:**
  - `detalhamento_vigas_nbr6118.py`: `ah_min_cm(...)` e `av_min_cm(...)` (18.3.2.2).
  - `diametro_curvatura_barra_dobrada(phi, aco, sigma_s_fyd=1.0, camadas=1)` (18.2.2).
  - `cobertura_diagrama(x, Md_x, z, al, barras) -> pontos de corte` com a regra do ponto A e B (18.3.2.3.1, Figura 18.3); o caso de ponto A na face do apoio; `comprimento_adicional_mesa(...)` (18.3.2.3.2).
  - `FSd_apoio_extremo(VSd, al, d, NSd)` (18.3.2.4 b), a mesma fórmula servindo ao apoio intermediário de 18.6.1.1; `fracao_As_vao_no_apoio(M_apoio, M_vao)` com 1/3 no ponto exato 0,5 (18.3.2.4 c); `ancoragem_no_apoio_cm(...)` = máx(lb,nec, r + 5,5φ, 60 mm) com as dispensas (18.3.2.4.1).
- **Depende de:** P21 (raio de gancho), P15 (aℓ com Vc), P24 (`phi_n_feixe`).
- **Testes e aceite:** Viga biapoiada com carga uniforme: pontos de corte à mão; |Mapoio| = 0,5·Mvão dá 1/3.
- **Tamanho:** G (10 a 12 funções; `cobertura_diagrama` é algoritmo).

### P23 — Detalhamento de vigas: estribos, torção e suspensão

- **Objetivo:** Detalhar estribos de viga, torção, suspensão e ligação mesa-alma.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/detalhamento_vigas_nbr6118.py.
- **Itens (15):**
  - `18.2.4-protecao-flambagem-barras` · 18.2.4 · p. 167
  - `18.3.3.2-diametro-min-max-estribo` · 18.3.3.2 · p. 170
  - `18.3.3.2-barras-amarracao-canto-estribo` · 18.3.3.2 · p. 171
  - `18.3.3.2-espacamento-longitudinal-max-estribos` · 18.3.3.2 · p. 171
  - `18.3.3.2-espacamento-transversal-max-ramos` · 18.3.3.2 · p. 171
  - `18.3.3.2-emenda-traspasse-estribo` · 18.3.3.2 · p. 171
  - `18.3.3.3.2-espacamento-barras-dobradas` · 18.3.3.3.2 · p. 171
  - `18.3.4-estribo-torcao-135-graus-fechado` · 18.3.4 · p. 171
  - `18.3.4-espacamento-longitudinal-barras-torcao` · 18.3.4 · p. 172
  - `18.3.4-relacao-deltaAsl-deltau` · 18.3.4 · p. 172
  - `18.3.4-barra-cada-vertice-poligonal` · 18.3.4 · p. 172
  - `18.3.6-armadura-suspensao-percentuais` · 18.3.6 · p. 172
  - `18.3.6-fator-reducao-vigas-face-superior-coincidente` · 18.3.6 · p. 172
  - `18.3.6-definicao-viga-pendurada` · 18.3.6 · p. 172
  - `18.3.7-armadura-ligacao-mesa-alma` · 18.3.7 · p. 173
- **O que criar:**
  - `phi_estribo_limites_mm(bw_cm, tipo)` e `phi_min_barra_canto(...)`; `s_max_estribo_cm(Vd, VRd2, d)` e `st_max_cm(Vd, VRd2, d)` com os degraus de 0,67 e 0,20; `emenda_estribo_permitida(tipo)`; `s_max_barras_dobradas_cm(alfa)` (18.3.3).
  - `protecao_flambagem(barras, estribo)` com 20·φt (18.2.4).
  - Torção: `verificar_estribo_torcao(fechado, angulo_gancho)`, `S_MAX_LONGITUDINAL_TORCAO_CM = 35`, `verificar_barra_por_vertice(...)`, `verificar_delta_Asl_delta_u(...)` (18.3.4).
  - Suspensão: `viga_pendurada(...)`, `As_suspensao_viga(Fd, ...)` com 75/25 % e extensão h/2, `fator_reducao_suspensao(...)` (18.3.6), sem reusar o nome da de blocos.
  - `As_ligacao_mesa_alma_min()` = 1,5 cm²/m (18.3.7).
- **Depende de:** P15 (VRd2), P21 (ganchos 135°).
- **Testes e aceite:** Os dois lados de cada degrau de Vd/VRd2; 20·φt exato; suspensão contra caso à mão.
- **Tamanho:** G (15 a 16 funções).

### P24 — Detalhamento de pilares

- **Objetivo:** Detalhar pilares: bitolas, número de barras, espaçamentos e estribos.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/detalhamento_pilares_nbr6118.py.
- **Itens (8):**
  - `18.4.2.1-diametro-min-max-barra-longitudinal-pilar` · 18.4.2.1 · p. 173
  - `18.4.2.2-distribuicao-transversal-vertices-pilar` · 18.4.2.2 · p. 173
  - `18.4.2.2-espacamento-min-barras-pilar` · 18.4.2.2 · p. 173
  - `18.4.2.2-espacamento-max-eixos-pilar` · 18.4.2.2 · p. 174
  - `18.4.3-diametro-min-estribo-pilar` · 18.4.3 · p. 174
  - `18.4.3-espacamento-max-estribo-pilar-basico` · 18.4.3 · p. 174
  - `18.4.3-espacamento-max-estribo-pilar-phi-reduzido` · 18.4.3 · p. 174
  - `18.4.3-nota-dutilidade-concreto-alta-resistencia` · 18.4.3 (NOTA) · p. 174
- **O que criar:**
  - No núcleo: `phi_n_feixe(phi_mm, n) -> mm` = φ·√n, usado também por P22 e P27. `detalhamento_pilares_nbr6118.py`: `phi_longitudinal_limites_mm(b_min_cm)` (18.4.2.1); `n_min_barras(forma)`; `espacamento_min_livre_cm(phi, phi_n, dmax)`; `espacamento_max_eixos_cm(b_min)` (18.4.2.2).
  - `phi_min_estribo_pilar_mm(phi_long)`; `s_max_estribo_pilar_cm(b_min, phi_long, aco, phi_t=None, fyk=None, fck=None)` com os três critérios, a fórmula com fyk quando φt < φ/4 e a redução recomendada de 50 % para C55 a C90 como opção (18.4.3).
  - `verificar_detalhamento_pilar(...) -> Resultado` que junta tudo.
- **Depende de:** P11.
- **Testes e aceite:** 400 mm e 200 mm exatos; 12φ para CA-50; fórmula de fyk com números à mão.
- **Tamanho:** M (9 funções).

### P25 — Pilares: 2ª ordem local pelo pilar-padrão

- **Objetivo:** Fechar o pilar isolado: ℓe, λ genérico, limite de 200, γn1 ligado, fluência, as duas direções juntas e a envoltória mínima com 2ª ordem.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/pilares_nbr6118.py (extensão) + rotinas/verificacao_pilar.py.
- **Itens (9):**
  - `15.3.1-kappa-sec-adimensional` · 15.3.1 · p. 122
  - `15.3.2-envoltoria-minima-2a-ordem` · 15.3.2 · p. 122
  - `15.6-comprimento-equivalente-nos-fixos` · 15.6 · p. 125
  - `15.8.1-limite-esbeltez-200` · 15.8.1 · p. 127
  - `15.8.1-n1-majoracao-lambda140` · 15.8.1 · p. 127
  - `15.8.2-lambda-esbeltez-basico` · 15.8.2 · p. 127
  - `15.8.3.3.5-pilar-padrao-flexao-obliqua` · 15.8.3.3.5 · p. 131
  - `15.8.4-fluencia-ecc` · 15.8.4 · p. 131
  - `15.7.4-efeitos-locais-em-nos-moveis` · 15.7.4 · p. 127
- **O que criar:**
  - `pilares_nbr6118`: `comprimento_equivalente_cm(l0, h, l)` (15.6); `esbeltez(le_cm, I_cm4, A_cm2)` genérico (15.8.2); `verificar_esbeltez_limite(lam, Nd, fcd, Ac)` (15.8.1).
  - γn1 aplicado ao Md,tot quando 140 < λ ≤ 200 (15.8.1); hoje `n1_majoracao` não é chamada.
  - `ecc_fluencia_cm(Msg, Nsg, ea, phi, Eci, Ic, le)` com Ne = 10·Eci·Ic/le² (15.8.4), usando a Tabela 8.1 do núcleo ou o φ do P6.
  - `kappa_sec(EI_sec, Ac, h, fcd)` (15.3.1).
  - `pilar_padrao_obliquo(...)`: 15.8.3.3.2 ou 15.8.3.3.3 nas duas direções e verificação da envoltória em 3 seções com o kernel (15.8.3.3.5).
  - `verificacao_pilar.verificar_envoltoria_minima` já monta e verifica a elipse da Figura 15.2, mas recebe Md,tot,mín,xx e Md,tot,mín,yy prontos. Falta calculá-los pelo 15.8.3 em cada direção, a partir de M1d,mín, e encadear (15.3.2); `efeitos_locais_nos_moveis(MA, MB, ...)` (15.7.4).
- **Depende de:** P10 (γn de pilar), P4 (γf3), P6 opcional.
- **Testes e aceite:** λ = 140 e 200 nas fronteiras; ecc contra caso à mão; pilar oblíquo contra um caso do TQS (rodar `compare_3way_pilar.py`).
- **Tamanho:** G (10 a 12 funções, a oblíqua é a maior).

### P26 — Estabilidade global e imperfeições globais

- **Objetivo:** Estabilidade global a partir do resultado da análise (do P46 ou de programa externo): α, γz, classificação, rigidezes aproximadas e desaprumo contra vento.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/estabilidade_global_nbr6118.py.
- **Itens (10):**
  - `15.4.2-classificacao-nos-fixos-moveis` · 15.4.2 · p. 123
  - `15.5.1-majoracao-ecs-analise-global` · 15.5.1 · p. 124
  - `15.5.2-parametro-instabilidade-alfa` · 15.5.2 · p. 124
  - `15.5.2-alfa1-limite` · 15.5.2 · p. 124
  - `15.5.2-rigidez-pilar-equivalente` · 15.5.2 · p. 125
  - `15.5.3-coeficiente-gama-z` · 15.5.3 · p. 125
  - `15.7.2-processo-aproximado-095-gamaz` · 15.7.2 · p. 126
  - `15.7.3-rigidez-aproximada-analise-global` · 15.7.3 · p. 126
  - `11.3.3.4.1-desaprumo-global` · 11.3.3.4.1 · p. 79
  - `11.3.3.4.1-combinacao-vento-desaprumo` · 11.3.3.4.1 · p. 79
- **O que criar:**
  - `estabilidade_global_nbr6118.py`: `rigidez_pilar_equivalente(Htot, F, delta_topo)` (15.5.2); `parametro_alfa(Htot, Nk, EcsIc)`; `alfa1(n_andares, contraventamento)`.
  - `gama_z(M1tot_d, delta_Mtot_d)` (15.5.3); `classificar_nos(alfa=None, gama_z=None)` (15.4.2).
  - `FATOR_ECS_ESTABILIDADE = 1.1` (15.5.1); `rigidezes_aproximadas(elemento, As_iguais=...)` (15.7.3); `majoracao_horizontal(gama_z)` = 0,95·γz com o limite de 1,3 (15.7.2).
  - `desaprumo_global(H_m, n_pilares)` com θ1 e os limites de 1/300 e 1/200 (11.3.3.4.1); `combinar_vento_desaprumo(M_vento, M_desaprumo)` com os casos a, b e c.
- **Depende de:** P4.
- **Testes e aceite:** γz = 1,1 na fronteira; α1 nos dois tipos de contraventamento; os três casos de vento contra desaprumo na fronteira de 30 %. A docstring diz de onde cada entrada pode vir: do modelo da biblioteca (P46) ou do TQS.
- **Tamanho:** M (10 funções).

### P27 — Emendas, feixes, telas e dispositivos mecânicos

- **Objetivo:** Tudo o que é emenda e barra composta: feixes, telas, Tabela 9.3, armadura transversal nas emendas, luvas, solda e dispositivos mecânicos.
- **Onda 3**, prioridade média. Módulo: dimensionamento/emendas_nbr6118.py.
- **Itens (15):**
  - `9.4.3-feixe-diametro-equivalente` · 9.4.3 · p. 58
  - `9.4.3-feixe-regras-ancoragem` · 9.4.3 · p. 58
  - `9.4.4-tela-soldada-ancoragem` · 9.4.4 · p. 58
  - `9.4.7-dispositivos-mecanicos-ancoragem` · 9.4.7 · p. 61
  - `9.4.7.1-barra-transversal-unica` · 9.4.7.1 · p. 61
  - `9.5.2-traspasse-limite-32mm-feixe-45mm` · 9.5.2 · p. 62
  - `9.5.2.1-tab9.3-proporcao-maxima-emendas` · 9.5.2.1 (Tabela 9.3) · p. 63
  - `9.5.2.1-mesma-secao-transversal` · 9.5.2.1 · p. 62
  - `9.5.2.2.2-l0t-distancia-maior-4phi` · 9.5.2.2.2 · p. 63
  - `9.5.2.4.1-armadura-transversal-emendas-tracionadas` · 9.5.2.4.1 · p. 64
  - `9.5.2.4.2-armadura-transversal-emendas-comprimidas` · 9.5.2.4.2 · p. 64
  - `9.5.2.4.3-armadura-transversal-emendas-secundarias` · 9.5.2.4.3 · p. 64
  - `9.5.2.5-emenda-traspasse-feixe` · 9.5.2.5 · p. 64
  - `9.5.3-emendas-luvas` · 9.5.3 · p. 65
  - `9.5.4-emendas-solda` · 9.5.4 · p. 65
- **O que criar:**
  - `emendas_nbr6118.py`: `ancoragem_feixe(...)` por faixa de φn (9.4.3); `n_fios_transversais_tela(As_calc, As_ef)` (9.4.4).
  - `TABELA_9_3` e `verificar_proporcao_emendas(pct, tipo, carregamento)`; `mesma_secao(dist, l0t)` (9.5.2.1); `l0t_com_distancia_livre(...)` (9.5.2.2.2); limite de 45 mm para feixe (9.5.2).
  - `Ast_emenda(...)` tracionada, comprimida e secundária (9.5.2.4); `escalonamento_emenda_feixe(...)` (9.5.2.5).
  - `verificar_luva(F_ensaio, fyk, As)` (9.5.3); `verificar_emenda_solda(tipo, phi, ...)` (9.5.4); `verificar_dispositivo_mecanico(...)` e `barra_transversal_unica(...)` (9.4.7).
  - `transpasse_tracionado_cm` e `transpasse_comprimido_cm` passam a aceitar `diametros_diferentes` e `distancia_livre_cm`.
- **Depende de:** P21, P24 (`phi_n_feixe`).
- **Testes e aceite:** Tabela 9.3 inteira (p. 63); φn = 25 mm na fronteira; 45 mm exato.
- **Tamanho:** G (15 a 16 funções).

### P28 — Kernel de flexão: domínios, momento-curvatura e método geral

- **Objetivo:** Fazer o kernel crescer onde o pilar esbelto precisa: rótulo de domínio, diagrama M-N-1/r e método geral de uma barra, em Python.
- **Onda 3**, prioridade média. Módulo: dimensionamento/rotinas/momento_curvatura.py + flexao_composta_obliqua.py + verificacao_pilar.py.
- **Itens (3):**
  - `17.2.2g-classificacao-dominio` · 17.2.2 g) · p. 142
  - `15.8.3.3.4-metodo-diagramas-mn1r` · 15.8.3.3.4 · p. 130
  - `15.8.3.2-metodo-geral` · 15.8.3.2 · p. 129
- **O que criar:**
  - `flexao_composta_obliqua`: `dominio_deformacao(eps_topo, eps_base, fck) -> str` (reta a, 1, 2, 3, 4, 4a, 5, reta b; Figura 17.1).
  - `rotinas/momento_curvatura.py`: `diagrama_M_N_curvatura(secao, concreto, aco, Nd, n_pontos)` sobre `_esforcos_internos_els`, com o pico de 1,10·fcd de 15.3.1.
  - `pilar_padrao_MN1r(...)` (15.8.3.3.4, λ ≤ 140).
  - `metodo_geral_pilar(secao, le, Nd, M1_topo, M1_base, n_segmentos=20)`: iteração da linha elástica com a curvatura real em cada seção (15.8.3.2).
  - O C++ não muda; o dispatcher manda estes casos ao Python.
- **Depende de:** P25, P6 (fluência no diagrama, 15.8.3.3.4).
- **Testes e aceite:** Método geral converge para o pilar-padrão quando λ é pequeno; M-N-1/r cruza `ei_secante` no ponto B; domínios nas fronteiras x = 0, x23, x34, h.
- **Tamanho:** G (5 funções, mas duas iterativas).

### P29 — Pilar-parede

- **Objetivo:** Pilar-parede: esbeltez de lâmina, ℓe pelos 4 casos da Figura 15.4, decomposição em faixas e armadura transversal mínima.
- **Onda 3**, prioridade média. Módulo: dimensionamento/pilares_parede_nbr6118.py.
- **Itens (4):**
  - `15.9.2-esbeltez-lamina-pilar-parede` · 15.9.2 · p. 132
  - `15.9.2-comprimento-equivalente-lamina` · 15.9.2 · p. 132
  - `15.9.3-faixas-verticais-pilar-parede` · 15.9.3 · p. 133
  - `18.5-armadura-transversal-pilar-parede-25pct` · 18.5 · p. 174
- **O que criar:**
  - `pilares_parede_nbr6118.py`: `le_lamina(l, b, vinculacao)` com os 4 casos (Figura 15.4); `esbeltez_lamina(...)` e `dispensa_efeito_localizado(...)` (15.9.2).
  - `decompor_em_faixas(lamina, Nd, M1xd) -> list[Faixa]` com nd(x), Ni e Myid, chamando `pilares_nbr6118` por faixa (15.9.3).
  - `As_transversal_pilar_parede(As_long_por_m)` = 25 % (18.5).
- **Depende de:** P11, P25, P28.
- **Testes e aceite:** Os 4 casos da Figura 15.4 (p. 132) em β = 1; soma das Ni = Nd.
- **Tamanho:** M (6 a 7 funções).

### P30 — Protensão: força, limites e perdas

- **Objetivo:** Aplicar os limites de σpi e σp0, compor Pt(x), Pk e Pd, e completar as perdas (tabela de μ e k, processo aproximado RN e RB, αp(t) entre grupos).
- **Onda 3**, prioridade média. Módulo: dimensionamento/protendido_nbr6118.py (extensão).
- **Itens (12):**
  - `9.6.1.1-forca-media` · 9.6.1.1 · p. 67
  - `9.6.1.2.1-sigma-pi-limites` · 9.6.1.2.1 · p. 67
  - `9.6.1.2.2-sigma-p0-termino` · 9.6.1.2.2 · p. 67
  - `9.6.1.2.3-tolerancia-execucao` · 9.6.1.2.3 · p. 67
  - `9.6.1.3-Pk-caracteristico` · 9.6.1.3 · p. 68
  - `9.6.1.4-Pd-calculo` · 9.6.1.4 · p. 68
  - `9.6.3.3.2.1-encurtamento-postracao` · 9.6.3.3.2.1 · p. 70
  - `9.6.3.3.2.2-tabela-mu-k` · 9.6.3.3.2.2 · p. 71
  - `9.6.3.4.2-deformacoes-aco-concreto` · 9.6.3.4.2 · p. 72
  - `9.6.3.4.3-processo-aproximado-RN` · 9.6.3.4.3 · p. 73
  - `9.6.3.4.3-processo-aproximado-RB` · 9.6.3.4.3 · p. 73
  - `9.6.3.4.5-psi-limite-tensao-minima` · 9.6.3.4.5 · p. 74
- **O que criar:**
  - `protendido_nbr6118`: `sigma_pi_limite(fptk, fpyk, sistema, aco)` (9.6.1.2.1); `verificar_sigma_p0(...)` (9.6.1.2.2); `tolerancia_execucao(...)` (9.6.1.2.3).
  - `forca_media(Pi, perdas_imediatas, perdas_progressivas) -> Pt` (9.6.1.1); `Pk_sup_inf(Pt, perda_max, Pi)` (9.6.1.3); `Pd(Pt, gama_p)` (9.6.1.4, γp do P4).
  - `TABELA_MU_K` com o caso de μ = 0,07 separado (9.6.3.3.2.2).
  - `perda_encurtamento_cabos_restantes_kncm2(..., Eci_t0_mpa=None)` com αp(t) (9.6.3.3.2.1).
  - `perda_progressiva_aproximada(aco='RN'|'RB', ...)` com a condição de 25 % de retração (9.6.3.4.3); `deformacoes_aco_concreto(...)` (9.6.3.4.2).
  - `psi_1000` devolve 0 abaixo de 0,5·fptk (9.6.3.4.5), mudança de comportamento declarada.
- **Depende de:** P4 (γp), P3 (catálogo), P6 (condição do processo aproximado).
- **Testes e aceite:** Os 4 limites de σpi (p. 67); tabela μ e k (p. 71); σpi = 0,5·fptk exato.
- **Tamanho:** G (13 a 14 funções).

### P31 — Protensão: ancoragem ativa, introdução da força e cabos

- **Objetivo:** Tirar a ancoragem de armadura ativa do legado e juntar introdução da força e detalhamento de cabos.
- **Onda 3**, prioridade média. Módulo: dimensionamento/protensao_detalhamento_nbr6118.py + ancoragem_nbr6118.py.
- **Itens (12):**
  - `9.3.2.2-fbpd` · 9.3.2.2 · p. 54
  - `9.3.2.2-etap2` · 9.3.2.2 · p. 54
  - `9.4.5.1-lbp-basico` · 9.4.5.1 · p. 59
  - `9.4.5.2-lbpt-transferencia` · 9.4.5.2 · p. 59
  - `9.4.5.3-lbpd-necessario` · 9.4.5.3 · p. 59
  - `9.6.2.2-angulo-beta-difusao` · 9.6.2.2 · p. 68
  - `9.6.2.3-lp-regularizacao` · 9.6.2.3 · p. 69
  - `18.6.1.2-raio-minimo-curvatura` · 18.6.1.2 · p. 175
  - `18.6.1.5-extremidade-reta-minima` · 18.6.1.5 · p. 175
  - `18.6.2.2-agrupamento-cabos` · 18.6.2.2 · p. 176
  - `18.6.2.3-tabela18.1-espacamento-postracao` · 18.6.2.3 · p. 177
  - `18.6.2.3-tabela18.2-espacamento-pretracao` · 18.6.2.3 · p. 177
- **O que criar:**
  - `ancoragem_nbr6118`: `fbpd_mpa(...)` e `eta_p2(...)` delegando ao núcleo; `lbp_cm`, `lbpt_cm(..., liberacao_gradual)`, `lbpd_cm(...)` (9.4.5), com `sec9.py` virando fachada.
  - `protensao_detalhamento_nbr6118.py`: `angulo_difusao_beta()` (9.6.2.2); `lp_regularizacao(h, lbpt)` (9.6.2.3).
  - `raio_minimo_curvatura(tipo)` (18.6.1.2); `trecho_reto_extremidade_min(...)` (18.6.1.5); `verificar_agrupamento_cabos(...)` (18.6.2.2); `TABELA_18_1`, `TABELA_18_2` e `espacamento_min_bainhas(...)`, `espacamento_min_fios(...)` (18.6.2.3).
- **Depende de:** P3, P22 (a fórmula de FSd de apoio intermediário já sai lá).
- **Testes e aceite:** Tabelas 18.1 e 18.2 inteiras (p. 177); lbpt com e sem liberação gradual (×1,25); fachada de `sec9` dá o mesmo número.
- **Tamanho:** M (12 a 13 funções).

### P32 — Protensão: ato da protensão e ELS de tensões

- **Objetivo:** Verificar a protensão no ato e em serviço: γ do ato, tensões-limite, armadura no estádio II, descompressão e formação de fissuras, Δσp não aderente e flecha com armadura ativa.
- **Onda 3**, prioridade média. Módulo: dimensionamento/protendido_nbr6118.py (extensão).
- **Itens (9):**
  - `17.2.4.3.1-coeficientes-ato-protensao` · 17.2.4.3.1-b · p. 143
  - `17.2.4.3.2-tensao-max-compressao` · 17.2.4.3.2-a · p. 144
  - `17.2.4.3.2-tensao-max-tracao` · 17.2.4.3.2-b · p. 144
  - `17.2.4.3.2-armadura-tracao-estadio2` · 17.2.4.3.2-c · p. 144
  - `17.2.4.4.1-limites-tensao-compressao-els` · 17.2.4.4.1 · p. 144
  - `17.2.4.4.2-limite-tensao-tracao-els` · 17.2.4.4.2 · p. 144
  - `17.3.4-descompressao-formacao-fissuras` · 17.3.4 · p. 150
  - `17.2.2c-delta-sigma-p-nao-aderente` · 17.2.2 c) · p. 140
  - `17.3.2.1.3-flecha-armaduras-ativas` · 17.3.2.1.3 · p. 148
- **O que criar:**
  - `protendido_nbr6118`: `GAMAS_ATO_PROTENSAO` (17.2.4.3.1 b); `verificar_ato_protensao(secao, P, M, fckj, ...) -> Resultado` com compressão, tração e armadura de tração no estádio II com limite de 150 ou 250 MPa (17.2.4.3.2).
  - `limites_tensao_servico(nivel, combinacao)` (17.2.4.4.1 e 17.2.4.4.2), conferindo `fct_admissivel_traçao_kncm2` (o fator 1,2 suspeito).
  - `verificar_descompressao_fissuracao(secao, P, e, M, nivel) -> Resultado` (17.3.4), sobre o estádio I e o P9.
  - `delta_sigma_p_nao_aderente(fck, rho_p, l_h)` (17.2.2 c); `flecha_protendido(...)` (17.3.2.1.3).
- **Depende de:** P1, P3, P8, P9, P30.
- **Testes e aceite:** Os limites do texto (p. 143-145) célula a célula; descompressão com σ = 0 exato; Δσp nas duas faixas de l/dp.
- **Tamanho:** M (10 a 11 funções).

### P33 — Lajes protendidas: detalhamento

- **Objetivo:** Regras de detalhamento de laje protendida (20.3.2).
- **Onda 3**, prioridade média. Módulo: dimensionamento/detalhamento_lajes_nbr6118.py.
- **Itens (10):**
  - `20.3.2.1-espacamento-max-cabos` · 20.3.2.1 · p. 194
  - `20.3.2.1-tensao-compressao-media-minima` · 20.3.2.1 · p. 194
  - `20.3.2.2-largura-max-faixa-externa` · 20.3.2.2 · p. 195
  - `20.3.2.3-espacamento-min-cabos` · 20.3.2.3 · p. 195
  - `20.3.2.4-cobrimento-min-cabo-abertura` · 20.3.2.4 · p. 195
  - `20.3.2.5-desvio-max-inclinacao` · 20.3.2.5 · p. 195
  - `20.3.2.5-distancia-min-cabos-curva` · 20.3.2.5 · p. 195
  - `20.3.2.6-cabos-atravessando-pilar` · 20.3.2.6 · p. 196
  - `20.3.2.6-barras-apoio-laje-lisa-protendida` · 20.3.2.6 · p. 196
  - `20.3.2.6-max-cabos-feixe-monocordoalha` · 20.3.2.6 · p. 196
- **O que criar:**
  - `detalhamento_lajes_nbr6118.py`: `espacamento_max_cabos(h)` e `verificar_compressao_media(P, Ac)` ≥ 1 MPa (20.3.2.1); `largura_max_faixa_externa(...)` (20.3.2.2); `espacamento_min_cabos(...)` (20.3.2.3); `cobrimento_cabo_abertura_min()` (20.3.2.4); `desvio_max_planta(...)` e `distancia_min_cabos_curva(...)` (20.3.2.5); `cabos_min_sobre_pilar()`, `armadura_apoio_laje_protendida(...)` e `max_monocordoalhas_feixe()` (20.3.2.6).
- **Depende de:** P18, P30.
- **Testes e aceite:** Cada limite literal do texto (p. 194-196), nos dois lados.
- **Tamanho:** M (10 funções).

### P34 — Regiões especiais: furos, aberturas e pressão de contato

- **Objetivo:** Regiões especiais: pressão de contato em área reduzida, articulação de concreto, furos em vigas e aberturas em lajes.
- **Onda 3**, prioridade média. Módulo: dimensionamento/regioes_especiais_nbr6118.py.
- **Itens (9):**
  - `21.2.1-FRd-esmagamento-area-reduzida` · 21.2.1 · p. 197
  - `21.2.1-proporcao-lados-ac0` · 21.2.1 · p. 197
  - `21.2.2-articulacao-concreto` · 21.2.2 · p. 198
  - `21.3.3-diametro-max-furo-viga` · 21.3.3 · p. 200
  - `21.3.3-distancia-min-furo-face` · 21.3.3 · p. 200
  - `21.3.3-secao-remanescente-furo-viga` · 21.3.3 · p. 200
  - `21.3.3-conjunto-furos-alinhados` · 21.3.3 · p. 200
  - `21.3.4a-secao-remanescente-abertura-laje` · 21.3.4 · p. 201
  - `21.3.4b-armadura-reforco-abertura-laje` · 21.3.4 · p. 201
- **O que criar:**
  - `regioes_especiais_nbr6118.py`: `FRd_area_reduzida(Ac0, Ac1, fcd)` com o limite de 3,3·fcd·Ac0 e a proporção de lados (21.2.1); `verificar_articulacao(...)` (21.2.2).
  - `phi_max_furo_viga(b)`, `distancia_min_furo_face(...)`, `verificar_conjunto_furos(...)` e `secao_remanescente_furo_viga(...)` chamando flexão e cortante (21.3.3).
  - `secao_remanescente_abertura_laje(...)` e `As_reforco_abertura(...)` (21.3.4 a e b).
- **Depende de:** P10 (dispensas de 13.2.5), P15.
- **Testes e aceite:** Proporção de lados no limite; furo com diâmetro exatamente no limite de 21.3.3 (ler o valor na imagem, p. 200).
- **Tamanho:** M (9 funções).

### P35 — Bielas e tirantes e vigas-parede

- **Objetivo:** Criar o núcleo de bielas e tirantes (fcd1, fcd2, fcd3, tirante, inclinação) e as armaduras de viga-parede.
- **Onda 3**, prioridade média. Módulo: dimensionamento/bielas_tirantes_nbr6118.py + vigas_parede_nbr6118.py.
- **Itens (7):**
  - `22.3.1-limite-inclinacao-biela` · 22.3.1 · p. 204
  - `22.3.2-fcd2` · 22.3.2 · p. 204
  - `22.3.3-as-tirante` · 22.3.3 · p. 204
  - `22.4.4.1-as-viga-parede-continua` · 22.4.4.1 · p. 205
  - `22.4.4.1-armadura-horizontal-minima-viga-parede` · 22.4.4.1 · p. 205
  - `22.4.4.3-armadura-vertical-minima-viga-parede` · 22.4.4.3 · p. 206
  - `22.4.4.3-verificacao-suspensao-carga-inferior` · 22.4.4.3 · p. 206
- **O que criar:**
  - `bielas_tirantes_nbr6118.py`: `fcd1`, `fcd2`, `fcd3` (22.3.2; fcd1 e fcd3 movidas de `blocos_nbr6118`, com reexportação); `As_tirante(FSd, fyd)` (22.3.3); `verificar_inclinacao_biela(tan)` entre 0,57 e 2 (22.3.1); `verificar_no(tipo, sigma)`.
  - `vigas_parede_nbr6118.py`: `repartir_As_negativa(As, l_h)` em 3 faixas (22.4.4.1); `As_horizontal_min(b)` e `As_vertical_min(b)` = 0,075 % (22.4.4.1 e 22.4.4.3); `suspensao_carga_inferior(F, fyd)` (22.4.4.3).
- **Depende de:** P11.
- **Testes e aceite:** Repartição em l/h = 1 e 3 (fronteiras); fcd2 contra a expressão da p. 204; fcd1 e fcd3 dão os mesmos números que `blocos_nbr6118`.
- **Tamanho:** M (9 funções).

### P36 — Consolos e dentes Gerber

- **Objetivo:** Consolos curtos e muito curtos e dentes Gerber, hoje inexistentes.
- **Onda 3**, prioridade média. Módulo: dimensionamento/consolos_nbr6118.py.
- **Itens (9):**
  - `22.5.1.1-classificacao-consolo` · 22.5.1.1 · p. 206
  - `22.5.1.2-limite-inclinacao-biela-consolo` · 22.5.1.2 · p. 207
  - `22.5.1.3-modelo-calculo-consolo` · 22.5.1.3 · p. 208
  - `22.5.1.4.1-as-min-tirante-consolo` · 22.5.1.4.1 · p. 208
  - `22.5.1.4.1-restricao-gancho-vertical-consolo` · 22.5.1.4.1 · p. 208
  - `22.5.1.4.3-armadura-costura-consolo` · 22.5.1.4.3 · p. 209
  - `22.5.1.4.4-armadura-suspensao-consolo` · 22.5.1.4.4 · p. 209
  - `22.5.2.3-modelo-calculo-dente-gerber` · 22.5.2.3 · p. 210
  - `22.5.2.4.2-as-suspensao-dente-gerber` · 22.5.2.4.2 · p. 211
- **O que criar:**
  - `consolos_nbr6118.py`: `classificar_consolo(a, d)` (22.5.1.1); `verificar_abertura_carga(...)` 1:2 (22.5.1.2).
  - `dimensionar_consolo(Fd, Hd, a, d, b, h, fck, fyk, modelo='biela_tirante'|'atrito') -> ResultadoConsolo` (22.5.1.3), com As do tirante e As,mín pela 17.3.5.2 (22.5.1.4.1), costura de 40 % em 2/3·d (22.5.1.4.3), suspensão (22.5.1.4.4) e a restrição de gancho vertical.
  - `dimensionar_dente_gerber(...)` reaproveitando o consolo com os ajustes de 22.5.2.2 (22.5.2.3); `As_suspensao_dente(Fd, fyd)` (22.5.2.4.2).
  - γn do P10 aplicado por padrão.
- **Depende de:** P10, P35.
- **Testes e aceite:** a/d = 0,5 e 1,0 nas fronteiras; exemplo de consolo montado à mão com modelo de biela e tirante; costura = 0,4·As exato.
- **Tamanho:** M (9 a 10 funções).

### P37 — Fundações: sapatas e blocos

- **Objetivo:** Completar sapatas e blocos: pré-condição de rigidez para tensão linear, detalhamento, fendilhamento, arranque, classificação e as regras de armadura do bloco.
- **Onda 3**, prioridade média. Módulo: dimensionamento/sapatas_nbr6118.py + blocos_nbr6118.py (extensão).
- **Itens (12):**
  - `22.6.1-hipotese-distribuicao-plana` · 22.6.1 · p. 211
  - `22.6.4.1.1-armadura-flexao-sapata-detalhamento` · 22.6.4.1.1 · p. 212
  - `22.6.4.1.1-fendilhamento-barra-25mm` · 22.6.4.1.1 · p. 213
  - `22.6.4.1.2-armadura-arranque-pilar-sapata` · 22.6.4.1.2 · p. 213
  - `22.7.1-classificacao-bloco-rigido-flexivel` · 22.7.1 · p. 213
  - `22.7.2.1-a-faixa-armadura-estacas` · 22.7.2.1 · p. 213
  - `22.7.4.1.1-armadura-flexao-bloco-85pct` · 22.7.4.1.1 · p. 214
  - `22.7.4.1.1-estacas-tracionadas-ancoragem` · 22.7.4.1.1 · p. 214
  - `22.7.4.1.2-armadura-distribuicao-bloco-20pct` · 22.7.4.1.2 · p. 214
  - `22.7.4.1.3-armadura-suspensao-bloco-condicional` · 22.7.4.1.3 · p. 215
  - `22.7.4.1.4-armadura-arranque-pilar-bloco` · 22.7.4.1.4 · p. 215
  - `22.7.4.1.5-armadura-lateral-superior-obrigatoria` · 22.7.4.1.5 · p. 215
- **O que criar:**
  - `sapatas_nbr6118`: `tensoes_sapata_excentrica_*` avisam quando `eh_rigida_nbr` é falso (22.6.1); `detalhamento_flexao_sapata(...)` (22.6.4.1.1); `verificar_fendilhamento_horizontal(phi)` para φ ≥ 25 mm; `altura_arranque_suficiente(h, lb_nec, c)` (22.6.4.1.2).
  - `blocos_nbr6118`: `eh_rigido_bloco(...)` (22.7.1); `faixa_armadura_estaca(phi_estaca)` = 1,2·φ (22.7.2.1); `verificar_85pct_nas_faixas(...)` com desigualdade estrita (mais de 85 %, não ≥ 85 %) (22.7.4.1.1); `ancoragem_estaca_tracionada(...)`.
  - Ligar `As_superior_dir` (20 % das forças, conferindo a base) e `Asp_pele_face` a `projetar_bloco`; suspensão só quando a distribuição passa de 25 % ou o espaçamento passa de 3·φ (22.7.4.1.2 a 22.7.4.1.5); altura para o arranque (22.7.4.1.4).
- **Depende de:** P20 (punção de sapata flexível), P21.
- **Testes e aceite:** Rigidez na fronteira; mais de 85 % (desigualdade estrita, não 85 % exato); as duas condições de disparo da suspensão; bloco em linha única exige armadura lateral.
- **Tamanho:** G (12 a 13 funções).

### P38 — Fadiga da armadura, curvas S-N e vibração

- **Objetivo:** Fadiga da armadura com as Tabelas 23.2 e 23.3, curva S-N, Palmgren-Miner e vibração (fn contra fcrit).
- **Onda 4**, prioridade baixa. Módulo: dimensionamento/fadiga_nbr6118.py.
- **Itens (12):**
  - `23.3-freq-natural-vs-critica` · 23.3 · p. 215
  - `23.3-tab23.1-fcrit` · 23.3 Tabela 23.1 · p. 216
  - `23.5.1-limite-20000-ciclos` · 23.5.1 · p. 216
  - `23.5.1-palmgren-miner` · 23.5.1 · p. 217
  - `23.5.5-verificacao-fadiga-armadura` · 23.5.5 · p. 220
  - `23.5.5-tab23.2-delta-fsd-fad` · 23.5.5 Tabela 23.2 · p. 220
  - `23.5.5-tab23.3-tipos-curva` · 23.5.5 Tabela 23.3 · p. 222
  - `23.5.5-curva-SN-armadura` · 23.5.5 · p. 222
  - `23.5.5-nota-e-barra-reta-limite` · 23.5.5 nota e · p. 221
  - `23.5.5-fator-redutor-pino-dobramento` · 23.5.5 nota d · p. 221
  - `23.5.5-relevo-nervura-r-h` · 23.5.5 · p. 223
  - `23.6-deformacao-progressiva-ciclica` · 23.6 · p. 223
- **O que criar:**
  - `fadiga_nbr6118.py`: `TABELA_23_1` e `verificar_vibracao(fn, uso)` com fn > 1,2·fcrit, com fn vindo de fora (23.3).
  - `TABELA_23_2` com erro nas células "–"; `TABELA_23_3`; `delta_fsd_fad(caso, phi, N=2e6)` com a curva S-N, a barra reta como teto e o fator ξ do pino (23.5.5).
  - `fator_relevo(r_h)` com a redução de 30 %; `verificar_fadiga_armadura(delta_sigma_s, ...)`; `palmgren_miner(espectro)`; `faixa_aplicabilidade(n_ciclos)` (23.5.1).
  - `deformacao_progressiva(a1, n)` (23.6).
- **Depende de:** P9 (Δσs em estádio II).
- **Testes e aceite:** Tabelas 23.1 a 23.3 inteiras (p. 216-222); curva S-N contínua em N*; Miner = 1 no limite.
- **Tamanho:** M (12 funções).

### P39 — Fadiga: combinação, cortante, concreto e protensão

- **Objetivo:** Fadiga do concreto e da cortante e a combinação própria de fadiga.
- **Onda 4**, prioridade baixa. Módulo: dimensionamento/fadiga_nbr6118.py + cortante_nbr6118.py.
- **Itens (11):**
  - `23.5.2-combinacao-frequente-fadiga` · 23.5.2 · p. 217
  - `23.5.2-psi1-fadiga-tabela` · 23.5.2 · p. 217
  - `23.5.5-fator-reducao-ciclos-menor` · 23.5.2 · p. 217
  - `23.5.3-modelo-I-vc-reduzido-fadiga` · 23.5.3 · p. 218
  - `23.5.3-modelo-II-theta-corrigido-fadiga` · 23.5.3 · p. 218
  - `23.5.3-eta-s-fator-aderencia` · 23.5.3 · p. 218
  - `23.5.3-xi-relacao-aderencia` · 23.5.3 · p. 219
  - `23.5.3-phi-eq-feixe` · 23.5.3 · p. 218
  - `23.5.4.1-fadiga-concreto-compressao` · 23.5.4.1 · p. 219
  - `23.5.4.1-eta-c-grad` · 23.5.4.1 · p. 219
  - `23.5.4.2-fadiga-concreto-tracao` · 23.5.4.2 · p. 220
- **O que criar:**
  - `combinacao_fadiga(acoes, tipo_obra)` com `TABELA_PSI1_FADIGA` (23.5.2), sobre o P4.
  - `cortante_nbr6118.modelo_calculo_I/II(..., fadiga=True)`: Vc × 0,5 e tg θcor = √tg θ ≤ 1 (23.5.3).
  - `eta_s(...)`, `TABELA_XI_ADERENCIA` e `phi_eq_feixe(Ap)` (23.5.3).
  - `eta_c_grad(sigma_c1, sigma_c2)` e `verificar_fadiga_concreto_compressao(...)` (23.5.4.1); `verificar_fadiga_concreto_tracao(...)` com 0,3·fctd,inf (23.5.4.2); ciclos muito menores que 2·10⁶ (23.5.5).
- **Depende de:** P4, P9, P15, P38.
- **Testes e aceite:** Os valores de ψ1 e ξ (p. 217-219) célula a célula; θcor em θ = 30° e 45°.
- **Tamanho:** M (11 funções).

### P40 — Concreto simples: núcleo e seções

- **Objetivo:** Criar o núcleo do concreto simples, com γc = 1,68 isolado para não herdar o 1,4.
- **Onda 4**, prioridade baixa. Módulo: dimensionamento/concreto_simples_nbr6118.py.
- **Itens (15):**
  - `24.2-condicoes-uso` · 24.2 · p. 224
  - `24.3-classe-concreto` · 24.3 · p. 224
  - `24.4-junta-dilatacao-espacamento` · 24.4 · p. 224
  - `24.4-distancia-armadura-junta` · 24.4 · p. 224
  - `24.5.2.1-fctd-simples` · 24.5.2.1 · p. 225
  - `24.5.2.2-tensoes-resistentes-fibra-extrema` · 24.5.2.2 · p. 225
  - `24.5.2.3-tau-wRd-flexao` · 24.5.2.3 · p. 225
  - `24.5.2.4-6-tau-Rd-limitado` · 24.5.2.4/24.5.2.5/24.5.2.6 · p. 225-226
  - `24.5.3-altura-concreto-contra-solo` · 24.5.3 · p. 226
  - `24.5.4.1-limites-deformacao-extrema` · 24.5.4.1 · p. 226
  - `24.5.4.2-limites-deformacao-media` · 24.5.4.2 · p. 227
  - `24.5.4.3-tensoes-resistentes-flexao-simplificada` · 24.5.4.3 · p. 227
  - `24.5.5.1-tau-wd-secao-retangular` · 24.5.5.1 · p. 227
  - `24.5.5.2-3-secao-critica-lajes` · 24.5.5.2/24.5.5.3 · p. 227
  - `24.5.6-torcao-cisalhamento-interacao` · 24.5.6 · p. 227
- **O que criar:**
  - `concreto_simples_nbr6118.py`: `GAMA_C_SIMPLES = 1.68`; `validar_fck_simples` (C15 a C40, 24.3); `concreto_simples_aplicavel(...)` (24.2); juntas: `JUNTA_MAX_M = 15`, `DIST_ARMADURA_JUNTA_CM = 6` (24.4).
  - `fctd_simples`, `fcd_simples` (24.5.2.1); `sigma_cRd`, `sigma_ctRd` com 0,85 (24.5.2.2); `tau_wRd(...)` (24.5.2.3); `tau_Rd_laje_torcao_puncao(...)` com teto de 1,0 MPa (24.5.2.4 a 24.5.2.6).
  - `altura_contra_solo(h)` (24.5.3); limites de deformação (24.5.4.1 e 24.5.4.2); `tensoes_flexao_simplificada(...)` com 0,8 (24.5.4.3).
  - `tau_wd_retangular(V, b, h)` = 3V/(2bh) (24.5.5.1); `secao_critica_cisalhamento(...)` (24.5.5.2 e 24.5.5.3); `verificar_torcao_cortante(...)` (24.5.6).
- **Depende de:** Nenhum.
- **Testes e aceite:** γc = 1,68 em todas as funções (teste que falha se alguma chamar `nucleo.fctd` sem γc); 0,85 × 0,8 em funções diferentes; tetos de 2× e de 1 MPa.
- **Tamanho:** G (15 a 16 funções, simples).

### P41 — Concreto simples: elementos

- **Objetivo:** Elementos de concreto simples: seção comprimida excêntrica, pilar-parede e pilar, bloco de fundação e arco.
- **Onda 4**, prioridade baixa. Módulo: dimensionamento/concreto_simples_nbr6118.py.
- **Itens (16):**
  - `24.5.7.2-secao-comprimida-excentrica` · 24.5.7.2 · p. 228
  - `24.5.7.3-secao-comprimida-cortante` · 24.5.7.3 · p. 229
  - `24.6.1-NRd-pilar-parede` · 24.6.1 · p. 229
  - `24.6.1-comprimento-horizontal-carga` · 24.6.1 · p. 229
  - `24.6.1-espessura-minima` · 24.6.1 · p. 229-230
  - `24.6.1-abertura-armadura-minima` · 24.6.1 · p. 230
  - `24.6.2-proibicao-bloco-estaca` · 24.6.2 · p. 230
  - `24.6.2-area-base-tensao-admissivel` · 24.6.2 · p. 230
  - `24.6.2-espessura-bloco` · 24.6.2 · p. 230
  - `24.6.2-momento-secao-critica` · 24.6.2 · p. 230
  - `24.6.2-cortante-limite` · 24.6.2 · p. 230
  - `24.6.3-remissao-pilar-parede` · 24.6.3 · p. 230
  - `24.6.3-nucleo-central-inercia` · 24.6.3 · p. 230
  - `24.6.3-dimensao-minima` · 24.6.3 · p. 230
  - `24.6.4-sem-tracao` · 24.6.4 · p. 230
  - `24.6.4-majoracao-2a-ordem` · 24.6.4 · p. 230
- **O que criar:**
  - `secao_comprimida_excentrica(Nd, ex, ey, hx, hy) -> (G1, Ae, ok)` (24.5.7.2) e `com_cortante(...)` (24.5.7.3).
  - `NRd_pilar_parede(...)`, `comprimento_horizontal_carga(...)`, `espessura_minima_pilar_parede(...)` e `armadura_aberturas(...)` (24.6.1); pilar comum pelo mesmo método, com núcleo central e dimensão mínima (24.6.3).
  - Blocos: proibição sobre estacas, área da base reusando `sapatas_nbr6118.area_base_cm2`, espessura mínima de 20 cm, momento e cortante na seção crítica (24.6.2).
  - Arcos: `verificar_sem_tracao(...)` e o teto de 10 % de 2ª ordem (24.6.4).
- **Depende de:** P40.
- **Testes e aceite:** G1 e Ae contra a figura da p. 228 com números à mão; e = h/6 no limite do núcleo; NRd na esbeltez de fronteira.
- **Tamanho:** G (16 funções; a área eficaz é geometria).

### P42 — Flexo-torção de perfis abertos

- **Objetivo:** Flexo-torção de perfis abertos de parede fina (pré-moldados).
- **Onda 4**, prioridade baixa. Módulo: dimensionamento/torcao_perfis_abertos_nbr6118.py.
- **Itens (3):**
  - `17.5.2.1-17.5.2.2-perfis-abertos-generalidades` · 17.5.2.1/17.5.2.2 · p. 162
  - `17.5.2.3-rigidez-flexo-torcao` · 17.5.2.3 · p. 163
  - `17.5.2.4-resistencia-flexo-torcao` · 17.5.2.4 · p. 163
- **O que criar:**
  - `torcao_perfis_abertos_nbr6118.py`: `rigidezes_reduzidas()` com 0,15 e 0,50 (17.5.2.2); `rigidez_flexo_torcao(f1, f2, z, T)` (17.5.2.3); `TRd_flexo_torcao(FRd, FSd, z)` (17.5.2.4).
- **Depende de:** P14 (largura colaborante).
- **Testes e aceite:** Caso simétrico montado à mão.
- **Tamanho:** P (3 a 4 funções).

### P43 — Método geral de perdas e fluência com tensão variável

- **Objetivo:** O caso geral: fluência com tensão variável (forma integral) e perdas progressivas em fases diferentes.
- **Onda 4**, prioridade baixa. Módulo: dimensionamento/tempo_concreto_nbr6118.py + protendido_nbr6118.py.
- **Itens (2):**
  - `9.6.3.4.4-metodo-geral` · 9.6.3.4.4 · p. 73
  - `A.2.5-formula-integral` · A.2.5 · p. 240
- **O que criar:**
  - `tempo_concreto_nbr6118.eps_c_integral(historico_sigma, ...)` por passos (A.2.5).
  - `protendido_nbr6118.perdas_metodo_geral(fases, camadas, cabos, ...)` (9.6.3.4.4).
- **Depende de:** P6, P7, P30.
- **Testes e aceite:** Com uma fase só, reproduz o processo simplificado (9.6.3.4.2); com tensão constante, reproduz a forma simplificada de A.2.5.
- **Tamanho:** G (2 funções, ambas iterativas).

### P44 — Análise de barras: pórtico plano, pórtico espacial, grelha e treliça

- **Objetivo:** Dar à biblioteca um cálculo próprio de estruturas de barras, pelo método dos deslocamentos e com as hipóteses da análise linear da 6118, para que ela produza os esforços em vez de só recebê-los.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/analise_barras_nbr6118.py.
- **Itens (5):**
  - `11.3.3.3-deslocamentos-apoio` · 11.3.3.3 · p. 78
  - `11.4.1.1-cargas-utilizacao` · 11.4.1.1 · p. 81
  - `14.5.2-analise-linear` · 14.5.2 · p. 105
  - `14.6.4.1-rigidez-vigas-pilares` · 14.6.4.1 · p. 111
  - `14.8.1-vigas-parede-pilares-parede-analise` · 14.8.1 · p. 119
- **O que criar:**
  - `Modelo`, com nós, barras, apoios (inclusive mola), liberações de extremidade, trechos rígidos e casos de carga; `Barra`, com a seção (A, I, J e área de cisalhamento) e o material pelo núcleo (Ecs de 8.2.8, Gc de 8.2.9).
  - Elementos: pórtico plano (3 graus de liberdade por nó), grelha (3), pórtico espacial (6) e treliça 2D e 3D (só força normal). Opção de deformação por cisalhamento (Timoshenko), exigida para representar viga-parede e pilar-parede como elemento linear equivalente (14.8.1).
  - `resolver(modelo, caso) -> ResultadoAnalise`: montagem esparsa, deslocamentos, reações e esforços nas extremidades e ao longo de cada barra. Todo resultado confere o equilíbrio (soma das reações igual à soma das cargas) e levanta erro se não fechar.
  - Cargas: nodal, distribuída uniforme e trapezoidal, concentrada na barra, temperatura uniforme e gradiente (os valores vêm do P4) e deslocamento imposto de apoio (11.3.3.3), com dk,sup pessimista e dk,inf nulo.
  - `alternancia_cargas(modelo, caso_q)`: as variáveis nas posições mais desfavoráveis, vão a vão, com a envoltória (11.4.1.1); respeita a dispensa de 14.6.6.3 (P14).
  - Rigidez padrão pela seção bruta, com Ecs (14.5.2 e 14.6.4.1). A rigidez à torção reduzida de 14.6.6.2 e as rigidezes aproximadas de 15.7.3 entram como opção.
- **Depende de:** P2 (ν e Gc), P4 (casos de carga e combinações), P14 (trecho rígido, largura colaborante e rigidez à torção).
- **Testes e aceite:** Soluções fechadas: viga biapoiada, engastada e contínua de dois vãos (equação dos três momentos), pórtico simples, grelha de duas vigas cruzadas e treliça isostática pelo método dos nós; recalque de apoio em viga contínua; equilíbrio em todos os casos, nas duas direções e nos dois sentidos de carga. Como a norma não tabela esses números, o verificador de execução refaz cada caso com solução analítica própria.
- **Tamanho:** G (algoritmo matricial, 18 a 22 funções e classes).

### P45 — Lajes por grelha e pórtico equivalente

- **Objetivo:** Calcular laje nervurada e laje lisa pelos processos que a 6118 prescreve: grelha de nervuras, grelha equivalente e pórtico equivalente.
- **Onda 2**, prioridade alta. Módulo: dimensionamento/analise_lajes_nbr6118.py.
- **Itens (5):**
  - `14.7.3.1-rigidez-estadio-I-placas` · 14.7.3.1 · p. 116
  - `14.7.7-lajes-nervuradas-grelha-vigas` · 14.7.7 · p. 117
  - `14.7.7-lajes-nervuradas-unidirecionais` · 14.7.7 · p. 118
  - `14.7.8-analise-numerica-lajes-lisas` · 14.7.8 · p. 118
  - `14.7.8-portico-equivalente` · 14.7.8 · p. 118
- **O que criar:**
  - `grelha_nervurada(...)`: gera a grelha das nervuras, cada uma com a seção T da largura colaborante do P14, e a resolve no P44 (14.7.7); `nervurada_unidirecional(...)`: vigas na direção das nervuras, sem rigidez transversal e sem rigidez à torção.
  - `grelha_equivalente_laje_lisa(...)`: malha de barras com a rigidez à flexão da faixa e a rigidez à torção da placa, com os pilares como apoios elásticos (14.7.8, procedimento numérico por grelha equivalente).
  - `portico_equivalente(...)`: monta os pórticos múltiplos de cada direção, com a carga total, resolve no P44 e reparte os momentos entre as faixas pela Figura 14.9 (P17). Confere antes as condições de uso do processo: pilares em filas ortogonais e vãos pouco diferentes (14.7.8).
  - `verificar_rigidez_estadio_I(Md_max, Mr)`: autoriza a rigidez bruta na flecha de placa só se o momento ficar abaixo do de fissuração (14.7.3.1); se não ficar, manda para o P8.
- **Depende de:** P44, P14 (largura colaborante e rigidez à torção), P17 (faixas da Figura 14.9), P10 (limites de nervurada de 13.2.4.2).
- **Testes e aceite:** Grelha de uma laje quadrada simplesmente apoiada contra a solução de placa de Timoshenko, com tolerância declarada e convergência com o refinamento da malha; pórtico equivalente de um painel regular com os momentos das faixas somando o total do pórtico; nervurada unidirecional igual à viga contínua equivalente.
- **Tamanho:** G (12 a 15 funções, com a geração de malha).

### P46 — Redistribuição com reequilíbrio e 2ª ordem global por análise não linear

- **Objetivo:** Fechar os procedimentos que a 6118 prevê em cima da análise: redistribuir e reequilibrar e, em estrutura de nós móveis, calcular a 2ª ordem global com não linearidade geométrica e física, em vez de só receber o γz pronto.
- **Onda 3**, prioridade média. Módulo: dimensionamento/analise_barras_nbr6118.py + estabilidade_global_nbr6118.py.
- **Itens (3):**
  - `14.5.3-analise-redistrib-geral` · 14.5.3 · p. 106
  - `14.6.4.2-restricoes-redistribuicao` · 14.6.4.2 · p. 111
  - `15.7.1-nao-linearidade-nos-moveis` · 15.7.1 · p. 126
- **O que criar:**
  - `redistribuir(resultado, apoios, delta)`: reduz os momentos de apoio por δ, refaz o equilíbrio de cada vão e devolve os esforços redistribuídos, com os limites do P13 (x/d e δ mínimo) (14.5.3). Recusa redistribuir em pilar e consolo fora do caso que a norma permite (14.6.4.2).
  - `analise_p_delta(modelo, caso, rigidez='nlf_aproximada')`: 2ª ordem geométrica iterativa com as rigidezes de 15.7.3 como não linearidade física aproximada, até convergir, com o número de iterações e o critério na memória (15.7.1).
  - `gama_z_do_modelo(modelo, combinacao)`: calcula M1tot,d e ΔMtot,d no próprio modelo e chama o `gama_z` do P26; `classificar_nos` passa a aceitar o modelo.
- **Depende de:** P44, P13, P26, P4.
- **Testes e aceite:** Viga contínua redistribuída que continua em equilíbrio; pilar em balanço com carga vertical e horizontal contra o fator de amplificação 1/(1 − P/Pcr); γz do modelo igual ao γz do P26 com as mesmas entradas; P-Δ e 0,95·γz próximos quando γz ≤ 1,3.
- **Tamanho:** G (iterativo, 8 a 10 funções).

### P47 — Esforços hiperestáticos de protensão

- **Objetivo:** Calcular os esforços hiperestáticos da protensão em viga contínua e pórtico e levá-los ao ELU como a 6118 pede.
- **Onda 3**, prioridade média. Módulo: dimensionamento/protendido_nbr6118.py + analise_barras_nbr6118.py.
- **Itens (2):**
  - `11.3.3.5-protensao-acao` · 11.3.3.5 · p. 81
  - `17.2.4.2.1-protensao-hiperestatica-pre-alongamento` · 17.2.4.2.1 · p. 143
- **O que criar:**
  - `cargas_equivalentes_cabo(perfil, P)`: as forças que o cabo aplica ao concreto (carga distribuída da curvatura e forças concentradas nas ancoragens e nas mudanças de traçado), com a força P ao longo do cabo vinda do P30.
  - `esforcos_hiperestaticos_protensao(modelo, cabo) -> Resultado`: resolve as cargas equivalentes no P44 e separa o esforço total, o isostático (P·e) e o hiperestático (11.3.3.5).
  - `combinar_protensao_elu(...)`: no ELU entra só o hiperestático, e a armadura ativa entra pelo pré-alongamento (17.2.4.2.1), com o γp do P30.
- **Depende de:** P44, P30, P3.
- **Testes e aceite:** Viga contínua de dois vãos iguais com cabo parabólico: momento hiperestático contra a solução fechada; em viga biapoiada, o hiperestático é zero.
- **Tamanho:** M (6 a 8 funções).

### P48 — Bielas e tirantes: treliças e modelos de cálculo

- **Objetivo:** Montar e resolver as treliças de bielas e tirantes que a 6118 pede para regiões D, vigas-parede, sapatas e blocos, e entregar as forças às verificações do P35.
- **Onda 3**, prioridade média. Módulo: dimensionamento/bielas_tirantes_nbr6118.py.
- **Itens (6):**
  - `21.2.3-intro-protensao-modelo-3d` · 21.2.3 · p. 199
  - `22.2-limite-regiao-bd` · 22.2 · p. 202
  - `22.3.1-procedimento-bielas-tirantes` · 22.3.1 · p. 203
  - `22.4.3-modelo-calculo-viga-parede` · 22.4.3 · p. 205
  - `22.6.3-modelo-calculo-sapata` · 22.6.3 · p. 212
  - `22.7.3-modelo-calculo-bloco` · 22.7.3 · p. 213
- **O que criar:**
  - `extensao_regiao_d(h_cm, ...)`: a região D vai até a distância h da descontinuidade (22.2).
  - `TrelicaBT`: nós, bielas e tirantes, resolvida na treliça do P44. Confere que a treliça é isostática e autoequilibrada e devolve a força em cada barra, já classificada em biela ou tirante (22.3.1).
  - Modelos-padrão, cada um com a geometria da literatura declarada na docstring: viga-parede biapoiada e contínua (22.4.3); sapata sob pilar com carga centrada e excêntrica, em 3D (22.6.3); bloco de 2 a 6 estacas, em 3D, com a reação de cada estaca (22.7.3); e a zona de ancoragem da protensão, com a força de fendilhamento (21.2.3).
  - Cada modelo entrega as forças a `verificar_biela`, `verificar_no` e `As_tirante` do P35.
- **Depende de:** P44 (treliça), P35 (verificações), P31 (ancoragem ativa).
- **Testes e aceite:** Bloco de 2 estacas contra o método das bielas que já existe (mesma força no tirante); viga-parede biapoiada com o braço z da literatura; treliça hipostática recusada com mensagem clara; zona de ancoragem concêntrica contra a expressão fechada do fendilhamento, com a fonte declarada.
- **Tamanho:** G (12 a 14 funções).

## 5. Ordem de execução

| Onda | Pacotes | Leva paralela possível |
|---|---|---|
| Preparação | Renomear os módulos (decisão 4) | Sozinha, antes de tudo, com commit próprio |
| 1 | P1 a P9 | {P1, P2, P3, P4, P6} → {P5, P7, P8} → {P9} |
| 2 | P10 a P26, P44 e P45 | {P10, P11, P13, P14, P21} → {P12, P15, P17, P24, P26, P44} → {P16, P19, P25, P45} → {P18, P20, P22, P23} |
| 3 | P27 a P37, P46 a P48 | {P27, P28, P30, P34, P35, P46} → {P29, P31, P32, P36, P47} → {P33, P37, P48} |
| 4 | P38 a P43 | {P38, P40, P42} → {P39, P41, P43} |

**Dependências que forçam a ordem:**

1. **P4 (combinações)** alimenta P8 (flecha, combinação quase permanente), P9 (fissuração, frequente), P26 (vento contra desaprumo), P30 (Pd = γp·Pt) e P39.
2. **P6 (Anexo A)** alimenta P7, P25 (fluência de pilar, 15.8.4), P43 e, opcionalmente, P8 (flecha diferida com φ preciso).
3. **P9 (estádio II)** alimenta P32 (ELS de protensão), P38 e P39 (tensões de fadiga) e o wk automático com Acri.
4. **P1 (wk,máx)** alimenta P9 e P32.
5. **P21 (ganchos e Tabela 9.2)** vem antes de P22 e P23, porque 18.3.2.4.1 usa o raio do gancho; **P24** cria `phi_n_feixe` no núcleo, usado por P22 e P27.
6. **P15 (VRd2)** vem antes de P23 (smáx e st,máx de estribo dependem de Vd/VRd2).
7. **P19** vem antes de **P20**, e P20 vem antes de P37 (sapata flexível) e de P34 (abertura junto a pilar).
8. **P11 (classificação)** vem antes de P29 (pilar-parede), P35 (viga-parede) e P36.
9. **P3 (Figura 8.6)** vem antes de P32 (tensão na armadura ativa).
10. **P28 (M-N-1/r)** vem antes de P29.
11. **P44 (cálculo de barras)** vem depois de P2, P4 e P14, e alimenta P45, P46, P47 e P48. **P46** precisa ainda de P13 e P26; **P47**, de P30; **P48**, de P35 e P31.

## 6. Decisões tomadas em 19/09/2026

1. **Análise estrutural.** Entra a análise que a 6118 prescreve, com cálculo próprio em Python e só com barras: pórtico plano e espacial, grelha, treliça 2D e 3D e 2ª ordem global. Ficam de fora os elementos finitos de placa e de sólido e o vento (NBR 6123). Ver 3.1 e os pacotes P44 a P48.
2. **Figura 8.6.** O ramo inclinado até fptd em εpu vira o **padrão**, e o patamar de hoje fica como opção (`diagrama="patamar"`). Muda o resultado de seção protendida no ELU (a estimativa, com o cabo a uns 15 ‰, é de 2 % a 3 % a mais no momento resistente), e o P3 lista o antes e o depois.
3. **γg da nota a da Tabela 11.1.** O padrão é 1,4, num parâmetro configurável no começo do script (`nucleo.GAMA_G`), lido na hora da chamada e registrado na memória de cálculo. A biblioteca não decide se a obra é de pequena variabilidade (3.3, item 9).
4. **Nomes dos módulos.** Os `*_bastos.py` são renomeados para `*_nbr6118.py` já, antes da onda 1, sem fachada no nome antigo. Quem importa o nome antigo troca o import. O crédito ao Prof. Bastos passa para a docstring de cada módulo e para o README (3.2).
5. **Versionamento.** Direto no main, com um commit por pacote aprovado nas três verificações. Push só quando o Gustavo mandar.
6. **VRd1 de laje.** `lajes_nbr6118.cortante_resistente_laje` passa a delegar a `cortante_nbr6118.laje_sem_armadura` (P15). O resultado muda só quando há força normal.

## 7. Fora do escopo

1. **Não computáveis (143 itens).** Princípios, remissões e recomendações sem regra verificável: a 16.x inteira, a 25.x e as hipóteses gerais de 14.2 a 14.5. Estão listados na matriz como "não computável".
2. **Outra norma (1 item):** o vento (11.4.1.2, NBR 6123). A biblioteca recebe os esforços de vento, combina-os (P4) e os compara com o desaprumo (P26).
3. **Método que a biblioteca não vai ter:** elementos finitos de placa e de sólido (decisão 1). Isso não tira nenhum item do plano: onde a norma aceita outro procedimento, ele entra (grelha equivalente para laje lisa, treliça 3D para sapata e bloco). O que só se faz com elementos finitos, como a análise não linear de placas (14.7.5), já estava entre os não computáveis.

## 8. Riscos e cuidados

1. **Duas unidades para o mesmo h no Anexo A.** O h vai em cm em φ2c e ε2s e em m em βf e βs: fator 100 em duas das quatro fórmulas. A função recebe `hfic_cm` e converte dentro, com teste que cruza as quatro.
2. **Duas idades t0.**
   - A Tabela 8.1 usa idade real, e o Anexo A usa idade fictícia.
   - Os parâmetros têm nomes diferentes (`t0_dias` e `t0_ficticia_dias`), e a docstring proíbe trocar um pelo outro.
3. **Fórmulas parecidas com semântica diferente:**
   - imperfeição global (H total, n pilares) contra a local (Hi do lance);
   - suspensão de bloco contra suspensão de viga;
   - γn de laje em balanço (13.2.4.1) contra a armadura de robustez de balanço (20.6);
   - 0,85·fctd (24.5.2.2) contra 0,8·fctd (24.5.4.3) no concreto simples.
   - Em todos, o nome da função diz qual é.
4. **γ fixos que não são os do projeto.** M0 usa γf = 1,0 e γp = 0,9 (17.4.2.2). No ato da protensão, γp = 1,1 e γf = 1,0. O concreto simples usa γc = 1,68. São constantes locais nomeadas, nunca o padrão do núcleo, para não herdar γc = 1,4 em silêncio.
5. **Descontinuidades propositais da norma.** Os degraus em Vd/VRd2 = 0,67 e 0,20 (18.3.3.2) e o limite exato |Mapoio| = 0,5·Mvão (18.3.2.4 c) são saltos da norma, não erros de redação. Cada um ganha teste dos dois lados do degrau.
6. **Tabelas degrau contra interpolação.** Conferido na imagem: nem a Tabela 9.4 (α0t) nem a Tabela 19.2 (K) dizem como tratar valores intermediários. O `alpha_0t` atual usa o degrau superior, o que fica a favor da segurança, e continua assim, com teste em 30 % e 40 %. Para o K da punção, ver o P19. Regra geral: só interpolar quando a norma diz que pode (como nas Tabelas 8.1 e 8.3); quando não diz, a escolha fica declarada na docstring.
7. **Figura 20.2 embaralhada no texto extraído.** Os percentuais e as frações de vão só se leem na imagem (p. 194). Vale para toda figura: a fonte é o PNG, nunca o .txt.
8. **Mudança de comportamento.** Onde um pacote muda resultado existente (P3 com a Figura 8.6 como padrão, P15 com Vc em flexo-compressão, P30 com ψ1000 abaixo de 0,5·fptk devolvendo 0 em vez de erro), o parecer do pacote lista antes e depois, como a CORRECOES fez.
9. **Comparação com o TQS.** Os pacotes que mexem em pilar (P25, P28) exigem rodar de novo o `compare_3way_parallel.py`. Os dois obstáculos da CORRECOES (o `import tests` e o fck fora da faixa fora do `try`) precisam ser resolvidos antes.
10. **Tamanho do núcleo.** Ver 3.2, item 3.
11. **Cálculo de barras sem número na norma.** O risco típico é erro de sinal ou de convenção de eixo, que passa despercebido num caso simétrico. Os testes do P44 cobrem as duas direções e os dois sentidos de carga, conferem o equilíbrio em todo resultado e comparam com solução fechada (3.1).
12. **Renomear quebra import.** A preparação troca o nome dos módulos sem fachada. Antes do commit, o pytest inteiro e os scripts de comparação com o TQS têm de rodar com os nomes novos, e o README muda junto. O artigo do blog sobre a biblioteca usa o nome antigo no exemplo de código e nos créditos, e muda junto se ainda não tiver sido publicado.

## 9. Como a execução vai funcionar

**Antes da onda 1, a preparação (decisão 4):** renomear os módulos com `git mv`, para o histórico acompanhar cada arquivo; trocar todos os imports (biblioteca, testes, `secoes_norma/`, scripts de comparação e README); levar o crédito ao Prof. Bastos para a docstring de cada módulo; rodar o pytest inteiro; e commitar sozinho, sem nenhuma mudança de conteúdo misturada.

Para cada pacote, na ordem da seção 5:

1. **Brief de implementação.** O agente recebe só três coisas:
   - o texto do pacote (esta seção 4);
   - as linhas dos seus itens no `PLANO_IMPLEMENTACAO_NBR6118_2026_ITENS.json` (fórmula transcrita, teste sugerido, dependências);
   - as páginas da norma em PNG.

   Não recebe o histórico da conversa. O modelo e o esforço seguem a nota de cada tarefa, conforme a regra global. A fórmula do JSON é ponto de partida: quem implementa confere na imagem da página antes de codificar.
2. **Implementação com testes.** Código mais `tests/test_<modulo>.py`, com os valores esperados tirados da norma. O pytest inteiro tem de passar, inclusive os 613 testes atuais.
3. **Verificação independente em 3 lentes,** cada uma por um agente diferente, que não viu o gerador:
   - **Norma na imagem:** confere cada fórmula, coeficiente e célula de tabela contra o PNG da página.
   - **Execução com script próprio:** recalcula os casos de teste e casos novos sem importar a biblioteca, e compara.
   - **Revisão do diff:** assinaturas, unidades no nome, faixa de validade, mensagens com acento, nada quebrado fora do pacote.
4. **Correção e segunda volta.** O que as lentes acharem volta ao implementador, e só a lente que achou confere de novo.
5. **Registro.** Uma linha por item na matriz (status novo, função, teste) e um parecer curto do pacote, com as mudanças de comportamento.
6. **Commit.** Um por pacote, direto no main (decisão 5), depois que as três lentes aprovarem. **Push só quando ele mandar.**
7. **Fim de onda.** Resumo para ele revisar: pacotes fechados, testes, mudanças de comportamento e o que ficou para a onda seguinte.

## 10. Como este plano foi montado e conferido

1. **Mapa da norma.** 16 agentes leram, cada um, um trecho do PDF (seções 5 a 25 e Anexo A) e listaram todo item calculável ou conferível: fórmula, tabela, limite, verificação, regra de detalhamento, procedimento ou classificação. Para cada item, abriram o código e disseram se está implementado, parcial ou ausente. As fórmulas foram transcritas da imagem da página, não do texto extraído.
2. **Síntese.** Um agente juntou os 661 itens em pacotes, ondas e convenções. Um script conferiu que todo item pendente caiu em exatamente um pacote ou tem motivo para ficar fora.
3. **Verificação em 3 lentes, independentes do gerador:**
   - **Cobertura da norma:** as páginas 30 a 242 foram relidas por inteiro atrás de prescrição calculável sem item. Achou 4 candidatos: 1 era item novo (Tabela 13.2, que já estava implementada), e os outros 3 já existiam no mapa.
   - **Estado do código:** os 266 itens implementados, parciais ou ausentes de prioridade alta foram conferidos um a um, com Grep e execução. Três estavam errados e foram corrigidos: a Tabela 9.2 já existe no legado; a envoltória mínima com 2ª ordem já é verificada, faltando só calcular os momentos; e uma citação de função apontava para o lugar errado. Um quarto achado, que rebaixava o `alpha_0t` por não interpolar, foi rejeitado depois de ler a norma: a Tabela 9.4 não manda interpolar.
   - **Fórmulas na imagem:** as 458 fórmulas transcritas foram conferidas na imagem da página, uma a uma. A primeira rodada foi por amostragem e foi refeita completa. Cada achado passou por uma segunda leitura independente. Somando as duas rodadas, foram corrigidas 14 fórmulas ou condições de validade e 22 páginas. Outros 23 achados foram rejeitados, quase todos por confundirem a página impressa com a do PDF.
4. **Revisão de 19/09/2026.** Com as decisões da seção 6, 21 itens entraram em pacotes: os 7 de análise que estavam fora; 13 que estavam como não computáveis só porque a biblioteca não calculava estrutura (reclassificados na revisão, com o motivo no campo `revisao` do JSON); e 1 item que o mapa não tinha (15.7.1, conferido no texto da p. 126). Um script confere que a matriz, o JSON e este plano dão os mesmos números. Os pacotes P44 a P48 foram escritos nessa revisão e ainda não passaram pelas três lentes da etapa 3; a conferência deles acontece na execução, como a de todo pacote.
5. **O que isso garante e o que não garante.** Garante que o escopo, o estado do código e a divisão em pacotes estão conferidos. Não dispensa conferir de novo cada fórmula na imagem na hora de implementar: o protocolo da seção 9 faz isso em todo pacote.

---

**Anexos:**
- [PLANO_IMPLEMENTACAO_NBR6118_2026_MATRIZ.md](PLANO_IMPLEMENTACAO_NBR6118_2026_MATRIZ.md) — uma linha por item da norma, com situação, prioridade e pacote.
- `PLANO_IMPLEMENTACAO_NBR6118_2026_ITENS.json` — os mesmos itens com fórmula transcrita, o que falta, dependências e teste sugerido. É a entrada dos agentes na execução.
