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
        if (!res.ok) throw new Error('Failed to fetch models');
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
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">Models</h1>
        <p className="text-sm text-muted-foreground mt-2">
          Select and manage models for inference.
        </p>
      </div>

      {error && <div className="p-4 bg-card border-l-2 border-destructive text-sm text-foreground">{error}</div>}

      <Card className="bg-card shadow-none">
        <CardHeader className="flex flex-row justify-between items-center">
          <div>
            <CardTitle className="text-base font-semibold">Cloud Inference Models</CardTitle>
          </div>
          <Button variant="ghost" size="sm" onClick={() => window.location.reload()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </Button>
        </CardHeader>
        <CardContent>
          {apiModels.length === 0 && !loading ? (
            <p className="text-muted-foreground text-sm py-4">No models available from API.</p>
          ) : (
            <div className="rounded-md border border-border">
              <Table>
                <TableHeader className="bg-muted/50">
                  <TableRow>
                    <TableHead className="text-xs uppercase text-muted-foreground">Model ID</TableHead>
                    <TableHead className="text-xs uppercase text-muted-foreground">Owner</TableHead>
                    <TableHead className="text-xs uppercase text-muted-foreground">Status</TableHead>
                    <TableHead className="text-xs uppercase text-muted-foreground text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {apiModels.map(m => (
                    <TableRow key={m.id} className="hover:bg-muted/50">
                      <TableCell className="font-medium text-foreground">{m.id}</TableCell>
                      <TableCell className="text-muted-foreground">{m.owned_by}</TableCell>
                      <TableCell className="text-foreground">Available</TableCell>
                      <TableCell className="text-right">
                        <Button 
                          variant={currentModel === m.id ? 'default' : 'outline'}
                          size="sm"
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

      <Card className="bg-card shadow-none">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Local MLX Models (macOS Apple Silicon)</CardTitle>
          <CardDescription className="text-muted-foreground">
            Run inference locally using Apple Silicon unified memory via the MLX framework.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-6 space-y-2">
            <p className="text-sm font-medium text-foreground">Installation command:</p>
            <pre className="p-4 bg-background border border-border rounded-md overflow-x-auto text-xs font-mono text-muted-foreground">
              <code>bash studio/install_gemma4_mlx.sh</code>
            </pre>
          </div>

          <div className="rounded-md border border-border">
            <Table>
              <TableHeader className="bg-muted/50">
                <TableRow>
                  <TableHead className="text-xs uppercase text-muted-foreground">MLX Model ID</TableHead>
                  <TableHead className="text-xs uppercase text-muted-foreground">Description</TableHead>
                  <TableHead className="text-xs uppercase text-muted-foreground text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {MLX_MODELS.map(m => (
                  <TableRow key={m.id} className="hover:bg-muted/50">
                    <TableCell className="font-medium text-foreground">{m.id}</TableCell>
                    <TableCell className="text-muted-foreground">{m.name}</TableCell>
                    <TableCell className="text-right">
                      <Button 
                        variant={currentModel === m.id ? 'default' : 'outline'}
                        size="sm"
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
