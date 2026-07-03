import { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { MessageSquare, Search, RefreshCw, Sparkles, Eye, ExternalLink, Clock, CheckCircle, AlertCircle, FileText, Users } from 'lucide-react';
import { client } from '@/lib/api';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

interface Conversation {
  id: number;
  supplier_phone: string;
  supplier_name: string;
  status: string;
  offer_draft_id: number | null;
  last_message_at: string;
  message_count: number;
  ai_analysis: string;
  window_closed: boolean;
  created_at: string;
}

interface ConversationDetail {
  id: number;
  supplier_phone: string;
  supplier_name: string;
  status: string;
  offer_draft_id: number | null;
  last_message_at: string;
  message_count: number;
  ai_analysis: any;
  window_closed: boolean;
  created_at: string;
  messages: MessageItem[];
}

interface MessageItem {
  id: number;
  phone: string;
  contact_name: string;
  direction: string;
  message_type: string;
  content: string;
  media_url: string;
  processed: boolean;
  is_supplier: boolean;
  is_buyer: boolean;
  conversation_id: number | null;
  timestamp: string;
  created_at: string;
}

function getStatusBadge(status: string) {
  const map: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; icon: any }> = {
    active: { label: 'Ativa', variant: 'default', icon: Clock },
    analyzing: { label: 'Analisando', variant: 'secondary', icon: RefreshCw },
    draft_created: { label: 'Rascunho Criado', variant: 'default', icon: FileText },
    completed: { label: 'Concluída', variant: 'secondary', icon: CheckCircle },
    expired: { label: 'Expirada', variant: 'outline', icon: AlertCircle },
  };
  const info = map[status] || { label: status, variant: 'outline' as const, icon: AlertCircle };
  const Icon = info.icon;
  return (
    <Badge variant={info.variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {info.label}
    </Badge>
  );
}

export default function WhatsAppConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedConv, setSelectedConv] = useState<ConversationDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [analyzing, setAnalyzing] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'conversations' | 'messages'>('conversations');
  const navigate = useNavigate();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const convRes = await client.entities.whatsapp_conversations.query({ limit: 200, sort: '-last_message_at' });
      const convItems = convRes?.data?.items || [];
      setConversations(convItems);
    } catch (error: any) {
      console.error('Error loading conversations:', error);
      toast.error('Erro ao carregar conversas: ' + (error?.message || 'erro desconhecido'));
    }

    try {
      const msgRes = await client.entities.whatsapp_messages.query({ limit: 500, sort: '-id' });
      const msgItems = msgRes?.data?.items || [];
      setMessages(msgItems);
    } catch (error: any) {
      console.error('Error loading messages:', error);
      toast.error('Erro ao carregar mensagens: ' + (error?.message || 'erro desconhecido'));
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleViewConversation = async (conv: Conversation) => {
    setLoadingDetail(true);
    setDetailOpen(true);
    try {
      // Fetch messages for this conversation directly from the API
      const msgRes = await client.entities.whatsapp_messages.query({
        limit: 500,
        sort: 'id',
        query: { conversation_id: conv.id },
      });
      const convMessages = msgRes?.data?.items || [];
      setSelectedConv({
        ...conv,
        ai_analysis: conv.ai_analysis ? (typeof conv.ai_analysis === 'string' ? JSON.parse(conv.ai_analysis) : conv.ai_analysis) : null,
        messages: convMessages,
      });
    } catch (error: any) {
      // Fallback to pre-loaded messages
      const convMessages = messages.filter(m => m.conversation_id === conv.id);
      setSelectedConv({
        ...conv,
        ai_analysis: conv.ai_analysis ? (typeof conv.ai_analysis === 'string' ? JSON.parse(conv.ai_analysis) : conv.ai_analysis) : null,
        messages: convMessages,
      });
      toast.error('Erro ao carregar mensagens da conversa');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleTriggerAnalysis = async (conversationId: number) => {
    setAnalyzing(conversationId);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/whatsapp/trigger-analysis',
        method: 'POST',
        data: { conversation_id: conversationId },
        options: { timeout: 120_000 },
      });
      if (res.data?.offer_id) {
        toast.success(`Rascunho de oferta criado! Oferta #${res.data.offer_id}`);
      } else if (res.data?.error) {
        toast.error(res.data.error);
      } else {
        toast.success('Análise concluída!');
      }
      loadData();
    } catch (error: any) {
      toast.error(error?.data?.detail || 'Erro ao analisar conversa');
    } finally {
      setAnalyzing(null);
    }
  };

  const filtered = conversations.filter((c) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      (c.supplier_phone && c.supplier_phone.includes(s)) ||
      (c.supplier_name && c.supplier_name.toLowerCase().includes(s))
    );
  });

  const filteredMessages = messages.filter((m) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      (m.phone && m.phone.includes(s)) ||
      (m.contact_name && m.contact_name.toLowerCase().includes(s)) ||
      (m.content && m.content.toLowerCase().includes(s))
    );
  });

  const filteredByStatus = statusFilter
    ? filtered.filter(c => c.status === statusFilter)
    : filtered;

  const formatTimestamp = (ts: string) => {
    if (!ts) return '-';
    try {
      // Handle Unix timestamp (numeric string)
      const num = Number(ts);
      if (!isNaN(num) && num > 1_000_000_000 && num < 10_000_000_000) {
        return new Date(num * 1000).toLocaleString('pt-BR');
      }
      return new Date(ts).toLocaleString('pt-BR');
    } catch {
      return ts;
    }
  };

  const renderAiAnalysis = (analysis: any) => {
    if (!analysis) return <p className="text-muted-foreground text-sm">Nenhuma análise disponível</p>;
    if (analysis.error) return <p className="text-red-500 text-sm">{analysis.error}</p>;

    const fields = [
      { key: 'brand', label: 'Marca' },
      { key: 'model', label: 'Modelo' },
      { key: 'version', label: 'Versão' },
      { key: 'year', label: 'Ano' },
      { key: 'fuel', label: 'Combustível' },
      { key: 'auction', label: 'Leilão' },
      { key: 'mileage', label: 'KM' },
      { key: 'fipe_value', label: 'Valor FIPE' },
      { key: 'price', label: 'Preço' },
      { key: 'color', label: 'Cor' },
      { key: 'city', label: 'Cidade' },
      { key: 'photo_count', label: 'Fotos' },
      { key: 'video_count', label: 'Vídeos' },
    ];

    return (
      <div className="grid grid-cols-2 gap-2">
        {fields.map(({ key, label }) => (
          analysis[key] !== null && analysis[key] !== undefined && (
            <div key={key} className="text-sm">
              <span className="text-muted-foreground">{label}:</span>{' '}
              <span className="font-medium">{String(analysis[key])}</span>
            </div>
          )
        ))}
        {analysis.observations && (
          <div className="col-span-2 text-sm">
            <span className="text-muted-foreground">Observações:</span>{' '}
            <span>{analysis.observations}</span>
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <MessageSquare className="h-6 w-6 text-green-500" />
            Conversas WhatsApp
          </h1>
          <p className="text-muted-foreground mt-1">
            Mensagens recebidas e análise IA de ofertas
          </p>
        </div>
        <Button variant="outline" onClick={() => loadData()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Atualizar
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                <MessageSquare className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{messages.length}</p>
                <p className="text-sm text-muted-foreground">Mensagens recebidas</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{conversations.length}</p>
                <p className="text-sm text-muted-foreground">Conversas</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
                <Sparkles className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {conversations.filter(c => c.status === 'draft_created').length}
                </p>
                <p className="text-sm text-muted-foreground">Rascunhos IA</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tab Switcher */}
      <div className="flex gap-2">
        <Button
          variant={activeTab === 'conversations' ? 'default' : 'outline'}
          onClick={() => setActiveTab('conversations')}
        >
          <Users className="h-4 w-4 mr-2" />
          Conversas ({conversations.length})
        </Button>
        <Button
          variant={activeTab === 'messages' ? 'default' : 'outline'}
          onClick={() => setActiveTab('messages')}
        >
          <MessageSquare className="h-4 w-4 mr-2" />
          Mensagens ({messages.length})
        </Button>
      </div>

      {/* Search & Filter */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por telefone, nome ou conteúdo..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            {activeTab === 'conversations' && (
              <select
                className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">Todos os status</option>
                <option value="active">Ativas</option>
                <option value="analyzing">Analisando</option>
                <option value="draft_created">Rascunho Criado</option>
                <option value="completed">Concluídas</option>
                <option value="expired">Expiradas</option>
              </select>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {activeTab === 'conversations' ? (
            /* Conversations Table */
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Contato</TableHead>
                  <TableHead>Telefone</TableHead>
                  <TableHead>Mensagens</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Última Mensagem</TableHead>
                  <TableHead>Oferta</TableHead>
                  <TableHead className="text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredByStatus.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                      Nenhuma conversa encontrada. Envie uma mensagem WhatsApp para o número conectado!
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredByStatus.map((conv) => (
                    <TableRow key={conv.id}>
                      <TableCell className="font-mono">#{conv.id}</TableCell>
                      <TableCell className="font-medium">
                        {conv.supplier_name || 'Desconhecido'}
                      </TableCell>
                      <TableCell className="font-mono text-sm">{conv.supplier_phone}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{conv.message_count}</Badge>
                      </TableCell>
                      <TableCell>{getStatusBadge(conv.status)}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatTimestamp(conv.last_message_at)}
                      </TableCell>
                      <TableCell>
                        {conv.offer_draft_id ? (
                          <Button
                            variant="link"
                            className="h-auto p-0 text-primary"
                            onClick={() => navigate('/offers')}
                          >
                            #{conv.offer_draft_id}
                            <ExternalLink className="h-3 w-3 ml-1" />
                          </Button>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon" onClick={() => handleViewConversation(conv)} title="Ver detalhes">
                          <Eye className="h-4 w-4" />
                        </Button>
                        {conv.status === 'active' && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleTriggerAnalysis(conv.id)}
                            disabled={analyzing === conv.id}
                            title="Analisar com IA"
                          >
                            <Sparkles className="h-4 w-4 text-purple-500" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          ) : (
            /* Messages Table */
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Contato</TableHead>
                  <TableHead>Telefone</TableHead>
                  <TableHead>Direção</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Conteúdo</TableHead>
                  <TableHead>Data/Hora</TableHead>
                  <TableHead>Conv.</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredMessages.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                      Nenhuma mensagem encontrada
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredMessages.map((msg) => (
                    <TableRow key={msg.id}>
                      <TableCell className="font-mono">#{msg.id}</TableCell>
                      <TableCell className="font-medium">
                        {msg.contact_name || 'Desconhecido'}
                      </TableCell>
                      <TableCell className="font-mono text-sm">{msg.phone}</TableCell>
                      <TableCell>
                        <Badge variant={msg.direction === 'incoming' ? 'default' : 'secondary'}>
                          {msg.direction === 'incoming' ? '📥 Recebida' : '📤 Enviada'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{msg.message_type}</Badge>
                      </TableCell>
                      <TableCell className="max-w-xs truncate text-sm">
                        {msg.content || (msg.media_url ? '📎 Mídia' : '-')}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatTimestamp(msg.created_at || msg.timestamp)}
                      </TableCell>
                      <TableCell>
                        {msg.conversation_id ? (
                          <span className="font-mono text-sm">#{msg.conversation_id}</span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Conversation Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-green-500" />
              Conversa #{selectedConv?.id}
            </DialogTitle>
          </DialogHeader>
          {loadingDetail ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
            </div>
          ) : selectedConv ? (
            <div className="space-y-6">
              {/* Conversation Info */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Contato:</span>{' '}
                  <span className="font-medium">{selectedConv.supplier_name || 'Desconhecido'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Telefone:</span>{' '}
                  <span className="font-mono">{selectedConv.supplier_phone}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Status:</span>{' '}
                  {getStatusBadge(selectedConv.status)}
                </div>
                <div>
                  <span className="text-muted-foreground">Mensagens:</span>{' '}
                  <span className="font-medium">{selectedConv.message_count}</span>
                </div>
              </div>

              {/* AI Analysis */}
              {selectedConv.ai_analysis && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-purple-500" />
                      Análise IA
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {renderAiAnalysis(selectedConv.ai_analysis)}
                  </CardContent>
                </Card>
              )}

              {/* Offer Link */}
              {selectedConv.offer_draft_id && (
                <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                  <FileText className="h-4 w-4 text-primary" />
                  <span className="text-sm">Rascunho de oferta criado:</span>
                  <Button
                    variant="link"
                    className="h-auto p-0"
                    onClick={() => { setDetailOpen(false); navigate('/offers'); }}
                  >
                    Ver Oferta #{selectedConv.offer_draft_id}
                  </Button>
                </div>
              )}

              {/* Trigger Analysis Button */}
              {selectedConv.status === 'active' && !selectedConv.offer_draft_id && (
                <Button
                  onClick={() => handleTriggerAnalysis(selectedConv.id)}
                  disabled={analyzing === selectedConv.id}
                  className="w-full"
                >
                  <Sparkles className="h-4 w-4 mr-2" />
                  {analyzing === selectedConv.id ? 'Analisando com IA...' : 'Analisar Conversa com IA'}
                </Button>
              )}

              {/* Messages */}
              <div>
                <h3 className="text-sm font-medium mb-3">Mensagens</h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {selectedConv.messages?.map((msg) => (
                    <div
                      key={msg.id}
                      className={`p-3 rounded-lg text-sm ${
                        msg.direction === 'incoming'
                          ? 'bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800'
                          : 'bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium">
                          {msg.direction === 'incoming' ? '📥 Recebida' : '📤 Enviada'}
                          {msg.message_type !== 'text' && (
                            <Badge variant="outline" className="ml-2 text-xs">{msg.message_type}</Badge>
                          )}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {formatTimestamp(msg.created_at || msg.timestamp)}
                        </span>
                      </div>
                      {msg.content && <p>{msg.content}</p>}
                      {msg.media_url && (
                        <p className="text-xs text-muted-foreground mt-1">
                          📎 Mídia: {msg.media_url.substring(0, 60)}...
                        </p>
                      )}
                    </div>
                  ))}
                  {(!selectedConv.messages || selectedConv.messages.length === 0) && (
                    <p className="text-center text-muted-foreground py-4">Nenhuma mensagem</p>
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}