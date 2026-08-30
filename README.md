# Mecanicar - Sistema Integrado de Gestão Automotiva

O Mecanicar é um ecossistema digital corporativo desenvolvido sob medida para uma oficina mecânica de médio porte situada no interior paulista. O projeto engloba desde a descoberta tática de domínio até a implementação de um ecossistema robusto, seguro, testado e de fácil inicialização conteinerizada.

Este documento narra a jornada completa de concepção, modelagem, desenvolvimento seguro e operacionalização da plataforma, estruturada como uma narrativa fluida de transformação operacional e excelência técnica.

---

## 1. A Jornada Domain-Driven Design (DDD) e Discovery

### O Começo: Alinhamento e Descobrimento de Domínio
Para lidar com a complexidade de gerenciar uma oficina em franca expansão (pátio, estoque, faturamento, clientes e mecânicos), adotamos o Domain-Driven Design (DDD) como filosofia metodológica desde o primeiro dia de concepção do projeto. O objetivo inicial foi derrubar as barreiras de comunicação entre o time de desenvolvimento e os especialistas de negócio da Mecanicar. 

Por meio de sessões colaborativas de **Event Storming**, mapeamos toda a linha do tempo operacional da oficina, identificando como os eventos do mundo real direcionam os fluxos internos de trabalho.

### A Jornada do Veículo (Storytelling de Domínio)
A vida operacional da Mecanicar começa quando um cliente traz seu veículo para a oficina. A recepção registra a entrada do veículo, disparando o evento **Ordem de Serviço Recebida**. Nesse momento, a Ordem de Serviço (OS) - que é o nosso Core Domain e Agregado Principal - é instanciada no status inicial de `RECEBIDA`.

A partir desse ponto, o fluxo do pátio se divide em duas esteiras de trabalho:
- **Fluxo Normal:** O veículo é direcionado para a baia técnica de um mecânico, que inicia a inspeção (evento **Diagnóstico Iniciado**, status `EM_DIAGNOSTICO`). Ao concluir a análise, o mecânico gera o laudo técnico e lista as peças de estoque e as mãos de obra necessárias (evento **Diagnóstico Concluído**). O status da OS é transicionado para `AGUARDANDO_APROVACAO`, e um link seguro contendo um hash criptográfico é enviado ao cliente por WhatsApp.
- **Fluxo Expresso:** Caso o cliente solicite um serviço rápido de prateleira cadastrado no catálogo (como troca de óleo ou alinhamento rápido), a etapa de diagnóstico físico é totalmente pulada. A OS é direcionada imediatamente para o status de `AGUARDANDO_APROVACAO` com as peças e mãos de obra do serviço expresso já acopladas.

Em ambos os fluxos, o cliente recebe o orçamento de forma autônoma e toma sua decisão diretamente pelo portal público:
- **Se Aprovado:** O evento **Orçamento Aprovado** é disparado. O sistema adquire um bloqueio sobre o inventário do estoque, decrementa as quantidades físicas de peças e lança a OS para o status de `EM_EXECUCAO`, onde o mecânico inicia o trabalho físico. Ao finalizar todas as atividades, o status move-se para `FINALIZADA`.
- **Se Rejeitado:** O evento **Orçamento Rejeitado** é disparado, e a OS é transicionada de forma terminal para o status de `CANCELADA`.

A jornada termina com o faturamento e a retirada física do veículo pelo cliente (evento **Veículo Entregue**, status `ENTREGUE`), concluindo o ciclo operacional de forma integrada.

### Contextos Delimitados (Bounded Contexts)
Para garantir alta coesão e limites de responsabilidade limpos, o ecossistema foi mapeado em contextos delimitados com fronteiras bem definidas:
1. **Autenticação e Segurança (IAM):** Controle de credenciais, geração de sessões JWT de rotação rápida (RTR) e atribuição de papéis de acesso (RBAC).
2. **Clientes e Frota:** Gestão cadastral de clientes (Pessoa Física e Jurídica) e seus veículos utilizando Value Objects estruturados.
3. **Ordens de Serviço (Core Domain):** Agregado principal que gerencia a máquina de estados física do veículo no pátio, as transições e o histórico de status de auditoria.
4. **Estoque e Inventário:** Catálogo de insumos e controle de saldos físicos com políticas de alerta de estoque baixo.
5. **Catálogo de Serviços:** Mãos de obra autorizadas e tempos padrão de execução.

