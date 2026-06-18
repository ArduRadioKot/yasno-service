import type { ReactNode } from 'react';

type LoadingOverlayProps = {
  children: ReactNode;
  className?: string;
};

export function LoadingOverlay({ children, className = '' }: LoadingOverlayProps) {
  return (
    <div
      className={`fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-6 ${className}`.trim()}
    >
      {children}
    </div>
  );
}
