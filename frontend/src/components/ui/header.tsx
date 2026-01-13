import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Navigation } from './navigation';
import { Button } from './button';
import { Input } from './input';
import enbdLogo from '@/assets/enbd.jpeg';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './dropdown-menu';
import { Search, LogOut, User, ChevronDown } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';


export function Header() {
  const navigate = useNavigate();
  const { user, logout, forceLogout } = useAuth();

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-sm">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo and Brand */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/') }>
          <img 
            src={enbdLogo} 
            alt="ENBD" 
            className="w-24 h-12 sm:w-28 sm:h-14 object-contain"
          />
        </div>

        {/* Navigation */}
        <div className="hidden lg:flex">
          <Navigation />
        </div>

        {/* Search and Actions */}
        <div className="flex items-center gap-3">
          {/* Show search only for authenticated users */}
          {user && (
            <div className="relative hidden md:block">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search documents..."
                className="pl-10 w-64"
              />
            </div>
          )}
          
          {user ? (
            // Authenticated user actions - User dropdown menu
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button 
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <User className="w-4 h-4" />
                  <span className="hidden sm:inline">{user.full_name}</span>
                  <ChevronDown className="w-3 h-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{user.full_name}</p>
                    <p className="text-xs leading-none text-muted-foreground">{user.email}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => logout()}>
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenuItem>
                <DropdownMenuItem 
                  onClick={() => forceLogout()} 
                  className="text-red-600 focus:text-red-600"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Clear all data & logout</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            // Guest user actions
            <>
              <Button 
                variant="ghost" 
                onClick={() => navigate('/signin')}
                className="hidden sm:flex"
              >
                Sign In
              </Button>
              
              <Button 
                onClick={() => navigate('/signup')}
                className="bg-gradient-primary hover:shadow-lg"
              >
                Sign Up
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}