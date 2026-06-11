import { useEffect, useRef } from 'react';
import { config, resolveImageUrl } from '../config';

interface HtmlRendererProps {
  html: string;
  className?: string;
}

export function HtmlRenderer({ html, className = '' }: HtmlRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const renderMath = async () => {
      if (!(window as Window & { katex?: unknown }).katex) {
        await loadKaTeX();
      }

      const katex = (window as Window & { katex?: { render: (text: string, el: HTMLElement, opts: object) => void } }).katex;
      if (!katex) return;

      const elements = containerRef.current?.querySelectorAll('.math-tex') || [];
      elements.forEach((el) => {
        const text = el.textContent || '';
        try {
          katex.render(text, el as HTMLElement, {
            throwOnError: false,
            displayMode: el.classList.contains('display-mode'),
          });
        } catch (error) {
          console.error('KaTeX render error:', error);
        }
      });
    };

    void renderMath();

    const images = containerRef.current.querySelectorAll('img');
    images.forEach((img) => {
      img.referrerPolicy = 'no-referrer';
      img.onerror = () => {
        img.src = config.images.fallback;
        img.alt = 'Изображение не загрузилось';
      };
    });
  }, [html]);

  const processHtml = (htmlContent: string): string => {
    let processed = htmlContent.replace(/\u00a0/g, ' ');

    processed = processed.replace(/\$([^$]+)\$/g, '<span class="math-tex">$1</span>');
    processed = processed.replace(
      /\\\[([^\]]+)\\\]/g,
      '<div class="math-tex display-mode">$1</div>'
    );
    processed = processed.replace(
      /<math[^>]*>(.*?)<\/math>/gis,
      '<span class="math-tex">$1</span>'
    );

    processed = processed.replace(
      /<img([^>]*?)src=["']([^"']+)["']([^>]*?)>/gi,
      (_match, beforeSrc, src, afterSrc) => {
        const finalSrc = resolveImageUrl(src);
        return `<img${beforeSrc}src="${finalSrc}"${afterSrc} class="sdamgia-formula" referrerpolicy="no-referrer" style="max-width:100%;height:auto;display:inline-block;vertical-align:middle;margin:4px 0;border-radius:8px;" loading="lazy" />`;
      }
    );

    const bareImagePattern = /(https?:\/\/[^\s<"']+\.(?:svg|png|jpg|jpeg|gif))/gi;
    processed = processed.replace(bareImagePattern, (url) => {
      const finalSrc = resolveImageUrl(url);
      return `<img src="${finalSrc}" alt="" class="sdamgia-formula" referrerpolicy="no-referrer" style="max-width:100%;height:auto;display:inline-block;vertical-align:middle;margin:4px 0;border-radius:8px;" loading="lazy" />`;
    });

    return processed;
  };

  return (
    <div
      ref={containerRef}
      className={`sdamgia-html ${className}`.trim()}
      style={{ fontSize: 'inherit', lineHeight: 'inherit' }}
      dangerouslySetInnerHTML={{ __html: processHtml(html) }}
    />
  );
}

async function loadKaTeX() {
  return new Promise<void>((resolve, reject) => {
    if ((window as Window & { katex?: unknown }).katex) {
      resolve();
      return;
    }

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css';
    document.head.appendChild(link);

    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js';
    script.async = true;
    script.onload = () => resolve();
    script.onerror = reject;
    document.head.appendChild(script);
  });
}
