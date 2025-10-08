import type {
  BuildingInfoResponse,
  BuildingQueryPayload,
  Coordinates,
} from '../types/building';

/**
 * When the React app requests /api/v1/building/info during npm run dev, Vite catches the path, opens a matching request to http://localhost:8081/api/v1/building/info, and
 * streams the response back, eliminating CORS issues and keeping cookies/headers consistent.
 * The changeOrigin flag makes the proxied request present localhost:8081 as its origin host, which some backends require when validating host headers.
 */
const DEFAULT_API_BASE_URL = '/api/v1';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL;

const fileToBase64 = (file: File): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result !== 'string') {
        reject(new Error('Не удалось преобразовать файл в base64'));
        return;
      }
      resolve(reader.result);
    };
    reader.onerror = () => {
      reject(new Error('Ошибка чтения файла изображения'));
    };
    reader.readAsDataURL(file);
  });

const sanitizeCoordinates = (coordinates?: Coordinates): Coordinates | undefined => {
  if (!coordinates) {
    return undefined;
  }
  return {
    lat: Number(coordinates.lat),
    lon: Number(coordinates.lon),
  };
};

export const buildingService = {
  async searchBuilding(payload: BuildingQueryPayload): Promise<BuildingInfoResponse> {
    const { address, coordinates, photo } = payload;
    const body: Record<string, unknown> = {};

    if (address?.trim()) {
      body.address = address.trim();
    }

    const normalizedCoordinates = sanitizeCoordinates(coordinates);
    if (normalizedCoordinates) {
      body.coordinates = normalizedCoordinates;
    }

    if (photo) {
      body.image_base64 = await fileToBase64(photo);
    }

    if (!body.address && !body.coordinates) {
      throw new Error('Необходимо указать адрес или координаты для поиска здания');
    }

    const response = await fetch(`${API_BASE_URL}/building/info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || 'Ошибка запроса к backend');
    }

    const data = (await response.json()) as BuildingInfoResponse;
    return data;
  },
};
