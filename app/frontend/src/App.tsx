import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import AppLayout from '@/components/AppLayout';
import LoginPage from '@/pages/LoginPage';
import AuthCallback from './pages/AuthCallback';
import AuthError from './pages/AuthError';
import Index from './pages/Index';
import SuppliersPage from './pages/SuppliersPage';
import BuyersPage from './pages/BuyersPage';
import CategoriesPage from './pages/CategoriesPage';
import OffersPage from './pages/OffersPage';
import DistributionPage from './pages/DistributionPage';
import NegotiationsPage from './pages/NegotiationsPage';
import NegotiationNumbersPage from './pages/NegotiationNumbersPage';
import HistoryPage from './pages/HistoryPage';
import WhatsAppSettingsPage from './pages/WhatsAppSettingsPage';
import WhatsAppConversationsPage from './pages/WhatsAppConversationsPage';
import AdminPhonesPage from './pages/AdminPhonesPage';
import VehicleDossiersPage from './pages/VehicleDossiersPage';
import BuyerVehicleDossiersPage from './pages/BuyerVehicleDossiersPage';
import PlateLookupPage from './pages/PlateLookupPage';
import FipeLookupPage from './pages/FipeLookupPage';

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    client.auth
      .me()
      .then((res) => {
        if (res?.data) {
          setAuthenticated(true);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!authenticated) {
    return <Navigate to="/login" replace />;
  }

  return <AppLayout>{children}</AppLayout>;
}

const AppRoutes = () => (
  <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/auth/callback" element={<AuthCallback />} />
    <Route path="/auth/error" element={<AuthError />} />
    <Route
      path="/"
      element={
        <ProtectedRoute>
          <Index />
        </ProtectedRoute>
      }
    />
    <Route
      path="/suppliers"
      element={
        <ProtectedRoute>
          <SuppliersPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/buyers"
      element={
        <ProtectedRoute>
          <BuyersPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/categories"
      element={
        <ProtectedRoute>
          <CategoriesPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/offers"
      element={
        <ProtectedRoute>
          <OffersPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/distribution"
      element={
        <ProtectedRoute>
          <DistributionPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/negotiations"
      element={
        <ProtectedRoute>
          <NegotiationsPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/negotiation-numbers"
      element={
        <ProtectedRoute>
          <NegotiationNumbersPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/history"
      element={
        <ProtectedRoute>
          <HistoryPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/whatsapp-settings"
      element={
        <ProtectedRoute>
          <WhatsAppSettingsPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/whatsapp-conversations"
      element={
        <ProtectedRoute>
          <WhatsAppConversationsPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/admin-phones"
      element={
        <ProtectedRoute>
          <AdminPhonesPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/vehicle-dossiers"
      element={
        <ProtectedRoute>
          <VehicleDossiersPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/my-vehicles"
      element={
        <ProtectedRoute>
          <BuyerVehicleDossiersPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/plate-lookup"
      element={
        <ProtectedRoute>
          <PlateLookupPage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/fipe-lookup"
      element={
        <ProtectedRoute>
          <FipeLookupPage />
        </ProtectedRoute>
      }
    />
  </Routes>
);

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
export { AppRoutes };
