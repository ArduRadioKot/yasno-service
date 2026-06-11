// Application configuration
export const config = {
  // Backend API URL for serving static files (images, etc.)
  // Falls back to localhost:8000 for development
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:5001',
  
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
  
  // If it's already an absolute URL or data URI, return as-is
  if (src.startsWith('http://') || src.startsWith('https://') || src.startsWith('data:')) {
    // Check if it's from an allowed external domain
    if (src.startsWith('http')) {
      try {
        const url = new URL(src);
        const domain = url.hostname;
        const isAllowed = config.images.allowedDomains.some(
          (allowed) => domain === allowed || domain.endsWith(`.${allowed}`) || domain.includes(allowed)
        );
        if (isAllowed) {
          return src;
        }
      } catch (e) {
        console.warn('Invalid external URL:', src);
      }
    }
    return src;
  }
  
  // If it's a relative path starting with /, prepend API base
  if (src.startsWith('/')) {
    return `${config.apiUrl}${src}`;
  }
  
  // If it's a relative path without leading /, prepend API base with /
  return `${config.apiUrl}/${src}`;
}
