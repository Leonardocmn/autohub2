import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { DossierHistoryItem } from './types';

export default function VehicleNegotiationTimeline({ history }: { history: DossierHistoryItem[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Historico da negociacao</CardTitle>
      </CardHeader>
      <CardContent>
        {history.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum historico registrado.</p>
        ) : (
          <div className="space-y-3">
            {history.map((item) => (
              <div key={item.id} className="rounded-md border p-3">
                <p className="text-sm font-medium">
                  {item.previous_status || '-'} para {item.new_status || '-'}
                </p>
                <p className="text-xs text-muted-foreground">
                  {item.created_at ? new Date(item.created_at).toLocaleString('pt-BR') : '-'}
                </p>
                {item.observations && <p className="mt-2 text-sm">{item.observations}</p>}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
