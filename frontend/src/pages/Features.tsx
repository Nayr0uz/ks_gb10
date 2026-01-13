import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '@/components/ui/header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { 
  MessageSquare, 
  GraduationCap, 
  Presentation, 
  FileText,
  BookOpen,
  Search,
  Target,
  Clock,
  Users,
  Zap,
  Shield,
  Download,
  ArrowRight,
  CheckCircle,
  Star,
  Sparkles
} from 'lucide-react';

const features = [
  {
    icon: MessageSquare,
    title: 'AI Chat with Documents',
    description: 'Allow staff to query internal documents (product sheets, policies, procedures) in natural language and receive precise, sourced answers.',
    gradient: 'from-blue-600 to-sky-500',
    benefits: [
      'Natural language queries for quick access to answers',
      'Document citations to trace policy or product sources',
      'Context-aware responses scoped to your internal documents',
      'Cross-document lookup for consistent service guidance',
      'Fast retrieval that reduces time-to-response'
    ],
    useCases: [
      'Frontline staff answering customer queries accurately',
      'Ops teams locating process steps and SLAs',
      'Product teams validating product specs and pricing',
      'Compliance checks against internal policies'
    ],
    detailedFeatures: [
      {
        title: 'Context-Sensitive Answers',
        description: 'Responses are grounded in the content of your uploaded documents; the assistant will not hallucinate external information.'
      },
      {
        title: 'Source Linking',
        description: 'Every answer includes references to the originating document and location for auditability and compliance.'
      },
      {
        title: 'Session Memory',
        description: 'Maintain context across a session to support follow-up clarifications and multi-step workflows.'
      }
    ]
  }
];

const additionalFeatures = [
  {
    icon: BookOpen,
    title: 'Policy & Product Catalog',
    description: 'Centralized access to verified product documentation, policy manuals, and service guides.'
  },
  {
    icon: Search,
    title: 'Advanced Semantic Search',
    description: 'Find relevant policy clauses and product details across large document sets.'
  },
  {
    icon: Target,
    title: 'Regulatory Compliance',
    description: 'Tools to help surface compliance-relevant passages and evidence for audits.'
  },
  {
    icon: Clock,
    title: 'Workflow Automation',
    description: 'Automate common operational lookups and approvals to speed up resolution times.'
  },
  {
    icon: Users,
    title: 'Team Collaboration',
    description: 'Share insights across teams with source-linked answers and collaborative notes.'
  },
  {
    icon: Shield,
    title: 'Privacy & Security',
    description: 'Enterprise-grade data protection and access controls to meet bank security policies.'
  }
];