---

## 2. Desafios Operacionais e Soluções sob a Ótica de Negócio

O desenvolvimento do Mecanicar foi guiado pelo compromisso de sanar as dores reais do cotidiano da oficina. Antes de qualquer detalhe técnico, cada desafio do Tech Challenge foi analisado e resolvido sob a ótica de processos e regras de negócio, criando um fluxo operacional harmonioso e eficiente.

### • Erros na Priorização dos Atendimentos
- **O Problema de Negócio:** Carros acumulados no pátio, ociosidade de mecânicos sêniores em tarefas simples de rotina e atrasos nas entregas devido à falta de triagem inteligente.
- **A Solução de Negócio:** Dividimos a operação do pátio em duas vias de atendimento. Criamos o conceito de **Serviço Expresso** para manutenções preventivas de catálogo (como troca de óleo). Quando um cliente chega para um serviço expresso, ele pula a baia de diagnóstico e vai direto para a fila de execução rápida, liberando os especialistas de pátio para focar em inspeções físicas complexas de veículos que realmente demandam investigação técnica.

### • Falhas no Controle de Peças e Insumos
- **O Problema de Negócio:** Inconsistência de estoque (vender peças fisicamente inexistentes ao cliente) e prejuízo financeiro por reajustes de preços ocorridos entre o momento do diagnóstico e o faturamento final da OS.
- **A Solução de Negócio:** Estabelecemos uma regra rígida de **reserva imediata e congelamento de valores**. No instante em que o diagnóstico é gerado, as peças necessárias ficam vinculadas de forma estática ao orçamento com o valor comercial daquele momento. Mudanças na tabela geral de preços da oficina não afetam contratos antigos já emitidos ou em execução, garantindo previsibilidade para o cliente e protegendo as margens financeiras acordadas.

### • Dificuldade em Acompanhar o Status dos Serviços
- **O Problema de Negócio:** Ansiedade do cliente ligando constantemente para a recepção pedindo atualizações, o que sobrecarrega a equipe administrativa e gera gargalo de atendimento.
- **A Solução de Negócio:** Criamos uma **Política Ativa de Notificação**. O cliente deixa de ser um agente passivo e passa a ser notificado de forma proativa via WhatsApp em duas etapas cruciais da jornada: quando o diagnóstico físico é concluído (com o link de aprovação do orçamento) e no instante em que o mecânico finaliza a manutenção e o carro está limpo e pronto para retirada.

### • Perda de Histórico de Clientes e Veículos
- **O Problema de Negócio:** Exclusões acidentais de registros de clientes ou veículos antigos por operadores do caixa, resultando na perda de dados históricos de faturamento e quebra de garantia de serviços prestados.
- **A Solução de Negócio:** Adotamos a política de **Inativação Cadastral e Preservação Histórica**. Nenhuma entidade comercial ou administrativa é excluída permanentemente do sistema. Em vez disso, cadastros antigos são apenas desativados (Soft Delete). Eles deixam de ser listados para novas transações comerciais no pátio, mas o histórico de faturamentos antigos, ordens de serviço concluídas e assinaturas de autoria permanecem intactos para futuras auditorias ou consultas de garantia.

### • Ineficiência no Fluxo de Orçamentos e Autorizações
- **O Problema de Negócio:** Carros travados desmontados ocupando espaço físico nas baias de serviço enquanto a recepção tenta ligar repetidas vezes para o cliente para obter autorização dos reparos adicionais detectados.
- **A Solução de Negócio:** Implementamos o **Portal de Aprovação Autônoma**. Ao fechar o diagnóstico, o sistema envia ao cliente um link interativo seguro. O proprietário consegue visualizar todos os itens do laudo (serviços e peças) com seus respectivos preços de forma detalhada e pode aprovar ou rejeitar os reparos adicionais com um único clique no celular, de onde estiver. A decisão é integrada transacionalmente e o mecânico recebe o sinal verde para iniciar o trabalho imediatamente.

