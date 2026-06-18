// Application configuration
export const config = {
  // Backend API URL for serving static files (images, etc.)
  // Falls back to localhost:8000 for development
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  
  // Image loading configuration
  images: {
    // Enable lazy loading for images
    lazy: true,
    // Fallback image when loading fails
    fallback: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2YzZjRmNiIgcng9IjgiLz48dGV4dCB4PSI1MCIgeT0iNTAiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzZkM2RmNSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuKIkOKAnPCBpbWFnZTwvdGV4dD48L3N2Zz4=',
    // Maximum image width in pixels
    maxWidth: 800,
    // Allowed external domains for images
    allowedDomains: ['sdamgia.ru'],
  },
};

// Helper function to resolve image URLs
export function resolveImageUrl(src: string): string {
  if (!src) return config.images.fallback;

  const cleanSrc = src.replace(/\s+/g, '');

  if (cleanSrc.startsWith('http://') || cleanSrc.startsWith('https://') || cleanSrc.startsWith('data:')) {
    if (cleanSrc.startsWith('http')) {
      try {
        const url = new URL(cleanSrc);
        const domain = url.hostname;
        const isAllowed = config.images.allowedDomains.some(
          (allowed) => domain === allowed || domain.endsWith(`.${allowed}`) || domain.includes(allowed)
        );
        if (isAllowed) {
          return cleanSrc;
        }
      } catch {
        // ignore invalid URL
      }
    }
    return cleanSrc;
  }

  if (cleanSrc.startsWith('/')) {
    return `${config.apiUrl}${cleanSrc}`;
  }

  return `${config.apiUrl}/${cleanSrc}`;
}
