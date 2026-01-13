import React from 'react';
import { Card } from './card';
import { Users, BookOpen, Award, Clock } from 'lucide-react';

const stats = [
  {
    icon: Users,
    value: '10,000+',
    label: 'Active Employees',
    description: 'Serving customers faster'
  },
  {
    icon: BookOpen,
    value: '50,000+',
    label: 'Documents Processed',
    description: 'Policy, product and operational documents'
  },
  {
    icon: Award,
    value: '95%',
    label: 'Answer Accuracy',
    description: 'Precision on sourced responses'
  },
  {
    icon: Clock,
    value: '75%',
    label: 'Avg. Time Saved',
    description: 'Per lookup for staff'
  }
];

export function StatsSection() {
  return (
    <section className="py-16 bg-muted/30">
      <div className="container mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">
            Trusted by knowledge Sphere teams and branches
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Operational teams across the bank use the Smart Assistant to reduce response times, ensure compliance, and improve customer service consistency.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat, index) => (
            <Card 
              key={index}
              className="p-6 text-center interactive-card border-0 shadow-soft hover:shadow-medium"
            >
              <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-gradient-primary flex items-center justify-center">
                <stat.icon className="w-6 h-6 text-primary-foreground" />
              </div>
              <div className="text-2xl font-bold text-primary mb-1">
                {stat.value}
              </div>
              <div className="font-medium text-foreground mb-1">
                {stat.label}
              </div>
              <div className="text-sm text-muted-foreground">
                {stat.description}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}