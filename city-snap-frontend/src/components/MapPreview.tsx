import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet';
import L from 'leaflet';

import type { Coordinates } from '../types/building';

const DEFAULT_CENTER: [number, number] = [59.9386, 30.3141];

const markerIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

interface MapPreviewProps {
  coordinates?: Coordinates | null;
}

const MapPreview = ({ coordinates }: MapPreviewProps) => {
  const hasCoordinates = Boolean(coordinates);
  const center: [number, number] = hasCoordinates
    ? [coordinates!.lat, coordinates!.lon]
    : DEFAULT_CENTER;

  return (
    <div className="card shadow-sm mt-4">
      <div className="card-body">
        <h6 className="mb-3">Карта</h6>
        <div className="map-wrapper">
          <MapContainer center={center} zoom={hasCoordinates ? 17 : 12} style={{ height: 320 }} scrollWheelZoom>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {hasCoordinates && (
              <Marker position={center} icon={markerIcon}>
                <Popup>
                  {coordinates!.lat.toFixed(5)}, {coordinates!.lon.toFixed(5)}
                </Popup>
              </Marker>
            )}
          </MapContainer>
        </div>
        {!hasCoordinates && (
          <p className="mt-3 mb-0 text-muted">
            Укажите адрес или координаты, чтобы увидеть расположение здания на карте.
          </p>
        )}
      </div>
    </div>
  );
};

export default MapPreview;
