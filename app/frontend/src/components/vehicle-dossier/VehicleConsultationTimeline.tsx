import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { DossierConsultation } from './types';

export default function VehicleConsultationTimeline({ consultations }: { consultations: DossierConsultation[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Consultas realizadas</CardTitle>
      </CardHeader>
      <CardContent>
        {consultations.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhuma consulta registrada.</p>
        ) : (
          <div className="space-y-3">
            {consultations.map((item) => (
              <div key={item.id} className="rounded-md border p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium">
                      {item.source || 'Fonte desconhecida'} - {item.created_at ? new Date(item.created_at).toLocaleString('pt-BR') : '-'}
                    </p>
                    <p className="text-xs text-muted-foreground">Placa {item.plate}</p>
                  </div>
                  <Badge variant={item.success ? 'default' : 'destructive'}>
                    {item.success ? 'Sucesso' : 'Erro'}
                  </Badge>
                </div>
                {item.error_message && <p className="text-sm text-destructive mt-2">{item.error_message}</p>}
                {item.result && (
                  <div className="mt-3 grid gap-2 md:grid-cols-3 text-sm">
                    <span>Marca: {String(item.result.brand || '-')}</span>
                    <span>Modelo: {String(item.result.model || '-')}</span>
                    <span>Ano: {String(item.result.year || item.result.ano_modelo || '-')}</span>
                    <span>Cor: {String(item.result.color || '-')}</span>
                    <span>Combustivel: {String(item.result.fuel || '-')}</span>
                    <span>FIPE: {String(item.result.fipe_price || '-')}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
