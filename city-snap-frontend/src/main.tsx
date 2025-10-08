import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import App from './App';
import './styles/style.css';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Не удалось найти корневой элемент для инициализации приложения');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