export default function Features() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-accent/5">
      <Header />
      
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          {/* Header Section */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-4">
              <Sparkles className="w-4 h-4" />
              Detailed Features
            </div>
            <h1 className="text-4xl md:text-5xl font-bold mb-6">
              Everything You Need to
              <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"> Serve Customers with Confidence</span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto mb-8">
              Discover how the Your knowledge Sphere Assistant empowers frontline and back-office teams to access product, policy and operational documents instantly — improving response times, consistency and compliance.
            </p>
            <Button onClick={() => navigate('/')} variant="outline">
              ← Back to Home
            </Button>
          </div>

          {/* Core Features */}
          <div className="space-y-16 mb-20">
            {features.map((feature, index) => (
              <div key={index} className="relative">
                <Card className="overflow-hidden border-0 shadow-lg">
                  {/* Gradient background */}
                  <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-5`} />
                  
                  <CardContent className="relative p-8 md:p-12">
                    <div className="grid lg:grid-cols-2 gap-12 items-start">
                      {/* Feature Overview */}
                      <div className="space-y-6">
                        <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-6`}>
                          <feature.icon className="w-8 h-8 text-white" />
                        </div>
                        
                        <div>
                          <h2 className="text-3xl font-bold mb-4">{feature.title}</h2>
                          <p className="text-lg text-muted-foreground mb-6">
                            {feature.description}
                          </p>
                        </div>

                        <div>
                          <h3 className="text-lg font-semibold mb-4">Key Benefits</h3>
                          <ul className="space-y-3">
                            {feature.benefits.map((benefit, idx) => (
                              <li key={idx} className="flex items-start gap-3">
                                <CheckCircle className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                                <span>{benefit}</span>
                              </li>
                            ))}
                          </ul>
                        </div>

                        <div className="flex gap-3">
                          <Button 
                            onClick={() => {
                              if (feature.title.includes('Chat')) navigate('/chat');
                              else if (feature.title.includes('Exam')) navigate('/exams');
                              else if (feature.title.includes('Rehearsal')) navigate('/exam');
                              else if (feature.title.includes('Scripts')) navigate('/scripts');
                            }}
                          >
                            Try {feature.title}
                            <ArrowRight className="w-4 h-4 ml-2" />
                          </Button>
                        </div>
                      </div>

                      {/* Detailed Features */}
                      <div className="space-y-8">
                        <div>
                          <h3 className="text-lg font-semibold mb-4">How It Works</h3>
                          <div className="space-y-4">
                            {feature.detailedFeatures.map((detail, idx) => (
                              <Card key={idx} className="p-4 bg-background/50">
                                <h4 className="font-medium mb-2">{detail.title}</h4>
                                <p className="text-sm text-muted-foreground">{detail.description}</p>
                              </Card>
                            ))}
                          </div>
                        </div>

                        <div>
                          <h3 className="text-lg font-semibold mb-4">Use Cases</h3>
                          <div className="grid gap-3">
                            {feature.useCases.map((useCase, idx) => (
                              <div key={idx} className="flex items-center gap-3 p-3 rounded-lg bg-primary/5">
                                <Star className="w-4 h-4 text-primary flex-shrink-0" />
                                <span className="text-sm">{useCase}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            ))}
          </div>

          {/* Additional Features */}
          <div className="mb-16">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold mb-4">Additional Features</h2>
              <p className="text-lg text-muted-foreground">
                More tools to enhance your learning experience
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {additionalFeatures.map((feature, index) => (
                <Card key={index} className="p-6 hover:shadow-lg transition-shadow duration-200">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center flex-shrink-0">
                      <feature.icon className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h3 className="font-semibold mb-2">{feature.title}</h3>
                      <p className="text-sm text-muted-foreground">{feature.description}</p>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          {/* Technology Highlights */}
          <Card className="p-8 bg-gradient-to-br from-primary/5 to-secondary/5 border-0">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-4">Powered by Advanced AI</h2>
              <p className="text-muted-foreground max-w-2xl mx-auto">
                The knowledge Sphere Assistant leverages cutting-edge artificial intelligence to provide accurate, contextual, and auditable answers from your internal documents.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center mx-auto mb-4">
                  <Zap className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-semibold mb-2">Natural Language Processing</h3>
                <p className="text-sm text-muted-foreground">
                  Advanced NLP models understand context and nuance in academic content
                </p>
              </div>
              
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-green-500 to-teal-500 flex items-center justify-center mx-auto mb-4">
                  <Target className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-semibold mb-2">Adaptive Learning</h3>
                <p className="text-sm text-muted-foreground">
                  Personalized recommendations based on your learning patterns and progress
                </p>
              </div>
              
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center mx-auto mb-4">
                  <Shield className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-semibold mb-2">Secure & Private</h3>
                <p className="text-sm text-muted-foreground">
                  Your academic data is protected with enterprise-grade security measures
                </p>
              </div>
            </div>
          </Card>

          {/* CTA Section */}
          <div className="text-center mt-16">
            <h2 className="text-2xl font-bold mb-4">Ready to Transform How You Serve Customers?</h2>
            <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
              Trusted by knowledge Sphere teams and branches, the knowledge Sphere Assistant helps staff resolve customer queries faster, maintain policy compliance, and reduce escalation times.
            </p>
            <div className="flex gap-4 justify-center">
              <Button onClick={() => navigate('/books')} className="bg-gradient-primary">
                Get Started
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
              <Button onClick={() => navigate('/')} variant="outline">
                Learn More
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}