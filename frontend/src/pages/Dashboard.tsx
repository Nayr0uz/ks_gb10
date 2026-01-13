import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '@/components/ui/header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { BooksService, SessionService } from '@/lib/services';
import { useAuth } from '@/contexts/AuthContext';
import { 
  BookOpen, 
  TrendingUp, 
  Flame,
  BarChart3,
  Activity,
  Plus,
  ArrowRight,
  CheckCircle,
  MessageCircle,
  FileText,
  Loader2,
  AlertCircle
} from 'lucide-react';

interface DashboardStats {
  totalDocuments: number;
  totalSessions: number;
  totalChats: number;
  lastActivity: string;
  streak: number;
}

interface Document {
  id: number;
  title: string;
  author?: string;
  category_id: number;
  created_at: string;
}

interface Session {
  id: string;
  session_name?: string;
  created_at: string;
  updated_at: string;
}

interface RecentActivity {
  type: 'document' | 'script' | 'session' | 'chat';
  title: string;
  time: string;
  score?: string;
  icon: React.ComponentType<any>;
}

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // State for real data
  const [stats, setStats] = useState<DashboardStats>({
    totalDocuments: 0,
    totalSessions: 0,
    totalChats: 0,
    lastActivity: 'Never'
  });
  
  const [recentDocuments, setRecentDocuments] = useState<Document[]>([]);

  const [recentSessions, setRecentSessions] = useState<Session[]>([]);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);

  // Fetch user data on component mount
  useEffect(() => {
    if (user?.sub) {
      fetchDashboardData();
    }
  }, [user?.sub]);

  const fetchDashboardData = async () => {
    if (!user?.sub) return;
    
    try {
      setLoading(true);
      setError(null);

      // Fetch all data in parallel
      const [booksData, sessionsData] = await Promise.all([
        BooksService.getBooks().catch(err => {
          console.warn('Failed to fetch books:', err);
          return [];
        }),
        SessionService.getUserSessions(user.sub).catch(err => {
          console.warn('Failed to fetch sessions:', err);
          return [];
        })
      ]);

      // Process and set data
      setRecentDocuments(booksData.slice(0, 5) || []);
      setRecentSessions(sessionsData.slice(0, 5) || []);

      // Calculate stats
      const newStats: DashboardStats = {
        totalDocuments: booksData?.length || 0,
        totalSessions: sessionsData?.length || 0,
        totalChats: sessionsData?.length || 0,
        lastActivity: getLastActivity(booksData, sessionsData),
        streak: calculateStreak(booksData, sessionsData)
      };
      setStats(newStats);

      // Generate recent activity
      generateRecentActivity(booksData, sessionsData);

    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError('Failed to load dashboard data. Please try refreshing the page.');
    } finally {
      setLoading(false);
    }
  };

  const getLastActivity = (documents: Document[], sessions: Session[]): string => {
    const allDates = [
      ...documents.map(b => new Date(b.created_at)),
      ...sessions.map(s => new Date(s.updated_at))
    ];

    if (allDates.length === 0) return 'Never';

    const latest = new Date(Math.max(...allDates.map(d => d.getTime())));
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - latest.getTime()) / (1000 * 60 * 60));

    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${diffInHours} hours ago`;
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays === 1) return 'Yesterday';
    if (diffInDays < 7) return `${diffInDays} days ago`;
    return latest.toLocaleDateString();
  };

  const calculateStreak = (documents: Document[], sessions: Session[]): number => {
    const allDates = [
      ...documents.map(b => new Date(b.created_at)),
      ...sessions.map(s => new Date(s.updated_at))
    ];

    if (allDates.length === 0) return 0;

    // Get unique dates (days only, ignoring time)
    const uniqueDates = new Set(
      allDates.map(d => {
        const date = new Date(d);
        return date.toLocaleDateString('en-CA'); // YYYY-MM-DD format
      })
    );

    // Sort dates in descending order
    const sortedDates = Array.from(uniqueDates)
      .sort()
      .reverse();

    if (sortedDates.length === 0) return 0;

    // Check if streak is active (last activity was today or yesterday)
    const today = new Date().toLocaleDateString('en-CA');
    const yesterday = new Date(Date.now() - 86400000).toLocaleDateString('en-CA');
    
    if (sortedDates[0] !== today && sortedDates[0] !== yesterday) {
      return 0; // Streak is broken
    }

    // Count consecutive days from the most recent date
    let streak = 1;
    let currentDate = new Date(sortedDates[0]);

    for (let i = 1; i < sortedDates.length; i++) {
      const prevDate = new Date(currentDate);
      prevDate.setDate(prevDate.getDate() - 1);
      const prevDateStr = prevDate.toLocaleDateString('en-CA');

      if (sortedDates[i] === prevDateStr) {
        streak++;
        currentDate = prevDate;
      } else {
        break;
      }
    }

    return streak;
  };

  const generateRecentActivity = (documents: Document[], sessions: Session[]) => {
    const activities: RecentActivity[] = [];

    // Add recent documents
    documents.slice(0, 3).forEach(document => {
      activities.push({
        type: 'document',
        title: `Added "${document.title}"`,
        time: getRelativeTime(document.created_at),
        icon: BookOpen
      });
    });

    // Add recent sessions
    sessions.slice(0, 3).forEach(session => {
      activities.push({
        type: 'session',
        title: `Chat session: ${session.session_name || 'Unnamed'}`,
        time: getRelativeTime(session.updated_at),
        icon: MessageCircle
      });
    });

    // Sort by time and take the most recent 10
    activities.sort((a, b) => {
      const timeA = new Date(a.time.includes('ago') ? Date.now() : a.time).getTime();
      const timeB = new Date(b.time.includes('ago') ? Date.now() : b.time).getTime();
      return timeB - timeA;
    });

    setRecentActivity(activities.slice(0, 10));
  };

  const getRelativeTime = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));

    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes} minutes ago`;
    
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours} hours ago`;
    
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays === 1) return 'Yesterday';
    if (diffInDays < 7) return `${diffInDays} days ago`;
    
    return date.toLocaleDateString();
  };

  const statCards = [
    { 
      label: "Documents in Library", 
      value: stats.totalDocuments, 
      icon: BookOpen, 
      color: "text-blue-600", 
      bgColor: "bg-blue-100",
      action: () => navigate('/books')
    },

    { 
      label: "Chat Sessions", 
      value: stats.totalSessions, 
      icon: MessageCircle, 
      color: "text-green-600", 
      bgColor: "bg-green-100",
      action: () => navigate('/chat')
    }
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background via-background to-accent/5">
        <Header />
        <div className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
              <p className="text-muted-foreground">Loading your dashboard...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-accent/5">
      <Header />
      
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-7xl mx-auto">
          {/* Welcome Section */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-purple-600 bg-clip-text text-transparent mb-2">
                  Welcome back {user?.full_name}! 👋
                </h1>
                <p className="text-muted-foreground">
                  Here's your learning progress and activities
                </p>
              </div>
              <div className="text-right">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="w-5 h-5 text-primary" />
                  <span className="font-medium">Last active: {stats.lastActivity}</span>
                </div>
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <Alert className="mb-6">
                <AlertCircle className="w-4 h-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </div>

          {/* Stats Overview */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {statCards.map((stat, index) => (
              <Card 
                key={index} 
                className="hover:shadow-lg transition-all duration-200 cursor-pointer group"
                onClick={stat.action}
              >
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">{stat.label}</p>
                      <p className="text-2xl font-bold">{stat.value}</p>
                    </div>
                    <div className={`w-12 h-12 rounded-lg ${stat.bgColor} flex items-center justify-center group-hover:scale-110 transition-transform`}>
                      <stat.icon className={`w-6 h-6 ${stat.color}`} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <Card className="hover:shadow-lg transition-all duration-200 cursor-pointer group" onClick={() => navigate('/books/add')}>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center group-hover:scale-110 transition-transform">
                    <Plus className="w-6 h-6 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Add New Document</h3>
                    <p className="text-sm text-muted-foreground">Expand your library</p>
                  </div>
                  <ArrowRight className="w-5 h-5 text-muted-foreground ml-auto group-hover:translate-x-1 transition-transform" />
                </div>
              </CardContent>
            </Card>

            <Card className="hover:shadow-lg transition-all duration-200 cursor-pointer group" onClick={() => navigate('/chat')}>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-lg bg-green-100 flex items-center justify-center group-hover:scale-110 transition-transform">
                    <MessageCircle className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Start Chat</h3>
                    <p className="text-sm text-muted-foreground">AI-powered learning</p>
                  </div>
                  <ArrowRight className="w-5 h-5 text-muted-foreground ml-auto group-hover:translate-x-1 transition-transform" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Main Content Tabs */}
          <Tabs value={selectedTab} onValueChange={setSelectedTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3 mb-8">
              <TabsTrigger value="overview" className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                Overview
              </TabsTrigger>
              <TabsTrigger value="activity" className="flex items-center gap-2">
                <Activity className="w-4 h-4" />
                Recent Activity
              </TabsTrigger>
              <TabsTrigger value="library" className="flex items-center gap-2">
                <BookOpen className="w-4 h-4" />
                My Library
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Learning Streak */}
                <Card>
                  <CardHeader className="pb-4">
                    <CardTitle className="flex items-center gap-2">
                      <Flame className="w-5 h-5 text-orange-500" />
                      Learning Momentum
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="text-center">
                        <div className="text-3xl font-bold text-orange-500 mb-2">
                          {stats.streak} days
                        </div>
                        <p className="text-muted-foreground">Current streak</p>
                      </div>
                      <div className="grid grid-cols-7 gap-1">
                        {Array.from({ length: 7 }, (_, i) => (
                          <div
                            key={i}
                            className={`h-8 rounded flex items-center justify-center text-xs font-medium ${
                              i < stats.streak
                                ? 'bg-orange-100 text-orange-600'
                                : 'bg-gray-100 text-gray-400'
                            }`}
                          >
                            {i < stats.streak ? '🔥' : '💤'}
                          </div>
                        ))}
                      </div>
                      <p className="text-sm text-center text-muted-foreground">
                        Keep learning daily to maintain your streak!
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Performance Overview */}
                <Card>
                  <CardHeader className="pb-4">
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-green-500" />
                      This Week's Activity
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">Documents Added</span>
                        <span className="font-semibold">{recentDocuments.length}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">Scripts Created</span>
                        <span className="font-semibold">0</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">Chat Sessions</span>
                        <span className="font-semibold">{recentSessions.length}</span>
                      </div>
                      <div className="pt-4 border-t">
                        <div className="flex items-center gap-2">
                          <CheckCircle className="w-4 h-4 text-green-500" />
                          <span className="text-sm">
                            {stats.totalDocuments + stats.totalSessions > 0 
                              ? "Great progress this week!" 
                              : "Start your learning journey today!"}
                          </span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="activity">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="w-5 h-5" />
                    Recent Activity
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {recentActivity.length > 0 ? (
                    <div className="space-y-4">
                      {recentActivity.map((activity, index) => {
                        const IconComponent = activity.icon;
                        return (
                          <div key={index} className="flex items-center gap-4 p-3 rounded-lg hover:bg-accent/50 transition-colors">
                            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                              <IconComponent className="w-5 h-5 text-primary" />
                            </div>
                            <div className="flex-1">
                              <p className="font-medium">{activity.title}</p>
                              <p className="text-sm text-muted-foreground">{activity.time}</p>
                            </div>
                            {activity.score && (
                              <Badge variant="secondary" className="bg-green-100 text-green-700">
                                {activity.score}
                              </Badge>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Activity className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                      <p className="text-muted-foreground">No recent activity</p>
                      <p className="text-sm text-muted-foreground mt-2">
                        Start by adding a document or creating your first script!
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="library">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Recent Documents */}
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <BookOpen className="w-5 h-5" />
                      Recent Documents
                    </CardTitle>
                    <Button variant="outline" size="sm" onClick={() => navigate('/books')}>
                      View All
                    </Button>
                  </CardHeader>
                  <CardContent>
                    {recentDocuments.length > 0 ? (
                      <div className="space-y-3">
                        {recentDocuments.map((document) => (
                          <div key={document.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-accent/50 transition-colors">
                            <div className="w-10 h-10 rounded bg-blue-100 flex items-center justify-center">
                              <BookOpen className="w-5 h-5 text-blue-600" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium truncate">{document.title}</p>
                              {document.author && (
                                <p className="text-sm text-muted-foreground truncate">{document.author}</p>
                              )}
                              <p className="text-xs text-muted-foreground">
                                Added {getRelativeTime(document.created_at)}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-6">
                        <BookOpen className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
                        <p className="text-muted-foreground">No documents yet</p>
                        <Button size="sm" className="mt-3" onClick={() => navigate('/books/add')}>
                          Add Your First Document
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Recent Sessions */}
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <MessageCircle className="w-5 h-5" />
                      Recent Chat Sessions
                    </CardTitle>
                    <Button variant="outline" size="sm" onClick={() => navigate('/chat')}>
                      View All
                    </Button>
                  </CardHeader>
                  <CardContent>
                    {recentSessions.length > 0 ? (
                      <div className="space-y-3">
                        {recentSessions.map((session) => (
                          <div key={session.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-accent/50 transition-colors">
                            <div className="w-10 h-10 rounded bg-green-100 flex items-center justify-center">
                              <MessageCircle className="w-5 h-5 text-green-600" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium truncate">{session.session_name || 'Unnamed Session'}</p>
                              <p className="text-xs text-muted-foreground">
                                Last active {getRelativeTime(session.updated_at)}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-6">
                        <MessageCircle className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
                        <p className="text-muted-foreground">No chat sessions yet</p>
                        <Button size="sm" className="mt-3" onClick={() => navigate('/chat')}>
                          Start a Chat Session
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}