**[Footer]** AutoHub - Manual Completo de Funcionamento | Uso interno

**

AUTOHUB
Manual Completo de Funcionamento do Aplicativo
**Especificacao funcional para Atoms, Codex e equipe de desenvolvimento

**Versao 1.0
**Documento criado para orientar o comportamento geral da plataforma AutoHub.

# Sumario Executivo

O AutoHub e uma plataforma operacional para intermediar oportunidades de compra e venda de veiculos entre fornecedores e compradores profissionais. O WhatsApp e o canal principal de entrada e saida, a Evolution API e o conector de mensagens, a OpenAI atua na interpretacao e padronizacao dos anuncios, e o painel administrativo concentra aprovacao, controle, historico e negociacoes.

- Receber ofertas de fornecedores cadastrados pelo WhatsApp.

- Agrupar fotos, videos e textos relacionados ao mesmo veiculo.

- Padronizar e anonimizar anuncios para proteger a origem da oferta.

- Exigir aprovacao manual antes de qualquer envio aos compradores.

- Enviar anuncios para categorias de compradores sem duplicidade.

- Registrar comprador vencedor, status de negociacao, documentos, fotos e consultas veiculares.

- Disponibilizar historico completo do veiculo por placa.

- Permitir comando administrativo pelo WhatsApp com menu de funcoes.

# 1. Visao Geral do Produto

O sistema deve funcionar como um CRM operacional especializado em repasse e intermediação de veículos. Ele nao deve ser tratado como um simples site de cadastro, mas como uma central de operacao integrada ao WhatsApp.

# 2. Principios de Funcionamento

Todas as decisoes comerciais importantes devem passar pelo administrador. A IA organiza e sugere, mas nao publica, nao negocia valores e nao altera status criticos sem comando autorizado.

# 3. Arquitetura Geral

A arquitetura recomendada e: WhatsApp -> Evolution API -> Webhook do AutoHub -> Backend -> Banco de dados -> OpenAI -> Painel de aprovacao -> Evolution API -> Compradores.

## 3.1 Camadas do Sistema

| Camada | Responsabilidade | Observacoes |
| --- | --- | --- |
| WhatsApp | Canal principal de comunicacao | Recebe fornecedores, envia compradores e recebe comandos do administrador. |
| Evolution API | Gateway de mensagens | Envia e recebe textos, imagens, eventos e status de conexao. |
| Backend AutoHub | Regras de negocio | Valida usuarios, processa webhook, chama IA, salva dados e envia mensagens. |
| OpenAI | Inteligencia artificial | Extrai dados, padroniza anuncios, anonimiza textos e auxilia comandos. |
| Banco de dados | Persistencia | Armazena veiculos, consultas, anexos, historico, compradores e fornecedores. |
| Painel Web | Operacao administrativa | Aprovacao, edicao, consultas, relatorios e configuracoes. |

# 4. Perfis de Usuario e Permissoes

| Perfil | Pode Fazer | Nao Pode Fazer |
| --- | --- | --- |
| Administrador | Gerenciar tudo, aprovar ofertas, enviar anuncios, registrar venda, consultar placa, anexar documentos, acessar dossies. | Nao deve ter API Keys expostas no frontend. |
| Fornecedor | Enviar fotos e descricoes pelo WhatsApp se estiver cadastrado. | Nao acessa painel e nao ve compradores. |
| Comprador | Receber ofertas, solicitar negociacao, consultar status permitido e consultas anteriores se vinculado a venda. | Nao faz novas consultas veiculares e nao acessa fornecedor/origem. |
| Sistema/IA | Interpretar, organizar, padronizar, sugerir, classificar e responder conforme regras. | Nao publica sem aprovacao, nao revela origem, nao inventa dados. |

# 5. Painel Administrativo

O painel administrativo e o centro de decisao. Todas as acoes criticas devem poder ser feitas pelo painel e, quando aplicavel, tambem por comandos do WhatsApp administrativo.

