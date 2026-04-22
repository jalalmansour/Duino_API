import { 
  Sidebar, 
  SidebarContent, 
  SidebarFooter, 
  SidebarGroup, 
  SidebarGroupContent, 
  SidebarGroupLabel, 
  SidebarHeader, 
  SidebarMenu, 
  SidebarMenuButton, 
  SidebarMenuItem 
} from "@/components/ui/sidebar";
import { 
  MessageSquare, 
  Key, 
  Box, 
  Settings, 
  Plus, 
  ExternalLink 
} from "lucide-react";

export type View = 'chat' | 'keys' | 'models' | 'settings';

interface AppSidebarProps {
  currentView: View;
  onViewChange: (view: View) => void;
  onNewSession: () => void;
  health: any;
}

export function AppSidebar({ currentView, onViewChange, onNewSession, health }: AppSidebarProps) {
  const items = [
    { title: "Chat", view: "chat" as View, icon: MessageSquare },
    { title: "Keys", view: "keys" as View, icon: Key },
    { title: "Models", view: "models" as View, icon: Box },
  ];

  return (
    <Sidebar collapsible="icon" className="border-r border-slate bg-void">
      <SidebarHeader className="p-4 border-b border-slate">
        <div className="flex items-center gap-3">
          <div className="size-8 rounded-[4px] bg-bone flex items-center justify-center">
            <span className="text-void font-bold text-lg">D</span>
          </div>
          <div className="flex flex-col truncate group-data-[collapsible=icon]:hidden">
            <span className="font-semibold text-sm text-bone">Duino API</span>
            <span className="text-[10px] text-mist uppercase tracking-widest">
              {health?.model_loaded ? "Model Ready" : "Standby"}
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-mist uppercase tracking-[0.08em] text-[10px] px-4 py-2">System</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    isActive={currentView === item.view}
                    onClick={() => onViewChange(item.view)}
                    tooltip={item.title}
                    className="hover:bg-slate/50 data-[active=true]:bg-slate text-mist data-[active=true]:text-bone rounded-[4px]"
                  >
                    <item.icon className="size-4" />
                    <span className="font-medium">{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel className="text-mist uppercase tracking-[0.08em] text-[10px] px-4 py-2">Operations</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton 
                  onClick={onNewSession} 
                  tooltip="New Session"
                  className="hover:bg-slate/50 text-mist hover:text-bone rounded-[4px]"
                >
                  <Plus className="size-4" />
                  <span className="font-medium">Reset Session</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-4 border-t border-slate">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton 
              onClick={() => onViewChange('settings')} 
              isActive={currentView === 'settings'} 
              tooltip="Settings"
              className="hover:bg-slate/50 data-[active=true]:bg-slate text-mist data-[active=true]:text-bone rounded-[4px]"
            >
              <Settings className="size-4" />
              <span className="font-medium">Settings</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton asChild tooltip="Documentation" className="text-mist hover:text-bone rounded-[4px]">
              <a href="https://github.com/jalalmansour/Duino_API" target="_blank" rel="noreferrer">
                <ExternalLink className="size-4" />
                <span className="font-medium">Archive</span>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
