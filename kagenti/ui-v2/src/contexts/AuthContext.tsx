// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
} from 'react';
import Keycloak from 'keycloak-js';

// Auth configuration - can be overridden via environment variables
const AUTH_CONFIG = {
  url: import.meta.env.VITE_KEYCLOAK_URL || 'http://keycloak.localtest.me:8080',
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'master',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'kagenti-ui',
};

// Check if auth is enabled (can be disabled for development)
const AUTH_ENABLED = import.meta.env.VITE_ENABLE_AUTH !== 'false';

export interface User {
  username: string;
  email?: string;
  firstName?: string;
  lastName?: string;
  roles: string[];
}

export interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  isEnabled: boolean;
  user: User | null;
  token: string | null;
  login: () => void;
  logout: () => void;
  getToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Create Keycloak instance
const keycloakInstance = new Keycloak({
  url: AUTH_CONFIG.url,
  realm: AUTH_CONFIG.realm,
  clientId: AUTH_CONFIG.clientId,
});

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(AUTH_ENABLED);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);

  // Extract user info from Keycloak token
  const extractUserInfo = useCallback((): User | null => {
    if (!keycloakInstance.tokenParsed) {
      return null;
    }

    const tokenParsed = keycloakInstance.tokenParsed as {
      preferred_username?: string;
      email?: string;
      given_name?: string;
      family_name?: string;
      realm_access?: { roles?: string[] };
      resource_access?: Record<string, { roles?: string[] }>;
    };

    // Get roles from realm and client access
    const realmRoles = tokenParsed.realm_access?.roles || [];
    const clientRoles =
      tokenParsed.resource_access?.[AUTH_CONFIG.clientId]?.roles || [];

    return {
      username: tokenParsed.preferred_username || 'unknown',
      email: tokenParsed.email,
      firstName: tokenParsed.given_name,
      lastName: tokenParsed.family_name,
      roles: [...realmRoles, ...clientRoles],
    };
  }, []);

  // Initialize Keycloak
  useEffect(() => {
    if (!AUTH_ENABLED) {
      // Auth disabled - set mock authenticated state
      setIsAuthenticated(true);
      setUser({
        username: 'admin',
        email: 'admin@example.com',
        roles: ['admin'],
      });
      setIsLoading(false);
      return;
    }

    const initKeycloak = async () => {
      try {
        const authenticated = await keycloakInstance.init({
          onLoad: 'check-sso',
          silentCheckSsoRedirectUri:
            window.location.origin + '/silent-check-sso.html',
          pkceMethod: 'S256',
        });

        setIsAuthenticated(authenticated);

        if (authenticated) {
          setToken(keycloakInstance.token || null);
          setUser(extractUserInfo());
        }
      } catch (error) {
        console.error('Keycloak initialization failed:', error);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    initKeycloak();

    // Set up token refresh
    const refreshInterval = setInterval(() => {
      if (keycloakInstance.authenticated) {
        keycloakInstance
          .updateToken(60) // Refresh if token expires in 60 seconds
          .then((refreshed) => {
            if (refreshed) {
              setToken(keycloakInstance.token || null);
              console.debug('Token refreshed');
            }
          })
          .catch(() => {
            console.warn('Token refresh failed, logging out');
            keycloakInstance.logout();
          });
      }
    }, 30000); // Check every 30 seconds

    return () => {
      clearInterval(refreshInterval);
    };
  }, [extractUserInfo]);

  // Login function
  const login = useCallback(() => {
    if (!AUTH_ENABLED) return;
    keycloakInstance.login();
  }, []);

  // Logout function
  const logout = useCallback(() => {
    if (!AUTH_ENABLED) return;
    keycloakInstance.logout({
      redirectUri: window.location.origin,
    });
  }, []);

  // Get current token (with refresh if needed)
  const getToken = useCallback(async (): Promise<string | null> => {
    if (!AUTH_ENABLED) {
      return 'mock-token-for-development';
    }

    if (!keycloakInstance.authenticated) {
      return null;
    }

    try {
      await keycloakInstance.updateToken(30);
      return keycloakInstance.token || null;
    } catch {
      console.error('Failed to refresh token');
      return null;
    }
  }, []);

  const value = useMemo(
    () => ({
      isAuthenticated,
      isLoading,
      isEnabled: AUTH_ENABLED,
      user,
      token,
      login,
      logout,
      getToken,
    }),
    [isAuthenticated, isLoading, user, token, login, logout, getToken]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Hook to use auth context
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Export for direct access if needed
export { keycloakInstance };
