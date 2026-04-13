export const pointCloudPoints = Array.from({ length: 160 }).map((_, index) => ({
  id: index,
  left: `${8 + ((index * 17) % 84)}%`,
  top: `${12 + ((index * 23) % 68)}%`,
  size: `${2 + ((index * 5) % 4)}px`,
  opacity: 0.22 + ((index * 13) % 55) / 100,
}));
