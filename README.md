# Mecanicar - Sistema Integrado de Gestao Automotiva

O Mecanicar e um ecossistema digital corporativo desenvolvido sob medida para uma oficina mecanica de medio porte situada no interior paulista. O projeto representa a entrega da Fase 1 do Tech Challenge, englobando desde a descoberta tatica de dominio ate a implementacao de um ecossistema robusto, seguro, testado e conteinerizado.

Este documento narra a jornada completa de concepcao, modelagem, desenvolvimento seguro e operacionalizacao da plataforma.

---

## 1. A Jornada Domain-Driven Design (DDD) e Descobrimento

Para lidar com a complexidade de gerenciar uma oficina em expansao (patio, estoque, faturamento, clientes e mecanicos), adotamos o Domain-Driven Design (DDD) como filosofia metodologica desde a primeira reuniao de alinhamento.

### Event Storming e Core Domain
Realizamos sessoes colaborativas de Event Storming com especialistas de negocio para modelar a linha do tempo operacional da oficina, contada sob a forma de uma narrativa continua de eventos de dominio e transicoes de status.

A jornada do veiculo na Mecanicar comeca quando um cliente traz seu veiculo para a oficina. A recepcao registra a entrada do veiculo, disparando o evento Ordem de Servico Recebida. Nesse momento, a Ordem de Servico (OS) - que e o nosso Core Domain - e instanciada no status inicial de RECEBIDA.

A partir desse ponto, o fluxo do patio se divide em duas esteiras inteligentes:

- Fluxo Normal: O veiculo e direcionado para a baia tecnica de um mecanico, que inicia a inspecao (evento Diagnostico Iniciado, status EM_DIAGNOSTICO). Ao concluir a analise, o mecanico gera o laudo tecnico e lista as pecas de estoque e as maos de obra necessarias (evento Diagnostico Concluido). O status da OS e transicionado para AGUARDANDO_APROVACAO, e um link seguro contendo um hash criptografico e enviado ao cliente por WhatsApp.

- Fluxo Expresso: Caso o cliente solicite um servico rapido de prateleira cadastrado no catalogo (como troca de oleo ou alinhamento rapido), a etapa de diagnostico fisico e totalmente pulada. A OS e direcionada imediatamente para o status de AGUARDANDO_APROVACAO com as pecas e maos de obra do servico expresso ja acopladas.

Em ambos os fluxos, o cliente recebe o orcamento de forma autonoma e pode tomar sua decisao diretamente pelo portal publico:

- Se Aprovado: O evento Orcamento Aprovado e disparado. O sistema adquire um bloqueio pessimista imediato sobre o inventario do estoque, decrementa as quantidades fisicas de pecas e lanca a OS para o status de EM_EXECUCAO, onde o mecanico inicia o trabalho fisico. Ao finalizar todas as atividades, o status move-se para FINALIZADA.

- Se Rejeitado: O evento Orcamento Rejeitado e disparado, e a OS e transicionada de forma terminal para o status de CANCELADA.

A jornada termina com o faturamento e a retirada fisica do veiculo pelo cliente (evento Veiculo Entregue, status ENTREGUE).

### Contextos Delimitados (Bounded Contexts)
O ecossistema foi mapeado em contextos limpos com fronteiras de codigo e modelos bem definidos:

1. Autenticacao e Seguranca (IAM): Controle de credenciais, geracao de sessoes JWT de rotacao rapida (RTR) e atribuicao de papeis de acesso (RBAC).
2. Clientes e Frota: Gestao cadastral de clientes (Pessoa Fisica e Juridica) e seus veiculos utilizando Value Objects estruturados.
3. Ordens de Servico (Core Domain): Agregado principal que gerencia a maquina de estados fisica do veiculo no patio, as transicoes e o historico de status de auditoria.
4. Estoque e Inventario: Catalogo de insumos e controle de saldos fisicos com politicas de recompra automatica.
5. Catalogo de Servicos: Maos de obra autorizadas e tempos padrao de execucao.

---

## 2. Escolha Arquitetural e Modelagem de Componentes

### A decisão de arquitetura Feature-Sliced Design
Durante o desenvolvimento do Mecanicar, optamos conscientemente por nao utilizar a Clean Architecture tradicional, escolhendo em seu lugar o Feature-Sliced Design (Arquitetura por Slices de Funcionalidades ou Monolito Modular). 

Os motivadores para essa decisao sao de ordem estrategica e de engenharia de software:

- Estrutura de Monolito Modular: Como o produto opera como um monolito, organizar o projeto em Slices verticais de funcionalidades (onde cada funcionalidade agrupa suas proprias rotas, esquemas, modelos, handlers e repositorios) maximiza a coesao interna e reduz drasticamente o acoplamento entre modulos.

- Migracao Descomplicada para Microservicos: No futuro, a medida que a oficina Mecanicar expandir e demandar escala independente, a migracao desse monolito para microservicos sera de baixo risco e natural. Como os componentes estao empacotados por contexto e funcionalidade (ex: todo o contexto de estoque reside sob app/features/estoque), basta mover essa pasta para um repositorio ou container isolado, sem necessidade de separar camadas horizontais complexas como ocorreria na Clean Architecture.

- Facilidade de Manutencao de Codigo: Desenvolvedores conseguem focar em uma unica funcionalidade (como faturamento ou abertura de OS) alterando arquivos geograficamente proximos no projeto, eliminando a friccao de navegar em dezenas de camadas indiretas de abstracao desnecessarias para o tamanho atual do negocio.

