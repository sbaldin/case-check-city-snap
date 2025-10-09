import { useEffect, useMemo } from 'react';
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';

import type { Coordinates } from '../types/building';

const DEFAULT_CENTER: [number, number] = [55.345, 86.0823]; // Center of the Kemerovo City
const DEFAULT_ZOOM = 12;
const LOCATION_ZOOM = 15;

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

interface MapCenterUpdaterProps {
  center: [number, number];
}

const MapCenterUpdater = ({ center }: MapCenterUpdaterProps) => {
  const map = useMap();

  useEffect(() => {
    map.setView(center);
  }, [map, center]);

  return null;
};

const MapPreview = ({ coordinates }: MapPreviewProps) => {
  const hasCoordinates = Boolean(coordinates);
  const center: [number, number] = useMemo(
    () => (hasCoordinates ? [coordinates!.lat, coordinates!.lon] : DEFAULT_CENTER),
    [hasCoordinates, coordinates?.lat, coordinates?.lon],
  );
  const zoom = hasCoordinates ? LOCATION_ZOOM : DEFAULT_ZOOM;

  return (
    <div className="card shadow-sm mt-4">
      <div className="card-body">
        <h6 className="mb-3">Карта</h6>
        <div className="map-wrapper">
          <MapContainer center={center} zoom={zoom} style={{ height: 320 }} scrollWheelZoom>
            <MapCenterUpdater center={center} />
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {hasCoordinates && (
              <Marker position={center} icon={markerIcon}>
                <Popup>
                  {center[0].toFixed(5)}, {center[1].toFixed(5)}
                </Popup>
              </Marker>
            )}
          </MapContainer>
        </div>
      </div>
    </div>
  );
};

export default MapPreview;
