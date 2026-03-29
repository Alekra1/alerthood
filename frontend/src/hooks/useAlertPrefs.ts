import { useState } from 'react'

const KEY = 'alerthood:show_nearest_alerts'

function readPref(): boolean {
  try {
    return localStorage.getItem(KEY) === 'true'
  } catch {
    return false
  }
}

export function useAlertPrefs() {
  const [showNearest, setShowNearestState] = useState<boolean>(readPref)

  function setShowNearest(val: boolean) {
    try {
      localStorage.setItem(KEY, String(val))
    } catch { /* ignore */ }
    setShowNearestState(val)
  }

  return { showNearest, setShowNearest }
}
