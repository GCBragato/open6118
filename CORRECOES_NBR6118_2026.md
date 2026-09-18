# Correções do open6118 — NBR 6118:2026

- **Data:** 18/09/2026
- **Base:** [AUDITORIA_NBR6118_2026.md](AUDITORIA_NBR6118_2026.md) (73 defeitos confirmados)
- **Norma:** ABNT NBR 6118:2026, 5ª edição. Páginas citadas = página do PDF (a impressa é 18 a menos).
- **Estado:** nada foi commitado. O estado anterior está guardado em [_backup_pre_correcao_2026-09-18/](_backup_pre_correcao_2026-09-18/) (repositório completo, patch das suas alterações locais e o diff das correções).

## 1. Resumo

1. **Os 73 defeitos da auditoria foram corrigidos.** Uma verificação independente, com as mesmas três lentes da auditoria (norma na imagem, execução com script próprio e revisão do diff), confirmou cada um. O resultado está na seção 5.
2. **Apareceram mais 6 problemas durante as correções, e também foram corrigidos.**
   - **PRO-09:** um 0,85 extra na mesa da seção T protendida.
   - **αp(t) na perda progressiva:** a norma usa αp(t) no termo de fluência.
   - **`sec17.py` não carregava:** um import quebrado de `conv_datas`.
   - **Eci do kernel de flexão oblíqua 10× menor:** propriedade sem uso.
   - **`sec9.py`:** `comp_ancor_basico_ativo` devolvia mm com rótulo de cm, e `res_ade_ati` não validava o tipo de fio.
   - **Textos sem acento.**
3. **Há agora um núcleo normativo único:** [dimensionamento/nucleo_nbr6118.py](dimensionamento/nucleo_nbr6118.py).
   - Concentra fct,m, Eci, Ecs, fckj/β1, fcd, ηc, αc, λ, εc2, εcu, n, pivô C, x/d-limite, ρmín (Tabela 17.3), As,mín e As,máx de pilar, η1, η2, η3, fbd, fbpd, τRd, αv2, momento mínimo, cobrimento (Tabela 7.2) e γf3.
   - Todos os módulos delegam a ele. As 11 cópias de fct,m deixaram de existir.
   - Fora da faixa C20–C90, levanta `FaixaNormativaError` em vez de calcular com a fórmula errada.
4. **Grupo II (C55–C90)** passou a ser calculado de verdade em todos os módulos: vigas, lajes, pilares, cortante, torção, ancoragem, fundações, protendido e kernel.
5. **Backend C++ recompilado** com as mesmas correções do Python. A paridade foi medida de C20 a C90, inclusive no domínio 5 e em seção assimétrica: diferença máxima de 1,5·10⁻¹² em 1 800 casos.
6. **Testes:**
   - o pytest foi de **27 para 613** testes, com os valores esperados tirados da norma e não das apostilas;
   - os 10 autotestes de módulo passam;
   - nenhum teste foi afrouxado. Os que mudaram afirmavam o valor errado e agora citam o item da norma.
7. **Achado da própria norma.** De C55 a C90, a Tabela 17.3 foi calculada com o fct,m de 2014 e não foi refeita quando a fórmula mudou em 2023. A definição de 17.3.5.2.1 dá até 1,6 % a mais em C55. As duas vias são normativas, e o núcleo oferece ambas (`rho_min_flexao` e `As_min_flexao_retangular`).

## 2. O que muda para quem usa a biblioteca

Nenhuma assinatura pública quebrou: todo parâmetro novo entrou no fim, com padrão (437 assinaturas comparadas). Mas alguns resultados e comportamentos mudaram, de propósito:

| Onde | O que muda | Por quê |
|---|---|---|
| Todos os módulos | fck fora de 20–90 MPa levanta `FaixaNormativaError` (25 MPa no mínimo com armadura ativa) | 8.2.1 |
| Todos os módulos | Agregado desconhecido em αE levanta erro (antes, caía em silêncio em granito) | 8.2.8 |
| Resultados com fck > 40 | ηc passa a valer: MRd, As e A′s mudam já em C45 e C50 | 8.2.10.1, 17.2.2 e) |
| Resultados com fck > 50 | fct,m, Eci, λ, αc, εcu, pivô C, x/d ≤ 0,35 e ρmín do Grupo II | 8.2.5, 8.2.8, 14.6.4.3, Tab. 17.3 |
| `vigas_bastos` | As entregue ≥ As,mín, com o campo novo `minimo_governou` | 17.3.5.2.1 |
| `viga_servico_bastos.decalagem_modelo_II` | Sem `VSd_kn` e `Vc_kn`, emite aviso e devolve aℓ = d (limite conservador); com eles, aplica a fórmula completa | 17.4.2.3 c) |
| `viga_servico_bastos` | Função nova `sigma_si_estadio_II` | 17.3.3.2 |
| `lajes_bastos` | Função nova `gama_n_laje_balanco`. `momentos_uma_direcao(..., "balanco", h_cm=...)` aplica γn; sem `h_cm`, emite aviso. `dimensionar_flexao(gama_n=...)` | 13.2.4.1, Tab. 13.2 |
| `pilares_bastos` | Md,tot soma o M2d ao M1d,mín; αb = 1,0 abaixo do mínimo; λ > 90 levanta erro | 11.3.3.4.3, 15.8.2 d), 15.8.3.3 |
| `cortante_bastos`, `torcao_bastos` | α fora de 45°–90° e θ fora de 30°–45° levantam erro | 17.4.1.1.5, 17.5.1.1 |
| `ancoragem_bastos`, `sec9` | Traspasse com φ > 32 mm levanta erro | 9.5.2 |
| `sec9` | `comp_ancor_basico` e `comp_ancor_basico_ativo` devolvem **cm**; `res_ade_pass(..., categoria=)`; `comp_transferencia(..., liberacao_gradual=)` | 9.4.2.4, Tab. 8.2, 9.4.5.2 |
| `sapatas_bastos` | `criterio_as_min` (padrão "laje" = 0,67·ρmín; opções "rho_min" e "nenhum"); `secao_critica` ("d" padrão; "d/2" rotulado CEB-70) | 22.6.4.1.3, 19.4.1 |
| `blocos_bastos` | Continua usando Blévot; ganhou fcd1, fcd3, as razões e `ok_bielas_22_3_2` como informação | 22.3.2 |
| `protendido_bastos` | `psi_1000(tipo, relaxação, σpi/fptk)` e `PSI_1000_TIPICOS` com os valores da Tabela 8.3. `phi_eps_cs_NBR` usa t0 e a classe. Função nova `perda_progressiva_simplificada(..., t0_dias=, cimento=, Eci_t0_mpa=)` | 8.4.8, Tab. 8.1, 9.6.3.4.2 |
| Kernel FCO | Sinais de Mx e My respeitados; "OK" só com razão ≥ 1; As,mín de pilar aplicado; `razao_dc_radial` converge em flexão normal | 17.2, 17.3.5.3.1 |
| Kernel FCO | `ei_secante` passa a dar a secante do ponto B (15.3.1); o comportamento antigo é `ponto="Md"` | 15.3.1 |
| Kernel FCO | Módulo novo [verificacao_pilar.py](dimensionamento/rotinas/verificacao_pilar.py) com a envoltória mínima (Figura 11.3, e Figura 15.2 opcional). `verificar_fco` com Md = 0 continua verificando só a seção | 11.3.3.4.3 |
| `fco_dispatch` | Com curva de concreto do usuário, o cálculo cai para o Python com `AvisoNBR6118`, em vez de descartar a curva em silêncio | — |
| `sec17` | `multiplicador_flecha_diferida(..., t0_meses=1)`: padrão de 1 mês, como dizia o comentário (antes era 0,47 fixo). `VRd2` devolve valor e tem o modelo II | 17.3.2.1.2, 17.4.2 |

## 3. Correções, por frente

Valores do exemplo de cada achado, antes → depois. A reprodução completa está na auditoria.

**Frente 1 — núcleo normativo (32 achados)**

| Achado | Antes → depois |
|---|---|
| CRT-01 (C70) | Asw 2,409 → 3,153 cm²/m |
| CRT-02 (C90) | VRd1 337,39 → 243,87 kN |
| CRT-08 (C90) | Asw simplificada 0 → 5,02 cm²/m |
| ANC-07 (C90) | ℓb 25,66 → 30,64 cm |
| ANC-01 (CA-60) | fbd 2,89 → 1,28 MPa |
| LAJ-02 (C70) | Passa a acusar x/d > 0,35 |
| LAJ-05 (C90) | VRd1 231,51 → 167,33 kN/m |
| LAJ-06 (C90) | As,mín 3,12 → 3,84 cm²/m |
| VIG-01 (C50) | A′s 2,08 → 3,54 cm² |
| VIG-03 (C70) | Limite de dutilidade em Md 50 811 → 29 316 kN·cm |
| PRO-05 (C90) | MRd 133 549 → 124 968 kN·cm |
| PRO-06 (C70) | "Dútil" deixa de valer |
| LEG-03 (7 dias) | fcd 21,43 → 14,65 MPa |
| LEG-07b | Patamar de σc 21,43 → 18,21 MPa |