| Modulo | Comportamento esperado |
| --- | --- |
| Dashboard | Exibir ofertas recebidas, pendentes, enviadas, negociadas, vendidas, nao negociadas, consultas veiculares, instancias WhatsApp e alertas. |
| Administradores | Cadastrar, editar, inativar administradores e definir permissões. |
| Fornecedores | Cadastrar fornecedores por nome, empresa, telefone, categoria, cidade, status e observacoes. |
| Compradores | Cadastrar compradores, categorias de interesse, telefone, empresa, cidade, status, historico e observacoes. |
| Categorias | Criar grupos de compradores como SUV, Hatch, Premium, Lojistas RJ, Diesel, Todos etc. |
| Ofertas | Visualizar rascunhos, pendentes, aprovadas, enviadas, vendidas, finalizadas e nao negociadas. |
| Negociacoes | Controlar comprador vencedor, entrou/nao entrou, documentacao e retirada. |
| Dossie do Veiculo | Consultar historico por placa com anuncio, consultas, comprador, fotos e documentos. |
| Consultas Veiculares | Executar e armazenar consultas basicas ou completas por placa/chassi. |
| Configuracoes | Evolution API, OpenAI, APIs veiculares, webhooks, storage e mensagens padrao. |

# 6. Fluxo de Recebimento de Ofertas

1. Fornecedor cadastrado envia texto, fotos, videos ou documentos para o WhatsApp conectado a Evolution API.

1. Evolution API dispara webhook para o backend AutoHub.

1. Sistema identifica o numero remetente e verifica se e fornecedor cadastrado e ativo.

1. Se nao for fornecedor cadastrado, a mensagem nao gera oferta automaticamente.

1. Sistema agrupa mensagens consecutivas relacionadas ao mesmo veiculo.

1. Apos periodo de inatividade configuravel, o lote e enviado para IA.

1. IA extrai dados, padroniza descricao, anonimiza informacoes sensiveis e cria rascunho.

1. Administrador recebe notificacao e revisa no painel de aprovacao.

## 6.1 Regras de Agrupamento

- Mensagens do mesmo fornecedor em curto intervalo devem ser agrupadas como uma possivel oferta.

- Fotos enviadas antes ou depois da descricao devem ser associadas ao mesmo rascunho quando o contexto indicar o mesmo veiculo.

- O sistema deve evitar criar varios rascunhos incompletos enquanto o fornecedor ainda esta enviando material.

- O tempo de espera sugerido e configuravel entre 30 e 90 segundos de inatividade.

# 7. Padronizacao e Anonimizacao de Anuncios

Todo anuncio recebido deve ser reescrito nos moldes da AutoHub. A mensagem original nunca deve ser encaminhada ao comprador.

| Item a remover/ocultar | Motivo |
| --- | --- |
| Placa, chassi, RENAVAM | Evitar acesso direto e proteger informacoes sensiveis. |
| Nome do vendedor, fornecedor, loja ou concessionaria | Impedir que o comprador contorne a AutoHub. |
| Telefone, WhatsApp, e-mail, links, QR Codes | Evitar contato direto com origem da oferta. |
| Endereco, localizacao, cidade de origem quando identificar fornecedor | Proteger a origem comercial. |
| Logos, marcas d agua, banners e placas de loja nas imagens | Evitar rastros visuais. |

## 7.1 Modelo Padrao de Anuncio

[CODIGO DA OFERTA]

🚗 Marca Modelo Versao
📅 Ano: ____
📍 KM: ____
⚙️ Cambio: ____
⛽ Combustivel: ____
🎨 Cor: ____
💰 Valor: R$ ____

Observacoes:
- ____
- ____

Para negociar, clique no botao ou responda com o codigo da oferta.

# 8. IA de Extracao de Dados do Veiculo

| Campo | Obrigatorio | Origem |
| --- | --- | --- |
| Marca | Sim | Texto ou inferencia do modelo. |
| Modelo | Sim | Texto recebido. |
| Versao | Nao | Texto recebido ou consulta veicular. |
| Ano fabricacao/modelo | Sim quando informado | Texto recebido. |
| KM | Nao | Texto recebido. |
| Valor fornecedor | Nao | Texto recebido; nao deve ser enviado automaticamente sem revisao. |
| Valor venda | Sim para envio | Informado pelo administrador. |
| Cor | Nao | Texto ou consulta. |
| Cambio | Nao | Texto ou inferencia segura. |
| Combustivel | Nao | Texto ou inferencia segura. |
| Categoria sugerida | Nao | Classificacao IA. |

# 9. Aprovacao de Ofertas

