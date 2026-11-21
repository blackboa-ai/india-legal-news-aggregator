import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  api,
  clearStoredTokens,
  getStoredToken,
  handleUrlTokenHandoff,
  setStoredTokens,
} from '../api/client';
import { User } from '../types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Check for ?token= URL handoff on initial app mount
  useEffect(() => {
    let isMounted = true;

    const initializeAuth = async () => {
      if (isMounted) setIsLoading(true);
      try {
        const handoffToken = handleUrlTokenHandoff();
        const currentToken = handoffToken || getStoredToken();

        if (currentToken) {
          if (isMounted) setToken(currentToken);
          const userProfile = await api.auth.me();
          if (isMounted) setUser(userProfile);
        }
      } catch (err) {
        console.warn('Initial session fetch failed:', err);
        clearStoredTokens();
        if (isMounted) {
          setToken(null);
          setUser(null);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    initializeAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.auth.login({ email, password });
      setStoredTokens(response.access_token, response.refresh_token);
      setToken(response.access_token);
      setUser(response.user);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, fullName?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.auth.register({ email, password, full_name: fullName });
      setStoredTokens(response.access_token, response.refresh_token);
      setToken(response.access_token);
      setUser(response.user);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Registration failed';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithGoogle = async (idToken: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.auth.google(idToken);
      setStoredTokens(response.access_token, response.refresh_token);
      setToken(response.access_token);
      setUser(response.user);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Google authentication failed';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    clearStoredTokens();
    setToken(null);
    setUser(null);
    setIsLoading(false);
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        error,
        login,
        register,
        loginWithGoogle,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
