import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { presentationApiClient } from "@/lib/api";
import { Download, FileText, Loader2, ArrowLeft, Sparkles } from "lucide-react";

type PresentationRow = {
  id: number;
  title: string;
  status: string;
  output_file_path?: string | null;
  created_at?: string | null;
  content?: string | null;
};

type Slide = {
  title: string;
  content: string;
  index: number;
};

const slideThemes = [
  { bg: "bg-gradient-to-br from-blue-500 to-purple-600", text: "text-white" },
  { bg: "bg-gradient-to-br from-emerald-500 to-teal-600", text: "text-white" },
  { bg: "bg-gradient-to-br from-orange-500 to-pink-600", text: "text-white" },
  { bg: "bg-gradient-to-br from-indigo-500 to-blue-600", text: "text-white" },
  { bg: "bg-gradient-to-br from-purple-500 to-pink-600", text: "text-white" },
  { bg: "bg-gradient-to-br from-cyan-500 to-blue-600", text: "text-white" },
];

const parseSlide = (slideText: string, index: number): Slide => {
  const lines = slideText.trim().split('\n').filter(line => line.trim());
  const title = lines[0]?.replace(/^\*\*|\*\*$/g, '').replace(/^Slide Title:|^Title:/i, '').trim() || `Slide ${index + 1}`;
  const content = lines.slice(1).join('\n');
  return { title, content, index };
};

