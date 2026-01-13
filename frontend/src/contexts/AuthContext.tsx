import { createContext, useState, useEffect, useContext, ReactNode } from 'react';
import { jwtDecode } from 'jwt-decode';
import { useNavigate } from 'react-router-dom';

// User interface matching JWT payload
interface User {
  sub: string; // user ID
  email: string;
  full_name: string;
  iat: number;
  exp: number;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
  forceLogout: () => void; // Force logout and clear all data
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  // On initial app load, check for an existing token
  useEffect(() => {
    console.log("AuthContext: App loading, checking for token...");
    
    const storedToken = localStorage.getItem('auth_token');
    
    if (storedToken) {
      try {
        const decodedUser: User = jwtDecode(storedToken);
        
        // Check if token is expired
        const currentTime = Date.now() / 1000;
        if (decodedUser.exp > currentTime) {
          console.log("AuthContext: Found valid token, decoded user:", decodedUser);
          setUser(decodedUser);
          setToken(storedToken);
        } else {
          console.log("AuthContext: Token expired, removing from storage");
          localStorage.removeItem('auth_token');
          setUser(null);
          setToken(null);
        }
      } catch (error) {
        console.error("AuthContext: Invalid token on initial load.", error);
        localStorage.removeItem('auth_token');
        setUser(null);
        setToken(null);
      }
    } else {
      console.log("AuthContext: No token found on initial load.");
      setUser(null);
      setToken(null);
    }
    
    setIsLoading(false);
  }, []);

  const login = (newToken: string) => {
    console.log("AuthContext: login function called");
    try {
      const decodedUser: User = jwtDecode(newToken);
      console.log("AuthContext: Decoded user on login:", decodedUser);
      
      // Validate token expiration
      const currentTime = Date.now() / 1000;
      if (decodedUser.exp <= currentTime) {
        throw new Error("Token is expired");
      }
      
      // Store token and update state
      localStorage.setItem('auth_token', newToken);
      setUser(decodedUser);
      setToken(newToken);
      
      // Navigate to dashboard after successful login
      navigate('/dashboard', { replace: true });
      
    } catch (error) {
      console.error("AuthContext: Failed to decode token on login.", error);
      // Clean up any invalid state
      localStorage.removeItem('auth_token');
      setUser(null);
      setToken(null);
      throw new Error("Invalid token");
    }
  };

  const forceLogout = () => {
    console.log("AuthContext: force logout called - clearing all auth data");
    localStorage.clear(); // Clear all localStorage
    sessionStorage.clear(); // Clear all sessionStorage
    setUser(null);
    setToken(null);
    navigate('/');
  };

  const logout = () => {
    console.log("AuthContext: logout function called.");
    localStorage.removeItem('auth_token');
    sessionStorage.removeItem('app_initialized'); // Also clear session flag
    setUser(null);
    setToken(null);
    navigate('/');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, forceLogout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
