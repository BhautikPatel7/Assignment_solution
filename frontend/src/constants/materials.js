/**
 * materials.js — Complete Material Catalog for Module 3
 * Textures served from /static/textures/{file}
 *
 * NOTE: "balcony" region = the RAILING detected by segmentation model.
 * Only railing texture types (no paint). Roof is excluded entirely.
 */

const PAINTS = [
  { id: 'paint_white',      hex: '#F5F5F0', name: 'Classic White',  rate_per_sqft: 4.50 },
  { id: 'paint_cream',      hex: '#F2E7D0', name: 'Warm Cream',     rate_per_sqft: 4.50 },
  { id: 'paint_beige',      hex: '#D8C7A3', name: 'Sandy Beige',    rate_per_sqft: 4.50 },
  { id: 'paint_grey',       hex: '#9E9E9E', name: 'Modern Grey',    rate_per_sqft: 4.50 },
  { id: 'paint_terracotta', hex: '#C1714A', name: 'Terracotta',     rate_per_sqft: 4.50 },
];

export const MATERIAL_CATALOG = {
  main_wall: {
    label: 'Main Wall',
    icon: '🏠',
    paints: PAINTS,
    textures: [
      { id: 'stone_natural',    name: 'Natural Stone',   file: 'stone_natural.png',    material_rate: 180, labor_rate: 70 },
      { id: 'stone_slate',      name: 'Slate Stone',     file: 'stone_slate.png',      material_rate: 160, labor_rate: 70 },
      { id: 'stone_sandstone',  name: 'Sandstone',       file: 'stone_sandstone.png',  material_rate: 140, labor_rate: 70 },
      { id: 'texture_sand',     name: 'Sand Finish',     file: 'texture_sand.png',     material_rate: 90,  labor_rate: 40 },
      { id: 'texture_concrete', name: 'Concrete Finish', file: 'texture_concrete.png', material_rate: 80,  labor_rate: 40 },
    ],
  },

  pillar: {
    label: 'Pillar',
    icon: '🏛️',
    paints: PAINTS,
    textures: [
      { id: 'stone_natural',  name: 'Natural Stone', file: 'stone_natural.png',  material_rate: 180, labor_rate: 70 },
      { id: 'texture_sand',   name: 'Sand Finish',   file: 'texture_sand.png',   material_rate: 90,  labor_rate: 40 },
      { id: 'texture_marble', name: 'Marble Finish', file: 'texture_marble.png', material_rate: 220, labor_rate: 80 },
    ],
  },

  // "balcony" = RAILING — no paint option, only railing textures
  balcony: {
    label: 'Balcony Railing',
    icon: '🔩',
    paints: [],   // railings cannot be painted with wall paint
    textures: [
      { id: 'railing_ms_steel',        name: 'MS Steel Railing',        file: 'railing_ms_steel.png',        material_rate: 280, labor_rate: 120 },
      { id: 'railing_stainless',       name: 'Stainless Steel',         file: 'railing_stainless.png',       material_rate: 450, labor_rate: 150 },
      { id: 'railing_aluminium',       name: 'Aluminium Railing',       file: 'railing_aluminium.png',       material_rate: 350, labor_rate: 120 },
      { id: 'railing_glass',           name: 'Glass Panel Railing',     file: 'railing_glass.png',           material_rate: 650, labor_rate: 200 },
      { id: 'railing_decorative_iron', name: 'Decorative Iron Railing', file: 'railing_decorative_iron.png', material_rate: 320, labor_rate: 140 },
    ],
  },

  // roof: REMOVED — roof cannot be changed in renovation

  boundary_wall: {
    label: 'Boundary Wall',
    icon: '🧱',
    paints: PAINTS,
    textures: [
      { id: 'stone_natural', name: 'Natural Stone', file: 'stone_natural.png', material_rate: 180, labor_rate: 70 },
      { id: 'stone_rubble',  name: 'Rubble Stone',  file: 'stone_rubble.png',  material_rate: 120, labor_rate: 60 },
    ],
  },
};

/** Lookup a material entry by region_id + material_id */
export function getMaterial(regionId, materialId) {
  const reg = MATERIAL_CATALOG[regionId];
  if (!reg) return null;
  return (
    reg.paints.find(p => p.id === materialId) ||
    reg.textures.find(t => t.id === materialId) ||
    null
  );
}

/** Return whether a material id is a paint/color (not a texture image) */
export function isPaint(materialId) {
  return materialId?.startsWith('paint_');
}

/** Texture image URL — served from FastAPI static mount */
export function textureUrl(file) {
  const base = import.meta.env.VITE_API_URL || '';
  return `${base}/static/textures/${file}`;
}
