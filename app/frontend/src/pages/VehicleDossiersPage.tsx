import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Search, Upload } from 'lucide-react';
import { client } from '@/lib/api';
import { toast } from 'sonner';
import VehicleConsultationTimeline from '@/components/vehicle-dossier/VehicleConsultationTimeline';
import VehicleDossierSummary from '@/components/vehicle-dossier/VehicleDossierSummary';
import VehicleFileList from '@/components/vehicle-dossier/VehicleFileList';
import VehicleNegotiationTimeline from '@/components/vehicle-dossier/VehicleNegotiationTimeline';
import type { DossierFile, DossierSummary, VehicleDossierDetail } from '@/components/vehicle-dossier/types';

export default function VehicleDossiersPage() {
  const [items, setItems] = useState<DossierSummary[]>([]);
  const [detail, setDetail] = useState<VehicleDossierDetail | null>(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [fileType, setFileType] = useState('document');
  const [releaseToBuyer, setReleaseToBuyer] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadDossiers();
  }, []);

  const loadDossiers = async (plate = '') => {
    setLoading(true);
    try {
      const url = plate ? `/api/v1/vehicle-dossiers?plate=${encodeURIComponent(plate)}` : '/api/v1/vehicle-dossiers';
      const res = await client.apiCall.invoke({ url, method: 'GET' });
      setItems(res.data?.items || []);
    } catch (error: any) {
      toast.error(error?.data?.detail || 'Erro ao carregar dossies');
    } finally {
      setLoading(false);
    }
  };

  const loadDetail = async (id: number) => {
    try {
      const res = await client.apiCall.invoke({ url: `/api/v1/vehicle-dossiers/${id}`, method: 'GET' });
      setDetail(res.data);
    } catch (error: any) {
      toast.error(error?.data?.detail || 'Erro ao carregar dossie');
    }
  };

  const handleSearch = () => {
    loadDossiers(search.trim());
  };

  const handleUpload = async () => {
    if (!detail || !file) return;
    setUploading(true);
    try {
      const init = await client.apiCall.invoke({
        url: `/api/v1/vehicle-dossiers/${detail.dossier.id}/files`,
        method: 'POST',
        data: {
          file_name: file.name,
          file_type: fileType,
          mime_type: file.type,
          file_size: file.size,
          is_released_to_buyer: releaseToBuyer,
        },
      });
      const uploadUrl = init.data?.upload_url;
      if (!uploadUrl) throw new Error('URL de upload nao retornada');
      const putRes = await fetch(uploadUrl, {
        method: 'PUT',
        body: file,
        headers: file.type ? { 'Content-Type': file.type } : undefined,
      });
      if (!putRes.ok) throw new Error('Falha no upload do arquivo');
      toast.success('Arquivo adicionado ao dossie');
      setFile(null);
      await loadDetail(detail.dossier.id);
    } catch (error: any) {
      toast.error(error?.message || error?.data?.detail || 'Erro ao enviar arquivo');
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (item: DossierFile) => {
    try {
      const res = await client.apiCall.invoke({
        url: `/api/v1/vehicle-dossiers/files/${item.id}/download-url`,
        method: 'POST',
      });
      if (res.data?.download_url) window.open(res.data.download_url, '_blank');
    } catch (error: any) {
      toast.error(error?.data?.detail || 'Erro ao baixar arquivo');
    }
  };

  const handleToggleRelease = async (item: DossierFile) => {
    if (!detail) return;
    try {
      await client.apiCall.invoke({
        url: `/api/v1/vehicle-dossiers/files/${item.id}`,
        method: 'PUT',
        data: {
          is_released_to_buyer: !item.is_released_to_buyer,
          file_type: item.file_type,
        },
      });
      await loadDetail(detail.dossier.id);
    } catch (error: any) {
      toast.error(error?.data?.detail || 'Erro ao atualizar permissao');
    }
  };

  const handleDeleteFile = async (item: DossierFile) => {
    if (!detail) return;
    try {
      await client.apiCall.invoke({
        url: `/api/v1/vehicle-dossiers/files/${item.id}`,
        method: 'DELETE',
      });
      await loadDetail(detail.dossier.id);
      toast.success('Arquivo removido');
    } catch (error: any) {
      toast.error(error?.data?.detail || 'Erro ao remover arquivo');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1>Dossie do Veiculo</h1>
        <p className="text-muted-foreground mt-1">Consulte o arquivo historico por placa, venda, documentos e negociacoes.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Buscar dossie</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-3 md:flex-row">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input className="pl-9" placeholder="Informe a placa" value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <Button onClick={handleSearch}>Buscar</Button>
            <Button variant="outline" onClick={() => { setSearch(''); loadDossiers(); }}>Limpar</Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Dossies</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-sm text-muted-foreground">Carregando...</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Placa</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Acoes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center text-muted-foreground">Nenhum dossie encontrado</TableCell>
                    </TableRow>
                  ) : items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-mono">{item.plate}</TableCell>
                      <TableCell>{item.status || '-'}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" onClick={() => loadDetail(item.id)}>Abrir</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          {!detail ? (
            <Card>
              <CardContent className="py-10 text-center text-muted-foreground">
                Selecione um dossie para visualizar os detalhes.
              </CardContent>
            </Card>
          ) : (
            <>
              <VehicleDossierSummary detail={detail} />
              <Card>
                <CardHeader>
                  <CardTitle>Adicionar arquivo</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-4 md:grid-cols-[1fr_180px_180px_auto] md:items-end">
                  <div>
                    <Label>Arquivo</Label>
                    <Input type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} />
                  </div>
                  <div>
                    <Label>Tipo</Label>
                    <Select value={fileType} onValueChange={setFileType}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="photo">Foto</SelectItem>
                        <SelectItem value="receipt">Recibo</SelectItem>
                        <SelectItem value="proof">Comprovante</SelectItem>
                        <SelectItem value="document">Documento</SelectItem>
                        <SelectItem value="other">Outro</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Comprador</Label>
                    <Select value={releaseToBuyer ? 'yes' : 'no'} onValueChange={(value) => setReleaseToBuyer(value === 'yes')}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="no">Restrito</SelectItem>
                        <SelectItem value="yes">Liberado</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={handleUpload} disabled={!file || uploading}>
                    <Upload className="mr-2 h-4 w-4" />
                    Enviar
                  </Button>
                </CardContent>
              </Card>
              <VehicleFileList
                files={detail.files}
                admin
                onDownload={handleDownload}
                onToggleRelease={handleToggleRelease}
                onDelete={handleDeleteFile}
              />
              <VehicleConsultationTimeline consultations={detail.consultations} />
              <VehicleNegotiationTimeline history={detail.negotiation_history} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
