# Auditoria do open6118 contra a NBR 6118:2026 — e plano de correção

> **Situação:** os 73 defeitos foram corrigidos em 18/09/2026 — ver [CORRECOES_NBR6118_2026.md](CORRECOES_NBR6118_2026.md). O plano para implementar o resto da norma (seções 7 e 8 abaixo) está em [PLANO_IMPLEMENTACAO_NBR6118_2026.md](PLANO_IMPLEMENTACAO_NBR6118_2026.md).

- **Data:** 18/09/2026
- **Norma:** ABNT NBR 6118:2026, 5ª edição (11/03/2026). Equivale à NBR 6118:2023 Versão Corrigida 2:2024 mais a Emenda 1.
- **Código auditado:** branch `main` no commit `05fa6ce`, mais os arquivos ainda não versionados (`dimensionamento/*_bastos.py`) e as alterações locais não commitadas do legado.
- **Páginas citadas:** sempre a página do PDF. A numeração impressa na norma é 18 a menos.

## 1. Resposta curta

**Sim, há erros, e vários são contra a segurança.** Dos 82 achados, **73 são defeitos confirmados**: 38 graves, 23 médios e 12 leves. Os outros 9 não são defeito: são escolha documentada, lacuna ou alteração local não commitada.

Quase nada disso é erro isolado. São poucas causas, repetidas em muitos arquivos:

1. **Funções de material copiadas em cada módulo.** O fct,m é calculado em 11 lugares, e nenhum usa a fórmula de 2026 para fck > 50 MPa. Nenhum módulo aplica o **ηc** que entrou em 2023 (σc = 0,85·ηc·fcd, com ηc < 1 já a partir de C45). Quase todos aceitam C55 a C90 e calculam como se fosse Grupo I.
2. **Limites da norma que o código calcula e não aplica.** Armadura mínima, γn de laje em balanço, piso do momento mínimo em pilar e faixas de θ e α.
3. **Bugs de código.** Sinal do momento no kernel de flexão oblíqua, pivô C fixo em 3h/7, `return` inalcançável, milímetro tratado como centímetro, equações do fuso limite com sinal trocado.
4. **Testes calibrados nas apostilas, não na norma.** Todos passam hoje (27 do pytest e 128 autotestes dos módulos). Num caso, o teste registra a divergência num comentário e testa outra coisa; noutro, só confere se as chaves do resultado existem.

Os dez piores, pelo efeito medido:

| # | Achado | Efeito medido |
|---|---|---|
| 1 | FCO-01 e FCO-02: kernel de flexão oblíqua sem ηc e com pivô C fixo | MRd superestimado em até **+160 %** (C70) e **+42 %** (C50 com ν = 0,85) |
| 2 | FCO-03: o kernel usa \|Mx\| e \|My\| | seção ou armadura assimétrica sai "OK" com razão 2,11 quando a real é **0,38** |
| 3 | PIL-01 e PIL-02: o momento mínimo não entra no momento total | Md,tot de pilar **34 % a 45 % menor** |
| 4 | VIG-01: armadura dupla sem ηc | A′s **41 % menor** (C50) |
| 5 | CRT-07: θ da torção não é validado | armadura de torção **54 % menor**, sem aviso |
| 6 | FCO-09 e VIG-04: As,mín calculado e não aplicado | pilar com 0,40 cm² onde a norma pede **7,20 cm²**; viga 58 % abaixo do mínimo |
| 7 | PRO-04: Ψ1000 de relaxação normal errados | perda por relaxação **29 % a 42 % menor** |
| 8 | ANC-04 e ANC-01: `sec9.py` | ℓbpt **61 % a 64 % menor**; fbd do CA-60 **2,25 vezes** maior |
| 9 | LAJ-07: laje em balanço sem γn | momento **26 % a 31 % menor** |
| 10 | CRT-02, LAJ-05 e CRT-08: resistência ao cortante sem os limites de fck > 50 | VRd1 **+38 %** em C90; estribo calculado zero em C90 |

O pedido previa: havendo erro, plano de correção; não havendo, plano para implementar o resto da norma. Como há erro, este documento é o plano de correção. O plano para o resto da norma fica para depois (seção 8).

## 2. Como foi verificado

