import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
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
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { client } from '@/lib/api';
import { toast } from 'sonner';

interface NegotiationNumber {
  id: number;
  phone: string;
  responsible_name: string;
  status: string;
}

export default function NegotiationNumbersPage() {
  const [numbers, setNumbers] = useState<NegotiationNumber[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<NegotiationNumber | null>(null);
  const [form, setForm] = useState({ phone: '', responsible_name: '', status: 'active' });

  useEffect(() => {
    loadNumbers();
  }, []);

  const loadNumbers = async () => {
    try {
      const res = await client.entities.negotiation_numbers.query({ limit: 200 });
      setNumbers(res?.data?.items || []);
    } catch (error) {
      console.error('Error loading numbers:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      if (editing) {
        await client.entities.negotiation_numbers.update({ id: String(editing.id), data: form });
        toast.success('Número atualizado com sucesso');
      } else {
        await client.entities.negotiation_numbers.create({ data: form });
        toast.success('Número cadastrado com sucesso');
      }
      setDialogOpen(false);
      setEditing(null);
      setForm({ phone: '', responsible_name: '', status: 'active' });
      loadNumbers();
    } catch (error) {
      toast.error('Erro ao salvar número');
    }
  };

  const handleEdit = (num: NegotiationNumber) => {
    setEditing(num);
    setForm({
      phone: num.phone,
      responsible_name: num.responsible_name,
      status: num.status,
    });
    setDialogOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Tem certeza que deseja excluir este número?')) return;
    try {
      await client.entities.negotiation_numbers.delete({ id: String(id) });
      toast.success('Número excluído');
      loadNumbers();
    } catch (error) {
      toast.error('Erro ao excluir número');
    }
  };

  const handleNew = () => {
    setEditing(null);
    setForm({ phone: '', responsible_name: '', status: 'active' });
    setDialogOpen(true);
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
          <h1>Números de Negociação</h1>
          <p className="text-muted-foreground mt-1">
            Gerencie os números WhatsApp responsáveis pela negociação
          </p>
        </div>
        <Button onClick={handleNew}>
          <Plus className="h-4 w-4 mr-2" />
          Novo Número
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm text-muted-foreground">
            {numbers.length} número(s) cadastrado(s)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Responsável</TableHead>
                <TableHead>Telefone WhatsApp</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {numbers.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                    Nenhum número cadastrado
                  </TableCell>
                </TableRow>
              ) : (
                numbers.map((num) => (
                  <TableRow key={num.id}>
                    <TableCell className="font-medium">{num.responsible_name}</TableCell>
                    <TableCell>{num.phone}</TableCell>
                    <TableCell>
                      <Badge variant={num.status === 'active' ? 'default' : 'secondary'}>
                        {num.status === 'active' ? 'Ativo' : 'Inativo'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => handleEdit(num)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => handleDelete(num.id)}>
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
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? 'Editar Número' : 'Novo Número de Negociação'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Nome do Responsável</Label>
              <Input
                value={form.responsible_name}
                onChange={(e) => setForm({ ...form, responsible_name: e.target.value })}
                placeholder="Nome do responsável"
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
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={!form.phone || !form.responsible_name}>
              {editing ? 'Salvar' : 'Cadastrar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}