import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar, View } from "./AppSidebar";
import { TooltipProvider } from "@/components/ui/tooltip";

interface RootLayoutProps {
  children: React.ReactNode;
  currentView: View;
  onViewChange: (view: View) => void;
  onNewSession: () => void;
  health: any;
}

export function RootLayout({ 
  children, 
  currentView, 
  onViewChange, 
  onNewSession, 
  health 
}: RootLayoutProps) {
  return (
    <TooltipProvider delayDuration={0}>
      <SidebarProvider defaultOpen={true}>
        <div className="flex h-screen w-full bg-background overflow-hidden">
          <AppSidebar 
            currentView={currentView} 
            onViewChange={onViewChange} 
            onNewSession={onNewSession}
            health={health}
          />
          <SidebarInset className="flex flex-col h-full overflow-hidden bg-background">
            <header className="flex h-14 shrink-0 items-center gap-2 px-4 border-b border-border/50">
              <SidebarTrigger className="-ml-1" />
              <div className="flex items-center gap-2 px-2 text-sm font-medium">
                <span className="text-muted-foreground uppercase tracking-widest text-[10px]">Platform</span>
                <span className="text-border">/</span>
                <span className="capitalize">{currentView}</span>
              </div>
              
              <div className="ml-auto flex items-center gap-4">
                {health && (
                  <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-secondary/50 border border-border/50">
                    <div className={`size-1.5 rounded-full ${health.model_loaded ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                    <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-tight">
                      {health.environment}
                    </span>
                  </div>
                )}
              </div>
            </header>
            <main className="flex-1 overflow-hidden">
              {children}
            </main>
          </SidebarInset>
        </div>
      </SidebarProvider>
    </TooltipProvider>
  );
}
