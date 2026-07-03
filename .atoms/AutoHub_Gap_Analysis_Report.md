# AutoHub — Relatório Técnico de Análise Comparativa
**Manual vs. Implementação Atual**

Gerado em: 2026-07-02  
Referência: AutoHub Manual Completo de Funcionamento v1.0

---

## 1. Funções Já Implementadas Corretamente

| # | Função | Localização | Observações |
|---|--------|-------------|-------------|
| 1 | Recebimento de ofertas via WhatsApp | `routers/whatsapp.py` webhook | Fornecedor cadastrado envia texto/fotos/vídeos |
| 2 | Agrupamento de mensagens consecutivas | `services/whatsapp_conversation.py` | Janela de 10 minutos |
| 3 | Parser IA de ofertas | `services/whatsapp_ai.py` | Extrai dados do veículo via gpt-5.4 |
| 4 | Assistente IA para compradores | `services/whatsapp_ai.py` | Auto-reply + escalonamento para admin |
| 5 | Workflow de aprovação (APROVAR/REJEITAR/CONFIRMAR/VOLTAR) | `services/offer_workflow.py` | Via WhatsApp e painel web |
| 6 | Distribuição para categorias com deduplicação | `services/offer_workflow.py` | Comprador em 2 categorias recebe apenas 1x |
| 7 | Envio de múltiplas imagens (1ª com caption, demais sem) | `offer_workflow.py` + `admin_ad_workflow.py` | Implementado corretamente |
| 8 | Comando NEGOCIAR do comprador | `services/offer_workflow.py` | Retorna número de negociação |
| 9 | Consulta veicular por placa | `services/plate_lookup.py` | ConsultarPlaca (primário) + BrasilAPI (fallback) |
| 10 | Dossiê digital do veículo | `services/vehicle_dossiers.py` | Criação, busca por placa, arquivos, consultas |
| 11 | Comandos admin via WhatsApp | `services/admin_chat_commands.py` | Contatos, categorias, config, PLACA |
| 12 | Criação de anúncio via WhatsApp | `services/admin_ad_workflow.py` | CRIAR ANUNCIO + fluxo multi-step |
| 13 | Chat IA conversacional admin | `services/admin_ai_chat.py` | Fallback para mensagens não-comando |
| 14 | Processamento de imagens (blur de placas/logos) | `services/image_processor.py` | Detecção IA + blur PIL |
| 15 | Anonimização no parser IA | `services/whatsapp_ai.py` | Prompt remove placa, telefone, nome do vendedor |
| 16 | Geração de código de oferta | `models/offers.py` | Código numérico de 6 dígitos |
| 17 | Status de negociação (awaiting → negotiated → entered/not_entered) | `pages/NegotiationsPage.tsx` | Fluxo completo com substatus |
| 18 | Controle de documentação e situação do veículo | `pages/NegotiationsPage.tsx` | Doc pendente/OK, em troca/disponível/retirado |
| 19 | Registro de venda com criação de dossiê | `services/vehicle_dossiers.py` | register_sale() |
| 20 | Controle de acesso do comprador ao dossiê | `models/vehicle_dossier_access.py` | Tabela de acesso + validação |
| 21 | Permissão de visibilidade de arquivos | `models/vehicle_dossier_files.py` | is_admin_only / is_released_to_buyer |
| 22 | Config WhatsApp em banco de dados | `services/whatsapp.py` | DB-backed com cache |
| 23 | Setup e status de webhook | `services/whatsapp.py` | Configurar Evolution API webhook |
| 24 | Envio de texto e mídia via Evolution API | `services/whatsapp.py` | send_text_message + send_media_message |
| 25 | Decodificação de mídia criptografada do WhatsApp | `services/whatsapp.py` | getBase64FromMediaMessage + upload storage |
| 26 | Gerenciamento de telefones admin | `pages/AdminPhonesPage.tsx` | CRUD completo |
| 27 | Notificação admin em eventos críticos | `services/whatsapp_conversation.py` | Draft criado, mensagem escalada |
| 28 | Páginas frontend completas | 14 páginas | Dashboard, Fornecedores, Compradores, Categorias, Ofertas, Distribuição, Negociações, Números, Histórico, WhatsApp Settings, Conversas, Admin Phones, Dossiês, Dossiês Comprador |

