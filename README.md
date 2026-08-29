# Mecanicar - Sistema Integrado de Gestao Automotiva (Fase 1)

O Mecanicar e um ecossistema digital corporativo desenvolvido sob medida para uma oficina mecanica de medio porte situada no interior paulista. O projeto engloba desde a descoberta tatica de dominio ate a implementacao de um ecossistema robusto, seguro, testado e de facil inicializacao conteinerizada.

Este documento narra a jornada completa de concepcao, modelagem, desenvolvimento seguro e operacionalizacao da plataforma, estruturada como uma narrativa fluida de transformacao operacional e excelencia tecnica.

---

## 1. A Jornada Domain-Driven Design (DDD) e Discovery

### O Comeco: Alinhamento e Descobrimento de Dominio
Para lidar com a complexidade de gerenciar uma oficina em franca expansao (patio, estoque, faturamento, clientes e mecanicos), adotamos o Domain-Driven Design (DDD) como filosofia metodologica desde o primeiro dia de concepcao do projeto. O objetivo inicial foi derrubar as barreiras de comunicacao entre o time de desenvolvimento e os especialistas de negocio da Mecanicar. 

Por meio de sessoes colaborativas de **Event Storming**, mapeamos toda a linha do tempo operacional da oficina, identificando como os eventos do mundo real direcionam os fluxos internos de trabalho.

### A Jornada do Veiculo (Storytelling de Dominio)
A vida operacional da Mecanicar comeca quando um cliente traz seu veiculo para a oficina. A recepcao registra a entrada do veiculo, disparando o evento **Ordem de Servico Recebida**. Nesse momento, a Ordem de Servico (OS) - que e o nosso Core Domain e Agregado Principal - e instanciada no status inicial de `RECEBIDA`.

A partir desse ponto, o fluxo do patio se divide em duas esteiras de trabalho:
- **Fluxo Normal:** O veiculo e direcionado para a baia tecnica de um mecanico, que inicia a inspecao (evento **Diagnostico Iniciado**, status `EM_DIAGNOSTICO`). Ao concluir a analise, o mecanico gera o laudo tecnico e lista as pecas de estoque e as maos de obra necessarias (evento **Diagnostico Concluido**). O status da OS e transicionado para `AGUARDANDO_APROVACAO`, e um link seguro contendo um hash criptografico e enviado ao cliente por WhatsApp.
- **Fluxo Expresso:** Caso o cliente solicite um servico rapido de prateleira cadastrado no catalogo (como troca de oleo ou alinhamento rapido), a etapa de diagnostico fisico e totalmente pulada. A OS e direcionada imediatamente para o status de `AGUARDANDO_APROVACAO` com as pecas e maos de obra do servico expresso ja acopladas.

Em ambos os fluxos, o cliente recebe o orcamento de forma autonoma e toma sua decisao diretamente pelo portal publico:
- **Se Aprovado:** O evento **Orcamento Aprovado** e disparado. O sistema adquire um bloqueio sobre o inventario do estoque, decrementa as quantidades fisicas de pecas e lanca a OS para o status de `EM_EXECUCAO`, onde o mecanico inicia o trabalho fisico. Ao finalizar todas as atividades, o status move-se para `FINALIZADA`.
- **Se Rejeitado:** O evento **Orcamento Rejeitado** e disparado, e a OS e transicionada de forma terminal para o status de `CANCELADA`.

A jornada termina com o faturamento e a retirada fisica do veiculo pelo cliente (evento **Veiculo Entregue**, status `ENTREGUE`), concluindo o ciclo operacional de forma integrada.

### Contextos Delimitados (Bounded Contexts)
Para garantir alta coesao e limites de responsabilidade limpos, o ecossistema foi mapeado em contextos delimitados com fronteiras bem definidas:
1. **Autenticacao e Seguranca (IAM):** Controle de credenciais, geracao de sessoes JWT de rotacao rapida (RTR) e atribuicao de papeis de acesso (RBAC).
2. **Clientes e Frota:** Gestao cadastral de clientes (Pessoa Fisica e Juridica) e seus veiculos utilizando Value Objects estruturados.
3. **Ordens de Servico (Core Domain):** Agregado principal que gerencia a maquina de estados fisica do veiculo no patio, as transicoes e o historico de status de auditoria.
4. **Estoque e Inventario:** Catalogo de insumos e controle de saldos fisicos com politicas de alerta de estoque baixo.
5. **Catalogo de Servicos:** Maos de obra autorizadas e tempos padrao de execucao.

