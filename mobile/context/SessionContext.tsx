import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

interface SessionPhoto {
  base64: string;
  uri: string;
}

interface SessionContextValue {
  photo: SessionPhoto | null;
  setPhoto: (photo: SessionPhoto | null) => void;
  clearPhoto: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [photo, setPhotoState] = useState<SessionPhoto | null>(null);

  const setPhoto = useCallback((next: SessionPhoto | null) => {
    setPhotoState(next);
  }, []);

  const clearPhoto = useCallback(() => setPhotoState(null), []);

  const value = useMemo(
    () => ({ photo, setPhoto, clearPhoto }),
    [photo, setPhoto, clearPhoto],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error('useSession must be used within SessionProvider');
  }
  return ctx;
}