- **Norma.** O texto do PDF foi extraído e cada página, renderizada em imagem. Toda fórmula que sustenta um achado foi conferida na imagem, porque a extração de texto estraga fórmulas. O sumário impresso da norma está defasado de 1 a 3 páginas a partir da seção 6 (texto da Emenda 1 inserido sem atualizar o sumário); as páginas deste documento são as reais.
- **Auditoria.** Nove auditores independentes, um por grupo de módulos, cada um com o texto e as imagens da norma e a obrigação de reproduzir cada achado executando o código.
- **Verificação.** Cada achado passou por três verificadores independentes, cada um com uma lente:
  - **norma:** releu a página e confirmou a fórmula, o valor ou o limite citado;
  - **execução:** reproduziu com script próprio, chamando a função real e recalculando o valor da norma à parte (para o kernel de flexão oblíqua, com um integrador por fibras escrito do zero);
  - **critério:** separou defeito de escolha documentada, de exigência inexistente, de lacuna e de alteração não commitada, e recalibrou a gravidade.
- **Resultado.**
  - Nenhuma afirmação sobre a norma divergiu do texto de 2026.
  - Todas as reproduções se confirmaram; em dois achados o número foi corrigido (CRT-03 e FCO-13).
  - A lente de critério reclassificou 9 achados (seção 6) e encontrou um defeito novo (LEG-07b).
  - Outros três (FCO-18, CRT-08 e VIG-10) apareceram na consolidação e foram confirmados por execução.

**Gravidade:**
- **ALTA:** contra a segurança, ou erro acima de 5 % em caso comum.
- **MÉDIA:** caso menos comum, erro a favor da segurança mas relevante, ou verificação da norma omitida.
- **BAIXA:** divergência pequena ou caso raro.

## 3. Achados, agrupados pela correção

Cada frente reúne os achados que se corrigem juntos. A ordem das frentes é a ordem sugerida de execução (seção 5).

### Frente 1 — Núcleo normativo único (32 achados)

Criar um módulo único com as grandezas de material e os parâmetros da norma, testado contra valores tirados da própria norma. Todos os módulos passam a importar dele em vez de manter cópias locais. Conteúdo mínimo:

- fct,m, fctk,inf, fctk,sup e fctd com os dois ramos de 8.2.5 (até 50 MPa e acima);
- Eci com os dois ramos de 8.2.8 e αE; Ecs com αi(fck); Eci(t);
- fckj com o β1 de 12.3.3 (s = 0,20 para CPV-ARI **e para todo concreto C60 ou superior**), e fcd = fckj/γc quando t < 28 dias;
- ηc, αc(fck) e λ(fck) de 8.2.10.1 e 17.2.2 e); εc2, εcu e n; σc(εc) com 0,85·ηc·fcd no trecho parabólico **e** no patamar; distância do pivô C, igual a (εcu − εc2)·h/εcu;
- limite de x/d de 14.6.4.3: 0,45 até C50 e 0,35 de C55 a C90;
- ρmín da Tabela 17.3 de C20 a C90, com regra explícita para fck intermediário;
- η1 por categoria do aço (Tabela 8.2: CA-25 1,00; CA-50 2,25; **CA-60 1,00**), η2, η3 e fbd;
- τRd de 19.4.1, com fck limitado a 60 MPa;
- validação da faixa 20 ≤ fck ≤ 90 (mínimo 25 com armadura ativa), com erro explícito fora dela.

