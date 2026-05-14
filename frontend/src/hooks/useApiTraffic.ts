import { useSyncExternalStore } from "react";

import { getApiTrafficEntries, subscribeApiTraffic } from "../api/traffic";

export function useApiTraffic() {
  return useSyncExternalStore(subscribeApiTraffic, getApiTrafficEntries, getApiTrafficEntries);
}

