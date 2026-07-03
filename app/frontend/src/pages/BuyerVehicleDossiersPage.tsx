import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { client } from '@/lib/api';
import { toast } from 'sonner';
import VehicleConsultationTimeline from '@/components/vehicle-dossier/VehicleConsultationTimeline';
import VehicleDossierSummary from '@/components/vehicle-dossier/VehicleDossierSummary';
import VehicleFileList from '@/components/vehicle-dossier/VehicleFileList';
import type { DossierFile, DossierSummary, VehicleDossierDetail } from '@/components/vehicle-dossier/types';

export default function BuyerVehicleDossiersPage() {
  const [items, setItems] = useState<DossierSummary[]>([]);
  const [detail, setDetail] = useState<VehicleDossierDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDossiers();
  }, []);

  const loadDossiers = async () => {
    setLoading(true);
    try {
      const res = await client.apiCall.invoke({ url: '/api/v1/buyer/vehicle-dossiers', method: 'GET' });
      setItems(res.data?.items || []);
    } catch (error: any) {
      toast.error(error?.data?.detail || 'Erro ao carregar seus veiculos');
    } finally {
      setLoading(false);
    }
  };

  const loadDetail = async (id: number) => {
    try {
      const res = await client.apiCall.invoke({ url: `/api/v1/buyer/vehicle-dossiers/${id}`, method: 'GET' });
      setDetail(res.data);
    } catch (error: any) {
      toast.error(error?.data?.detail || 'Dossie indisponivel');
    }
  };

  const handleDownload = async (file: DossierFile) => {
    try {
      const res = await client.apiCall.invoke({
        url: `/api/v1/buyer/vehicle-dossiers/files/${file.id}/download-url`,
        method: 'POST',
      });
      if (res.data?.download_url) window.open(res.data.download_url, '_blank');
    } catch (error: any) {
      toast.error(error?.data?.detail || 'Arquivo indisponivel');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1>Meus Veiculos</h1>
        <p className="text-muted-foreground mt-1">Consulte dossies e arquivos liberados pelo administrador.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Veiculos vinculados</CardTitle>
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
                      <TableCell colSpan={3} className="text-center text-muted-foreground">Nenhum veiculo liberado</TableCell>
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
                Selecione um veiculo para visualizar o dossie.
              </CardContent>
            </Card>
          ) : (
            <>
              <VehicleDossierSummary detail={detail} />
              <VehicleFileList files={detail.files} onDownload={handleDownload} />
              <VehicleConsultationTimeline consultations={detail.consultations} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
