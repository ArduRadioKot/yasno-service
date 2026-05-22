import { useCallback, useEffect, useRef, useState } from 'react';
import { Send, Sparkles, BookOpen, FileQuestion, Zap, Loader2, Hand } from 'lucide-react';
import { api } from '../api/client';
import { useApp } from '../context/AppContext';
import type { ChatMessage } from '../types';

const iconMap = {
  book: BookOpen,
  question: FileQuestion,
  zap: Zap,
};

export default function ChatScreen() {
  const { activeSubjectId, activeSubject, pendingChatPrompt, clearPendingChatPrompt } = useApp();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      role: 'assistant',
      content:
        'Привет! Я твой AI-помощник Ясно! для подготовки к ЕГЭ\n\nВыбери предмет на вкладке «План» и задавай вопросы по темам, задачам и стратегии подготовки.',
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);
  const [prompts, setPrompts] = useState<{ text: string; icon: string }[]>([]);

  useEffect(() => {
    api
      .getChatSuggestions(activeSubjectId)
      .then((d) => setPrompts(d.prompts))
      .catch(() =>
        setPrompts([
          { text: 'Объясни проще', icon: 'book' },
          { text: 'Разбери задачу', icon: 'question' },
          { text: 'Составь мини тест', icon: 'zap' },
        ])
      );
  }, [activeSubjectId]);

  const handleSend = useCallback(
    async (text?: string) => {
      const msg = (text ?? inputText).trim();
      if (!msg || sending) return;

      const userMsg: ChatMessage = {
        id: Date.now(),
        role: 'user',
        content: msg,
      };
      setMessages((prev) => [...prev, userMsg]);
      setInputText('');
      setSending(true);

      try {
        const reply = await api.chat(msg, activeSubjectId);
        setMessages((prev) => [
          ...prev,
          { id: Date.now() + 1, role: 'assistant', content: reply.content },
        ]);
      } catch (error) {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
            role: 'assistant',
            content:
              error instanceof Error
                ? error.message
                : 'AI-чат сейчас недоступен. Проверьте backend и MISTRAL_API_KEY.',
          },
        ]);
      } finally {
        setSending(false);
      }
    },
    [activeSubjectId, inputText, sending]
  );

  const pendingHandled = useRef(false);
  useEffect(() => {
    if (!pendingChatPrompt || pendingHandled.current) return;
    pendingHandled.current = true;
    const prompt = pendingChatPrompt;
    clearPendingChatPrompt();
    handleSend(prompt).finally(() => {
      pendingHandled.current = false;
    });
  }, [pendingChatPrompt, clearPendingChatPrompt, handleSend]);

  return (
    <div className="h-full flex flex-col bg-[#F3F4F6]">
      <div className="bg-white border-b border-border px-4 sm:px-6 py-4 shrink-0">
        <div className="flex items-center gap-4 max-w-3xl mx-auto">
          <img src="/logo.png" alt="Ясно!" className="size-12 object-contain" />
          <div>
            <h2 className="font-semibold text-lg">Ясно!</h2>
            <div className="flex items-center gap-2">
              <div className="size-2 rounded-full bg-[#6D3DF5] animate-pulse" />
              <p className="text-sm text-muted-foreground">
                {activeSubject ? `${activeSubject.name}` : 'Онлайн'}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        <div className="max-w-3xl mx-auto w-full space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] md:max-w-[75%] rounded-2xl p-5 shadow-sm ${
                  message.role === 'user'
                    ? 'bg-[#6D3DF5] text-white'
                    : 'bg-white border border-border'
                }`}
              >
                {message.role === 'assistant' && (
                  <div className="flex items-center gap-2 mb-3">
                    <div className="size-7 rounded-xl bg-[#6D3DF5] flex items-center justify-center">
                      <Sparkles className="size-4 text-white" />
                    </div>
                    <span className="text-xs font-semibold text-[#6D3DF5]">Ясно!</span>
                  </div>
                )}
                <p
                  className={`leading-relaxed whitespace-pre-line ${
                    message.role === 'assistant' ? 'text-foreground' : ''
                  }`}
                >
                  {message.content}
                </p>
              </div>
            </div>
          ))}

          {messages.length <= 2 && prompts.length > 0 && (
            <div className="pt-4">
              <p className="text-sm text-muted-foreground mb-3 px-1">Попробуй спросить:</p>
              <div className="flex flex-wrap gap-2">
                {prompts.map((prompt, index) => {
                  const Icon = iconMap[prompt.icon as keyof typeof iconMap] ?? BookOpen;
                  return (
                    <button
                      key={index}
                      onClick={() => handleSend(prompt.text)}
                      className="inline-flex items-center gap-2 bg-white border border-border px-4 py-2.5 rounded-full text-sm font-medium hover:border-[#6D3DF5] hover:bg-[#6D3DF5]/5 transition-colors"
                    >
                      <Icon className="size-4 text-[#6D3DF5]" />
                      {prompt.text}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="shrink-0 bg-white border-t border-border p-4">
        <div className="max-w-3xl mx-auto w-full">
          <div className="bg-muted/50 rounded-2xl p-2 flex items-center gap-2">
            <div className="flex-1 bg-white rounded-2xl border border-border px-4 py-3">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                placeholder="Задай вопрос по выбранному предмету..."
                className="w-full bg-transparent outline-none"
                disabled={sending}
              />
            </div>
            <button
              onClick={() => handleSend()}
              disabled={!inputText.trim() || sending}
              className="size-11 rounded-2xl bg-[#6D3DF5] flex items-center justify-center disabled:opacity-40 shrink-0"
            >
              {sending ? (
                <Loader2 className="size-5 text-white animate-spin" />
              ) : (
                <Send className="size-5 text-white" />
              )}
            </button>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-3">
            AI может ошибаться. Проверяй важную информацию.
          </p>
        </div>
      </div>
    </div>
  );
}
