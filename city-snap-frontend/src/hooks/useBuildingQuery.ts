import { useMutation } from '@tanstack/react-query';

import { buildingService } from '../api/buildingService';
import type { BuildingInfoResponse, BuildingQueryPayload } from '../types/building';

export const useBuildingQuery = () =>
  useMutation<BuildingInfoResponse, Error, BuildingQueryPayload>({
    mutationFn: async (variables) => buildingService.searchBuilding(variables),
  });
