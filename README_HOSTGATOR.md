# AutoHub MVP para HostGator

Projeto simples em PHP + MySQL para rodar no Plano Turbo da HostGator e usar a Evolution API em VPS dedicado separado.

## Rodar em localhost primeiro

Este pacote tem um modo local com SQLite, para testar sem MySQL.

No Windows, execute:

```powershell
cd caminho\para\autohub-mvp-hostgator
.\start-localhost.ps1
```

Se PHP não estiver instalado, instale PHP ou use o PHP portátil gerado em `work/tools/php` durante os testes locais.

Depois acesse:

```text
http://127.0.0.1:8080/install.php
```

No ambiente local desta entrega, já foi criado um usuário de teste:

```text
E-mail: admin@autohub.local
Senha: autohub123
```

Para resetar o banco local, apague:

```text
storage/local.sqlite
```

e abra `/install.php` novamente.

## Arquitetura

```text
WhatsApp
  -> Evolution API no VPS dedicado 143.95.217.12
  -> Webhook público no HostGator
  -> AutoHub PHP + MySQL
  -> OpenAI no backend
  -> Evolution sendMedia
  -> Compradores cadastrados
```

## Estrutura

```text
autohub-mvp-hostgator/
  app/          backend PHP privado
  cron/         script para processar fila
  database/     schema.sql
  public/       arquivos públicos do site
  storage/      logs internos
  .env.example  exemplo de configuração
```

## Como subir no HostGator

### 1. Criar banco MySQL

No cPanel:

1. Abra Bancos de dados MySQL.
2. Crie um banco, por exemplo `seuusuario_autohub`.
3. Crie um usuário MySQL.
4. Dê todas as permissões desse usuário ao banco.

### 2. Enviar arquivos

Recomendado:

```text
/home/SEU_USUARIO/autohub/
  app/
  cron/
  database/
  storage/
  .env

/home/SEU_USUARIO/public_html/
  index.php
  install.php
  .htaccess
  assets/
```

Ou seja:

- envie o conteúdo da pasta `public/` para `public_html/`;
- envie `app/`, `cron/`, `database/`, `storage/` e `.env` para uma pasta fora do `public_html`, por exemplo `/home/SEU_USUARIO/autohub/`;
- se usar essa estrutura recomendada, edite `public_html/autohub_path.php` e coloque:

```php
return '/home/SEU_USUARIO/autohub';
```

Alternativa mais simples:

- envie a pasta inteira para `public_html/autohub`;
- acesse `https://seudominio.com/autohub/public`;
- esta alternativa é menos elegante, mas funciona para teste.

### 3. Configurar .env

Copie `.env.example` para `.env` e ajuste:

```env
APP_NAME=AutoHub MVP
APP_URL=https://seudominio.com
APP_ENV=production
APP_DEBUG=false
APP_KEY=gere-uma-chave-grande-aleatoria

DB_HOST=localhost
DB_NAME=seuusuario_autohub
DB_USER=seuusuario_user
DB_PASS=sua_senha
DB_CHARSET=utf8mb4
```

### 4. Instalar

Acesse:

```text
https://seudominio.com/install.php
```

Crie o primeiro usuário do painel.

Depois apague:

```text
public_html/install.php
```

### 5. Configurar Evolution e AIService

No painel:

```text
/settings
```

Configure:

- URL Evolution: `https://143.95.217.12`
- Instance name
- API Key da Evolution
- Provedor AIService: `openai`
- API Key do provedor de IA
- Modelo de IA, exemplo: `gpt-4o-mini`
- Temperatura, limite de tokens, timeout e maximo de tentativas

As chaves ficam criptografadas no banco e nunca vão para o frontend.

### 6. Configurar webhook na Evolution

Use no painel da Evolution:

```text
https://seudominio.com/webhook/evolution
```

Eventos mínimos:

```text
MESSAGES_UPSERT
```

### 7. Configurar cron no cPanel

Para agrupar múltiplas fotos antes de enviar, configure um cron a cada minuto:

```bash
* * * * * /usr/local/bin/php /home/SEU_USUARIO/autohub/cron/process_pending.php >/dev/null 2>&1
```

Se o caminho do PHP for diferente, veja no cPanel ou use:

```bash
php /home/SEU_USUARIO/autohub/cron/process_pending.php
```

## Fluxo de uso

1. Cadastre administradores em `/admins`.
2. Cadastre compradores em `/buyers`.
   - No MVP nao existem categorias de compradores.
   - Toda oferta aprovada pelo fluxo vai para todos os compradores ativos.
   - Numeros duplicados sao removidos pelo WhatsApp normalizado antes do envio.
3. Um admin manda uma ou mais fotos no WhatsApp com a descrição.
4. O webhook salva as mensagens.
5. O cron espera 45 segundos sem novas mensagens daquele admin.
6. A IA limpa e padroniza o texto.
7. O sistema envia a primeira foto com legenda e as demais sem legenda.
8. Os logs aparecem em `/logs`.

## O que este MVP não faz

- fornecedores;
- aprovação complexa;
- consulta placa;
- dossiê;
- negociação;
- relatórios;
- menu administrativo por WhatsApp;
- categorias complexas.

## Segurança

- OpenAI roda somente no backend.
- Evolution roda somente no backend.
- API Keys não são renderizadas no HTML.
- Configurações sensíveis são criptografadas no banco.
- Mensagens de números não cadastrados como admin são ignoradas.
- Compradores duplicados são removidos por telefone normalizado antes do envio.

## Atualizacao AIService

Em instalacoes novas, o banco ja vem pronto.

Em instalacoes antigas, rode no MySQL:

```text
database/migrations/2026_07_03_ai_service_logs.sql
```

## Fluxo de aprovacao do MVP

1. Admin envia foto + descricao pelo WhatsApp.
2. Sistema confirma recebimento ao admin.
3. AIService prepara a previa e remove dados sensiveis.
4. Sistema envia a previa ao admin com:
   - `1 - Aprovar envio`
   - `2 - Reprovar e corrigir`
   - `3 - Cancelar anuncio`
5. Compradores so recebem depois da aprovacao.
6. Em instalacoes antigas, rode tambem:

```text
database/migrations/2026_07_03_approval_flow.sql
```
