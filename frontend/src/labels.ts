/**
 * Arayüz etiketleri. Backend sınıf adları (İngilizce) değiştirilmez;
 * yalnızca kullanıcıya gösterimde Türkçe karşılık kullanılır.
 */

const DEFECT_LABELS: Record<string, string> = {
  insufficient_solder: 'Yetersiz Lehim',
  excess_solder: 'Fazla Lehim',
  solder_bridge: 'Lehim Köprüsü',
  solder_void: 'Lehim Boşluğu',
  missing_component: 'Eksik Komponent',
  shifted_component: 'Kaymış Komponent',
  burn: 'Yanık',
  physical_damage: 'Fiziksel Hasar',
  oxidation: 'Oksitlenme',
}

const COMPONENT_LABELS: Record<string, string> = {
  resistor: 'Direnç',
  capacitor: 'Kondansatör',
  ic: 'Entegre Devre',
  diode: 'Diyot',
  inductor: 'Bobin',
  connector: 'Konnektör',
  transistor: 'Transistör',
  oscillator: 'Osilatör',
  'switch/button': 'Anahtar / Buton',
  led: 'LED',
}

const ISSUE_LABELS: Record<string, string> = {
  missing_component: 'Eksik komponent',
  wrong_component: 'Yanlış komponent',
  shifted_component: 'Kaymış komponent',
  extra_component: 'Fazla komponent',
}

function humanize(name: string): string {
  return name
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

export function defectLabel(name: string): string {
  return DEFECT_LABELS[name] ?? COMPONENT_LABELS[name] ?? humanize(name)
}

export function componentLabel(name: string): string {
  return COMPONENT_LABELS[name] ?? DEFECT_LABELS[name] ?? humanize(name)
}

export function issueLabel(name: string): string {
  return ISSUE_LABELS[name] ?? humanize(name)
}
