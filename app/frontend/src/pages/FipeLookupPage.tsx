import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Search,
  Car,
  DollarSign,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  FileText,
  Calendar,
  Fuel,
  Palette,
  History,
  Hash,
} from 'lucide-react';
import { toast } from 'sonner';

interface FipePriceEntry {
  valor: string;
  mes_referencia: string;
  ano_modelo: string;
  combustivel: string;
  codigo_fipe: string;
  modelo: string;
}

interface FipeVersion {
  codigo_fipe: string;
  modelo_versao: string;
  preco: string;
  mes_referencia: string;
}

interface FipeResult {
  success: boolean;
  source?: string;
  fipe_code?: string;
  plate?: string;
  brand?: string;
  model?: string;
  year?: string;
  color?: string;
  fuel?: string;
  vehicle_description?: string;
  price_returned?: string;
  fipe_price?: string;
  fipe_reference?: string;
  reference_month?: string;
  prices?: FipePriceEntry[];
  fipe_versions?: FipeVersion[];
  consultation_id?: number;
  error?: string;
}

interface LogEntry {
  id: number;
  phone: string;
  plate: string | null;
  fipe_code: string | null;
  vehicle_description: string | null;
  price_returned: string | null;
  source: string;
  user_id: string | null;
  result: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export default function FipeLookupPage() {
  const [activeTab, setActiveTab] = useState('lookup');
  const [lookupMode, setLookupMode] = useState<'plate' | 'code'>('plate');
  const [plateInput, setPlateInput] = useState('');
  const [fipeCodeInput, setFipeCodeInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FipeResult | null>(null);
  const [showVersions, setShowVersions] = useState(false);
  const [showPriceHistory, setShowPriceHistory] = useState(false);

  // Consultation logs state
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsPage, setLogsPage] = useState(0);
  const [logFilter, setLogFilter] = useState({ phone: '', plate: '', fipe_code: '', source: '' });

  const handleLookup = async () => {
    if (lookupMode === 'plate') {
      const plate = plateInput.trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
      if (!plate || plate.length < 7) {
        toast.error('Digite uma placa válida (formato ABC1D23 ou ABC1234)');
        return;
      }
      setLoading(true);
      setResult(null);
      setShowVersions(false);
      setShowPriceHistory(false);

      try {
        const token = localStorage.getItem('auth_token') || '';
        const res = await fetch('/api/v1/fipe/lookup-by-plate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ plate }),
        });
        const data = await res.json();
        setResult(data);
        if (data.success) {
          toast.success(`FIPE consultado com sucesso`);
        } else {
          toast.error(data.error || 'Consulta sem resultado');
        }
      } catch {
        toast.error('Erro ao consultar FIPE');
      } finally {
        setLoading(false);
      }
    } else {
      const code = fipeCodeInput.trim().toUpperCase().replace(/[^A-Z0-9-]/g, '');
      if (!code || code.length < 5) {
        toast.error('Digite um código FIPE válido');
        return;
      }
      setLoading(true);
      setResult(null);
      setShowVersions(false);
      setShowPriceHistory(false);

      try {
        const token = localStorage.getItem('auth_token') || '';
        const res = await fetch('/api/v1/fipe/lookup-by-code', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ fipe_code: code }),
        });
        const data = await res.json();
        setResult(data);
        if (data.success) {
          toast.success('FIPE consultado com sucesso');
        } else {
          toast.error(data.error || 'Consulta sem resultado');
        }
      } catch {
        toast.error('Erro ao consultar FIPE');
      } finally {
        setLoading(false);
      }
    }
  };

  const fetchLogs = async (page = 0) => {
    setLogsLoading(true);
    try {
      const token = localStorage.getItem('auth_token') || '';
      const params = new URLSearchParams({
        skip: String(page * 20),
        limit: '20',
        ...(logFilter.phone && { phone: logFilter.phone }),
        ...(logFilter.plate && { plate: logFilter.plate }),
        ...(logFilter.fipe_code && { fipe_code: logFilter.fipe_code }),
        ...(logFilter.source && { source: logFilter.source }),
      });
      const res = await fetch(`/api/v1/fipe/consultation-logs?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setLogs(data.items || []);
      setLogsTotal(data.total || 0);
      setLogsPage(page);
    } catch {
      toast.error('Erro ao carregar logs de consulta');
    } finally {
      setLogsLoading(false);
    }
  };

  const formatPrice = (value: string | undefined) => {
    if (!value) return '-';
    if (typeof value === 'string' && value.startsWith('R$')) return value;
    try {
      const num = typeof value === 'string' ? parseFloat(value) : value;
      return `R$ ${num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    } catch {
      return String(value);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    try {
      const d = new Date(dateStr);
      return d.toLocaleString('pt-BR');
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Consulta FIPE</h1>
        <p className="text-muted-foreground mt-1">
          Consulte o preço FIPE por placa ou código FIPE. Todas as consultas são registradas para auditoria.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v); if (v === 'logs') fetchLogs(0); }}>
        <TabsList>
          <TabsTrigger value="lookup">Consulta FIPE</TabsTrigger>
          <TabsTrigger value="logs">Logs de Consulta</TabsTrigger>
        </TabsList>

        {/* ===== Lookup Tab ===== */}
        <TabsContent value="lookup" className="space-y-4 mt-4">
          {/* Mode Toggle + Search */}
          <Card>
            <CardContent className="pt-6 space-y-4">
              <div className="flex gap-2">
                <Button
                  variant={lookupMode === 'plate' ? 'default' : 'outline'}
                  onClick={() => setLookupMode('plate')}
                  className={lookupMode === 'plate' ? 'bg-[#F16801] hover:bg-[#d55d01] text-white' : ''}
                >
                  <Car className="h-4 w-4 mr-2" />
                  Por Placa
                </Button>
                <Button
                  variant={lookupMode === 'code' ? 'default' : 'outline'}
                  onClick={() => setLookupMode('code')}
                  className={lookupMode === 'code' ? 'bg-[#F16801] hover:bg-[#d55d01] text-white' : ''}
                >
                  <Hash className="h-4 w-4 mr-2" />
                  Por Código FIPE
                </Button>
              </div>

              <div className="flex flex-col sm:flex-row gap-3">
                {lookupMode === 'plate' ? (
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
                ) : (
                  <div className="relative flex-1 max-w-md">
                    <Hash className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      value={fipeCodeInput}
                      onChange={(e) => setFipeCodeInput(e.target.value.toUpperCase())}
                      placeholder="Digite o código FIPE (ex: 001267-0)"
                      className="pl-9 uppercase font-mono text-lg tracking-wider"
                      maxLength={12}
                      onKeyDown={(e) => { if (e.key === 'Enter') handleLookup(); }}
                    />
                  </div>
                )}
                <Button
                  onClick={handleLookup}
                  disabled={loading || (lookupMode === 'plate' ? !plateInput.trim() : !fipeCodeInput.trim())}
                  className="bg-[#F16801] hover:bg-[#d55d01] text-white min-w-[140px]"
                >
                  {loading ? (
                    <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Consultando...</>
                  ) : (
                    <><Search className="h-4 w-4 mr-2" />Consultar</>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Error */}
          {result && !result.success && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <AlertCircle className="h-6 w-6 text-red-500 flex-shrink-0" />
                  <div>
                    <p className="font-medium text-red-700">Consulta sem resultado</p>
                    <p className="text-sm text-red-600">{result.error || 'Nenhum dado encontrado.'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Success Result */}
          {result && result.success && (
            <div className="space-y-4">
              {/* Source Badge */}
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="outline" className="text-xs">
                  Fonte: {result.source === 'consultarplaca' ? 'ConsultarPlaca' : 'BrasilAPI'}
                </Badge>
                {(result.fipe_price || result.price_returned) && (
                  <Badge className="bg-green-100 text-green-700 border-green-200">
                    <DollarSign className="h-3 w-3 mr-1" />
                    FIPE disponível
                  </Badge>
                )}
                {result.consultation_id && (
                  <Badge variant="secondary" className="text-xs">
                    <FileText className="h-3 w-3 mr-1" />
                    Log #{result.consultation_id}
                  </Badge>
                )}
              </div>

              {/* Vehicle Info (plate lookup) */}
              {(result.brand || result.model) && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2">
                      <Car className="h-5 w-5 text-[#F16801]" />
                      {result.brand} {result.model}
                    </CardTitle>
                    {result.plate && (
                      <p className="text-sm text-muted-foreground font-mono">
                        Placa: {result.plate}
                      </p>
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                      {result.brand && <InfoItem icon={<Car className="h-4 w-4" />} label="Marca" value={result.brand} />}
                      {result.model && <InfoItem icon={<Car className="h-4 w-4" />} label="Modelo" value={result.model} />}
                      {result.year && <InfoItem icon={<Calendar className="h-4 w-4" />} label="Ano" value={result.year} />}
                      {result.color && <InfoItem icon={<Palette className="h-4 w-4" />} label="Cor" value={result.color} />}
                      {result.fuel && <InfoItem icon={<Fuel className="h-4 w-4" />} label="Combustível" value={result.fuel} />}
                      {result.fipe_code && <InfoItem icon={<Hash className="h-4 w-4" />} label="Código FIPE" value={result.fipe_code} />}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Vehicle Description (code lookup) */}
              {result.vehicle_description && !result.brand && (
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center gap-2">
                      <Car className="h-5 w-5 text-[#F16801]" />
                      <span className="text-lg font-semibold">{result.vehicle_description}</span>
                    </div>
                    {result.fipe_code && (
                      <p className="text-sm text-muted-foreground mt-1 font-mono">
                        Código FIPE: {result.fipe_code}
                      </p>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* FIPE Price Card */}
              {(result.fipe_price || result.price_returned) && (
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
                        <p className="text-2xl font-bold text-green-800">
                          {result.fipe_price || result.price_returned || '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-green-600">Mês Referência</p>
                        <p className="text-lg font-semibold text-green-800">
                          {result.fipe_reference || result.reference_month || '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-green-600">Código FIPE</p>
                        <p className="text-lg font-mono font-semibold text-green-800">
                          {result.fipe_code || '-'}
                        </p>
                      </div>
                    </div>

                    {/* FIPE Versions (ConsultarPlaca) */}
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

                    {/* Price History (BrasilAPI) */}
                    {result.prices && result.prices.length > 1 && (
                      <div className="mt-4">
                        <Separator className="mb-3" />
                        <button
                          className="flex items-center gap-1 text-sm font-medium text-green-700 hover:text-green-900 transition-colors"
                          onClick={() => setShowPriceHistory(!showPriceHistory)}
                        >
                          {showPriceHistory ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          Histórico de preços ({result.prices.length} meses)
                        </button>
                        {showPriceHistory && (
                          <div className="mt-3 space-y-2">
                            {result.prices.map((p, idx) => (
                              <div
                                key={idx}
                                className="flex items-center justify-between p-3 bg-white/70 rounded-lg border border-green-100"
                              >
                                <div>
                                  <p className="font-medium text-sm">{p.modelo || p.ano_modelo || '-'}</p>
                                  <p className="text-xs text-muted-foreground">
                                    Ref: {p.mes_referencia} | {p.combustivel} | Ano: {p.ano_modelo}
                                  </p>
                                </div>
                                <p className="font-semibold text-green-700">{p.valor}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* Empty State */}
          {!result && !loading && (
            <Card>
              <CardContent className="py-16 text-center">
                <DollarSign className="h-12 w-12 mx-auto text-muted-foreground/40 mb-4" />
                <p className="text-lg font-medium text-muted-foreground">Consulte o preço FIPE do veículo</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Busque por placa ou código FIPE. Preço de referência, histórico e versões.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ===== Logs Tab ===== */}
        <TabsContent value="logs" className="space-y-4 mt-4">
          {/* Filters */}
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                <div>
                  <Label className="text-xs">Telefone</Label>
                  <Input
                    value={logFilter.phone}
                    onChange={(e) => setLogFilter({ ...logFilter, phone: e.target.value })}
                    placeholder="Filtrar telefone"
                    className="h-9 text-sm"
                  />
                </div>
                <div>
                  <Label className="text-xs">Placa</Label>
                  <Input
                    value={logFilter.plate}
                    onChange={(e) => setLogFilter({ ...logFilter, plate: e.target.value.toUpperCase() })}
                    placeholder="Filtrar placa"
                    className="h-9 text-sm uppercase"
                  />
                </div>
                <div>
                  <Label className="text-xs">Código FIPE</Label>
                  <Input
                    value={logFilter.fipe_code}
                    onChange={(e) => setLogFilter({ ...logFilter, fipe_code: e.target.value })}
                    placeholder="Filtrar código"
                    className="h-9 text-sm"
                  />
                </div>
                <div>
                  <Label className="text-xs">Origem</Label>
                  <Input
                    value={logFilter.source}
                    onChange={(e) => setLogFilter({ ...logFilter, source: e.target.value })}
                    placeholder="admin, buyer, whatsapp"
                    className="h-9 text-sm"
                  />
                </div>
                <div className="flex items-end">
                  <Button
                    onClick={() => fetchLogs(0)}
                    className="bg-[#F16801] hover:bg-[#d55d01] text-white w-full"
                  >
                    <Search className="h-4 w-4 mr-2" />
                    Filtrar
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Logs Table */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <History className="h-5 w-5" />
                Logs de Consulta FIPE
                <Badge variant="secondary" className="ml-2">{logsTotal} registros</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {logsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : logs.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="h-10 w-10 mx-auto mb-2 opacity-40" />
                  <p>Nenhum log de consulta encontrado</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="pb-2 pr-3 font-medium">ID</th>
                        <th className="pb-2 pr-3 font-medium">Telefone</th>
                        <th className="pb-2 pr-3 font-medium">Placa</th>
                        <th className="pb-2 pr-3 font-medium">Código FIPE</th>
                        <th className="pb-2 pr-3 font-medium">Veículo</th>
                        <th className="pb-2 pr-3 font-medium">Preço</th>
                        <th className="pb-2 pr-3 font-medium">Origem</th>
                        <th className="pb-2 font-medium">Data</th>
                      </tr>
                    </thead>
                    <tbody>
                      {logs.map((log) => (
                        <tr key={log.id} className="border-b last:border-0 hover:bg-muted/50">
                          <td className="py-2.5 pr-3 font-mono text-xs">{log.id}</td>
                          <td className="py-2.5 pr-3 font-mono text-xs">{log.phone || '-'}</td>
                          <td className="py-2.5 pr-3 font-mono text-xs uppercase">{log.plate || '-'}</td>
                          <td className="py-2.5 pr-3 font-mono text-xs">{log.fipe_code || '-'}</td>
                          <td className="py-2.5 pr-3 max-w-[200px] truncate">{log.vehicle_description || '-'}</td>
                          <td className="py-2.5 pr-3 font-semibold text-green-700">{log.price_returned || '-'}</td>
                          <td className="py-2.5 pr-3">
                            <Badge
                              variant="outline"
                              className={
                                log.source === 'admin' ? 'border-blue-200 text-blue-700' :
                                log.source === 'buyer' ? 'border-purple-200 text-purple-700' :
                                log.source === 'whatsapp' ? 'border-green-200 text-green-700' :
                                ''
                              }
                            >
                              {log.source}
                            </Badge>
                          </td>
                          <td className="py-2.5 text-xs text-muted-foreground">{formatDate(log.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Pagination */}
              {logsTotal > 20 && (
                <div className="flex items-center justify-between mt-4 pt-3 border-t">
                  <p className="text-sm text-muted-foreground">
                    Mostrando {logsPage * 20 + 1}-{Math.min((logsPage + 1) * 20, logsTotal)} de {logsTotal}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={logsPage === 0}
                      onClick={() => fetchLogs(logsPage - 1)}
                    >
                      Anterior
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={(logsPage + 1) * 20 >= logsTotal}
                      onClick={() => fetchLogs(logsPage + 1)}
                    >
                      Próximo
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
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