---

## 3. A Engenharia Tática por Trás das Soluções

Para dar vida às soluções de negócio descritas acima com o máximo de robustez e segurança, traduzimos cada regra em componentes, design patterns e barreiras transacionais de software de nível enterprise:

### • Esteiras Inteligentes de Fluxo e Métricas de Pátio
- **A Tradução Técnica:** A separação de fluxos é controlada por uma máquina de estados acoplada ao agregador `OrdemServico`. A medição e priorização do pátio são calculadas de forma analítica através de timestamps automatizados no banco de dados.
- **O Mecanismo:** O gerenciamento de logs de status (`OrdemServicoStatusLog`) calcula métricas operacionais de BI em tempo real: `leadtime_full_minutos` (tempo total no pátio), `leadtime_ativo_minutos` (tempo real de chaves na mão do mecânico) e `tempo_espera_aprovacao_minutos` (tempo de resposta do cliente), fornecendo dados estruturados para otimização de escala do pátio.

### • Garantia de Integridade de Inventário e Congelamento Financeiro
- **A Tradução Técnica:** Implementamos um controle de concorrência no banco de dados via **Locks Pessimistas** e isolamos as alterações de preços através de tabelas associativas estáticas.
- **O Mecanismo:** Ao aprovar um orçamento, o sistema adquire um bloqueio exclusivo usando a cláusula **`SELECT FOR UPDATE`** sobre os registros de peças, garantindo que operações concorrentes não causem furos de saldo físico ou estoque negativo. Além disso, os preços e tempos de execução são gravados fisicamente em tabelas associativas (`ItemPecaOS` e `ItemServicoOS`) no ato do diagnóstico, isolando as transações de reajustes futuros do catálogo geral.

### • Máquina de Estados e Notificações Proativas
- **A Tradução Técnica:** Aplicamos o padrão de **Arquitetura Hexagonal (Ports & Adapters)** para isolar o envio de mensagens externas, disparados de forma automática nas transições críticas de status.
- **O Mecanismo:** O core do domínio de OS interage exclusivamente com a porta abstrata `EnviadorNotificacaoPort`. Os adaptadores de infraestrutura (como `WhatsAppConsoleAdapter`) são injetados de forma dinâmica para realizar o envio das mensagens sem acoplar a nossa regra de negócio a provedores de telefonia de terceiros.

### • Referencialidade Temporal e Soft Delete
- **A Tradução Técnica:** Aplicamos a integridade referencial estrita do PostgreSQL aliada ao controle lógico de estado nos modelos SQLAlchemy 2.0.
- **O Mecanismo:** A inativação lógica é feita alterando a flag `ativo = False` na entidade correspondente. Isso mantém intactas todas as chaves estrangeiras (`ForeignKey`) de Ordens de Serviço e logs de auditoria do passado, impedindo erros de órfãos no banco de dados, ao mesmo tempo em que a rota `get_db` ou as consultas de faturamento filtram apenas itens ativos para novos fluxos.

### • Acesso Público Opaco e Prevenção de IDOR
- **A Tradução Técnica:** Protegemos o portal público contra vulnerabilidades de IDOR (Insecure Direct Object Reference) utilizando chaves alternativas criptográficas.
- **O Mecanismo:** As rotas públicas de aprovação não expõem chaves sequenciais primárias (`id` incremental). Em vez disso, o sistema gera e persiste um `visualizacao_hash` único baseado em **UUIDv7** para cada OS. O cliente valida seus dados de forma segura sem autenticação e sem conseguir adivinhar identificadores de terceiros.

---

## 4. Alinhamento Arquitetural: Escolha do Feature-Sliced Design