export function GeneratePresentation() {
  const [title, setTitle] = useState("");
  const [scope, setScope] = useState("Entire Document");
  const [topic, setTopic] = useState("");
  const [detailLevel, setDetailLevel] = useState("Summary");
  const [difficulty, setDifficulty] = useState("Beginner");
  const [slideStyle, setSlideStyle] = useState("Professional");
  const [numSlides, setNumSlides] = useState([15]);
  const [includeDiagrams, setIncludeDiagrams] = useState(false);
  const [includeCodeExamples, setIncludeCodeExamples] = useState(false);

  const [presentations, setPresentations] = useState<PresentationRow[]>([]);
  const [loadingPresentations, setLoadingPresentations] = useState(false);
  const [selectedPresentation, setSelectedPresentation] = useState<PresentationRow | null>(null);
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedSlides, setGeneratedSlides] = useState<Slide[]>([]);
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);

  const { toast } = useToast();

  const loadPresentations = async () => {
    setLoadingPresentations(true);
    try {
      const data = await presentationApiClient.get<PresentationRow[]>("/presentations/");
      setPresentations(data);
    } catch (error) {
      console.error("Error loading presentations:", error);
      toast({
        title: "Could not load presentations",
        variant: "destructive",
      });
    } finally {
      setLoadingPresentations(false);
    }
  };

  useEffect(() => {
    void loadPresentations();
  }, []);

  const handleSelectPresentation = async (presentationId: number) => {
    try {
      const data = await presentationApiClient.get<PresentationRow>(`/${presentationId}`);
      setSelectedPresentation(data);
      
      if (data.content) {
        const slides = data.content
          .split("\n\n---SLIDE_SEPARATOR---\n\n")
          .filter(s => s.trim() && s.trim() !== "---SLIDE_SEPARATOR---")
          .map((slide, idx) => parseSlide(slide, idx));
        setGeneratedSlides(slides);
      }
    } catch (error) {
      console.error("Error loading presentation details:", error);
      toast({
        title: "Could not load presentation details",
        variant: "destructive",
      });
    }
  };

  const handleSubmit = async () => {
    if (!title.trim()) {
      toast({
        title: "Title required",
        description: "Please enter a presentation title",
        variant: "destructive",
      });
      return;
    }

    setIsGenerating(true);
    setGeneratedSlides([]);
    setCurrentSlideIndex(0);

    try {
      // Use a streaming approach
      const response = await fetch("http://localhost:8003/api/v1/presentation/generate-presentation-stream/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          scope,
          topic: scope === "Specific Topic" ? topic : null,
          detail_level: detailLevel,
          difficulty,
          slide_style: slideStyle,
          num_slides: numSlides[0],
          include_diagrams: includeDiagrams,
          include_code_examples: includeCodeExamples,
        }),
      });

      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedData = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        accumulatedData += decoder.decode(value, { stream: true });
        
        // Process slide by slide
        const parts = accumulatedData.split("\n\n");
        
        if (parts.length > 1) {
          for (let i = 0; i < parts.length - 1; i++) {
            const slideJson = parts[i];
            if (slideJson) {
              const slide = JSON.parse(slideJson);
              // Skip separator-only slides emitted by the generator
              if (!slide.content || slide.content.trim() === '---SLIDE_SEPARATOR---') {
                continue;
              }
              setGeneratedSlides(prev => [...prev, parseSlide(slide.content, prev.length)]);
              setCurrentSlideIndex(prev => prev + 1);
            }
          }
          accumulatedData = parts[parts.length - 1];
        }
      }

      void loadPresentations();

      toast({
        title: "Presentation generated",
        description: `"${title}" is ready.`,
      });

    } catch (error) {
      console.error("Error generating presentation:", error);
      toast({
        title: "Error",
        description: "Failed to generate presentation.",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadAsPPT = async () => {
    if (!selectedPresentation) return;
    
    try {
      const response = await fetch(`http://localhost:8080/api/v1/presentation/${selectedPresentation.id}/download/ppt`);

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        console.error("PPT download failed", { status: response.status, statusText: response.statusText, body: text });
        throw new Error(`Download failed: ${response.status} ${response.statusText}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedPresentation.title}.pptx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      toast({
        title: "PPTX Downloaded",
        description: "The presentation has been downloaded.",
      });
    } catch (error) {
      console.error("Error downloading PPTX:", error);
      toast({
        title: "Download Failed",
        description: "Could not download the presentation.",
        variant: "destructive",
      });
    }
  };

  const downloadAsTXT = async () => {
    if (!selectedPresentation?.content) return;

    const content = generatedSlides.map((slide, i) =>
      `Slide ${i + 1}: ${slide.title}\n\n${slide.content}`
    ).join('\n\n---SLIDE_SEPARATOR---\n\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedPresentation.title}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    
    toast({
      title: "Downloaded",
      description: "Presentation exported as text file.",
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="container mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
            Generate Presentation
          </h1>
          <p className="text-slate-600">Create beautiful presentations with AI</p>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <Card className="lg:col-span-2 shadow-lg border-0">
            <CardHeader className="bg-gradient-to-r from-blue-500 to-purple-500 text-white">
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                Presentation Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-4">
                <div>
                  <Label htmlFor="title">Title</Label>
                  <Input
                    id="title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g., loans"
                    className="mt-1"
                  />
                </div>

                <div>
                  <Label htmlFor="scope">Scope</Label>
                  <Select value={scope} onValueChange={setScope}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="Select scope" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Entire Document">Entire Document</SelectItem>
                      <SelectItem value="Specific Topic">Specific Topic</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {scope === "Specific Topic" && (
                  <div>
                    <Label htmlFor="topic">Topic Name</Label>
                    <Input
                      id="topic"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      placeholder="e.g., Loan Repayment Terms"
                      className="mt-1"
                    />
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label htmlFor="detailLevel">Detail Level</Label>
                    <Select value={detailLevel} onValueChange={setDetailLevel}>
                      <SelectTrigger className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Summary">Summary</SelectItem>
                        <SelectItem value="Detailed">Detailed</SelectItem>
                        <SelectItem value="Comprehensive">Comprehensive</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="difficulty">Difficulty</Label>
                    <Select value={difficulty} onValueChange={setDifficulty}>
                      <SelectTrigger className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Beginner">Beginner</SelectItem>
                        <SelectItem value="Intermediate">Intermediate</SelectItem>
                        <SelectItem value="Advanced">Advanced</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div>
                  <Label htmlFor="slideStyle">Slide Style</Label>
                  <Select value={slideStyle} onValueChange={setSlideStyle}>
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Professional">Professional</SelectItem>
                      <SelectItem value="Creative">Creative</SelectItem>
                      <SelectItem value="Modern">Modern</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="numSlides">Number of Slides: {numSlides[0]}</Label>
                  <Slider
                    id="numSlides"
                    min={5}
                    max={30}
                    step={1}
                    value={numSlides}
                    onValueChange={setNumSlides}
                    className="mt-2"
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="includeDiagrams"
                    checked={includeDiagrams}
                    onCheckedChange={setIncludeDiagrams}
                  />
                  <Label htmlFor="includeDiagrams">Include Diagrams</Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="includeCodeExamples"
                    checked={includeCodeExamples}
                    onCheckedChange={setIncludeCodeExamples}
                  />
                  <Label htmlFor="includeCodeExamples">Include Code Examples</Label>
                </div>

                <Button 
                  onClick={handleSubmit}
                  className="w-full bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600"
                  disabled={isGenerating}
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    "Generate Presentation"
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="lg:col-span-3 space-y-4">
            {selectedPresentation || generatedSlides.length > 0 ? (
              <>
                <div className="flex items-center justify-between">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => {
                      setSelectedPresentation(null);
                      setGeneratedSlides([]);
                    }}
                  >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to list
                  </Button>
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={downloadAsTXT}
                      disabled={isGenerating}
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Export TXT
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={downloadAsPPT}
                      disabled={isGenerating}
                    >
                      <FileText className="w-4 h-4 mr-2" />
                      Export PPT
                    </Button>
                  </div>
                </div>

                <div className="bg-white rounded-lg shadow-lg p-6">
                  <h2 className="text-2xl font-bold mb-1">
                    {selectedPresentation?.title || title}
                  </h2>
                  <p className="text-sm text-slate-500 mb-6">
                    {generatedSlides.length} slides
                    {isGenerating && " • Generating..."}
                  </p>

                  <div id="slides-container" className="space-y-6">
                    {generatedSlides.map((slide, index) => {
                      const theme = slideThemes[index % slideThemes.length];
                      return (
                        <Card 
                          key={index}
                          className={`overflow-hidden transform transition-all duration-500 ${
                            index === currentSlideIndex && isGenerating
                              ? 'scale-105 shadow-2xl'
                              : 'hover:shadow-xl'
                          }`}
                          style={{
                            animationName: 'slideIn',
                            animationDuration: '0.5s',
                            animationTimingFunction: 'ease-out',
                            animationDelay: `${index * 0.1}s`,
                            animationFillMode: 'both'
                          }}
                        >
                          <div className={`${theme.bg} ${theme.text} p-8 relative overflow-hidden`}>
                            <div className="absolute top-0 right-0 w-32 h-32 bg-white opacity-10 rounded-full -mr-16 -mt-16" />
                            <div className="absolute bottom-0 left-0 w-24 h-24 bg-white opacity-10 rounded-full -ml-12 -mb-12" />
                            <div className="relative z-10">
                              <div className="text-sm font-semibold opacity-80 mb-2">
                                Slide {slide.index + 1}
                              </div>
                              <h3 className="text-3xl font-bold mb-4">
                                {slide.title}
                              </h3>
                            </div>
                          </div>
                          <CardContent className="p-8 bg-gradient-to-b from-white to-slate-50">
                            <div className="prose prose-slate max-w-none">
                              <pre className="whitespace-pre-wrap text-sm leading-relaxed font-sans">
                                {slide.content}
                              </pre>
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                    
                    {isGenerating && (
                      <div className="flex items-center justify-center p-12">
                        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                        <span className="ml-3 text-slate-600">Generating next slide...</span>
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <Card className="shadow-lg border-0">
                <CardHeader className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white">
                  <CardTitle>Your Presentations</CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  {loadingPresentations ? (
                    <div className="flex items-center justify-center p-12">
                      <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                    </div>
                  ) : presentations.length === 0 ? (
                    <div className="text-center p-12">
                      <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                      <p className="text-slate-500">
                        No presentations yet. Generate one to get started!
                      </p>
                    </div>
                  ) : (
                    <div className="grid gap-3">
                      {presentations.map((p) => (
                        <Card
                          key={p.id}
                          className="cursor-pointer hover:shadow-md transition-all border-l-4 border-l-blue-500"
                          onClick={() => handleSelectPresentation(p.id)}
                        >
                          <CardContent className="p-4">
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <p className="font-semibold text-slate-800">{p.title}</p>
                                <p className="text-xs text-slate-500 mt-1">
                                  #{p.id} · {p.created_at ? new Date(p.created_at).toLocaleString() : "No date"}
                                </p>
                              </div>
                              <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                                p.status === 'completed' 
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : p.status === 'processing'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-amber-100 text-amber-800'
                              }`}>
                                {p.status}
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}
