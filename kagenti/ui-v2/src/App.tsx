// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { Routes, Route } from 'react-router-dom';

import { AppLayout } from './components/AppLayout';
import { HomePage } from './pages/HomePage';
import { AgentCatalogPage } from './pages/AgentCatalogPage';
import { AgentDetailPage } from './pages/AgentDetailPage';
import { ToolCatalogPage } from './pages/ToolCatalogPage';
import { ToolDetailPage } from './pages/ToolDetailPage';
import { ObservabilityPage } from './pages/ObservabilityPage';
import { ImportAgentPage } from './pages/ImportAgentPage';
import { ImportToolPage } from './pages/ImportToolPage';
import { AdminPage } from './pages/AdminPage';
import { NotFoundPage } from './pages/NotFoundPage';

function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/agents" element={<AgentCatalogPage />} />
        <Route path="/agents/import" element={<ImportAgentPage />} />
        <Route path="/agents/:namespace/:name" element={<AgentDetailPage />} />
        <Route path="/tools" element={<ToolCatalogPage />} />
        <Route path="/tools/import" element={<ImportToolPage />} />
        <Route path="/tools/:namespace/:name" element={<ToolDetailPage />} />
        <Route path="/observability" element={<ObservabilityPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppLayout>
  );
}

export default App;