---

## 2. Desafios Operacionais e Solucoes sob a Otica de Negocio

O desenvolvimento do Mecanicar foi guiado pelo compromisso de sanar as dores reais do cotidiano da oficina. Antes de qualquer detalhe tecnico, cada desafio do Tech Challenge foi analisado e resolvido sob a otica de processos e regras de negocio, criando um fluxo operacional harmonioso e eficiente.

### • Erros na Priorizacao dos Atendimentos
- **O Problema de Negocio:** Carros acumulados no patio, ociosidade de mecanicos seniores em tarefas simples de rotina e atrasos nas entregas devido a falta de triagem inteligente.
- **A Solucao de Negocio:** Dividimos a operacao do patio em duas vias de atendimento. Criamos o conceito de **Servico Expresso** para manutenções preventivas de catalogo (como troca de óleo). Quando um cliente chega para um servico expresso, ele pula a baia de diagnostico e vai direto para a fila de execucao rapida, liberando os especialistas de patio para focar em inspeções fisicas complexas de veiculos que realmente demandam investigacao tecnica.

### • Falhas no Controle de Pecas e Insumos
- **O Problema de Negocio:** Inconsistencia de estoque (vender pecas fisicamente inexistentes ao cliente) e prejuizo financeiro por reajustes de preços ocorridos entre o momento do diagnostico e o faturamento final da OS.
- **A Solucao de Negocio:** Estabelecemos uma regra rigida de **reserva imediata e congelamento de valores**. No instante em que o diagnostico e gerado, as pecas necessarias ficam vinculadas de forma estatica ao orcamento com o valor comercial daquele momento. Mudancas na tabela geral de precos da oficina nao afetam contratos antigos ja emitidos ou em execucao, garantindo previsibilidade para o cliente e protegendo as margens financeiras acordadas.

### • Dificuldade em Acompanhar o Status dos Servicos
- **O Problema de Negocio:** Ansiedade do cliente ligando constantemente para a recepcao pedindo atualizacoes, o que sobrecarrega a equipe administrativa e gera gargalo de atendimento.
- **A Solucao de Negocio:** Criamos uma **Politica Ativa de Notificacao**. O cliente deixa de ser um agente passivo e passa a ser notificado de forma proativa via WhatsApp em duas etapas cruciais da jornada: quando o diagnostico fisico e concluido (com o link de aprovacao do orcamento) e no instante em que o mecanico finaliza a manutencao e o carro esta limpo e pronto para retirada.

### • Perda de Historico de Clientes e Veiculos
- **O Problema de Negocio:** Exclusoes acidentais de registros de clientes ou veiculos antigos por operadores do caixa, resultando na perda de dados historicos de faturamento e quebra de garantia de servicos prestados.
- **A Solucao de Negocio:** Adotamos a politica de **Inativacao Cadastral e Preservacao Historica**. Nenhuma entidade comercial ou administrativa e excluida permanentemente do sistema. Em vez disso, cadastros antigos sao apenas desativados (Soft Delete). Eles deixam de ser listados para novas transacoes comerciais no patio, mas o historico de faturamentos antigos, ordens de servico concluidas e assinaturas de autoria permanecem intactos para futuras auditorias ou consultas de garantia.

### • Ineficiencia no Fluxo de Orcamentos e Autorizacoes
- **O Problema de Negocio:** Carros travados desmontados ocupando espaco fisico nas baias de servico enquanto a recepcao tenta ligar repetidas vezes para o cliente para obter autorizacao dos reparos adicionais detectados.
- **A Solucao de Negocio:** Implementamos o **Portal de Aprovacao Autonoma**. Ao fechar o diagnostico, o sistema envia ao cliente um link interativo seguro. O proprietario consegue visualizar todos os itens do laudo (servicos e pecas) com seus respectivos precos de forma detalhada e pode aprovar ou rejeitar os reparos adicionais com um unico clique no celular, de onde estiver. A decisao e integrada transacionalmente e o mecanico recebe o sinal verde para iniciar o trabalho imediatamente.

