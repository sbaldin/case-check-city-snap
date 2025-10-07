import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import BuildingInfoCard from '../components/BuildingInfoCard';
import ErrorMessage from '../components/ErrorMessage';
import LoadingSpinner from '../components/LoadingSpinner';
import MapPreview from '../components/MapPreview';
import SearchForm from '../components/SearchForm';
import { useBuildingQuery } from '../hooks/useBuildingQuery';
import type { BuildingInfo, BuildingQueryPayload } from '../types/building';

const SearchPage = () => {
  const navigate = useNavigate();
  const [building, setBuilding] = useState<BuildingInfo | null>(null);
  const [sources, setSources] = useState<string[]>([]);
  const buildingMutation = useBuildingQuery();

  const handleSubmit = useCallback(
    async (payload: BuildingQueryPayload) => {
      try {
        const result = await buildingMutation.mutateAsync(payload);
        setBuilding(result.building ?? null);
        setSources(result.source ?? []);
      } catch (err) {
        console.error('Ошибка получения данных о здании', err);
        setBuilding(null);
        setSources([]);
      }
    },
    [buildingMutation],
  );

  const handleOpenDetails = () => {
    if (!building) {
      return;
    }

    navigate('/building', {
      state: {
        building,
        sources,
      },
    });
  };

  return (
    <main className="container my-5">
      <SearchForm onSubmit={handleSubmit} isLoading={buildingMutation.isPending} />

      {buildingMutation.isPending && <LoadingSpinner />}

      {buildingMutation.isError && buildingMutation.error && (
        <ErrorMessage message={buildingMutation.error.message} />
      )}

      <BuildingInfoCard building={building} sources={sources} />
      <MapPreview coordinates={building?.location ?? null} />

      {building && (
        <div className="mt-4 d-flex justify-content-end">
          <button type="button" className="btn btn-outline-primary" onClick={handleOpenDetails}>
            Открыть подробности
          </button>
        </div>
      )}
    </main>
  );
};

export default SearchPage;
