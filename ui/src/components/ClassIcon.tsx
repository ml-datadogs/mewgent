const CLASS_ICON_MAP: Record<string, string> = {
  Collarless: 'Collarless_Icon.png',
  Fighter: 'Fighter_Icon.png',
  Hunter: 'Hunter_Icon.png',
  Mage: 'Mage_Icon.png',
  Tank: 'Tank_Icon.png',
  Cleric: 'Cleric_Icon.png',
  Thief: 'Thief_Icon.png',
  Necromancer: 'Necromancer_Icon.png',
  Tinkerer: 'Tinkerer_Icon.png',
  Butcher: 'Butcher_Icon.png',
  Druid: 'Druid_Icon.png',
  Psychic: 'Psychic_Icon.png',
  Monk: 'Monk_Icon.png',
  Jester: 'Jester_Icon.png',
};

// eslint-disable-next-line react-refresh/only-export-components
export function classIconUrl(className: string): string | null {
  const file = CLASS_ICON_MAP[className];
  if (!file) return null;
  return `./icons/classes/${file}`;
}

interface ClassIconProps {
  name: string;
  size?: number;
  className?: string;
}

export function ClassIcon({ name, size = 16, className = '' }: ClassIconProps) {
  const url = classIconUrl(name);
  if (!url) return null;
  return (
    <img
      src={url}
      alt={name}
      width={size}
      height={size}
      className={`inline-block shrink-0 ${className}`}
      style={{ imageRendering: 'auto' }}
    />
  );
}
