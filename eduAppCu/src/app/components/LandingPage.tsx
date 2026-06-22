import { useState } from "react";
import { motion } from "motion/react";
import {
  Brain,
  Camera,
  TrendingUp,
  FileText,
  Trophy,
  Target,
  Menu,
  X,
  ArrowRight,
  Sparkles,
  CheckCircle,
  BookOpen,
  Zap,
  Star,
} from "lucide-react";
import phoneScreen from "@/imports/image.png";
import aiChat from "@/imports/image-1.png";
import { ImageWithFallback } from "./ImageWithFallback";

const FONT = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

const features = [
  {
    icon: Target,
    title: "Персональный трек",
    desc: "Алгоритм находит твои слабые темы и перестраивает план обучения на лету — ты учишь только то, что реально нужно.",
  },
  {
    icon: Brain,
    title: "ИИ-Ментор 24/7",
    desc: "Задай вопрос в чат, попроси объяснить проще или мгновенно разбери сложные формулы — ИИ доступен в любое время.",
  },
  {
    icon: Camera,
    title: "Разбор по фото",
    desc: "Застрял на задаче из сборника? Просто сфотографируй её — ИИ выдаст пошаговое решение и объяснит логику.",
  },
  {
    icon: TrendingUp,
    title: "Прогноз баллов",
    desc: "Динамический график реального результата на ОГЭ/ЕГЭ на основе твоих текущих успехов — видишь рост каждый день.",
  },
  {
    icon: FileText,
    title: "Честные КИМы",
    desc: "Полноценные симуляторы экзаменов. ИИ проверяет даже сложную развёрнутую часть строго по критериям ФИПИ.",
  },
  {
    icon: Trophy,
    title: "Умные достижения",
    desc: "Встроенная система мотивации и флеш-карточки помогут закрепить материал без нудной зубрёжки.",
  },
];

const subjects = ["Физика", "Математика", "Русский язык", "Химия", "История", "Биология", "Обществознание", "Информатика"];

const freePlan = [
  "1 предмет на выбор",
  "До 10 заданий в день",
  "Базовый ИИ-чат (5 вопросов/день)",
  "Прогноз баллов",
  "Серия дней и достижения",
];

const premiumPlan = [
  "Все предметы без ограничений",
  "Неограниченные задания",
  "ИИ-Ментор без лимитов 24/7",
  "Разбор задач по фото",
  "Полные симуляторы КИМов",
  "Приоритетные обновления",
];

interface LandingPageProps {
  onGetStarted: () => void;
}

