import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { DossierFile } from './types';

interface VehicleFileListProps {
  files: DossierFile[];
  admin?: boolean;
  onDownload: (file: DossierFile) => void;
  onToggleRelease?: (file: DossierFile) => void;
  onDelete?: (file: DossierFile) => void;
}

export default function VehicleFileList({
  files,
  admin = false,
  onDownload,
  onToggleRelease,
  onDelete,
}: VehicleFileListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Arquivos do veiculo</CardTitle>
      </CardHeader>
      <CardContent>
        {files.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum arquivo registrado.</p>
        ) : (
          <div className="space-y-2">
            {files.map((file) => (
              <div key={file.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3">
                <div>
                  <p className="text-sm font-medium">{file.file_name || file.storage_key}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{file.file_type}</Badge>
                    {admin && (
                      <Badge variant={file.is_released_to_buyer ? 'default' : 'secondary'}>
                        {file.is_released_to_buyer ? 'Liberado ao comprador' : 'Restrito ao admin'}
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => onDownload(file)}>
                    Baixar
                  </Button>
                  {admin && onToggleRelease && (
                    <Button variant="ghost" size="sm" onClick={() => onToggleRelease(file)}>
                      {file.is_released_to_buyer ? 'Bloquear' : 'Liberar'}
                    </Button>
                  )}
                  {admin && onDelete && (
                    <Button variant="ghost" size="sm" onClick={() => onDelete(file)}>
                      Remover
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