Durante as etapas iniciais de design do Mecanicar, optamos de forma deliberada e estratégica por não utilizar a Clean Architecture tradicional, escolhendo em seu lugar o **Feature-Sliced Design (Arquitetura por Slices de Funcionalidades / Monolito Modular)**. 

Os motivadores para essa decisão são tecnicamente fundamentados na busca pelo melhor equilíbrio entre coesao de domínio e velocidade de evolução:

- **Maximização da Coesão Interna (Feature-Based Thinking):** Diferente da Clean Architecture, que separa o código de forma horizontal por tipo de componente técnico (routers em uma pasta, handlers em outra, modelos em outra), o Feature-Sliced Design agrupa o código de forma vertical por funcionalidade de negócio. Todo o ciclo de uma feature (como `cadastrar_servico` ou `listar_servicos`) reside geograficamente próximo dentro de sua respectiva pasta. Isso reduz drasticamente a complexidade cognitiva do time e elimina a verbosidade de transitar por múltiplas camadas vazias de abstração.
- **Caminho Natural para Microsserviços (Desacoplamento de Contextos):** Estruturar a aplicação em fatias verticais modulares prepara o sistema para uma futura quebra em microsserviços com quase zero esforço de engenharia. Como cada contexto (como `estoque` ou `clientes`) é isolado e independente, se houver necessidade de escala individual no futuro, basta extrair a pasta correspondente para um repositório ou container dedicado, mantendo as assinaturas e interfaces intactas.
- **Pilha Tecnológica de Alta Performance:** 
  - **FastAPI:** Escolhido como o framework web devido à sua alta performance baseada em execução assíncrona, suporte nativo a tipagem estrita do Python e validação robusta de payloads de entrada e resposta via Pydantic v2. A geração automática de documentação interativa (Swagger/OpenAPI) reduz a barreira de integração com times de frontend.
  - **PostgreSQL:** Selecionado como banco de dados relacional de produção pela sua excelente confiabilidade, conformidade estrita com propriedades ACID e suporte a índices eficientes, crucial para garantir a consistência das travas físicas de concorrência.

---

## 5. Estratégia de Robustez: Suíte de Testes Coesa e Cobertura Estrita

A qualidade de software e a garantia de que as regras de negócio do Mecanicar estão blindadas contra regressões são asseguradas por uma suíte de testes automatizados completa e de alta fidelidade, que combina de forma equilibrada as abordagens de **Testes Unitários** e **Testes de Integração**, alcançando uma cobertura estrita de **97% do código**.

### • Testes Unitários (Foco no Core de Domínio)
Estes testes validam a menor unidade lógica do nosso código de forma isolada, livre de efeitos colaterais de rede ou banco de dados. Utilizamos dublês de teste e mocks para simular integrações de infraestrutura.
- **Invariantes da FSM:** Testamos exaustivamente a Máquina de Estados Finita da Ordem de Serviço, garantindo que caminhos incorretos de transição (como mover uma OS `EM_EXECUCAO` direto para `ENTREGUE` sem passar por `FINALIZADA`) sejam barrados e lancem exceções consistentes de domínio.
- **Value Objects:** Asseguramos que os Value Objects de CpfCnpj, Email, Telefone e Placas de Veículos validem e higienizem sintaticamente as entradas (como remoção de espaços extras e normalização de casing de e-mails), impedindo a entrada de dados corrompidos.

### • Testes de Integração (Foco nas APIs e Persistência)
Exercitam as rotas HTTP e controladores expostos pelo FastAPI de ponta a ponta, simulando o comportamento real de chamadas de rede e garantindo a correta comunicação com a camada de dados.
- **Isolamento de Banco de Dados:** Para manter a suíte rápida e isolada, os testes são executados contra uma base de dados PostgreSQL transacional descartável ou banco em memória, isolando cada suíte por meio de rollbacks transacionais.
- **Validação de RBAC e Segurança:** Simula requisições com tokens JWT reais contendo diferentes papéis de acesso (Gerente, Recepcionista, Mecânico, Estoquista), assegurando que o sistema responda com `HTTP 403 Forbidden` nas rotas proibidas e `HTTP 201/200` nas rotas autorizadas.
- **Cenários de Condição de Corrida:** Testamos de forma concorrente fluxos de baixa de estoque e faturamento de orçamentos sob carga paralela, garantindo que o PostgreSQL trave e sincronize as escritas corretamente sem estourar saldos negativos.