| ID | Onde | Norma (p.) | O que está errado e efeito medido |
|---|---|---|---|
| CRT-01 · ALTA | `cortante_bastos.py:52` `fctm_mpa` | 8.2.5 (42–43) | sem o ramo de fck > 50. C70: Vc0 +10,5 % e Asw **−23,6 %** |
| CRT-08 · ALTA | `cortante_bastos.py:274` `simplificada_modelo_I` | 8.2.5 | as constantes 0,0137 e 0,023 embutem fck^(2/3). C70: Asw −13,5 %. C90: VSd abaixo do "VSd,mín" e o módulo **não pede estribo além do mínimo** (5,04 cm²/m pela norma) |
| ANC-07 · ALTA | `ancoragem_bastos.py:41` `fctm_mpa` | 8.2.5 | sem o ramo de fck > 50. C90: ℓb **−16,3 %** |
| FUN-03 · ALTA | `sapatas_bastos.py:297` | 8.2.5 | idem. C70: VRd1 +10,5 % |
| PRO-01 · ALTA | `protendido_bastos.py:40` e `:228` | 8.2.5 | idem, também no limite de tração do ELS-F, e a força de protensão estimada sai menor que a necessária |
| LAJ-03 · MÉDIA | `lajes_bastos.py:73` | 8.2.5 | idem, em Mr e em VRd1. C70: +10,5 % |
| VIG-10 · MÉDIA | `viga_servico_bastos.py:184` `fctm_kncm2` | 8.2.5 | idem, em wk2: −9,5 % (C70) e −16,3 % (C90); muda o wk quando wk2 governa |
| CRT-04 · MÉDIA | `torcao_bastos.py:38` | 8.2.5 | idem, nos mínimos de torção: +10,5 % (a favor da segurança) |
| LEG-04 · BAIXA | `sec8.py:74` `fct_m_F` | 8.2.5 | usa 2,12·ln(1 + 0,11 fck), fórmula de 2014: −1,75 % a +0,4 % (é o mesmo que ANC-09) |
| LAJ-04 · MÉDIA | `lajes_bastos.py:82` `Ecs_kncm2` | 8.2.8 (44) | Eci sem o ramo de fck > 50: Ecs +7,9 % (C70) e +13,8 % (C90) |
| FCO-14 · BAIXA | `flexao_composta_obliqua.py:182–196` | 8.2.5, 8.2.8 | Eci sem o ramo de fck > 50 e fct de 2014 (propriedades sem uso hoje) |
| CRT-02 · ALTA | `cortante_bastos.py:352` `laje_sem_armadura` | 19.4.1 (181) | τRd sem o teto de fck = 60 MPa. C90: VRd1 **+38 %** |
| LAJ-05 · ALTA | `lajes_bastos.py:614` | 19.4.1 | idem: +17 % (C70) e **+38 %** (C90) |
| LEG-07 · ALTA | `sec8.py:144` `o_c_de_Eps_c` | Fig. 8.2 (45) | sem ηc. C60: σc +14,5 % |
| LEG-07b · ALTA | `sec8.py:145` | Fig. 8.2 | o patamar devolve fcd em vez de 0,85·fcd: **+17,6 % para qualquer fck** (a tensão salta em εc2) |
| VIG-01 · ALTA | `vigas_bastos.py:223` `secao_retangular_dupla` | 17.2.2 e) (141) | sem ηc; com x fixo, o erro se concentra em A′s: **−41 %** (C50) |
| VIG-02 · MÉDIA | `vigas_bastos.py:153` e `:369` | 17.2.2 e) | sem ηc nas seções simples e T. C50 com x/d = 0,45: As −2,2 % |
| LAJ-01 · BAIXA | `lajes_bastos.py:571` | 17.2.2 e) | sem ηc. C50: As −0,7 % |
| LEG-11b · BAIXA | `flexao_simples.py:21` (versão commitada) | 17.2.2 e) | sem ηc. C45 e C50: As −0,6 % a −1,4 %; o erro cresce acima de C50 |
| VIG-03 · ALTA | `vigas_bastos.py` (módulo inteiro) | 17.2.2 e), 14.6.4.3, Tab. 17.3 | declara Grupo I, mas aceita fck > 50 e calcula com λ = 0,8, 0,85·fcd, x/d ≤ 0,45 e o ρmín do C50. Em C70, aceita Md **73 % acima** do limite de dutilidade |
| PRO-05 · ALTA | `protendido_bastos.py:375` e `:525` | 17.2.2 e) | λ, αc e ηc fixos: MRd +6,9 % (C90) e +4,7 % (C70) |
| LAJ-02 · ALTA | `lajes_bastos.py:52` e `:584` | 14.6.4.3 (112) | x/d ≤ 0,45 para qualquer fck (a norma pede 0,35 acima de C50) |
| PRO-06 · ALTA | `protendido_bastos.py:406` e `:572` | 14.6.4.3 | idem: marca como "dútil" o que a norma não aceita |
| LAJ-06 · ALTA | `lajes_bastos.py:56` e `:126` | Tab. 17.3 (151) | ρmín só até C50; acima disso cai no valor do C50: **−18,75 %** em C90 |
| VIG-08 · BAIXA | `vigas_bastos.py:50` e `:96` | Tab. 17.3 | fck fora dos múltiplos de 5 cai no valor do C50 (a favor da segurança) |
| ANC-01 · ALTA | `sec9.py:35` `res_ade_pass` | Tab. 8.2 (48) | η1 pela superfície da barra (regra de 2014): o CA-60 sai com fbd **2,25 vezes** maior e ℓb 56 % menor |
| LEG-08 · MÉDIA | `sec8.py:176` `n_1_F` | Tab. 8.2 | o mesmo erro de η1 (sem uso hoje) |
| LEG-03 · ALTA | `sec8.py:107` `fcd_F` | 12.3.3 b) (90) | com t < 28 dias, usa fck em vez de fckj: fcd **+46 %** aos 7 dias |
| LEG-02 · MÉDIA | `sec8.py:54` `fck_j_F` | 12.3.3 (91) | ignora s = 0,20 para C60 ou mais: fckj −16,5 % (a favor da segurança) |
| LEG-05 · MÉDIA | `sec8.py:96` `E_ci_F` | 8.2.8 (44) | efeito da idade aplicado duas vezes: −17 % aos 7 dias |
| LEG-06 · BAIXA | `sec8.py:103` `E_cs_F` | 8.2.8 | αi calculado com fckj: −2,7 % aos 7 dias |
| FCO-13 · BAIXA | `flexao_composta_obliqua.py:162` | 8.2.1 (41–42) | aceita fck fora de 20 a 90 MPa sem erro |

