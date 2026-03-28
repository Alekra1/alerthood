import { MOCK_PROFILE } from '../../data/mock'
import { MetricsBento } from './MetricsBento'
import { BadgeGrid } from './BadgeGrid'
import { MonitoredAreaCard } from './MonitoredAreaCard'

export function ProfileView() {
  const profile = MOCK_PROFILE

  return (
    <div className="px-4 max-w-2xl mx-auto space-y-8 mt-6">
      <section className="flex flex-col items-center pt-4">
        <div className="w-24 h-24 bg-surface-container border-4 border-black shadow-hard rounded-full flex items-center justify-center mb-4 overflow-hidden">
          <span
            className="material-symbols-outlined text-5xl text-primary"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            account_circle
          </span>
        </div>
        <h2 className="font-headline text-3xl font-bold uppercase tracking-tight">{profile.name}</h2>
        <p className="font-body text-on-surface-variant text-sm">{profile.email}</p>
      </section>

      <MetricsBento
        karma={profile.karma}
        karmaWeekly={profile.karmaWeekly}
        trustScore={profile.trustScore}
        streakDays={profile.streakDays}
      />

      <BadgeGrid badges={profile.badges} />

      <section className="space-y-4">
        <h3 className="font-headline text-xl font-bold uppercase tracking-tight flex items-center gap-2">
          <span className="w-6 h-1 bg-secondary inline-block" />
          MONITORED AREAS
        </h3>
        {profile.areas.map((area, i) => (
          <MonitoredAreaCard
            key={area.id}
            area={area}
            onDelete={i > 0 ? (id) => console.log('delete', id) : undefined}
          />
        ))}
      </section>

      <section className="pb-12">
        <button className="w-full py-4 border-2 border-black font-headline font-bold text-error uppercase tracking-widest hover:bg-error-container hover:text-white transition-none active:translate-x-[2px] active:translate-y-[2px] active:shadow-none">
          LOGOUT SESSION
        </button>
      </section>
    </div>
  )
}