---

## 2. Funções Ausentes

| # | Função | Seção do Manual | Prioridade |
|---|--------|-----------------|------------|
| 1 | Dashboard completo com KPIs (ofertas recebidas/pendentes/enviadas/negociadas/vendidas/não negociadas, consultas, instâncias, alertas) | §5 Dashboard | Alta |
| 2 | Gerenciamento de administradores (CRUD com permissões) | §5 Administradores | Alta |
| 3 | Campos completos de fornecedores (categoria, cidade, observações) | §5 Fornecedores | Média |
| 4 | Campos completos de compradores (empresa, cidade, observações) | §5 Compradores | Média |
| 5 | Timeout de inatividade configurável (30-90s) para agrupamento | §6.1 | Alta |
| 6 | Modelo padrão de anúncio (formato exato do §7.1) | §7.1 | Alta |
| 7 | Menu administrativo completo via WhatsApp (§11) | §11 | Alta |
| 8 | Comandos em linguagem natural (§11.1) | §11.1 | Média |
| 9 | Submenu Veículos (nova oferta, pendentes, enviar, editar, marcar negociado, encerrar, buscar por código) | §11 | Alta |
| 10 | Submenu Consulta Veicular (básica, completa, débitos, multas, gravame, leilão, sinistro, FIPE, proprietários, ATPV-e) | §11 | Média |
| 11 | Submenu Negociações (pendentes, em andamento, não concluídas, vendidos, documentação, retirada) | §11 | Média |
| 12 | Submenu Relatórios (ofertas recebidas/enviadas/vendidas, compradores ativos, fornecedores ativos, consultas) | §11 Relatórios | Média |
| 13 | Submenu Configurações (Evolution API, OpenAI, consulta veicular, categorias, administradores, instâncias) | §11 Configurações | Baixa |
| 14 | Tabela offer_media (separada do JSON na offers) | §15 | Média |
| 15 | Tabela whatsapp_events (eventos brutos para auditoria) | §15 + §16 | Média |
| 16 | Tabela audit_logs (histórico de alterações) | §15 + §17 | Média |
| 17 | Prazo configurável para expiração automática de negociação (→ não negociado) | §12 | Alta |
| 18 | Página de configurações gerais (APIs veiculares, storage, mensagens padrão) | §5 Configurações | Baixa |
| 19 | Botão/link NEGOCIAR como botão interativo do WhatsApp | §10 | Média |
| 20 | Validação de instância/origem no webhook | §16 | Alta |

---

## 3. Funções Parcialmente Implementadas

| # | Função | Estado Atual | Gap |
|---|--------|-------------|-----|
| 1 | Anonimização de anúncios | Parser IA remove placa/telefone/nome, image_processor blura placas/logos | Não remove QR codes, e-mails, links, endereços do texto; não remove marcas d'água/banners de loja nas imagens |
| 2 | Menu admin WhatsApp | Contatos, categorias, config, PLACA, CRIAR ANUNCIO | Faltam: submenu Veículos, Consulta Veicular, Negociações, Relatórios, Configurações |
| 3 | Dossiê do veículo | Estrutura completa com consultas, arquivos, histórico | Falta: seção dedicada "Anúncio" (descrição usada, data, código, fotos); visualização do comprador com acesso controlado |
| 4 | Consulta veicular | Apenas consulta básica por placa (ConsultarPlaca/BrasilAPI) | Faltam tipos: débitos, multas, gravame, leilão, sinistro, FIPE isolada, proprietários, ATPV-e |
| 5 | Modelo de dados da oferta | Campos principais presentes | Faltam: versão (version), câmbio (transmission), categoria sugerida (suggested_category), valor fornecedor vs valor venda separados |
| 6 | Dashboard | Página Index.tsx com stats básicos | Faltam: KPIs completos (ofertas por status, consultas, instâncias WhatsApp, alertas) |
| 7 | Validação de fornecedor | Verifica se telefone está cadastrado | Não impede totalmente criação de oferta (unregistered contacts são tratados como potential suppliers) |
| 8 | Registro de envio | Offer_distributions registra offer_id, buyer_id, category_id, sent_at | Faltam: status do envio, erro (se houver), horário como timestamp real |

