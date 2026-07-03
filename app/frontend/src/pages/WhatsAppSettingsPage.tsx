import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Settings, Wifi, WifiOff, RefreshCw, CheckCircle, XCircle, MessageSquare, Bot, Webhook, Copy } from 'lucide-react';
import { client } from '@/lib/api';
import { toast } from 'sonner';

interface ConfigStatus {
  configured: boolean;
  missing_vars: string[];
  current_values: {
    api_url: string;
    api_key: string;
    instance_name: string;
  };
}

interface ConnectionTest {
  connected: boolean;
  instance_name: string;
  status: string;
  error: string;
}

interface WebhookStatus {
  configured: boolean;
  enabled: boolean;
  url: string;
  events: string[];
  error: string;
}

interface AISettings {
  auto_reply_enabled: boolean;
  auto_analysis_enabled: boolean;
  escalate_price: boolean;
  escalate_interest: boolean;
  custom_instructions: string;
  offer_parser_model: string;
  buyer_assistant_model: string;
  admin_chat_model: string;
  grouping_timeout_seconds: number;
}

export default function WhatsAppSettingsPage() {
  const [configStatus, setConfigStatus] = useState<ConfigStatus | null>(null);
  const [connectionResult, setConnectionResult] = useState<ConnectionTest | null>(null);
  const [webhookStatus, setWebhookStatus] = useState<WebhookStatus | null>(null);
  const [aiSettings, setAiSettings] = useState<AISettings>({
    auto_reply_enabled: true,
    auto_analysis_enabled: true,
    escalate_price: true,
    escalate_interest: true,
    custom_instructions: '',
    offer_parser_model: 'gpt-4o-mini',
    buyer_assistant_model: 'gpt-4o-mini',
    admin_chat_model: 'gpt-4o-mini',
    grouping_timeout_seconds: 600,
  });
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [configuringWebhook, setConfiguringWebhook] = useState(false);
  const [savingAi, setSavingAi] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [form, setForm] = useState({
    apiUrl: '',
    apiKey: '',
    instanceName: '',
  });

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    try {
      const [configRes, webhookRes, aiRes] = await Promise.allSettled([
        client.apiCall.invoke({ url: '/api/v1/whatsapp/config-status', method: 'GET' }),
        client.apiCall.invoke({ url: '/api/v1/whatsapp/webhook-status', method: 'GET' }),
        client.apiCall.invoke({ url: '/api/v1/whatsapp/ai-settings', method: 'GET' }),
      ]);

      if (configRes.status === 'fulfilled') {
        const configData = configRes.value.data;
        setConfigStatus(configData);
        if (configData.current_values) {
          setForm({
            apiUrl: configData.current_values.api_url || '',
            apiKey: '', // Never pre-fill API key for security
            instanceName: configData.current_values.instance_name || '',
          });
        }
      }
      if (webhookRes.status === 'fulfilled') {
        setWebhookStatus(webhookRes.value.data);
        if (webhookRes.value.data.url && !webhookUrl) {
          setWebhookUrl(webhookRes.value.data.url);
        }
      }
      if (aiRes.status === 'fulfilled') setAiSettings(prev => ({ ...prev, ...aiRes.value.data }));
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setConnectionResult(null);
    try {
      const res = await client.apiCall.invoke({ url: '/api/v1/whatsapp/test-connection', method: 'GET' });
      setConnectionResult(res.data);
      if (res.data.connected) {
        toast.success('Conexão com Evolution API estabelecida com sucesso!');
      } else {
        toast.error('Falha na conexão com Evolution API');
      }
    } catch (error: any) {
      const msg = error?.data?.detail || error?.message || 'Erro ao testar conexão';
      setConnectionResult({ connected: false, instance_name: '', status: '', error: msg });
      toast.error(msg);
    } finally {
      setTesting(false);
    }
  };

  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/whatsapp/save-settings',
        method: 'POST',
        data: {
          api_url: form.apiUrl,
          api_key: form.apiKey,
          instance_name: form.instanceName,
        },
      });
      if (res.data.success) {
        toast.success('Configurações salvas com sucesso!');
        setForm(prev => ({ ...prev, apiKey: '' }));
        loadAllData();
      } else {
        toast.error(res.data.error || 'Erro ao salvar configurações');
      }
    } catch (error: any) {
      toast.error('Erro ao salvar configurações');
    } finally {
      setSaving(false);
    }
  };

  const handleConfigureWebhook = async () => {
    if (!webhookUrl) {
      toast.error('Informe a URL do webhook');
      return;
    }
    setConfiguringWebhook(true);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/whatsapp/setup-webhook',
        method: 'POST',
        data: { webhook_url: webhookUrl },
      });
      if (res.data.success) {
        toast.success('Webhook configurado com sucesso!');
        loadAllData();
      } else {
        toast.error(res.data.error || 'Erro ao configurar webhook');
      }
    } catch (error: any) {
      toast.error(error?.data?.detail || 'Erro ao configurar webhook');
    } finally {
      setConfiguringWebhook(false);
    }
  };

  const handleSaveAiSettings = async () => {
    setSavingAi(true);
    try {
      await client.apiCall.invoke({
        url: '/api/v1/whatsapp/ai-settings',
        method: 'PUT',
        data: aiSettings,
      });
      toast.success('Configurações da IA salvas com sucesso!');
    } catch (error: any) {
      toast.error('Erro ao salvar configurações da IA');
    } finally {
      setSavingAi(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copiado para a área de transferência');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="flex items-center gap-2">
          <MessageSquare className="h-6 w-6 text-green-500" />
          Configurações WhatsApp
        </h1>
        <p className="text-muted-foreground mt-1">
          Configure a integração com Evolution API, webhook e assistente IA
        </p>
      </div>

      {/* Connection Status Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            {configStatus?.configured ? (
              <Wifi className="h-5 w-5 text-green-500" />
            ) : (
              <WifiOff className="h-5 w-5 text-red-500" />
            )}
            Status da Conexão
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <Badge variant={configStatus?.configured ? 'default' : 'destructive'}>
              {configStatus?.configured ? 'Configurado' : 'Não Configurado'}
            </Badge>
            {connectionResult?.connected && (
              <Badge className="bg-green-600 text-white">
                <CheckCircle className="h-3 w-3 mr-1" />
                Conectado - {connectionResult.status}
              </Badge>
            )}
            {connectionResult && !connectionResult.connected && (
              <Badge variant="destructive">
                <XCircle className="h-3 w-3 mr-1" />
                Desconectado
              </Badge>
            )}
          </div>

          {configStatus && !configStatus.configured && configStatus.missing_vars.length > 0 && (
            <Alert variant="destructive">
              <AlertDescription>
                Variáveis ausentes: <strong>{configStatus.missing_vars.join(', ')}</strong>.
              </AlertDescription>
            </Alert>
          )}

          {connectionResult?.error && (
            <Alert variant="destructive">
              <AlertDescription>{connectionResult.error}</AlertDescription>
            </Alert>
          )}

          <Button variant="outline" onClick={handleTestConnection} disabled={testing || !configStatus?.configured}>
            <RefreshCw className={`h-4 w-4 mr-2 ${testing ? 'animate-spin' : ''}`} />
            {testing ? 'Testando...' : 'Testar Conexão'}
          </Button>
        </CardContent>
      </Card>

      {/* Evolution API Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Configuração Evolution API
          </CardTitle>
          <CardDescription>
            Preencha os dados da sua instância Evolution API.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="apiUrl">URL da API Evolution</Label>
            <Input id="apiUrl" value={form.apiUrl} onChange={(e) => setForm({ ...form, apiUrl: e.target.value })} placeholder="https://seu-servidor-evolution.com" />
          </div>
          <div>
            <Label htmlFor="apiKey">API Key</Label>
            <Input id="apiKey" type="password" value={form.apiKey} onChange={(e) => setForm({ ...form, apiKey: e.target.value })} placeholder="Sua API Key" />
          </div>
          <div>
            <Label htmlFor="instanceName">Nome da Instância</Label>
            <Input id="instanceName" value={form.instanceName} onChange={(e) => setForm({ ...form, instanceName: e.target.value })} placeholder="nome-da-sua-instancia" />
          </div>
          <div className="flex gap-3 pt-2">
            <Button onClick={handleSaveSettings} disabled={saving || (!form.apiUrl && !form.apiKey && !form.instanceName)}>
              {saving ? 'Salvando...' : 'Salvar Configurações'}
            </Button>
            <Button variant="outline" onClick={() => setForm({ apiUrl: '', apiKey: '', instanceName: '' })}>Limpar</Button>
          </div>
        </CardContent>
      </Card>

      {/* Webhook Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Webhook className="h-5 w-5 text-blue-500" />
            Configuração Webhook
          </CardTitle>
          <CardDescription>
            Configure o webhook para receber mensagens automaticamente da Evolution API.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <Badge variant={webhookStatus?.enabled ? 'default' : 'outline'}>
              {webhookStatus?.enabled ? 'Webhook Ativo' : 'Webhook Inativo'}
            </Badge>
            {webhookStatus?.url && (
              <span className="text-xs text-muted-foreground truncate max-w-xs">{webhookStatus.url}</span>
            )}
          </div>

          {webhookStatus?.events && webhookStatus.events.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {webhookStatus.events.map((evt: string) => (
                <Badge key={evt} variant="secondary" className="text-xs">{evt}</Badge>
              ))}
            </div>
          )}

          <div>
            <Label htmlFor="webhookUrl">URL do Webhook</Label>
            <div className="flex gap-2">
              <Input
                id="webhookUrl"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://seu-servidor.com/api/v1/whatsapp/webhook"
              />
              <Button
                variant="outline"
                size="icon"
                onClick={() => copyToClipboard(webhookUrl)}
                title="Copiar URL"
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Esta é a URL que a Evolution API usará para enviar eventos de mensagem.
              Deve ser uma URL pública acessível.
            </p>
          </div>

          <Button
            onClick={handleConfigureWebhook}
            disabled={configuringWebhook || !webhookUrl || !configStatus?.configured}
          >
            <Webhook className="h-4 w-4 mr-2" />
            {configuringWebhook ? 'Configurando...' : 'Configurar Webhook'}
          </Button>
        </CardContent>
      </Card>

      {/* AI Assistant Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Bot className="h-5 w-5 text-purple-500" />
            Assistente IA - Atendimento ao Comprador
          </CardTitle>
          <CardDescription>
            Configure o comportamento do assistente virtual para respostas automáticas aos compradores.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label>Resposta Automática</Label>
              <p className="text-xs text-muted-foreground">Ativar respostas automáticas para mensagens de compradores</p>
            </div>
            <Switch
              checked={aiSettings.auto_reply_enabled}
              onCheckedChange={(checked) => setAiSettings({ ...aiSettings, auto_reply_enabled: checked })}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>Análise Automática de Ofertas</Label>
              <p className="text-xs text-muted-foreground">Analisar mensagens de fornecedores com IA e criar rascunhos automaticamente</p>
            </div>
            <Switch
              checked={aiSettings.auto_analysis_enabled}
              onCheckedChange={(checked) => setAiSettings({ ...aiSettings, auto_analysis_enabled: checked })}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>Escalar Negociação de Preço</Label>
              <p className="text-xs text-muted-foreground">Encaminhar ao admin quando comprador negociar preço</p>
            </div>
            <Switch
              checked={aiSettings.escalate_price}
              onCheckedChange={(checked) => setAiSettings({ ...aiSettings, escalate_price: checked })}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>Escalar Interesse de Compra</Label>
              <p className="text-xs text-muted-foreground">Encaminhar ao admin quando comprador demonstrar interesse</p>
            </div>
            <Switch
              checked={aiSettings.escalate_interest}
              onCheckedChange={(checked) => setAiSettings({ ...aiSettings, escalate_interest: checked })}
            />
          </div>

          <div>
            <Label>Timeout de Agrupamento (segundos)</Label>
            <Input
              type="number"
              min={30}
              max={600}
              value={aiSettings.grouping_timeout_seconds}
              onChange={(e) => {
                const val = parseInt(e.target.value) || 600;
                setAiSettings({ ...aiSettings, grouping_timeout_seconds: Math.max(30, Math.min(600, val)) });
              }}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Tempo de espera para agrupar mensagens consecutivas (30-600s). Padrão: 600s (10 min).
            </p>
          </div>

          <div>
            <Label>Instruções Personalizadas</Label>
            <Textarea
              value={aiSettings.custom_instructions}
              onChange={(e) => setAiSettings({ ...aiSettings, custom_instructions: e.target.value })}
              placeholder="Instruções adicionais para o assistente IA. Ex: Sempre mencionar que oferecemos garantia de 30 dias..."
              rows={3}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Instruções extras que o assistente seguirá ao responder compradores
            </p>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label>Modelo Parser de Ofertas</Label>
              <Input value={aiSettings.offer_parser_model} disabled className="bg-muted" />
            </div>
            <div>
              <Label>Modelo Assistente Comprador</Label>
              <Input value={aiSettings.buyer_assistant_model} disabled className="bg-muted" />
            </div>
            <div>
              <Label>Modelo Chat Admin</Label>
              <Input value={aiSettings.admin_chat_model} disabled className="bg-muted" />
            </div>
          </div>

          <Button onClick={handleSaveAiSettings} disabled={savingAi}>
            <Bot className="h-4 w-4 mr-2" />
            {savingAi ? 'Salvando...' : 'Salvar Configurações IA'}
          </Button>
        </CardContent>
      </Card>

      {/* Setup Instructions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">ℹ️ Como configurar</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p><strong>1.</strong> Instale e configure o <a href="https://github.com/EvolutionAPI/evolution-api" target="_blank" rel="noopener noreferrer" className="text-primary underline">Evolution API</a></p>
          <p><strong>2.</strong> Crie uma instância e conecte seu número WhatsApp via QR Code</p>
          <p><strong>3.</strong> Copie a URL, API Key e nome da instância para os campos acima</p>
          <p><strong>4.</strong> Configure o webhook apontando para: <code className="bg-muted px-1 py-0.5 rounded text-xs">/api/v1/whatsapp/webhook</code></p>
          <p><strong>5.</strong> Teste a conexão e ative o webhook</p>
          <p><strong>6.</strong> Configure o assistente IA para respostas automáticas</p>
          <p className="pt-2"><strong>Importante:</strong> Mensagens de fornecedores cadastrados serão automaticamente analisadas pela IA para criar rascunhos de ofertas.</p>
        </CardContent>
      </Card>
    </div>
  );
}
