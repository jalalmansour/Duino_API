import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

const MLX_MODELS = [
  { id: 'unsloth/gemma-4-E2B-it-UD-MLX-4bit', name: 'Gemma 4 E2B (MLX 4-bit)' },
  { id: 'unsloth/gemma-4-E4B-it-UD-MLX-4bit', name: 'Gemma 4 E4B (MLX 4-bit)' },
  { id: 'unsloth/gemma-4-26b-a4b-it-UD-MLX-4bit', name: 'Gemma 4 26B A4B (MLX 4-bit)' },
  { id: 'unsloth/gemma-4-31b-it-UD-MLX-4bit', name: 'Gemma 4 31B (MLX 4-bit, Vision)' },
];

export default function ModelsPage({ apiUrl, apiKey, currentModel, onSelectModel }: any) {
  const [apiModels, setApiModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    async function fetchModels() {
      if (!apiUrl) return;
      setLoading(true);
      try {
        const res = await fetch(`${apiUrl}/v1/models`, {
          headers: apiKey ? { 'X-API-Key': apiKey } : {}
        });
        if (!res.ok) throw new Error('Models fetch failed');
        const data = await res.json();
        setApiModels(data.data || []);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchModels();
  }, [apiUrl, apiKey]);

  return (
    <div className="flex flex-col gap-10">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-bone mb-3">Models</h1>
        <p className="text-mist font-normal">
          Select and provision inference resources for active sessions.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-ink border-l-2 border-crimson text-[14px] text-bone">
          {error}
        </div>
      )}

      <Card className="bg-ink border-slate rounded-[6px] shadow-none">
        <CardHeader className="flex flex-row justify-between items-center border-b border-slate/50 pb-6">
          <div>
            <CardTitle className="text-xs font-semibold text-mist uppercase tracking-[0.08em]">Provisioned Cloud Models</CardTitle>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            className="h-8 text-[11px] uppercase tracking-widest bg-slate/20 border-slate rounded-[4px]"
            onClick={() => window.location.reload()} 
            disabled={loading}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {apiModels.length === 0 && !loading ? (
            <p className="text-mist text-sm p-8">No models discovered in current gateway.</p>
          ) : (
            <div className="overflow-x-auto">
              <Table className="rounded-none border-none">
                <TableHeader className="bg-void">
                  <TableRow className="border-slate hover:bg-transparent">
                    <TableHead className="text-[10px] font-semibold uppercase tracking-[0.08em] text-mist py-4">Model ID</TableHead>
                    <TableHead className="text-[10px] font-semibold uppercase tracking-[0.08em] text-mist py-4">Publisher</TableHead>
                    <TableHead className="text-[10px] font-semibold uppercase tracking-[0.08em] text-mist py-4">State</TableHead>
                    <TableHead className="text-[10px] font-semibold uppercase tracking-[0.08em] text-mist py-4 text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {apiModels.map(m => (
                    <TableRow key={m.id} className="border-slate hover:bg-slate/10 transition-colors">
                      <TableCell className="font-mono text-sm text-bone py-4">{m.id}</TableCell>
                      <TableCell className="text-mist text-sm py-4">{m.owned_by}</TableCell>
                      <TableCell className="py-4">
                        <span className="text-[11px] font-medium text-bone uppercase tracking-tight">Active</span>
                      </TableCell>
                      <TableCell className="text-right py-4">
                        <Button 
                          variant={currentModel === m.id ? 'secondary' : 'outline'}
                          className={`h-8 px-4 text-[11px] uppercase tracking-widest rounded-[4px] ${
                            currentModel === m.id ? 'bg-bone text-void hover:bg-bone' : 'border-slate bg-slate/10'
                          }`}
                          onClick={() => onSelectModel(m.id)}
                          disabled={currentModel === m.id}
                        >
                          {currentModel === m.id ? 'Active' : 'Select'}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-ink border-slate rounded-[6px] shadow-none">
        <CardHeader className="border-b border-slate/50 pb-6">
          <CardTitle className="text-xs font-semibold text-mist uppercase tracking-[0.08em]">Local MLX Resources</CardTitle>
          <CardDescription className="text-mist font-normal mt-1">
            Execution via Apple Silicon unified memory / MLX framework.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="p-8 border-b border-slate/50 bg-void/30">
            <p className="text-[10px] font-semibold text-mist uppercase tracking-[0.08em] mb-4">Provisioning command</p>
            <pre className="p-5 bg-void border border-slate rounded-none overflow-x-auto text-xs font-mono text-violet">
              <code>bash studio/install_gemma4_mlx.sh</code>
            </pre>
          </div>

          <div className="overflow-x-auto">
            <Table className="rounded-none border-none">
              <TableHeader className="bg-void">
                <TableRow className="border-slate hover:bg-transparent">
                  <TableHead className="text-[10px] font-semibold uppercase tracking-[0.08em] text-mist py-4">MLX Resource ID</TableHead>
                  <TableHead className="text-[10px] font-semibold uppercase tracking-[0.08em] text-mist py-4">Architecture</TableHead>
                  <TableHead className="text-[10px] font-semibold uppercase tracking-[0.08em] text-mist py-4 text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {MLX_MODELS.map(m => (
                  <TableRow key={m.id} className="border-slate hover:bg-slate/10 transition-colors">
                    <TableCell className="font-mono text-sm text-bone py-4">{m.id}</TableCell>
                    <TableCell className="text-mist text-sm py-4">{m.name}</TableCell>
                    <TableCell className="text-right py-4">
                      <Button 
                        variant={currentModel === m.id ? 'secondary' : 'outline'}
                        className={`h-8 px-4 text-[11px] uppercase tracking-widest rounded-[4px] ${
                          currentModel === m.id ? 'bg-bone text-void hover:bg-bone' : 'border-slate bg-slate/10'
                        }`}
                        onClick={() => onSelectModel(m.id)}
                        disabled={currentModel === m.id}
                      >
                        {currentModel === m.id ? 'Active' : 'Select'}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
