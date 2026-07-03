import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
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
import {
  Plus,
  Pencil,
  Eye,
  Search,
  CheckCircle,
  XCircle,
  Send,
  ArrowLeft,
  Image as ImageIcon,
  Users,
  ChevronRight,
  Car,
} from 'lucide-react';
import { client } from '@/lib/api';
import { toast } from 'sonner';

interface Supplier {
  id: number;
  name: string;
}

interface Category {
  id: number;
  name: string;
}

interface Offer {
  id: number;
  code: string;
  supplier_id: number;
  title: string;
  brand: string;
  model: string;
  year: string;
  color: string;
  mileage: string;
  price: number;
  fipe: string;
  fuel: string;
  plate: string;
  has_manual: boolean;
  has_spare_key: boolean;
  description: string;
  status: string;
  images: string;
  selected_images: string;
  processed_images: string;
  target_categories: string;
  vehicle_dossier_id?: number;
  created_at: string;
}

function generateCode(): string {
  return String(Math.floor(100000 + Math.random() * 900000));
}

export default function OffersPage() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [workflowOpen, setWorkflowOpen] = useState(false);
  const [selectedOffer, setSelectedOffer] = useState<Offer | null>(null);
  const [editing, setEditing] = useState<Offer | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<number[]>([]);
  const [selectedPhotoUrls, setSelectedPhotoUrls] = useState<string[]>([]);
  const [form, setForm] = useState({
    title: '',
    brand: '',
    model: '',
    version: '',
    year: '',
    color: '',
    mileage: '',
    price: '',
    supplier_price: '',
    fipe: '',
    fuel: '',
    transmission: '',
    plate: '',
    has_manual: false,
    has_spare_key: false,
    is_auction: false,
    suggested_category: '',
    description: '',
    supplier_id: '',
  });
  const [plateInput, setPlateInput] = useState('');
  const [plateLoading, setPlateLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [offersRes, suppliersRes, categoriesRes] = await Promise.all([
        client.entities.offers.query({ limit: 200, sort: '-created_at' }),
        client.entities.suppliers.query({ limit: 200 }),
        client.entities.categories.query({ limit: 200 }),
      ]);
      setOffers(offersRes?.data?.items || []);
      setSuppliers(suppliersRes?.data?.items || []);
      setCategories(categoriesRes?.data?.items || []);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSupplierName = (id: number) => {
    return suppliers.find((s) => s.id === id)?.name || 'Desconhecido';
  };

  const handlePlateLookup = async () => {
    if (!plateInput.trim()) {
      toast.error('Digite a placa do veículo');
      return;
    }
    setPlateLoading(true);
    try {
      const token = localStorage.getItem('auth_token') || '';
      const res = await fetch('/api/v1/vehicle-dossiers/plate-lookup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ plate: plateInput.trim(), offer_id: editing?.id }),
      });
      const data = await res.json();
      if (data.success) {
        const brand = data.brand || '';
        const model = data.model || '';
        const year = data.ano_modelo || data.year || '';
        const color = data.color || '';
        const fuel = data.fuel || '';
        const fipe = data.fipe_price || '';
        const title = [brand, model, year].filter(Boolean).join(' ');

        setForm((prev) => ({
          ...prev,
          title: title || prev.title,
          brand: brand || prev.brand,
          model: model || prev.model,
          year: year || prev.year,
          color: color || prev.color,
          fuel: fuel || prev.fuel,
          fipe: fipe || prev.fipe,
          plate: plateInput.trim() || prev.plate,
        }));

        // Build success message with extra info from ConsultarPlaca
        const source = data.source === 'consultarplaca' ? ' (ConsultarPlaca)' : ' (BrasilAPI)';
        let msg = `Veículo encontrado: ${brand} ${model} ${year}${source}`;
        if (data.fipe_price) {
          msg += ` | FIPE: ${data.fipe_price}`;
        }
        if (data.fipe_versions && data.fipe_versions.length > 1) {
          msg += ` | ${data.fipe_versions.length} versões FIPE disponíveis`;
        }
        toast.success(msg, { duration: 5000 });
      } else {
        toast.error(data.error || 'Placa não encontrada');
      }
    } catch (error) {
      toast.error('Erro ao consultar placa');
    } finally {
      setPlateLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      const data = {
        ...form,
        supplier_id: Number(form.supplier_id),
        price: form.price ? Number(form.price) : 0,
        supplier_price: form.supplier_price ? Number(form.supplier_price) : null,
        code: editing?.code || generateCode(),
        status: editing?.status || 'pending',
      };

      if (editing) {
        await client.entities.offers.update({ id: String(editing.id), data });
        toast.success('Oferta atualizada com sucesso');
      } else {
        await client.entities.offers.create({ data });
        toast.success('Oferta criada com sucesso');
      }
      setDialogOpen(false);
      setEditing(null);
      resetForm();
      loadData();
    } catch (error) {
      toast.error('Erro ao salvar oferta');
    }
  };

  const handleEdit = (offer: Offer) => {
    setEditing(offer);
    setForm({
      title: offer.title || '',
      brand: offer.brand || '',
      model: offer.model || '',
      version: (offer as any).version || '',
      year: offer.year || '',
      color: offer.color || '',
      mileage: offer.mileage || '',
      price: offer.price ? String(offer.price) : '',
      supplier_price: (offer as any).supplier_price ? String((offer as any).supplier_price) : '',
      fipe: offer.fipe || '',
      fuel: offer.fuel || '',
      transmission: (offer as any).transmission || '',
      plate: offer.plate || '',
      has_manual: offer.has_manual || false,
      has_spare_key: offer.has_spare_key || false,
      is_auction: (offer as any).is_auction || false,
      suggested_category: (offer as any).suggested_category || '',
      description: offer.description || '',
      supplier_id: offer.supplier_id ? String(offer.supplier_id) : '',
    });
    setDialogOpen(true);
  };

  const handleView = (offer: Offer) => {
    setSelectedOffer(offer);
    setDetailOpen(true);
  };

  const handleOpenWorkflow = (offer: Offer) => {
    setSelectedOffer(offer);
    // Parse existing selected photos
    try {
      const parsed = offer.selected_images
        ? (typeof offer.selected_images === 'string'
            ? JSON.parse(offer.selected_images)
            : offer.selected_images)
        : [];
      setSelectedPhotoUrls(Array.isArray(parsed) ? parsed : []);
    } catch {
      setSelectedPhotoUrls([]);
    }
    // Parse existing target categories
    try {
      const parsed = offer.target_categories
        ? (typeof offer.target_categories === 'string'
            ? JSON.parse(offer.target_categories)
            : offer.target_categories)
        : [];
      setSelectedCategoryIds(Array.isArray(parsed) ? parsed : []);
    } catch {
      setSelectedCategoryIds([]);
    }
    setWorkflowOpen(true);
  };

  const handleSendForApproval = async (offer: Offer) => {
    try {
      const token = localStorage.getItem('auth_token') || '';
      const res = await fetch('/api/v1/whatsapp/offer/send-for-approval', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ offer_id: offer.id }),
      });
      const data = await res.json();
      if (data.error) {
        toast.error(data.error);
      } else {
        toast.success('Oferta enviada para aprovação via WhatsApp!');
        loadData();
      }
    } catch (error) {
      toast.error('Erro ao enviar para aprovação');
    }
  };

  const handleApprove = async (offer: Offer) => {
    try {
      await client.entities.offers.update({
        id: String(offer.id),
        data: { status: 'approved' },
      });
      toast.success('Oferta aprovada!');
      loadData();
      if (selectedOffer) {
        setSelectedOffer({ ...offer, status: 'approved' });
      }
    } catch (error) {
      toast.error('Erro ao aprovar oferta');
    }
  };

  const handleReject = async (offer: Offer) => {
    try {
      await client.entities.offers.update({
        id: String(offer.id),
        data: { status: 'rejected' },
      });
      toast.success('Oferta rejeitada');
      loadData();
      if (selectedOffer) {
        setSelectedOffer({ ...offer, status: 'rejected' });
      }
    } catch (error) {
      toast.error('Erro ao rejeitar oferta');
    }
  };

  const handleConfirm = async (offer: Offer) => {
    try {
      await client.entities.offers.update({
        id: String(offer.id),
        data: { status: 'confirmed' },
      });
      toast.success('Oferta confirmada! Pronta para distribuição.');
      loadData();
      if (selectedOffer) {
        setSelectedOffer({ ...offer, status: 'confirmed' });
      }
    } catch (error) {
      toast.error('Erro ao confirmar oferta');
    }
  };

  const handleBackStatus = async (offer: Offer) => {
    const backMap: Record<string, string> = {
      pending_approval: 'draft',
      approved: 'pending_approval',
      confirmed: 'approved',
    };
    const newStatus = backMap[offer.status];
    if (!newStatus) return;
    try {
      await client.entities.offers.update({
        id: String(offer.id),
        data: { status: newStatus },
      });
      toast.success(`Oferta retornou para: ${getStatusLabel(newStatus)}`);
      loadData();
      if (selectedOffer) {
        setSelectedOffer({ ...offer, status: newStatus });
      }
    } catch (error) {
      toast.error('Erro ao alterar status');
    }
  };

  const handleSaveSelectedPhotos = async () => {
    if (!selectedOffer) return;
    try {
      await client.entities.offers.update({
        id: String(selectedOffer.id),
        data: { selected_images: JSON.stringify(selectedPhotoUrls) },
      });
      toast.success('Fotos selecionadas salvas!');
      loadData();
    } catch (error) {
      toast.error('Erro ao salvar fotos');
    }
  };

  const handleDistribute = async () => {
    if (!selectedOffer) return;
    if (selectedCategoryIds.length === 0) {
      toast.error('Selecione pelo menos uma categoria');
      return;
    }
    try {
      const token = localStorage.getItem('auth_token') || '';
      const res = await fetch('/api/v1/whatsapp/offer/distribute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          offer_id: selectedOffer.id,
          category_ids: selectedCategoryIds,
        }),
      });
      const data = await res.json();
      if (data.error) {
        toast.error(data.error);
      } else {
        toast.success(
          `Oferta distribuída para ${data.sent_count}/${data.total_buyers} compradores!`
        );
        loadData();
        setWorkflowOpen(false);
      }
    } catch (error) {
      toast.error('Erro ao distribuir oferta');
    }
  };

  const resetForm = () => {
    setForm({
      title: '',
      brand: '',
      model: '',
      version: '',
      year: '',
      color: '',
      mileage: '',
      price: '',
      supplier_price: '',
      fipe: '',
      fuel: '',
      transmission: '',
      plate: '',
      has_manual: false,
      has_spare_key: false,
      is_auction: false,
      suggested_category: '',
      description: '',
      supplier_id: '',
    });
    setPlateInput('');
  };

  const handleNew = () => {
    setEditing(null);
    resetForm();
    setDialogOpen(true);
  };

  const getStatusLabel = (status: string) => {
    const map: Record<string, string> = {
      draft: 'Rascunho IA',
      pending: 'Pendente',
      pending_approval: 'Aguardando Aprovação',
      approved: 'Aprovada',
      confirmed: 'Confirmada',
      distributed: 'Distribuída',
      negotiating: 'Negociando',
      sold: 'Vendido',
      cancelled: 'Cancelada',
      rejected: 'Rejeitada',
    };
    return map[status] || status;
  };

  const getStatusBadge = (status: string) => {
    const map: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline"; className?: string }> = {
      draft: { label: "Rascunho IA", variant: "outline", className: "border-purple-400 text-purple-600 bg-purple-50" },
      pending: { label: "Pendente", variant: "outline" },
      pending_approval: { label: "Aguardando Aprovação", variant: "outline", className: "border-amber-400 text-amber-600 bg-amber-50" },
      approved: { label: "Aprovada", variant: "secondary", className: "bg-green-100 text-green-700" },
      confirmed: { label: "Confirmada", variant: "secondary", className: "bg-blue-100 text-blue-700" },
      distributed: { label: "Distribuída", variant: "default" },
      negotiating: { label: "Negociando", variant: "default" },
      sold: { label: "Vendido", variant: "secondary" },
      cancelled: { label: "Cancelada", variant: "destructive" },
      rejected: { label: "Rejeitada", variant: "destructive" },
    };
    const info = map[status] || { label: status, variant: "outline" as const };
    return <Badge variant={info.variant} className={info.className}>{info.label}</Badge>;
  };

  const getOfferImages = (offer: Offer): string[] => {
    try {
      const processed = offer.processed_images
        ? (typeof offer.processed_images === 'string'
            ? JSON.parse(offer.processed_images)
            : offer.processed_images)
        : [];
      if (Array.isArray(processed) && processed.length > 0) {
        return processed.map((p: any) =>
          typeof p === 'string' ? p : p.processed_url || p.url || ''
        ).filter(Boolean);
      }
    } catch { /* fall through */ }
    try {
      const raw = offer.images
        ? (typeof offer.images === 'string'
            ? JSON.parse(offer.images)
            : offer.images)
        : [];
      if (Array.isArray(raw)) {
        return raw.filter(Boolean);
      }
    } catch { /* fall through */ }
    return [];
  };

  const filtered = offers.filter((o) => {
    const matchSearch =
      (o.title && o.title.toLowerCase().includes(search.toLowerCase())) ||
      (o.code && o.code.includes(search)) ||
      (o.brand && o.brand.toLowerCase().includes(search.toLowerCase())) ||
      (o.model && o.model.toLowerCase().includes(search.toLowerCase()));
    const matchStatus = statusFilter === 'all' || o.status === statusFilter;
    return matchSearch && matchStatus;
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
      <div className="flex items-center justify-between">
        <div>
          <h1>Ofertas</h1>
          <p className="text-muted-foreground mt-1">Gerencie as ofertas de veículos</p>
        </div>
        <Button onClick={handleNew}>
          <Plus className="h-4 w-4 mr-2" />
          Nova Oferta
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por código, título, marca..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <select
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">Todos os status</option>
              <option value="draft">Rascunho IA</option>
              <option value="pending_approval">Aguardando Aprovação</option>
              <option value="pending">Pendentes</option>
              <option value="approved">Aprovadas</option>
              <option value="confirmed">Confirmadas</option>
              <option value="distributed">Distribuídas</option>
              <option value="negotiating">Negociando</option>
              <option value="sold">Vendidas</option>
              <option value="rejected">Rejeitadas</option>
              <option value="cancelled">Canceladas</option>
            </select>
            <CardTitle className="text-sm text-muted-foreground">
              {filtered.length} oferta(s)
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
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                    Nenhuma oferta encontrada
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((offer) => (
                  <TableRow key={offer.id}>
                    <TableCell className="font-mono text-primary font-medium">
                      #{offer.code}
                    </TableCell>
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
                      {offer.price
                        ? `R$ ${Number(offer.price).toLocaleString('pt-BR')}`
                        : '-'}
                    </TableCell>
                    <TableCell>{getStatusBadge(offer.status)}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => handleView(offer)} title="Ver detalhes">
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => handleEdit(offer)} title="Editar">
                        <Pencil className="h-4 w-4" />
                      </Button>
                      {(offer.status === 'draft' || offer.status === 'pending_approval' || offer.status === 'approved' || offer.status === 'confirmed') && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleOpenWorkflow(offer)}
                          title="Workflow"
                        >
                          <ChevronRight className="h-4 w-4 text-blue-600" />
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

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editing ? 'Editar Oferta' : 'Nova Oferta'}</DialogTitle>
          </DialogHeader>
          <div className="bg-muted/50 border rounded-lg p-4 space-y-2">
            <Label className="text-sm font-semibold flex items-center gap-2">
              <Car className="h-4 w-4" />
              Consultar por Placa
            </Label>
            <div className="flex gap-2">
              <Input
                value={plateInput}
                onChange={(e) => setPlateInput(e.target.value.toUpperCase())}
                placeholder="ABC1D23"
                className="max-w-[180px] uppercase"
                maxLength={8}
                onKeyDown={(e) => { if (e.key === 'Enter') handlePlateLookup(); }}
              />
              <Button
                onClick={handlePlateLookup}
                disabled={plateLoading || !plateInput.trim()}
                size="sm"
                className="bg-[#F16801] hover:bg-[#d55d01]"
              >
                {plateLoading ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-1" />
                    Consultar
                  </>
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Consulta via ConsultarPlaca (dados completos + FIPE) ou BrasilAPI (fallback gratuito).
              Preenche automaticamente marca, modelo, ano, cor, combustível e preço FIPE.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Label>Título</Label>
              <Input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Ex: Honda Civic 2022 Touring"
              />
            </div>
            <div>
              <Label>Marca</Label>
              <Input
                value={form.brand}
                onChange={(e) => setForm({ ...form, brand: e.target.value })}
                placeholder="Honda"
              />
            </div>
            <div>
              <Label>Modelo</Label>
              <Input
                value={form.model}
                onChange={(e) => setForm({ ...form, model: e.target.value })}
                placeholder="Civic"
              />
            </div>
            <div>
              <Label>Versão</Label>
              <Input
                value={form.version}
                onChange={(e) => setForm({ ...form, version: e.target.value })}
                placeholder="Touring 1.5 Turbo"
              />
            </div>
            <div>
              <Label>Ano</Label>
              <Input
                value={form.year}
                onChange={(e) => setForm({ ...form, year: e.target.value })}
                placeholder="2022"
              />
            </div>
            <div>
              <Label>Cor</Label>
              <Input
                value={form.color}
                onChange={(e) => setForm({ ...form, color: e.target.value })}
                placeholder="Preto"
              />
            </div>
            <div>
              <Label>Quilometragem</Label>
              <Input
                value={form.mileage}
                onChange={(e) => setForm({ ...form, mileage: e.target.value })}
                placeholder="25.000 km"
              />
            </div>
            <div>
              <Label>Preço de Venda (R$)</Label>
              <Input
                type="number"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
                placeholder="150000"
              />
            </div>
            <div>
              <Label>Preço Fornecedor (R$)</Label>
              <Input
                type="number"
                value={form.supplier_price}
                onChange={(e) => setForm({ ...form, supplier_price: e.target.value })}
                placeholder="135000"
              />
            </div>
            <div>
              <Label>FIPE</Label>
              <Input
                value={form.fipe}
                onChange={(e) => setForm({ ...form, fipe: e.target.value })}
                placeholder="R$ 120.000"
              />
            </div>
            <div>
              <Label>Combustível</Label>
              <Input
                value={form.fuel}
                onChange={(e) => setForm({ ...form, fuel: e.target.value })}
                placeholder="Flex"
              />
            </div>
            <div>
              <Label>Câmbio</Label>
              <Input
                value={form.transmission}
                onChange={(e) => setForm({ ...form, transmission: e.target.value })}
                placeholder="Automático"
              />
            </div>
            <div>
              <Label>Placa</Label>
              <Input
                value={form.plate}
                onChange={(e) => setForm({ ...form, plate: e.target.value.toUpperCase() })}
                placeholder="ABC1D23"
                className="uppercase"
                maxLength={8}
              />
            </div>
            <div>
              <Label>Categoria Sugerida</Label>
              <Input
                value={form.suggested_category}
                onChange={(e) => setForm({ ...form, suggested_category: e.target.value })}
                placeholder="Sedan, SUV, Hatch..."
              />
            </div>
            <div className="flex items-center gap-6 pt-6">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="has_manual"
                  checked={form.has_manual}
                  onCheckedChange={(checked) => setForm({ ...form, has_manual: !!checked })}
                />
                <Label htmlFor="has_manual" className="cursor-pointer">Manual</Label>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="has_spare_key"
                  checked={form.has_spare_key}
                  onCheckedChange={(checked) => setForm({ ...form, has_spare_key: !!checked })}
                />
                <Label htmlFor="has_spare_key" className="cursor-pointer">Chave Reserva</Label>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="is_auction"
                  checked={form.is_auction}
                  onCheckedChange={(checked) => setForm({ ...form, is_auction: !!checked })}
                />
                <Label htmlFor="is_auction" className="cursor-pointer">Leilão</Label>
              </div>
            </div>
            <div className="col-span-2">
              <Label>Fornecedor</Label>
              <select
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={form.supplier_id}
                onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}
              >
                <option value="">Selecione um fornecedor</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-span-2">
              <Label>Descrição</Label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Descrição completa do veículo..."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={!form.title || !form.supplier_id}>
              {editing ? 'Salvar' : 'Criar Oferta'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              Detalhes da Oferta {selectedOffer?.code && `#${selectedOffer.code}`}
            </DialogTitle>
          </DialogHeader>
          {selectedOffer && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Título</p>
                  <p className="font-medium">{selectedOffer.title}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  {getStatusBadge(selectedOffer.status)}
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Marca / Modelo</p>
                  <p className="font-medium">
                    {selectedOffer.brand} {selectedOffer.model}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Ano</p>
                  <p className="font-medium">{selectedOffer.year || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Cor</p>
                  <p className="font-medium">{selectedOffer.color || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Quilometragem</p>
                  <p className="font-medium">{selectedOffer.mileage || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Preço</p>
                  <p className="font-medium">
                    {selectedOffer.price
                      ? `R$ ${Number(selectedOffer.price).toLocaleString('pt-BR')}`
                      : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">FIPE</p>
                  <p className="font-medium">{selectedOffer.fipe || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Combustível</p>
                  <p className="font-medium">{selectedOffer.fuel || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Placa</p>
                  <p className="font-medium font-mono">{selectedOffer.plate || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Manual / Chave Reserva</p>
                  <p className="font-medium">
                    {selectedOffer.has_manual ? '✅ Manual' : '❌ Manual'}{' / '}
                    {selectedOffer.has_spare_key ? '✅ Chave' : '❌ Chave'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Fornecedor</p>
                  <p className="font-medium">{getSupplierName(selectedOffer.supplier_id)}</p>
                </div>
              </div>
              {selectedOffer.description && (
                <div>
                  <p className="text-sm text-muted-foreground">Descrição</p>
                  <p className="mt-1 text-sm whitespace-pre-wrap bg-muted p-3 rounded-md">{selectedOffer.description}</p>
                </div>
              )}
              {/* Show images */}
              {getOfferImages(selectedOffer).length > 0 && (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Fotos</p>
                  <div className="grid grid-cols-3 gap-2">
                    {getOfferImages(selectedOffer).map((url, idx) => (
                      <img
                        key={idx}
                        src={url}
                        alt={`Foto ${idx + 1}`}
                        className="w-full h-24 object-cover rounded-md border"
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Workflow Dialog */}
      <Dialog open={workflowOpen} onOpenChange={setWorkflowOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              Workflow da Oferta {selectedOffer?.code && `#${selectedOffer.code}`}
            </DialogTitle>
          </DialogHeader>
          {selectedOffer && (
            <div className="space-y-6">
              {/* Status indicator */}
              <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                <span className="text-sm font-medium">Status atual:</span>
                {getStatusBadge(selectedOffer.status)}
              </div>

              {/* Offer summary */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-muted-foreground">Veículo:</span> {selectedOffer.title}</div>
                <div><span className="text-muted-foreground">Preço:</span> {selectedOffer.price ? `R$ ${Number(selectedOffer.price).toLocaleString('pt-BR')}` : 'Não definido'}</div>
                <div><span className="text-muted-foreground">FIPE:</span> {selectedOffer.fipe || '-'}</div>
                <div><span className="text-muted-foreground">Combustível:</span> {selectedOffer.fuel || '-'}</div>
              </div>

              {/* Step 1: Review & Edit (draft / pending_approval) */}
              {(selectedOffer.status === 'draft' || selectedOffer.status === 'pending_approval') && (
                <div className="space-y-3">
                  <h3 className="font-semibold flex items-center gap-2">
                    <ImageIcon className="h-4 w-4" /> Revisar e Editar
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Revise os dados da oferta, edite se necessário e selecione as fotos para o anúncio.
                  </p>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => handleEdit(selectedOffer)}>
                      <Pencil className="h-4 w-4 mr-1" /> Editar Oferta
                    </Button>
                  </div>
                </div>
              )}

              {/* Step 2: Select Photos */}
              {(selectedOffer.status === 'draft' || selectedOffer.status === 'pending_approval' || selectedOffer.status === 'approved') && (
                <div className="space-y-3">
                  <h3 className="font-semibold flex items-center gap-2">
                    <ImageIcon className="h-4 w-4" /> Selecionar Fotos
                  </h3>
                  {getOfferImages(selectedOffer).length > 0 ? (
                    <div className="grid grid-cols-4 gap-2">
                      {getOfferImages(selectedOffer).map((url, idx) => {
                        const isSelected = selectedPhotoUrls.includes(url);
                        return (
                          <div
                            key={idx}
                            className={`relative cursor-pointer rounded-md border-2 overflow-hidden ${
                              isSelected ? 'border-primary ring-2 ring-primary/30' : 'border-transparent'
                            }`}
                            onClick={() => {
                              setSelectedPhotoUrls((prev) =>
                                isSelected ? prev.filter((u) => u !== url) : [...prev, url]
                              );
                            }}
                          >
                            <img src={url} alt={`Foto ${idx + 1}`} className="w-full h-20 object-cover" />
                            {isSelected && (
                              <div className="absolute top-1 right-1 bg-primary text-primary-foreground rounded-full w-5 h-5 flex items-center justify-center text-xs">
                                ✓
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Nenhuma foto disponível</p>
                  )}
                  <Button size="sm" onClick={handleSaveSelectedPhotos} disabled={selectedPhotoUrls.length === 0}>
                    Salvar Fotos Selecionadas ({selectedPhotoUrls.length})
                  </Button>
                </div>
              )}

              {/* Step 3: Set Value */}
              {(selectedOffer.status === 'draft' || selectedOffer.status === 'pending_approval') && (
                <div className="space-y-3">
                  <h3 className="font-semibold">Definir Valor</h3>
                  <div className="flex items-center gap-3">
                    <span className="text-sm">R$</span>
                    <Input
                      type="number"
                      value={selectedOffer.price || ''}
                      onChange={(e) => {
                        const val = e.target.value;
                        setSelectedOffer({ ...selectedOffer, price: val ? Number(val) : 0 });
                      }}
                      placeholder="Valor de venda"
                      className="max-w-[200px]"
                    />
                    <Button
                      size="sm"
                      onClick={async () => {
                        try {
                          await client.entities.offers.update({
                            id: String(selectedOffer.id),
                            data: { price: selectedOffer.price },
                          });
                          toast.success('Preço atualizado!');
                          loadData();
                        } catch {
                          toast.error('Erro ao atualizar preço');
                        }
                      }}
                    >
                      Salvar
                    </Button>
                  </div>
                </div>
              )}

              {/* Step 4: Send for Approval */}
              {selectedOffer.status === 'draft' && (
                <div className="space-y-3 border-t pt-4">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Send className="h-4 w-4" /> Enviar para Aprovação
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Envia a oferta para o admin aprovar via WhatsApp.
                  </p>
                  <Button onClick={() => handleSendForApproval(selectedOffer)}>
                    <Send className="h-4 w-4 mr-2" /> Enviar para Aprovação
                  </Button>
                </div>
              )}

              {/* Step 5: Approve / Reject */}
              {selectedOffer.status === 'pending_approval' && (
                <div className="space-y-3 border-t pt-4">
                  <h3 className="font-semibold">Aprovar ou Rejeitar</h3>
                  <div className="flex gap-2">
                    <Button
                      className="bg-green-600 hover:bg-green-700"
                      onClick={() => handleApprove(selectedOffer)}
                    >
                      <CheckCircle className="h-4 w-4 mr-2" /> Aprovar
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={() => handleReject(selectedOffer)}
                    >
                      <XCircle className="h-4 w-4 mr-2" /> Rejeitar
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => handleBackStatus(selectedOffer)}
                    >
                      <ArrowLeft className="h-4 w-4 mr-2" /> Voltar
                    </Button>
                  </div>
                </div>
              )}

              {/* Step 6: Confirm */}
              {selectedOffer.status === 'approved' && (
                <div className="space-y-3 border-t pt-4">
                  <h3 className="font-semibold">Confirmar para Distribuição</h3>
                  <div className="flex gap-2">
                    <Button onClick={() => handleConfirm(selectedOffer)}>
                      <CheckCircle className="h-4 w-4 mr-2" /> Confirmar
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => handleBackStatus(selectedOffer)}
                    >
                      <ArrowLeft className="h-4 w-4 mr-2" /> Voltar
                    </Button>
                  </div>
                </div>
              )}

              {/* Step 7: Choose Groups & Distribute */}
              {selectedOffer.status === 'confirmed' && (
                <div className="space-y-3 border-t pt-4">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Users className="h-4 w-4" /> Distribuir para Compradores
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Selecione as categorias de compradores para enviar a oferta via WhatsApp.
                  </p>
                  {categories.length > 0 ? (
                    <div className="space-y-2">
                      {categories.map((cat) => (
                        <div key={cat.id} className="flex items-center gap-2">
                          <Checkbox
                            id={`cat-${cat.id}`}
                            checked={selectedCategoryIds.includes(cat.id)}
                            onCheckedChange={(checked) => {
                              setSelectedCategoryIds((prev) =>
                                checked
                                  ? [...prev, cat.id]
                                  : prev.filter((id) => id !== cat.id)
                              );
                            }}
                          />
                          <Label htmlFor={`cat-${cat.id}`} className="cursor-pointer">
                            {cat.name}
                          </Label>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Nenhuma categoria cadastrada</p>
                  )}
                  <div className="flex gap-2">
                    <Button
                      onClick={handleDistribute}
                      disabled={selectedCategoryIds.length === 0}
                    >
                      <Send className="h-4 w-4 mr-2" /> Distribuir ({selectedCategoryIds.length} categoria{selectedCategoryIds.length !== 1 ? 's' : ''})
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => handleBackStatus(selectedOffer)}
                    >
                      <ArrowLeft className="h-4 w-4 mr-2" /> Voltar
                    </Button>
                  </div>
                </div>
              )}

              {/* Distributed status */}
              {selectedOffer.status === 'distributed' && (
                <div className="space-y-3 border-t pt-4">
                  <div className="flex items-center gap-2 p-3 bg-green-50 text-green-700 rounded-lg">
                    <CheckCircle className="h-5 w-5" />
                    <span className="font-medium">Oferta distribuída com sucesso!</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Compradores podem responder NEGOCIAR para receber o número de negociação.
                  </p>
                </div>
              )}

              {/* Rejected status */}
              {selectedOffer.status === 'rejected' && (
                <div className="space-y-3 border-t pt-4">
                  <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg">
                    <XCircle className="h-5 w-5" />
                    <span className="font-medium">Oferta rejeitada</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
