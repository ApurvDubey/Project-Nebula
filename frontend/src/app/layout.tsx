import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nebula",
  description: "Chat with your documents locally",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased min-h-screen bg-background text-gray-100 font-sans selection:bg-primary-600/30">
        {children}
      </body>
    </html>
  );
}
