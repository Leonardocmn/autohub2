import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { VehicleDossierDetail } from './types';

export default function VehicleDossierSummary({ detail }: { detail: VehicleDossierDetail }) {
  const { dossier, offer, buyer } = detail;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle>{dossier.plate}</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {offer?.title || [offer?.brand, offer?.model, offer?.year].filter(Boolean).join(' ') || 'Veiculo sem oferta vinculada'}
            </p>
          </div>
          <Badge variant={dossier.status === 'sold' ? 'default' : 'outline'}>
            {dossier.status === 'sold' ? 'Vendido' : dossier.status || 'Ativo'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <p className="text-xs text-muted-foreground">Comprador</p>
            <p className="font-medium">{buyer?.name || '-'}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Data do anuncio</p>
            <p className="font-medium">{offer?.created_at ? new Date(offer.created_at).toLocaleDateString('pt-BR') : '-'}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Data da venda</p>
            <p className="font-medium">{offer?.sold_at ? new Date(offer.sold_at).toLocaleDateString('pt-BR') : '-'}</p>
          </div>
        </div>
        {offer?.description && (
          <div className="mt-4">
            <p className="text-xs text-muted-foreground">Descricao do anuncio</p>
            <p className="text-sm whitespace-pre-wrap">{offer.description}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