### Decisoes de Componentes e Pilha Tecnologica
A definicao da nossa pilha tecnologica foi estrategicamente fundamentada nos seguintes componentes de infraestrutura:

- FastAPI: Escolhido como o nosso framework web devido a sua alta performance baseada em execucao assincrona, suporte nativo a tipagem estrita do Python e validacao robusta de payloads de entrada e resposta via Pydantic. Adicionalmente, a geracao automatica de documentacao interativa (Swagger/OpenAPI) reduz a barreira de integracao com times de frontend.

- PostgreSQL: Selecionado como banco de dados relacional de producao pela sua excelente confiabilidade, conformidade estrita com propriedades ACID e suporte a indices eficientes. O motivador primordial para sua escolha foi a sua robustez na aplicacao de travas fisicas de concorrencia (como SELECT FOR UPDATE), essencial para impedir inconsistencias fisicas de estoque quando multiplos operadores realizam operacoes transacionais paralelas.

---

## 3. Estrategia de Testes Simplificada

A qualidade do Mecanicar e garantida atraves de uma suite de testes automatizados altamente focada em cobrir tanto as regras de negocio criticas quanto os fluxos expostos pelas APIs:

- Testes Unitarios: Focados em validar isoladamente componentes criticos e livres de efeitos colaterais. Os principais alvos sao a Maquina de Estados Finita (FSM) da Ordem de Servico (garantindo a impossibilidade de transicoes invalidas) e os Value Objects de CpfCnpj, Email, Telefone e Placas (assegurando higienizacao e validacao sintatica impecaveis).

- Testes de Integracao: Exercitam os endpoints HTTP expostos pelas APIs de ponta a ponta, simulando o banco de dados assincrono e aplicando o controle de permissao baseado em papeis (RBAC). Todas as funcionalidades expostas do sistema sao integralmente cobertas por testes de integracao, permitindo alcancar uma cobertura de testes de mais de 90%.

---

## 4. Desenvolvimento Seguro (OWASP e Praticas Corporativas)

Alinhado com as diretrizes e recomendacoes de seguranca da OWASP, o Mecanicar implementa barreiras ativas contra as principais ameacas do mercado:

- Rate Limiting Inteligente (SlowAPI): Protege a infraestrutura contra ataques de forca bruta, raspagem de dados e exaustao de recursos (DDoS). Roteia o controle de taxa de duas formas:
  1. Rotas Publicas de Autenticacao: Limita por IP real de conexao, varrendo e limpando cabeçalhos de proxies (como X-Forwarded-For).
  2. Rotas Privadas e Transacionais: Identifica o ID do usuario logado extraido do token JWT ou o Hash do Cookie HttpOnly de refresh. Isso garante que se um terminal do patio abusar do limite de chamadas, apenas aquela sessao especifica sera controlada, sem travar o restante da rede fisica da oficina.

- Lock Pessimista contra Condicoes de Corrida (Race Conditions): No instante em que o orcamento e aprovado e o estoque e baixado, a aplicacao adquire uma trava de escrita sobre os registros de pecas usando a clausula SELECT FOR UPDATE. Isso garante que a contagem do saldo fisico de estoque permaneca consistente, mesmo se dois mecanicos tentarem faturar itens simultaneamente.

- Blindagem contra IDOR (Insecure Direct Object Reference): Os links de WhatsApp enviados ao cliente para consulta publica de orcamentos nao expoe chaves sequenciais primarias do banco de dados. Em vez disso, cada OS possui um visualizacao_hash unico gerado a partir do UUIDv7. O cliente visualiza seus dados de forma segura sem autenticacao e sem conseguir adivinhar identificadores de terceiros.

- Criptografia de Senhas com Argon2: Adotamos o algoritmo hashing Argon2id para salvar credenciais operacionais de forma estritamente protegida, garantindo alta resistencia contra ataques de forca bruta por dicionario e processamento por GPUs.

- Role-Based Access Control (RBAC): Toda rota transacional valida o papel (Role) do operador logado (Gerente, Recepcionista, Mecanico, Estoquista) por meio da injecao de dependencias do FastAPI, garantindo isolamento total de privilegios.

- Refresh Token Rotation (RTR): Cada renovacao de sessao invalida imediatamente o refresh token anterior e gera um novo, mitigando ameacas de sequestro de sessao ativa.

---

## 5. Qualidade de Software e Analise Estatica

O codigo fonte do Mecanicar e verificado de forma continua para alcancar conformidade com padroes de projeto corporativos:
- Limite de Complexidade Cognitiva: Mantido rigidamente abaixo do teto de 15 pontos exigido pelo SonarQube para assegurar que os metodos de negocio sejam modulares, limpos e de facil compreensao.
- Tipagem Estrita (PEP 484): Uso sistematico de type hints e do tipo Annotated para injecoes de dependencias do FastAPI, eliminando bugs silenciosos de tipos e incompatibilidades estruturais.
- Eliminacao de Duplicidades: Extracao de validacoes comuns e utilitarios (como geradores de hashes e manipuladores de fuso horario) para modulos reutilizaveis na camada shared.

---

## 6. Guia de Inicializacao Rapida (Quick Start)

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

## 7. Guia de Inicializacao do Ambiente de Testes (Test Quick Start)

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
   APP_ENV=test uv run coverage xml -I
  ```

- **Executar a suite de testes rapida de forma tradicional:**
  ```bash
  APP_ENV=test uv run pytest
  ```

---

## 8. Credenciais de Testes e Massa de Dados (Seed v4)

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