---

## 6. Desenvolvimento Seguro (OWASP e Práticas Corporativas)

Alinhado com as diretrizes e recomendações de segurança da OWASP, o Mecanicar implementa barreiras ativas contra as principais ameaças do mercado:

- **Rate Limiting Inteligente (SlowAPI):** Protege a infraestrutura contra ataques de força bruta, raspagem de dados e exaustão de recursos (DDoS). Roteia o controle de taxa de duas formas:
  1. Rotas Públicas de Autenticação: Limita por IP real de conexão, varrendo e limpando cabeçalhos de proxies (como X-Forwarded-For).
  2. Rotas Privadas e Transacionais: Identifica o ID do usuário logado extraído do token JWT ou o Hash do Cookie HttpOnly de refresh. Isso garante que se um terminal do pátio abusar do limite de chamadas, apenas aquela sessão específica será controlada, sem travar o restante da rede física da oficina.
- **Lock Pessimista contra Condições de Corrida (Race Conditions):** No instante em que o orçamento é aprovado e o estoque é baixado, a aplicação adquire uma trava de escrita sobre os registros de peças usando a cláusula SELECT FOR UPDATE. Isso garante que a contagem do saldo físico de estoque permaneça consistente, mesmo se dois mecânicos tentarem faturar itens simultaneamente.
- **Blindagem contra IDOR (Insecure Direct Object Reference):** Os links de WhatsApp enviados ao cliente para consulta pública de orçamentos não expõem chaves sequenciais primárias do banco de dados. Em vez disso, cada OS possui um visualizacao_hash único gerado a partir do UUIDv7. O cliente visualiza seus dados de forma segura sem autenticação e sem conseguir adivinhar identificadores de terceiros.
- **Criptografia de Senhas com Argon2:** Adotamos o algoritmo hashing Argon2id para salvar credenciais operacionais de forma estritamente protegida, garantindo alta resistência contra ataques de força bruta por dicionário e processamento por GPUs.
- **Role-Based Access Control (RBAC):** Toda rota transacional valida o papel (Role) do operador logado (Gerente, Recepcionista, Mecânico, Estoquista) por meio da injeção de dependências do FastAPI, garantindo isolamento total de privilégios.
- **Refresh Token Rotation (RTR):** Cada renovação de sessão invalida imediatamente o refresh token anterior e gera um novo, mitigando ameaças de sequestro de sessão ativa.

---

## 7. Qualidade de Software e Análise Estática

O código-fonte do Mecanicar é verificado de forma contínua para alcançar conformidade com padrões de projeto corporativos:
- **Limite de Complexidade Cognitiva:** Mantido rigidamente abaixo do teto de 15 pontos exigido pelo SonarQube para assegurar que os métodos de negócio sejam modulares, limpos e de fácil compreensão.
- **Tipagem Estrita (PEP 484):** Uso sistemático de type hints e do tipo Annotated para injeções de dependências do FastAPI, eliminando bugs silenciosos de tipos e incompatibilidades estruturais.
- **Eliminação de Duplicidades:** Extração de validações comuns e utilitários (como geradores de hashes e de schemas comuns do módulo de serviços) para arquivos base ou pacotes compartilhados.

---

## 8. Guia de Inicialização Rápida (Quick Start)

Coloque toda a aplicação, o banco de dados e a massa de testes de produção em execução local em um único comando.

### Requisitos Necessários
- Docker instalado e ativo.
- Docker Compose configurado.

### Como Executar
Abra o seu terminal na pasta raiz do projeto e execute:
```bash
docker compose up --build
```