- Nenhuma oferta pode ser enviada sem aprovacao do administrador.

- Administrador visualiza descricao original e descricao padronizada.

- Administrador ve informacoes removidas pela anonimização.

- Administrador seleciona fotos, remove fotos e reordena imagens.

- Administrador informa valor de venda antes do envio.

- Administrador escolhe categorias de compradores.

- Sistema deve validar duplicidade de compradores antes do envio.

# 10. Envio de Ofertas aos Compradores

| Regra | Comportamento |
| --- | --- |
| Sem duplicidade | Se comprador estiver em varias categorias selecionadas, recebera apenas uma vez. |
| Imagem principal | Primeira imagem deve ir com caption contendo a descricao padronizada. |
| Demais imagens | Enviar sem repetir legenda ou com legenda curta. |
| Codigo da oferta | Todo anuncio deve iniciar com codigo unico de ate 6 digitos ou prefixo AH. |
| Negociar | Mensagem deve conter link/botao que direcione ao numero comercial/manual do administrador. |
| Registro | Cada envio deve gerar registro de destinatario, horario, status e erro se houver. |

# 11. Menu Administrativo pelo WhatsApp

Quando um administrador cadastrado enviar qualquer mensagem ao WhatsApp operacional, o sistema deve responder com menu administrativo.

| Menu | Opcoes |
| --- | --- |
| Veiculos | Nova oferta, pendentes, enviar, editar, marcar negociado, encerrar, buscar por codigo. |
| Consulta Veicular | Basica, completa, debitos, multas, gravame, leilao, sinistro, FIPE, proprietarios, ATPV-e. |
| Compradores | Cadastrar, editar, categorias, buscar, estatisticas. |
| Fornecedores | Cadastrar, listar, editar, bloquear, buscar. |
| Negociacoes | Pendentes, em andamento, nao concluidas, vendidos, documentacao, retirada. |
| Relatorios | Ofertas recebidas, enviadas, vendidas, compradores ativos, fornecedores ativos, consultas. |
| Configuracoes | Evolution API, OpenAI, consulta veicular, categorias, administradores, instancias. |
| Ajuda | Comandos, status do sistema, versao, suporte. |

## 11.1 Comandos Naturais

- consultar placa ABC1D23

- consulta completa ABC1D23

- mostrar ofertas pendentes

- marcar AH4821 como vendido

- buscar comprador Joao

- cadastrar fornecedor

# 12. Negociacao e Venda

1. Apos envio, oferta entra como Aguardando Atualizacao.

1. Se nao houver parecer do administrador no prazo configurado, vira Nao Negociado.

1. Administrador pode marcar como Negociado.

1. Ao marcar Negociado, deve selecionar obrigatoriamente o comprador.

1. Substatus deve ser Entrou ou Nao Entrou.

1. Se Nao Entrou, mover para Negociacoes Nao Concluidas.

1. Se Entrou, liberar controle de documentacao e situacao do veiculo.

| Status | Opcoes |
| --- | --- |
| Documentacao | Documentacao pendente; Documentacao OK. |
| Situacao | Veiculo em processo de troca; Disponivel para retirada; Retirado. |

# 13. Dossie Digital do Veiculo

Todo veiculo anunciado deve possuir um dossie vinculado principalmente a placa. O administrador deve conseguir consultar o historico informando a placa.

| Informacao no dossie | Descricao |
| --- | --- |
| Dados do veiculo | Marca, modelo, versao, ano, km, cor, cambio, combustivel, placa quando registrada. |
| Anuncio | Descricao usada, data do anuncio, codigo da oferta, fotos utilizadas. |
| Venda | Comprador selecionado, data do registro de venda, status e substatus. |
| Consultas | Todas as consultas veiculares vinculadas a placa. |
| Arquivos | Fotos, recibos, documentos, comprovantes e anexos. |
| Historico | Alteracoes de status, usuario responsavel, data e hora. |

## 13.1 Arquivos do Veiculo

- Administrador pode anexar fotos adicionais ao veiculo vendido.

- Administrador pode anexar recibo de compra, documentos do veiculo e comprovantes.

- Arquivos devem ter controle de visibilidade: interno ou visivel ao comprador.

- Comprador vinculado pode acessar apenas arquivos liberados pelo administrador.

