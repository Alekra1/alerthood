interface SafetyScoreGaugeProps {
  score: number
  updatedAt: string | null
}

function getRiskColor(score: number): string {
  if (score >= 70) return '#4ade80'
  if (score >= 40) return '#FE9400'
  return '#FF5545'
}

function getRiskDescription(score: number, areaName: string): string {
  if (score >= 70) return 'Low incident activity. Generally safe.'
  if (score >= 40) return `Elevated activity near ${areaName}. Exercise caution after dark.`
  return 'High incident volume reported. Stay alert.'
}

function timeAgoFromDate(dateStr: string): string {
  const diffMs = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function SafetyScoreGauge({ score, updatedAt }: SafetyScoreGaugeProps) {
  const riskColor = getRiskColor(score)
  const deg = Math.round((score / 100) * 360)

  return (
    <div className="bg-surface-container border-2 border-black shadow-hard rounded-xl p-6 flex flex-col items-center gap-4">
      {/* Circular gauge */}
      <div className="relative flex items-center justify-center" style={{ width: 160, height: 160 }}>
        {/* Outer ring — conic-gradient */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: `conic-gradient(${riskColor} 0deg ${deg}deg, #2A2A2A ${deg}deg 360deg)`,
          }}
        />
        {/* Inner overlay */}
        <div
          className="absolute rounded-full bg-surface-container"
          style={{ inset: 12 }}
        />
        {/* Score text */}
        <div className="relative flex flex-col items-center">
          <span className="font-headline font-black text-5xl leading-none text-on-surface" style={{ color: riskColor }}>
            {score}
          </span>
          <span className="font-body text-xs text-on-surface-variant font-semibold">/100</span>
        </div>
      </div>

      {/* Subtitle */}
      <p className="font-body text-xs text-on-surface-variant uppercase tracking-widest font-bold">
        Safety score{updatedAt ? ` · updated ${timeAgoFromDate(updatedAt)}` : ''}
      </p>

      {/* Description */}
      <p className="font-body text-sm text-on-surface text-center">
        {getRiskDescription(score, 'your area')}
      </p>
    </div>
  )
}