### Frente 2 — Kernel de flexão composta oblíqua, Python e C++ (13 achados)

É o conjunto de maior efeito numérico. Os quatro primeiros mudam o "passa" ou "não passa" de pilares reais.

| ID | Onde | Norma (p.) | O que está errado e efeito medido |
|---|---|---|---|
| FCO-01 · ALTA | `flexao_composta_obliqua.py:51, 82–129, 1103, 1592`; `constitutive.h:5`, `constitutive.cpp:52` e `:56`, `verifier.cpp:11` | Fig. 8.2 (45), 17.2.2 e) (141) | pico de 0,85·fcd sem ηc em todo o ELU, nos dois backends. C50: MRd **+8,5 %** (ν = 0,5) e **+42 %** (ν = 0,85). Nd,máx +7,1 %: aprova Nd 6 % acima do limite |
| FCO-02 · ALTA | `:604–606` `_strain`; `constitutive.cpp:40–41` | Fig. 17.1 (142) | pivô C fixo em 3h/7, que só vale até C50. Sozinho: +40 % (C70, ν = 0,85). Somado ao FCO-01: **+56 % a +160 %** (C70) |
| FCO-03 · ALTA | `:1171–1287`, `:1382`, `:1697–1730`; `verifier.cpp:74–81` | 17.2.1, 17.2.2 | usa \|Mx\| e \|My\| e comprime sempre o mesmo quadrante. Armadura assimétrica: "OK" com 2,11 quando a real é **0,38**. Seção L girada: "OK" com 1,50 quando a real é 0,71 |
| FCO-09 · ALTA | `:1515` e `:1539–1549` `dimensionar_as_fco`, e `flexao_composta_normal.py:56` | 17.3.5.3.1 (153) | As,mín fixo em 0,4 cm². Pilar 30×60 com Nd = 300 kN: **0,40 cm²**, quando a norma pede **7,20 cm²** |
| FCO-05 · MÉDIA | `:1100–1103`, `:1593`; `verifier.cpp:9–12` | Fig. 17.1 (reta b), 8.3.6 | Nd,máx calculado com fyd em vez de σs(εc2): +0,8 % (CA-50) a +12 % (CA-60, ρ = 4 %). O pré-teste aprova e o solver quebra |
| FCO-06 · MÉDIA | `:1580–1599` | 17.2.4.2.1 (143) | Nd,máx e Nd,mín da seção poligonal ignoram os cabos: +10 % |
| FCO-07 · MÉDIA | `constitutive.cpp:49` | Fig. 8.2 | o C++ zera σ além de εcu e o Python não; a paridade só vale até C50. C60: −23 %. C90: não converge |
| FCO-08 · MÉDIA | `fco_dispatch.py:48–49` | — | o dispatcher descarta, sem aviso, a curva de concreto que o usuário passou (+8,5 % no exemplo) |
| FCO-10 · MÉDIA | `:994–1027` `ei_secante` | 15.3.1, Fig. 15.1 (121) | usa a curva de ELU em vez de pico 1,10·fcd e NRd/γf3: EI −20 % (a favor da segurança) |
| FCO-18 · MÉDIA | `razao_dc_radial` | — | não converge em flexão normal (Mx ou My nulo). É a função usada pelos comparadores com o TQS, e a concordância de 98 % do último commit é calculada só sobre os casos que convergiram: os uniaxiais ficaram fora |
| FCO-11 · BAIXA | `:1226, 1303, 1703, 1720, 1741`; `verifier.cpp:30` e `:88` | 17.2.1 | aprova com razão a partir de 0,99, ou seja, aceita 1 % de déficit |
| FCO-15 · BAIXA | `:790–792` | 17.2.2 a) | seção com mais de um fck ganha um plano de deformação por parte: +2,4 % |
| FCO-16 · BAIXA | `:545–581`; `geometry.cpp:26–27` | Fig. 17.1 | o pivô A ignora os cabos; sem barras passivas, usa d = 1 cm |

Corrigir primeiro no Python, usando o integrador de referência como teste. Depois, portar para o C++ ou rotear para o Python (decisão 7).

### Frente 3 — Pilares: momento total e momento mínimo (4 achados)

