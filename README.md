# 🚢 CASNAV DMarSup — Sistema de Acompanhamento de Atividades

**Projeto Sistemas Marítimos Não Tripulados | Termo 66/2025**
**Subprojeto: Visão Computacional**

## Visão Geral

App Streamlit para gerenciamento e geração de relatórios de acompanhamento das atividades dos bolsistas do projeto CASNAV DMarSup.

### Decisões de projeto

1. **Nº do Termo é atributo do BOLSISTA**, não do projeto — cada bolsista tem seu próprio Termo de Concessão de Bolsa
2. **Campos pré-preenchidos** — nome, coordenador, mês, período, faixa do cronograma, atividades designadas e dados do último formulário são carregados automaticamente
3. **Histórico para o gerente** — matriz de preenchimento (mês × bolsista), timeline cronológica, gráfico de evolução da curva S por bolsista, e detalhe de cada relatório

### Funcionalidades

- **Dashboard** — Painel com métricas, cronograma Gantt visual e status dos bolsistas
- **Formulário do Bolsista** — Formulário completo (12 seções) aderente ao modelo CASNAV
- **Relatório Individual** — Geração automática em 4 blocos (Técnico, Gantt, Curva S, Resumo)
- **Relatório Unificado** — Consolidação de todos os bolsistas por período
- **Gantt & Cronograma** — Visualização planejado vs. realizado
- **Curva S** — Acompanhamento de avanço físico real
- **Gestão de Bolsistas** — Cadastro e edição de dados
- **Histórico** — Consulta a formulários e relatórios salvos

### Bolsistas

1. Victor
2. Guilherme
3. Gabriel Saad
4. André Ferreira
5. Daniela Lopes Freire
6. Dannylo C. Maurício
7. Wanderson Corrêa

### Cronograma de Atividades (Mês 1 = Agosto/2025)

| Código | Atividade | Meses |
|--------|-----------|-------|
| 3.1 | Incremento do dataset | 1–6 |
| 3.2 | Armazenamento e acesso multiusuário | 7–12 |
| 3.3 | Pesquisa em modelos de redes neurais | 13–18 |
| 3.4 | Solução para estabilização de vídeos | 13–18 |
| 3.5 | Módulo de visão computacional especializado | 19–24 |
| 3.6 | Estimativa de localização de embarcações de superfície | 25–30 |
| 3.7 | Integração de IA/VC ao sistema de monitoramento | 31–36 |

## Instalação e Execução

```bash
pip install -r requirements.txt
streamlit run Principal.py
```

## Estrutura de Dados

```
data/
├── projeto.json        # Dados fixos do projeto e cronograma
├── bolsistas.json      # Cadastro dos bolsistas
└── relatorios/         # Formulários e relatórios salvos (JSON)
```

## Fluxo de Trabalho

1. O coordenador solicita preenchimento dos relatórios
2. Cada bolsista preenche o **Formulário** (aba 📝)
3. Formulários são salvos automaticamente em `data/relatorios/`
4. O coordenador gera **Relatórios Individuais** (aba 📄)
5. Quando todos preencheram, gera o **Relatório Unificado** (aba 📑)
6. Gantt e Curva S são atualizados com os dados reportados

## Coordenação

- **Coordenador:** Leandro Aparecido Simal Moreira
- **Concedente:** Fundação de Estudos do Mar - FEMAR