Os demais achados da frente (fct,m, Eci, ηc, η1, fckj e Eci(t) no legado) delegam ao núcleo.

**Frente 2 — kernel de flexão oblíqua e C++ (13 achados, mais a envoltória)**

| Achado | Antes → depois |
|---|---|
| FCO-01 (C50, ν = 0,5) | MRd 24 696 → 22 765 kN·cm |
| FCO-02 (C70) | MRd 23 073 → 14 750 kN·cm (norma: 14 749) |
| FCO-03 (seção assimétrica) | "OK" 2,114 → NAO_VERIFICA 0,378 |
| FCO-09 | As 0,40 → 7,20 cm² |
| FCO-18 | NAO_CONVERGIU → OK |
| FCO-04 (lacuna) | Envoltória mínima implementada: pilar que passava com Md = 0 dá razão 0,340 |

**Frente 3 — pilares**

| Achado | Antes → depois |
|---|---|
| PIL-01 | Md,tot 2 940 → 5 319 kN·cm |
| PIL-02 | 2 940 → 4 461 kN·cm |
| PIL-03 | αb 0,76 → 1,0 |
| PIL-04 | λ = 104 passa a levantar erro |

**Frente 4 — mínimos e limites**

| Achado | Antes → depois |
|---|---|
| VIG-04 | As 0,70 → 1,65 cm² |
| FUN-02 | As_B 16,20 → 18,64 cm² |
| LAJ-07 (h = 12 cm) | Momento de balanço × 1,35 |
| CRT-07 | θ = 15° passa a levantar erro (Asw era 54 % menor) |
| CRT-05 | Mínimo de torção com CA-60: 2,57 → 3,08 cm²/m |
| CRT-06 | he 8,25 → 3,75 cm |
| ANC-08 | φ > 32 passa a levantar erro |
| CRT-03 | α < 45° passa a levantar erro |

**Frente 5 — fórmulas específicas**

| Achado | Antes → depois |
|---|---|
| VIG-05 | aℓ 23 → 46 cm |
| VIG-07 | aℓ 39,8 → 46 cm |
| VIG-06 | aℓ com α = 45°: 34,0 → 22,1 cm |
| PRO-04 | Perda por relaxação 323 → 456 MPa |
| PRO-02 | φ de C60 4,4 → 2,0 |
| PRO-08 | ep_77 do fuso −2,75 → +17,25 cm (e os outros três) |
| PRO-03 | αp com Eci |
| LEG-01 | Cobrimento 22 → 25 mm |
| LEG-09 | αf 1,467 → 1,323 |
| FUN-04 | VSd 1 156 → 938 kN (seção a d) |

**Frente 6 — legado**

| Achado | Antes → depois |
|---|---|
| ANC-02 | ℓb 602,7 → 60,27 cm |
| ANC-03 | Piso de 200 mm aplicado |
| ANC-04 | ℓbpt 22,4 → 62,8 cm |
| ANC-05 | `None` → 5φ |
| ANC-06 | Aceita 'má' |
| LEG-10 | `None` → 549,9 kN |
| LEG-11 | a_c com αc·ηc; C30: As 11,23 → 11,87 cm² |
| LEG-13 | O import não imprime mais "0.1" |

## 4. Suas alterações locais

As alterações não commitadas que você tinha no legado estão preservadas, com duas exceções que a própria correção substituiu:

1. **`flexao_simples.py`, `a_c = 1`.** Agora vem do núcleo (αc·ηc). Era uma regressão contra a segurança.
2. **`conv_unidades.py`, `print` ativo no fim.** Virou comentário.

O `vigas.py` (seu script de estudo) não foi tocado, mas **os resultados dele mudam**: As(h = 50 cm) passa de 169,97 para 176,54 cm² em todas as 19 alturas. A diferença vem só do `a_c = 1`, que era uma regressão. O patch original das suas alterações está em `_backup_pre_correcao_2026-09-18/`.

## 5. Verificação independente das correções

