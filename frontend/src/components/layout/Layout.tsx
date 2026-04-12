import { ReactNode } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';
import SupportChatWidget from '../support/SupportChatWidget';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <div className="bg-mesh" />
      <div className="app-shell">
        <Sidebar />
        <Header />
        <main className="main-content">
          {children}
        </main>
      </div>
      <SupportChatWidget />
    </>
  );
}