| ID | Onde | Norma (p.) | O que está errado e efeito medido |
|---|---|---|---|
| PIL-01 · ALTA | `pilares_bastos.py:143` `Mdtot_curvatura_aprox` | 15.8.3.3.2 (129), 11.3.3.4.3 (80) | M1d,A não é elevado ao M1d,mín antes da soma; com M1d,A < M1d,mín, o M2d some. Nd = 1 400 kN, ℓe = 280 cm, h = 20 cm: Md,tot de 2 940 kN·cm, quando a norma pede **5 319** (−45 %). O teste `test_Mdtot_curvatura_apostila` registra a divergência num comentário e testa outra coisa |
| PIL-02 · ALTA | `:180` `Mdtot_rigidez_aprox` | 15.8.3.3.3 (130) | a mesma falha no método da rigidez: 2 940 kN·cm, quando a norma pede **4 461** (−34 %) |
| PIL-03 · ALTA | `:57–69` `alpha_b` | 15.8.2 d) (128) | não força αb = 1,0 quando os momentos são menores que o mínimo: devolve 0,76 |
| PIL-04 · MÉDIA | `:126–192` | 15.8.3.3.2 e 15.8.3.3.3 (129–130), 15.8.4 (131) | não valida λ ≤ 90 nem exige fluência acima disso: devolve resultado para λ = 104 |

Correção:
- usar `M1d_A_ef = max(M1d_A, M1d_min)` na soma e no piso final;
- `alpha_b` passa a receber M1d,mín;
- levantar exceção para λ > 90.

A envoltória mínima de flexão oblíqua (lacuna FCO-04, seção 6) entra aqui: uma função de verificação de pilar monta a envoltória da Figura 11.3 e chama o kernel de flexão oblíqua.

### Frente 4 — Mínimos e limites que o código não aplica (8 achados)

| ID | Onde | Norma (p.) | O que está errado e efeito medido | Correção |
|---|---|---|---|---|
| VIG-04 · ALTA | `vigas_bastos.py:176` e `:188` | 17.3.5.2.1 (151) | calcula As,mín, mas devolve o As de equilíbrio: 0,70 cm², com mínimo de **1,65 cm²**, sem aviso | `As = max(As, As_min)` nas três funções |
| FUN-02 · ALTA | `sapatas_bastos.py:108` | 22.6, 17.3.5.2.1, Tab. 19.1 | sapata sem armadura mínima: 16,21 cm², para um mínimo de 18,64 cm² (0,67·ρmín) ou 27,83 cm² (ρmín cheio) | aplicar mínimo; o critério é a decisão 2 |
| LAJ-07 · ALTA | `lajes_bastos.py:417` | 13.2.4.1, Tab. 13.2 (94) | laje em balanço sem γn = 1,95 − 0,05h: momento **−26 %** (h = 12 cm) a **−31 %** (h = 10 cm) | aplicar γn a M e V de todo balanço com h < 19 cm |
| CRT-07 · ALTA | `torcao_bastos.py:85–199` | 17.5.1.1 (159) | aceita θ fora de 30° a 45°: com 15°, Asw **−54 %**, sem aviso | validar θ nas quatro funções |
| CRT-05 · MÉDIA | `torcao_bastos.py:124–137` | 17.5.1.2 (159–160) | não limita fywk a 500 MPa no mínimo de torção: −17 % com CA-60 | usar `min(fywk, 500)` |
| CRT-06 · MÉDIA | `torcao_bastos.py:54–79` | 17.5.1.4.1 (160–161) | quando A/u < 2c1, adota he = 2c1 (a norma manda he = A/u ≤ bw − 2c1): 8,25 cm contra 3,75 cm | seguir a exceção da norma |
| ANC-08 · MÉDIA | `sec9.py:236` e `:262`; `ancoragem_bastos.py:199` e `:226` | 9.5.2 (62) | calcula traspasse para φ > 32 mm, que a norma proíbe | erro explícito para φ > 32 mm |
| CRT-03 · BAIXA | `cortante_bastos.py:125` `modelo_calculo_I` | 17.4.1.1.5 (155) | não valida 45° ≤ α ≤ 90° (o modelo II valida): +3,5 % | a mesma validação do modelo II |

### Frente 5 — Fórmulas específicas erradas (10 achados)

