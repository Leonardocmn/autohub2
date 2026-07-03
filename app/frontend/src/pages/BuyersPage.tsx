import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
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
import { Plus, Pencil, Trash2, Search } from 'lucide-react';
import { client } from '@/lib/api';
import { toast } from 'sonner';

interface Buyer {
  id: number;
  name: string;
  phone: string;
  email: string;
  company: string;
  city: string;
  observations: string;
  status: string;
  categories?: number[];
}

interface Category {
  id: number;
  name: string;
}

interface BuyerCategory {
  id: number;
  buyer_id: number;
  category_id: number;
}

const emptyForm = { name: '', phone: '', email: '', company: '', city: '', observations: '', status: 'active' };

export default function BuyersPage() {
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [buyerCategories, setBuyerCategories] = useState<BuyerCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Buyer | null>(null);
  const [search, setSearch] = useState('');
  const [form, setForm] = useState(emptyForm);
  const [selectedCategories, setSelectedCategories] = useState<number[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [buyersRes, catsRes, bcRes] = await Promise.all([
        client.entities.buyers.query({ limit: 200 }),
        client.entities.categories.query({ limit: 200 }),
        client.entities.buyer_categories.query({ limit: 1000 }),
      ]);
      setBuyers(buyersRes?.data?.items || []);
      setCategories(catsRes?.data?.items || []);
      setBuyerCategories(bcRes?.data?.items || []);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getBuyerCategoryNames = (buyerId: number) => {
    const catIds = buyerCategories
      .filter((bc) => bc.buyer_id === buyerId)
      .map((bc) => bc.category_id);
    return categories
      .filter((c) => catIds.includes(c.id))
      .map((c) => c.name);
  };

  const handleSave = async () => {
    try {
      if (editing) {
        await client.entities.buyers.update({ id: String(editing.id), data: form });
        const existing = buyerCategories.filter((bc) => bc.buyer_id === editing.id);
        for (const bc of existing) {
          if (!selectedCategories.includes(bc.category_id)) {
            await client.entities.buyer_categories.delete({ id: String(bc.id) });
          }
        }
        const existingCatIds = existing.map((bc) => bc.category_id);
        for (const catId of selectedCategories) {
          if (!existingCatIds.includes(catId)) {
            await client.entities.buyer_categories.create({
              data: { buyer_id: editing.id, category_id: catId },
            });
          }
        }
        toast.success('Comprador atualizado com sucesso');
      } else {
        const res = await client.entities.buyers.create({ data: form });
        const newBuyer = res?.data;
        if (newBuyer) {
          // Ensure "Geral" category exists
          let geralCat = categories.find((c) => c.name.toLowerCase() === 'geral');
          if (!geralCat) {
            const catRes = await client.entities.categories.create({
              data: { name: 'Geral' },
            });
            geralCat = catRes?.data;
          }
          // Build final category list: selected + Geral (deduplicated)
          const finalCatIds = new Set(selectedCategories);
          if (geralCat) {
            finalCatIds.add(geralCat.id);
          }
          for (const catId of finalCatIds) {
            await client.entities.buyer_categories.create({
              data: { buyer_id: newBuyer.id, category_id: catId },
            });
          }
        }
        toast.success('Comprador cadastrado com sucesso');
      }
      setDialogOpen(false);
      setEditing(null);
      setForm(emptyForm);
      setSelectedCategories([]);
      loadData();
    } catch (error) {
      toast.error('Erro ao salvar comprador');
    }
  };

  const handleEdit = (buyer: Buyer) => {
    setEditing(buyer);
    setForm({
      name: buyer.name,
      phone: buyer.phone,
      email: buyer.email || '',
      company: buyer.company || '',
      city: buyer.city || '',
      observations: buyer.observations || '',
      status: buyer.status,
    });
    const catIds = buyerCategories
      .filter((bc) => bc.buyer_id === buyer.id)
      .map((bc) => bc.category_id);
    setSelectedCategories(catIds);
    setDialogOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Tem certeza que deseja excluir este comprador?')) return;
    try {
      const bcs = buyerCategories.filter((bc) => bc.buyer_id === id);
      for (const bc of bcs) {
        await client.entities.buyer_categories.delete({ id: String(bc.id) });
      }
      await client.entities.buyers.delete({ id: String(id) });
      toast.success('Comprador excluído');
      loadData();
    } catch (error) {
      toast.error('Erro ao excluir comprador');
    }
  };

  const handleNew = () => {
    setEditing(null);
    setForm(emptyForm);
    setSelectedCategories([]);
    setDialogOpen(true);
  };

  const toggleCategory = (catId: number) => {
    setSelectedCategories((prev) =>
      prev.includes(catId) ? prev.filter((id) => id !== catId) : [...prev, catId]
    );
  };

  const filtered = buyers.filter(
    (b) =>
      b.name.toLowerCase().includes(search.toLowerCase()) ||
      b.phone.includes(search) ||
      (b.company && b.company.toLowerCase().includes(search.toLowerCase())) ||
      (b.city && b.city.toLowerCase().includes(search.toLowerCase()))
  );

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
          <h1>Compradores</h1>
          <p className="text-muted-foreground mt-1">Gerencie seus compradores e suas categorias</p>
        </div>
        <Button onClick={handleNew}>
          <Plus className="h-4 w-4 mr-2" />
          Novo Comprador
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar comprador..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <CardTitle className="text-sm text-muted-foreground">
              {filtered.length} comprador(es)
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Telefone</TableHead>
                <TableHead>Empresa</TableHead>
                <TableHead>Cidade</TableHead>
                <TableHead>Categorias</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                    Nenhum comprador encontrado
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((buyer) => (
                  <TableRow key={buyer.id}>
                    <TableCell className="font-medium">{buyer.name}</TableCell>
                    <TableCell>{buyer.phone}</TableCell>
                    <TableCell>{buyer.company || '-'}</TableCell>
                    <TableCell>{buyer.city || '-'}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {getBuyerCategoryNames(buyer.id).map((name) => (
                          <Badge key={name} variant="outline" className="text-xs">
                            {name}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={buyer.status === 'active' ? 'default' : 'secondary'}>
                        {buyer.status === 'active' ? 'Ativo' : 'Inativo'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => handleEdit(buyer)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => handleDelete(buyer.id)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? 'Editar Comprador' : 'Novo Comprador'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Nome</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Nome do comprador"
              />
            </div>
            <div>
              <Label>Telefone WhatsApp</Label>
              <Input
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="+55 11 99999-9999"
              />
            </div>
            <div>
              <Label>E-mail</Label>
              <Input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="email@exemplo.com"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Empresa</Label>
                <Input
                  value={form.company}
                  onChange={(e) => setForm({ ...form, company: e.target.value })}
                  placeholder="Nome da empresa"
                />
              </div>
              <div>
                <Label>Cidade</Label>
                <Input
                  value={form.city}
                  onChange={(e) => setForm({ ...form, city: e.target.value })}
                  placeholder="São Paulo"
                />
              </div>
            </div>
            <div>
              <Label>Observações</Label>
              <Textarea
                value={form.observations}
                onChange={(e) => setForm({ ...form, observations: e.target.value })}
                placeholder="Observações sobre o comprador..."
                rows={3}
              />
            </div>
            <div>
              <Label>Status</Label>
              <select
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                <option value="active">Ativo</option>
                <option value="inactive">Inativo</option>
              </select>
            </div>
            {categories.length > 0 && (
              <div>
                <Label>Categorias</Label>
                <div className="mt-2 space-y-2 max-h-40 overflow-y-auto border rounded-md p-3">
                  {categories.map((cat) => (
                    <div key={cat.id} className="flex items-center gap-2">
                      <Checkbox
                        checked={selectedCategories.includes(cat.id)}
                        onCheckedChange={() => toggleCategory(cat.id)}
                      />
                      <span className="text-sm">{cat.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={!form.name || !form.phone}>
              {editing ? 'Salvar' : 'Cadastrar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}