---

## 4. Bugs Encontrados

| # | Bug | Arquivo | Descrição |
|---|-----|---------|-----------|
| 1 | **Mismatch de campos no parser IA** | `services/whatsapp_ai.py` | O prompt pede campos em português ("modelo", "ano", "combustivel") mas a validação `expected_fields` usa nomes em inglês ("brand", "model", "version", "year"). O JSON retornado pela IA usa chaves em português, mas o código espera inglês. |
| 2 | **Mensagens de não-cadastrados geram ofertas** | `routers/whatsapp.py` | Contatos não cadastrados são tratados como "potential suppliers" e podem gerar rascunhos, violando §6 item 4 ("Se não for fornecedor cadastrado, a mensagem não gera oferta automaticamente"). |
| 3 | **Campo `version` não existe no modelo Offers** | `models/offers.py` | O parser IA tenta validar campo "version" mas a tabela offers não tem coluna `version`. |
| 4 | **Campo `transmission` (câmbio) ausente** | `models/offers.py` | Manual §8 exige campo "Câmbio" mas não existe no modelo. |
| 5 | **Negociação sem prazo automático** | `models/offers.py` | `negotiation_deadline_hours` existe mas nunca é verificado automaticamente. Ofertas distribuídas nunca viram "Não Negociado" sozinhas. |
| 6 | **Timestamp como string** | `models/offers.py` | `distributed_at` e `finalized_at` são String ao invés de DateTime, dificultando consultas e comparações. |
| 7 | **Imagens como JSON string** | `models/offers.py` | `images`, `selected_images`, `processed_images`, `original_images` são strings JSON ao invés de tabela separada offer_media. |

---

## 5. Riscos de Segurança

| # | Risco | Severidade | Descrição |
|---|-------|------------|-----------|
| 1 | **Webhook sem validação de origem** | Alta | O endpoint POST /webhook não valida se a requisição veio realmente da Evolution API. Qualquer pessoa pode enviar eventos falsos. |
| 2 | **SSL desabilitado por padrão** | Média | `SSL_VERIFY = False` em todos os clientes httpx, suprimindo verificação de certificado. |
| 3 | **API keys no banco sem criptografia** | Média | Chaves da Evolution API e outras são armazenadas em texto plano na tabela whatsapp_settings. |
| 4 | **Validação fraca de telefone admin** | Média | Comparação por substring (`clean_sender in p or p in clean_sender`) pode causar falsos positivos. |
| 5 | **Sem rate limiting no webhook** | Média | Nenhuma proteção contra flood de mensagens no endpoint público. |
| 6 | **Sem sanitização de input nos comandos** | Baixa | Comandos WhatsApp são processados sem validação de conteúdo malicioso. |
| 7 | **Config-status expõe estrutura de chaves** | Baixa | Embora mascaradas, a estrutura das API keys é visível no endpoint. |

---

## 6. Problemas de Arquitetura

| # | Problema | Impacto | Recomendação |
|---|----------|---------|-------------|
| 1 | **Imagens como JSON string na tabela offers** | Dificulta queries, reordenação, e não permite metadados por imagem | Criar tabela offer_media separada |
| 2 | **Sem tabela de audit logs** | Impossível rastrear quem fez o quê e quando | Criar tabela audit_logs |
| 3 | **Sem tabela de eventos brutos do webhook** | Debug e auditoria limitados | Criar tabela whatsapp_events |
| 4 | **Buyers e Suppliers como tabelas separadas** | Duplicação de lógica de contatos | Considerar tabela contacts unificada (ou manter separadas mas com campos consistentes) |
| 5 | **Sem gerenciamento de administradores** | Apenas telefones admin, sem usuários com permissões | Implementar CRUD de admins com roles |
| 6 | **Settings como key-value sem validação** | Sem tipo, sem schema, propenso a erros | Adicionar validação por tipo nas configurações |
| 7 | **Sem fila assíncrona** | Processamento de imagem e distribuição em massa bloqueiam o webhook | Considerar processamento em background |
| 8 | **Timestamps como String** | distributed_at e finalized_at como String impedem ordenação/filtro correto | Migrar para DateTime com timezone |

