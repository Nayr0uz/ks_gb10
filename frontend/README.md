# Zakerly - AI-Powered Academic Assistant

![Zakerly Logo](src/assets/zakerly-logo.png)

Zakerly is a comprehensive AI-powered learning platform designed to revolutionize how students and researchers interact with academic content. Transform your books into intelligent companions that can answer questions, generate exams, create lecture scripts, and help you master any subject.

## 🚀 Features Overview

### 📚 **Smart Book Management**
- Upload and organize your academic library
- Track reading progress and learning goals
- Categorize books by subject and difficulty
- Monitor your study statistics and achievements

### 💬 **AI Chat with Books**
- **Natural Language Queries**: Ask questions about any uploaded book in plain English
- **Contextual Understanding**: AI understands the broader context of your questions
- **Source Citations**: Every answer includes precise citations for academic credibility
- **Cross-Reference Capabilities**: Connect ideas across different chapters and books
- **External Information Labeling**: Clearly marked when AI provides information from external sources

### 🎓 **Smart Exam Generator**
- **Multiple Question Types**: 
  - Multiple Choice
  - True/False
  - Short Answer
  - Essay Questions
- **Adaptive Difficulty**: Choose from Easy, Medium, or Hard difficulty levels
- **Customizable Parameters**: 
  - Set number of questions (5-100)
  - Configure time limits (15-180 minutes)
  - Select specific topics or chapters
- **Instant Generation**: AI creates unique exams in seconds
- **Export Options**: Save as PDF or print for offline use

### 🏋️ **Interactive Exam Rehearsal**
- **Real-time Practice Environment**: Take generated exams with immediate feedback
- **Progress Tracking**: Monitor your performance across multiple attempts
- **Detailed Explanations**: Get comprehensive explanations for both correct and incorrect answers
- **Performance Analytics**: Identify strengths and areas for improvement
- **Confidence Building**: Practice in a supportive, low-pressure environment
- **Adaptive Review**: Focus on areas where you need the most practice

### 📝 **Lecture Script Generator**
- **Structured Content Creation**: Generate professional lecture scripts from book content
- **Customizable Depth Levels**:
  - Overview: High-level concepts
  - Detailed: Comprehensive coverage
  - In-depth: Extensive analysis
- **Flexible Duration**: Scripts for 15-180 minute presentations
- **Multiple Export Formats**: 
  - Plain text (.txt)
  - Microsoft Word (.docx) 
  - PDF format
- **Author Attribution**: Track script creators and speakers

### 🎤 **Media Transcription (AI-Powered)**
- **Audio & Video Support**: Upload lectures in multiple formats
  - Audio: MP3, WAV, OGG, M4A
  - Video: MP4, WebM, MOV, AVI
- **Advanced Speech Recognition**: Powered by OpenAI Whisper model
- **WebGPU Acceleration**: Fast, accurate transcription entirely in your browser
- **Edit & Review**: Review and edit transcriptions before saving
- **Speaker Attribution**: Add author/speaker information to transcribed content
- **No Server Required**: All processing happens client-side for privacy

## 🎯 Key Benefits

### **For Students**
- **Exam Preparation**: Generate unlimited practice tests tailored to your materials
- **Quick Knowledge Checks**: Ask specific questions about complex topics
- **Study Efficiency**: Get instant answers instead of searching through entire books
- **Progress Tracking**: Monitor your learning journey with detailed analytics

### **For Researchers**
- **Deep Content Exploration**: Investigate connections between different academic works
- **Citation Support**: Get properly cited references for your research
- **Literature Review**: Quickly understand key concepts from multiple sources
- **Knowledge Synthesis**: Combine insights from various academic materials

### **For Educators**
- **Lecture Preparation**: Generate structured presentation materials
- **Assessment Creation**: Create diverse exams and quizzes instantly
- **Content Organization**: Transform recorded lectures into readable scripts
- **Student Support**: Provide additional learning resources and practice materials

## 🛠️ Technology Stack

### **Frontend**
- **React 18**: Modern component-based UI framework
- **TypeScript**: Type-safe development for better code quality
- **Vite**: Lightning-fast build tool and development server
- **Tailwind CSS**: Utility-first CSS framework for responsive design
- **shadcn/ui**: Beautiful, accessible component library

### **AI & Machine Learning**
- **Hugging Face Transformers**: Browser-based AI model execution
- **OpenAI Whisper**: State-of-the-art speech recognition
- **WebGPU Acceleration**: Hardware-accelerated AI inference
- **Natural Language Processing**: Advanced text understanding and generation

### **Architecture**
- **Client-Side Processing**: Privacy-first approach with local AI execution
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Progressive Web App**: Fast loading with offline capabilities
- **Modern ES Modules**: Tree-shakable, optimized bundle size

## 🚀 Getting Started

### **Prerequisites**
- Node.js 16+ and npm installed
- Modern web browser with WebGPU support (recommended)
- Sufficient RAM (4GB+) for AI model execution

### **Installation**