| ID | Onde | Norma (p.) | O que está errado e efeito medido | Correção |
|---|---|---|---|---|
| VIG-05 · ALTA | `viga_servico_bastos.py:151` `decalagem_modelo_I` | 17.4.2.2 c) (158) | com \|VSd\| ≤ \|Vc\|, devolve aℓ = 0,5d; a norma manda aℓ = d: **−50 %** | devolver d |
| VIG-07 · ALTA | `viga_servico_bastos.py:157` `decalagem_modelo_II` | 17.4.2.3 c) (159) | ignora Vc (que é Vc1 na flexão simples), o que sempre subestima aℓ: −13 % | receber Vc e usar a fórmula completa |
| VIG-06 · MÉDIA | `viga_servico_bastos.py:144` | 17.4.2.2 c) | recebe `alfa_deg` e não usa; nem sempre fica a favor da segurança | aplicar cotg α |
| PRO-04 · ALTA | `protendido_bastos.py:132` `PSI_1000_TIPICOS` | 8.4.8, Tab. 8.3 (51) | Ψ1000 de relaxação normal errados. Pela norma: cordoalha RN 12,0 %, fio RN 8,5 %, cordoalha RB 3,5 %, fio RB 3,0 %. Perda por relaxação **29 % a 42 % menor** | usar os quatro valores da Tabela 8.3, por tipo (fio ou cordoalha) e não por classe comercial |
| PRO-02 · ALTA | `protendido_bastos.py:487–513` | 8.2.11, Tab. 8.1 (47) | ignora t0 e a classe do concreto (C20–C45 × C50–C90): φ **+29 %** (C20–C45) a **+120 %** (C50–C90); εcs 20 % menor | refazer a tabela com os eixos fck e t0 |
| PRO-08 · ALTA | `protendido_bastos.py:580` `fuso_limite_excentricidade` | apostila (não é item da norma) | as quatro equações de ep têm sinal trocado e nenhuma reproduz a tensão-alvo. O teste só confere as chaves do dicionário | re-derivar a partir de `sigma_base_topo` e testar realimentando o ep |
| PRO-03 · MÉDIA | `protendido_bastos.py:166`, `:185` e `:420` | 9.1 (52), 9.6.3.3.2.1, 9.6.3.4.2 | αp = Ep/Ecs, mas a norma define αp = Ep/Eci: perdas +8 % a +14 % (a favor da segurança) | trocar Ecs por Eci |
| LEG-01 · ALTA | `sec7.py:28` | Tab. 7.2 (39) | cobrimento de viga e pilar em CAA I = 22 mm; a norma pede 25 mm | corrigir o valor |
| LEG-09 · MÉDIA | `sec17.py:26` | 17.3.2.1.2 (148) | t0 fixo em 0,47 mês (o comentário diz 1 mês), quando t0 é dado do projeto: αf +11 % (a favor da segurança) | t0 como parâmetro |
| FUN-04 · MÉDIA | `sapatas_bastos.py:287` | 19.4.1 (181) | verifica o cortante a d/2 da face e atribui isso ao 19.4.1, que manda a d: VSd +23 % (a favor da segurança) | decisão 3 |

### Frente 6 — Código legado: `secoes_norma/`, `flexao_simples.py` e `vigas.py` (6 achados)

O legado tem os bugs mais grosseiros, e para quase tudo já existe um módulo novo que faz certo: `ancoragem_bastos.py` no lugar de `sec9.py`, `cortante_bastos.py` no lugar de `sec17.VRd2`. Nenhum módulo novo importa o legado; só o `vigas.py` o usa.

| ID | Onde | Norma (p.) | O que está errado |
|---|---|---|---|
| ANC-02 · ALTA | `sec9.py:106–136` | 9.4.2.4 e 9.4.2.5 (57) | ℓb sai em milímetros com rótulo de centímetros (fator 10), e o piso é 10 em vez de 100 mm: −32 % |
| ANC-03 · ALTA | `sec9.py:236–273` | 9.5.2.2.1, 9.5.2.3 (63) | piso de traspasse de 20 em vez de 200 mm: −9,6 % |
| ANC-04 · ALTA | `sec9.py:163–182` | 9.4.5.2 (59) | ℓbpt calculado com os coeficientes de ℓbp (1/4 e 7/36 em vez de 0,7 e 0,5): **−61 % a −64 %**; falta o ×1,25 da liberação súbita |
| ANC-05 · ALTA | `sec9.py:80–103` e `:201–229` | Tab. 9.1 e 9.2 | `return` inalcançável: as duas funções de pino de dobramento sempre devolvem `None` |
| ANC-06 · MÉDIA | `sec9.py:46` e `:69` | 9.3.2.1 | aceita "ma", mas a docstring manda "má", e "má" dá `TypeError` |
| LEG-10 · BAIXA | `sec17.py:67–78` `VRd2` | 17.4.2.2 (156–157) | sem `return`: sempre `None`; sem modelo II; ninguém usa |

Também são do legado ANC-01, LEG-02 a LEG-08 e LEG-11b (na Frente 1) e LEG-01 e LEG-09 (na Frente 5). A recomendação está na decisão 5.

**Alterações locais não commitadas no legado** (feitas entre 2024 e 2025):
- `flexao_simples.py` troca `a_c = 0.85` por `a_c = 1`. É uma regressão: As de −5 % a −8 %.
- `conv_unidades.py` ficou com um `print` ativo, que imprime "0.1" a cada import.
- `vigas.py` virou script de estudo.

Ver decisão 6.

