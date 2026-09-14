import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';

import { LanguageProvider } from './context/LanguageContext.jsx';
import { AuthProvider } from './context/AuthContext.jsx';
import { ToastProvider } from './context/ToastContext.jsx';
import { ProblemsProvider } from './context/ProblemsContext.jsx';
import { ApplicationsProvider } from './context/ApplicationsContext.jsx';

import './styles/theme.css';
import './styles/layout.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <LanguageProvider>
        <ToastProvider>
          <AuthProvider>
            <ProblemsProvider>
              <ApplicationsProvider>
                <App />
              </ApplicationsProvider>
            </ProblemsProvider>
          </AuthProvider>
        </ToastProvider>
      </LanguageProvider>
    </BrowserRouter>
  </StrictMode>,
);
