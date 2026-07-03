import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { UserCheck, Plus, Pencil, Trash2, Phone, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { client } from '@/lib/api';

interface AdminPhone {
  id: number;
  phone: string;
  name: string | null;
  active: boolean | null;
  created_at: string | null;
  updated_at: string | null;
}

export default function AdminPhonesPage() {
  const [phones, setPhones] = useState<AdminPhone[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState({ phone: '', name: '', active: true });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);

  const loadPhones = useCallback(async () => {
    setLoading(true);
    try {
      const res = await client.entities.whatsapp_admin_phones.query({ limit: 200, sort: '-id' });
      setPhones(res.data?.items || []);
    } catch (error: any) {
      console.error('Error loading admin phones:', error);
      toast.error('Erro ao carregar números de administrador');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPhones();
  }, [loadPhones]);

  const openCreate = () => {
    setEditingId(null);
    setForm({ phone: '', name: '', active: true });
    setDialogOpen(true);
  };

  const openEdit = (item: AdminPhone) => {
    setEditingId(item.id);
    setForm({ phone: item.phone, name: item.name || '', active: item.active ?? true });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.phone.trim()) {
      toast.error('Informe o número de telefone');
      return;
    }
    setSaving(true);
    try {
      const data = { phone: form.phone.trim(), name: form.name.trim() || null, active: form.active };
      if (editingId) {
        await client.entities.whatsapp_admin_phones.update({ id: String(editingId), data });
        toast.success('Número atualizado com sucesso!');
      } else {
        await client.entities.whatsapp_admin_phones.create({ data });
        toast.success('Número adicionado com sucesso!');
      }
      setDialogOpen(false);
      loadPhones();
    } catch (error: any) {
      const msg = error?.response?.data?.detail || error?.message || 'Erro ao salvar';
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    setDeleting(id);
    try {
      await client.entities.whatsapp_admin_phones.delete({ id: String(id) });
      toast.success('Número removido com sucesso!');
      loadPhones();
    } catch (error: any) {
      toast.error('Erro ao remover número');
    } finally {
      setDeleting(null);
    }
  };

  const handleToggleActive = async (item: AdminPhone) => {
    try {
      await client.entities.whatsapp_admin_phones.update({
        id: String(item.id),
        data: { active: !item.active },
      });
      loadPhones();
    } catch (error: any) {
      toast.error('Erro ao atualizar status');
    }
  };

  const activeCount = phones.filter(p => p.active).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Números de Administrador</h1>
          <p className="text-muted-foreground mt-1">
            Gerencie os números que recebem mensagens para aprovação de anúncios antes do envio aos compradores.
          </p>
        </div>
        <Button onClick={openCreate} className="gap-2">
          <Plus className="h-4 w-4" />
          Adicionar Número
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-blue-100 p-2.5">
                <Phone className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total de Números</p>
                <p className="text-2xl font-bold">{phones.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-green-100 p-2.5">
                <UserCheck className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Ativos</p>
                <p className="text-2xl font-bold">{activeCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-orange-100 p-2.5">
                <AlertCircle className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Inativos</p>
                <p className="text-2xl font-bold">{phones.length - activeCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Phone List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Números Cadastrados</CardTitle>
          <CardDescription>
            Estes números recebem notificações WhatsApp quando novas ofertas são criadas ou mensagens de compradores precisam de atenção.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
            </div>
          ) : phones.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Phone className="h-10 w-10 mx-auto mb-3 opacity-40" />
              <p>Nenhum número de administrador cadastrado.</p>
              <p className="text-sm mt-1">Clique em "Adicionar Número" para começar.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {phones.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between rounded-lg border p-4 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="rounded-full bg-muted p-2.5">
                      <Phone className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{item.name || 'Sem nome'}</span>
                        <Badge variant={item.active ? 'default' : 'secondary'} className="text-xs">
                          {item.active ? 'Ativo' : 'Inativo'}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{item.phone}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <Label htmlFor={`active-${item.id}`} className="text-xs text-muted-foreground">
                        Ativo
                      </Label>
                      <Switch
                        id={`active-${item.id}`}
                        checked={item.active ?? true}
                        onCheckedChange={() => handleToggleActive(item)}
                      />
                    </div>
                    <Button variant="ghost" size="icon" onClick={() => openEdit(item)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(item.id)}
                      disabled={deleting === item.id}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingId ? 'Editar Número' : 'Adicionar Número'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label htmlFor="phone">Número do WhatsApp</Label>
              <Input
                id="phone"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="5521999999999"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Informe o número no formato internacional, apenas dígitos (ex: 5521999999999).
              </p>
            </div>
            <div>
              <Label htmlFor="name">Nome do Administrador</Label>
              <Input
                id="name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="João Silva"
              />
            </div>
            <div className="flex items-center gap-3">
              <Switch
                id="active-new"
                checked={form.active}
                onCheckedChange={(checked) => setForm({ ...form, active: checked })}
              />
              <Label htmlFor="active-new">Ativo (receber notificações)</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? 'Salvando...' : editingId ? 'Atualizar' : 'Adicionar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}