### Frente 7 — Testes contra a norma

1. Cada reprodução deste documento vira um teste, com o valor da norma (não o da apostila) como esperado.
2. Corrigir os testes que desviam do problema: `test_Mdtot_curvatura_apostila` (pilares), `test_fuso_limite_basico` (protendido, que só confere chaves) e a decalagem com \|VSd\| ≤ \|Vc\|, que hoje não tem teste.
3. Varredura de classes em toda função pública que recebe fck: C20, C40, C45, C50, C55, C70 e C90.
4. No kernel de flexão oblíqua:
   - usar um integrador por fibras independente como oráculo;
   - testar seção e armadura assimétricas;
   - medir a paridade Python × C++ de C20 a C90, inclusive no domínio 5.
5. Rodar de novo o comparador com o TQS depois das Frentes 2 e 3, já incluindo os casos uniaxiais (FCO-18).

## 4. Decisões que são suas

Cada uma traz a minha recomendação. O plano funciona com os padrões recomendados; mudar qualquer um só altera o item correspondente.

1. **Blocos: Blévot ou 22.3.2 (FUN-01).** No nó do pilar, os limites de Blévot (1,4 a 2,6·KR·fcd) ficam de 1,7 a 3,2 vezes acima de fcd1 = 0,85·αv2·fcd da 22.3.2. A 22.7.3 aceita modelos de biela e tirante e não cita Blévot. *Recomendo* manter Blévot como critério principal, deixar escrito que esse limite não é da NBR e mostrar a verificação da 22.3.2 ao lado, como informação.
2. **Armadura mínima em sapatas (FUN-02).** A seção 22.6 não traz uma taxa própria, e a sapata flexível remete a lajes. *Recomendo* um parâmetro com padrão 0,67·ρmín (Tabela 19.1, laje armada em duas direções) e a opção de ρmín cheio (Tabela 17.3).
3. **Cortante em sapata flexível: seção a d ou a d/2 (FUN-04).** *Recomendo* a seção a d (19.4.1), com o VRd1 da norma. A d/2, só se o método inteiro for o do CEB-70, e dito explicitamente.
4. **Grupo II (C55 a C90) em vigas, lajes e protendido.** *Recomendo* implementar em vez de recusar. Com o núcleo da Frente 1, o custo é pequeno.
5. **Legado.** *Recomendo* aposentar `sec8.py`, `sec9.py`, `sec17.py`, `flexao_simples.py` e `vigas.py`, ou transformá-los em fachadas finas sobre os módulos novos. A tabela de cobrimento do `sec7.py`, já corrigida, vai para o núcleo.
6. **Alterações locais não commitadas no legado.** *Recomendo* descartar. Se o `vigas.py` como script de estudo tiver valor, guarde-o fora da biblioteca.
7. **Backend C++.** Hoje ele reproduz o Python só até C50 e só com a curva padrão. *Recomendo* que o dispatcher use o Python sempre que o caso não tiver paridade medida (fck > 40, curva do usuário, seção poligonal), até as correções serem portadas.
8. **Onde fica o momento mínimo (FCO-04).** *Recomendo* que o kernel de flexão oblíqua continue verificando só a seção, e que uma função de pilar monte a envoltória mínima (Figura 11.3) e chame o kernel.
9. **g = 10 nas conversões (LEG-12).** O `conv_unidades.py` usa 1 tf = 10 kN. *Recomendo* manter, se for convenção do escritório, mas documentar no módulo.
10. **Versionamento.** Todos os `*_bastos.py` estão fora do git. *Recomendo* commitá-los como estão, antes de corrigir, para que cada correção vire um diff revisável.

## 5. Ordem de execução

1. **Linha de base no git.** Commitar os `*_bastos.py` como estão e resolver as alterações locais do legado (decisão 6).
2. **Núcleo normativo (Frente 1),** com testes tirados da norma. Está pronto quando os valores das Tabelas 8.2, 8.3 e 17.3 e as fórmulas de 8.2.5, 8.2.8, 8.2.10.1, 12.3.3, 14.6.4.3 e 17.2.2 e) baterem de C20 a C90.
3. **Migrar os módulos para o núcleo.** Apagar as cópias locais de cortante, torção, ancoragem, lajes, vigas, serviço, protendido, sapatas, blocos e flexão oblíqua. Os 32 achados da Frente 1 se fecham aqui.
4. **Kernel de flexão oblíqua em Python (Frente 2):** ηc, pivô C, sinal, As,mín, Nd,máx, cabos e `razao_dc_radial`. Está pronto quando bater com o integrador independente em C30, C50, C70 e C90 e na seção assimétrica.
5. **Pilares (Frente 3):** momento total, αb, λ ≤ 90 e envoltória mínima.
6. **Mínimos e limites (Frente 4).**
7. **Fórmulas específicas (Frente 5):** decalagem, protensão, cobrimento e t0.
8. **Backend C++:** portar as correções da etapa 4 ou rotear para o Python (decisão 7).
9. **Legado (Frente 6):** aposentar ou reduzir a fachada (decisão 5).
10. **Comparação com o TQS:** rodar de novo o `compare_3way_parallel.py`. A concordância de 98 % precisa ser medida outra vez, com as correções e com os casos uniaxiais.