export default function LandingPage({ onGetStarted }: LandingPageProps) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background text-foreground" style={{ fontFamily: FONT }}>
      {/* NAV */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-border">
        <div className="max-w-6xl mx-auto px-5 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen size={22} className="text-foreground" strokeWidth={2.5} />
            <span className="text-xl font-black text-foreground tracking-tight" style={{ fontFamily: FONT }}>Ясно!</span>
          </div>

          <nav className="hidden md:flex items-center gap-8 text-sm font-semibold text-muted-foreground">
            <a href="#features" className="hover:text-primary transition-colors">Возможности</a>
            <a href="#how" className="hover:text-primary transition-colors">Как работает</a>
            <a href="#pricing" className="hover:text-primary transition-colors">Тарифы</a>
          </nav>

          <div className="hidden md:flex items-center gap-3">
            <button onClick={onGetStarted} className="text-sm font-semibold text-muted-foreground hover:text-primary transition-colors px-4 py-2">
              Войти
            </button>
            <button onClick={onGetStarted} className="bg-primary text-white text-sm font-bold px-5 py-2.5 rounded-xl hover:bg-violet-700 transition-colors">
              Начать бесплатно
            </button>
          </div>

          <button
            className="md:hidden p-2 rounded-lg hover:bg-muted transition-colors"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {menuOpen && (
          <div className="md:hidden bg-white border-t border-border px-5 py-4 flex flex-col gap-4">
            <a href="#features" className="text-sm font-semibold hover:text-primary" onClick={() => setMenuOpen(false)}>Возможности</a>
            <a href="#how" className="text-sm font-semibold hover:text-primary" onClick={() => setMenuOpen(false)}>Как работает</a>
            <a href="#pricing" className="text-sm font-semibold hover:text-primary" onClick={() => setMenuOpen(false)}>Тарифы</a>
            <div className="flex gap-3 pt-2 border-t border-border">
              <button onClick={onGetStarted} className="text-sm font-semibold text-muted-foreground px-4 py-2.5 rounded-xl border border-border flex-1">Войти</button>
              <button onClick={onGetStarted} className="bg-primary text-white text-sm font-bold px-4 py-2.5 rounded-xl flex-1">Начать</button>
            </div>
          </div>
        )}
      </header>

      {/* HERO */}
      <section className="pt-32 pb-20 px-5 relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-violet-100 rounded-full opacity-40 blur-3xl translate-x-1/3 -translate-y-1/4" />
          <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-blue-100 rounded-full opacity-30 blur-3xl -translate-x-1/3 translate-y-1/4" />
        </div>

        <div className="max-w-6xl mx-auto relative">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="inline-flex items-center gap-2 bg-accent text-accent-foreground text-xs font-bold px-3 py-1.5 rounded-full mb-6">
                <Sparkles size={12} />
                AI-подготовка нового поколения
              </div>

              <h1 className="text-4xl md:text-5xl lg:text-6xl font-black leading-[1.1] tracking-tight mb-6" style={{ fontFamily: FONT }}>
                Готовься к экзаменам{" "}
                <span className="text-primary">эффективно</span>{" "}
                с ИИ-ментором
              </h1>

              <p className="text-lg text-muted-foreground leading-relaxed mb-8 max-w-md">
                Умная адаптивная платформа для подготовки к ОГЭ и ЕГЭ.
                Хватит переплачивать репетиторам — учись в своём темпе.
              </p>

              <div className="flex flex-col sm:flex-row gap-3 mb-10">
                <button onClick={onGetStarted} className="bg-primary text-white font-bold text-base px-8 py-4 rounded-2xl hover:bg-violet-700 transition-all hover:scale-[1.02] active:scale-[0.98] shadow-lg shadow-violet-200 flex items-center justify-center gap-2">
                  Начать бесплатно
                  <ArrowRight size={18} />
                </button>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 32 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.7, delay: 0.15 }}
              className="flex justify-center lg:justify-end relative"
            >
              <div className="relative">
                <div className="w-60 md:w-68 rounded-[2.5rem] overflow-hidden shadow-2xl">
                  <ImageWithFallback
                    src={phoneScreen}
                    alt="Приложение Ясно! — главный экран"
                    className="w-full h-auto object-cover"
                  />
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* SUBJECTS TICKER */}
      <section className="py-8 bg-muted border-y border-border overflow-hidden">
        <div className="flex gap-3 animate-[scroll_22s_linear_infinite] whitespace-nowrap">
          {[...subjects, ...subjects, ...subjects, ...subjects].map((s, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-2 bg-white border border-border rounded-full px-5 py-2 text-sm font-semibold text-foreground shrink-0"
            >
              <span className="w-2 h-2 bg-primary rounded-full" />
              {s}
            </span>
          ))}
        </div>
        <style>{`@keyframes scroll { from { transform: translateX(0); } to { transform: translateX(-50%); } }`}</style>
      </section>

      {/* FEATURES */}
      <section id="features" className="py-24 px-5">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 bg-accent text-accent-foreground text-xs font-bold px-3 py-1.5 rounded-full mb-4">
              <CheckCircle size={12} />
              Всё включено
            </div>
            <h2 className="text-3xl md:text-4xl font-black tracking-tight" style={{ fontFamily: FONT }}>
              Всё, что нужно для сотки,
              <br />
              <span className="text-primary">в одном месте</span>
            </h2>
            <p className="text-muted-foreground mt-4 max-w-md mx-auto">
              Никаких скучных тестов — только умная подготовка, которая реально работает
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08, duration: 0.5 }}
                className="group bg-card border border-border rounded-2xl p-6 hover:border-primary/30 hover:shadow-lg hover:shadow-violet-50 transition-all duration-300"
              >
                <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-4 bg-accent text-primary">
                  <f.icon size={22} />
                </div>
                <h3 className="font-bold text-lg mb-2">{f.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="py-24 px-5 bg-muted">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-black tracking-tight" style={{ fontFamily: FONT }}>
              Как это работает
            </h2>
            <p className="text-muted-foreground mt-4">Три шага до результата</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: "01", title: "Выбери предмет", desc: "Укажи предмет и дату экзамена. ИИ оценит уровень знаний и составит персональный план.", Icon: Target },
              { step: "02", title: "Занимайся каждый день", desc: "Выполняй задания из плана, задавай вопросы ИИ-ментору, фотографируй непонятные задачи.", Icon: BookOpen },
              { step: "03", title: "Следи за прогрессом", desc: "Смотри, как растёт прогноз баллов. Получай достижения и не теряй серию дней.", Icon: TrendingUp },
            ].map((step, i) => (
              <motion.div
                key={step.step}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
                className="bg-card rounded-2xl p-8 border border-border text-center"
              >
                <div className="w-20 h-20 bg-secondary rounded-full flex items-center justify-center mx-auto mb-5">
                  <step.Icon size={32} className="text-primary" />
                </div>
                <div className="text-xs font-bold text-primary tracking-widest uppercase mb-2">Шаг {step.step}</div>
                <h3 className="font-bold text-xl mb-3">{step.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* AI CHAT SHOWCASE */}
      <section className="py-24 px-5">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <div className="inline-flex items-center gap-2 bg-accent text-accent-foreground text-xs font-bold px-3 py-1.5 rounded-full mb-6">
                <Brain size={12} />
                ИИ-Ментор
              </div>
              <h2 className="text-3xl md:text-4xl font-black tracking-tight mb-6" style={{ fontFamily: FONT }}>
                Твой личный
                <br />
                <span className="text-primary">репетитор в кармане</span>
              </h2>
              <p className="text-muted-foreground leading-relaxed mb-8">
                Забудь о занятиях по расписанию. ИИ-ментор объясняет любые темы простым языком,
                разбирает ошибки и всегда готов помочь — в 2 ночи перед экзаменом тоже.
              </p>
              <ul className="space-y-4">
                {[
                  "Объясняет темы на твоём уровне",
                  "Разбирает задачи пошагово",
                  "Составляет мини-тесты по запросу",
                  "Помнит твои ошибки и возвращается к ним",
                ].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-sm font-semibold">
                    <CheckCircle size={18} className="text-primary shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex justify-center">
              <div className="relative">
                <div className="absolute inset-0 bg-violet-200 rounded-[2.5rem] blur-2xl opacity-50 scale-95 translate-y-4" />
                <div className="relative w-60 md:w-68 rounded-[2.5rem] overflow-hidden shadow-2xl">
                  <ImageWithFallback
                    src={aiChat}
                    alt="ИИ-чат в приложении Ясно!"
                    className="w-full h-auto object-cover"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* PRICING */}
      <section id="pricing" className="py-24 px-5 bg-muted">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 bg-accent text-accent-foreground text-xs font-bold px-3 py-1.5 rounded-full mb-4">
              <Star size={12} />
              Тарифы
            </div>
            <h2 className="text-3xl md:text-4xl font-black tracking-tight" style={{ fontFamily: FONT }}>
              Выбери свой план
            </h2>
            <p className="text-muted-foreground mt-4 max-w-sm mx-auto">
              Начни бесплатно, перейди на Премиум когда будешь готов
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {/* Free plan */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="bg-card border border-border rounded-2xl p-8 flex flex-col"
            >
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-9 h-9 bg-muted rounded-xl flex items-center justify-center">
                    <BookOpen size={18} className="text-muted-foreground" />
                  </div>
                  <span className="font-bold text-lg">Бесплатный</span>
                </div>
                <div className="text-4xl font-black mb-1">0 ₽</div>
                <div className="text-sm text-muted-foreground">Навсегда бесплатно</div>
              </div>

              <ul className="space-y-3 mb-8 flex-1">
                {freePlan.map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm">
                    <CheckCircle size={16} className="text-muted-foreground shrink-0 mt-0.5" />
                    <span className="text-muted-foreground">{item}</span>
                  </li>
                ))}
              </ul>

              <button onClick={onGetStarted} className="w-full border-2 border-border text-foreground font-bold py-3.5 rounded-xl hover:border-primary hover:text-primary transition-colors">
                Начать бесплатно
              </button>
            </motion.div>

            {/* Premium plan */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="bg-foreground text-background rounded-2xl p-8 flex flex-col relative overflow-hidden"
            >
              {/* Glow */}
              <div className="absolute top-0 right-0 w-48 h-48 bg-primary rounded-full opacity-20 blur-3xl translate-x-1/2 -translate-y-1/2 pointer-events-none" />

              <div className="mb-6 relative">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-9 h-9 bg-primary rounded-xl flex items-center justify-center">
                      <Zap size={18} className="text-white" />
                    </div>
                    <span className="font-bold text-lg">Премиум</span>
                  </div>
                  <span className="text-xs font-bold bg-primary/20 text-violet-300 px-2.5 py-1 rounded-full">
                    Популярный
                  </span>
                </div>

                {/* Telegram Stars price */}
                <div className="flex items-end gap-2 mb-1">
                  <div className="text-4xl font-black">120</div>
                  <div className="flex items-center gap-1 mb-1.5">
                    <span className="text-yellow-400 text-xl">⭐</span>
                    <span className="text-white/70 text-sm font-semibold">Telegram Stars</span>
                  </div>
                </div>
                <div className="text-sm text-white/50">Оплата через Telegram-бота</div>
              </div>

              <ul className="space-y-3 mb-8 flex-1 relative">
                {premiumPlan.map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm">
                    <CheckCircle size={16} className="text-violet-400 shrink-0 mt-0.5" />
                    <span className="text-white/90">{item}</span>
                  </li>
                ))}
              </ul>

              <button className="relative w-full bg-primary text-white font-bold py-3.5 rounded-xl hover:bg-violet-500 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2 shadow-lg shadow-violet-900/30">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L7.19 13.6l-2.948-.924c-.64-.203-.654-.64.136-.953l11.52-4.44c.533-.194 1.001.13.996.938z"/>
                </svg>
                Оплатить в Telegram
              </button>

              <a href="https://t.me/yasno_sub_bot" className="text-xs text-white/40 text-center mt-3">
                Открывает бот · Оплата в один клик
              </a>
            </motion.div>
          </div>

          {/* Note about Telegram Stars */}
          <p className="text-center text-sm text-muted-foreground mt-8">
            Telegram Stars — внутренняя валюта Telegram. Купить их можно прямо в приложении Telegram в разделе «Настройки → Telegram Stars».
          </p>
        </div>
      </section>

      {/* CTA BANNER */}
      <section className="py-24 px-5">
        <div className="max-w-4xl mx-auto">
          <div className="bg-foreground text-background rounded-3xl p-12 md:p-16 text-center relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary rounded-full opacity-20 blur-3xl translate-x-1/2 -translate-y-1/2" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-violet-400 rounded-full opacity-20 blur-2xl -translate-x-1/2 translate-y-1/2" />
            <div className="relative">
              <div className="flex justify-center mb-4">
                <Target size={44} className="text-violet-400" />
              </div>
              <h2 className="text-3xl md:text-4xl font-black tracking-tight mb-4" style={{ fontFamily: FONT }}>
                Сделай свой результат{" "}
                <span className="text-violet-400">ясным</span>
              </h2>
              <p className="text-white/70 mb-8 max-w-md mx-auto">
                Присоединяйся к умной подготовке и подними прогноз баллов уже через неделю.
              </p>
              <button onClick={onGetStarted} className="bg-primary text-white font-bold text-base px-10 py-4 rounded-2xl hover:bg-violet-500 transition-all hover:scale-[1.03] active:scale-[0.98] shadow-lg shadow-violet-900/30 inline-flex items-center gap-2">
                Запустить приложение
                <ArrowRight size={18} />
              </button>
              <p className="text-white/40 text-sm mt-4">Бесплатно · Без регистрации карты</p>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-border py-10 px-5">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <BookOpen size={20} className="text-foreground" strokeWidth={2.5} />
            <span className="font-black text-lg" style={{ fontFamily: FONT }}>Ясно!</span>
          </div>
          <p className="text-sm text-muted-foreground text-center">
            © 2026 Ясно! Экосистема AI подготовки к экзаменам. Все права защищены.
          </p>
          <div className="flex gap-5 text-sm font-semibold text-muted-foreground">
            <a href="#" className="hover:text-primary transition-colors">Политика</a>
            <a href="#" className="hover:text-primary transition-colors">Условия</a>
            <a href="#" className="hover:text-primary transition-colors">Контакты</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