### Operações Executadas pelo Docker Compose
1. Inicializa o banco de dados PostgreSQL assíncrono em rede interna e segura.
2. Compila a imagem Docker do backend Mecanicar.
3. Roda automaticamente todas as migrações pendentes no banco usando o Alembic.
4. Executa o script de sementes seed_db-v4.py, populando operadores, clientes, frota, catálogo de peças com políticas de alerta e quatro cenários de fluxo de Ordens de Serviço completos com histórico de logs.

---

## 9. Guia de Inicialização do Ambiente de Testes (Test Quick Start)

Configure e execute toda a suíte de testes locais (unitários e integração) acompanhados dos relatórios de cobertura de código dentro de um ambiente de testes totalmente isolado.

### Requisitos Necessários
- Docker instalado e ativo.
- Gerenciador de pacotes python `uv` configurado.

### Como Inicializar o Ambiente
Abra o seu terminal na pasta raiz do projeto e execute os passos a seguir:

1. **Subir o banco de dados PostgreSQL exclusivo de testes:**
   ```bash
   docker compose -f docker-compose.test.yml up -d
   ```

2. **Instalar e sincronizar as dependências do projeto via `uv`:**
   ```bash
   uv sync
   ```

3. **Executar as migrações do Alembic no banco de testes:**
   ```bash
   APP_ENV=test uv run alembic upgrade head
   ```

4. **Popular a base de testes com as massas estruturadas de sementes:**
   ```bash
   APP_ENV=test uv run python app/scripts/seed.py
   ```

### Como Executar as Suítes de Testes

Escolha uma das instruções abaixo de acordo com a sua necessidade de análise:

- **Executar testes exibindo a cobertura completa com linhas não cobertas:**
  ```bash
  APP_ENV=test uv run pytest --cov=app --cov-report=term-missing
  ```

- **Executar a suíte de testes rápida de forma tradicional:**
  ```bash
  APP_ENV=test uv run pytest
  ```

- **Gerar os relatórios XML de testes e cobertura para integração com SonarQube / CI:**
  ```bash
  APP_ENV=test uv run pytest --junitxml=report.xml
  APP_ENV=test uv run coverage xml
  ```

### Como Rodar a API

- **Executar a aplicação:**
  ```bash
  APP_ENV=test uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ```

### Acessando a aplicação

API: http://localhost:8000  
Docs: http://localhost:8000/docs

---

## 11. Credenciais de Testes e Massa de Dados

Utilize os usuários cadastrados pelo seeder automático para simular o acesso baseado em papéis (RBAC):

| Operador | E-mail Funcional | Senha de Teste | Papel Comercial (Role) | Atribuições no Sistema |
| :--- | :--- | :--- | :--- | :--- |
| Armando Neto | armando.gerente@oficina.com | Gerente123! | GERENTE | Acesso irrestrito a relatórios analíticos de BI, faturamento e estoque. |
| Bárbara Silva | barbara.recepcao@oficina.com | Recepcao123! | RECEPCIONISTA | Cadastro base de clientes, veículos e abertura inicial de OSs no pátio. |
| Roberto Santos | roberto.mecanico@oficina.com | Mecanico123! | MECÂNICO | Acesso a ordens de serviço, preenchimento de diagnóstico e execução. |
| Denílson Souza | denilson.estoque@oficina.com | Estoque123! | ESTOQUISTA | Controle físico de inventário de peças e entrada de notas de compras. |

### Portal do Cliente (Teste Público do WhatsApp)
Para testar a decisão do cliente de forma autônoma e sem necessidade de tokens JWT de operadores internos:

1. Acesse a página interativa do Swagger: http://localhost:8000/docs
2. Localize a rota pública de aprovação: POST /ordens-servico/publica/{hash}/responder
3. Forneça o UUID de visualização estático gerado automaticamente pelo seeder v4:
   019f3a5b-7c10-7000-8000-000000000001
4. Envie o JSON de resposta (exemplo: {"aprovado": true, "observacoes_cliente": "Serviço aprovado!"}).
5. O sistema realizará a baixa física automática de estoque das peças correspondentes sob bloqueio pessimista e moverá o veículo para EM_EXECUCAO de forma transacional e integrada.