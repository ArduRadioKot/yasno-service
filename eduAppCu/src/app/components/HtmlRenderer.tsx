import { useEffect, useRef } from 'react';
import { config, resolveImageUrl } from '../config';

interface HtmlRendererProps {
  html: string;
  className?: string;
}

function decodeHtmlEntities(text: string): string {
  if (!text.includes('&lt;') && !text.includes('&gt;') && !text.includes('&amp;')) {
    return text;
  }
  const textarea = document.createElement('textarea');
  textarea.innerHTML = text;
  return textarea.value;
}

function looksLikeHtml(text: string): boolean {
  return /<\/?[a-z][\s\S]*>/i.test(text);
}

function applyMarkdown(text: string): string {
  let processed = text.replace(/\u00a0/g, ' ');

  processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  processed = processed.replace(/__([^_]+)__/g, '<strong>$1</strong>');
  processed = processed.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
  processed = processed.replace(/_([^_\n]+)_/g, '<em>$1</em>');
  processed = processed.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  processed = processed.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  processed = processed.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  processed = processed.replace(/`([^`]+)`/g, '<code>$1</code>');
  processed = processed.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
  processed = processed.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
  );

  if (!processed.includes('<p>') && !processed.includes('<br')) {
    processed = processed
      .split(/\n{2,}/)
      .map((block) => block.trim())
      .filter(Boolean)
      .map((block) => `<p>${block.replace(/\n/g, '<br>')}</p>`)
      .join('');
  } else {
    processed = processed.replace(/\n\n/g, '</p><p>');
    processed = processed.replace(/\n/g, '<br>');
  }

  return processed;
}

function processHtml(htmlContent: string): string {
  if (!htmlContent) return '';

  let processed = decodeHtmlEntities(htmlContent.trim());
  const isHtml = looksLikeHtml(processed);

  if (!isHtml) {
    processed = applyMarkdown(processed);
  }

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
      return `<img${beforeSrc}src="${finalSrc}"${afterSrc} class="sdamgia-formula" referrerpolicy="no-referrer" loading="lazy" />`;
    }
  );

  if (!isHtml) {
    const bareImagePattern = /(?<!src=["'])(https?:\/\/[^\s<"']+\.(?:svg|png|jpg|jpeg|gif|webp))/gi;
    processed = processed.replace(bareImagePattern, (url) => {
      const finalSrc = resolveImageUrl(url);
      return `<img src="${finalSrc}" alt="" class="sdamgia-formula" referrerpolicy="no-referrer" loading="lazy" />`;
    });
  }

  return processed;
}

export function HtmlRenderer({ html, className = '' }: HtmlRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const renderMath = async () => {
      if (!(window as Window & { katex?: unknown }).katex) {
        await loadKaTeX();
      }

      const katex = (
        window as Window & { katex?: { render: (text: string, el: HTMLElement, opts: object) => void } }
      ).katex;
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
      if (img.src.startsWith('data:')) {
        img.src = img.src.replace(/\s+/g, '');
      }
      img.onerror = () => {
        if (img.dataset.fallbackApplied === 'true') return;
        img.dataset.fallbackApplied = 'true';
        img.alt = 'Изображение не загрузилось';
        img.classList.add('sdamgia-image-fallback');
        img.removeAttribute('srcset');
        img.src = config.images.fallback.replace(/\s+/g, '');
      };
    });
  }, [html]);

  return (
    <div
      ref={containerRef}
      className={`sdamgia-html ${className}`.trim()}
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
