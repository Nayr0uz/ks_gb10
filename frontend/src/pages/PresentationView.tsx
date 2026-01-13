// src/pages/PresentationView.tsx
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { apiClient, API_ENDPOINTS } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Download, FileText, ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

type Presentation = {
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
  { bg: "from-blue-500 to-purple-600", text: "text-white" },
  { bg: "from-emerald-500 to-teal-600", text: "text-white" },
  { bg: "from-orange-500 to-pink-600", text: "text-white" },
  { bg: "from-indigo-500 to-blue-600", text: "text-white" },
  { bg: "from-purple-500 to-pink-600", text: "text-white" },
  { bg: "from-cyan-500 to-blue-600", text: "text-white" },
];

const parseSlide = (slideText: string, index: number): Slide => {
  const lines = slideText.trim().split('\n').filter(line => line.trim());
  const title = lines[0]?.replace(/^\*\*|\*\*$/g, '').replace(/^Slide Title:|^Title:/i, '').trim() || `Slide ${index + 1}`;
  const content = lines.slice(1).map(line => {
    line = line.replace(/^[*\-•]\s*/, '• ');
    return line;
  }).join('\n');
  return { title, content, index };
};

export default function PresentationView() {
  const { id } = useParams();
  const [presentation, setPresentation] = useState<Presentation | null>(null);
  const [slides, setSlides] = useState<Slide[]>([]);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      setLoading(true);
      try {
        const data = await apiClient.get<Presentation>(
          API_ENDPOINTS.PRESENTATION_BY_ID(Number(id))
        );
        setPresentation(data);
        
        if (data.content) {
          const parsedSlides = data.content
            .split("\n\n---SLIDE_SEPARATOR---\n\n")
            .filter(slide => slide.trim() && slide.trim() !== "---SLIDE_SEPARATOR---")
            .map((slide, idx) => parseSlide(slide, idx));
          setSlides(parsedSlides);
        }
      } catch (e: any) {
        setErr(e.message || "Failed to load presentation");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [id]);

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" && currentSlide < slides.length - 1) {
        setCurrentSlide(prev => prev + 1);
      } else if (e.key === "ArrowLeft" && currentSlide > 0) {
        setCurrentSlide(prev => prev - 1);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [currentSlide, slides.length]);

  const downloadAsPPT = async () => {
    if (!presentation) return;
    
    try {
      const response = await fetch(`http://localhost:8080/api/v1/presentation/${presentation.id}/download/ppt`);
      
      if (!response.ok) {
        const text = await response.text().catch(() => "");
        console.error("PPT download failed", { status: response.status, statusText: response.statusText, body: text });
        throw new Error(`Download failed: ${response.status} ${response.statusText}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${presentation.title}.pptx`;
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

  const downloadAsTXT = () => {
    if (!presentation?.content) return;

    // Use original content with separators preserved
    const content = slides.map((slide, i) => 
      `Slide ${i + 1}: ${slide.title}\n\n${slide.content}`
    ).join('\n\n---SLIDE_SEPARATOR---\n\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${presentation.title}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    
    toast({
      title: "Downloaded",
      description: "Presentation exported as text file.",
    });
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-900">
        <p className="text-white text-lg">Loading presentation...</p>
      </div>
    );
  }

  if (err || !presentation || slides.length === 0) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-slate-900 text-white p-6">
        <p className="text-red-400 text-lg mb-4">{err || "Presentation not found"}</p>
        <Button asChild variant="outline">
          <Link to="/presentations">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Presentations
          </Link>
        </Button>
      </div>
    );
  }

  const currentSlideData = slides[currentSlide];
  const theme = slideThemes[currentSlide % slideThemes.length];

  return (
    <div className="h-screen bg-slate-900 flex flex-col">
      {/* Top Bar */}
      <div className="bg-slate-800 border-b border-slate-700 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button asChild variant="ghost" size="sm" className="text-slate-300 hover:text-white">
            <Link to="/presentations">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Link>
          </Button>
          <div>
            <h1 className="text-white font-semibold">{presentation.title}</h1>
            <p className="text-slate-400 text-xs">
              Slide {currentSlide + 1} of {slides.length}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="ghost" 
            size="sm"
            onClick={downloadAsTXT}
            className="text-slate-300 hover:text-white"
          >
            <Download className="w-4 h-4 mr-2" />
            TXT
          </Button>
          <Button 
            variant="ghost" 
            size="sm"
            onClick={downloadAsPPT}
            className="text-slate-300 hover:text-white"
          >
            <FileText className="w-4 h-4 mr-2" />
            PPT
          </Button>
        </div>
      </div>

      {/* Slide Display */}
      <div className="flex-1 flex items-center justify-center p-8">
        <Card className="w-full max-w-5xl aspect-video overflow-hidden shadow-2xl">
          <div className={`bg-gradient-to-br ${theme.bg} ${theme.text} h-1/3 p-12 relative overflow-hidden`}>
            <div className="absolute top-0 right-0 w-40 h-40 bg-white opacity-10 rounded-full -mr-20 -mt-20" />
            <div className="absolute bottom-0 left-0 w-32 h-32 bg-white opacity-10 rounded-full -ml-16 -mb-16" />
            <div className="relative z-10">
              <div className="text-sm font-semibold opacity-80 mb-3">
                Slide {currentSlideData.index + 1}
              </div>
              <h2 className="text-4xl font-bold leading-tight">
                {currentSlideData.title}
              </h2>
            </div>
          </div>
          <CardContent className="h-2/3 p-12 bg-gradient-to-b from-white to-slate-50 overflow-y-auto">
            <div className="space-y-4">
              {currentSlideData.content.split('\n').filter(line => line.trim()).map((line, idx) => (
                <div key={idx} className="flex items-start gap-4">
                  {line.startsWith('•') ? (
                    <>
                      <span className="text-blue-500 font-bold text-2xl mt-1">•</span>
                      <p className="text-slate-700 leading-relaxed flex-1 text-xl">
                        {line.substring(1).trim()}
                      </p>
                    </>
                  ) : (
                    <p className="text-slate-700 leading-relaxed text-xl w-full">
                      {line}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bottom Navigation */}
      <div className="bg-slate-800 border-t border-slate-700 px-6 py-4 flex items-center justify-between">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCurrentSlide(prev => Math.max(0, prev - 1))}
          disabled={currentSlide === 0}
          className="text-slate-300 hover:text-white disabled:opacity-30"
        >
          <ChevronLeft className="w-5 h-5 mr-1" />
          Previous
        </Button>

        <div className="flex gap-2">
          {slides.map((_, idx) => (
            <button
              key={idx}
              onClick={() => setCurrentSlide(idx)}
              className={`w-2 h-2 rounded-full transition-all ${
                idx === currentSlide 
                  ? 'bg-blue-500 w-8' 
                  : 'bg-slate-600 hover:bg-slate-500'
              }`}
            />
          ))}
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCurrentSlide(prev => Math.min(slides.length - 1, prev + 1))}
          disabled={currentSlide === slides.length - 1}
          className="text-slate-300 hover:text-white disabled:opacity-30"
        >
          Next
          <ChevronRight className="w-5 h-5 ml-1" />
        </Button>
      </div>
    </div>
  );
}