---

## 7. Ajustes Necessários na Evolution API

| # | Ajuste | Prioridade | Descrição |
|---|--------|------------|-----------|
| 1 | **Validação de instância no webhook** | Alta | Verificar se o evento veio da instância configurada antes de processar |
| 2 | **Suporte a eventos de conexão** | Média | Escutar CONNECTION_UPDATE para detectar desconexão do WhatsApp e alertar admin |
| 3 | **Botão interativo NEGOCIAR** | Média | Usar endpoint de botões interativos do WhatsApp ao invés de apenas texto "Responda NEGOCIAR" |
| 4 | **Melhor tratamento de falhas de mídia** | Média | Retry automático quando decode de mídia falha, log detalhado |
| 5 | **Suporte a envio de documentos** | Baixa | Enviar PDFs/recibos via sendMedia com mediatype="document" |

---

## 8. Ajustes Necessários na OpenAI

| # | Ajuste | Prioridade | Descrição |
|---|--------|------------|-----------|
| 1 | **Corrigir mismatch de campos PT/EN** | Alta | Unificar nomes de campos no prompt e na validação (usar português ou inglês consistentemente) |
| 2 | **Step explícito de anonimização** | Alta | Adicionar passo dedicado para remover placa, chassi, RENAVAM, telefone, e-mail, links, endereço, nome de vendedor/loja do texto |
| 3 | **Adicionar campos faltantes ao parser** | Alta | Incluir versão, câmbio (transmission), categoria sugerida, valor fornecedor separado do valor venda |
| 4 | **Formato padrão de anúncio (§7.1)** | Alta | Gerar saída no formato exato do modelo padrão com emojis e campos obrigatórios |
| 5 | **Comandos em linguagem natural** | Média | Interpretar "consultar placa ABC1D23", "mostrar ofertas pendentes", "marcar AH4821 como vendido" como comandos estruturados |

---

## 9. Ajustes Necessários no Envio de Mídias

| # | Ajuste | Prioridade | Descrição |
|---|--------|------------|-----------|
| 1 | **Botão NEGOCIAR interativo** | Média | Substituir texto "Responda NEGOCIAR" por botão clicável do WhatsApp |
| 2 | **Reordenação de imagens pelo admin** | Média | Permitir drag-and-drop ou numeração para definir ordem das fotos antes do envio |
| 3 | **Remoção de marcas d'água/logos** | Média | Atual image_processor apenas blura; ideal seria remover ou recortar |
| 4 | **Envio de vídeos com caption** | Baixa | Atualmente apenas imagens são enviadas com caption |
| 5 | **Envio de documentos (PDF)** | Baixa | Suporte a envio de laudos, documentos do veículo |

---

## 10. Ajustes Necessários em Banco de Dados, Permissões e Dossiê

| # | Ajuste | Prioridade | Descrição |
|---|--------|------------|-----------|
| 1 | **Criar tabela offer_media** | Alta | Separar mídias da tabela offers com campos: id, offer_id, url, processed_url, media_type, position, is_selected |
| 2 | **Criar tabela whatsapp_events** | Média | Armazenar eventos brutos do webhook para auditoria e debug |
| 3 | **Criar tabela audit_logs** | Média | Rastrear alterações: user_id, action, entity, entity_id, old_value, new_value, timestamp |
| 4 | **Adicionar campos ao modelo Buyers** | Média | company, city, observations |
| 5 | **Adicionar campos ao modelo Suppliers** | Média | category, city, observations |
| 6 | **Adicionar campos ao modelo Offers** | Alta | version, transmission, suggested_category, supplier_price (separado do price que é valor de venda) |
| 7 | **Migrar timestamps String → DateTime** | Média | distributed_at e finalized_at para DateTime com timezone |
| 8 | **Adicionar tipo de consulta** | Média | Campo consultation_type em vehicle_plate_consultations (básica, completa, débitos, multas, etc.) |
| 9 | **Implementar CRUD de administradores** | Alta | Tabela admin_users com campos: name, email, phone, role, permissions, status |
| 10 | **Expiração automática de negociações** | Alta | Job/cron que verifica negotiation_deadline_hours e marca como not_negotiated |
| 11 | **Visualização do comprador no dossiê** | Média | Página dedicada onde comprador vinculado vê apenas arquivos liberados e consultas anteriores |
| 12 | **Configuração de timeout de agrupamento** | Alta | Setting GROUPING_TIMEOUT_SECONDS configurável (30-90s) ao invés de hardcoded 10 minutos |

