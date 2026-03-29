// Module-level cache — survives route changes, resets on full page reload.
// MapView writes here when it gets a GPS fix; other views read from it.
let cached: { lat: number; lng: number } | null = null

export function getCachedUserLocation() {
  return cached
}

export function setCachedUserLocation(lat: number, lng: number) {
  cached = { lat, lng }
}
