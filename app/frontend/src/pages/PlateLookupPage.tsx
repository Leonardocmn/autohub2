import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Search,
  Car,
  Fuel,
  Calendar,
  Palette,
  Gauge,
  MapPin,
  Zap,
  Wrench,
  FileText,
  DollarSign,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { toast } from 'sonner';

interface PlateResult {
  success: boolean;
  source?: string;
  plate?: string;
  brand?: string;
  model?: string;
  year?: string;
  color?: string;
  fuel?: string;
  chassi?: string;
  segment?: string;
  procedence?: string;
  municipality?: string;
  uf?: string;
  ano_fabricacao?: string;
  ano_modelo?: string;
  vehicle_type?: string;
  sub_segment?: string;
  power?: string;
  displacement?: string;
  fipe_code?: string;
  fipe_price?: string;
  fipe_reference?: string;
  fipe_versions?: Array<{
    codigo_fipe: string;
    modelo_versao: string;
    preco: string;
    mes_referencia: string;
  }>;
  error?: string;
}

export default function PlateLookupPage() {
  const [plateInput, setPlateInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PlateResult | null>(null);
  const [showVersions, setShowVersions] = useState(false);

  const handleLookup = async () => {
    const plate = plateInput.trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
    if (!plate || plate.length < 7) {
      toast.error('Digite uma placa válida (formato ABC1D23 ou ABC1234)');
      return;
    }

    setLoading(true);
    setResult(null);
    setShowVersions(false);

    try {
      const token = localStorage.getItem('auth_token') || '';
      const res = await fetch('/api/v1/vehicle-dossiers/plate-lookup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ plate }),
      });
      const data = await res.json();
      setResult(data);

      if (data.success) {
        const source = data.source === 'consultarplaca' ? 'ConsultarPlaca' : 'BrasilAPI';
        toast.success(`Veículo encontrado via ${source}`);
      } else {
        toast.error(data.error || 'Placa não encontrada');
      }
    } catch {
      toast.error('Erro ao consultar placa');
    } finally {
      setLoading(false);
    }
  };

  const formatPrice = (value: string | number | undefined) => {
    if (!value) return '-';
    if (typeof value === 'string' && value.startsWith('R$')) return value;
    try {
      const num = typeof value === 'string' ? parseFloat(value) : value;
      return `R$ ${num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    } catch {
      return String(value);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Consulta de Placa</h1>
        <p className="text-muted-foreground mt-1">
          Consulte dados do veículo e preço FIPE pela placa. Integração com ConsultarPlaca e BrasilAPI.
        </p>
      </div>

      {/* Search Card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={plateInput}
                onChange={(e) => setPlateInput(e.target.value.toUpperCase())}
                placeholder="Digite a placa (ex: ABC1D23)"
                className="pl-9 uppercase font-mono text-lg tracking-wider"
                maxLength={8}
                onKeyDown={(e) => { if (e.key === 'Enter') handleLookup(); }}
              />
            </div>
            <Button
              onClick={handleLookup}
              disabled={loading || !plateInput.trim()}
              className="bg-[#F16801] hover:bg-[#d55d01] text-white min-w-[140px]"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Consultando...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Consultar
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Error State */}
      {result && !result.success && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-6 w-6 text-red-500 flex-shrink-0" />
              <div>
                <p className="font-medium text-red-700">Consulta sem resultado</p>
                <p className="text-sm text-red-600">{result.error || 'Placa não encontrada na base de dados.'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Success Result */}
      {result && result.success && (
        <div className="space-y-4">
          {/* Source Badge */}
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              Fonte: {result.source === 'consultarplaca' ? 'ConsultarPlaca' : 'BrasilAPI'}
            </Badge>
            {result.fipe_price && (
              <Badge className="bg-green-100 text-green-700 border-green-200">
                <DollarSign className="h-3 w-3 mr-1" />
                FIPE disponível
              </Badge>
            )}
          </div>

          {/* Main Vehicle Info */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <Car className="h-5 w-5 text-[#F16801]" />
                {result.brand} {result.model}
              </CardTitle>
              <p className="text-sm text-muted-foreground font-mono">
                Placa: {result.plate}
              </p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                <InfoItem icon={<Car className="h-4 w-4" />} label="Marca" value={result.brand} />
                <InfoItem icon={<Car className="h-4 w-4" />} label="Modelo" value={result.model} />
                <InfoItem icon={<Calendar className="h-4 w-4" />} label="Ano Fabricação" value={result.ano_fabricacao || result.year} />
                <InfoItem icon={<Calendar className="h-4 w-4" />} label="Ano Modelo" value={result.ano_modelo || result.year} />
                <InfoItem icon={<Palette className="h-4 w-4" />} label="Cor" value={result.color} />
                <InfoItem icon={<Fuel className="h-4 w-4" />} label="Combustível" value={result.fuel} />
                <InfoItem icon={<Gauge className="h-4 w-4" />} label="Segmento" value={result.segment} />
                <InfoItem icon={<MapPin className="h-4 w-4" />} label="Município" value={result.municipality} />
                <InfoItem icon={<MapPin className="h-4 w-4" />} label="UF" value={result.uf} />
                <InfoItem icon={<FileText className="h-4 w-4" />} label="Procedência" value={result.procedence} />
                <InfoItem icon={<Zap className="h-4 w-4" />} label="Potência" value={result.power ? `${result.power} cv` : undefined} />
                <InfoItem icon={<Wrench className="h-4 w-4" />} label="Cilindradas" value={result.displacement ? `${result.displacement} cc` : undefined} />
              </div>
            </CardContent>
          </Card>

          {/* FIPE Price Card */}
          {result.fipe_price && (
            <Card className="border-green-200 bg-gradient-to-br from-green-50 to-emerald-50">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-green-800">
                  <DollarSign className="h-5 w-5" />
                  Preço FIPE
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-green-600">Preço Referência</p>
                    <p className="text-2xl font-bold text-green-800">{result.fipe_price}</p>
                  </div>
                  <div>
                    <p className="text-sm text-green-600">Mês Referência</p>
                    <p className="text-lg font-semibold text-green-800">{result.fipe_reference || '-'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-green-600">Código FIPE</p>
                    <p className="text-lg font-mono font-semibold text-green-800">{result.fipe_code || '-'}</p>
                  </div>
                </div>

                {/* FIPE Versions */}
                {result.fipe_versions && result.fipe_versions.length > 1 && (
                  <div className="mt-4">
                    <Separator className="mb-3" />
                    <button
                      className="flex items-center gap-1 text-sm font-medium text-green-700 hover:text-green-900 transition-colors"
                      onClick={() => setShowVersions(!showVersions)}
                    >
                      {showVersions ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      {result.fipe_versions.length} versões FIPE disponíveis
                    </button>
                    {showVersions && (
                      <div className="mt-3 space-y-2">
                        {result.fipe_versions.map((v, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between p-3 bg-white/70 rounded-lg border border-green-100"
                          >
                            <div>
                              <p className="font-medium text-sm">{v.modelo_versao || '-'}</p>
                              <p className="text-xs text-muted-foreground">
                                FIPE: {v.codigo_fipe} | Ref: {v.mes_referencia}
                              </p>
                            </div>
                            <p className="font-semibold text-green-700">
                              {formatPrice(v.preco)}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Chassi (restricted info) */}
          {result.chassi && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Chassi:</span>
                  <span className="font-mono text-sm">{result.chassi}</span>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Empty State */}
      {!result && !loading && (
        <Card>
          <CardContent className="py-16 text-center">
            <Car className="h-12 w-12 mx-auto text-muted-foreground/40 mb-4" />
            <p className="text-lg font-medium text-muted-foreground">Consulte uma placa para ver os dados do veículo</p>
            <p className="text-sm text-muted-foreground mt-1">
              Dados de marca, modelo, ano, cor, combustível, FIPE e mais.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function InfoItem({ icon, label, value }: { icon: React.ReactNode; label: string; value?: string | null }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="font-medium text-sm">{value || '-'}</p>
    </div>
  );
}