# 14. Consulta Veicular

- Toda consulta deve ser vinculada a placa.

- Toda consulta deve ser armazenada para consulta futura.

- Ao consultar uma placa ja existente, mostrar historico anterior antes de permitir nova consulta.

- Comprador vinculado a venda pode visualizar consultas anteriores, mas nao pode realizar novas consultas.

| Campo da consulta | Obrigatorio |
| --- | --- |
| Placa | Sim |
| Tipo da consulta | Sim |
| Provedor | Sim |
| Resultado JSON/relatorio | Sim |
| Data e hora | Sim |
| Administrador solicitante | Sim |
| Custo estimado | Opcional |

# 15. Modelo de Dados Recomendado

| Tabela | Finalidade |
| --- | --- |
| users | Administradores e usuarios do sistema. |
| contacts | Compradores e fornecedores. |
| buyer_categories | Categorias de compradores. |
| contact_categories | Relacionamento comprador-categoria. |
| vehicles | Cadastro principal do veiculo. |
| offers | Anuncios/ofertas vinculadas a veiculos. |
| offer_media | Fotos e videos da oferta. |
| offer_recipients | Registros de envio aos compradores. |
| negotiations | Controle de comprador vencedor e status. |
| vehicle_queries | Consultas veiculares por placa. |
| vehicle_files | Documentos, fotos e anexos do dossie. |
| whatsapp_events | Eventos recebidos da Evolution API. |
| audit_logs | Historico de alteracoes e auditoria. |

# 16. Webhooks e Eventos

- Criar endpoint publico backend POST /api/v1/whatsapp/webhook.

- Receber mensagens, midias, status e eventos de conexao.

- Validar instancia e origem da mensagem.

- Salvar evento bruto para auditoria e debug.

- Processar de forma assíncrona para nao perder eventos.

# 17. Seguranca e Boas Praticas

- API Keys da Evolution API e OpenAI devem ficar apenas no backend/variaveis seguras.

- Frontend nunca deve chamar Evolution API diretamente.

- Validar administrador antes de exibir menu administrativo.

- Validar fornecedor antes de gerar oferta.

- Validar comprador antes de exibir status ou consultas.

- Registrar logs de erros de envio e webhook.

- Criar controle de permissao para arquivos internos e arquivos liberados ao comprador.

# 18. Checklist de Funcionamento Completo

- Fornecedor cadastrado envia texto e sistema recebe.

- Fornecedor cadastrado envia varias fotos e sistema agrupa.

- Fornecedor nao cadastrado nao gera oferta.

- IA extrai dados do veiculo corretamente.

- IA remove placa, telefone, nome do vendedor, loja e localizacao.

- Administrador aprova oferta antes do envio.

- Sistema envia uma imagem com caption corretamente.

- Sistema envia varias imagens corretamente.

- Comprador em duas categorias recebe apenas uma vez.

- Botao/link negociar direciona ao numero correto.

- Administrador registra comprador vencedor.

- Status Entrou libera documentacao e situacao.

- Status Nao Entrou move para negociacoes nao concluidas.

- Consulta veicular fica vinculada a placa.

- Historico por placa mostra venda, anuncio, consultas, fotos e documentos.

- Comprador vinculado ve consultas anteriores sem poder consultar novamente.

- Comprador nao vinculado nao ve informacoes da negociacao.

- Menu administrativo aparece apenas para administrador cadastrado.

- API Keys nao aparecem no frontend.

# 19. Pedido de Revisao Completa para Enviar ao Atoms

Analise todo o projeto AutoHub e compare o comportamento atual com este manual completo de funcionamento.

Antes de alterar qualquer arquivo, gere um relatorio tecnico indicando:
1. Funcoes ja implementadas corretamente.
2. Funcoes ausentes.
3. Funcoes parcialmente implementadas.
4. Bugs encontrados.
5. Riscos de seguranca.
6. Problemas de arquitetura.
7. Ajustes necessarios na Evolution API.
8. Ajustes necessarios na OpenAI.
9. Ajustes necessarios no envio de midias.
10. Ajustes necessarios em banco de dados, permissoes e dossie do veiculo.

Nao modifique o codigo sem minha aprovacao.
Depois do relatorio, proponha um plano de implementacao por etapas, preservando tudo que ja esta funcionando.