---

## Plano de Implementação por Etapas

### ETAPA 1 — Correções Críticas (Bug Fixes + Segurança)
**Objetivo:** Corrigir bugs que impedem funcionamento correto e fechar brechas de segurança

1. Corrigir mismatch de campos PT/EN no parser IA (unificar para português)
2. Adicionar campos faltantes ao modelo Offers (version, transmission, suggested_category, supplier_price)
3. Impedir que contatos não cadastrados gerem ofertas automaticamente (§6.4)
4. Adicionar validação de origem no webhook (verificar instância)
5. Melhorar validação de telefone admin (match exato, não substring)
6. Criar tabela offer_media e migrar dados de imagens JSON

### ETAPA 2 — Modelo Padrão de Anúncio + Anonimização
**Objetivo:** Implementar formato exato do §7.1 e anonimização completa

1. Atualizar prompt do parser IA para gerar anúncio no formato padrão (§7.1)
2. Adicionar step explícito de anonimização (remover placa, chassi, RENAVAM, telefone, e-mail, links, endereço, nome de vendedor/loja)
3. Atualizar format_offer_for_buyer() para usar o modelo padrão
4. Adicionar campos de câmbio e versão ao formulário de ofertas no frontend

### ETAPA 3 — Timeout Configurável + Expiração Automática
**Objetivo:** Agrupamento configurável e expiração de negociações

1. Criar setting GROUPING_TIMEOUT_SECONDS (padrão 60s, range 30-90s)
2. Substituir hardcoded 10-minute window pelo valor configurável
3. Implementar verificação de negotiation_deadline_hours (endpoint ou cron)
4. Migrar distributed_at e finalized_at de String para DateTime

### ETAPA 4 — Menu Admin WhatsApp Completo
**Objetivo:** Implementar todos os submenus do §11

1. Submenu Veículos: pendentes, enviar, editar, marcar negociado, encerrar, buscar por código
2. Submenu Consulta Veicular: tipos de consulta (básica, completa, débitos, etc.)
3. Submenu Negociações: pendentes, em andamento, não concluídas, vendidos
4. Submenu Relatórios: resumos de ofertas, compradores, fornecedores, consultas
5. Comandos em linguagem natural (§11.1)

### ETAPA 5 — Dashboard + Relatórios
**Objetivo:** Dashboard completo com KPIs e página de relatórios

1. Atualizar Dashboard com cards: ofertas por status, consultas, instâncias, alertas
2. Criar página de Relatórios com filtros por período
3. Adicionar gráficos de tendências

### ETAPA 6 — Auditoria e Dados Completos
**Objetivo:** Tabelas de auditoria e campos completos de contatos

1. Criar tabela whatsapp_events para eventos brutos
2. Criar tabela audit_logs para rastreamento de alterações
3. Adicionar campos a Buyers (company, city, observations)
4. Adicionar campos a Suppliers (category, city, observations)
5. Implementar CRUD de administradores com permissões

### ETAPA 7 — Dossiê do Comprador + Melhorias de Mídia
**Objetivo:** Visualização do comprador e melhorias no envio

1. Página de dossiê do comprador (arquivos liberados + consultas anteriores)
2. Botão NEGOCIAR interativo no WhatsApp
3. Reordenação de imagens pelo admin antes do envio
4. Suporte a envio de documentos (PDF)

---

**Nota:** Cada etapa deve ser implementada e testada individualmente antes de prosseguir para a próxima, preservando tudo que já está funcionando. Nenhuma alteração deve ser feita sem aprovação prévia.