'use client';

import React, { useEffect, useState } from 'react';

/**
 * Interface que define o contrato de dados dos eventos 
 * recebidos em tempo real pelo WebSocket.
 */
interface AIEvent {
  type: 'NEW_APPOINTMENT' | 'CANCELLATION';
  client: string;
  status: string;
  timestamp: string;
}

/**
 * Organismo DashboardPanel.
 * 
 * Componente responsável por estabelecer uma conexão WebSocket 
 * com o backend FastAPI, gerenciar o estado da conexão e renderizar 
 * reativamente as atualizações do agente de IA.
 */
export const DashboardPanel: React.FC = () => {
  const [events, setEvents] = useState<AIEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/dashboard';
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);

    ws.onmessage = (event) => {
      const data: AIEvent = JSON.parse(event.data);
      setEvents((prev) => [data, ...prev]);
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div className="w-full max-w-4xl mx-auto p-6 bg-white dark:bg-gray-900 rounded-xl shadow-lg">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-white">
          Monitoramento do Agente de IA
        </h2>
        <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
          isConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
        }`}>
          {isConnected ? 'Online' : 'Desconectado'}
        </span>
      </div>

      <div className="space-y-4">
        {events.length === 0 ? (
          <div className="text-center py-10 text-gray-500 dark:text-gray-400">
            Aguardando interações dos clientes no WhatsApp...
          </div>
        ) : (
          events.map((evt, idx) => (
            <div 
              key={idx} 
              className={`p-4 rounded-lg border-l-4 shadow-sm flex flex-col transition-all duration-300 animate-in fade-in slide-in-from-top-4 ${
                evt.type === 'NEW_APPOINTMENT' 
                  ? 'bg-blue-50 border-blue-500 dark:bg-blue-900/20' 
                  : 'bg-red-50 border-red-500 dark:bg-red-900/20'
              }`}
            >
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-semibold text-gray-900 dark:text-gray-100">
                    Cliente: {evt.client}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                    Ação: <span className="font-medium">{evt.type === 'NEW_APPOINTMENT' ? 'Agendamento Confirmado' : 'Cancelamento'}</span>
                  </p>
                </div>
                <span className="text-xs text-gray-400">
                  {new Date(evt.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