---

## 3. A Engenharia Tatica por Tras das Solucoes

Para dar vida as solucoes de negocio descritas acima com o maximo de robustez e seguranca, traduzimos cada regra em componentes, design patterns e barreiras transacionais de software de nivel enterprise:

### • Esteiras Inteligentes de Fluxo e Metricas de Patio
- **A Traducao Tecnica:** A separacao de fluxos e controlada por uma maquina de estados acoplada ao agregador `OrdemServico`. A medicao e priorizacao do patio sao calculadas de forma analitica atraves de timestamps automatizados no banco de dados.
- **O Mecanismo:** O gerenciamento de logs de status (`OrdemServicoStatusLog`) calcula metricas operacionais de BI em tempo real: `leadtime_full_minutos` (tempo total no patio), `leadtime_ativo_minutos` (tempo real de chaves na mao do mecanico) e `tempo_espera_aprovacao_minutos` (tempo de resposta do cliente), fornecendo dados estruturados para otimizacao de escala do patio.

### • Garantia de Integridade de Inventario e Congelamento Financeiro
- **A Traducao Tecnica:** Implementamos um controle de concorrencia no banco de dados via **Locks Pessimistas** e isolamos as alteracoes de precos atraves de tabelas associativas estaticas.
- **O Mecanismo:** Ao aprovar um orcamento, o sistema adquire um bloqueio exclusivo usando a clausula **`SELECT FOR UPDATE`** sobre os registros de pecas, garantindo que operacoes concorrentes nao causem furos de saldo fisico ou estoque negativo. Alem disso, os precos e tempos de execucao sao gravados fisicamente em tabelas associativas (`ItemPecaOS` e `ItemServicoOS`) no ato do diagnostico, isolando as transações de reajustes futuros do catalogo geral.

### • Maquina de Estados e Notificacoes Proativas
- **A Traducao Tecnica:** Aplicamos o padrao de **Arquitetura Hexagonal (Ports & Adapters)** para isolar o envio de mensagens externas, disparados de forma automatica nas transicoes criticas de status.
- **O Mecanismo:** O core do dominio de OS interage exclusivamente com a porta abstrata `EnviadorNotificacaoPort`. Os adaptadores de infraestrutura (como `WhatsAppConsoleAdapter`) sao injetados de forma dinâmica para realizar o envio das mensagens sem acoplar a nossa regra de negocio a provedores de telefonia de terceiros.

### • Referencialidade Temporal e Soft Delete
- **A Traducao Tecnica:** Aplicamos a integridade referencial estrita do PostgreSQL aliada ao controle logico de estado nos modelos SQLAlchemy 2.0.
- **O Mecanismo:** A inativacao logica e feita alterando a flag `ativo = False` na entidade correspondente. Isso mantem intactas todas as chaves estrangeiras (`ForeignKey`) de Ordens de Servico e logs de auditoria do passado, impedindo erros de orfaos no banco de dados, ao mesmo tempo em que a rota `get_db` ou as consultas de faturamento filtram apenas itens ativos para novos fluxos.

### • Acesso Publico Opaco e Prevencao de IDOR
- **A Traducao Tecnica:** Protegemos o portal publico contra vulnerabilidades de IDOR (Insecure Direct Object Reference) utilizando chaves alternativas criptograficas.
- **O Mecanismo:** As rotas publicas de aprovacao nao expoe chaves sequenciais primarias (`id` incremental). Em vez disso, o sistema gera e persiste um `visualizacao_hash` unico baseado em **UUIDv7** para cada OS. O cliente valida seus dados de forma segura sem autenticacao e sem conseguir adivinhar identificadores de terceiros.

---

## 4. Alinhamento Arquitetural: Escolha do Feature-Sliced Design

