import { MobileHeader } from "./mobile-header";
import { BottomNavigation } from "./bottom-navigation";
import { DashboardContent } from "./dashboard-content";

export default function PantauCukurDashboard() {
  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      {/* Sticky Mobile Header */}
      <MobileHeader />

      {/* Scrollable Main Content */}
      <DashboardContent />

      {/* Floating Bottom Navigation */}
      <BottomNavigation />
    </div>
  );
}
