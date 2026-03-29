export type ThreatCategory = 'CRIME' | 'UTILITY' | 'NATURAL' | 'DISTURBANCE'
export type ThreatSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface Threat {
  id: string
  title: string
  category: ThreatCategory
  severity: ThreatSeverity
  severityPct: number
  relevancePct: number
  location: string
  lat: number
  lng: number
  minutesAgo: number
  upvotes: number
  downvotes: number
  source: string
}

export interface MonitoredArea {
  id: string
  name: string
  area_type: 'city' | 'neighborhood'
  parent_name: string | null
  safety_score: number
  safety_color: string
  isActive: boolean
  notifyCrime: boolean
  notifyUtility: boolean
  notifyNatural: boolean
  notifyDisturbance: boolean
}

export interface Badge {
  id: string
  name: string
  icon: string
  color: 'primary' | 'secondary' | 'tertiary'
  earned: boolean
}

export interface UserProfile {
  name: string
  email: string
  karma: number
  karmaWeekly: number
  trustScore: number
  streakDays: number
  badges: Badge[]
  areas: MonitoredArea[]
}

export type TabId = 'map' | 'feed' | 'profile'

export interface Notification {
  id: string
  userId: string
  eventId: string | null
  title: string
  body: string | null
  isRead: boolean
  createdAt: string
}
