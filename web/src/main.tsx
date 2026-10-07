import { StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth, useUser } from "./auth";
import { Loading } from "./components";
import { AwaitingApproval, Register, SignIn } from "./pages/Access";
import { Approvals, Prices } from "./pages/Admin";
import { Agreements } from "./pages/Agreements";
import { DetailsStep, PhotoStep, SellStep } from "./pages/Capture";
import { BuyerDashboard, SellerDashboard } from "./pages/Dashboard";
import { Impact } from "./pages/Impact";
import { InvoicePage } from "./pages/Invoice";
import { Market, MyLots, WalletPage } from "./pages/Lists";
import { LotPage } from "./pages/LotPage";
import { More } from "./pages/More";
import { Anchors, Jobs, PickupRoutes, Transporters } from "./pages/Operations";
import { Requests } from "./pages/Requests";
import { Verify } from "./pages/Verify";
import { Shell } from "./Shell";
import "./styles.css";

function RequireApproved({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Navigate to="/signin" replace />;
  if (user.kyc_status !== "approved")
    return <AwaitingApproval rejected={user.kyc_status === "rejected"} note={user.kyc_note} />;
  return children;
}

function SignedOutOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  return user ? <Navigate to="/" replace /> : children;
}

/** Everyone lands where their work is: admins on the approvals queue, traders on their dashboard. */
function Home() {
  const { role } = useUser();
  if (role === "admin") return <Navigate to="/admin" replace />;
  if (role === "buyer") return <BuyerDashboard />;
  return <SellerDashboard />;
}

function App() {
  return (
    <Routes>
      <Route path="/signin" element={<SignedOutOnly><SignIn /></SignedOutOnly>} />
      <Route path="/register" element={<SignedOutOnly><Register /></SignedOutOnly>} />
      <Route path="/certificates/:id/verify" element={<Verify />} />
      <Route element={<RequireApproved><Shell /></RequireApproved>}>
        <Route index element={<Home />} />
        <Route path="mine" element={<MyLots />} />
        <Route path="market" element={<Market />} />
        <Route path="wallet" element={<WalletPage />} />
        <Route path="lots/new" element={<PhotoStep />} />
        <Route path="lots/:id" element={<LotPage />} />
        <Route path="lots/:id/details" element={<DetailsStep />} />
        <Route path="lots/:id/sell" element={<SellStep />} />
        <Route path="lots/:id/invoice" element={<InvoicePage />} />
        <Route path="more" element={<More />} />
        <Route path="requests" element={<Requests />} />
        <Route path="agreements" element={<Agreements />} />
        <Route path="impact" element={<Impact />} />
        <Route path="admin" element={<Approvals />} />
        <Route path="admin/prices" element={<Prices />} />
        <Route path="admin/transporters" element={<Transporters />} />
        <Route path="admin/routes" element={<PickupRoutes />} />
        <Route path="admin/anchors" element={<Anchors />} />
        <Route path="admin/jobs" element={<Jobs />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
