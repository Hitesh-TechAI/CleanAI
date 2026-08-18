import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import FileUpload from "@/components/FileUpload";
import DataPreview from "@/components/DataPreview";
import DatasetStats from "@/components/DatasetStats";
import ChatInterface from "@/components/ChatInterface";
import CleaningSummary from "@/components/CleaningSummary";

const Index = () => {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <Hero />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Two column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Upload + Preview + Stats */}
          <div className="space-y-6">
            <FileUpload />
            <DatasetStats />
            <DataPreview />
          </div>

          {/* Right: Chat */}
          <div>
            <ChatInterface />
          </div>
        </div>

        {/* Bottom: Summary */}
        <CleaningSummary />
      </main>
    </div>
  );
};

export default Index;
