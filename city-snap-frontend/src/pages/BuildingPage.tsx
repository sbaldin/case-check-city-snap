import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import BuildingInfoCard from '../components/BuildingInfoCard';
import MapPreview from '../components/MapPreview';
import type { BuildingInfo } from '../types/building';

interface LocationState {
  building?: BuildingInfo | null;
  sources?: string[];
  requestedAddress?: string;
}

const BuildingPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as LocationState | undefined) ?? {};

  useEffect(() => {
    if (!state.building) {
      // при прямом переходе возвращаем пользователя к форме поиска
      navigate('/', { replace: true });
    }
  }, [navigate, state.building]);

  if (!state.building) {
    return null;
  }

  return (
    <main className="container my-5">
      <div className="mb-4">
        <button type="button" className="btn btn-link px-0" onClick={() => navigate(-1)}>
          ← Назад к поиску
        </button>
      </div>

      <BuildingInfoCard
        building={state.building}
        sources={state.sources ?? []}
        fallbackTitle={state.requestedAddress}
      />
      <MapPreview coordinates={state.building.location ?? null} />
    </main>
  );
};

export default BuildingPage;