Durante as etapas iniciais de design do Mecanicar, optamos de forma deliberada e estrategica por nao utilizar a Clean Architecture tradicional, escolhendo em seu lugar o **Feature-Sliced Design (Arquitetura por Slices de Funcionalidades / Monolito Modular)**. 

Os motivadores para essa decisao sao tecnicamente fundamentados na busca pelo melhor equilibrio entre coesao de dominio e velocidade de evolucao:

- **Maximizacao da Coesao Interna (Feature-Based Thinking):** Diferente da Clean Architecture, que separa o codigo de forma horizontal por tipo de componente tecnico (routers em uma pasta, handlers em outra, modelos em outra), o Feature-Sliced Design agrupa o codigo de forma vertical por funcionalidade de negocio. Todo o ciclo de uma feature (como `cadastrar_servico` ou `listar_servicos`) reside geograficamente proximo dentro de sua respectiva pasta. Isso reduz drasticamente a complexidade cognitiva do time e elimina a verbosidade de transitar por multiplas camadas vazias de abstracao.
- **Caminho Natural para Microservicos (Desacoplamento de Contextos):** Estruturar a aplicacao em fatias verticais modulares prepara o sistema para uma futura quebra em microservicos com quase zero esforco de engenharia. Como cada contexto (como `estoque` ou `clientes`) e isolado e independente, se houver necessidade de escala individual no futuro, basta extrair a pasta correspondente para um repositorio ou container dedicado, mantendo as assinaturas e interfaces intactas.
- **Pilha Tecnologica de Alta Performance:** 
  - **FastAPI:** Escolhido como o framework web devido a sua alta performance baseada em execucao assincrona, suporte nativo a tipagem estrita do Python e validacao robusta de payloads de entrada e resposta via Pydantic v2. A geracao automatica de documentacao interativa (Swagger/OpenAPI) reduz a barreira de integracao com times de frontend.
  - **PostgreSQL:** Selecionado como banco de dados relacional de producao pela sua excelente confiabilidade, conformidade estrita com propriedades ACID e suporte a indices eficientes, crucial para garantir a consistencia das travas fisicas de concorrencia.

---

## 5. Estrategia de Robustez: Suite de Testes Coesa e Cobertura Estrita

A qualidade de software e a garantia de que as regras de negocio do Mecanicar estao blindadas contra regressões sao asseguradas por uma suite de testes automatizados completa e de alta fidelidade, que combina de forma equilibrada as abordagens de **Testes Unitarios** e **Testes de Integracao**, alcancando uma cobertura estrita de **97% do codigo**.

### • Testes Unitarios (Foco no Core de Dominio)
Estes testes validam a menor unidade logica do nosso codigo de forma isolada, livre de efeitos colaterais de rede ou banco de dados. Utilizamos dubles de teste e mocks para simular integracoes de infraestrutura.
- **Invariantes da FSM:** Testamos exaustivamente a Maquina de Estados Finita da Ordem de Servico, garantindo que caminhos incorretos de transicao (como mover uma OS `EM_EXECUCAO` direto para `ENTREGUE` sem passar por `FINALIZADA`) sejam barrados e lancem exceções consistentes de dominio.
- **Value Objects:** Asseguramos que os Value Objects de CpfCnpj, Email, Telefone e Placas de Veiculos validem e higienizem sintaticamente as entradas (como remocao de espacos extras e normalizacao de casing de e-mails), impedindo a entrada de dados corrompidos.

### • Testes de Integracao (Foco nas APIs e Persistencia)
Exercitam as rotas HTTP e controladores expostos pelo FastAPI de ponta a ponta, simulando o comportamento real de chamadas de rede e garantindo a correta comunicacao com a camada de dados.
- **Isolamento de Banco de Dados:** Para manter a suite rapida e isolada, os testes sao executados contra uma base de dados PostgreSQL transacional descartavel ou banco em memoria, isolando cada suite por meio de rollbacks transacionais.
- **Validacao de RBAC e Seguranca:** Simula requisições com tokens JWT reais contendo diferentes papeis de acesso (Gerente, Recepcionista, Mecanico, Estoquista), assegurando que o sistema responda com `HTTP 403 Forbidden` nas rotas proibidas e `HTTP 201/200` nas rotas autorizadas.
- **Cenarios de Condicao de Corrida:** Testamos de forma concorrente fluxos de baixa de estoque e faturamento de orçamentos sob carga paralela, garantindo que o PostgreSQL trave e sincronize as escritas corretamente sem estourar saldos negativos.