A Frente 7 (testes) acompanha todas as etapas: nenhuma correção entra sem o teste que a prova contra a norma.

## 6. O que não é defeito

| ID | Classificação | Por quê |
|---|---|---|
| FUN-01 | escolha documentada | Blévot está declarado no módulo, e a 22.7 não impõe a 22.3.2 (decisão 1) |
| FCO-12 | escolha documentada | os expoentes de 1,2 a 2,0 estão rotulados como Bresler/CEB; a 17.2.5 só prevê 1 e 1,2. Falta avisar quando o valor sai disso |
| FCO-17 | escolha documentada | o patamar do aço de protensão está declarado e fica a favor da segurança (a norma tem ramo inclinado até fptd) |
| VIG-09 | escolha documentada | σsi "aproximada", com braço de 0,85d, está rotulada e fica a favor da segurança (+12 %). Melhoria possível: usar o estádio II que o próprio módulo já calcula |
| FCO-04 | lacuna | a envoltória mínima de 11.3.3.4.3 não existe em nenhum módulo (Frente 3) |
| PRO-07 | lacuna **perigosa** | não há função de perda progressiva combinada (9.6.3.4.2). O único caminho hoje é somar as três parcelas do módulo, o que dá +41 % no exemplo |
| LEG-11a | não commitado | `a_c = 1` só existe no disco |
| LEG-13 | não commitado | o `print` ativo só existe no disco |
| LEG-12 | não exigido | 1 tf = 10 kN é convenção; a norma não trata disso (decisão 9) |

## 7. Lacunas registradas

Coisas que a norma pede e o módulo ainda não cobre, dentro do escopo de cada um. Não são erros no que já existe.

- **Pilares:**
  - dimensões mínimas e γn (13.2.3, Tabela 13.1);
  - limite λ ≤ 200;
  - método geral e pilar-padrão com M-N-1/r (15.8.3.2, 15.8.3.3.4);
  - fluência (15.8.4);
  - armadura mínima e máxima de pilar (17.3.5.3);
  - diâmetros (18.4.2).
- **Cortante e torção:**
  - Vc em flexo-compressão;
  - redução de VSd para carga junto ao apoio (17.4.1.2.1);
  - detalhamento de estribos (18.3.3, 18.3.4);
  - seções compostas e vazadas (17.5.1.4.2 e 17.5.1.4.3);
  - flexão com torção (17.7.1).
- **Ancoragem:**
  - fator 1,75 de 9.3.2.3;
  - feixes, telas e dispositivos mecânicos (9.4.3, 9.4.4, 9.4.7);
  - limites da Tabela 9.3;
  - armadura transversal nas emendas (9.5.2.4);
  - luvas e solda (9.5.3, 9.5.4).
- **Vigas:**
  - armadura de pele (17.3.5.2.3, 18.3.5);
  - As + A′s ≤ 4 % de Ac;
  - aplicação de aℓ no corte de barras (18.3.2.3.1);
  - wk,máx pela classe de agressividade (Tabela 13.4);
  - flecha.
- **Lajes:**
  - espessuras mínimas (13.2.4.1);
  - rigidez de Branson e estádio (17.3.2.1.1);
  - limites de deslocamento (13.3);
  - armadura secundária e detalhamento (Tabela 19.1, 20.1);
  - punção (19.5).
- **Protendido:**
  - limites de σpi e Pd,t (9.6.1);
  - ℓp (9.6.2.3);
  - perda progressiva combinada e método geral (9.6.3.4);
  - ELU no ato da protensão (17.2.4.3);
  - ELS-W.
- **Fundações:**
  - redução da força de punção pela reação do solo (19.5.2.1);
  - superfície C′ em sapata flexível (19.5.3.2);
  - pilar de borda e de canto;
  - fendilhamento (21.2);
  - ancoragem das estacas tracionadas.
- **Kernel de flexão oblíqua:**
  - domínio 1 (tração excêntrica);
  - armadura ativa não aderente;
  - ELS com estádios I e II normativos.

## 8. Próximo passo

Com as correções encaminhadas, faço o plano para implementar o resto da NBR 6118, que era o pedido para o caso de não haver erros. O núcleo da Frente 1 também é a base desse plano.
