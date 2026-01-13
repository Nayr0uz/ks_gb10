import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from './button';
import { Card } from './card';
import { Upload, Database, Brain, Zap, ArrowRight } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import indexImage from '@/assets/index_image.jpeg';

export function HeroSection() {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <section className="relative py-20 overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-hero opacity-5" />
      
      <div className="container mx-auto px-4 relative">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Hero Content */}
          <div className="space-y-8 animate-fade-in">
            <div className="space-y-4">
              <h1 className="text-4xl lg:text-6xl font-bold leading-tight">
                Your ENBD Smart Assistant
                <span className="block text-gradient-primary">
                  Enterprise Document Q&A
                </span>
              </h1>
              <p className="text-xl text-muted-foreground leading-relaxed">
                Upload and chat with ENBD's knowledge database. Get accurate answers to policy questions, product inquiries, and operational procedures in seconds.
              </p>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4">
              {user ? (
                // Authenticated user - show upload button
                <Button 
                  size="lg" 
                  className="bg-gradient-primary hover:shadow-strong floating-action text-lg px-8 py-6"
                  onClick={() => navigate('/books/add')}
                >
                  <Upload className="w-5 h-5 mr-2" />
                  Upload your document
                </Button>
              ) : (
                // Guest user - show auth buttons
                <>
                  <Button 
                    size="lg" 
                    className="bg-gradient-primary hover:shadow-strong floating-action text-lg px-8 py-6"
                    onClick={() => navigate('/signup')}
                  >
                    Get Started Free
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Button>
                  <Button 
                    size="lg" 
                    variant="outline"
                    className="text-lg px-8 py-6 border-2"
                    onClick={() => navigate('/signin')}
                  >
                    Sign In
                  </Button>
                </>
              )}
            </div>

            {/* Feature Highlights */}
            <div className="grid sm:grid-cols-2 gap-4 pt-8">
              <div className="flex items-center gap-3 text-sm">
                <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center">
                  <Brain className="w-4 h-4 text-accent" />
                </div>
                <span className="text-muted-foreground">AI-powered Q&A for Staff</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                  <Zap className="w-4 h-4 text-primary" />
                </div>
                <span className="text-muted-foreground">Instant policy summaries</span>
              </div>
            </div>
          </div>

          {/* Hero Illustration */}
          <div className="relative animate-bounce-subtle">
            <Card className="p-8 shadow-strong bg-gradient-to-br from-card to-card/50">
              <img 
                src={indexImage}
                alt="Bank staff accessing internal knowledge"
                className="w-full h-auto rounded-lg"
              />
            </Card>
            
            {/* Floating elements */}
            <div className="absolute -top-4 -right-4 w-16 h-16 bg-gradient-accent rounded-full opacity-20 animate-pulse" />
            <div className="absolute -bottom-4 -left-4 w-12 h-12 bg-gradient-primary rounded-full opacity-30 animate-pulse delay-1000" />
          </div>
        </div>
      </div>
    </section>
  );
}