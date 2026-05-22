import { useApp } from '../context/AppContext';
import type { Subject } from '../types';
import {
  Atom,
  Calculator,
  BookOpen,
  Landmark,
  FlaskConical,
  Laptop,
  Dna,
  Globe,
  ScrollText,
  Languages,
  Users,
} from 'lucide-react';

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  'atom': Atom,
  'calculator': Calculator,
  'book-open': BookOpen,
  'landmark': Landmark,
  'flask-conical': FlaskConical,
  'laptop': Laptop,
  'dna': Dna,
  'globe': Globe,
  'scroll-text': ScrollText,
  'languages': Languages,
  'users': Users,
};

function SubjectIcon({ iconName, className }: { iconName: string; className?: string }) {
  const Icon = iconMap[iconName] || Atom;
  return <Icon className={className} />;
}

type SubjectSelectorProps = {
  variant?: 'pills' | 'grid';
  className?: string;
};

export default function SubjectSelector({
  variant = 'pills',
  className = '',
}: SubjectSelectorProps) {
  const { subjects, activeSubjectId, setActiveSubject } = useApp();

  if (variant === 'grid') {
    return (
      <div className={`grid grid-cols-2 sm:grid-cols-3 gap-3 ${className}`}>
        {subjects.map((subject) => (
          <SubjectCard
            key={subject.id}
            subject={subject}
            active={activeSubjectId === subject.id}
            onSelect={() => setActiveSubject(subject.id)}
          />
        ))}
      </div>
    );
  }

  return (
    <div className={`flex gap-2 overflow-x-auto pb-1 scrollbar-hide ${className}`}>
      {subjects.map((subject) => {
        const active = activeSubjectId === subject.id;
        return (
          <button
            key={subject.id}
            onClick={() => setActiveSubject(subject.id)}
            className={`shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-xl border transition-all ${
              active
                ? 'border-[#6D3DF5] bg-[#6D3DF5]/10 text-[#6D3DF5]'
                : 'border-border bg-white text-foreground hover:border-muted-foreground/30'
            }`}
          >
            <SubjectIcon iconName={subject.icon} className="size-5" />
            <span className="font-medium text-sm whitespace-nowrap">{subject.name}</span>
          </button>
        );
      })}
    </div>
  );
}

function SubjectCard({
  subject,
  active,
  onSelect,
}: {
  subject: Subject;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      className={`text-left p-4 rounded-2xl border transition-all ${
        active
          ? 'border-[#6D3DF5] bg-[#6D3DF5]/10 text-[#6D3DF5]'
          : 'border-border bg-white hover:shadow-md'
      }`}
    >
      <SubjectIcon iconName={subject.icon} className="size-8 mb-2" />
      <span className="font-semibold block">{subject.name}</span>
      <span className="text-xs mt-1 block text-muted-foreground">
        цель {subject.targetScore} б.
      </span>
    </button>
  );
}
