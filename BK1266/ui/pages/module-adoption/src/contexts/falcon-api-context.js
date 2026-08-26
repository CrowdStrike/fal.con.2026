import FalconApi from '@crowdstrike/foundry-js';
import { createContext, useEffect, useMemo, useState } from 'react';

const FalconApiContext = createContext(null);

function useFalconApiContext() {
  const [isInitialized, setIsInitialized] = useState(false);
  const falcon = useMemo(() => new FalconApi(), []);
  const navigation = useMemo(() => falcon.isConnected ? falcon.navigation : undefined, [falcon.isConnected]);

  useEffect(() => {
    (async () => {
      await falcon.connect();

      setIsInitialized(true);
    })();
  }, []);

  return { falcon, navigation, isInitialized };
}

export { useFalconApiContext, FalconApiContext };