import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Search, Eye } from 'lucide-react';
import { client } from '@/lib/api';

interface Offer {
  id: number;
  code: string;
  supplier_id: number;
  title: string;
  brand: string;
  model: string;
  year: string;
  price: number;
  status: string;
  negotiation_status: string;
  negotiation_substatus: string;
  negotiation_buyer_id: number;
  sold_buyer_id?: number;
  sold_at?: string;
  plate?: string;
  doc_status: string;
  vehicle_status: string;
  finalized_at: string;
  created_at: string;
}

interface Supplier {
  id: number;
  name: string;
}

interface Buyer {
  id: number;
  name: string;
}

export default function HistoryPage() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedOffer, setSelectedOffer] = useState<Offer | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [offersRes, suppliersRes, buyersRes] = await Promise.all([
        client.entities.offers.query({ limit: 500, sort: '-created_at' }),
        client.entities.suppliers.query({ limit: 200 }),
        client.entities.buyers.query({ limit: 500 }),
      ]);
      const allOffers = offersRes?.data?.items || [];
      setOffers(allOffers.filter((o: Offer) => o.status === 'sold' || o.status === 'cancelled'));
      setSuppliers(suppliersRes?.data?.items || []);
      setBuyers(buyersRes?.data?.items || []);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSupplierName = (id: number) => suppliers.find((s) => s.id === id)?.name || '-';
  const getBuyerName = (id?: number) => id ? buyers.find((b) => b.id === id)?.name || '-' : '-';

  const handleFinalize = async (offer: Offer) => {
    try {
      await client.entities.offers.update({
        id: String(offer.id),
        data: { status: 'sold', finalized_at: new Date().toISOString() },
      });
      loadData();
    } catch (error) {
      console.error('Error finalizing:', error);
    }
  };

  const getStatusBadge = (status: string) => {
    if (status === 'sold') return <Badge className="bg-green-600 text-white">Vendido</Badge>;
    if (status === 'cancelled') return <Badge variant="destructive">Cancelada</Badge>;
    return <Badge variant="outline">{status}</Badge>;
  };

  const filtered = offers.filter((o) => {
    const q = search.toLowerCase();
    return (
      (o.code && o.code.includes(q)) ||
      (o.title && o.title.toLowerCase().includes(q)) ||
      (o.brand && o.brand.toLowerCase().includes(q)) ||
      (o.model && o.model.toLowerCase().includes(q)) ||
      getSupplierName(o.supplier_id).toLowerCase().includes(q)
    );
  });

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
        <h1>Histórico</h1>
        <p className="text-muted-foreground mt-1">
          Consulte ofertas finalizadas (vendidas ou canceladas)
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por código, marca, modelo ou fornecedor..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <CardTitle className="text-sm text-muted-foreground">
              {filtered.length} registro(s)
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Veículo</TableHead>
                <TableHead>Fornecedor</TableHead>
                <TableHead>Preço</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Finalizado em</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                    Nenhum registro encontrado
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((offer) => (
                  <TableRow key={offer.id}>
                    <TableCell className="font-mono text-primary font-medium">#{offer.code}</TableCell>
                    <TableCell>
                      <div>
                        <p className="font-medium">{offer.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {offer.brand} {offer.model} {offer.year}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{getSupplierName(offer.supplier_id)}</TableCell>
                    <TableCell>
                      {offer.price ? `R$ ${Number(offer.price).toLocaleString('pt-BR')}` : '-'}
                    </TableCell>
                    <TableCell>{getStatusBadge(offer.status)}</TableCell>
                    <TableCell>
                      {offer.finalized_at
                        ? new Date(offer.finalized_at).toLocaleDateString('pt-BR')
                        : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setSelectedOffer(offer);
                          setDetailOpen(true);
                        }}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              Detalhes - #{selectedOffer?.code} {selectedOffer?.title}
            </DialogTitle>
          </DialogHeader>
          {selectedOffer && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Marca / Modelo</p>
                  <p className="font-medium">{selectedOffer.brand} {selectedOffer.model}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Ano</p>
                  <p className="font-medium">{selectedOffer.year || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Preço</p>
                  <p className="font-medium">
                    {selectedOffer.price ? `R$ ${Number(selectedOffer.price).toLocaleString('pt-BR')}` : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Fornecedor</p>
                  <p className="font-medium">{getSupplierName(selectedOffer.supplier_id)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status Final</p>
                  {getStatusBadge(selectedOffer.status)}
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Comprador Negociação</p>
                  <p className="font-medium">
                    {selectedOffer.negotiation_buyer_id
                      ? getBuyerName(selectedOffer.negotiation_buyer_id)
                      : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Documentação</p>
                  <p className="font-medium">
                    {selectedOffer.doc_status === 'ok' ? 'OK' : selectedOffer.doc_status === 'pending' ? 'Pendente' : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Situação Veículo</p>
                  <p className="font-medium">
                    {selectedOffer.vehicle_status === 'picked_up' && 'Retirado'}
                    {selectedOffer.vehicle_status === 'available_pickup' && 'Disponível Retirada'}
                    {selectedOffer.vehicle_status === 'in_exchange' && 'Em Troca'}
                    {selectedOffer.vehicle_status === 'none' && '-'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
