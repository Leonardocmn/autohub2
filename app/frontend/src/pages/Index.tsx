import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Car,
  Clock,
  CheckCircle,
  Send,
  Users,
  Truck,
  TrendingUp,
  AlertTriangle,
  XCircle,
  Handshake,
  FileCheck,
  BarChart3,
} from 'lucide-react';
import { client } from '@/lib/api';

interface DashboardStats {
  totalOffers: number;
  draftOffers: number;
  pendingApprovalOffers: number;
  approvedOffers: number;
  confirmedOffers: number;
  distributedOffers: number;
  soldOffers: number;
  rejectedOffers: number;
  notNegotiatedOffers: number;
  totalSuppliers: number;
  activeSuppliers: number;
  totalBuyers: number;
  activeBuyers: number;
  totalCategories: number;
}

interface Offer {
  id: number;
  code: string;
  title: string;
  brand: string;
  model: string;
  version: string;
  year: string;
  status: string;
  price: number;
  supplier_price: number;
  negotiation_status: string;
  created_at: string;
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalOffers: 0,
    draftOffers: 0,
    pendingApprovalOffers: 0,
    approvedOffers: 0,
    confirmedOffers: 0,
    distributedOffers: 0,
    soldOffers: 0,
    rejectedOffers: 0,
    notNegotiatedOffers: 0,
    totalSuppliers: 0,
    activeSuppliers: 0,
    totalBuyers: 0,
    activeBuyers: 0,
    totalCategories: 0,
  });
  const [recentOffers, setRecentOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const [offersRes, suppliersRes, buyersRes, categoriesRes] = await Promise.all([
        client.entities.offers.query({ limit: 500 }),
        client.entities.suppliers.query({ limit: 500 }),
        client.entities.buyers.query({ limit: 500 }),
        client.entities.categories.query({ limit: 200 }),
      ]);

      const offers = offersRes?.data?.items || [];
      const suppliers = suppliersRes?.data?.items || [];
      const buyers = buyersRes?.data?.items || [];
      const categories = categoriesRes?.data?.items || [];

      setStats({
        totalOffers: offers.length,
        draftOffers: offers.filter((o: Offer) => o.status === 'draft').length,
        pendingApprovalOffers: offers.filter((o: Offer) => o.status === 'pending_approval').length,
        approvedOffers: offers.filter((o: Offer) => o.status === 'approved').length,
        confirmedOffers: offers.filter((o: Offer) => o.status === 'confirmed').length,
        distributedOffers: offers.filter((o: Offer) => o.status === 'distributed').length,
        soldOffers: offers.filter((o: Offer) => o.status === 'sold').length,
        rejectedOffers: offers.filter((o: Offer) => o.status === 'rejected').length,
        notNegotiatedOffers: offers.filter((o: Offer) => o.negotiation_status === 'not_negotiated').length,
        totalSuppliers: suppliers.length,
        activeSuppliers: suppliers.filter((s: any) => s.status === 'active').length,
        totalBuyers: buyers.length,
        activeBuyers: buyers.filter((b: any) => b.status === 'active').length,
        totalCategories: categories.length,
      });

      setRecentOffers(offers.slice(0, 8));
    } catch (error) {
      console.error('Error loading dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const map: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; className?: string }> = {
      draft: { label: 'Rascunho', variant: 'outline', className: 'border-purple-300 text-purple-700 bg-purple-50' },
      pending: { label: 'Pendente', variant: 'outline' },
      pending_approval: { label: 'Aguardando', variant: 'outline', className: 'border-amber-300 text-amber-700 bg-amber-50' },
      approved: { label: 'Aprovada', variant: 'secondary', className: 'bg-emerald-100 text-emerald-700' },
      confirmed: { label: 'Confirmada', variant: 'secondary', className: 'bg-sky-100 text-sky-700' },
      distributed: { label: 'Distribuída', variant: 'default' },
      negotiating: { label: 'Negociando', variant: 'default' },
      sold: { label: 'Vendido', variant: 'secondary', className: 'bg-green-100 text-green-700' },
      cancelled: { label: 'Cancelada', variant: 'destructive' },
      rejected: { label: 'Rejeitada', variant: 'destructive' },
    };
    const info = map[status] || { label: status, variant: 'outline' as const };
    return <Badge variant={info.variant} className={info.className}>{info.label}</Badge>;
  };

  const formatCurrency = (value: number) =>
    `R$ ${value.toLocaleString('pt-BR', { minimumFractionDigits: 0 })}`;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const pipelineTotal = stats.draftOffers + stats.pendingApprovalOffers + stats.approvedOffers + stats.confirmedOffers;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">Visão geral da operação AutoHub</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <BarChart3 className="h-4 w-4" />
          <span>{stats.totalCategories} categorias ativas</span>
        </div>
      </div>

      {/* Primary KPI Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-l-4 border-l-[#F16801]">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total de Ofertas</CardTitle>
            <Car className="h-4 w-4 text-[#F16801]" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tabular-nums">{stats.totalOffers}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {pipelineTotal} na pipeline
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Aguardando Aprovação</CardTitle>
            <Clock className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tabular-nums text-amber-600">{stats.pendingApprovalOffers}</div>
            <p className="text-xs text-muted-foreground mt-1">
              + {stats.draftOffers} rascunhos IA
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-sky-500">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Distribuídas</CardTitle>
            <Send className="h-4 w-4 text-sky-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tabular-nums text-sky-600">{stats.distributedOffers}</div>
            <p className="text-xs text-muted-foreground mt-1">
              + {stats.confirmedOffers} confirmadas
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-emerald-500">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Vendidas</CardTitle>
            <CheckCircle className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tabular-nums text-emerald-600">{stats.soldOffers}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {stats.totalOffers > 0 ? ((stats.soldOffers / stats.totalOffers) * 100).toFixed(1) : 0}% conversão
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Secondary KPI Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Fornecedores</CardTitle>
            <Truck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{stats.totalSuppliers}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {stats.activeSuppliers} ativos
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Compradores</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{stats.totalBuyers}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {stats.activeBuyers} ativos
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Não Negociadas</CardTitle>
            <XCircle className="h-4 w-4 text-red-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-red-500">{stats.notNegotiatedOffers}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Expiradas sem negociação
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Rejeitadas</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-orange-500">{stats.rejectedOffers}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Ofertas recusadas
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline Progress Bar */}
      {pipelineTotal > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Pipeline de Ofertas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-3 rounded-full overflow-hidden bg-muted">
              {stats.draftOffers > 0 && (
                <div
                  className="bg-purple-400 transition-all"
                  style={{ width: `${(stats.draftOffers / stats.totalOffers) * 100}%` }}
                  title={`${stats.draftOffers} rascunhos`}
                />
              )}
              {stats.pendingApprovalOffers > 0 && (
                <div
                  className="bg-amber-400 transition-all"
                  style={{ width: `${(stats.pendingApprovalOffers / stats.totalOffers) * 100}%` }}
                  title={`${stats.pendingApprovalOffers} aguardando`}
                />
              )}
              {stats.approvedOffers > 0 && (
                <div
                  className="bg-emerald-400 transition-all"
                  style={{ width: `${(stats.approvedOffers / stats.totalOffers) * 100}%` }}
                  title={`${stats.approvedOffers} aprovadas`}
                />
              )}
              {stats.confirmedOffers > 0 && (
                <div
                  className="bg-sky-400 transition-all"
                  style={{ width: `${(stats.confirmedOffers / stats.totalOffers) * 100}%` }}
                  title={`${stats.confirmedOffers} confirmadas`}
                />
              )}
              {stats.distributedOffers > 0 && (
                <div
                  className="bg-blue-500 transition-all"
                  style={{ width: `${(stats.distributedOffers / stats.totalOffers) * 100}%` }}
                  title={`${stats.distributedOffers} distribuídas`}
                />
              )}
              {stats.soldOffers > 0 && (
                <div
                  className="bg-green-600 transition-all"
                  style={{ width: `${(stats.soldOffers / stats.totalOffers) * 100}%` }}
                  title={`${stats.soldOffers} vendidas`}
                />
              )}
            </div>
            <div className="flex flex-wrap gap-4 mt-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-purple-400" /> Rascunho ({stats.draftOffers})</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-amber-400" /> Aguardando ({stats.pendingApprovalOffers})</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-emerald-400" /> Aprovadas ({stats.approvedOffers})</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-sky-400" /> Confirmadas ({stats.confirmedOffers})</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-blue-500" /> Distribuídas ({stats.distributedOffers})</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-green-600" /> Vendidas ({stats.soldOffers})</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Offers */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Ofertas Recentes</CardTitle>
        </CardHeader>
        <CardContent>
          {recentOffers.length === 0 ? (
            <div className="text-center py-12">
              <Car className="h-10 w-10 text-muted-foreground/40 mx-auto mb-3" />
              <p className="text-muted-foreground">Nenhuma oferta cadastrada ainda.</p>
              <p className="text-sm text-muted-foreground/70 mt-1">Crie uma nova oferta ou aguarde recebê-la via WhatsApp.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {recentOffers.map((offer) => (
                <div
                  key={offer.id}
                  className="flex items-center justify-between rounded-lg border p-3 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#F16801]/10">
                      <Car className="h-4 w-4 text-[#F16801]" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">
                        {offer.code && <span className="text-[#F16801] mr-2 font-mono">#{offer.code}</span>}
                        {offer.title}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {[offer.brand, offer.model, offer.version, offer.year].filter(Boolean).join(' ')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {offer.price ? (
                      <span className="text-sm font-semibold tabular-nums">
                        {formatCurrency(offer.price)}
                      </span>
                    ) : null}
                    {getStatusBadge(offer.status)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}