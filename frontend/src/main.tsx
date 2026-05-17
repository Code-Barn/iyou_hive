import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from './App';
import './index.css';

const queryClient = new QueryClient();

document.addEventListener('DOMContentLoaded', () => {
  const rootElement = document.getElementById('timeline-app');
  if (rootElement) {
    ReactDOM.createRoot(rootElement).render(
      <React.StrictMode>
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      </React.StrictMode>
    );
  } else {
    console.error('Root element #timeline-app not found!');
  }
});
