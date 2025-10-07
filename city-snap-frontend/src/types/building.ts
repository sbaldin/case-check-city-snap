export interface Coordinates {
  lat: number;
  lon: number;
}

export interface BuildingInfo {
  name?: string | null;
  year_built?: number | null;
  architect?: string | null;
  history?: string | null;
  location?: Coordinates | null;
  image_path?: string | null;
}

export interface BuildingInfoResponse {
  building: BuildingInfo;
  source: string[];
}

export interface BuildingQueryPayload {
  address?: string;
  coordinates?: Coordinates;
  photo?: File | null;
}

export interface BuildingQueryVariables {
  address?: string;
  coordinates?: Coordinates;
  photo?: File | null;
}
