import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './card';
import { Button } from './button';
import { 
  MessageSquare, 
  FileText,
  ArrowRight,
  Sparkles
} from 'lucide-react';

const features = [
  {
    icon: MessageSquare,
    title: 'AI Chat with Documents',
    description: 'Ask questions about any uploaded document and get instant, accurate answers with citations.',
    benefits: ['Natural language queries', 'Source citations', 'Context-aware responses'],
    gradient: 'from-blue-500 to-cyan-500'
  },
  {
    icon: FileText,
    title: 'Policy & Process Summaries',
    description: 'Automatically generate concise summaries of policies and procedures to help staff find answers faster.',
    benefits: ['Policy summaries', 'Procedure highlights', 'Quick reference points'],
    gradient: 'from-orange-500 to-red-500'
  }
];

export function FeaturesSection() {
  const navigate = useNavigate();
  return (
    <section className="py-20">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent/10 text-accent text-sm font-medium mb-4">
            <Sparkles className="w-4 h-4" />
            Key Capabilities
          </div>
          <h2 className="text-4xl font-bold mb-4">
            Essential Tools for Knowledge Operations
          </h2>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            The knowledge Sphere combines enterprise-level AI with intuitive design to help staff locate policy, product and operational guidance quickly and with audit-ready source references.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {features.map((feature, index) => (
            <Card 
              key={index}
              className="group interactive-card border-0 shadow-soft overflow-hidden relative"
            >
              {/* Gradient background */}
              <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-5 group-hover:opacity-10 transition-opacity duration-300`} />
              
              <CardHeader className="relative">
                <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-4`}>
                  <feature.icon className="w-6 h-6 text-white" />
                </div>
                <CardTitle className="text-xl mb-2">{feature.title}</CardTitle>
                <CardDescription className="text-base">
                  {feature.description}
                </CardDescription>
              </CardHeader>
              
              <CardContent className="relative">
                <ul className="space-y-2 mb-6">
                  {feature.benefits.map((benefit, idx) => (
                    <li key={idx} className="flex items-center gap-2 text-sm text-muted-foreground">
                      <div className="w-1.5 h-1.5 rounded-full bg-accent" />
                      {benefit}
                    </li>
                  ))}
                </ul>
                
                <Button 
                  variant="ghost" 
                  className="group/btn text-primary hover:text-primary hover:bg-primary/10 p-0"
                  onClick={() => navigate('/features')}
                >
                  Explore Feature
                  <ArrowRight className="w-4 h-4 ml-2 group-hover/btn:translate-x-1 transition-transform" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}