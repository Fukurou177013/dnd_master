import { Navigate, Route, Routes } from "react-router-dom";

import { AuthPage } from "./AuthPage";
import { useAuth } from "./AuthContext";
import { CampaignPage } from "./CampaignPage";
import { CampaignChatPage } from "./CampaignChatPage";
import { CharacterPage } from "./CharacterPage";
import { Layout } from "./Layout";

export function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <span className="spinner" aria-hidden="true" />
        <p>Загружаем сессию...</p>
      </div>
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/characters" replace /> : <AuthPage />}
      />
      <Route element={user ? <Layout /> : <Navigate to="/login" replace />}>
        <Route path="/characters" element={<CharacterPage />} />
        <Route path="/campaigns" element={<CampaignPage />} />
        <Route path="/campaigns/:campaignId" element={<CampaignChatPage />} />
      </Route>
      <Route
        path="*"
        element={<Navigate to={user ? "/characters" : "/login"} replace />}
      />
    </Routes>
  );
}