---

## 6. Desenvolvimento Seguro (OWASP e Praticas Corporativas)

Alinhado com as diretrizes e recomendacoes de seguranca da OWASP, o Mecanicar implementa barreiras ativas contra as principais ameacas do mercado:

- **Rate Limiting Inteligente (SlowAPI):** Protege a infraestrutura contra ataques de forca bruta, raspagem de dados e exaustao de recursos (DDoS). Roteia o controle de taxa de duas formas:
  1. Rotas Publicas de Autenticacao: Limita por IP real de conexao, varrendo e limpando cabeçalhos de proxies (como X-Forwarded-For).
  2. Rotas Privadas e Transacionais: Identifica o ID do usuario logado extraido do token JWT ou o Hash do Cookie HttpOnly de refresh. Isso garante que se um terminal do patio abusar do limite de chamadas, apenas aquela sessao especifica sera controlada, sem travar o restante da rede fisica da oficina.
- **Lock Pessimista contra Condicoes de Corrida (Race Conditions):** No instante em que o orcamento e aprovado e o estoque e baixado, a aplicacao adquire uma trava de escrita sobre os registros de pecas usando a clausula SELECT FOR UPDATE. Isso garante que a contagem do saldo fisico de estoque permaneca consistente, mesmo se dois mecanicos tentarem faturar itens simultaneamente.
- **Blindagem contra IDOR (Insecure Direct Object Reference):** Os links de WhatsApp enviados ao cliente para consulta publica de orcamentos nao expoe chaves sequenciais primarias do banco de dados. Em vez disso, cada OS possui um visualizacao_hash unico gerado a partir do UUIDv7. O cliente visualiza seus dados de forma segura sem autenticacao e sem conseguir adivinhar identificadores de terceiros.
- **Criptografia de Senhas com Argon2:** Adotamos o algoritmo hashing Argon2id para salvar credenciais operacionais de forma estritamente protegida, garantindo alta resistencia contra ataques de forca bruta por dicionario e processamento por GPUs.
- **Role-Based Access Control (RBAC):** Toda rota transacional valida o papel (Role) do operador logado (Gerente, Recepcionista, Mecanico, Estoquista) por meio da injecao de dependencias do FastAPI, garantindo isolamento total de privilegios.
- **Refresh Token Rotation (RTR):** Cada renovacao de sessao invalida imediatamente o refresh token anterior e gera um novo, mitigando ameacas de sequestro de sessao ativa.

---

## 7. Qualidade de Software e Analise Estatica

O codigo fonte do Mecanicar e verificado de forma continua para alcancar conformidade com padroes de projeto corporativos:
- **Limite de Complexidade Cognitiva:** Mantido rigidamente abaixo do teto de 15 pontos exigido pelo SonarQube para assegurar que os metodos de negocio sejam modulares, limpos e de facil compreensao.
- **Tipagem Estrita (PEP 484):** Uso sistematico de type hints e do tipo Annotated para injecoes de dependencias do FastAPI, eliminando bugs silenciosos de tipos e incompatibilidades estruturais.
- **Eliminacao de Duplicidades:** Extracao de validacoes comuns e utilitarios (como geradores de hashes e de schemas comuns do modulo de servicos) para arquivos base ou pacotes compartilhados.

---

## 8. Guia de Inicializacao Rapida (Quick Start)

Coloque toda a aplicacao, o banco de dados e a massa de testes de producao em execucao local em um unico comando.

### Requisitos Necessarios
- Docker instalado e ativo.
- Docker Compose configurado.

### Como Executar
Abra o seu terminal na pasta raiz do projeto e execute:
```bash
docker compose up --build
```

