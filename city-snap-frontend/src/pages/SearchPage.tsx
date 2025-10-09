import {useCallback, useState} from 'react';
import {useNavigate} from 'react-router-dom';

import BuildingInfoCard from '../components/BuildingInfoCard';
import ErrorMessage from '../components/ErrorMessage';
import LoadingSpinner from '../components/LoadingSpinner';
import MapPreview from '../components/MapPreview';
import SearchForm from '../components/SearchForm';
import {buildingService} from '../api/buildingService';
import type {BuildingInfo, BuildingQueryPayload} from '../types/building';

const SearchPage = () => {
    const navigate = useNavigate();
    const [building, setBuilding] = useState<BuildingInfo | null>(null);
    const [sources, setSources] = useState<string[]>([]);
    const [requestedAddress, setRequestedAddress] = useState<string | undefined>(undefined);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = useCallback(
        async (payload: BuildingQueryPayload) => {
            setIsLoading(true);
            setError(null);
            setRequestedAddress(payload.address || undefined);
            try {
                const result = await buildingService.searchBuilding(payload);
                setBuilding(result.building ?? null);
                setSources(result.source ?? []);
            } catch (err) {
                console.error('Ошибка получения данных о здании', err);
                setBuilding(null);
                setSources([]);
                if (err instanceof Error) {
                    setError(err.message);
                } else {
                    setError('Ошибка запроса к backend');
                }
            } finally {
                setIsLoading(false);
            }
        },
        [],
    );

    const handleOpenDetails = () => {
        if (!building) {
            return;
        }

        navigate('/building', {
            state: {
                building,
                sources,
                requestedAddress,
            },
        });
    };

    return (
        <main className="container my-5">
            <SearchForm onSubmit={handleSubmit} isLoading={isLoading}/>

            {isLoading && <LoadingSpinner/>}

            {error && <ErrorMessage message={error}/>}

            <BuildingInfoCard building={building} sources={sources} fallbackTitle={requestedAddress}/>
            {building && (
                <div className="mt-4 d-flex justify-content-end">
                    <button type="button" className="btn btn-outline-primary" onClick={handleOpenDetails}>
                        Открыть подробности
                    </button>
                </div>
            )}
            <MapPreview coordinates={building?.location ?? null}/>
        </main>
    );
};

export default SearchPage;
