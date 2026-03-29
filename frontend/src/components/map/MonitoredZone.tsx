import { Tooltip } from 'react-leaflet'
import type { MonitoredArea } from '../../types'

interface MonitoredZoneProps {
  area: MonitoredArea
}

/**
 * Legacy component — no longer rendered on the map.
 * Kept for reference; neighborhood polygons are now rendered via NeighborhoodLayer.
 */
export function MonitoredZone({ area }: MonitoredZoneProps) {
  return (
    <Tooltip
      permanent
      direction="center"
      className="!bg-black/60 !border !border-primary !text-primary !text-[10px] !font-black !uppercase !tracking-widest !italic !rounded-none !shadow-none"
    >
      {area.name} ZONE
    </Tooltip>
  )
}