1. **Clone the repository**
   ```bash
   git clone <YOUR_GIT_URL>
   cd zakerly
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

4. **Open in browser**
   ```
   http://localhost:5173
   ```

### **First Steps**
1. **Add Your Books**: Navigate to `/books` and upload your academic materials
2. **Start Chatting**: Go to `/chat`, select a book, and ask your first question
3. **Generate Exams**: Visit `/exams` to create your first practice test
4. **Create Scripts**: Use `/scripts` to generate lecture materials

## 📖 Feature Documentation

### **Book Management (`/books`)**
- **Upload Process**: Add books to your personal library
- **Organization**: Filter by subject, author, or reading status
- **Progress Tracking**: Monitor your reading progress with visual indicators
- **Quick Actions**: Direct access to chat and exam generation for each book

### **AI Chat Interface (`/chat`)**
- **Book Selection**: Choose from your uploaded library
- **Conversation History**: Maintain context throughout your session
- **Export Options**: Save conversations as text files
- **Citation Tracking**: Verify information with source references

### **Exam Generation (`/exams`)**
- **Configuration Wizard**: Step-by-step exam setup process
- **Review Phase**: Preview settings before generation
- **Generated Exam View**: Detailed exam overview with metadata
- **Action Options**: Start rehearsal, view questions, or export

### **Exam Rehearsal (`/exam`)**
- **Timed Practice**: Real-time countdown with visual progress
- **Question Navigation**: Move between questions freely
- **Answer Types**: Support for all question formats
- **Results Analysis**: Comprehensive performance breakdown

### **Script Creation (`/scripts`)**
- **Manual Creation**: Form-based script configuration
- **Media Transcription**: Upload audio/video for automatic transcription
- **Author Management**: Track script creators and speakers
- **Export Flexibility**: Multiple format options for different use cases

## 🔧 Advanced Configuration

### **AI Model Settings**
- Models are automatically downloaded and cached in the browser
- WebGPU acceleration is enabled by default where supported
- Fallback to WebGL/CPU if WebGPU is unavailable

### **Performance Optimization**
- Large files (>100MB) are automatically rejected to maintain performance
- Background model initialization for faster subsequent use
- Progressive loading with user feedback during AI operations

### **Privacy & Security**
- All AI processing happens locally in your browser
- No data is sent to external servers for processing
- Book content remains private on your device
- Optional cloud sync (if implemented) with encryption

## 🎨 User Interface

### **Design System**
- **Color Palette**: Modern gradient-based design with accessible contrast
- **Typography**: Clean, readable fonts optimized for academic content
- **Responsive Layout**: Seamless experience across all device sizes
- **Dark/Light Mode**: Comfortable viewing in any environment
- **Accessibility**: WCAG 2.1 compliant with keyboard navigation support

### **Navigation**
- **Header Navigation**: Quick access to all main features
- **Breadcrumb System**: Clear path tracking for complex workflows
- **Search Integration**: Global search across all content types
- **Quick Actions**: Context-sensitive shortcuts and buttons

## 📊 Analytics & Insights

### **Learning Analytics**
- **Progress Tracking**: Monitor your learning journey over time
- **Performance Metrics**: Detailed exam and quiz statistics
- **Knowledge Gaps**: Identify areas needing additional focus
- **Study Patterns**: Understand your most effective learning times

### **Content Statistics**
- **Library Overview**: Total books, subjects, and completion rates
- **Usage Metrics**: Most accessed books and frequently asked questions
- **Generation History**: Track created exams and scripts
- **Time Investment**: Monitor study time and session duration

## 🤝 Contributing

We welcome contributions to make Zakerly even better! Please read our contributing guidelines and feel free to submit issues, feature requests, or pull requests.

### **Development Workflow**
1. Fork the repository
2. Create a feature branch
3. Make your changes with proper TypeScript typing
4. Test across different browsers and devices
5. Submit a pull request with detailed description

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### **Common Issues**
- **AI Model Loading**: Ensure stable internet connection for initial model download
- **Performance**: Close other browser tabs if experiencing slowdowns
- **File Upload**: Check file format and size limitations (100MB max)
- **Browser Compatibility**: Use Chrome, Firefox, or Safari for best experience

### **Getting Help**
- Check the [FAQ section](docs/FAQ.md) for common questions
- Submit issues on our GitHub repository
- Join our community Discord for real-time support
- Contact our support team for enterprise inquiries

## 🎯 Roadmap

### **Upcoming Features**
- **Multi-language Support**: Interface localization for global users
- **Collaborative Study**: Share resources and study together
- **Advanced Analytics**: Deeper insights into learning patterns
- **Mobile Apps**: Native iOS and Android applications
- **Integration APIs**: Connect with popular learning management systems

### **Long-term Vision**
- **Personalized AI Tutoring**: Adaptive learning paths based on individual progress
- **Research Assistant**: Advanced academic research and citation tools
- **Institution Support**: Features designed for educational institutions
- **Offline Capabilities**: Full functionality without internet connection

---

**Made with ❤️ for the academic community**

Transform your learning experience today with Zakerly - where AI meets academic excellence.