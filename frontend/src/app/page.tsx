import Link from 'next/link';

export default function Home() {
  return (
    <main className="relative flex flex-col items-center justify-center min-h-screen p-8 text-center overflow-hidden">
      {/* Background Glows */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-600/20 rounded-full mix-blend-screen filter blur-[100px] animate-pulse-slow"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-600/20 rounded-full mix-blend-screen filter blur-[100px] animate-pulse-slow" style={{ animationDelay: '1.5s' }}></div>

      <div className="relative z-10 animate-slide-up">
        <h1 className="text-7xl font-display font-extrabold mb-6 tracking-tight text-white drop-shadow-sm">
          Welcome to <span className="text-gradient">Nebula</span>
        </h1>
        <p className="text-2xl text-gray-400 mb-12 max-w-2xl font-light leading-relaxed">
          Your fully offline, privacy-first second brain. Chat with your documents using advanced local AI.
        </p>
        
        <div className="flex justify-center gap-6">
          <Link 
            href="/notebooks" 
            className="px-8 py-4 bg-primary-600 hover:bg-primary-500 text-white rounded-xl font-semibold shadow-lg shadow-primary-500/30 transition-all duration-300 hover:-translate-y-1"
          >
            Open Notebooks
          </Link>
          <a
            href="https://github.com/yourusername/nebula"
            target="_blank"
            rel="noopener noreferrer"
            className="px-8 py-4 glass-panel hover:bg-white/10 text-white rounded-xl font-semibold transition-all duration-300 hover:-translate-y-1"
          >
            View on GitHub
          </a>
        </div>
      </div>
    </main>
  );
}
