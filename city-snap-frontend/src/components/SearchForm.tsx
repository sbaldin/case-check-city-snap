import { useState } from 'react';
import type { FormEvent } from 'react';

import type { BuildingQueryPayload } from '../types/building';

interface SearchFormProps {
  onSubmit: (payload: BuildingQueryPayload) => Promise<void> | void;
  isLoading: boolean;
}

const SearchForm = ({ onSubmit, isLoading }: SearchFormProps) => {
  const [address, setAddress] = useState('');
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [photo, setPhoto] = useState<File | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);

    const trimmedAddress = address.trim();
    const hasAddress = Boolean(trimmedAddress);
    const hasCoordinates = lat.trim() !== '' && lon.trim() !== '';

    if (!hasAddress && !hasCoordinates) {
      setFormError('Укажите адрес или заполните координаты для поиска.');
      return;
    }

    let coordinates;
    if (hasCoordinates) {
      const parsedLat = Number(lat);
      const parsedLon = Number(lon);
      if (Number.isNaN(parsedLat) || Number.isNaN(parsedLon)) {
        setFormError('Координаты должны быть числом.');
        return;
      }
      coordinates = { lat: parsedLat, lon: parsedLon };
    }

    await onSubmit({
      address: hasAddress ? trimmedAddress : undefined,
      coordinates,
      photo,
    });
  };

  return (
    <div className="card shadow-sm p-4">
      <form className="row g-3 align-items-center" onSubmit={handleSubmit} noValidate>
        <div className="col-lg-8">
          <label className="form-label visually-hidden" htmlFor="address-input">
            Адрес
          </label>
          <input
            id="address-input"
            type="text"
            className="form-control"
            placeholder="Улица, номер дома, город, почтовый индекс"
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            disabled={isLoading}
          />
        </div>
        <div className="col-lg-4 d-flex">
          <label className="form-label visually-hidden" htmlFor="photo-input">
            Фото здания
          </label>
          <input
            id="photo-input"
            type="file"
            className="form-control"
            accept="image/*"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              setPhoto(file);
            }}
            disabled={isLoading}
          />
        </div>
        <div className="col-12">
          <button
            type="button"
            className="btn btn-link p-0 text-decoration-none"
            onClick={() => setAdvancedOpen((prev) => !prev)}
          >
            {advancedOpen ? 'Скрыть координаты' : 'Указать координаты вручную'}
          </button>
        </div>
        {advancedOpen && (
          <div className="col-12">
            <div className="row g-3">
              <div className="col-md-6">
                <label className="form-label" htmlFor="latitude-input">
                  Широта (lat)
                </label>
                <input
                  id="latitude-input"
                  type="text"
                  className="form-control"
                  placeholder="59.935"
                  value={lat}
                  onChange={(event) => setLat(event.target.value)}
                  disabled={isLoading}
                />
              </div>
              <div className="col-md-6">
                <label className="form-label" htmlFor="longitude-input">
                  Долгота (lon)
                </label>
                <input
                  id="longitude-input"
                  type="text"
                  className="form-control"
                  placeholder="30.325"
                  value={lon}
                  onChange={(event) => setLon(event.target.value)}
                  disabled={isLoading}
                />
              </div>
            </div>
          </div>
        )}
        {formError && (
          <div className="col-12">
            <div className="alert alert-warning" role="alert">
              {formError}
            </div>
          </div>
        )}
        <div className="col-12">
          <button type="submit" className="btn btn-primary w-100" disabled={isLoading}>
            {isLoading ? 'Запрашиваем данные…' : 'Найти информацию о здании'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default SearchForm;
