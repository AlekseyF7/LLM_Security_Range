"use client";

import { ReactNode } from "react";
import { AppStateProvider } from "./AppState";
import { TopNav } from "./TopNav";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <AppStateProvider>
      <TopNav />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 lg:px-6">{children}</main>
    </AppStateProvider>
  );
}