| Lente | Resultado |
|---|---|
| Norma (código × imagem da página) | Tudo confere, inclusive as tabelas transcritas célula a célula (8.1 com 96 valores, 8.3, 17.3, 9.1, 9.2, 7.2). Uma divergência parcial (αp(t) na perda progressiva) foi corrigida em seguida |
| Execução (reprodução de cada achado contra o código corrigido, com scripts próprios e referências independentes, sem usar os testes de quem corrigiu) | **73 corrigidos e 1 parcial, sem nenhum defeito remanescente** (detalhe abaixo) |
| Revisão do diff | Sem regressão: em fck ≤ 40 com momento positivo, diferença máxima de 1·10⁻¹⁵. Nenhum teste afrouxado, nenhuma API quebrada, suas alterações preservadas. Quatro textos sem acento foram corrigidos |

**O item parcial é o CRT-08.**
- A equação simplificada da apostila (`simplificada_modelo_I`) agora cobre o Grupo II. Antes: −13,5 % no C70 e estribo zero no C90.
- Ela ainda fica −0,55 % abaixo do modelo I teórico em C90. Isso é o erro próprio da aproximação da apostila, que já existia em C30 (−0,33 %) e C50 (−0,43 %).
- Quando a precisão importar, use `modelo_calculo_I`, que dá o valor exato da norma.

**Exemplos de apostila (fck ≤ 40), antes × depois.**
- Os exemplos de ancoragem, blocos, cortante, torção e flexão de vigas deram resultado **idêntico, byte a byte**.
- Só mudaram os casos em que um achado exige a mudança:

| Módulo | Exemplo | Antes | Depois | Motivo |
|---|---|---|---|---|
| Pilares | Md,tot (Nd = 1 400 kN, ℓe = 280 cm, h = 20 cm, C30) | 2 940 kN·cm | 5 319 kN·cm | PIL-01 |
| Sapatas | As_B do exemplo da apostila (C25) | 16,21 cm² | 18,64 cm² | FUN-02 |
| Sapatas | VSd_A | 1 156 kN | 938 kN (a d); 1 156 kN só com "d/2" | FUN-04 |
| Vigas (serviço) | aℓ no modelo II (θ = 30°) | 39,84 cm | 46,00 cm | VIG-07 |
| Protendido | Seção T com a LN na nervura (C30) | MRd 148 167 kN·cm | MRd 153 104 kN·cm | PRO-09 |
| Lajes | Balanço L1 | 988,8 kN·cm | igual, com aviso de γn não aplicado | LAJ-07 |

Estado final: **613 testes pytest** passando (eram 27), os 10 autotestes de módulo passando, e `git status` sem nada commitado.

## 6. Atenção

1. **Comparação com o TQS.**
   - A concordância de 98 % do último commit foi calculada só sobre os casos que convergiram, e os uniaxiais ficaram de fora (FCO-18).
   - Com o kernel corrigido, é preciso rodar de novo o `tests/compare_3way_parallel.py`. Dois obstáculos, anteriores a estas correções:
     - nesta máquina, `import tests` resolve para `def_lajes\tests` (há um `.pth` no `sys.path`), e isso quebra os comparadores quando rodam como script;
     - um fck fora de 20–90 no XML do TQS agora interrompe o script, porque o `Concreto(...)` fica fora do `try`.
2. **Duplicações que sobraram, sem defeito de valor:**
   - `viga_servico_bastos.py` ainda tem `alpha_E` e `Eci_mpa` próprios. Os valores estão certos, mas agregado desconhecido cai em 1,0 em vez de dar erro;
   - `lajes_bastos.fyd_kncm2` é local.
3. **O que não foi feito:** as lacunas da seção 7 da auditoria. São recursos que a norma pede e o código não tem, não erros no que existe. É o próximo passo: o plano para implementar o resto da NBR 6118.

## 7. Como revisar e versionar

- **Diff completo:** `_backup_pre_correcao_2026-09-18/correcoes.diff`.
- **Estado anterior:** `_backup_pre_correcao_2026-09-18/repo_completo.tar`. Os `*_bastos.py` não estavam no git, então essa cópia é a única versão anterior deles.
- **Sugestão para commitar:** criar uma branch com dois commits.
  1. O primeiro com os `*_bastos.py` como estavam (a linha de base), para o git mostrar o que mudou neles.
  2. O segundo com as correções.

  Depois disso, a pasta de backup pode ser apagada.
