import { Circle, Tooltip } from 'react-leaflet'
import type { MonitoredArea } from '../../types'

const METERS_PER_MILE = 1609.34

interface MonitoredZoneProps {
  area: MonitoredArea
}

export function MonitoredZone({ area }: MonitoredZoneProps) {
  return (
    <Circle
      center={[area.lat, area.lng]}
      radius={area.radiusMiles * METERS_PER_MILE}
      pathOptions={{
        color: '#ffb4aa',
        weight: 2,
        dashArray: '8 6',
        fillColor: '#ffb4aa',
        fillOpacity: 0.05,
      }}
    >
      <Tooltip
        permanent
        direction="center"
        className="!bg-black/60 !border !border-primary !text-primary !text-[10px] !font-black !uppercase !tracking-widest !italic !rounded-none !shadow-none"
      >
        {area.name} ZONE
      </Tooltip>
    </Circle>
  )
}
