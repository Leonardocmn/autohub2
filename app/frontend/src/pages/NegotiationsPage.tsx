import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Handshake, Clock, XCircle, CheckCircle, MessageSquare } from 'lucide-react';
import { client } from '@/lib/api';
import { toast } from 'sonner';

interface Offer {
  id: number;
  code: string;
  title: string;
  brand: string;
  model: string;
  plate: string;
  price: number;
  status: string;
  negotiation_status: string;
  negotiation_substatus: string;
  negotiation_buyer_id: number;
  sold_buyer_id?: number;
  sold_at?: string;
  doc_status: string;
  vehicle_status: string;
  distributed_at: string;
  negotiation_deadline_hours: number;
}

interface Buyer {
  id: number;
  name: string;
  phone: string;
}

interface NegotiationHistoryItem {
  id: number;
  offer_id: number;
  admin_name: string;
  previous_status: string;
  new_status: string;
  buyer_id: number;
  observations: string;
  created_at: string;
}

export default function NegotiationsPage() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [history, setHistory] = useState<NegotiationHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [historyDialogOpen, setHistoryDialogOpen] = useState(false);
  const [selectedOffer, setSelectedOffer] = useState<Offer | null>(null);
  const [selectedOfferHistory, setSelectedOfferHistory] = useState<NegotiationHistoryItem[]>([]);
  const [negotiationForm, setNegotiationForm] = useState({
    negotiation_status: '',
    negotiation_substatus: 'none',
    negotiation_buyer_id: '',
    doc_status: 'none',
    vehicle_status: 'none',
    observations: '',
  });
  const [whatsappConfigured, setWhatsappConfigured] = useState(false);
  const [sendingWhatsApp, setSendingWhatsApp] = useState<number | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [offersRes, buyersRes, historyRes, waRes] = await Promise.all([
        client.entities.offers.query({ limit: 500 }),
        client.entities.buyers.query({ limit: 500 }),
        client.entities.negotiation_history.query({ limit: 1000, sort: '-created_at' }),
        client.apiCall.invoke({ url: '/api/v1/whatsapp/config-status', method: 'GET' }).catch(() => ({ data: { configured: false } })),
      ]);
      const allOffers = offersRes?.data?.items || [];
      setOffers(allOffers.filter((o: Offer) => o.status === 'distributed' || o.status === 'negotiating'));
      setBuyers(buyersRes?.data?.items || []);
      setHistory(historyRes?.data?.items || []);
      setWhatsappConfigured(waRes?.data?.configured || false);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSendWhatsAppUpdate = async (offer: Offer) => {
    if (!offer.negotiation_buyer_id) {
      toast.error('Nenhum comprador vinculado a esta oferta');
      return;
    }
    const buyer = buyers.find((b) => b.id === offer.negotiation_buyer_id);
    if (!buyer?.phone) {
      toast.error('Comprador sem telefone cadastrado');
      return;
    }
    setSendingWhatsApp(offer.id);
    try {
      const statusLabels: Record<string, string> = {
        awaiting_update: 'Aguardando Atualização',
        not_negotiated: 'Não Negociado',
        negotiated: 'Negociado',
      };
      const res = await client.apiCall.invoke({
        url: '/api/v1/whatsapp/send-negotiation-update',
        method: 'POST',
        data: {
          phone: buyer.phone,
          offer: {
            code: offer.code,
            title: offer.title,
            brand: offer.brand,
            model: offer.model,
            price: offer.price,
          },
          buyer_name: buyer.name,
          status_label: statusLabels[offer.negotiation_status] || offer.negotiation_status,
        },
      });
      if (res.data?.success) {
        toast.success(`WhatsApp: atualização enviada para ${buyer.name}`);
      } else {
        toast.error(res.data?.error || 'Erro ao enviar mensagem WhatsApp');
      }
    } catch (err: any) {
      toast.error(err?.data?.detail || 'Erro ao enviar mensagem WhatsApp');
    } finally {
      setSendingWhatsApp(null);
    }
  };

  const getBuyerName = (id: number) => buyers.find((b) => b.id === id)?.name || '-';

  const getNegotiationStatusBadge = (status: string) => {
    const map: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
      awaiting_update: { label: 'Aguardando Atualização', variant: 'outline' },
      not_negotiated: { label: 'Não Negociado', variant: 'secondary' },
      negotiated: { label: 'Negociado', variant: 'default' },
    };
    const info = map[status] || { label: status, variant: 'outline' as const };
    return <Badge variant={info.variant}>{info.label}</Badge>;
  };

  const getSubstatusBadge = (substatus: string) => {
    if (substatus === 'entered') return <Badge className="bg-green-600 text-white">Entrou</Badge>;
    if (substatus === 'not_entered') return <Badge variant="destructive">Não Entrou</Badge>;
    return null;
  };

  const openNegotiation = (offer: Offer) => {
    setSelectedOffer(offer);
    setNegotiationForm({
      negotiation_status: offer.negotiation_status || 'awaiting_update',
      negotiation_substatus: offer.negotiation_substatus || 'none',
      negotiation_buyer_id: offer.negotiation_buyer_id ? String(offer.negotiation_buyer_id) : '',
      doc_status: offer.doc_status || 'none',
      vehicle_status: offer.vehicle_status || 'none',
      observations: '',
    });
    setDialogOpen(true);
  };

  const openHistory = (offer: Offer) => {
    const offerHistory = history.filter((h) => h.offer_id === offer.id);
    setSelectedOffer(offer);
    setSelectedOfferHistory(offerHistory);
    setHistoryDialogOpen(true);
  };

  const handleSaveNegotiation = async () => {
    if (!selectedOffer) return;
    try {
      const previousStatus = selectedOffer.negotiation_status;
      const updateData: Record<string, unknown> = {
        negotiation_status: negotiationForm.negotiation_status,
        negotiation_substatus: negotiationForm.negotiation_substatus,
        negotiation_buyer_id: negotiationForm.negotiation_buyer_id
          ? Number(negotiationForm.negotiation_buyer_id)
          : null,
        doc_status: negotiationForm.doc_status,
        vehicle_status: negotiationForm.vehicle_status,
      };

      if (negotiationForm.negotiation_status === 'negotiated') {
        updateData.status = 'negotiating';
      }

      await client.entities.offers.update({
        id: String(selectedOffer.id),
        data: updateData,
      });

      // Record history
      await client.entities.negotiation_history.create({
        data: {
          offer_id: selectedOffer.id,
          admin_name: 'Administrador',
          previous_status: previousStatus,
          new_status: negotiationForm.negotiation_status,
          buyer_id: negotiationForm.negotiation_buyer_id
            ? Number(negotiationForm.negotiation_buyer_id)
            : null,
          observations: negotiationForm.observations,
        },
      });

      toast.success('Negociação atualizada com sucesso');
      setDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error('Erro ao atualizar negociação');
    }
  };

  const handleRegisterSale = async (offer: Offer) => {
    if (!offer.negotiation_buyer_id) {
      toast.error('Selecione o comprador antes de registrar a venda');
      return;
    }
    if (!offer.plate) {
      toast.error('A oferta precisa ter placa para criar o dossie');
      return;
    }
    try {
      await client.apiCall.invoke({
        url: '/api/v1/vehicle-dossiers/register-sale',
        method: 'POST',
        data: {
          offer_id: offer.id,
          buyer_id: offer.negotiation_buyer_id,
          notes: 'Venda registrada pela tela de negociacoes',
        },
      });
      toast.success('Venda registrada e dossie atualizado');
      loadData();
    } catch (error: any) {
      toast.error(error?.data?.detail || 'Erro ao registrar venda');
    }
  };

  const awaitingOffers = offers.filter((o) => o.negotiation_status === 'awaiting_update');
  const negotiatedOffers = offers.filter(
    (o) => o.negotiation_status === 'negotiated' && o.negotiation_substatus === 'entered'
  );
  const notEnteredOffers = offers.filter(
    (o) => o.negotiation_status === 'negotiated' && o.negotiation_substatus === 'not_entered'
  );
  const notNegotiatedOffers = offers.filter((o) => o.negotiation_status === 'not_negotiated');

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const renderOfferRow = (offer: Offer) => (
    <TableRow key={offer.id}>
      <TableCell className="font-mono text-primary font-medium">#{offer.code}</TableCell>
      <TableCell>
        <div>
          <p className="font-medium">{offer.title}</p>
          <p className="text-xs text-muted-foreground">{offer.brand} {offer.model}</p>
        </div>
      </TableCell>
      <TableCell>{getNegotiationStatusBadge(offer.negotiation_status)}</TableCell>
      <TableCell>{getSubstatusBadge(offer.negotiation_substatus)}</TableCell>
      <TableCell>{offer.negotiation_buyer_id ? getBuyerName(offer.negotiation_buyer_id) : '-'}</TableCell>
      <TableCell className="text-right space-x-1">
        <Button variant="outline" size="sm" onClick={() => openNegotiation(offer)}>
          Atualizar
        </Button>
        <Button variant="ghost" size="sm" onClick={() => openHistory(offer)}>
          Histórico
        </Button>
        {offer.negotiation_buyer_id && offer.plate && (
          <Button variant="outline" size="sm" onClick={() => handleRegisterSale(offer)}>
            Registrar venda
          </Button>
        )}
        {whatsappConfigured && offer.negotiation_buyer_id && (
          <Button
            variant="outline"
            size="sm"
            className="text-green-600 border-green-300 hover:bg-green-50"
            onClick={() => handleSendWhatsAppUpdate(offer)}
            disabled={sendingWhatsApp === offer.id}
          >
            <MessageSquare className="h-3 w-3 mr-1" />
            {sendingWhatsApp === offer.id ? 'Enviando...' : 'WhatsApp'}
          </Button>
        )}
      </TableCell>
    </TableRow>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1>Negociações</h1>
        <p className="text-muted-foreground mt-1">
          Acompanhe e gerencie as negociações das ofertas distribuídas
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Clock className="h-4 w-4 text-amber-500" />
              Aguardando
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{awaitingOffers.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Entrou
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{negotiatedOffers.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <XCircle className="h-4 w-4 text-red-500" />
              Não Entrou
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{notEnteredOffers.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Handshake className="h-4 w-4 text-muted-foreground" />
              Não Negociado
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{notNegotiatedOffers.length}</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="awaiting">
        <TabsList>
          <TabsTrigger value="awaiting">Aguardando ({awaitingOffers.length})</TabsTrigger>
          <TabsTrigger value="entered">Entrou ({negotiatedOffers.length})</TabsTrigger>
          <TabsTrigger value="not_entered">Não Entrou ({notEnteredOffers.length})</TabsTrigger>
          <TabsTrigger value="not_negotiated">Não Negociado ({notNegotiatedOffers.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="awaiting">
          <Card>
            <CardContent className="pt-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Código</TableHead>
                    <TableHead>Veículo</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Substatus</TableHead>
                    <TableHead>Comprador</TableHead>
                    <TableHead className="text-right">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {awaitingOffers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                        Nenhuma oferta aguardando atualização
                      </TableCell>
                    </TableRow>
                  ) : (
                    awaitingOffers.map(renderOfferRow)
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="entered">
          <Card>
            <CardContent className="pt-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Código</TableHead>
                    <TableHead>Veículo</TableHead>
                    <TableHead>Comprador</TableHead>
                    <TableHead>Documentação</TableHead>
                    <TableHead>Situação Veículo</TableHead>
                    <TableHead className="text-right">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {negotiatedOffers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                        Nenhuma negociação em andamento
                      </TableCell>
                    </TableRow>
                  ) : (
                    negotiatedOffers.map((offer) => (
                      <TableRow key={offer.id}>
                        <TableCell className="font-mono text-primary font-medium">#{offer.code}</TableCell>
                        <TableCell>
                          <p className="font-medium">{offer.title}</p>
                        </TableCell>
                        <TableCell>{getBuyerName(offer.negotiation_buyer_id)}</TableCell>
                        <TableCell>
                          <Badge variant={offer.doc_status === 'ok' ? 'default' : 'outline'}>
                            {offer.doc_status === 'ok' ? 'OK' : offer.doc_status === 'pending' ? 'Pendente' : '-'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {offer.vehicle_status === 'in_exchange' && 'Em Troca'}
                            {offer.vehicle_status === 'available_pickup' && 'Disponível Retirada'}
                            {offer.vehicle_status === 'picked_up' && 'Retirado'}
                            {offer.vehicle_status === 'none' && '-'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right space-x-1">
                          <Button variant="outline" size="sm" onClick={() => openNegotiation(offer)}>
                            Atualizar
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => openHistory(offer)}>
                            Histórico
                          </Button>
                          {whatsappConfigured && offer.negotiation_buyer_id && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-green-600 border-green-300 hover:bg-green-50"
                              onClick={() => handleSendWhatsAppUpdate(offer)}
                              disabled={sendingWhatsApp === offer.id}
                            >
                              <MessageSquare className="h-3 w-3 mr-1" />
                              {sendingWhatsApp === offer.id ? 'Enviando...' : 'WhatsApp'}
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="not_entered">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Negociações Não Concluídas</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Código</TableHead>
                    <TableHead>Veículo</TableHead>
                    <TableHead>Comprador Vinculado</TableHead>
                    <TableHead className="text-right">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {notEnteredOffers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                        Nenhuma negociação não concluída
                      </TableCell>
                    </TableRow>
                  ) : (
                    notEnteredOffers.map((offer) => (
                      <TableRow key={offer.id}>
                        <TableCell className="font-mono text-primary font-medium">#{offer.code}</TableCell>
                        <TableCell>{offer.title}</TableCell>
                        <TableCell>{getBuyerName(offer.negotiation_buyer_id)}</TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm" onClick={() => openHistory(offer)}>
                            Histórico
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="not_negotiated">
          <Card>
            <CardContent className="pt-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Código</TableHead>
                    <TableHead>Veículo</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {notNegotiatedOffers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                        Nenhuma oferta sem negociação
                      </TableCell>
                    </TableRow>
                  ) : (
                    notNegotiatedOffers.map((offer) => (
                      <TableRow key={offer.id}>
                        <TableCell className="font-mono text-primary font-medium">#{offer.code}</TableCell>
                        <TableCell>{offer.title}</TableCell>
                        <TableCell>{getNegotiationStatusBadge(offer.negotiation_status)}</TableCell>
                        <TableCell className="text-right">
                          <Button variant="outline" size="sm" onClick={() => openNegotiation(offer)}>
                            Atualizar
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Negotiation Update Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              Atualizar Negociação - #{selectedOffer?.code}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Status da Negociação</Label>
              <select
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1"
                value={negotiationForm.negotiation_status}
                onChange={(e) =>
                  setNegotiationForm({
                    ...negotiationForm,
                    negotiation_status: e.target.value,
                    negotiation_substatus: e.target.value === 'negotiated' ? negotiationForm.negotiation_substatus : 'none',
                  })
                }
              >
                <option value="awaiting_update">Aguardando Atualização</option>
                <option value="not_negotiated">Não Negociado</option>
                <option value="negotiated">Negociado</option>
              </select>
            </div>

            {negotiationForm.negotiation_status === 'negotiated' && (
              <>
                <div>
                  <Label>Comprador Responsável *</Label>
                  <select
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1"
                    value={negotiationForm.negotiation_buyer_id}
                    onChange={(e) =>
                      setNegotiationForm({ ...negotiationForm, negotiation_buyer_id: e.target.value })
                    }
                  >
                    <option value="">Selecione o comprador</option>
                    {buyers.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name} - {b.phone}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <Label>Substatus</Label>
                  <select
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1"
                    value={negotiationForm.negotiation_substatus}
                    onChange={(e) =>
                      setNegotiationForm({ ...negotiationForm, negotiation_substatus: e.target.value })
                    }
                  >
                    <option value="none">Selecione</option>
                    <option value="entered">Entrou</option>
                    <option value="not_entered">Não Entrou</option>
                  </select>
                </div>

                {negotiationForm.negotiation_substatus === 'entered' && (
                  <>
                    <div>
                      <Label>Status da Documentação</Label>
                      <select
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1"
                        value={negotiationForm.doc_status}
                        onChange={(e) =>
                          setNegotiationForm({ ...negotiationForm, doc_status: e.target.value })
                        }
                      >
                        <option value="none">-</option>
                        <option value="pending">Documentação Pendente</option>
                        <option value="ok">Documentação OK</option>
                      </select>
                    </div>
                    <div>
                      <Label>Situação do Veículo</Label>
                      <select
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1"
                        value={negotiationForm.vehicle_status}
                        onChange={(e) =>
                          setNegotiationForm({ ...negotiationForm, vehicle_status: e.target.value })
                        }
                      >
                        <option value="none">-</option>
                        <option value="in_exchange">Veículo em Processo de Troca</option>
                        <option value="available_pickup">Veículo Disponível para Retirada</option>
                        <option value="picked_up">Veículo Retirado</option>
                      </select>
                    </div>
                  </>
                )}
              </>
            )}

            <div>
              <Label>Observações</Label>
              <Textarea
                value={negotiationForm.observations}
                onChange={(e) =>
                  setNegotiationForm({ ...negotiationForm, observations: e.target.value })
                }
                placeholder="Observações sobre a negociação..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleSaveNegotiation}
              disabled={
                negotiationForm.negotiation_status === 'negotiated' &&
                !negotiationForm.negotiation_buyer_id
              }
            >
              Salvar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* History Dialog */}
      <Dialog open={historyDialogOpen} onOpenChange={setHistoryDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              Histórico - #{selectedOffer?.code} {selectedOffer?.title}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            {selectedOfferHistory.length === 0 ? (
              <p className="text-center text-muted-foreground py-4">
                Nenhum registro de histórico
              </p>
            ) : (
              selectedOfferHistory.map((item) => (
                <div key={item.id} className="border rounded-lg p-3 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{item.admin_name}</span>
                    <span className="text-xs text-muted-foreground">
                      {item.created_at ? new Date(item.created_at).toLocaleString('pt-BR') : '-'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Badge variant="outline">{item.previous_status || '-'}</Badge>
                    <span>→</span>
                    <Badge variant="default">{item.new_status}</Badge>
                  </div>
                  {item.buyer_id && (
                    <p className="text-xs text-muted-foreground">
                      Comprador: {getBuyerName(item.buyer_id)}
                    </p>
                  )}
                  {item.observations && (
                    <p className="text-sm text-muted-foreground italic">
                      "{item.observations}"
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
