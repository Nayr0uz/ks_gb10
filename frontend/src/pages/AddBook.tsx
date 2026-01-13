import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '@/components/ui/header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { 
  Upload, 
  FileText, 
  Save,
  ArrowLeft,
  CheckCircle,
  AlertCircle,
  Brain,
  Sparkles,
  BookOpen,
  InfoIcon
} from 'lucide-react';
import { BooksService, Utils } from '@/lib/services';
import type { Book } from '@/lib/types';

export default function AddBook() {
  const navigate = useNavigate();
  const [bookFile, setBookFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [uploadedBook, setUploadedBook] = useState<Book | null>(null);
  const [isDuplicate, setIsDuplicate] = useState(false);
  const [existingBook, setExistingBook] = useState<Book | null>(null);

  const handleFileSelect = (file: File) => {
    const validation = Utils.validateFileType(file);
    
    if (!validation.valid) {
      setError(validation.error!);
      return;
    }

    setBookFile(file);
    setError('');
    setIsDuplicate(false);
    setExistingBook(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!bookFile) {
      setError('Please select a file to upload');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setError('');
    setIsDuplicate(false);
    setExistingBook(null);

    try {
      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 300);

      // Upload the document
      const book = await BooksService.uploadBook(bookFile);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploadedBook(book);
      setSuccess(true);
      
      // Redirect after success
      setTimeout(() => {
        navigate('/books');
      }, 3000);
      
    } catch (err) {
      setUploadProgress(0);
      
      if (err instanceof Error) {
        // Check if it's a duplicate (409 status)
        if (err.message.includes('already exists') || err.message.includes('409')) {
          setIsDuplicate(true);
          setError('This document already exists in your library.');
          
          // Try to extract document info from error or make a simple assumption
          // In a real scenario, the backend should return the existing document
          setExistingBook({
            id: 0,
            title: bookFile.name.replace(/\.[^/.]+$/, ""), // Remove extension
            author: 'Unknown',
            category_id: 7,
            file_name: bookFile.name,
            created_at: new Date().toISOString(),
            publication_year: null,
            file_hash: ''
          });
        } else {
          setError(err.message);
        }
      } else {
        setError('Failed to upload document. Please try again.');
      }
    } finally {
      setIsUploading(false);
    }
  };

  // Success Screen
  if (success && uploadedBook) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background via-background to-accent/5">
        <Header />
        
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-2xl mx-auto">
            <Card className="text-center p-8">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-10 h-10 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold mb-4">Document Added Successfully!</h2>
              <div className="bg-primary/5 rounded-lg p-6 mb-6">
                <div className="flex items-center gap-4 justify-center">
                  <div className="w-12 h-16 bg-gradient-to-br from-primary to-secondary rounded shadow-sm flex items-center justify-center">
                    <BookOpen className="w-6 h-6 text-white" />
                  </div>
                  <div className="text-left">
                    <h3 className="font-semibold text-lg">{uploadedBook.title}</h3>
                    {uploadedBook.author && (
                      <p className="text-muted-foreground">by {uploadedBook.author}</p>
                    )}
                    <p className="text-sm text-muted-foreground">
                      Category: {Utils.getCategoryName(uploadedBook.category_id)}
                    </p>
                  </div>
                </div>
              </div>
              <p className="text-muted-foreground mb-6">
                Your document has been processed with AI and is now available for chat and exam generation.
              </p>
              <div className="flex gap-4 justify-center">
                <Button onClick={() => navigate('/books')} className="bg-gradient-primary">
                  View My Library
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => navigate(`/chat?book=${encodeURIComponent(uploadedBook.title)}`)}
                >
                  Start Chatting
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  // Main Upload Screen
  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-accent/5">
      <Header />
      
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="flex items-center gap-4 mb-8">
            <Button 
              variant="outline" 
              onClick={() => navigate('/books')}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Library
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-gradient-primary">Add New Document</h1>
              <p className="text-muted-foreground text-lg">
                Upload a document and let AI extract all the information automatically
              </p>
            </div>
          </div>

          {/* AI Processing Info */}
          <Card className="mb-8 border-primary/20 bg-gradient-to-r from-primary/5 to-secondary/5">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gradient-to-br from-primary to-secondary rounded-full flex items-center justify-center">
                  <Brain className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold mb-1 flex items-center gap-2">
                    AI-Powered Processing
                    <Sparkles className="w-4 h-4 text-primary" />
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Just upload your file! Our AI will automatically extract title, author, publication details, 
                    categorize the content, and create intelligent embeddings for enhanced search and chat.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <form onSubmit={handleSubmit} className="space-y-8">
            {/* File Upload Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="w-5 h-5 text-primary" />
                  Upload Your Document
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {error && !isDuplicate && (
                  <Alert variant="destructive">
                    <AlertCircle className="w-4 h-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {isDuplicate && existingBook && (
                  <Alert className="border-orange-200 bg-orange-50">
                    <InfoIcon className="w-4 h-4 text-orange-600" />
                    <AlertDescription>
                      <div className="space-y-3">
                        <p className="font-medium text-orange-800">
                          This document already exists in your library!
                        </p>
                        <div className="bg-white rounded-lg p-4 border border-orange-200">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-12 bg-gradient-to-br from-primary to-secondary rounded shadow-sm flex items-center justify-center">
                              <BookOpen className="w-5 h-5 text-white" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-900">{existingBook.title}</p>
                              <p className="text-sm text-gray-600">
                                {existingBook.author && existingBook.author !== 'Unknown' 
                                  ? `by ${existingBook.author}` 
                                  : 'File name: ' + existingBook.file_name}
                              </p>
                            </div>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button 
                            size="sm" 
                            onClick={() => navigate('/books')}
                            className="bg-orange-600 hover:bg-orange-700"
                          >
                            View in Library
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => navigate(`/chat?book=${encodeURIComponent(existingBook.title)}`)}
                          >
                            Start Chatting
                          </Button>
                        </div>
                      </div>
                    </AlertDescription>
                  </Alert>
                )}

                {/* Book File Upload */}
                <div
                  className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-12 text-center hover:border-primary/50 transition-colors cursor-pointer"
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  onClick={() => document.getElementById('document-file')?.click()}
                >
                  <input
                    id="document-file"
                    type="file"
                    accept=".pdf,.txt,.docx"
                    onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                    className="hidden"
                  />
                  
                  {bookFile ? (
                    <div className="flex items-center justify-center gap-4">
                      <div className="w-16 h-20 bg-primary/10 rounded-lg flex items-center justify-center">
                        <FileText className="w-8 h-8 text-primary" />
                      </div>
                      <div className="text-left">
                        <p className="font-semibold text-lg">{bookFile.name}</p>
                        <p className="text-muted-foreground">
                          {Utils.formatFileSize(bookFile.size)}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <CheckCircle className="w-4 h-4 text-green-600" />
                          <span className="text-sm text-green-600">Ready to process</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-6">
                        <Upload className="w-10 h-10 text-primary" />
                      </div>
                      <h3 className="text-xl font-semibold mb-3">Drop your document file here</h3>
                      <p className="text-muted-foreground mb-6">
                        or click to browse your files
                      </p>
                      <div className="bg-muted/50 rounded-lg p-4 mb-6">
                        <p className="text-sm font-medium mb-2">Supported formats:</p>
                        <div className="flex items-center justify-center gap-6 text-sm text-muted-foreground">
                          <span>📄 PDF</span>
                          <span>📝 TXT</span>
                          <span>📃 DOCX</span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">Maximum file size: 100MB</p>
                      </div>
                      <div className="flex items-center justify-center gap-6 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Brain className="w-3 h-3" />
                          <span>AI Metadata Extraction</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Sparkles className="w-3 h-3" />
                          <span>Smart Categorization</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Upload Progress */}
            {isUploading && (
              <Card>
                <CardContent className="pt-6">
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                      <span className="font-medium">Processing your document with AI...</span>
                    </div>
                    <Progress value={uploadProgress} className="h-3" />
                    <div className="text-sm text-muted-foreground text-center">
                      {uploadProgress < 30 && "📄 Reading document content..."}
                      {uploadProgress >= 30 && uploadProgress < 60 && "🧠 Extracting metadata with AI..."}
                      {uploadProgress >= 60 && uploadProgress < 90 && "📚 Creating embeddings for smart search..."}
                      {uploadProgress >= 90 && "✨ Finalizing..."}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Submit Button */}
            <div className="flex gap-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate('/books')}
                disabled={isUploading}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isUploading || !bookFile}
                className="flex-1 bg-gradient-primary"
              >
                {isUploading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Processing with AI...
                  </div>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    Add Document to Library
                  </>
                )}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
