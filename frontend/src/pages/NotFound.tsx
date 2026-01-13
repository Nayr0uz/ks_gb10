import React, { useEffect } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { AlertTriangle, Home } from 'lucide-react';
import { Header } from '@/components/ui/header'; // Optional: for a consistent look

export default function NotFound() {
  const location = useLocation();

  useEffect(() => {
    // This logging is good for development and can be kept.
    console.error(
      `404 Not Found: User attempted to access non-existent route: ${location.pathname}`
    );
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-background">
      {/* Optional: Include the header for a more integrated feel */}
      <Header />
      
      <div className="flex items-center justify-center py-24">
        <Card className="max-w-md w-full text-center p-8 shadow-lg">
          <CardContent>
            <AlertTriangle className="w-16 h-16 text-destructive mx-auto mb-6" />
            <h1 className="text-5xl font-bold mb-2">404</h1>
            <h2 className="text-2xl font-semibold text-foreground mb-4">Page Not Found</h2>
            <p className="text-muted-foreground mb-8">
              Sorry, the page you are looking for does not exist or has been moved.
            </p>
            <Button asChild className="bg-gradient-primary">
              <Link to="/documents">
                <Home className="w-4 h-4 mr-2" />
                Back to Knowledge Base
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};