### Operacoes Executadas pelo Docker Compose
1. Inicializa o banco de dados PostgreSQL assincrono em rede interna e segura.
2. Compila a imagem Docker do backend Mecanicar.
3. Roda automaticamente todas as migrations pendentes no banco usando o Alembic.
4. Executa o script de sementes seed_db-v4.py, populando operadores, clientes, frota, catalogo de pecas com politicas de alerta e quatro cenarios de fluxo de Ordens de Servico completos com historico de logs.

---

## 9. Guia de Inicializacao do Ambiente de Testes (Test Quick Start)

Configure e execute toda a suite de testes locais (unitarios e integracao) acompanhados dos relatorios de cobertura de codigo dentro de um ambiente de testes totalmente isolado.

### Requisitos Necessarios
- Docker instalado e ativo.
- Gerenciador de pacotes `uv` configurado.

### Como Inicializar o Ambiente
Abra o seu terminal na pasta raiz do projeto e execute os passos a seguir:

1. **Subir o banco de dados PostgreSQL exclusivo de testes:**
   ```bash
   docker compose -f docker-compose.test.yml up -d
   ```

2. **Instalar e sincronizar as dependencias do projeto via `uv`:**
   ```bash
   uv sync
   ```

3. **Executar as migracoes do Alembic no banco de testes:**
   ```bash
   APP_ENV=test uv run alembic upgrade head
   ```

4. **Popular a base de testes com as massas estruturadas de sementes:**
   ```bash
   APP_ENV=test uv run python app/scripts/seed.py
   ```

### Como Executar as Suites de Testes

Escolha uma das instrucoes abaixo de acordo com a sua necessidade de analise:

- **Executar testes exibindo a cobertura completa com linhas nao cobertas:**
  ```bash
  APP_ENV=test uv run pytest --cov=app --cov-report=term-missing
  ```

- **Executar a suite de testes rapida de forma tradicional:**
  ```bash
  APP_ENV=test uv run pytest
  ```

- **Gerar os relatorios XML de testes e cobertura para integracao com SonarQube / CI:**
  ```bash
  APP_ENV=test uv run pytest --junitxml=report.xml
  APP_ENV=test uv run coverage xml -I
  ```

---

## 10. Credenciais de Testes e Massa de Dados (Seed v4)

Utilize os usuarios cadastrados pelo seeder automatico para simular o acesso baseado em papeis (RBAC):

| Operador | E-mail Funcional | Senha de Teste | Papel Comercial (Role) | Atribuicoes no Sistema |
| :--- | :--- | :--- | :--- | :--- |
| Armando Neto | armando.gerente@oficina.com | Gerente123! | GERENTE | Acesso irrestrito a relatorios analiticos de BI, faturamento e estoque. |
| Barbara Silva | barbara.recepcao@oficina.com | Recepcao123! | RECEPCIONISTA | Cadastro base de clientes, veiculos e abertura inicial de OSs no patio. |
| Roberto Santos | roberto.mecanico@oficina.com | Mecanico123! | MECANICO | Acesso a ordens de servico, preenchimento de diagnostico e execucao. |
| Denilson Souza | denilson.estoque@oficina.com | Estoque123! | ESTOQUISTA | Controle fisico de inventario de pecas e entrada de notas de compras. |

### Portal do Cliente (Teste Publico do WhatsApp)
Para testar a decisao do cliente de forma autonoma e sem necessidade de tokens JWT de operadores internos:

1. Acesse a pagina interativa do Swagger: http://localhost:8000/docs
2. Locate a rota publica de aprovacao: POST /ordens-servico/publica/{hash}/responder
3. Forneca o UUID de visualizacao estatico gerado automaticamente pelo seeder v4:
   019f3a5b-7c10-7000-8000-000000000001
4. Envie o JSON de resposta (exemplo: {"aprovado": true, "observacoes_cliente": "Servico aprovado!"}).
5. O sistema realizara a baixa fisica automatica de estoque das pecas correspondentes sob bloqueio pessimista e movera o veiculo para EM_EXECUCAO de forma transacional e integrada.
