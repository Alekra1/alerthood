import { CircleMarker, Tooltip } from 'react-leaflet'
import type { Threat, ThreatCategory } from '../../types'

const CATEGORY_COLORS: Record<ThreatCategory, string> = {
  CRIME: '#ff5545',
  UTILITY: '#fe9400',
  NATURAL: '#facc15',
  DISTURBANCE: '#c567f4',
}

interface ThreatMarkerProps {
  threat: Threat
  onSelect: (threat: Threat) => void
  isSelected: boolean
}

export function ThreatMarker({ threat, onSelect, isSelected }: ThreatMarkerProps) {
  const color = CATEGORY_COLORS[threat.category]

  return (
    <>
      {isSelected && (
        <CircleMarker
          center={[threat.lat, threat.lng]}
          radius={20}
          pathOptions={{
            color,
            fillColor: color,
            fillOpacity: 0.15,
            weight: 0,
          }}
          eventHandlers={{ click: () => onSelect(threat) }}
        />
      )}
      <CircleMarker
        center={[threat.lat, threat.lng]}
        radius={isSelected ? 10 : 7}
        pathOptions={{
          color: '#000000',
          weight: 2,
          fillColor: color,
          fillOpacity: 1,
        }}
        eventHandlers={{ click: () => onSelect(threat) }}
      >
        <Tooltip
          permanent={false}
          direction="top"
          offset={[0, -8]}
          className="!bg-surface-container !border-2 !border-black !shadow-hard !rounded-none !font-headline !text-[10px] !font-bold !uppercase !tracking-widest !text-on-surface !px-2 !py-1"
        >
          {threat.category} • {threat.location}
        </Tooltip>
      </CircleMarker>
    </>
  )
}
