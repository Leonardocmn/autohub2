import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Send, Users, MessageSquare, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { client } from '@/lib/api';
import { toast } from 'sonner';

interface WhatsAppResult {
  buyer_id: number;
  buyer_name: string;
  phone: string;
  success: boolean;
  error: string;
}

interface Offer {
  id: number;
  code: string;
  title: string;
  brand: string;
  model: string;
  price: number;
  status: string;
}

interface Category {
  id: number;
  name: string;
}

interface Buyer {
  id: number;
  name: string;
  phone: string;
  status: string;
}

interface BuyerCategory {
  id: number;
  buyer_id: number;
  category_id: number;
}

export default function DistributionPage() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [buyerCategories, setBuyerCategories] = useState<BuyerCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedOffer, setSelectedOffer] = useState<Offer | null>(null);
  const [selectedCategories, setSelectedCategories] = useState<number[]>([]);
  const [distributing, setDistributing] = useState(false);
  const [sendWhatsApp, setSendWhatsApp] = useState(false);
  const [whatsappResults, setWhatsappResults] = useState<WhatsAppResult[]>([]);
  const [whatsappConfigured, setWhatsappConfigured] = useState(false);
  const [resultsDialogOpen, setResultsDialogOpen] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [offersRes, catsRes, buyersRes, bcRes, waRes] = await Promise.all([
        client.entities.offers.query({ query: { status: 'approved' }, limit: 200 }),
        client.entities.categories.query({ limit: 200 }),
        client.entities.buyers.query({ limit: 500 }),
        client.entities.buyer_categories.query({ limit: 2000 }),
        client.apiCall.invoke({ url: '/api/v1/whatsapp/config-status', method: 'GET' }).catch(() => ({ data: { configured: false, missing_vars: [] } })),
      ]);
      setOffers(offersRes?.data?.items || []);
      setCategories(catsRes?.data?.items || []);
      setBuyers(buyersRes?.data?.items || []);
      setBuyerCategories(bcRes?.data?.items || []);
      setWhatsappConfigured(waRes?.data?.configured || false);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getDeduplicatedBuyers = () => {
    const buyerIds = new Set<number>();
    for (const catId of selectedCategories) {
      const bcsInCat = buyerCategories.filter((bc) => bc.category_id === catId);
      for (const bc of bcsInCat) {
        const buyer = buyers.find((b) => b.id === bc.buyer_id);
        if (buyer && buyer.status === 'active') {
          buyerIds.add(bc.buyer_id);
        }
      }
    }
    return buyers.filter((b) => buyerIds.has(b.id));
  };

  const handleDistribute = async () => {
    if (!selectedOffer || selectedCategories.length === 0) return;
    setDistributing(true);
    setWhatsappResults([]);
    try {
      const dedupBuyers = getDeduplicatedBuyers();
      for (const buyer of dedupBuyers) {
        const catId = buyerCategories.find(
          (bc) => bc.buyer_id === buyer.id && selectedCategories.includes(bc.category_id)
        )?.category_id;
        await client.entities.offer_distributions.create({
          data: {
            offer_id: selectedOffer.id,
            buyer_id: buyer.id,
            category_id: catId || selectedCategories[0],
            sent_at: new Date().toISOString(),
          },
        });
      }
      await client.entities.offers.update({
        id: String(selectedOffer.id),
        data: {
          status: 'distributed',
          distributed_at: new Date().toISOString(),
          negotiation_status: 'awaiting_update',
        },
      });

      // Send WhatsApp messages if enabled and configured
      const waResults: WhatsAppResult[] = [];
      if (sendWhatsApp && whatsappConfigured) {
        for (const buyer of dedupBuyers) {
          if (buyer.phone) {
            try {
              const res = await client.apiCall.invoke({
                url: '/api/v1/whatsapp/send-offer',
                method: 'POST',
                data: {
                  phone: buyer.phone,
                  offer: {
                    code: selectedOffer.code,
                    title: selectedOffer.title,
                    brand: selectedOffer.brand,
                    model: selectedOffer.model,
                    price: selectedOffer.price,
                  },
                },
              });
              waResults.push({
                buyer_id: buyer.id,
                buyer_name: buyer.name,
                phone: buyer.phone,
                success: res.data?.success || false,
                error: res.data?.error || '',
              });
            } catch (err: any) {
              waResults.push({
                buyer_id: buyer.id,
                buyer_name: buyer.name,
                phone: buyer.phone,
                success: false,
                error: err?.data?.detail || err?.message || 'Erro ao enviar',
              });
            }
          } else {
            waResults.push({
              buyer_id: buyer.id,
              buyer_name: buyer.name,
              phone: buyer.phone || '-',
              success: false,
              error: 'Comprador sem telefone',
            });
          }
        }
        setWhatsappResults(waResults);
        const successCount = waResults.filter((r) => r.success).length;
        if (successCount > 0) {
          toast.success(`WhatsApp: ${successCount}/${dedupBuyers.length} mensagens enviadas`);
        }
        setResultsDialogOpen(true);
      } else {
        toast.success(`Oferta distribuída para ${dedupBuyers.length} comprador(es)`);
      }

      setDialogOpen(false);
      setSelectedOffer(null);
      setSelectedCategories([]);
      loadData();
    } catch (error) {
      toast.error('Erro ao distribuir oferta');
    } finally {
      setDistributing(false);
    }
  };

  const openDistribute = (offer: Offer) => {
    setSelectedOffer(offer);
    setSelectedCategories([]);
    setDialogOpen(true);
  };

  const toggleCategory = (catId: number) => {
    setSelectedCategories((prev) =>
      prev.includes(catId) ? prev.filter((id) => id !== catId) : [...prev, catId]
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
      <div>
        <h1>Distribuição</h1>
        <p className="text-muted-foreground mt-1">
          Distribua ofertas aprovadas para compradores por categoria
        </p>
      </div>

      {offers.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Send className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              Nenhuma oferta aprovada aguardando distribuição
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {offers.map((offer) => (
            <Card key={offer.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <Badge variant="outline" className="font-mono">
                    #{offer.code}
                  </Badge>
                  <Badge variant="secondary">Aprovada</Badge>
                </div>
                <CardTitle className="text-base mt-2">{offer.title}</CardTitle>
                <p className="text-sm text-muted-foreground">
                  {offer.brand} {offer.model}
                </p>
              </CardHeader>
              <CardContent>
                {offer.price && (
                  <p className="text-lg font-bold text-primary mb-3">
                    R$ {Number(offer.price).toLocaleString('pt-BR')}
                  </p>
                )}
                <Button className="w-full" onClick={() => openDistribute(offer)}>
                  <Send className="h-4 w-4 mr-2" />
                  Distribuir
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              Distribuir Oferta #{selectedOffer?.code}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Selecione as categorias de compradores que receberão esta oferta:
            </p>
            <div className="space-y-2 max-h-48 overflow-y-auto border rounded-md p-3">
              {categories.map((cat) => {
                const buyerCount = buyerCategories.filter(
                  (bc) => bc.category_id === cat.id
                ).length;
                return (
                  <div key={cat.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Checkbox
                        checked={selectedCategories.includes(cat.id)}
                        onCheckedChange={() => toggleCategory(cat.id)}
                      />
                      <span className="text-sm">{cat.name}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {buyerCount} comprador(es)
                    </span>
                  </div>
                );
              })}
            </div>

            {selectedCategories.length > 0 && (
              <div className="border rounded-md p-3 bg-muted/50">
                <div className="flex items-center gap-2 mb-2">
                  <Users className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium">
                    Destinatários (com deduplicação):
                  </span>
                </div>
                <p className="text-2xl font-bold text-primary">
                  {getDeduplicatedBuyers().length} comprador(es)
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Compradores em múltiplas categorias receberão apenas uma mensagem
                </p>
              </div>
            )}

            {whatsappConfigured && selectedCategories.length > 0 && (
              <div className="border rounded-md p-3 bg-green-50 dark:bg-green-950/20">
                <div className="flex items-center gap-2">
                  <Checkbox
                    checked={sendWhatsApp}
                    onCheckedChange={(checked) => setSendWhatsApp(checked === true)}
                  />
                  <MessageSquare className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-medium">
                    Enviar via WhatsApp
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1 ml-7">
                  Envia a oferta como mensagem WhatsApp para cada comprador com telefone cadastrado
                </p>
              </div>
            )}

            {!whatsappConfigured && selectedCategories.length > 0 && (
              <div className="border rounded-md p-3 bg-muted/30">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <MessageSquare className="h-4 w-4" />
                  <span className="text-sm">
                    WhatsApp não configurado —{' '}
                    <a href="/whatsapp-settings" className="text-primary underline">
                      Configurar
                    </a>
                  </span>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleDistribute}
              disabled={selectedCategories.length === 0 || distributing}
            >
              {distributing ? 'Distribuindo...' : 'Confirmar Distribuição'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* WhatsApp Results Dialog */}
      <Dialog open={resultsDialogOpen} onOpenChange={setResultsDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-green-600" />
              Resultado do Envio WhatsApp
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {whatsappResults.map((result, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between border rounded-md p-3"
              >
                <div className="flex items-center gap-2">
                  {result.success ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-500" />
                  )}
                  <div>
                    <p className="text-sm font-medium">{result.buyer_name}</p>
                    <p className="text-xs text-muted-foreground">{result.phone}</p>
                  </div>
                </div>
                {!result.success && (
                  <div className="flex items-center gap-1 text-xs text-red-500">
                    <AlertCircle className="h-3 w-3" />
                    {result.error}
                  </div>
                )}
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button onClick={() => setResultsDialogOpen(false)}>Fechar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}