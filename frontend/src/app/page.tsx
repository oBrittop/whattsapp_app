import { DashboardPanel } from "../components/organisms/DashboardPanel";

export default function Home() {
  return (
    <main className="min-h-screen p-8 flex flex-col items-center">
      <header className="mb-10 text-center">
        <h1 className="text-4xl font-extrabold text-blue-600 dark:text-blue-400 mb-2">
          Gestão de Atendimentos
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Acompanhe as interações do seu Agente de IA com os clientes no WhatsApp.
        </p>
      </header>

      <section className="w-full">
        <DashboardPanel />
      </section>
    </main>
  );
}
