import { useQuery } from '@tanstack/react-query';
import { adminApi } from '@/lib/api';

const NORMAL_INTERVAL = 120_000;
const EMERGENCY_INTERVAL = 30_000;

/**
 * Returns a refetch interval that shortens when emergency mode is active.
 */
export function useRefetchInterval(): number {
  const { data } = useQuery({
    queryKey: ['admin', 'emergency-mode'],
    queryFn: () => adminApi.getEmergencyMode(),
    refetchInterval: EMERGENCY_INTERVAL,
    staleTime: EMERGENCY_INTERVAL,
  });
  return data?.emergency_mode ? EMERGENCY_INTERVAL : NORMAL_INTERVAL;
}
