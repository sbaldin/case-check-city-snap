import { Navigate, Route, Routes } from 'react-router-dom';

import BuildingPage from '../pages/BuildingPage';
import SearchPage from '../pages/SearchPage';

const AppRouter = () => (
  <Routes>
    <Route path="/" element={<SearchPage />} />
    <Route path="/building" element={<BuildingPage />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
);

export default AppRouter;
